from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import os

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly"
]

TOKEN_PATH = "credentials/token.json"
CREDENTIALS_PATH = "credentials/credentials.json"

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_PATH,
        SCOPES
    )
    creds = flow.run_local_server(port=0)

    os.makedirs("credentials", exist_ok=True)

    with open(TOKEN_PATH, "w") as token:
        token.write(creds.to_json())

    print("✅ Authentication successful. token.json created.")

if __name__ == "__main__":
    authenticate()
