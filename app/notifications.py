"""
Email delivery for the reminders digest.

Works with ANY SMTP provider — Gmail (with an app password), SendGrid, Mailgun,
Amazon SES, your own mail server — nothing here is tied to one vendor's API/OAuth.
That's the tradeoff vs a Gmail/Outlook API integration: you lose "read the recruiter's
actual reply," you gain "works today with a password in .env."

Required environment variables (put these in your .env, never commit them):
    SMTP_HOST       e.g. smtp.gmail.com
    SMTP_PORT       e.g. 587
    SMTP_USER       the account that sends the digest
    SMTP_PASSWORD   an app password (NOT your real Gmail password — generate one at
                     https://myaccount.google.com/apppasswords) or provider API key
    SMTP_FROM       optional, e.g. "Career Copilot <you@yourdomain.com>" — defaults to SMTP_USER

Digest emails go to each user's account email (models.User.email) — no separate
"notification email" field needed unless you want one later.
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

import models
from reminders import compute_reminders

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def _send_email(to: str, subject: str, html_body: str) -> None:
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD]):
        raise RuntimeError(
            "SMTP not configured — set SMTP_HOST, SMTP_USER, SMTP_PASSWORD (and optionally "
            "SMTP_FROM) in your .env before sending digests."
        )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to], msg.as_string())


def _list_html(apps: list[dict], empty_message: str) -> str:
    if not apps:
        return f"<p style='color:#888;margin:4px 0 16px'>{empty_message}</p>"
    items = []
    for a in apps:
        extra = ""
        if a.get("oa_deadline"):
            extra = f" — OA due {a['oa_deadline']}"
        elif a.get("interview_date"):
            extra = f" — interview {a['interview_date']}"
        elif a.get("days_since_applied") is not None:
            extra = f" — applied {a['days_since_applied']} days ago, no update since"
        items.append(f"<li><b>{a['company']}</b> — {a['role']}{extra}</li>")
    return f"<ul style='margin:4px 0 16px'>{''.join(items)}</ul>"


def _build_digest_html(reminders: dict) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:520px">
      <h2 style="margin-bottom:4px">Your Career Copilot digest</h2>
      <h3 style="margin-bottom:0">Gone quiet (Applied, no update in 7+ days)</h3>
      {_list_html(reminders['stale_applications'], "Nothing stale right now.")}
      <h3 style="margin-bottom:0">OA deadlines coming up</h3>
      {_list_html(reminders['upcoming_oa_deadlines'], "None in the next few days.")}
      <h3 style="margin-bottom:0">Interviews coming up</h3>
      {_list_html(reminders['upcoming_interviews'], "None scheduled soon.")}
    </div>
    """


def send_reminder_digest(db: Session, user: models.User, lookahead_days: int = 3) -> bool:
    """Computes this user's reminders and emails them a digest.
    Returns False (and sends nothing) if there's genuinely nothing to report —
    so a quiet week doesn't mean a daily empty email."""
    reminders = compute_reminders(db, user.id, lookahead_days=lookahead_days)
    if not any(reminders.values()):
        return False
    html = _build_digest_html(reminders)
    _send_email(user.email, "Your Career Copilot digest", html)
    return True


def send_digest_to_all_users(db: Session, lookahead_days: int = 3) -> dict:
    """Runs across every registered user — this is what the scheduler calls daily."""
    sent, skipped, failed = [], [], []
    for user in db.query(models.User).all():
        try:
            if send_reminder_digest(db, user, lookahead_days=lookahead_days):
                sent.append(user.email)
            else:
                skipped.append(user.email)
        except Exception as e:
            failed.append({"email": user.email, "error": str(e)})
    return {"sent": sent, "skipped_empty": skipped, "failed": failed}