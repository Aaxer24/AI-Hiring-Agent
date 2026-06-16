from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import settings
from models.schemas import CandidateProfile, HiringIntent, parse_model, to_dict

embeddings = OpenAIEmbeddings(model=settings.openai_embedding_model)
llm = ChatOpenAI(model=settings.openai_chat_model, temperature=0)


def _dump_model(model):
    return to_dict(model)


def extract_hiring_intent(jd_text: str) -> dict:
    prompt = f"""
Extract hiring intent from the job description.

Return STRICT JSON:
{{
  "role": "data scientist / backend engineer / ml engineer / other",
  "must_have_skills": [],
  "nice_to_have_skills": [],
  "experience_level": "fresher / junior / mid / senior"
}}

JD:
{jd_text}
"""
    parsed = parse_model(HiringIntent, llm.invoke(prompt).content, HiringIntent())
    return _dump_model(parsed)


def extract_candidate_profile(resume_text: str) -> dict:
    prompt = f"""
Extract candidate profile.

Return STRICT JSON:
{{
  "primary_role": "data scientist / backend engineer / ml engineer / other",
  "primary_skills": [],
  "secondary_skills": [],
  "experience_years": 0,
  "has_projects": true
}}

Resume:
{resume_text}
"""
    parsed = parse_model(CandidateProfile, llm.invoke(prompt).content, CandidateProfile())
    return _dump_model(parsed)


def skill_coverage_score(required, candidate):
    if not required:
        return 1.0
    overlap = set(s.lower() for s in required) & set(s.lower() for s in candidate)
    return len(overlap) / len(required)


def experience_alignment(exp_years, level):
    if level == "fresher":
        return 1.0 if exp_years <= 1 else 0.6
    if level == "junior":
        return min(exp_years / 2, 1.0)
    if level == "mid":
        return min(exp_years / 4, 1.0)
    if level == "senior":
        return min(exp_years / 7, 1.0)
    return 0.5


def role_alignment_score(jd_role, candidate_role):
    jd_role = jd_role.lower()
    candidate_role = candidate_role.lower()

    if jd_role in candidate_role:
        return 1.0

    compatible_roles = {
        "data scientist": ["ml engineer", "data analyst"],
        "ml engineer": ["data scientist"],
        "backend engineer": ["software engineer"],
    }

    if jd_role in compatible_roles and candidate_role in compatible_roles[jd_role]:
        return 0.7

    return 0.2


def institute_match_score(jd_text, resume_text):
    jd_text = jd_text.lower()
    resume_text = resume_text.lower()

    if "iit" in jd_text or "nit" in jd_text:
        return 1.0 if "iit" in resume_text or "nit" in resume_text else 0.3
    return 1.0


def screen_candidate(jd_text: str, resume_text: str, threshold: float | None = None):
    threshold = threshold if threshold is not None else settings.default_score_threshold
    hiring_intent = extract_hiring_intent(jd_text)
    candidate = extract_candidate_profile(resume_text)

    jd_vec = embeddings.embed_query(jd_text)
    resume_vec = embeddings.embed_query(resume_text)
    semantic_fit = cosine_similarity([jd_vec], [resume_vec])[0][0]

    role_align = role_alignment_score(
        hiring_intent["role"],
        candidate["primary_role"],
    )
    must_skill_score = skill_coverage_score(
        hiring_intent["must_have_skills"],
        candidate["primary_skills"],
    )
    nice_skill_score = skill_coverage_score(
        hiring_intent["nice_to_have_skills"],
        candidate["secondary_skills"],
    )
    exp_score = experience_alignment(
        candidate["experience_years"],
        hiring_intent["experience_level"],
    )
    institute_score = institute_match_score(jd_text, resume_text)

    final_score = (
        0.30 * semantic_fit
        + 0.20 * role_align
        + 0.20 * must_skill_score
        + 0.10 * nice_skill_score
        + 0.10 * exp_score
        + 0.10 * institute_score
    )

    final_score = round(final_score * 100, 2)
    decision = "SHORTLIST" if final_score >= threshold else "REJECT"

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
        },
        "hiring_intent": hiring_intent,
        "candidate_profile": candidate,
    }
