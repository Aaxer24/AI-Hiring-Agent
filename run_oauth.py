import os

from google_auth_oauthlib.flow import InstalledAppFlow

from config.settings import settings

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
]

TOKEN_PATH = settings.google_token_file
CREDENTIALS_PATH = "credentials/credentials.json"


def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)

    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)

    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())

    print(f"Authentication successful. Token created at {TOKEN_PATH}.")


if __name__ == "__main__":
    authenticate()
