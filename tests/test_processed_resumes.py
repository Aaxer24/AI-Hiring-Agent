import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from storage import processed_resumes as store


class ProcessedResumesTests(unittest.TestCase):
    def test_job_lifecycle_and_candidate_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "hiring.db")
            with patch.object(store, "DB_PATH", db_path):
                job_id = store.create_job(
                    title="Backend Developer",
                    requirements="FastAPI",
                    jd_text="Need FastAPI developer",
                    score_threshold=75,
                )

                active = store.get_active_job()
                self.assertEqual(active["id"], job_id)
                self.assertEqual(active["normalized_title"], "backend developer")
                self.assertEqual(active["score_threshold"], 75)

                store.mark_processed(
                    file_id="file-1",
                    job_title="Backend Developer",
                    filename="resume.pdf",
                    name="Asha",
                    email="asha@example.com",
                    score=82,
                    decision="SHORTLIST",
                    breakdown={"semantic_fit": 90},
                )

                candidate = store.get_candidate("file-1", "backend developer")
                self.assertEqual(candidate["action_status"], "PENDING_REVIEW")
                self.assertEqual(candidate["decision"], "SHORTLIST")

                store.update_candidate_approval(
                    file_id="file-1",
                    job_title="backend developer",
                    interview_time="18 Jun 2026, 10:00 AM",
                    meet_link="https://meet.google.com/test",
                    calendar_event_id="event-1",
                )

                candidate = store.get_candidate("file-1", "backend developer")
                self.assertEqual(candidate["action_status"], "EMAIL_SENT")
                self.assertEqual(candidate["meet_link"], "https://meet.google.com/test")

                store.stop_active_job()
                self.assertIsNone(store.get_active_job())


if __name__ == "__main__":
    unittest.main()
