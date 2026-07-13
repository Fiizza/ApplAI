"""
Reads recent Gmail messages (read-only), matches each one to a tracked application,
and asks Gemini to summarize it and flag what kind of update it is. Nothing here
modifies, sends, or deletes anything in the connected inbox.
"""
import json
import logging
from datetime import datetime

from googleapiclient.discovery import build
from sqlalchemy.orm import Session

import models
from gmail_auth import get_valid_credentials
from parser import client as gemini_client, GEMINI_MODEL

logger = logging.getLogger("gmail_sync")

MAX_MESSAGES_PER_SYNC = 25
SEARCH_QUERY = (
    "newer_than:30d "
    '(interview OR assessment OR "online assessment" OR offer OR reject '
    "OR recruiting OR recruiter OR application OR candidacy)"
)

# Automated "jobs you might like" senders. These are recommendation digests, not
# real recruiter/application updates — they get excluded before ever reaching the
# LLM classifier so they can't be mistaken for a genuine signal on a tracked application.
AUTOMATED_JOB_ALERT_SENDERS = (
    # LinkedIn — multiple sending addresses used for digests/recommendations
    "jobs-noreply@linkedin.com",
    "jobalerts-noreply@linkedin.com",
    "notifications@linkedin.com",
    "messages-noreply@linkedin.com",
    "inmail-hit-reply@linkedin.com",
    # Indeed
    "jobalerts@indeed.com",
    "alert@indeed.com",
    "noreply@indeed.com",
    # Glassdoor
    "noreply@glassdoor.com",
    "alerts@glassdoor.com",
    # ZipRecruiter
    "donotreply@ziprecruiter.com",
    "noreply@ziprecruiter.com",
    # Rozee / local Pakistani job boards
    "no-reply@rozee.pk",
    "noreply@rozee.pk",
    "alerts@rozee.pk",
)

# Keywords that appear in Gemini's own summary when it correctly identifies
# a job-alert email but mistakenly returns detected_signal="other".
# Catching these here closes the filter gap without touching the LLM prompt.
JOB_ALERT_SUMMARY_KEYWORDS = (
    "job alert",
    "jobs you might like",
    "recommended job",
    "job recommendation",
    "open position",
    "new jobs for you",
    "jobs matching",
    "linkedin job alert",
    "indeed alert",
)


def _is_automated_job_alert(sender: str) -> bool:
    sender_lower = sender.lower()
    return any(addr in sender_lower for addr in AUTOMATED_JOB_ALERT_SENDERS)


def _summary_looks_like_job_alert(summary: str) -> bool:
    """Catches cases where Gemini correctly describes a job alert in the summary text
    but returns detected_signal='other' instead of 'job_alert' — closing the filter gap."""
    summary_lower = (summary or "").lower()
    return any(kw in summary_lower for kw in JOB_ALERT_SUMMARY_KEYWORDS)

MATCH_PROMPT = """You are triaging a job applicant's inbox against their tracked applications.

Email:
- From: {sender}
- Subject: {subject}
- Snippet: {snippet}

Candidate's tracked applications (id, company, role, recruiter email if known):
{applications}

Decide which application (if any) this email is about, and summarize it in plain language.
Return ONLY valid JSON in this exact shape, no markdown fences:
{{
  "application_id": <id or null>,
  "summary": "1-2 plain-language sentences on what this email actually says",
  "detected_signal": "one of: interview_invite, rejection, oa_invite, offer, other, not_job_related, job_alert",
  "suggested_action": "one short concrete next step, or null if none needed"
}}

Rules:
- Only match to an application if the company or recruiter genuinely lines up — don't force a match.
- If this isn't job-search related at all, set application_id to null and detected_signal to "not_job_related".
- If this is an automated "jobs you might like" / recommended-openings digest (LinkedIn, Indeed,
  Glassdoor, ZipRecruiter, etc.) rather than a real update on an application the candidate actually
  submitted, set application_id to null and detected_signal to "job_alert". This is noise, not a
  genuine recruiter/application signal, even though it mentions real job titles and companies.
- No preamble, ONLY the JSON object."""


def _get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _classify_email(sender: str, subject: str, snippet: str, applications: list[models.Application]) -> dict:
    app_lines = "\n".join(
        f"- id={a.id}, company={a.company}, role={a.role}, recruiter_email={a.recruiter_email or 'unknown'}"
        for a in applications
    ) or "(none tracked yet)"

    prompt = MATCH_PROMPT.format(sender=sender, subject=subject, snippet=snippet, applications=app_lines)
    response = gemini_client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    raw = response.text
    result = raw.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        logger.warning(
            "gmail_sync: failed to parse Gemini response as JSON for subject=%r. Raw response: %r",
            subject, raw,
        )
        raise


def sync_gmail_for_user(db: Session, user: models.User) -> dict:
    """Pulls recent likely-job-related emails, classifies each one, and stores new
    EmailSummary rows. Safe to call repeatedly — already-seen message IDs are skipped."""
    account = db.query(models.EmailAccount).filter(models.EmailAccount.owner_id == user.id).first()
    if not account:
        raise ValueError("No Gmail account connected — call GET /auth/gmail/connect first")

    creds = get_valid_credentials(account)
    # google-auth may have silently rotated the access token during refresh — persist it
    account.access_token = creds.token
    if creds.expiry:
        account.token_expiry = creds.expiry

    service = build("gmail", "v1", credentials=creds)

    already_seen = {
        row.gmail_message_id
        for row in db.query(models.EmailSummary.gmail_message_id)
        .filter(models.EmailSummary.owner_id == user.id)
        .all()
    }
    applications = db.query(models.Application).filter(models.Application.owner_id == user.id).all()

    msg_list = service.users().messages().list(
        userId="me", q=SEARCH_QUERY, maxResults=MAX_MESSAGES_PER_SYNC
    ).execute()
    message_ids = [m["id"] for m in msg_list.get("messages", [])]
    logger.info(
        "gmail_sync: user=%s query=%r returned %d message(s) from Gmail; %d already seen in DB",
        user.id, SEARCH_QUERY, len(message_ids), len(already_seen & set(message_ids)),
    )

    new_summaries = []
    matched = 0
    unmatched = 0

    for msg_id in message_ids:
        if msg_id in already_seen:
            continue

        full = service.users().messages().get(
            userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = full.get("payload", {}).get("headers", [])
        sender = _get_header(headers, "From")
        subject = _get_header(headers, "Subject")
        snippet = full.get("snippet", "")

        if _is_automated_job_alert(sender):
            logger.info("gmail_sync: skipping msg=%s sender=%r — matched automated job-alert sender list", msg_id, sender)
            continue  # known "jobs you might like" digest sender — skip before spending an LLM call on it

        try:
            classification = _classify_email(sender, subject, snippet, applications)
        except Exception:
            logger.exception("gmail_sync: skipping msg=%s subject=%r — classification failed", msg_id, subject)
            continue  # skip anything the model returned unparseable JSON for, rather than crash the whole sync

        signal = classification.get("detected_signal")
        if signal in ("not_job_related", "job_alert"):
            logger.info("gmail_sync: skipping msg=%s subject=%r — detected_signal=%r", msg_id, subject, signal)
            continue  # don't clutter the table with irrelevant mail or automated job recommendations

        # Second-pass guard: Gemini sometimes labels a job alert as "other" but still
        # writes "This is a LinkedIn Job Alert..." in the summary. Catch it here.
        if _summary_looks_like_job_alert(classification.get("summary", "")):
            logger.info("gmail_sync: skipping msg=%s subject=%r — summary matched job-alert keywords despite signal=%r", msg_id, subject, signal)
            continue

        logger.info(
            "gmail_sync: storing msg=%s subject=%r signal=%r application_id=%s",
            msg_id, subject, signal, classification.get("application_id"),
        )

        row = models.EmailSummary(
            owner_id=user.id,
            application_id=classification.get("application_id"),
            gmail_message_id=msg_id,
            sender=sender,
            subject=subject,
            received_at=datetime.utcnow(),
            summary=classification.get("summary"),
            detected_signal=classification.get("detected_signal"),
            suggested_action=classification.get("suggested_action"),
        )
        db.add(row)
        new_summaries.append(row)
        matched += 1 if row.application_id else 0
        unmatched += 0 if row.application_id else 1

    account.last_synced_at = datetime.utcnow()
    db.commit()
    for row in new_summaries:
        db.refresh(row)

    logger.info(
        "gmail_sync: finished for user=%s — %d new, %d matched, %d unmatched",
        user.id, len(new_summaries), matched, unmatched,
    )

    return {
        "new_emails_found": len(new_summaries),
        "matched_to_applications": matched,
        "unmatched": unmatched,
        "summaries": new_summaries,
    }