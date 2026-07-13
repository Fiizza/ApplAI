from .parser import client, GEMINI_MODEL  # reuse the same Gemini client/key already configured

RECOMMENDATION_PROMPT = """A job candidate is missing the following skills for a "{role}" role: {missing_skills}

For EACH missing skill, return ONLY valid JSON — a list of objects in this exact shape:
[
  {{
    "skill": "...",
    "why_it_matters": "one sentence on why this specific role cares about this skill",
    "suggested_topics": ["2-4 concrete sub-topics or concepts to study, not brand names or links"]
  }}
]

Rules:
- Do NOT invent or recommend specific paid courses, book titles, or URLs — you might hallucinate
  ones that don't exist. Stick to topic/concept names the candidate can search for themselves
  (e.g. "Docker Compose fundamentals", "REST vs GraphQL tradeoffs").
- Keep "why_it_matters" grounded in the role, not generic.
- No preamble, no markdown fences, ONLY the JSON array."""


def generate_recommendations(role: str, missing_skills: list[str]) -> list[dict]:
    if not missing_skills:
        return []
    prompt = RECOMMENDATION_PROMPT.format(
        role=role,
        missing_skills=", ".join(missing_skills),
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    result = response.text.strip().replace("```json", "").replace("```", "").strip()
    import json
    return json.loads(result)