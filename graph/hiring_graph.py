from services.batch_processor import process_batch
from agents.email_agent import send_email, generate_email
from agents.calendar_agent import schedule_interview
from services.interview_scheduler import allocate_interview_time
from storage.processed_resumes import mark_processed, was_shortlisted

"""This function automates the entire hiring workflow. It screens resumes against a job description, shortlists suitable candidates, schedules interviews, sends emails, and safely stores results. It is designed to avoid duplicate actions and run reliably in production."""

def hiring_agent(state: dict):
    #This function takes a state object, which contains: Job description,Resumes,Job title
    jd_text = state.get("jd_text")
    resumes = state.get("resumes")
    job_title = state.get("job_title") 

    # -------------------------------------------------
    # Safety checks
    if not jd_text:
        raise ValueError("JD text missing")
    if not resumes:
        raise ValueError("Resumes missing")
    if not job_title:
        raise ValueError("Job title missing")

    # -------------------------------------------------
    # Step 1: Screen candidates
    results = process_batch(jd_text, resumes)

    shortlist_index = 0  # ensures unique interview slots

    # -------------------------------------------------
    # Step 2: Take action on candidates (IDEMPOTENT)
    for r, resume in zip(results, resumes):
        candidate = r["candidate"]
        decision = r["decision"].upper()

        print("EMAIL CHECK →", candidate["email"], decision)

        interview_time_str = None
        meet_link = None

        if decision == "SHORTLIST":
            # Prevent duplicate side-effects
            if was_shortlisted(resume["file_id"], job_title):
                print(
                    "Already shortlisted earlier, skipping email & calendar →",
                    candidate["email"]
                )
            else:
                # -----------------------------------------
                # Step 3: Allocate unique interview time
                interview_time = allocate_interview_time(shortlist_index)
                shortlist_index += 1

                interview_time_str = interview_time.strftime(
                    "%d %b %Y, %I:%M %p"
                )

                # -----------------------------------------
                # Step 4: Schedule interview (Calendar)
                meet_link = schedule_interview(
                    candidate_email=candidate["email"],
                    start_time=interview_time
                )

                # -----------------------------------------
                # Step 5: Generate deterministic email
                email_body = generate_email(
                    candidate_name=candidate["name"],
                    job_role=job_title,
                    interview_time=interview_time_str,
                    meet_link=meet_link
                )

                # -----------------------------------------
                # Step 6: Send email
                send_email(
                    to_email=candidate["email"],
                    subject=f"Interview Invitation – {job_title}",
                    body=email_body
                )

                # Attach info for UI
                r["interview_time"] = interview_time_str
                r["meet_link"] = meet_link

        # -------------------------------------------------
        # Step 7: Persist result (ALWAYS SAFE)
        
        # Resume results are stored in the database by the hiring_graph orchestration layer using the mark_processed function.
        mark_processed(
            file_id=resume["file_id"],
            job_title=job_title,    
            name=candidate["name"],
            email=candidate["email"],
            score=r["score"],
            decision=decision,
            interview_time=interview_time_str,
            meet_link=meet_link
        )

    return {
        "job_title": job_title,
        "jd_text": jd_text,
        "results": results
    }
