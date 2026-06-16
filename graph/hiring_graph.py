import logging

from services.batch_processor import process_batch
from storage.processed_resumes import mark_processed

logger = logging.getLogger(__name__)


def hiring_agent(state: dict):
    jd_text = state.get("jd_text")
    resumes = state.get("resumes")
    job_title = state.get("job_title")
    threshold = state.get("score_threshold")

    if not jd_text:
        raise ValueError("JD text missing")
    if not resumes:
        raise ValueError("Resumes missing")
    if not job_title:
        raise ValueError("Job title missing")

    results = process_batch(jd_text, resumes, threshold=threshold)

    for result in results:
        candidate = result["candidate"]
        decision = result["decision"].upper()

        logger.info(
            "Screened candidate email=%s decision=%s score=%s",
            candidate.get("email"),
            decision,
            result["score"],
        )

        mark_processed(
            file_id=result["file_id"],
            job_title=job_title,
            filename=result.get("filename"),
            name=candidate.get("name", "Unknown"),
            email=candidate.get("email", ""),
            score=result["score"],
            decision=decision,
            breakdown=result.get("breakdown"),
        )

    return {
        "job_title": job_title,
        "jd_text": jd_text,
        "results": results,
    }
