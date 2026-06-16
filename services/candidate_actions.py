import logging

from agents.calendar_agent import schedule_interview
from agents.email_agent import generate_email, send_email
from services.interview_scheduler import allocate_interview_time
from storage.processed_resumes import (
    get_candidate,
    record_candidate_error,
    update_candidate_approval,
)

logger = logging.getLogger(__name__)


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
            subject=f"Interview Invitation - {job_title}",
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
