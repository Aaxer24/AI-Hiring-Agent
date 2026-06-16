from langchain_openai import ChatOpenAI
from config.settings import settings

llm = ChatOpenAI(model=settings.openai_chat_model, temperature=0)


def generate_jd(job_title: str, requirements: str = ""):
    """Generates a professional, ATS-friendly job description.
    """

    prompt = f"""
You are a senior technical recruiter and hiring manager.

Generate a professional job description for the role:
JOB TITLE: {job_title}

Additional hiring requirements / constraints (if any):
{requirements if requirements else "None specified"}

The job description must include:
- Role Overview
- Key Responsibilities
- Required Skills
- Preferred / Nice-to-Have Skills
- Experience Level

Rules:
- Use clear, professional language
- Do NOT include company-specific filler text
- Do NOT include salary unless explicitly asked
- Return plain text only
"""

    return llm.invoke(prompt).content
