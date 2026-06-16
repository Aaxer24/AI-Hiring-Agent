# import time
# import json
# import os

# from agents.resume_intake_agent import fetch_new_resumes
# from graph.hiring_graph import hiring_agent
# from storage.processed_resumes import init_db

# FOLDER_ID = "1UVNQnI5WGidYk-8_qJSuymE3ZXpOJS-CEDQytFJ3eBVL0BwHWdd4Rz7n6tI0mIkZCpvhCgmH"
# CHECK_INTERVAL = 300  # 5 minutes

# init_db()

# print("🤖 AI Hiring Agent started in background (IDLE MODE)...")

# while True:
#     try:
#         # -------------------------------------------------
#         # Wait for job activation
#         # -------------------------------------------------
#         if not os.path.exists("job_state.json"):
#             print("⏸️ Job state not found. Waiting...")
#             time.sleep(30)
#             continue

#         with open("job_state.json", "r") as f:
#             job_state = json.load(f)

#         if not job_state.get("active"):
#             print("⏸️ Job not active. Waiting...")
#             time.sleep(30)
#             continue

#         job_title = job_state.get("job_title")
#         if not job_title:
#             print("⚠️ Job active but job_title missing. Waiting...")
#             time.sleep(30)
#             continue

#         if not os.path.exists("jd.txt"):
#             print("⚠️ JD missing. Waiting...")
#             time.sleep(30)
#             continue

#         with open("jd.txt", "r", encoding="utf-8") as f:
#             jd_text = f.read().strip()

#         if not jd_text:
#             print("⚠️ JD empty. Waiting...")
#             time.sleep(30)
#             continue

#         # -------------------------------------------------
#         # Fetch ONLY unprocessed resumes for this job
#         # -------------------------------------------------
#         resumes = fetch_new_resumes(FOLDER_ID, job_title)

#         if resumes:
#             hiring_agent({
#                 "job_title": job_title,
#                 "jd_text": jd_text,
#                 "resumes": resumes
#             })
#             print(f"✅ Processed {len(resumes)} resumes for {job_title}")

#         time.sleep(CHECK_INTERVAL)

#     except Exception as e:
#         print("❌ Error in background agent:", e)
#         time.sleep(60)

import time
import json
import os

from agents.resume_intake_agent import fetch_new_resumes
from graph.hiring_graph import hiring_agent
from storage.processed_resumes import init_db

"""This script runs the hiring agent in the background. It periodically checks if a job is active, looks for new resumes, and automatically processes them using the hiring pipeline. If there is nothing to do or an error occurs, it safely waits and retries."""

FOLDER_ID = "19lpd3dRwp0SkK5o7-hOZZ5AY7aABaLLhU7lYZs3djGqJICdMfp7eEyKSB_0X3EbSeHQgsWU_"
CHECK_INTERVAL = 180  # 3 minutes

# Initialize DB ONCE
init_db()

print("🤖 AI Hiring Agent started in background (IDLE MODE)...")

while True:
    try:
        if not os.path.exists("job_state.json"):
            time.sleep(30)
            continue # Job might not be configured yet. Agent waits patiently

        with open("job_state.json", "r") as f:
            job_state = json.load(f)

        if not job_state.get("active"):
            print("⏸️ Job not active. Waiting...")
            time.sleep(30)
            continue

        job_title = job_state.get("job_title")
        if not job_title:
            time.sleep(30)
            continue

        # Normalize job title (VERY IMPORTANT)
        job_title = job_title.lower().strip()

        if not os.path.exists("jd.txt"):
            time.sleep(30)
            continue

        with open("jd.txt", "r", encoding="utf-8") as f:
            jd_text = f.read()

        resumes = fetch_new_resumes(FOLDER_ID, job_title)

        if not resumes:
            print("📭 No new resumes found.")
            time.sleep(CHECK_INTERVAL)
            continue

        hiring_agent({
            "job_title": job_title,
            "jd_text": jd_text,
            "resumes": resumes
        })

        print(f"✅ Processed {len(resumes)} resumes for '{job_title}'")
        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        print("❌ Error in background agent:", e)
        time.sleep(60)
