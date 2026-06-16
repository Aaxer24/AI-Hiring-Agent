import os
import sqlite3

import pandas as pd

from storage.processed_resumes import init_db, normalize_job_title

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "storage", "processed_resumes.db")


def get_candidates_for_job(job_title: str) -> pd.DataFrame:
    init_db()
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            file_id,
            filename,
            name,
            email,
            score,
            decision,
            action_status,
            interview_time,
            meet_link,
            processed_at,
            error_message
        FROM processed
        WHERE job_title = ?
        ORDER BY
            CASE action_status
                WHEN 'PENDING_REVIEW' THEN 0
                WHEN 'ERROR' THEN 1
                WHEN 'EMAIL_SENT' THEN 2
                ELSE 3
            END,
            score DESC,
            processed_at DESC
    """

    df = pd.read_sql_query(query, conn, params=(normalize_job_title(job_title),))
    conn.close()
    return df
