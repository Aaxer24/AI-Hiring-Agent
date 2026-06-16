import json
import os
import sqlite3
from datetime import datetime
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "storage", "processed_resumes.db")


def normalize_job_title(job_title: str) -> str:
    return job_title.lower().strip()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def _ensure_column(cursor: sqlite3.Cursor, table: str, column: str, ddl: str) -> None:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            normalized_title TEXT NOT NULL,
            requirements TEXT,
            jd_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            score_threshold REAL NOT NULL DEFAULT 70,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
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
        """
    )

    migrations = {
        "filename": "TEXT",
        "breakdown_json": "TEXT",
        "action_status": "TEXT DEFAULT 'PENDING_REVIEW'",
        "calendar_event_id": "TEXT",
        "email_sent_at": "TEXT",
        "approved_at": "TEXT",
        "error_message": "TEXT",
        # Post-interview fields
        "interview_outcome": "TEXT",
        "interview_notes": "TEXT",
        "offer_sent_at": "TEXT",
        "offer_details": "TEXT",
        # Multi-round tracking
        "interview_round": "INTEGER DEFAULT 1",
        "round_type": "TEXT DEFAULT 'Initial Interview'",
    }
    for column, ddl in migrations.items():
        _ensure_column(cursor, "processed", column, ddl)

    conn.commit()
    conn.close()


def create_job(
    *,
    title: str,
    requirements: str,
    jd_text: str,
    score_threshold: float,
) -> int:
    init_db()
    normalized_title = normalize_job_title(title)
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP")
    cursor.execute(
        """
        INSERT INTO jobs(title, normalized_title, requirements, jd_text, status, score_threshold)
        VALUES (?, ?, ?, ?, 'ACTIVE', ?)
        """,
        (title.strip(), normalized_title, requirements.strip(), jd_text, score_threshold),
    )
    job_id = int(cursor.lastrowid)
    conn.commit()
    conn.close()
    return job_id


def stop_active_job() -> None:
    init_db()
    conn = _connect()
    conn.execute("UPDATE jobs SET status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP WHERE status = 'ACTIVE'")
    conn.commit()
    conn.close()


def get_active_job() -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    row = conn.execute(
        """
        SELECT *
        FROM jobs
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    init_db()
    conn = _connect()
    rows = conn.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def is_already_processed(file_id: str, job_title: str) -> bool:
    init_db()
    conn = _connect()
    row = conn.execute(
        """
        SELECT 1 FROM processed
        WHERE file_id = ? AND job_title = ?
        """,
        (file_id, normalize_job_title(job_title)),
    ).fetchone()
    conn.close()
    return row is not None


def was_shortlisted(file_id: str, job_title: str) -> bool:
    init_db()
    conn = _connect()
    row = conn.execute(
        """
        SELECT 1 FROM processed
        WHERE file_id = ?
          AND job_title = ?
          AND decision = 'SHORTLIST'
          AND action_status IN ('APPROVED', 'SCHEDULED', 'EMAIL_SENT')
        """,
        (file_id, normalize_job_title(job_title)),
    ).fetchone()
    conn.close()
    return row is not None


def mark_processed(
    *,
    file_id: str,
    job_title: str,
    name: str,
    email: str,
    score: float,
    decision: str,
    filename: str | None = None,
    breakdown: dict[str, Any] | None = None,
    interview_time: str | None = None,
    meet_link: str | None = None,
) -> None:
    init_db()
    normalized_title = normalize_job_title(job_title)
    decision = decision.upper()
    action_status = "PENDING_REVIEW" if decision == "SHORTLIST" else "REJECTED"
    conn = _connect()
    conn.execute(
        """
        INSERT OR REPLACE INTO processed(
            file_id,
            job_title,
            filename,
            name,
            email,
            score,
            decision,
            interview_time,
            meet_link,
            breakdown_json,
            action_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            file_id,
            normalized_title,
            filename,
            name,
            email,
            score,
            decision,
            interview_time,
            meet_link,
            json.dumps(breakdown or {}),
            action_status,
        ),
    )
    conn.commit()
    conn.close()


def get_candidate(file_id: str, job_title: str) -> dict[str, Any] | None:
    init_db()
    conn = _connect()
    row = conn.execute(
        """
        SELECT *
        FROM processed
        WHERE file_id = ? AND job_title = ?
        """,
        (file_id, normalize_job_title(job_title)),
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def update_candidate_approval(
    *,
    file_id: str,
    job_title: str,
    interview_time: str,
    meet_link: str,
    calendar_event_id: str | None,
) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status = 'EMAIL_SENT',
            interview_time = ?,
            meet_link = ?,
            calendar_event_id = ?,
            email_sent_at = ?,
            approved_at = COALESCE(approved_at, ?),
            error_message = NULL
        WHERE file_id = ? AND job_title = ?
        """,
        (
            interview_time,
            meet_link,
            calendar_event_id,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            file_id,
            normalize_job_title(job_title),
        ),
    )
    conn.commit()
    conn.close()


def reject_candidate(file_id: str, job_title: str) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status = 'REJECTED',
            approved_at = NULL,
            error_message = NULL
        WHERE file_id = ? AND job_title = ?
        """,
        (file_id, normalize_job_title(job_title)),
    )
    conn.commit()
    conn.close()


def record_candidate_error(file_id: str, job_title: str, error_message: str) -> None:
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status = 'ERROR',
            error_message = ?
        WHERE file_id = ? AND job_title = ?
        """,
        (error_message, file_id, normalize_job_title(job_title)),
    )
    conn.commit()
    conn.close()


def mark_interview_outcome(
    file_id: str,
    job_title: str,
    outcome: str,          # PASSED | FAILED | NO_SHOW
    notes: str = "",
) -> None:
    """Record the result of the interview."""
    valid = {"PASSED", "FAILED", "NO_SHOW"}
    if outcome not in valid:
        raise ValueError(f"outcome must be one of {valid}")
    action_map = {"PASSED": "INTERVIEWED_PASSED", "FAILED": "INTERVIEWED_FAILED", "NO_SHOW": "NO_SHOW"}
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET interview_outcome = ?,
            interview_notes   = ?,
            action_status     = ?
        WHERE file_id = ? AND job_title = ?
        """,
        (outcome, notes, action_map[outcome], file_id, normalize_job_title(job_title)),
    )
    conn.commit()
    conn.close()


def mark_offer_sent(
    file_id: str,
    job_title: str,
    offer_details: str = "",
) -> None:
    """Record that an offer letter was sent."""
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status  = 'OFFER_SENT',
            offer_sent_at  = ?,
            offer_details  = ?
        WHERE file_id = ? AND job_title = ?
        """,
        (datetime.utcnow().isoformat(), offer_details, file_id, normalize_job_title(job_title)),
    )
    conn.commit()
    conn.close()


def reschedule_candidate(
    file_id: str,
    job_title: str,
    new_time: str,
    new_meet_link: str,
    calendar_event_id: str | None = None,
) -> None:
    """Reset candidate to EMAIL_SENT with a new interview slot."""
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status     = 'EMAIL_SENT',
            interview_time    = ?,
            meet_link         = ?,
            calendar_event_id = COALESCE(?, calendar_event_id),
            interview_outcome = NULL,
            interview_notes   = NULL,
            email_sent_at     = ?
        WHERE file_id = ? AND job_title = ?
        """,
        (new_time, new_meet_link, calendar_event_id,
         datetime.utcnow().isoformat(), file_id, normalize_job_title(job_title)),
    )
    conn.commit()
    conn.close()


def schedule_next_round(
    file_id: str,
    job_title: str,
    new_time: str,
    new_meet_link: str,
    round_number: int,
    round_type: str,
    calendar_event_id: str | None = None,
) -> None:
    """Advance candidate to the next interview round."""
    init_db()
    conn = _connect()
    conn.execute(
        """
        UPDATE processed
        SET action_status     = 'EMAIL_SENT',
            interview_time    = ?,
            meet_link         = ?,
            calendar_event_id = COALESCE(?, calendar_event_id),
            interview_outcome = NULL,
            interview_notes   = NULL,
            email_sent_at     = ?,
            interview_round   = ?,
            round_type        = ?
        WHERE file_id = ? AND job_title = ?
        """,
        (
            new_time, new_meet_link, calendar_event_id,
            datetime.utcnow().isoformat(),
            round_number, round_type,
            file_id, normalize_job_title(job_title),
        ),
    )
    conn.commit()
    conn.close()


def reset_job_candidates(job_title: str) -> int:
    """Delete all processed rows for a job so the worker re-screens every file."""
    init_db()
    conn = _connect()
    cursor = conn.execute(
        "DELETE FROM processed WHERE job_title = ?",
        (normalize_job_title(job_title),),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def get_job_stats(job_title: str) -> dict:
    """Return quick summary counts for dashboard metrics."""
    init_db()
    conn = _connect()
    normalized = normalize_job_title(job_title)
    row = conn.execute(
        """
        SELECT
            COUNT(*)                                             AS total,
            SUM(CASE WHEN decision='SHORTLIST' THEN 1 ELSE 0 END) AS shortlisted,
            SUM(CASE WHEN decision='REJECT'    THEN 1 ELSE 0 END) AS rejected,
            SUM(CASE WHEN action_status='EMAIL_SENT' THEN 1 ELSE 0 END) AS invited,
            SUM(CASE WHEN action_status='PENDING_REVIEW' AND decision='SHORTLIST' THEN 1 ELSE 0 END) AS awaiting
        FROM processed
        WHERE job_title = ?
        """,
        (normalized,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"total": 0, "shortlisted": 0, "rejected": 0, "invited": 0, "awaiting": 0}
