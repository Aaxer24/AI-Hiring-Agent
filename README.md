# 🤖 HirePilot AI — Autonomous AI Hiring Agent

> **A fully local, end-to-end AI-powered hiring system** that screens resumes from Google Drive, scores candidates using LLM + semantic embeddings, and manages the entire interview pipeline — from shortlisting to multi-round interviews to offer letters — all from a beautiful Streamlit dashboard.

---

## ✨ Features

### 🔍 Automated Resume Screening
- Watches a **Google Drive folder** for new PDF resumes every 3 minutes
- Extracts structured candidate data using **GPT-4o-mini**
- Scores candidates using a **multi-factor algorithm**:
  - Semantic similarity (OpenAI embeddings + cosine similarity)
  - Fuzzy skill matching with synonym awareness (`ML` ↔ `Machine Learning`, `NLP` ↔ `Natural Language Processing`)
  - Role alignment with compatible-group logic
  - Experience alignment (internships counted as 0.5 years each)
  - Project bonus for junior candidates with strong portfolios
  - Institute match (only penalises if JD explicitly requires IIT/NIT)

### 🧑‍💼 Human-in-the-Loop Dashboard
- **No email or calendar event is ever sent without recruiter approval**
- Create hiring jobs with AI-generated job descriptions
- Real-time candidate table with scores, decisions, and statuses
- Per-candidate **Approve** / **Reject** buttons
- Live metric tiles: Resumes Scanned · Shortlisted · Awaiting Approval · Invited

### 📅 Full Interview Pipeline
| Stage | What happens |
|---|---|
| **Shortlisted** | Candidate awaits recruiter approval |
| **Approved** | Google Calendar event created + Gmail invite sent |
| **Interview done** | Mark as ✅ Passed / ❌ Failed / 👻 No-Show |
| **Passed** | Choose: schedule next round OR send offer letter |
| **Next Round** | Pick round type (Technical, HR, CTO, etc.), new slot auto-books Calendar + sends congratulations email |
| **Offer Sent** | Personalised offer letter emailed with salary, joining date, and perks |

### 🔁 Multi-Round Interviews
- Unlimited interview rounds (Round 1 → Round 2 → Round 3 → ...)
- Round type presets: Technical Round, System Design, HR Discussion, Managerial Round, CTO Interview, Culture Fit, Assignment Review, Custom
- Each round: auto-increments round number, creates new Calendar event, sends round-specific email
- Round badges update in real time on the dashboard

### 🛡️ Safety & Reliability
- **SQLite-backed state** — no lost data on restart
- Schema-validated LLM outputs with graceful fallbacks (no pydantic required)
- Structured logging with rotating file handler
- All secrets, tokens, and databases excluded from Git
- Fresh-start reset button clears candidate data without deleting job config

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Dashboard                 │
│  Job Setup │ Candidate Review │ Interview Tracking  │
└────────────────────┬────────────────────────────────┘
                     │ SQLite (processed_resumes.db)
┌────────────────────▼────────────────────────────────┐
│              Background Worker                       │
│  run_agent_worker.py  ←  polls every 3 min          │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │   Google Drive API  │ ← PDF resumes
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   Resume Agent      │ ← pdfplumber + GPT-4o-mini
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   Screening Agent   │ ← embeddings + scoring
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │   SQLite DB         │ ← jobs + candidates + rounds
          └──────────┬──────────┘
                     │ (only after human approval)
          ┌──────────▼──────────┐
          │  Gmail + Calendar   │ ← invite / offer / reschedule
          └─────────────────────┘
```

---

## 📁 Project Structure

```
AI Hiring Agent/
├── app.py                      # Streamlit dashboard (main UI)
├── run_agent_worker.py         # Background resume screening worker
├── run_oauth.py                # Google OAuth token generator
├── generate_token.py           # Alternative token helper
│
├── agents/
│   ├── resume_intake_agent.py  # Fetches PDFs from Google Drive
│   ├── resume_agent.py         # Extracts structured text from PDFs
│   ├── screening_agent.py      # Scores candidates (LLM + embeddings)
│   ├── email_agent.py          # Gmail send helper
│   ├── calendar_agent.py       # Google Calendar event creator
│   ├── jd_generator_agent.py   # AI job description generator
│   ├── jd_agent.py             # JD parsing helper
│   └── jd_formatter_agent.py   # JD formatting helper
│
├── config/
│   ├── settings.py             # Centralised config from .env
│   ├── logging_config.py       # Rotating file + console logging
│   └── company_config.py       # Company branding defaults
│
├── graph/
│   └── hiring_graph.py         # LangGraph screening workflow
│
├── models/
│   ├── __init__.py
│   └── schemas.py              # Dataclasses + safe JSON parse helpers
│
├── services/
│   ├── candidate_actions.py    # Approve, reschedule, next round, offer
│   ├── batch_processor.py      # Batch resume processing
│   └── interview_scheduler.py  # Interview slot generator
│
├── storage/
│   ├── processed_resumes.py    # SQLite DB layer (all CRUD)
│   └── db_reader.py            # Read helpers for dashboard
│
├── tests/
│   ├── test_schemas.py         # Schema fallback tests
│   └── test_processed_resumes.py # DB lifecycle tests
│
├── credentials/                # OAuth files (git-ignored)
│   ├── credentials.json        # Google OAuth client secret
│   └── token.json              # Generated OAuth token
│
├── .env                        # Your secrets (git-ignored)
├── .env.example                # Template for .env
└── requirements.txt
```

---

## ⚙️ Setup

### 1. Clone & create virtual environment

```bash
git clone https://github.com/Aaxer24/AI-Hiring-Agent.git
cd "AI Hiring Agent"
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

Open `.env` and fill in:

```env
# Required
OPENAI_API_KEY=sk-...
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id

# Optional (defaults shown)
DEFAULT_SCORE_THRESHOLD=70
CHECK_INTERVAL_SECONDS=180
TIMEZONE=Asia/Kolkata
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Your company branding (appears in emails)
COMPANY_NAME=Your Company
COMPANY_WEBSITE=https://example.com
HR_NAME=Recruiting Team
HR_TITLE=Talent Acquisition
INTERVIEW_MODE=Google Meet
INTERVIEW_DURATION_MIN=45
```

**Finding your Google Drive Folder ID:**
Open the folder in your browser. The ID is the string after `/folders/` in the URL:
```
https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQ  ← this part
```

### 4. Set up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Gmail API**, **Google Calendar API**, **Google Drive API**
3. Create OAuth 2.0 credentials → Download as `credentials.json`
4. Place it at `credentials/credentials.json`
5. Run the token generator:

```bash
python run_oauth.py
```

This opens a browser for Google sign-in and saves `credentials/token.json`.

> ⚠️ The Google account used must have **Viewer** access to your Drive resume folder.

---

## 🚀 Running the App

Open **two terminals**:

**Terminal 1 — Dashboard:**
```bash
streamlit run app.py
```

**Terminal 2 — Worker:**
```bash
python run_agent_worker.py
```

Then open **http://localhost:8501** in your browser.

---

## 📖 Usage Walkthrough

### Step 1 — Create a hiring job
1. Go to **🚀 Launch Hiring** tab
2. Enter the role name and key requirements
3. Click **✨ Generate Job Description** — GPT writes the JD
4. Review/edit the JD
5. Set the shortlist score threshold (default: 70)
6. Click **🚀 Start Hiring Now**

### Step 2 — Worker screens resumes
The worker automatically:
- Polls the Drive folder every 3 minutes
- Downloads new PDFs
- Extracts text and scores each candidate
- Saves results to SQLite

Worker logs tell you exactly what's happening:
```
INFO - Found 4 PDF files in Drive folder
INFO - Screening done | score=81.3 | decision=SHORTLIST | ...
INFO - No new resumes found for job=data scientist
```

### Step 3 — Review candidates
Go to **👥 Candidate Review** → **⏳ Pending Approval** tab:
- See each shortlisted candidate with their score
- Click **✅ Approve & Invite** → Calendar event + Gmail sent instantly
- Click **❌ Reject** to dismiss

### Step 4 — Track interviews
Go to **🎤 Interview Tracking** tab:
- All invited candidates appear here
- Mark outcome: **🏆 Passed** / **❌ Failed** / **👻 No-Show**
- Add interview notes for your records

### Step 5 — Next round or offer
After a candidate **Passes**, two options appear:

**Option A — Schedule next round:**
- Pick round type (Technical, HR, CTO, custom, etc.)
- Add what the candidate should prepare for
- Pick a time slot → invite auto-sent with congratulations email

**Option B — Send offer letter:**
- Enter salary, joining date, extra notes
- Click Send → personalised offer letter emailed

### Fresh Start
If you want to re-screen all Drive files from scratch:
> **Sidebar → Reset & Rescan → Confirm**

This clears candidate results but keeps your job config intact.

---

## 🧪 Running Tests

No external test runner needed — uses Python's built-in `unittest`:

```bash
python -m unittest discover -s tests -p "*.py" -v
```

Current tests:
- `test_schemas.py` — LLM output parse with valid JSON and fallback for bad JSON
- `test_processed_resumes.py` — Full job + candidate lifecycle in SQLite

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI API key |
| `GOOGLE_DRIVE_FOLDER_ID` | — | **Required.** Drive folder containing resumes |
| `GOOGLE_TOKEN_FILE` | `credentials/token.json` | OAuth token path |
| `DEFAULT_SCORE_THRESHOLD` | `70` | Minimum score to shortlist a candidate |
| `CHECK_INTERVAL_SECONDS` | `180` | How often worker polls Drive (seconds) |
| `TIMEZONE` | `Asia/Kolkata` | Timezone for interview slot generation |
| `OPENAI_CHAT_MODEL` | `gpt-4o-mini` | GPT model for parsing + JD generation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for semantic scoring |
| `COMPANY_NAME` | `Your Company` | Appears in all emails |
| `COMPANY_WEBSITE` | `https://example.com` | Appears in email signatures |
| `HR_NAME` | `Recruiting Team` | Email sender name |
| `HR_TITLE` | `Talent Acquisition` | Email sender title |
| `INTERVIEW_MODE` | `Google Meet` | Shown in invite emails |
| `INTERVIEW_DURATION_MIN` | `45` | Shown in invite emails |

---

## 🔐 Security Notes

The following are **excluded from Git** via `.gitignore`:
- `.env` (API keys)
- `credentials/` (OAuth tokens and client secrets)
- `storage/*.db` (candidate data)
- `venv/` (virtual environment)
- `__pycache__/`

All candidate data is stored **locally** in `storage/processed_resumes.db` and never leaves your machine.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **UI** | Streamlit |
| **LLM** | OpenAI GPT-4o-mini via LangChain |
| **Embeddings** | OpenAI text-embedding-3-small |
| **Semantic Scoring** | scikit-learn cosine similarity |
| **PDF Parsing** | pdfplumber |
| **Workflow** | LangGraph |
| **Database** | SQLite (stdlib) |
| **Google APIs** | Drive · Gmail · Calendar |
| **Config** | python-dotenv |
| **Logging** | Python logging (rotating file handler) |

---

## 📄 License

MIT — feel free to fork, extend, and build on this.
