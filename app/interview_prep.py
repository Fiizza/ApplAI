from parser import client, GEMINI_MODEL  # reuse the same Gemini client/key already configured

INTERVIEW_PROMPT = """You are a senior technical recruiter helping a candidate prepare for an interview.

Job:
- Role: {role}
- Company: {company}
- Requirements: {requirements}

Candidate's skills that genuinely match this job: {matched_skills}
Candidate's gaps for this job (things they don't have yet): {missing_skills}

Generate interview prep as ONLY valid JSON in this exact shape:
{{
  "questions": ["...", "...", "..."],
  "talking_points": ["...", "...", "..."],
  "reasoning": "..."
}}

Rules:
- "questions": 6-8 realistic interview questions this candidate would likely be asked for this
  specific role — mix behavioral and role-specific/technical, grounded in the actual requirements
  above (not generic "tell me about yourself" filler).
- "talking_points": 3-5 short bullet reminders of how the candidate should frame their matched
  skills as concrete answers (e.g. "Mention your Docker experience when asked about deployment —
  tie it to a specific project if you can"). Also include one bullet on how to honestly address
  the biggest gap from missing_skills without underselling yourself.
- "reasoning": 2-3 sentences explaining WHY these particular questions were chosen for this role
  (e.g. which requirements or seniority signals drove them), so the candidate understands the
  logic, not just the output.
- No preamble, no markdown fences, ONLY the JSON object."""


def generate_prep(role: str, company: str, requirements: list[str],
                   matched_skills: list[str], missing_skills: list[str]) -> dict:
    prompt = INTERVIEW_PROMPT.format(
        role=role,
        company=company,
        requirements=", ".join(requirements) if requirements else "not specified",
        matched_skills=", ".join(matched_skills) if matched_skills else "none identified yet",
        missing_skills=", ".join(missing_skills) if missing_skills else "none identified",
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    import json
    return json.loads(result)