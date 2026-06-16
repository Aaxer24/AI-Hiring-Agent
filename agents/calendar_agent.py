from datetime import timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def schedule_interview(candidate_email, start_time, request_id: str):
    creds = Credentials.from_authorized_user_file(settings.google_token_file, SCOPES)
    service = build("calendar", "v3", credentials=creds)

    end_time = start_time + timedelta(minutes=settings.interview_duration_min)

    event = {
        "summary": f"Interview - {settings.company_name} Hiring",
        "description": "Interview scheduled by AI Hiring Agent after recruiter approval.",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": settings.timezone,
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": settings.timezone,
        },
        "attendees": [{"email": candidate_email}],
        "conferenceData": {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    event = (
        service.events()
        .insert(calendarId="primary", body=event, conferenceDataVersion=1)
        .execute()
    )

    return {
        "meet_link": event.get("hangoutLink", ""),
        "event_id": event.get("id"),
    }
