import streamlit as st
import pandas as pd
import json
import os

from agents.jd_generator_agent import generate_jd
from agents.jd_formatter_agent import format_for_platforms
from storage.db_reader import get_candidates_for_job

JOB_STATE_FILE = "job_state.json"

# job_state.json is created and managed by the Streamlit dashboard (app.py), and it is read by the background worker (run_agent_worker.py) to decide whether hiring should run. 

# =====================================================
# INIT JOB STATE
if not os.path.exists(JOB_STATE_FILE):
    with open(JOB_STATE_FILE, "w") as f:
        json.dump({"active": False, "job_title": None}, f)

# =====================================================
# PAGE CONFIGURATION
st.set_page_config(page_title="AI Hiring Dashboard", layout="wide")
st.title("🤖 Autonomous AI Hiring System")

# =====================================================
# SESSION STATE
if "jd_text" not in st.session_state:
    st.session_state.jd_text = None

# =====================================================
# JOB INPUT SECTION
st.subheader("🧩 Job Setup")

job_title = st.text_input(
    "Role Name",
    placeholder="e.g. Backend Developer"
)

job_requirements = st.text_area(
    "Extra Skills / Requirements",
    placeholder="FastAPI\nPostgreSQL\n3+ years experience\nAWS"
)

# =====================================================
# GENERATE JD (EXPLICIT ACTION)
if st.button("📝 Generate Job Description"):
    if not job_title.strip():
        st.error("Please enter a role name.")
    else:
        st.session_state.jd_text = generate_jd(
            job_title.strip(),
            job_requirements.strip()
        )
        st.success("Job Description generated successfully.")

# =====================================================
# SHOW JD IF GENERATED
if st.session_state.jd_text:
    with st.expander("📄 Generated Job Description"):
        st.text(st.session_state.jd_text)

    col1, col2 = st.columns(2)

    # ---------------- START HIRING ----------------
    with col1:
        if st.button("▶️ Start Hiring"):
            with open("jd.txt", "w", encoding="utf-8") as f:
                f.write(st.session_state.jd_text)

            with open(JOB_STATE_FILE, "w") as f:
                json.dump(
                    {
                        "active": True,
                        "job_title": job_title.lower().strip()
                    },
                    f
                )

            st.success(f"✅ Hiring STARTED for {job_title}")
            st.rerun()

    # ---------------- STOP HIRING ----------------
    with col2:
        if st.button("⏹ Stop Hiring"):
            with open(JOB_STATE_FILE, "w") as f:
                json.dump(
                    {"active": False, "job_title": None},
                    f
                )

            st.warning("⛔ Hiring STOPPED")
            st.rerun()

# =====================================================
# STATUS SECTION
st.divider()

with open(JOB_STATE_FILE, "r") as f:
    job_state = json.load(f)

if job_state["active"]:
    st.success(f"🟢 Hiring ACTIVE for {job_state['job_title']}")
else:
    st.info("🔴 Hiring INACTIVE")

# =====================================================
# CANDIDATES SECTION
st.subheader("📊 Processed Candidates")

if "candidates_df" not in st.session_state:
    st.session_state["candidates_df"] = pd.DataFrame()

if st.button("🔄 Show / Refresh Candidates"):
    if job_state["active"] and job_state["job_title"]:
        st.session_state["candidates_df"] = get_candidates_for_job(
            job_state["job_title"]
        )
    else:
        st.warning("No active job. Start hiring to view candidates.")


df = st.session_state["candidates_df"]

if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("No candidates processed yet.")
