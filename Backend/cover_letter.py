from .parser import client, GEMINI_MODEL  # reuse the same Gemini client/key already configured

OPENER_PROMPT = """You are helping a job applicant write the opening 2-3 sentences of a cover letter.
Write in first person, confident but not arrogant, no generic filler like "I am excited to apply."
Ground it in specific overlap between the candidate's real skills and the job's actual requirements.
Pick the 1-2 STRONGEST points of overlap rather than listing everything — specificity beats coverage.

Job:
- Role: {role}
- Company: {company}
- Key requirements: {requirements}

Candidate's matched skills (skills they genuinely have that this job wants): {matched_skills}

Return ONLY valid JSON in this exact shape, no markdown fences:
{{
  "opener": "the 2-3 sentence opener, first person, no 'Dear Hiring Manager', no sign-off",
  "why_these_skills": "one sentence explaining WHY you picked these particular skills to lead with over the others"
}}"""


def generate_opener(role: str, company: str, requirements: list[str], matched_skills: list[str]) -> dict:
    import json
    prompt = OPENER_PROMPT.format(
        role=role,
        company=company,
        requirements=", ".join(requirements) if requirements else "not specified",
        matched_skills=", ".join(matched_skills) if matched_skills else "general relevant background",
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(result)