import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    google_drive_folder_id: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    google_token_file: str = os.getenv("GOOGLE_TOKEN_FILE", "credentials/token.json")
    default_score_threshold: float = _get_float("DEFAULT_SCORE_THRESHOLD", 70.0)
    check_interval_seconds: int = _get_int("CHECK_INTERVAL_SECONDS", 180)
    timezone: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    # Which provider to use right now: "openai" or "groq". Flip this one value
    # to switch — no code changes needed anywhere else.
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")

    # OpenAI config (used when llm_provider == "openai")
    openai_chat_model: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        "text-embedding-3-small",
    )

    # Groq config (used when llm_provider == "groq") — free tier, open-source models.
    # Get a free key at https://console.groq.com/keys
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_chat_model: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.3-70b-versatile")

    # Local embedding model — used when llm_provider == "groq". Runs on CPU,
    # no API key, no rate limits, $0 cost.
    local_embedding_model: str = os.getenv(
        "LOCAL_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
    )

    company_name: str = os.getenv("COMPANY_NAME", "Zopper")
    company_website: str = os.getenv("COMPANY_WEBSITE", "https://www.zopper.com")
    hr_name: str = os.getenv("HR_NAME", "Priyanka Sharma")
    hr_title: str = os.getenv("HR_TITLE", "Recruitment Head")
    interview_mode: str = os.getenv("INTERVIEW_MODE", "Google Meet")
    interview_duration_min: int = _get_int("INTERVIEW_DURATION_MIN", 45)


settings = Settings()
