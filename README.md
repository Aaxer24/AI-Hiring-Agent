# AI Hiring Agent

Autonomous hiring workflow built with Streamlit, LangChain, LangGraph, and Google API integrations.

## Features

- Generate job descriptions for open roles.
- Start and stop hiring workflows from a Streamlit dashboard.
- Process resumes and candidate information.
- Schedule interviews and send email updates through Google integrations.

## Setup

1. Create and activate a Python virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a local `.env` file with the required API keys and configuration.
4. Add Google OAuth credentials under `credentials/`.

## Run

Start the dashboard:

```bash
streamlit run app.py
```

Start the background worker separately when needed:

```bash
python run_agent_worker.py
```

## Notes

Local secrets, OAuth tokens, generated job state, resumes, spreadsheets, and virtual environments are intentionally excluded from Git.
