import json
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any


@dataclass
class HiringIntent:
    role: str = "other"
    must_have_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    experience_level: str = "junior"


@dataclass
class CandidateProfile:
    primary_role: str = "other"
    primary_skills: list[str] = field(default_factory=list)
    secondary_skills: list[str] = field(default_factory=list)
    experience_years: float = 0
    has_projects: bool = False


@dataclass
class ParsedResume:
    name: str = "Unknown"
    email: str = ""
    skills: list[str] = field(default_factory=list)
    experience_years: float = 0
    projects: list[str] = field(default_factory=list)


ROLE_VALUES = {"data scientist", "backend engineer", "ml engineer", "other"}
EXPERIENCE_VALUES = {"fresher", "junior", "mid", "senior"}


def to_dict(model: Any) -> dict[str, Any]:
    return asdict(model)


def extract_json_object(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _coerce_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _normalize_value(name: str, value: Any, default: Any) -> Any:
    if name in {"role", "primary_role"}:
        value = str(value or default).lower().strip()
        return value if value in ROLE_VALUES else default
    if name == "experience_level":
        value = str(value or default).lower().strip()
        return value if value in EXPERIENCE_VALUES else default
    if name in {"must_have_skills", "nice_to_have_skills", "primary_skills", "secondary_skills", "skills", "projects"}:
        return _coerce_list(value)
    if name == "experience_years":
        return _coerce_float(value)
    if name == "has_projects":
        return bool(value)
    if name in {"name", "email"}:
        return str(value or default).strip()
    return value if value is not None else default


def _fallback_dict(fallback: Any) -> dict[str, Any]:
    return asdict(fallback)


def parse_model(model: type, text: str, fallback: Any) -> Any:
    data = extract_json_object(text)
    if data is None:
        return fallback

    fallback_data = _fallback_dict(fallback)
    cleaned = {}
    for field_def in fields(model):
        default = fallback_data.get(field_def.name)
        cleaned[field_def.name] = _normalize_value(
            field_def.name,
            data.get(field_def.name),
            default,
        )

    try:
        return model(**cleaned)
    except TypeError:
        return fallback
