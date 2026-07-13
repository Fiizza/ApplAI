"""
Pure logic, no LLM call needed — we already have both lists as data.
Matches are case-insensitive and allow simple substring matches
(e.g. job asks for "React.js", you have "React" -> still counts as a match).
"""


def _normalize(s: str) -> str:
    return s.strip().lower().replace(".js", "").replace(" ", "")


def match_skills(job_key_skills: list[str], user_skill_names: list[str]) -> dict:
    if not job_key_skills:
        return {
            "match_percentage": 0,
            "matched_skills": [],
            "missing_skills": [],
        }

    normalized_user = {_normalize(s): s for s in user_skill_names}

    matched = []
    missing = []

    for job_skill in job_key_skills:
        norm_job_skill = _normalize(job_skill)
        # exact match, or substring match either direction (handles "React" vs "React.js", "SQL" vs "PostgreSQL")
        hit = None
        for norm_user_skill, original in normalized_user.items():
            if norm_job_skill == norm_user_skill or norm_job_skill in norm_user_skill or norm_user_skill in norm_job_skill:
                hit = original
                break
        if hit:
            matched.append(job_skill)
        else:
            missing.append(job_skill)

    match_percentage = round((len(matched) / len(job_key_skills)) * 100) if job_key_skills else 0

    return {
        "match_percentage": match_percentage,
        "matched_skills": matched,
        "missing_skills": missing,
    }