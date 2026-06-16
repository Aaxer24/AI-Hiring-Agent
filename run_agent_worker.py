import logging
import time

from agents.resume_intake_agent import fetch_new_resumes
from config.logging_config import configure_logging
from config.settings import settings
from graph.hiring_graph import hiring_agent
from storage.processed_resumes import get_active_job, init_db

configure_logging()
logger = logging.getLogger(__name__)


def main():
    init_db()
    logger.info("AI Hiring Agent worker started")

    if not settings.google_drive_folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID is not set. Worker will wait.")

    while True:
        try:
            active_job = get_active_job()
            if not active_job:
                logger.info("No active job. Waiting.")
                time.sleep(30)
                continue

            if not settings.google_drive_folder_id:
                time.sleep(60)
                continue

            job_title = active_job["normalized_title"]
            jd_text = active_job["jd_text"]
            threshold = active_job["score_threshold"]

            resumes = fetch_new_resumes(settings.google_drive_folder_id, job_title)

            if not resumes:
                logger.info("No new resumes found for job=%s", job_title)
                time.sleep(settings.check_interval_seconds)
                continue

            hiring_agent(
                {
                    "job_title": job_title,
                    "jd_text": jd_text,
                    "resumes": resumes,
                    "score_threshold": threshold,
                }
            )
            logger.info("Processed %s resumes for job=%s", len(resumes), job_title)
            time.sleep(settings.check_interval_seconds)

        except Exception:
            logger.exception("Error in background worker")
            time.sleep(60)


if __name__ == "__main__":
    main()
