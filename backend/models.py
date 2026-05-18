from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="recruiter")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)

    job_roles = relationship(
        "JobRole",
        back_populates="creator",
        foreign_keys="JobRole.created_by",
    )
    shortlists = relationship(
        "Shortlist",
        back_populates="changer",
        foreign_keys="Shortlist.changed_by",
    )
    outcomes = relationship(
        "Outcome",
        back_populates="recorder",
        foreign_keys="Outcome.recorded_by",
    )
    audit_logs = relationship("AuditLog", back_populates="user")


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    current_version_id = Column(
        Integer,
        ForeignKey("resume_versions.id", use_alter=True, ondelete="SET NULL"),
        nullable=True,
    )
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    portfolio_url = Column(String(500), nullable=True)
    current_title = Column(String(200), nullable=True)
    experience_level = Column(String(20), nullable=True)
    years_experience = Column(Float, nullable=True)
    linkedin_data = Column(Text, nullable=True)
    github_summary = Column(Text, nullable=True)
    consistency_flags = Column(Text, nullable=True)
    enrichment_sources = Column(Text, nullable=True)
    needs_manual_review = Column(Boolean, nullable=False, default=False)

    resume_versions = relationship(
        "ResumeVersion",
        back_populates="candidate",
        foreign_keys="ResumeVersion.candidate_id",
    )
    current_version = relationship(
        "ResumeVersion",
        foreign_keys=[current_version_id],
        post_update=True,
    )
    outcomes = relationship("Outcome", back_populates="candidate")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    simhash = Column(String(64), nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=_utcnow)
    is_current = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        Index("ix_resume_versions_simhash", "simhash"),
    )

    candidate = relationship(
        "Candidate",
        back_populates="resume_versions",
        foreign_keys=[candidate_id],
    )
    resume = relationship("Resume", back_populates="version", uselist=False)


class Resume(Base):
    """Parsed content for a resume version. id == resume_version_id."""

    __tablename__ = "resumes"

    id = Column(
        Integer,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    raw_text = Column(Text, nullable=True)
    sections = Column(Text, nullable=True)
    parsed_at = Column(DateTime, nullable=False, default=_utcnow)

    version = relationship("ResumeVersion", back_populates="resume")
    evaluations = relationship("Evaluation", back_populates="resume")


class JobRoleRequirement(Base):
    __tablename__ = "job_role_requirements"

    id = Column(Integer, primary_key=True, index=True)
    job_role_id = Column(
        Integer,
        ForeignKey("job_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    label = Column(String(255), nullable=False)
    weight = Column(Float, nullable=False)
    req_type = Column(String(50), nullable=False, default="skill")
    description = Column(Text, nullable=True)
    min_years = Column(Integer, nullable=True)

    job_role = relationship("JobRole", back_populates="requirements")


class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    min_experience = Column(Integer, nullable=True, default=0)
    weight_projects = Column(Integer, nullable=False, default=50)
    weight_skills = Column(Integer, nullable=False, default=30)
    weight_education = Column(Integer, nullable=False, default=20)
    cosine_threshold = Column(Float, nullable=False, default=0.70)
    description = Column(Text, nullable=True)
    min_degree = Column(String(50), nullable=True)
    preferred_majors = Column(Text, nullable=True)
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(DateTime, nullable=False, default=_utcnow)
    filter_experience_levels = Column(String(100), nullable=True)
    intake_paused = Column(Boolean, nullable=False, default=False)
    shortlist_target = Column(Integer, nullable=True)
    min_fit_score = Column(Float, nullable=True)

    creator = relationship("User", back_populates="job_roles", foreign_keys=[created_by])
    job_role_skills = relationship(
        "JobRoleSkill",
        back_populates="job_role",
        cascade="all, delete-orphan",
    )
    requirements = relationship(
        "JobRoleRequirement",
        back_populates="job_role",
        cascade="all, delete-orphan",
        order_by="JobRoleRequirement.id",
    )
    evaluations = relationship("Evaluation", back_populates="job_role")
    inbound_emails = relationship("InboundEmail", back_populates="job_role")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    category = Column(String(100), nullable=True)
    embedding = Column(Text, nullable=True)

    job_role_skills = relationship(
        "JobRoleSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )


class JobRoleSkill(Base):
    __tablename__ = "job_role_skills"

    id = Column(Integer, primary_key=True, index=True)
    job_role_id = Column(
        Integer,
        ForeignKey("job_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id = Column(
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_keyword = Column(Boolean, nullable=False, default=False)

    job_role = relationship("JobRole", back_populates="job_role_skills")
    skill = relationship("Skill", back_populates="job_role_skills")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(
        Integer,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_role_id = Column(
        Integer,
        ForeignKey("job_roles.id", ondelete="CASCADE"),
        nullable=False,
    )
    total_score = Column(Float, nullable=False, default=0.0)
    project_score = Column(Float, nullable=False, default=0.0)
    skill_score = Column(Float, nullable=False, default=0.0)
    education_score = Column(Float, nullable=False, default=0.0)
    skills_matched = Column(Text, nullable=True)
    excerpts = Column(Text, nullable=True)
    requirements_breakdown = Column(Text, nullable=True)
    reasoning_summary = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, nullable=False, default=_utcnow)
    eval_status = Column(String(20), nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint("job_role_id", "resume_id", name="uq_eval_job_resume"),
        Index("ix_evaluations_total_score", "total_score"),
    )

    resume = relationship("Resume", back_populates="evaluations")
    job_role = relationship("JobRole", back_populates="evaluations")
    shortlists = relationship(
        "Shortlist",
        back_populates="evaluation",
        cascade="all, delete-orphan",
    )


class Shortlist(Base):
    __tablename__ = "shortlists"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(
        Integer,
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(String(50), nullable=False, default="review")
    note = Column(Text, nullable=True)
    changed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at = Column(DateTime, nullable=False, default=_utcnow)

    evaluation = relationship("Evaluation", back_populates="shortlists")
    changer = relationship("User", back_populates="shortlists", foreign_keys=[changed_by])


class Outcome(Base):
    __tablename__ = "outcomes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    outcome = Column(String(50), nullable=False)
    recorded_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recorded_at = Column(DateTime, nullable=False, default=_utcnow)

    candidate = relationship("Candidate", back_populates="outcomes")
    recorder = relationship("User", back_populates="outcomes", foreign_keys=[recorded_by])


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(String(255), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=_utcnow)

    user = relationship("User", back_populates="audit_logs")


class InboundEmail(Base):
    """Tracks emails received by the ingestion pipeline."""

    __tablename__ = "inbound_emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(500), unique=True, nullable=False)
    sender_email = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    received_at = Column(DateTime, nullable=False, default=_utcnow)
    job_id = Column(
        Integer,
        ForeignKey("job_roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(String(50), nullable=False, default="new")
    raw_file_paths = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    job_role = relationship("JobRole", back_populates="inbound_emails")


class ResumeAnalysis(Base):
    """Legacy analysis result table used by the current /analyze endpoints."""

    __tablename__ = "resume_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    resume_name = Column(String(255), nullable=False, index=True)
    resume_file_path = Column(String(500), nullable=True)
    candidate_name = Column(String(255), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone_number = Column(String(50), nullable=True)
    experience_years = Column(String(50), nullable=True)
    experience_level = Column(String(20), nullable=True, index=True)
    job_title = Column(String(255), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, index=True)
    tfidf_score = Column(Float, nullable=False)
    embeddings_score = Column(Float, nullable=False)
    skill_match_percentage = Column(Float, nullable=False)
    exposure_score = Column(Float, nullable=False)
    keyword_boost = Column(Float, nullable=False)
    ats_score = Column(Float, nullable=False)
    matched_skills = Column(Text, nullable=True)
    missing_skills = Column(Text, nullable=True)
    project_linked_skills = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    improvements = Column(Text, nullable=True)
    interview_likelihood = Column(String(50), nullable=True)
    experience_match = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    resume_text = Column(Text, nullable=True)
    job_description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=_utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("idx_overall_score_desc", overall_score.desc()),
        Index("idx_created_at_desc", created_at.desc()),
        Index("idx_interview_likelihood", interview_likelihood),
    )

    def __repr__(self):
        return (
            f"<ResumeAnalysis(id={self.id}, resume={self.resume_name}, "
            f"score={self.overall_score})>"
        )
