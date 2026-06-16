import logging

from agents.calendar_agent import schedule_interview
from agents.email_agent import generate_email, send_email
from config.settings import settings
from services.interview_scheduler import allocate_interview_time
from storage.processed_resumes import (
    get_candidate,
    mark_interview_outcome,
    mark_offer_sent,
    record_candidate_error,
    reschedule_candidate,
    schedule_next_round,
    update_candidate_approval,
)

logger = logging.getLogger(__name__)


# ── Approve & invite ──────────────────────────────────────────────────────────

def approve_candidate_for_interview(file_id: str, job_title: str, slot_index: int = 0):
    candidate = get_candidate(file_id, job_title)
    if not candidate:
        raise ValueError("Candidate not found")
    if candidate["decision"] != "SHORTLIST":
        raise ValueError("Only shortlisted candidates can be approved")
    if candidate["action_status"] == "EMAIL_SENT":
        return {
            "interview_time": candidate["interview_time"],
            "meet_link": candidate["meet_link"],
            "already_sent": True,
        }
    if not candidate["email"]:
        raise ValueError("Candidate email is missing")

    try:
        interview_time = allocate_interview_time(slot_index)
        interview_time_str = interview_time.strftime("%d %b %Y, %I:%M %p")
        request_id = f"{job_title}-{file_id}".lower().replace(" ", "-")[:100]

        calendar_result = schedule_interview(
            candidate_email=candidate["email"],
            start_time=interview_time,
            request_id=request_id,
        )
        meet_link = calendar_result["meet_link"]

        email_body = generate_email(
            candidate_name=candidate["name"],
            job_role=job_title,
            interview_time=interview_time_str,
            meet_link=meet_link,
        )
        send_email(
            to_email=candidate["email"],
            subject=f"Interview Invitation — {job_title.title()} | {settings.company_name}",
            body=email_body,
        )

        update_candidate_approval(
            file_id=file_id,
            job_title=job_title,
            interview_time=interview_time_str,
            meet_link=meet_link,
            calendar_event_id=calendar_result.get("event_id"),
        )
        logger.info("Approved and emailed candidate file_id=%s job=%s", file_id, job_title)
        return {
            "interview_time": interview_time_str,
            "meet_link": meet_link,
            "already_sent": False,
        }
    except Exception as exc:
        record_candidate_error(file_id, job_title, str(exc))
        raise


# ── Reschedule ────────────────────────────────────────────────────────────────

def reschedule_candidate_interview(file_id: str, job_title: str, slot_index: int):
    """Book a new slot, send a fresh invite, update DB."""
    candidate = get_candidate(file_id, job_title)
    if not candidate:
        raise ValueError("Candidate not found")
    if not candidate["email"]:
        raise ValueError("Candidate email is missing")

    interview_time = allocate_interview_time(slot_index)
    interview_time_str = interview_time.strftime("%d %b %Y, %I:%M %p")
    request_id = f"reschedule-{job_title}-{file_id}".lower().replace(" ", "-")[:100]

    calendar_result = schedule_interview(
        candidate_email=candidate["email"],
        start_time=interview_time,
        request_id=request_id,
    )
    meet_link = calendar_result["meet_link"]

    current_round = candidate.get("interview_round") or 1
    round_type    = candidate.get("round_type") or "Interview"
    email_body = _reschedule_email(candidate["name"], job_title, interview_time_str, meet_link,
                                   round_number=current_round, round_type=round_type)
    send_email(
        to_email=candidate["email"],
        subject=f"Rescheduled: Round {current_round} — {round_type} | {settings.company_name}",
        body=email_body,
    )

    reschedule_candidate(
        file_id=file_id,
        job_title=job_title,
        new_time=interview_time_str,
        new_meet_link=meet_link,
        calendar_event_id=calendar_result.get("event_id"),
    )
    logger.info("Rescheduled interview for file_id=%s new_time=%s", file_id, interview_time_str)
    return {"interview_time": interview_time_str, "meet_link": meet_link}


# ── Next round ────────────────────────────────────────────────────────────────

def advance_to_next_round(
    file_id: str,
    job_title: str,
    slot_index: int,
    round_type: str,
):
    """
    Schedule the next interview round for a candidate who passed the previous one.
    round_type: free-text description e.g. 'Technical Round 2', 'HR Discussion', 'CTO Interview'
    """
    candidate = get_candidate(file_id, job_title)
    if not candidate:
        raise ValueError("Candidate not found")
    if candidate["action_status"] != "INTERVIEWED_PASSED":
        raise ValueError("Next round can only be scheduled for candidates who passed the previous round.")
    if not candidate["email"]:
        raise ValueError("Candidate email is missing")

    prev_round    = candidate.get("interview_round") or 1
    next_round_no = prev_round + 1

    interview_time     = allocate_interview_time(slot_index)
    interview_time_str = interview_time.strftime("%d %b %Y, %I:%M %p")
    request_id         = f"round{next_round_no}-{job_title}-{file_id}".lower().replace(" ", "-")[:100]

    calendar_result = schedule_interview(
        candidate_email=candidate["email"],
        start_time=interview_time,
        request_id=request_id,
    )
    meet_link = calendar_result["meet_link"]

    email_body = _next_round_email(
        name=candidate["name"],
        job_role=job_title,
        round_number=next_round_no,
        round_type=round_type,
        interview_time=interview_time_str,
        meet_link=meet_link,
    )
    send_email(
        to_email=candidate["email"],
        subject=f"Round {next_round_no} Interview Invitation — {round_type} | {settings.company_name}",
        body=email_body,
    )

    schedule_next_round(
        file_id=file_id,
        job_title=job_title,
        new_time=interview_time_str,
        new_meet_link=meet_link,
        round_number=next_round_no,
        round_type=round_type,
        calendar_event_id=calendar_result.get("event_id"),
    )
    logger.info(
        "Next round scheduled: file_id=%s round=%s type=%s time=%s",
        file_id, next_round_no, round_type, interview_time_str,
    )
    return {
        "interview_time": interview_time_str,
        "meet_link": meet_link,
        "round_number": next_round_no,
        "round_type": round_type,
    }


# ── Interview outcome ─────────────────────────────────────────────────────────

def record_interview_result(file_id: str, job_title: str, outcome: str, notes: str = ""):
    """outcome: PASSED | FAILED | NO_SHOW"""
    mark_interview_outcome(file_id, job_title, outcome, notes)
    logger.info("Interview outcome recorded: file_id=%s outcome=%s", file_id, outcome)


# ── Offer letter ──────────────────────────────────────────────────────────────

def send_offer_letter(
    file_id: str,
    job_title: str,
    salary: str = "",
    joining_date: str = "",
    extra_notes: str = "",
):
    """Generate and email an offer letter to a passed candidate."""
    candidate = get_candidate(file_id, job_title)
    if not candidate:
        raise ValueError("Candidate not found")
    if candidate["action_status"] not in ("INTERVIEWED_PASSED",):
        raise ValueError("Offer can only be sent to candidates who passed the interview.")
    if not candidate["email"]:
        raise ValueError("Candidate email is missing")

    offer_details = f"Salary: {salary} | Joining: {joining_date}"
    body = _offer_letter_body(candidate["name"], job_title, salary, joining_date, extra_notes)

    send_email(
        to_email=candidate["email"],
        subject=f"Offer Letter — {job_title.title()} | {settings.company_name}",
        body=body,
    )
    mark_offer_sent(file_id, job_title, offer_details)
    logger.info("Offer letter sent to file_id=%s job=%s", file_id, job_title)
    return {"offer_details": offer_details}


# ── Email templates ───────────────────────────────────────────────────────────

def _reschedule_email(name: str, role: str, time: str, meet_link: str,
                      round_number: int = 1, round_type: str = "Interview") -> str:
    round_label = f"Round {round_number} — {round_type}" if round_number > 1 else role
    return f"""Dear {name},

We hope this message finds you well. We would like to reschedule your {round_label} interview for the {role} position at {settings.company_name}.

Updated interview details:

Round: {round_label}
Mode: {settings.interview_mode}
Duration: {settings.interview_duration_min} minutes
New date and time: {time}
Interview link: {meet_link}

We apologise for any inconvenience caused. Please ensure you are available at the new scheduled time. If you have any concerns, feel free to reply to this email.

Warm regards,
{settings.hr_name}
{settings.hr_title}
{settings.company_name}
{settings.company_website}""".strip()


def _next_round_email(name: str, job_role: str, round_number: int,
                      round_type: str, interview_time: str, meet_link: str) -> str:
    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(round_number, f"{round_number}th")
    return f"""Dear {name},

Congratulations! We are pleased to inform you that you have successfully cleared the previous interview round for the {job_role} position at {settings.company_name}.

We would like to invite you for the {ordinal} round — {round_type}.

Interview details:

Round: {ordinal} — {round_type}
Mode: {settings.interview_mode}
Duration: {settings.interview_duration_min} minutes
Date and time: {interview_time}
Interview link: {meet_link}

Please ensure you are available at the scheduled time. Feel free to reply to this email if you have any questions or require clarification about this round.

Warm regards,
{settings.hr_name}
{settings.hr_title}
{settings.company_name}
{settings.company_website}""".strip()


def _offer_letter_body(name: str, role: str, salary: str, joining_date: str, notes: str) -> str:
    salary_line = f"\nCompensation package: {salary}" if salary else ""
    joining_line = f"\nExpected joining date: {joining_date}" if joining_date else ""
    notes_line = f"\n\n{notes}" if notes else ""
    return f"""Dear {name},

We are delighted to extend this offer of employment to you for the position of {role} at {settings.company_name}.

After a thorough evaluation process, we are confident that your skills and experience make you an excellent fit for our team.
{salary_line}{joining_line}

To accept this offer, please reply to this email confirming your acceptance within 3 business days.{notes_line}

We look forward to welcoming you to the team and are excited about the contributions you will bring.

Warm regards,
{settings.hr_name}
{settings.hr_title}
{settings.company_name}
{settings.company_website}""".strip()
