import logging

from agents.resume_agent import parse_resume
from agents.screening_agent import screen_candidate

logger = logging.getLogger(__name__)


def process_batch(jd_text, resume_files, threshold=None):
    if not jd_text:
        raise ValueError("JD text missing")
    if not resume_files:
        raise ValueError("No resumes received in batch processor")

    results = []

    for resume in resume_files:
        parsed = parse_resume(resume)

        if "raw_text" not in parsed or "structured" not in parsed:
            logger.warning("Skipping broken resume: %s", resume.get("filename"))
            continue

        screening = screen_candidate(jd_text, parsed["raw_text"], threshold=threshold)

        results.append(
            {
                "file_id": resume["file_id"],
                "filename": resume.get("filename"),
                "candidate": parsed["structured"],
                "score": screening["score"],
                "decision": screening["decision"],
                "breakdown": screening["breakdown"],
            }
        )

    return sorted(results, key=lambda x: x["score"], reverse=True)
