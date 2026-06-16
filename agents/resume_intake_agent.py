import io
import logging

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config.settings import settings
from storage.processed_resumes import init_db, is_already_processed

logger = logging.getLogger(__name__)


def fetch_new_resumes(folder_id: str, job_title: str):
    init_db()

    creds = Credentials.from_authorized_user_file(
        settings.google_token_file,
        ["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=creds)

    results = (
        service.files()
        .list(
            q=(
                f"'{folder_id}' in parents "
                "and mimeType='application/pdf' "
                "and trashed=false"
            ),
            fields="files(id, name, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )

    files = results.get("files", [])
    logger.info("Found %s PDF files in Drive folder", len(files))

    resumes = []

    for file in files:
        if is_already_processed(file["id"], job_title):
            continue

        request = service.files().get_media(fileId=file["id"])
        file_bytes = io.BytesIO(request.execute()).getvalue()

        resumes.append(
            {
                "file_id": file["id"],
                "filename": file["name"],
                "content": file_bytes,
            }
        )

    return resumes
