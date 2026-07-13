from .parser import client, GEMINI_MODEL  # reuse the same Gemini client/key already configured

FOLLOWUP_PROMPT = """You are helping a job applicant write a short, polite follow-up email.

Context:
- Role: {role}
- Company: {company}
- Current status: {status}
- Days since they applied: {days_since_applied}

Write a brief, professional follow-up email checking in on their application. Keep it under
120 words, no groveling, no generic filler like "I hope this finds you well." Reaffirm interest
in one sentence grounded in the role, and ask a direct, low-pressure question about status/timeline.

Return ONLY valid JSON in this exact shape, no markdown fences:
{{
  "subject": "...",
  "body": "..."
}}"""


def generate_followup(role: str, company: str, status: str, days_since_applied) -> dict:
    prompt = FOLLOWUP_PROMPT.format(
        role=role,
        company=company,
        status=status,
        days_since_applied=days_since_applied if days_since_applied is not None else "unknown",
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    import json
    return json.loads(result)