from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from storage.processed_resumes import init_db, is_already_processed
import io # Converts downloaded file streams into raw bytes

"""
-This function fetches new resume PDFs from a Google Drive folder
-skips resumes already processed for a given job role
-downloads only the new ones as raw bytes
-and returns them in a structured list ready for parsing by my AI pipeline

so in short, this file:
-Connects to Google Drive
-Fetches PDF files
-Downloads file bytes
-Returns them as:
{
   "file_id": "...",
   "filename": "...",
   "content": file_bytes
}
"""
def fetch_new_resumes(folder_id: str, job_title: str):
    
    init_db()

    creds = Credentials.from_authorized_user_file(
        "credentials/token.json",
        ["https://www.googleapis.com/auth/drive.readonly"]
    ) # Loads OAuth token from file. Grants read-only access to Drive

    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        q=(
            f"'{folder_id}' in parents "
            "and mimeType='application/pdf' "
            "and trashed=false"
        ),
        fields="files(id, name, mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get("files", [])
    print(f"📂 Found {len(files)} files in Drive folder")

    resumes = []

    for file in files:
        if is_already_processed(file["id"], job_title):
            continue

        request = service.files().get_media(fileId=file["id"])
        file_bytes = io.BytesIO(request.execute()).getvalue()

        resumes.append({
            "file_id": file["id"],
            "filename": file["name"],
            "content": file_bytes
        })

    return resumes

# The resumes are downloaded into memory temporarily as byte streams and processed immediately. They are not permanently stored in my system. Only structured metadata and decisions are stored in the database. The original resumes remain in Google Drive.