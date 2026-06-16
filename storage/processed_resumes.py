import sqlite3
import os

"""This file handles all database operations for processed resumes.
It keeps track of which resumes have already been processed for each job to avoid duplicates.
It also stores candidate details, screening results, and interview information.
The design ensures idempotency, safe updates, and clean persistence for the hiring pipeline."""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "storage", "processed_resumes.db")


# -------------------------------------------------
# DB INIT
# -------------------------------------------------
def is_already_processed(file_id: str, job_title: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor() # Cursor executes SQL queries

    cursor.execute(
        """
        SELECT 1 FROM processed
        WHERE file_id = ? AND job_title = ?
        """,
        (file_id, job_title)
    )

    exists = cursor.fetchone() is not None
    conn.close()
    return exists
# Checks if the resume exists in the database for the given job title.Decision can be anything: REJECT, HOLD, SHORTLIST. Used before running screening logic.


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS processed (
            file_id TEXT,
            job_title TEXT,
            name TEXT,
            email TEXT,
            score REAL,
            decision TEXT,
            interview_time TEXT,
            meet_link TEXT,
            processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (file_id, job_title)
        )
    """)

    conn.commit()
    conn.close() # Close the connection after committing changes


# CHECK IF ALREADY SHORTLISTED (IDEMPOTENCY)
def was_shortlisted(file_id: str, job_title: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 1 FROM processed
        WHERE file_id = ? AND job_title = ? AND decision = 'SHORTLIST'
        """,
        (file_id, job_title)
    )

    exists = cursor.fetchone() is not None
    conn.close()
    return exists
#Checks if the decision was SHORTLISTED for the given resume and job title.Used after screening. Prevents duplicate interview actions


# PERSIST RESULT (SAFE, JOB-SCOPED)
def mark_processed(
    *,
    file_id: str,
    job_title: str,
    name: str,
    email: str,
    score: float,
    decision: str,
    interview_time: str = None,
    meet_link: str = None
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO processed(
            file_id,
            job_title,
            name,
            email,
            score,
            decision,
            interview_time,
            meet_link
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_id,
            job_title,
            name,
            email,
            score,
            decision,
            interview_time,
            meet_link
        )
    )

    conn.commit()
    conn.close()
    
    # It remembers what has already been processed so the system doesn’t repeat work or make mistakes
