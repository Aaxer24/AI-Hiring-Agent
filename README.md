# AI Hiring Agent

Local-first AI hiring workflow built with Streamlit, LangChain, OpenAI, SQLite, and Google Drive/Gmail/Calendar integrations.

## What It Does

- Creates job descriptions from role requirements.
- Stores hiring jobs in SQLite instead of temporary state files.
- Watches a Google Drive folder for new PDF resumes.
- Parses and screens candidates against the active job.
- Stores candidate score, decision, status, and interview metadata.
- Requires human approval before sending interview emails or creating Calendar events.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in:

   ```bash
   OPENAI_API_KEY=
   GOOGLE_DRIVE_FOLDER_ID=
   ```

4. Put your Google OAuth client file at:

   ```text
   credentials/credentials.json
   ```

5. Generate or refresh the Google token:

   ```bash
   python run_oauth.py
   ```

## Run Locally

Start the dashboard:

```bash
streamlit run app.py
```

Start the background worker in another terminal:

```bash
python run_agent_worker.py
```

## Workflow

1. Open the dashboard.
2. Generate a job description.
3. Start the hiring job.
4. Run the worker so resumes are fetched and screened.
5. Review shortlisted candidates in the dashboard.
6. Click approve to create the Calendar event and send the interview email.

## Safety Notes

Secrets, OAuth tokens, resumes, generated databases, and virtual environments are excluded from Git. Candidate emails and interview metadata are stored locally in SQLite.
