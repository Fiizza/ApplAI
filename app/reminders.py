"""
Pure query logic for the reminders feed. Used by BOTH the /reminders API endpoint
and the background email digest (notifications.py) so the two can never drift apart —
fix a bug here once, both places get it.
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models

FOLLOWUP_THRESHOLD_DAYS = 7  # flag "Applied" jobs with no update after this many days


def _row_to_out(row: "models.Application") -> dict:
    d = row.__dict__.copy()
    d.pop("_sa_instance_state", None)
    d["requirements"] = json.loads(row.requirements) if row.requirements else []
    d["key_skills"] = json.loads(row.key_skills) if row.key_skills else []

    days_since = (datetime.utcnow() - row.date_applied).days if row.date_applied else None
    d["days_since_applied"] = days_since
    d["needs_followup"] = bool(
        row.status == "Applied" and days_since is not None and days_since >= FOLLOWUP_THRESHOLD_DAYS
    )
    return d


def compute_reminders(db: Session, owner_id: int, lookahead_days: int = 3) -> dict:
    """Returns stale applications + upcoming OA deadlines + upcoming interviews for one user,
    as plain dicts (already shaped to match schemas.ApplicationOut)."""
    now = datetime.utcnow()
    horizon = now + timedelta(days=lookahead_days)
    stale_cutoff = now - timedelta(days=FOLLOWUP_THRESHOLD_DAYS)

    base = db.query(models.Application).filter(models.Application.owner_id == owner_id)

    stale = (
        base.filter(models.Application.status == "Applied")
        .filter(models.Application.date_applied <= stale_cutoff)
        .all()
    )
    upcoming_oa = (
        base.filter(models.Application.oa_deadline.isnot(None))
        .filter(models.Application.oa_deadline >= now, models.Application.oa_deadline <= horizon)
        .all()
    )
    upcoming_interviews = (
        base.filter(models.Application.interview_date.isnot(None))
        .filter(models.Application.interview_date >= now, models.Application.interview_date <= horizon)
        .all()
    )

    return {
        "stale_applications": [_row_to_out(r) for r in stale],
        "upcoming_oa_deadlines": [_row_to_out(r) for r in upcoming_oa],
        "upcoming_interviews": [_row_to_out(r) for r in upcoming_interviews],
    }