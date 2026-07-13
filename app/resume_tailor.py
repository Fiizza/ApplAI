from parser import client, GEMINI_MODEL  # reuse the same Gemini client already configured

TAILOR_PROMPT = """You are an ATS (Applicant Tracking System) resume optimization expert.

You will rewrite the candidate's resume below to score better against ATS keyword scanning \
for one specific job. Follow these rules strictly:

1. Do NOT invent skills, tools, job titles, employers, or experience that are not already \
   present in the original resume. Only reword, reorder, and re-emphasize what's already there.
2. Where the candidate's existing experience genuinely overlaps with the job's language, mirror \
   the job posting's exact terminology (e.g. if the resume says "built REST services" and the job \
   says "REST API development", rewrite it as "REST API development").
3. Reorder bullet points and the skills section so the most job-relevant items appear first.
4. Use simple, single-column, plain-text formatting — no tables, columns, icons, or graphics \
   (ATS parsers often fail on those).
5. Keep every section the original resume had (don't drop education/experience entries).
6. At the end, add a line: "NOTE: skills below are only what appeared in your original resume — \
   nothing was added." followed by a short bullet list of job-requested skills that were NOT \
   found anywhere in the original resume, so the candidate knows what's genuinely missing.

Job:
- Role: {role}
- Company: {company}
- Requirements: {requirements}
- Key skills wanted: {key_skills}

Candidate's original resume:
---
{resume_text}
---

Return the tailored resume as plain text, followed by the NOTE section described in rule 6."""


def tailor_resume(resume_text: str, role: str, company: str, requirements: list[str], key_skills: list[str]) -> str:
    prompt = TAILOR_PROMPT.format(
        role=role,
        company=company,
        requirements=", ".join(requirements) if requirements else "not specified",
        key_skills=", ".join(key_skills) if key_skills else "not specified",
        resume_text=resume_text,
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip()