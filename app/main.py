import json
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.discovery import build as gmail_build

import models, schemas, parser, matching, cover_letter, resume_tailor, auth
import interview_prep, followup_email, learning_recommendations, notifications
import gmail_auth, gmail_sync
from reminders import compute_reminders, _row_to_out, FOLLOWUP_THRESHOLD_DAYS
from database import engine, get_db, Base, SessionLocal
from resume_pdf import extract_pdf_text

Base.metadata.create_all(bind=engine)

DIGEST_HOUR_UTC = 13       # ~8-9am US Eastern; change to taste, or move to an env var
GMAIL_SYNC_HOUR_UTC = 12   # runs an hour before the digest so new emails can inform it
scheduler = BackgroundScheduler()


def _run_daily_digest():
    """Scheduler entrypoint — needs its own DB session since it runs outside any request."""
    db = SessionLocal()
    try:
        result = notifications.send_digest_to_all_users(db)
        print(f"[digest] sent={len(result['sent'])} skipped={len(result['skipped_empty'])} failed={len(result['failed'])}")
    finally:
        db.close()


def _run_daily_gmail_sync():
    """Syncs every connected Gmail account. One account failing (expired refresh token,
    API hiccup, etc.) never blocks the others."""
    db = SessionLocal()
    try:
        accounts = db.query(models.EmailAccount).all()
        for account in accounts:
            user = db.query(models.User).filter(models.User.id == account.owner_id).first()
            if not user:
                continue
            try:
                result = gmail_sync.sync_gmail_for_user(db, user)
                print(f"[gmail-sync] {user.email}: {result['new_emails_found']} new")
            except Exception as e:
                print(f"[gmail-sync] failed for {user.email}: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(_run_daily_gmail_sync, "cron", hour=GMAIL_SYNC_HOUR_UTC, id="daily_gmail_sync", replace_existing=True)
    scheduler.add_job(_run_daily_digest, "cron", hour=DIGEST_HOUR_UTC, id="daily_digest", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="AI Career Copilot", lifespan=lifespan)

# Enable CORS for frontend.
# allow_origin_regex catches ANY localhost/127.0.0.1 port so you stop getting
# silent "Failed to fetch" errors every time your dev server picks a new port
# (Vite does this automatically when 5173 is busy).
#
# In production, set FRONTEND_URL in Vercel (e.g. https://applai.vercel.app) so
# your deployed frontend isn't blocked by CORS. Comma-separate multiple values
# (e.g. a custom domain + the vercel.app preview URL) if needed.
_extra_origins = [o.strip() for o in os.getenv("FRONTEND_URL", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:8080", *_extra_origins],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_application_or_404(app_id: int, db: Session, owner_id: int) -> models.Application:
    row = (
        db.query(models.Application)
        .filter(models.Application.id == app_id, models.Application.owner_id == owner_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Application not found")
    return row


def _match_for(row: models.Application, db: Session) -> dict:
    job_skills = json.loads(row.key_skills) if row.key_skills else []
    user_skills = [
        s.name for s in db.query(models.Skill).filter(models.Skill.owner_id == row.owner_id).all()
    ]
    if not job_skills or not user_skills:
        return {"match_percentage": 0, "matched_skills": [], "missing_skills": job_skills}
    return matching.match_skills(job_skills, user_skills)


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Serverless-safe cron triggers ---
# On Vercel, functions are ephemeral: there's no long-running process, so the
# APScheduler background jobs above (daily_gmail_sync / daily_digest) will NOT
# reliably fire in production the way they do when you run `uvicorn` locally.
# These two endpoints let an external scheduler (Vercel Cron Jobs, or a free
# pinger like cron-job.org) trigger the same logic on a schedule instead.
# Set CRON_SECRET in Vercel's env vars and pass it as ?secret=... when calling.
CRON_SECRET = os.getenv("CRON_SECRET", "")


@app.post("/cron/gmail-sync")
def cron_gmail_sync(secret: str = ""):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    _run_daily_gmail_sync()
    return {"status": "triggered"}


@app.post("/cron/daily-digest")
def cron_daily_digest(secret: str = ""):
    if not CRON_SECRET or secret != CRON_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    _run_daily_digest()
    return {"status": "triggered"}


### --- Auth --- ###

@app.post("/auth/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email.ilike(payload.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with that email already exists")
    user = models.User(email=payload.email, hashed_password=auth.hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow — form fields are 'username' (use your email) and 'password'.
    Swagger's /docs 'Authorize' button uses this shape natively."""
    user = db.query(models.User).filter(models.User.email.ilike(form_data.username)).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = auth.create_access_token(user.id)
    return schemas.Token(access_token=token)


@app.get("/auth/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@app.post("/parse-job", response_model=schemas.ParsedJobData)
def parse_job(payload: schemas.ParseJobRequest, current_user: models.User = Depends(auth.get_current_user)):
    """Extract structured data from a job posting URL or pasted text (does NOT save it)."""
    try:
        data = parser.parse_job(payload.job_url, payload.raw_text)
        return schemas.ParsedJobData(**data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/applications", response_model=schemas.ApplicationOut)
def create_application(
    payload: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Save a tracked application — typically called after /parse-job with the extracted data."""
    row = models.Application(
        owner_id=current_user.id,
        company=payload.company,
        role=payload.role,
        job_url=payload.job_url,
        raw_description=payload.raw_description,
        requirements=json.dumps(payload.requirements or []),
        key_skills=json.dumps(payload.key_skills or []),
        location=payload.location,
        employment_type=payload.employment_type,
        seniority=payload.seniority,
        notes=payload.notes,
        recruiter_name=payload.recruiter_name,
        recruiter_email=payload.recruiter_email,
        oa_deadline=payload.oa_deadline,
        interview_date=payload.interview_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@app.get("/applications", response_model=list[schemas.ApplicationOut])
def list_applications(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    rows = (
        db.query(models.Application)
        .filter(models.Application.owner_id == current_user.id)
        .order_by(models.Application.date_applied.desc())
        .all()
    )
    return [_row_to_out(r) for r in rows]


@app.get("/applications/{app_id}", response_model=schemas.ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    row = _get_application_or_404(app_id, db, current_user.id)
    return _row_to_out(row)


@app.patch("/applications/{app_id}", response_model=schemas.ApplicationOut)
def update_application(
    app_id: int,
    payload: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    row = _get_application_or_404(app_id, db, current_user.id)
    if payload.status is not None:
        row.status = payload.status
        row.last_status_update = datetime.utcnow()
    if payload.notes is not None:
        row.notes = payload.notes
    if payload.recruiter_name is not None:
        row.recruiter_name = payload.recruiter_name
    if payload.recruiter_email is not None:
        row.recruiter_email = payload.recruiter_email
    if payload.oa_deadline is not None:
        row.oa_deadline = payload.oa_deadline
    if payload.interview_date is not None:
        row.interview_date = payload.interview_date
    if payload.last_followup_sent_at is not None:
        row.last_followup_sent_at = payload.last_followup_sent_at
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@app.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    row = _get_application_or_404(app_id, db, current_user.id)
    db.delete(row)
    db.commit()
    return {"deleted": app_id}


### --- Day 2: matching + cover letter --- ###

@app.get("/applications/{app_id}/match", response_model=schemas.MatchResult)
def match_application(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Compare this job's key_skills against your stored skills -> match % + gaps."""
    row = _get_application_or_404(app_id, db, current_user.id)

    job_skills = json.loads(row.key_skills) if row.key_skills else []
    user_skills = [s.name for s in db.query(models.Skill).filter(models.Skill.owner_id == current_user.id).all()]

    if not user_skills:
        raise HTTPException(status_code=400, detail="No skills stored yet — add some via POST /skills first")

    result = matching.match_skills(job_skills, user_skills)
    return result


@app.post("/applications/{app_id}/cover-letter", response_model=schemas.CoverLetterResponse)
def generate_cover_letter(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Draft a tailored 2-3 sentence cover letter opener using this job's matched skills."""
    row = _get_application_or_404(app_id, db, current_user.id)

    requirements = json.loads(row.requirements) if row.requirements else []
    match_result = _match_for(row, db)

    result = cover_letter.generate_opener(
        role=row.role,
        company=row.company,
        requirements=requirements,
        matched_skills=match_result["matched_skills"],
    )
    return schemas.CoverLetterResponse(
        opener=result["opener"],
        matched_skills_used=match_result["matched_skills"],
        why_these_skills=result.get("why_these_skills"),
    )


### --- Resume (base resume storage + ATS tailoring per job) --- ###

@app.post("/resume", response_model=schemas.ResumeOut)
def save_resume(
    payload: schemas.ResumeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Upsert your base resume — only one is stored per user, this replaces it."""
    row = db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).first()
    if row:
        row.content = payload.content
    else:
        row = models.Resume(owner_id=current_user.id, content=payload.content)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post("/resume/upload", response_model=schemas.ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Upload your resume as a PDF file — text is extracted automatically and stored,
    replacing any previously saved resume for your account."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported here — use POST /resume for plain text")

    pdf_bytes = await file.read()
    try:
        text = extract_pdf_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {e}")

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No extractable text found — this PDF may be a scanned image rather than real text",
        )

    row = db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).first()
    if row:
        row.content = text
    else:
        row = models.Resume(owner_id=current_user.id, content=text)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/resume", response_model=schemas.ResumeOut)
def get_resume(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    row = db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).first()
    if not row:
        raise HTTPException(status_code=404, detail="No resume stored yet — POST /resume first")
    return row


@app.post("/applications/{app_id}/tailor-resume", response_model=schemas.TailoredResumeResponse)
def tailor_resume_for_job(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Rewrites your base resume for this specific job's ATS keywords. Never invents new skills —
    only rewords/reorders what's already in your stored resume."""
    application = _get_application_or_404(app_id, db, current_user.id)

    resume_row = db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).first()
    if not resume_row:
        raise HTTPException(status_code=400, detail="No resume stored yet — POST /resume first")

    requirements = json.loads(application.requirements) if application.requirements else []
    key_skills = json.loads(application.key_skills) if application.key_skills else []

    tailored = resume_tailor.tailor_resume(
        resume_text=resume_row.content,
        role=application.role,
        company=application.company,
        requirements=requirements,
        key_skills=key_skills,
    )

    # Save as a version so you keep a history instead of a one-off throwaway result
    version = models.ResumeVersion(
        owner_id=current_user.id,
        application_id=application.id,
        content=tailored,
    )
    db.add(version)
    db.commit()

    return schemas.TailoredResumeResponse(tailored_resume=tailored)


@app.get("/applications/{app_id}/resume-versions", response_model=list[schemas.ResumeVersionOut])
def list_resume_versions(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """History of every tailored resume generated for this application, newest first."""
    _get_application_or_404(app_id, db, current_user.id)  # 404s + ownership check
    return (
        db.query(models.ResumeVersion)
        .filter(models.ResumeVersion.application_id == app_id, models.ResumeVersion.owner_id == current_user.id)
        .order_by(models.ResumeVersion.created_at.desc())
        .all()
    )


### --- Career Copilot: interview prep, follow-up emails, learning recs --- ###

@app.post("/applications/{app_id}/interview-prep", response_model=schemas.InterviewPrepResponse)
def interview_prep_for_job(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Generate likely interview questions + talking points for this job, grounded in the
    job's requirements and how your matched/missing skills line up against them."""
    row = _get_application_or_404(app_id, db, current_user.id)
    requirements = json.loads(row.requirements) if row.requirements else []
    match_result = _match_for(row, db)

    result = interview_prep.generate_prep(
        role=row.role,
        company=row.company,
        requirements=requirements,
        matched_skills=match_result["matched_skills"],
        missing_skills=match_result["missing_skills"],
    )
    return schemas.InterviewPrepResponse(**result)


@app.post("/applications/{app_id}/follow-up-email", response_model=schemas.FollowUpEmailResponse)
def follow_up_email_for_job(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Draft a short follow-up email for this application, aware of its current status
    and how many days it's been sitting since you applied."""
    row = _get_application_or_404(app_id, db, current_user.id)
    days_since = (datetime.utcnow() - row.date_applied).days if row.date_applied else None

    result = followup_email.generate_followup(
        role=row.role,
        company=row.company,
        status=row.status,
        days_since_applied=days_since,
    )
    return schemas.FollowUpEmailResponse(**result)


@app.get("/applications/{app_id}/learning-recommendations", response_model=schemas.LearningRecommendationsResponse)
def learning_recommendations_for_job(app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """For every skill this job wants that you don't have yet, suggest what to study
    (concepts/topics only — no hallucinated course names or links)."""
    row = _get_application_or_404(app_id, db, current_user.id)
    match_result = _match_for(row, db)

    if not match_result["missing_skills"]:
        return schemas.LearningRecommendationsResponse(recommendations=[])

    recs = learning_recommendations.generate_recommendations(
        role=row.role,
        missing_skills=match_result["missing_skills"],
    )
    return schemas.LearningRecommendationsResponse(recommendations=recs)


### --- Skills (your resume/reference skill set, lives in the same DB) --- ###

@app.post("/skills", response_model=schemas.SkillOut)
def add_skill(payload: schemas.SkillCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    existing = (
        db.query(models.Skill)
        .filter(models.Skill.owner_id == current_user.id, models.Skill.name.ilike(payload.name))
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Skill '{payload.name}' already exists")
    row = models.Skill(owner_id=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.post("/skills/bulk", response_model=list[schemas.SkillOut])
def add_skills_bulk(
    payload: list[schemas.SkillCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Seed your whole skill set in one call, e.g. from a resume you've already broken into a list."""
    created = []
    for skill in payload:
        existing = (
            db.query(models.Skill)
            .filter(models.Skill.owner_id == current_user.id, models.Skill.name.ilike(skill.name))
            .first()
        )
        if existing:
            continue  # skip duplicates rather than fail the whole batch
        row = models.Skill(owner_id=current_user.id, **skill.model_dump())
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


@app.get("/skills", response_model=list[schemas.SkillOut])
def list_skills(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.Skill)
        .filter(models.Skill.owner_id == current_user.id)
        .order_by(models.Skill.category, models.Skill.name)
        .all()
    )


@app.patch("/skills/{skill_id}", response_model=schemas.SkillOut)
def update_skill(
    skill_id: int,
    payload: schemas.SkillUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    row = (
        db.query(models.Skill)
        .filter(models.Skill.id == skill_id, models.Skill.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    row = (
        db.query(models.Skill)
        .filter(models.Skill.id == skill_id, models.Skill.owner_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(row)
    db.commit()
    return {"deleted": skill_id}


@app.get("/applications/stale/{days}", response_model=list[schemas.ApplicationOut])
def stale_applications(days: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Applications with status 'Applied' older than N days with no update."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(models.Application)
        .filter(models.Application.owner_id == current_user.id)
        .filter(models.Application.status == "Applied")
        .filter(models.Application.date_applied <= cutoff)
        .all()
    )
    return [_row_to_out(r) for r in rows]


@app.get("/reminders", response_model=schemas.RemindersResponse)
def get_reminders(
    lookahead_days: int = 3,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """One-stop dashboard feed: applications that have gone quiet, plus OA deadlines and
    interviews coming up within `lookahead_days`. Call this on app load to drive reminder banners.
    The same underlying data also goes out as a daily email — see POST /reminders/send-digest."""
    return schemas.RemindersResponse(**compute_reminders(db, current_user.id, lookahead_days))


@app.post("/reminders/send-digest")
def send_digest_now(
    lookahead_days: int = 3,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Manually trigger your own reminder digest email right now — useful for testing your
    SMTP setup without waiting for the daily scheduled run. Requires SMTP_HOST/USER/PASSWORD
    to be set in .env (see notifications.py)."""
    sent = notifications.send_reminder_digest(db, current_user, lookahead_days=lookahead_days)
    return {"sent": sent, "detail": "Digest sent" if sent else "Nothing to report — no email sent"}


### --- Gmail integration: recruiter email summaries --- ###

@app.get("/auth/gmail/connect", response_model=schemas.GmailAuthURLResponse)
def gmail_connect(current_user: models.User = Depends(auth.get_current_user)):
    """Returns a Google OAuth consent URL. Open it in a browser tab to connect Gmail with
    read-only access — used only to summarize recruiter emails, never to send or delete mail."""
    return schemas.GmailAuthURLResponse(auth_url=gmail_auth.build_auth_url(current_user.id))


@app.get("/auth/gmail/callback")
def gmail_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Google redirects here after the user grants consent. A browser redirect can't carry
    a Bearer token, so the user is identified via the signed `state` param instead (see
    gmail_auth.build_auth_url)."""
    try:
        user_id, code_verifier = gmail_auth.verify_state(state)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state — try connecting again")

    try:
        tokens = gmail_auth.exchange_code_for_tokens(code, code_verifier=code_verifier)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Google rejected the auth code exchange — check GOOGLE_CLIENT_ID/SECRET and "
                    f"GOOGLE_REDIRECT_URI match your OAuth client exactly. Error: {e}",
        )

    account = db.query(models.EmailAccount).filter(models.EmailAccount.owner_id == user_id).first()

    # Google only returns a refresh_token the FIRST time a user grants access. On a
    # reconnect it's often omitted — fall back to the one already stored instead of
    # crashing on a NOT NULL constraint.
    refresh_token = tokens.get("refresh_token") or (account.refresh_token if account else None)
    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google didn't return a refresh token, and none is on file for you yet. "
                "This usually happens when you've previously granted this app access. "
                "Go to https://myaccount.google.com/permissions, remove Career Copilot's "
                "access, then try connecting again."
            ),
        )

    try:
        creds = gmail_auth.credentials_from_tokens(tokens["access_token"], refresh_token)
        service = gmail_build("gmail", "v1", credentials=creds)
        email_address = service.users().getProfile(userId="me").execute()["emailAddress"]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not verify Gmail access: {e}")

    if account:
        account.email_address = email_address
        account.access_token = tokens["access_token"]
        account.refresh_token = refresh_token
        account.token_expiry = tokens["token_expiry"]
    else:
        account = models.EmailAccount(
            owner_id=user_id,
            email_address=email_address,
            access_token=tokens["access_token"],
            refresh_token=refresh_token,
            token_expiry=tokens["token_expiry"],
        )
        db.add(account)
    db.commit()

    # Configurable so this works for real deployed users, not just local dev.
    # Set FRONTEND_URL in .env (e.g. https://yourapp.com) — falls back to
    # localhost so nothing breaks for you today.
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=f"{frontend_url}/?gmail_connected=1")


@app.get("/email-account", response_model=schemas.EmailAccountOut)
def get_email_account(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    account = db.query(models.EmailAccount).filter(models.EmailAccount.owner_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="No Gmail account connected — see GET /auth/gmail/connect")
    return account


@app.delete("/email-account")
def disconnect_email_account(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    account = db.query(models.EmailAccount).filter(models.EmailAccount.owner_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=404, detail="No Gmail account connected")
    db.delete(account)
    db.commit()
    return {"disconnected": True}


@app.post("/gmail/sync", response_model=schemas.GmailSyncResponse)
def sync_gmail_now(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Manually pull and classify recent recruiter emails right now, instead of waiting
    for the daily scheduled sync. Safe to call repeatedly — already-seen emails are skipped."""
    try:
        return gmail_sync.sync_gmail_for_user(db, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/email-summaries", response_model=list[schemas.EmailSummaryOut])
def list_email_summaries(
    unmatched_only: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """All summarized recruiter emails across every application, newest first.
    Set unmatched_only=true to see emails that didn't match any tracked application
    (useful for catching a new company you forgot to log)."""
    q = db.query(models.EmailSummary).filter(models.EmailSummary.owner_id == current_user.id)
    if unmatched_only:
        q = q.filter(models.EmailSummary.application_id.is_(None))
    return q.order_by(models.EmailSummary.created_at.desc()).all()


@app.delete("/email-summaries/job-alerts")
def purge_job_alert_summaries(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """One-time cleanup: deletes any job-alert / recommendation emails that slipped
    through the sync filter before the sender blocklist and summary-keyword guard were added.
    Safe to call repeatedly — it only removes rows whose summary contains job-alert language."""
    from gmail_sync import JOB_ALERT_SUMMARY_KEYWORDS
    rows = (
        db.query(models.EmailSummary)
        .filter(models.EmailSummary.owner_id == current_user.id)
        .all()
    )
    deleted = 0
    for row in rows:
        summary_lower = (row.summary or "").lower()
        signal_is_alert = row.detected_signal in ("job_alert", "not_job_related")
        summary_is_alert = any(kw in summary_lower for kw in JOB_ALERT_SUMMARY_KEYWORDS)
        if signal_is_alert or summary_is_alert:
            db.delete(row)
            deleted += 1
    db.commit()
    return {"deleted": deleted}


@app.get("/applications/{app_id}/email-summaries", response_model=list[schemas.EmailSummaryOut])
def list_application_email_summaries(
    app_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
):
    """Every recruiter email matched to this specific application, newest first."""
    _get_application_or_404(app_id, db, current_user.id)  # 404s + ownership check
    return (
        db.query(models.EmailSummary)
        .filter(models.EmailSummary.application_id == app_id, models.EmailSummary.owner_id == current_user.id)
        .order_by(models.EmailSummary.created_at.desc())
        .all()
    )