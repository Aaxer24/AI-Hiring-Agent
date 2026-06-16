import time

import pandas as pd
import streamlit as st

from agents.jd_generator_agent import generate_jd
from config.settings import settings
from services.candidate_actions import (
    approve_candidate_for_interview,
    record_interview_result,
    reschedule_candidate_interview,
    send_offer_letter,
)
from storage.db_reader import get_candidates_for_job
from storage.processed_resumes import (
    create_job,
    get_active_job,
    get_job_stats,
    init_db,
    list_jobs,
    mark_interview_outcome,
    reject_candidate,
    reset_job_candidates,
    stop_active_job,
)

# ── Bootstrap ──────────────────────────────────────────────────────────────────
init_db()

st.set_page_config(
    page_title="HirePilot AI — Hiring Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* ── Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Background ── */
.stApp { background: #0d1117; color: #e6edf3; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}

/* ── Cards ── */
.hp-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.hp-card-accent {
    background: linear-gradient(135deg, #1a2332 0%, #161b22 100%);
    border: 1px solid #388bfd44;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}

/* ── Status pill ── */
.status-active {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1a4731; color: #3fb950;
    border: 1px solid #2ea043; border-radius: 20px;
    padding: 6px 14px; font-size: 13px; font-weight: 600;
    animation: pulse-green 2s infinite;
}
.status-idle {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1c1c2e; color: #8b949e;
    border: 1px solid #30363d; border-radius: 20px;
    padding: 6px 14px; font-size: 13px; font-weight: 600;
}
@keyframes pulse-green {
    0%,100% { box-shadow: 0 0 0 0 #2ea04340; }
    50%      { box-shadow: 0 0 0 6px #2ea04300; }
}
.dot-green { width: 8px; height: 8px; background: #3fb950; border-radius: 50%;
             animation: blink 1.4s ease-in-out infinite; }
.dot-grey  { width: 8px; height: 8px; background: #8b949e; border-radius: 50%; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Metric tiles ── */
.metric-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.metric-tile {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 20px; text-align: center;
}
.metric-tile .val { font-size: 36px; font-weight: 700; margin: 0; line-height: 1; }
.metric-tile .lbl { font-size: 12px; color: #8b949e; margin-top: 6px; text-transform: uppercase; letter-spacing: .05em; }
.val-blue   { color: #388bfd; }
.val-green  { color: #3fb950; }
.val-red    { color: #f85149; }
.val-yellow { color: #d29922; }

/* ── Candidate card ── */
.cand-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 12px;
    padding: 18px 22px; margin-bottom: 12px; transition: border-color .2s;
}
.cand-card:hover { border-color: #388bfd55; }
.score-badge {
    display: inline-block; border-radius: 8px; padding: 4px 10px;
    font-weight: 700; font-size: 15px;
}
.score-high  { background: #1a4731; color: #3fb950; }
.score-mid   { background: #2d2208; color: #d29922; }
.score-low   { background: #2d1217; color: #f85149; }

/* ── Buttons ── */
div[data-testid="stButton"] > button {
    border-radius: 8px; font-weight: 600; transition: all .15s;
}
div[data-testid="stButton"] > button:hover { transform: translateY(-1px); }

/* ── Section headers ── */
.section-title {
    font-size: 18px; font-weight: 700; color: #e6edf3;
    border-bottom: 1px solid #30363d; padding-bottom: 10px; margin-bottom: 18px;
}

/* ── Tab overrides ── */
[data-testid="stTabs"] [role="tab"] {
    color: #8b949e; font-weight: 500; border-radius: 8px 8px 0 0;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #e6edf3; border-bottom: 2px solid #388bfd;
}

/* ── Input fields ── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #0d1117 !important; color: #e6edf3 !important;
    border: 1px solid #30363d !important; border-radius: 8px !important;
}
[data-testid="stSlider"] { color: #388bfd; }

/* ── Divider ── */
hr { border-color: #30363d !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
if "jd_text" not in st.session_state:
    st.session_state.jd_text = None
if "confirm_reset" not in st.session_state:
    st.session_state.confirm_reset = False
if "confirm_stop" not in st.session_state:
    st.session_state.confirm_stop = False

# ── Data fetch ────────────────────────────────────────────────────────────────
active_job = get_active_job()
stats = get_job_stats(active_job["normalized_title"]) if active_job else {}

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚀 HirePilot AI")
    st.markdown("---")

    # Live status pill
    if active_job:
        st.markdown(
            f"""<div class="status-active">
                <span class="dot-green"></span> Hiring Active
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown(f"**{active_job['title']}**")
        st.caption(f"Threshold · {active_job['score_threshold']} pts")
        st.caption(f"Started · {active_job['created_at'][:16]}")
        st.markdown("")

        # Stop job
        if not st.session_state.confirm_stop:
            if st.button("⏹ Stop Hiring", use_container_width=True):
                st.session_state.confirm_stop = True
                st.rerun()
        else:
            st.warning("Stop this hiring session?")
            col1, col2 = st.columns(2)
            if col1.button("Yes, stop", type="primary"):
                stop_active_job()
                st.session_state.confirm_stop = False
                st.session_state.jd_text = None
                st.rerun()
            if col2.button("Cancel"):
                st.session_state.confirm_stop = False
                st.rerun()

        st.markdown("---")

        # Fresh start (reset candidates)
        st.markdown("**🔄 Fresh Start**")
        st.caption("Re-screen all Drive files from scratch.")
        if not st.session_state.confirm_reset:
            if st.button("Reset & Rescan", use_container_width=True):
                st.session_state.confirm_reset = True
                st.rerun()
        else:
            st.warning("Delete all candidate results and rescan?")
            col1, col2 = st.columns(2)
            if col1.button("Yes, reset", type="primary"):
                n = reset_job_candidates(active_job["normalized_title"])
                st.session_state.confirm_reset = False
                st.success(f"Cleared {n} record(s). Worker will rescan shortly.")
                time.sleep(1.2)
                st.rerun()
            if col2.button("Cancel"):
                st.session_state.confirm_reset = False
                st.rerun()

    else:
        st.markdown(
            """<div class="status-idle">
                <span class="dot-grey"></span> Idle
            </div>""",
            unsafe_allow_html=True,
        )
        st.caption("No active hiring session.")

    st.markdown("---")
    st.markdown("**Recent Jobs**")
    for job in list_jobs(limit=6):
        colour = "🟢" if job["status"] == "ACTIVE" else "⚫"
        st.caption(f"{colour} {job['title']} — {job['status']}")

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 🤖 HirePilot AI — Hiring Dashboard")

if active_job:
    st.markdown(
        f"""<div class="hp-card-accent">
            <div class="status-active" style="margin-bottom:10px">
                <span class="dot-green"></span> Hiring Active — {active_job['title']}
            </div>
            <p style="color:#8b949e;margin:0;font-size:13px">
                Worker is scanning Google Drive every 3 minutes · Shortlist threshold: {active_job['score_threshold']} pts
            </p>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Metric tiles ──────────────────────────────────────────────────────────
    interviewed = stats.get('shortlisted', 0)
    passed_n = 0
    st.markdown(
        f"""<div class="metric-grid">
            <div class="metric-tile">
                <p class="val val-blue">{stats.get('total', 0)}</p>
                <p class="lbl">📄 Resumes Scanned</p>
            </div>
            <div class="metric-tile">
                <p class="val val-green">{stats.get('shortlisted', 0)}</p>
                <p class="lbl">✅ Shortlisted</p>
            </div>
            <div class="metric-tile">
                <p class="val val-yellow">{stats.get('awaiting', 0)}</p>
                <p class="lbl">⏳ Awaiting Approval</p>
            </div>
            <div class="metric-tile">
                <p class="val val-green">{stats.get('invited', 0)}</p>
                <p class="lbl">📧 Invited to Interview</p>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
tab_launch, tab_review = st.tabs(["🚀  Launch Hiring", "👥  Candidate Review"])

# ─────────────────────────── TAB 1: LAUNCH ───────────────────────────────────
with tab_launch:

    if active_job:
        st.markdown(
            f"""<div class="hp-card">
                <h3 style="margin:0 0 8px 0;color:#3fb950">✅ Hiring is Running</h3>
                <p style="margin:0;color:#8b949e">
                    A session is already active for <strong style="color:#e6edf3">{active_job['title']}</strong>.
                    Stop it from the sidebar before creating a new one.
                </p>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="section-title">🎯 Set Up a New Hiring Session</div>', unsafe_allow_html=True)

        col_form, col_tip = st.columns([3, 1])

        with col_form:
            job_title = st.text_input(
                "Role Name",
                placeholder="e.g. Data Scientist, Backend Developer",
                key="job_title_input",
            )
            job_requirements = st.text_area(
                "Key Requirements (one per line)",
                placeholder="Python\nMachine Learning\n2+ years experience\nSQL",
                height=140,
                key="job_req_input",
            )
            score_threshold = st.slider(
                "Shortlist Score Threshold",
                min_value=40,
                max_value=95,
                value=int(settings.default_score_threshold),
                step=5,
                help="Candidates scoring below this are rejected automatically.",
            )

        with col_tip:
            st.markdown(
                """<div class="hp-card" style="margin-top:28px">
                    <p style="font-size:13px;color:#8b949e;margin:0">
                    💡 <strong style="color:#e6edf3">How it works</strong><br><br>
                    1. Enter role + skills<br>
                    2. Generate JD with AI<br>
                    3. Click <em>Start Hiring</em><br>
                    4. Worker scans Drive<br>
                    5. Review &amp; approve
                    </p>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("")
        gen_col, _ = st.columns([2, 3])
        if gen_col.button("✨ Generate Job Description", use_container_width=True):
            if not job_title.strip():
                st.error("Please enter a role name first.")
            else:
                with st.spinner("AI is writing the job description…"):
                    st.session_state.jd_text = generate_jd(
                        job_title.strip(), job_requirements.strip()
                    )
                st.success("Job description ready! Review it below.")

        if st.session_state.jd_text:
            st.markdown('<div class="section-title" style="margin-top:24px">📄 Generated Job Description</div>', unsafe_allow_html=True)
            jd_editable = st.text_area(
                "Edit if needed:",
                value=st.session_state.jd_text,
                height=320,
                key="jd_editor",
            )

            st.markdown("")
            start_col, _ = st.columns([2, 3])
            if start_col.button("🚀 Start Hiring Now", type="primary", use_container_width=True):
                create_job(
                    title=job_title.strip(),
                    requirements=job_requirements.strip(),
                    jd_text=jd_editable,
                    score_threshold=score_threshold,
                )
                st.session_state.jd_text = None
                st.balloons()
                st.success(f"🎉 Hiring session started for **{job_title}**! Worker will begin scanning Drive shortly.")
                time.sleep(1.5)
                st.rerun()

# ─────────────────────────── TAB 2: REVIEW ───────────────────────────────────
with tab_review:

    active_job = get_active_job()

    if not active_job:
        st.markdown(
            """<div class="hp-card" style="text-align:center;padding:48px">
                <p style="font-size:48px;margin:0">🎯</p>
                <h3 style="color:#8b949e;margin:12px 0 8px 0">No Active Hiring Session</h3>
                <p style="color:#8b949e;margin:0">Go to <strong>Launch Hiring</strong> to start screening candidates.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        st.stop()

    col_refresh, col_auto, _ = st.columns([1, 2, 4])
    if col_refresh.button("🔄 Refresh", use_container_width=True):
        st.rerun()
    auto_refresh = col_auto.checkbox("Auto-refresh every 30s", value=False)
    if auto_refresh:
        time.sleep(30)
        st.rerun()

    df = get_candidates_for_job(active_job["normalized_title"])

    if df.empty:
        st.markdown(
            """<div class="hp-card" style="text-align:center;padding:48px">
                <p style="font-size:48px;margin:0">⏳</p>
                <h3 style="color:#8b949e;margin:12px 0 8px 0">Scanning in Progress</h3>
                <p style="color:#8b949e;margin:0">No candidates yet. Keep the worker running — it checks every 3 minutes.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        st.stop()

    # ── Sub-tabs: Pending / Shortlisted / All ─────────────────────────────────
    pending_df = df[(df["decision"] == "SHORTLIST") & (df["action_status"].isin(["PENDING_REVIEW", "ERROR"]))]
    shortlisted_df = df[df["decision"] == "SHORTLIST"]
    rejected_df = df[df["decision"] == "REJECT"]

    sub_pending, sub_shortlisted, sub_post, sub_rejected, sub_all = st.tabs([
        f"⏳ Pending Approval ({len(pending_df)})",
        f"✅ Shortlisted ({len(shortlisted_df)})",
        f"🎤 Interview Tracking",
        f"❌ Rejected ({len(rejected_df)})",
        f"📋 All Candidates ({len(df)})",
    ])

    # ── PENDING ───────────────────────────────────────────────────────────────
    with sub_pending:
        if pending_df.empty:
            st.markdown(
                """<div class="hp-card" style="text-align:center;padding:32px">
                    <p style="font-size:36px;margin:0">🎉</p>
                    <p style="color:#3fb950;margin:12px 0 0 0;font-weight:600">All shortlisted candidates have been reviewed!</p>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'<div class="section-title">Candidates awaiting your decision ({len(pending_df)})</div>', unsafe_allow_html=True)

            for _, row in pending_df.reset_index(drop=True).iterrows():
                score = row["score"] or 0
                score_cls = "score-high" if score >= 75 else ("score-mid" if score >= 55 else "score-low")

                with st.container():
                    st.markdown(
                        f"""<div class="cand-card">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
                                <div>
                                    <span style="font-size:17px;font-weight:700;color:#e6edf3">{row['name'] or 'Unknown'}</span>
                                    <br>
                                    <span style="font-size:13px;color:#8b949e">{row['email'] or 'No email'}</span>
                                </div>
                                <span class="score-badge {score_cls}">{score} pts</span>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    btn_col1, btn_col2, slot_col = st.columns([2, 2, 3])

                    slot_index = slot_col.number_input(
                        "Interview slot #",
                        min_value=0, max_value=20, value=0, step=1,
                        key=f"slot-{row['file_id']}",
                        help="Index of the interview slot from your calendar settings.",
                    )

                    if row.get("error_message"):
                        st.error(f"⚠️ Previous attempt failed: {row['error_message']}")

                    if btn_col1.button("✅ Approve & Invite", key=f"approve-{row['file_id']}", type="primary", use_container_width=True):
                        with st.spinner("Scheduling interview & sending email…"):
                            try:
                                result = approve_candidate_for_interview(
                                    row["file_id"],
                                    active_job["normalized_title"],
                                    slot_index=int(slot_index),
                                )
                                if result.get("already_sent"):
                                    st.info("Interview email was already sent to this candidate.")
                                else:
                                    st.success(f"✅ Email sent! Interview: {result.get('interview_time', 'N/A')}")
                                time.sleep(0.8)
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Failed: {exc}")

                    if btn_col2.button("❌ Reject", key=f"reject-{row['file_id']}", use_container_width=True):
                        reject_candidate(row["file_id"], active_job["normalized_title"])
                        st.warning(f"Rejected {row['name']}.")
                        time.sleep(0.6)
                        st.rerun()

                    st.markdown("---")

    # ── SHORTLISTED ───────────────────────────────────────────────────────────
    with sub_shortlisted:
        if shortlisted_df.empty:
            st.info("No shortlisted candidates yet.")
        else:
            for _, row in shortlisted_df.iterrows():
                score = row["score"] or 0
                score_cls = "score-high" if score >= 75 else "score-mid"
                status_icon = {"EMAIL_SENT": "📧", "PENDING_REVIEW": "⏳", "REJECTED": "❌",
                               "ERROR": "⚠️", "INTERVIEWED_PASSED": "🏆",
                               "INTERVIEWED_FAILED": "❌", "NO_SHOW": "👻",
                               "OFFER_SENT": "🎉"}.get(row["action_status"], "❓")

                st.markdown(
                    f"""<div class="cand-card">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                            <div>
                                <span style="font-size:16px;font-weight:700;color:#e6edf3">{row['name'] or 'Unknown'}</span>
                                <span style="color:#8b949e;font-size:13px;margin-left:12px">{row['email'] or ''}</span>
                            </div>
                            <div style="display:flex;gap:10px;align-items:center">
                                <span class="score-badge {score_cls}">{score} pts</span>
                                <span style="color:#8b949e;font-size:13px">{status_icon} {row['action_status']}</span>
                            </div>
                        </div>
                        {f'<p style="color:#8b949e;font-size:12px;margin:8px 0 0 0">Interview: {row["interview_time"]}</p>' if row.get("interview_time") else ''}
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── POST-INTERVIEW TRACKING ───────────────────────────────────────────────
    with sub_post:
        invited_df = df[df["action_status"].isin(["EMAIL_SENT", "INTERVIEWED_PASSED",
                                                   "INTERVIEWED_FAILED", "NO_SHOW", "OFFER_SENT"])]
        if invited_df.empty:
            st.markdown(
                """<div class="hp-card" style="text-align:center;padding:40px">
                    <p style="font-size:36px;margin:0">🎤</p>
                    <p style="color:#8b949e;margin:12px 0 0 0;font-weight:600">No candidates have been invited yet.</p>
                    <p style="color:#8b949e;font-size:13px;margin:6px 0 0 0">Approve shortlisted candidates first.</p>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="section-title">Record interview results & send offers</div>', unsafe_allow_html=True)

            for _, row in invited_df.reset_index(drop=True).iterrows():
                score      = row["score"] or 0
                status     = row["action_status"]
                score_cls  = "score-high" if score >= 75 else "score-mid"
                status_map = {
                    "EMAIL_SENT": ("📧", "#388bfd", "Invited"),
                    "NO_SHOW":    ("👻", "#8b949e", "No-Show"),
                    "INTERVIEWED_PASSED": ("🏆", "#3fb950", "Passed"),
                    "INTERVIEWED_FAILED": ("❌", "#f85149", "Failed"),
                    "OFFER_SENT": ("🎉", "#d29922", "Offer Sent"),
                }
                icon, colour, label = status_map.get(status, ("❓", "#8b949e", status))

                with st.container():
                    st.markdown(
                        f"""<div class="cand-card">
                            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
                                <div>
                                    <span style="font-size:16px;font-weight:700;color:#e6edf3">{row['name'] or 'Unknown'}</span><br>
                                    <span style="color:#8b949e;font-size:13px">{row['email'] or 'No email'}</span>
                                </div>
                                <div style="display:flex;gap:10px;align-items:center">
                                    <span class="score-badge {score_cls}">{score} pts</span>
                                    <span style="color:{colour};font-size:13px;font-weight:600">{icon} {label}</span>
                                </div>
                            </div>
                            {f'<p style="color:#8b949e;font-size:12px;margin:8px 0 0 0">🕐 Interview: {row["interview_time"]}</p>' if row.get('interview_time') else ''}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    # ── Record outcome (only if still EMAIL_SENT or NO_SHOW) ──
                    if status in ("EMAIL_SENT", "NO_SHOW"):
                        st.markdown("**Record Interview Outcome:**")
                        notes = st.text_input(
                            "Notes (optional)",
                            key=f"notes-{row['file_id']}",
                            placeholder="e.g. Strong problem-solving, weak system design",
                        )
                        o1, o2, o3, o4 = st.columns(4)
                        if o1.button("🏆 Passed", key=f"pass-{row['file_id']}", use_container_width=True):
                            record_interview_result(row["file_id"], active_job["normalized_title"], "PASSED", notes)
                            st.success(f"{row['name']} marked as Passed!")
                            time.sleep(0.6); st.rerun()

                        if o2.button("❌ Failed", key=f"fail-{row['file_id']}", use_container_width=True):
                            record_interview_result(row["file_id"], active_job["normalized_title"], "FAILED", notes)
                            st.warning(f"{row['name']} marked as Failed.")
                            time.sleep(0.6); st.rerun()

                        if o3.button("👻 No-Show", key=f"noshow-{row['file_id']}", use_container_width=True):
                            record_interview_result(row["file_id"], active_job["normalized_title"], "NO_SHOW", notes)
                            st.info(f"{row['name']} marked as No-Show.")
                            time.sleep(0.6); st.rerun()

                        # Reschedule
                        with o4.expander("🔄 Reschedule"):
                            new_slot = st.number_input(
                                "New slot #", 0, 20, 1,
                                key=f"reslot-{row['file_id']}",
                            )
                            if st.button("Send new invite", key=f"resend-{row['file_id']}"):
                                with st.spinner("Rescheduling…"):
                                    try:
                                        res = reschedule_candidate_interview(
                                            row["file_id"], active_job["normalized_title"], int(new_slot)
                                        )
                                        st.success(f"Rescheduled: {res['interview_time']}")
                                        time.sleep(0.8); st.rerun()
                                    except Exception as e:
                                        st.error(str(e))

                    # ── Send offer (only if Passed) ──────────────────────────
                    if status == "INTERVIEWED_PASSED":
                        st.markdown("**🎉 Send Offer Letter:**")
                        off1, off2 = st.columns(2)
                        salary_val = off1.text_input(
                            "Salary / Package",
                            placeholder="e.g. ₹12 LPA",
                            key=f"salary-{row['file_id']}",
                        )
                        joining_val = off2.text_input(
                            "Expected Joining Date",
                            placeholder="e.g. 01 Aug 2026",
                            key=f"joining-{row['file_id']}",
                        )
                        extra = st.text_area(
                            "Additional notes",
                            placeholder="Benefits, perks, role details…",
                            height=80,
                            key=f"extra-{row['file_id']}",
                        )
                        if st.button("📨 Send Offer Letter", key=f"offer-{row['file_id']}",
                                     type="primary", use_container_width=False):
                            with st.spinner("Sending offer letter…"):
                                try:
                                    send_offer_letter(
                                        row["file_id"], active_job["normalized_title"],
                                        salary=salary_val, joining_date=joining_val, extra_notes=extra,
                                    )
                                    st.success(f"🎉 Offer letter sent to {row['name']}!")
                                    st.balloons()
                                    time.sleep(1); st.rerun()
                                except Exception as e:
                                    st.error(str(e))

                    if status == "OFFER_SENT":
                        st.success(f"✅ Offer sent on {row.get('offer_sent_at', '')[:10]}  ·  {row.get('offer_details', '')}")

                    if status == "INTERVIEWED_FAILED":
                        st.markdown(
                            f"<p style='color:#8b949e;font-size:13px'>Notes: {row.get('interview_notes') or '—'}</p>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("---")

    # ── REJECTED ──────────────────────────────────────────────────────────────
    with sub_rejected:
        if rejected_df.empty:
            st.info("No rejected candidates yet.")
        else:
            for _, row in rejected_df.iterrows():
                score = row["score"] or 0
                st.markdown(
                    f"""<div class="cand-card" style="opacity:.65">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <span style="font-size:15px;font-weight:600;color:#8b949e">{row['name'] or 'Unknown'}</span>
                                <span style="color:#8b949e;font-size:12px;margin-left:10px">{row['email'] or ''}</span>
                            </div>
                            <span class="score-badge score-low">{score} pts</span>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # ── ALL ───────────────────────────────────────────────────────────────────
    with sub_all:
        display_cols = ["name", "email", "score", "decision", "action_status", "interview_time", "processed_at"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(
            df[available].sort_values("score", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
