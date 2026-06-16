import pandas as pd
import streamlit as st

from agents.jd_generator_agent import generate_jd
from config.settings import settings
from services.candidate_actions import approve_candidate_for_interview
from storage.db_reader import get_candidates_for_job
from storage.processed_resumes import (
    create_job,
    get_active_job,
    init_db,
    list_jobs,
    reject_candidate,
    stop_active_job,
)

init_db()

st.set_page_config(page_title="AI Hiring Dashboard", layout="wide")
st.title("Autonomous AI Hiring System")

if "jd_text" not in st.session_state:
    st.session_state.jd_text = None

active_job = get_active_job()

with st.sidebar:
    st.header("System")
    if active_job:
        st.success(f"Active: {active_job['title']}")
        st.caption(f"Threshold: {active_job['score_threshold']}")
        if st.button("Stop active job", type="secondary"):
            stop_active_job()
            st.rerun()
    else:
        st.info("No active job")

    st.divider()
    st.subheader("Recent jobs")
    for job in list_jobs(limit=8):
        st.caption(f"{job['title']} - {job['status']}")

tab_setup, tab_candidates = st.tabs(["Job setup", "Candidate review"])

with tab_setup:
    st.subheader("Create hiring job")

    job_title = st.text_input("Role name", placeholder="Backend Developer")
    job_requirements = st.text_area(
        "Extra skills / requirements",
        placeholder="FastAPI\nPostgreSQL\n3+ years experience\nAWS",
    )
    score_threshold = st.slider(
        "Shortlist threshold",
        min_value=40,
        max_value=95,
        value=int(settings.default_score_threshold),
        step=5,
    )

    if st.button("Generate job description"):
        if not job_title.strip():
            st.error("Please enter a role name.")
        else:
            st.session_state.jd_text = generate_jd(
                job_title.strip(),
                job_requirements.strip(),
            )
            st.success("Job description generated.")

    if st.session_state.jd_text:
        st.text_area(
            "Generated job description",
            value=st.session_state.jd_text,
            height=320,
        )

        if st.button("Start hiring job", type="primary"):
            create_job(
                title=job_title,
                requirements=job_requirements,
                jd_text=st.session_state.jd_text,
                score_threshold=score_threshold,
            )
            st.success(f"Hiring started for {job_title}.")
            st.rerun()

with tab_candidates:
    st.subheader("Candidate review")

    active_job = get_active_job()
    if not active_job:
        st.info("Start a hiring job to review candidates.")
        st.stop()

    st.caption(
        f"Reviewing candidates for {active_job['title']} "
        f"with threshold {active_job['score_threshold']}"
    )

    if st.button("Refresh candidates"):
        st.rerun()

    df = get_candidates_for_job(active_job["normalized_title"])

    if df.empty:
        st.info("No candidates processed yet. Keep the worker running.")
        st.stop()

    display_cols = [
        "name",
        "email",
        "score",
        "decision",
        "action_status",
        "interview_time",
        "meet_link",
        "processed_at",
    ]
    st.dataframe(df[display_cols], use_container_width=True)

    pending = df[
        (df["decision"] == "SHORTLIST")
        & (df["action_status"].isin(["PENDING_REVIEW", "ERROR"]))
    ]

    if pending.empty:
        st.success("No shortlisted candidates are waiting for approval.")
    else:
        st.subheader("Pending approvals")
        for index, row in pending.reset_index(drop=True).iterrows():
            with st.container(border=True):
                left, middle, right = st.columns([3, 2, 2])
                left.markdown(f"**{row['name']}**")
                left.caption(row["email"] or "No email found")
                middle.metric("Score", row["score"])
                middle.caption(f"Status: {row['action_status']}")
                if row.get("error_message"):
                    st.error(row["error_message"])

                slot_index = right.number_input(
                    "Slot index",
                    min_value=0,
                    max_value=8,
                    value=index,
                    step=1,
                    key=f"slot-{row['file_id']}",
                )

                approve_col, reject_col = right.columns(2)
                if approve_col.button("Approve", key=f"approve-{row['file_id']}"):
                    try:
                        result = approve_candidate_for_interview(
                            row["file_id"],
                            active_job["normalized_title"],
                            slot_index=int(slot_index),
                        )
                        st.success(
                            "Interview email sent"
                            if not result["already_sent"]
                            else "Already emailed earlier"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Approval failed: {exc}")

                if reject_col.button("Reject", key=f"reject-{row['file_id']}"):
                    reject_candidate(row["file_id"], active_job["normalized_title"])
                    st.warning("Candidate rejected.")
                    st.rerun()
