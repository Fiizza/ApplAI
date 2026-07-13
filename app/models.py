from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    job_url = Column(String, nullable=True)
    raw_description = Column(Text, nullable=True)

    # Stored as JSON-encoded strings (kept simple for Day 1; SQLite has no native array type)
    requirements = Column(Text, nullable=True)   # JSON list of requirement strings
    key_skills = Column(Text, nullable=True)     # JSON list of extracted skills

    location = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    seniority = Column(String, nullable=True)

    status = Column(String, default="Applied")   # Applied, Interview, Offer, Rejected
    date_applied = Column(DateTime, server_default=func.now())
    last_status_update = Column(DateTime, server_default=func.now(), onupdate=func.now())
    notes = Column(Text, nullable=True)

    # --- Tracking fields ---
    recruiter_name = Column(String, nullable=True)
    recruiter_email = Column(String, nullable=True)
    oa_deadline = Column(DateTime, nullable=True)      # online assessment due date
    interview_date = Column(DateTime, nullable=True)
    last_followup_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())


class Skill(Base):
    """Your reference skill set — what /match will compare job requirements against."""
    __tablename__ = "skills"

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_skill_owner_name"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)                 # e.g. "Docker"
    category = Column(String, nullable=True)              # e.g. "DevOps", "Language", "Framework"
    proficiency = Column(String, nullable=True)            # e.g. "Beginner", "Intermediate", "Expert"
    years_experience = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Resume(Base):
    """Stores your one base resume as plain text. Tailoring never edits this row —
    it only reads it and generates a new tailored version per job."""
    __tablename__ = "resume"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ResumeVersion(Base):
    """A saved tailored-resume output for one specific application. Created every time
    /tailor-resume is called, so you keep a history instead of a one-off throwaway string."""
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class EmailAccount(Base):
    """One Gmail account connected via OAuth, per user. Only ever one row per owner —
    reconnecting overwrites the tokens rather than creating a duplicate row."""
    __tablename__ = "email_accounts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    email_address = Column(String, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    # Gmail history ID from the last sync — lets future syncs ask "what's new since this
    # point" instead of re-scanning the whole inbox every time.
    last_history_id = Column(String, nullable=True)
    connected_at = Column(DateTime, server_default=func.now())


class EmailSummary(Base):
    """An AI-summarized recruiter email, matched to one of your tracked applications.
    gmail_message_id is unique so re-running sync never creates duplicate summaries."""
    __tablename__ = "email_summaries"

    __table_args__ = (UniqueConstraint("owner_id", "gmail_message_id", name="uq_owner_gmail_message"),)

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)  # null = unmatched
    gmail_message_id = Column(String, nullable=False, index=True)
    sender = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    received_at = Column(DateTime, nullable=True)

    summary = Column(Text, nullable=True)              # 1-2 sentence plain-language summary
    detected_signal = Column(String, nullable=True)     # e.g. "interview_invite", "rejection", "oa_invite", "offer", "other"
    suggested_action = Column(Text, nullable=True)      # e.g. "Schedule the interview by Friday"

    created_at = Column(DateTime, server_default=func.now())