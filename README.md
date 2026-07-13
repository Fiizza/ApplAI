# Job Application Tracker — Day 1

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # then paste your ANTHROPIC_API_KEY into .env
uvicorn app.main:app --reload
```
The app reads `.env` automatically on startup — no need to export the key manually.
Server runs at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

## Test it (real job postings)

**1. Parse a job description (doesn't save it yet):**
```bash
curl -X POST http://localhost:8000/parse-job \
  -H "Content-Type: application/json" \
  -d '{"raw_text": "Paste a real job description here..."}'
```
Or with a URL instead of raw_text: `{"job_url": "https://..."}`

**2. Save it to the tracker** (use the parsed output as the body, filling in company/role):
```bash
curl -X POST http://localhost:8000/applications \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Acme Corp",
    "role": "Backend Engineer",
    "requirements": ["3+ years Python", "Docker experience"],
    "key_skills": ["Python", "Docker", "PostgreSQL"],
    "location": "Remote",
    "employment_type": "Full-time",
    "seniority": "Mid"
  }'
```

**3. List everything you're tracking:**
```bash
curl http://localhost:8000/applications
```

**4. Update status once you hear back:**
```bash
curl -X PATCH http://localhost:8000/applications/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "Interview"}'
```

**5. Preview of Day 2's follow-up reminder** — apps still "Applied" after N days:
```bash
curl http://localhost:8000/applications/stale/7
```

**6. Seed your skill set** (this is what Day 2's match % will compare jobs against):
```bash
curl -X POST http://localhost:8000/skills/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {"name": "Python", "category": "Language", "proficiency": "Expert", "years_experience": 3},
    {"name": "Docker", "category": "DevOps", "proficiency": "Intermediate", "years_experience": 1},
    {"name": "FastAPI", "category": "Framework", "proficiency": "Intermediate"}
  ]'
```
Or add one at a time via `POST /skills`. List them with `GET /skills`, edit with `PATCH /skills/{id}`.

## What's built (Day 1 + Day 2)

**Day 1**
- SQLite tables (`tracker.db`, auto-created on first run): `applications`, `skills`
- `/parse-job`: pastes a URL or raw text → Gemini extracts company, role, requirements,
  key skills, location, seniority, employment type as structured JSON
- Full CRUD for the tracker (`/applications`) and your skill set (`/skills`, `/skills/bulk`)

**Day 2**
- `GET /applications/{id}/match` — compares the job's `key_skills` against your `skills`
  table → `match_percentage`, `matched_skills`, `missing_skills` (the gaps)
- `POST /applications/{id}/cover-letter` — drafts a tailored 2-3 sentence opener using
  the job's requirements + your matched skills (no generic filler, grounded in real overlap)
- Every application returned from `/applications` now includes `days_since_applied` and
  `needs_followup` (true once a job is still "Applied" after 7+ days with no status change —
  change `FOLLOWUP_THRESHOLD_DAYS` in `main.py` to adjust)

### Test Day 2
```bash
# 1. Match a saved application against your skills
curl http://localhost:8000/applications/1/match

# 2. Generate a cover letter opener for it
curl -X POST http://localhost:8000/applications/1/cover-letter

# 3. See which applications need a follow-up right now
curl http://localhost:8000/applications | python3 -m json.tool
# look for "needs_followup": true
```

## What's next (Day 3)
- React dashboard: kanban view (Applied → Interview → Offer/Rejected) with match score per job
- Chat-style input: paste a job description, everything happens automatically end-to-end
- Polish the gap explanation UI for the demo
