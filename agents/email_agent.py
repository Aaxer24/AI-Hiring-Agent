import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from config.company_config import *



# Email Generator

def generate_email(
    candidate_name: str,
    job_role: str,
    interview_time: str,
    meet_link: str
):
    """Generates an interview invitation email body.
    """
    return f"""
Subject: Interview Invitation | {job_role} | {COMPANY_NAME}

Dear {candidate_name},

We are pleased to inform you that, after reviewing your profile, you have been shortlisted for the next stage of the hiring process for the {job_role} position at {COMPANY_NAME}.

Your background and experience appear to align well with our requirements, and we would like to proceed with an interview to learn more about your skills, projects, and career interests.

📅 Interview Details:

Mode: {INTERVIEW_MODE}

Duration: {INTERVIEW_DURATION_MIN} minutes

Date & Time: {interview_time}

🔗 Interview Link:

{meet_link}

Please ensure you have a stable internet connection and are available at the scheduled time. If you are unable to attend, kindly reply to this email with alternative time slots, and we will do our best to accommodate your availability.

Should you have any questions prior to the interview, feel free to reach out.

We look forward to speaking with you and wish you all the best for the interview.

Warm regards,
{HR_NAME}
{HR_TITLE}
{COMPANY_NAME}
🌐 {COMPANY_WEBSITE}
"""



# Gmail Sender

def send_email(to_email: str, subject: str, body: str):
    creds = Credentials.from_authorized_user_file(
        "credentials/token.json",
        [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )

    service = build("gmail", "v1", credentials=creds)

    msg = EmailMessage()
    msg.set_content(body)
    msg["To"] = to_email
    msg["Subject"] = subject

    encoded_msg = base64.urlsafe_b64encode(
        msg.as_bytes()
    ).decode()

    service.users().messages().send(
        userId="me",
        body={"raw": encoded_msg}
    ).execute()
