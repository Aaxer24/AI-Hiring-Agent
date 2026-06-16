import json
import re
import io
import pdfplumber
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

"""
This file:
-Takes the downloaded PDF bytes
-Extracts text using pdfplumber
-Sends text to LLM
-Converts resume into structured JSON like:
-Returns:
{
  "name": "",
  "email": "",
  "skills": [],
  "experience_years": "",
  "projects": []
}
"""

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def extract_text(file_bytes):
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text()
    return text


def extract_json(text: str):
    """
    Safely extract JSON object from LLM output
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


def parse_resume(resume_dict):
    resume_text = extract_text(resume_dict["content"])

    prompt = f"""
You MUST return ONLY valid JSON.
Do NOT include any text before or after JSON.

Schema:
{{
  "name": "",
  "email": "",
  "skills": [],
  "experience_years": "",
  "projects": []
}}

Resume:
{resume_text}
"""

    response = llm.invoke(prompt).content
    structured = extract_json(response)

    # FINAL SAFETY FALLBACK
    if structured is None:
        structured = {
            "name": "Unknown",
            "email": "",
            "skills": [],
            "experience_years": "",
            "projects": []
        }

    return {
        "raw_text": resume_text,
        "structured": structured
    }
