import base64
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings


def generate_email(
    candidate_name: str,
    job_role: str,
    interview_time: str,
    meet_link: str,
):
    return f"""
Dear {candidate_name},

We are pleased to inform you that, after reviewing your profile, you have been shortlisted for the next stage of the hiring process for the {job_role} position at {settings.company_name}.

Your background and experience appear to align well with our requirements, and we would like to proceed with an interview to learn more about your skills, projects, and career interests.

Interview details:

Mode: {settings.interview_mode}
Duration: {settings.interview_duration_min} minutes
Date and time: {interview_time}
Interview link: {meet_link}

Please ensure you have a stable internet connection and are available at the scheduled time. If you are unable to attend, kindly reply to this email with alternative time slots.

Warm regards,
{settings.hr_name}
{settings.hr_title}
{settings.company_name}
{settings.company_website}
""".strip()


def send_email(to_email: str, subject: str, body: str):
    creds = Credentials.from_authorized_user_file(
        settings.google_token_file,
        [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )

    service = build("gmail", "v1", credentials=creds)

    msg = EmailMessage()
    msg.set_content(body)
    msg["To"] = to_email
    msg["Subject"] = subject

    encoded_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    return (
        service.users()
        .messages()
        .send(userId="me", body={"raw": encoded_msg})
        .execute()
    )
