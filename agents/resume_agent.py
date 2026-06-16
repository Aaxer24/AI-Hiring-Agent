import io
import logging

import pdfplumber
from langchain_openai import ChatOpenAI

from config.settings import settings
from models.schemas import ParsedResume, parse_model, to_dict

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model=settings.openai_chat_model, temperature=0)


def extract_text(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def parse_resume(resume_dict: dict):
    resume_text = extract_text(resume_dict["content"])
    if not resume_text.strip():
        logger.warning("Resume %s had no extractable text", resume_dict.get("filename"))

    prompt = f"""
You MUST return ONLY valid JSON.
Do NOT include any text before or after JSON.

Schema:
{{
  "name": "",
  "email": "",
  "skills": [],
  "experience_years": 0,
  "projects": []
}}

Resume:
{resume_text}
"""

    response = llm.invoke(prompt).content
    structured = parse_model(ParsedResume, response, ParsedResume())

    return {
        "raw_text": resume_text,
        "structured": to_dict(structured),
    }
