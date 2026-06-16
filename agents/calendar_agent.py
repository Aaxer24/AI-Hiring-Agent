from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta


"""calendar_agent.py is responsible for:
-Creating a Google Calendar event
-Adding candidate as attendee
-Generating Google Meet link
-Setting start and end time

It assumes: You give me a start_time, I will schedule it. I do not decide the time, I just execute the scheduling. This keeps my role focused and allows interview_scheduler.py to handle time allocation logic separately.
"""

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def schedule_interview(candidate_email, start_time):
    creds = Credentials.from_authorized_user_file(
        "credentials/token.json",
        SCOPES
    )

    service = build("calendar", "v3", credentials=creds)

    end_time = start_time + timedelta(minutes=30)

    event = {
        "summary": "Interview – Zopper Hiring",
        "description": "Technical Interview",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "attendees": [{"email": candidate_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": "interview123",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    event = service.events().insert(
        calendarId="primary",
        body=event,
        conferenceDataVersion=1
    ).execute()

    return event["hangoutLink"]
