from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class SkillMatchDetail(BaseModel):
    """Pydantic model for skill matching details"""
    percentage: float = Field(..., ge=0, le=100, description="Skill match percentage (0-100)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills found in both resume and JD")
    missing_skills: List[str] = Field(default_factory=list, description="Skills in JD but not in resume")
    project_linked_skills: List[str] = Field(default_factory=list, description="Skills found in projects")


class AnalysisRequest(BaseModel):
    """Pydantic model for analysis request validation"""
    job_description: str = Field(..., min_length=10, description="Job description text")

    @field_validator("job_description")
    @classmethod
    def validate_job_description(cls, v):
        if not v or not v.strip():
            raise ValueError("Job description cannot be empty")
        return v.strip()


class AnalysisResponse(BaseModel):
    """Pydantic model for analysis response"""
    overall_score: float = Field(..., ge=0, le=100, description="Overall match score")
    tfidf_score: float = Field(..., ge=0, le=100, description="TF-IDF similarity score")
    embeddings_score: float = Field(..., ge=0, le=100, description="Semantic embeddings similarity")
    skill_match: SkillMatchDetail = Field(..., description="Skill matching details")
    keyword_boost: float = Field(..., ge=0, le=100, description="Keyword boost score")
    ats_score: float = Field(..., ge=0, le=100, description="ATS compatibility score")
    summary: str = Field(..., description="Analysis summary")
    strengths: List[str] = Field(default_factory=list, description="Resume strengths")
    interview_likelihood: str = Field(..., description="Interview likelihood: High/Moderate/Low")
    experience_match: str = Field(..., description="Experience match: Excellent/Good/Fair/Poor")
    analysis_id: Optional[int] = Field(None, description="Database ID of saved analysis")


class ResumeAnalysisCreate(BaseModel):
    """Pydantic model for creating analysis records in database"""
    resume_name: str
    resume_file_path: Optional[str] = None
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    experience_years: Optional[str] = None
    experience_level: Optional[str] = None
    job_title: str
    overall_score: float
    tfidf_score: float
    embeddings_score: float
    skill_match_percentage: float
    exposure_score: float
    keyword_boost: float
    ats_score: float
    matched_skills: Optional[str] = None
    missing_skills: Optional[str] = None
    project_linked_skills: Optional[str] = None
    strengths: Optional[str] = None
    improvements: Optional[str] = None
    interview_likelihood: Optional[str] = None
    experience_match: Optional[str] = None
    summary: Optional[str] = None
    resume_text: Optional[str] = None
    job_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ResumeAnalysisRead(ResumeAnalysisCreate):
    """Pydantic model for reading analysis records from database"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Allow reading from ORM objects


class AnalysisHistory(BaseModel):
    """Pydantic model for analysis history list"""
    total: int = Field(..., description="Total number of analyses")
    analyses: List[ResumeAnalysisRead] = Field(..., description="List of analyses")


class ErrorResponse(BaseModel):
    """Pydantic model for error responses"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")


class UserCreate(BaseModel):
    """Admin request for creating an application user."""
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    role: str = Field("recruiter", pattern="^(admin|recruiter)$")


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MailPullRequest(BaseModel):
    """Request body for pulling resumes from the configured mailbox."""
    job_description: str = Field(..., min_length=10)
    role_title: Optional[str] = None
    roles_json: Optional[str] = None
    expected_experience_level: Optional[str] = Field(None, pattern="^(junior|mid|senior|executive)$")
    min_fit_score: float = Field(80, ge=0, le=100)
    max_messages: int = Field(10, ge=1, le=50)
    send_shortlist_emails: bool = True


class ShortlistEmailRequest(BaseModel):
    """Request body for emailing saved shortlisted analyses."""
    role_title: Optional[str] = None
    min_fit_score: float = Field(80, ge=0, le=100)
    limit: int = Field(100, ge=1, le=500)


class MailSettingsPayload(BaseModel):
    """Admin payload for local mailbox integration settings."""
    auth_method: str = Field("basic", pattern="^(basic|oauth2|graph)$")
    imap_host: str = "outlook.office365.com"
    imap_port: int = Field(993, ge=1, le=65535)
    smtp_host: str = "smtp.office365.com"
    smtp_port: int = Field(587, ge=1, le=65535)
    username: str = ""
    password: str = ""
    from_email: str = ""
    tenant_id: str = "common"
    client_id: str = ""
    client_secret: str = ""


class JobRolePayload(BaseModel):
    id: Optional[str] = None
    roleTitle: str = Field(..., min_length=1, max_length=255)
    active: bool = True
    minExperience: str = "0"
    experienceLevel: Optional[str] = Field("junior", pattern="^(junior|mid|senior|executive)$")
    minFitScore: float = Field(80, ge=0, le=100)
    requiredSkills: List[str] = Field(default_factory=list)
    projectKeywords: List[str] = Field(default_factory=list)
    weights: dict = Field(default_factory=lambda: {"projects": 50, "skills": 30, "education": 20})
    jobDescription: str = ""


class JobRolesSaveRequest(BaseModel):
    roles: List[JobRolePayload] = Field(default_factory=list)
