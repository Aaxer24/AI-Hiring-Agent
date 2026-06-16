import sqlite3
import pandas as pd
import os

"""This function fetches all candidates processed for a given job role from the database. It runs a filtered SQL query, converts the results into a Pandas DataFrame, and returns them in a clean, structured format for display or analysis.”"""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "storage", "processed_resumes.db")


def get_candidates_for_job(job_title: str):
    conn = sqlite3.connect(DB_PATH)

    query = """
        SELECT
            name,
            email,
            score,
            decision,
            interview_time,
            meet_link,
            processed_at
        FROM processed
        WHERE job_title = ?
        ORDER BY processed_at DESC
    """

    df = pd.read_sql_query(query, conn, params=(job_title,))
    conn.close()

    return df
