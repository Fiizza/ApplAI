from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


### --- Auth --- ###

class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class ParseJobRequest(BaseModel):
    job_url: Optional[str] = None
    raw_text: Optional[str] = None


class ParsedJobData(BaseModel):
    company: str
    role: str
    requirements: List[str]
    key_skills: List[str]
    location: Optional[str] = None
    employment_type: Optional[str] = None
    seniority: Optional[str] = None


class ApplicationCreate(BaseModel):
    company: str
    role: str
    job_url: Optional[str] = None
    raw_description: Optional[str] = None
    requirements: Optional[List[str]] = []
    key_skills: Optional[List[str]] = []
    location: Optional[str] = None
    employment_type: Optional[str] = None
    seniority: Optional[str] = None
    notes: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    oa_deadline: Optional[datetime] = None
    interview_date: Optional[datetime] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    oa_deadline: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    last_followup_sent_at: Optional[datetime] = None


class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    years_experience: Optional[int] = None
    notes: Optional[str] = None


class SkillUpdate(BaseModel):
    category: Optional[str] = None
    proficiency: Optional[str] = None
    years_experience: Optional[int] = None
    notes: Optional[str] = None


class SkillOut(BaseModel):
    id: int
    name: str
    category: Optional[str]
    proficiency: Optional[str]
    years_experience: Optional[int]
    notes: Optional[str]

    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    match_percentage: int
    matched_skills: List[str]
    missing_skills: List[str]


class CoverLetterResponse(BaseModel):
    opener: str
    matched_skills_used: List[str]
    why_these_skills: Optional[str] = None


class ResumeCreate(BaseModel):
    content: str


class ResumeOut(BaseModel):
    id: int
    content: str
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TailoredResumeResponse(BaseModel):
    tailored_resume: str


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    job_url: Optional[str]
    requirements: Optional[List[str]]
    key_skills: Optional[List[str]]
    location: Optional[str]
    employment_type: Optional[str]
    seniority: Optional[str]
    status: str
    date_applied: datetime
    last_status_update: Optional[datetime]
    notes: Optional[str]
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    oa_deadline: Optional[datetime] = None
    interview_date: Optional[datetime] = None
    last_followup_sent_at: Optional[datetime] = None
    days_since_applied: Optional[int] = None
    needs_followup: Optional[bool] = None

    class Config:
        from_attributes = True


class ResumeVersionOut(BaseModel):
    id: int
    application_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class RemindersResponse(BaseModel):
    stale_applications: List[ApplicationOut]
    upcoming_oa_deadlines: List[ApplicationOut]
    upcoming_interviews: List[ApplicationOut]


class InterviewPrepResponse(BaseModel):
    questions: List[str]
    talking_points: List[str]
    reasoning: Optional[str] = None


class FollowUpEmailResponse(BaseModel):
    subject: str
    body: str


class LearningRecommendation(BaseModel):
    skill: str
    why_it_matters: str
    suggested_topics: List[str]


class LearningRecommendationsResponse(BaseModel):
    recommendations: List[LearningRecommendation]


### --- Gmail integration --- ###

class GmailAuthURLResponse(BaseModel):
    auth_url: str


class EmailAccountOut(BaseModel):
    email_address: str
    last_synced_at: Optional[datetime]
    connected_at: datetime

    class Config:
        from_attributes = True


class EmailSummaryOut(BaseModel):
    id: int
    application_id: Optional[int]
    sender: str
    subject: Optional[str]
    received_at: Optional[datetime]
    summary: Optional[str]
    detected_signal: Optional[str]
    suggested_action: Optional[str]

    class Config:
        from_attributes = True


class GmailSyncResponse(BaseModel):
    new_emails_found: int
    matched_to_applications: int
    unmatched: int
    summaries: List[EmailSummaryOut]