import logging

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings
from models.schemas import CandidateProfile, HiringIntent, parse_model, to_dict

logger = logging.getLogger(__name__)

embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
llm = ChatOpenAI(model=settings.openai_chat_model, temperature=0)


def _dump_model(model):
    return to_dict(model)


def extract_hiring_intent(jd_text: str) -> dict:
    prompt = f"""Extract hiring intent from the job description.

Return STRICT JSON with these exact fields:
{{
  "role": "one of: data scientist / ml engineer / backend engineer / frontend engineer / fullstack engineer / devops engineer / data engineer / other",
  "must_have_skills": ["list of required skills, be generous, include synonyms like ML and machine learning"],
  "nice_to_have_skills": ["list of preferred skills"],
  "experience_level": "one of: fresher / junior / mid / senior"
}}

Rules:
- experience_level should be "fresher" if 0-1 years, "junior" if 1-3 years, "mid" if 3-6 years, "senior" if 6+ years
- must_have_skills: include both full forms and abbreviations (e.g. both "machine learning" and "ml")
- If the JD does not specify experience level, default to "junior"

JD:
{jd_text}
"""
    parsed = parse_model(HiringIntent, llm.invoke(prompt).content, HiringIntent())
    result = _dump_model(parsed)
    logger.debug("Hiring intent extracted: %s", result)
    return result


def extract_candidate_profile(resume_text: str) -> dict:
    prompt = f"""Extract candidate profile from this resume.

Return STRICT JSON with these exact fields:
{{
  "primary_role": "one of: data scientist / ml engineer / backend engineer / frontend engineer / fullstack engineer / devops engineer / data engineer / other",
  "primary_skills": ["list ALL technical skills mentioned, include both abbreviations and full forms"],
  "secondary_skills": ["soft skills, tools, frameworks not listed as primary"],
  "experience_years": 0.5,
  "has_projects": true
}}

Rules:
- experience_years: count internships as 0.5 years each, part-time as 0.25 years each, full-time as actual years
- primary_skills: be thorough — list every technology, language, framework, library mentioned
- Include both "ML" and "machine learning" if either appears
- primary_role: pick the role that best matches the candidate's focus

Resume:
{resume_text}
"""
    parsed = parse_model(CandidateProfile, llm.invoke(prompt).content, CandidateProfile())
    result = _dump_model(parsed)
    logger.debug("Candidate profile extracted: %s", result)
    return result


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

# Skill synonyms — if JD lists any key, candidate having any value counts as a match
_SKILL_SYNONYMS: dict[str, list[str]] = {
    "machine learning": ["ml", "machine learning", "deep learning", "dl"],
    "ml": ["ml", "machine learning", "deep learning", "dl"],
    "deep learning": ["dl", "deep learning", "machine learning", "ml"],
    "dl": ["dl", "deep learning", "machine learning", "ml"],
    "natural language processing": ["nlp", "natural language processing"],
    "nlp": ["nlp", "natural language processing"],
    "computer vision": ["cv", "computer vision"],
    "cv": ["cv", "computer vision"],
    "javascript": ["js", "javascript"],
    "js": ["js", "javascript"],
    "typescript": ["ts", "typescript"],
    "ts": ["ts", "typescript"],
    "python": ["python", "py"],
    "generative ai": ["genai", "generative ai", "llm", "large language model"],
    "genai": ["genai", "generative ai", "llm", "large language model"],
    "llm": ["llm", "large language model", "genai", "generative ai"],
    "large language model": ["llm", "large language model", "genai", "generative ai"],
    "rag": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "sql": ["sql", "mysql", "postgresql", "sqlite", "postgres"],
    "mysql": ["sql", "mysql"],
    "postgresql": ["sql", "postgresql", "postgres"],
}


def _normalise(skill: str) -> str:
    return skill.strip().lower()


def _skill_matches(required_skill: str, candidate_skills_lower: set[str]) -> bool:
    """Return True if the required skill (or any of its synonyms) appears in candidate skills."""
    req = _normalise(required_skill)

    # Direct match
    if req in candidate_skills_lower:
        return True

    # Substring match — "tensorflow" matches "tensorflow/keras"
    for cs in candidate_skills_lower:
        if req in cs or cs in req:
            return True

    # Synonym match
    synonyms = _SKILL_SYNONYMS.get(req, [])
    for syn in synonyms:
        if syn in candidate_skills_lower:
            return True
        for cs in candidate_skills_lower:
            if syn in cs or cs in syn:
                return True

    return False


def skill_coverage_score(required: list, candidate: list) -> float:
    """Fraction of required skills matched by the candidate (fuzzy + synonym aware)."""
    if not required:
        return 1.0
    candidate_lower = {_normalise(s) for s in candidate}
    matched = sum(1 for req in required if _skill_matches(req, candidate_lower))
    return matched / len(required)


def experience_alignment(exp_years: float, level: str) -> float:
    """
    Score how well the candidate's experience matches the required level.
    Fresher candidates are not penalised for junior/mid roles — they just score
    proportionally rather than getting a hard 0.
    """
    if level == "fresher":
        # Perfect for 0-1 yr; slight penalty for over-qualified
        return 1.0 if exp_years <= 2 else 0.7

    if level == "junior":
        # 0-3 years is fine; internships (0.5 each) count
        if exp_years == 0:
            return 0.5          # No experience at all — uncertain
        return min(exp_years / 2, 1.0)

    if level == "mid":
        if exp_years == 0:
            return 0.3
        return min(exp_years / 3, 1.0)

    if level == "senior":
        if exp_years == 0:
            return 0.1
        return min(exp_years / 6, 1.0)

    return 0.5                  # unknown level — neutral


def role_alignment_score(jd_role: str, candidate_role: str) -> float:
    """Broader role compatibility including partial matches."""
    jd = jd_role.lower().strip()
    cand = candidate_role.lower().strip()

    # Exact / substring match
    if jd in cand or cand in jd:
        return 1.0

    # Compatible role groups
    compatible_groups = [
        {"data scientist", "ml engineer", "data engineer", "ai engineer"},
        {"backend engineer", "software engineer", "fullstack engineer"},
        {"frontend engineer", "fullstack engineer"},
        {"devops engineer", "cloud engineer", "platform engineer"},
    ]
    for group in compatible_groups:
        if jd in group and cand in group:
            return 0.8

    # Partial word overlap (e.g. "data scientist" vs "data analyst")
    jd_words = set(jd.split())
    cand_words = set(cand.split())
    if jd_words & cand_words:
        return 0.6

    return 0.2


def institute_match_score(jd_text: str, resume_text: str) -> float:
    jd_lower = jd_text.lower()
    resume_lower = resume_text.lower()

    # Only penalise if JD explicitly requires a tier-1 institute
    if "iit" in jd_lower or "nit" in jd_lower:
        return 1.0 if ("iit" in resume_lower or "nit" in resume_lower) else 0.4
    return 1.0


def projects_bonus(has_projects: bool, exp_years: float) -> float:
    """
    Give a small bonus for candidates with projects — especially important
    for freshers/juniors who compensate with side-projects.
    """
    if has_projects and exp_years < 2:
        return 0.15     # Bonus capped at 15 points
    if has_projects:
        return 0.05
    return 0.0


# ---------------------------------------------------------------------------
# Main screening entry point
# ---------------------------------------------------------------------------

def screen_candidate(jd_text: str, resume_text: str, threshold: float | None = None):
    threshold = threshold if threshold is not None else settings.default_score_threshold

    hiring_intent = extract_hiring_intent(jd_text)
    candidate = extract_candidate_profile(resume_text)

    # Semantic similarity (embeddings)
    jd_vec = embeddings.embed_query(jd_text)
    resume_vec = embeddings.embed_query(resume_text)
    semantic_fit = float(cosine_similarity([jd_vec], [resume_vec])[0][0])

    # Component scores
    role_align = role_alignment_score(hiring_intent["role"], candidate["primary_role"])

    # Pool ALL candidate skills for must-have matching (primary + secondary)
    all_candidate_skills = candidate["primary_skills"] + candidate["secondary_skills"]
    must_skill_score = skill_coverage_score(hiring_intent["must_have_skills"], all_candidate_skills)
    nice_skill_score = skill_coverage_score(hiring_intent["nice_to_have_skills"], all_candidate_skills)

    exp_score = experience_alignment(candidate["experience_years"], hiring_intent["experience_level"])
    institute_score = institute_match_score(jd_text, resume_text)
    proj_bonus = projects_bonus(candidate.get("has_projects", False), candidate["experience_years"])

    # Weighted formula
    raw_score = (
        0.30 * semantic_fit
        + 0.20 * role_align
        + 0.25 * must_skill_score       # bumped: skills matter most
        + 0.10 * nice_skill_score
        + 0.10 * exp_score
        + 0.05 * institute_score
    )

    # Apply project bonus (additive, max +15 pts before scaling)
    raw_score = min(raw_score + proj_bonus * raw_score, 1.0)

    final_score = round(raw_score * 100, 2)
    decision = "SHORTLIST" if final_score >= threshold else "REJECT"

    logger.info(
        "Screening done | score=%.1f | decision=%s | role_align=%.2f | "
        "must_skill=%.2f | exp=%.2f | semantic=%.2f",
        final_score, decision, role_align, must_skill_score, exp_score, semantic_fit,
    )

    return {
        "score": final_score,
        "decision": decision,
        "breakdown": {
            "semantic_fit": round(semantic_fit * 100, 2),
            "role_alignment": round(role_align * 100, 2),
            "must_skill_match": round(must_skill_score * 100, 2),
            "nice_skill_match": round(nice_skill_score * 100, 2),
            "experience_alignment": round(exp_score * 100, 2),
            "institute_match": round(institute_score * 100, 2),
            "project_bonus_applied": round(proj_bonus * 100, 1),
        },
        "hiring_intent": hiring_intent,
        "candidate_profile": candidate,
    }
