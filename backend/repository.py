from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from models import ResumeAnalysis
from schemas import ResumeAnalysisCreate
from typing import List, Optional
from datetime import datetime, timedelta


class ResumeAnalysisRepository:
    """Repository pattern for ResumeAnalysis database operations"""
    
    def __init__(self, db: Session):
        self.db = db

    def create(self, analysis: ResumeAnalysisCreate) -> ResumeAnalysis:
        """Create a new analysis record"""
        db_analysis = ResumeAnalysis(**analysis.dict(exclude_none=True))
        self.db.add(db_analysis)
        self.db.commit()
        self.db.refresh(db_analysis)
        return db_analysis

    def get_by_id(self, analysis_id: int) -> Optional[ResumeAnalysis]:
        """Get analysis by ID"""
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.id == analysis_id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ResumeAnalysis]:
        """Get all analyses with pagination"""
        return self.db.query(ResumeAnalysis).order_by(
            desc(ResumeAnalysis.created_at),
            desc(ResumeAnalysis.id),
        ).offset(skip).limit(limit).all()

    def get_by_resume_name(self, resume_name: str, skip: int = 0, limit: int = 100) -> List[ResumeAnalysis]:
        """Get analyses by resume name (case-insensitive)"""
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.resume_name.ilike(f"%{resume_name}%")
        ).offset(skip).limit(limit).all()

    def get_by_job_title(self, job_title: str, skip: int = 0, limit: int = 100) -> List[ResumeAnalysis]:
        """Get analyses by job title (case-insensitive)"""
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.job_title.ilike(f"%{job_title}%")
        ).offset(skip).limit(limit).all()

    def get_high_scoring(self, min_score: float = 75.0, limit: int = 50) -> List[ResumeAnalysis]:
        """Get high-scoring analyses"""
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.overall_score >= min_score
        ).order_by(desc(ResumeAnalysis.overall_score)).limit(limit).all()

    def get_recent(self, days: int = 7, limit: int = 50) -> List[ResumeAnalysis]:
        """Get recent analyses"""
        start_date = datetime.utcnow() - timedelta(days=days)
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.created_at >= start_date
        ).order_by(desc(ResumeAnalysis.created_at)).limit(limit).all()

    def get_top_scored(self, limit: int = 10) -> List[ResumeAnalysis]:
        """Get top scored analyses"""
        return self.db.query(ResumeAnalysis).order_by(
            desc(ResumeAnalysis.overall_score)
        ).limit(limit).all()

    def get_by_interview_likelihood(self, likelihood: str, limit: int = 50) -> List[ResumeAnalysis]:
        """Get analyses by interview likelihood"""
        return self.db.query(ResumeAnalysis).filter(
            ResumeAnalysis.interview_likelihood == likelihood
        ).order_by(desc(ResumeAnalysis.created_at)).limit(limit).all()

    def count_by_date_range(self, start_date: datetime, end_date: datetime) -> int:
        """Count analyses in date range"""
        return self.db.query(func.count(ResumeAnalysis.id)).filter(
            ResumeAnalysis.created_at.between(start_date, end_date)
        ).scalar()

    def get_statistics(self) -> dict:
        """Get general statistics about analyses"""
        total = self.db.query(func.count(ResumeAnalysis.id)).scalar() or 0
        avg_score = self.db.query(func.avg(ResumeAnalysis.overall_score)).scalar() or 0
        max_score = self.db.query(func.max(ResumeAnalysis.overall_score)).scalar() or 0
        min_score = self.db.query(func.min(ResumeAnalysis.overall_score)).scalar() or 0
        
        return {
            "total_analyses": total,
            "average_score": round(float(avg_score), 2),
            "max_score": round(float(max_score), 2),
            "min_score": round(float(min_score), 2),
        }

    def update(self, analysis_id: int, analysis: ResumeAnalysisCreate) -> Optional[ResumeAnalysis]:
        """Update an analysis record"""
        db_analysis = self.get_by_id(analysis_id)
        if db_analysis:
            for key, value in analysis.dict(exclude_unset=True).items():
                setattr(db_analysis, key, value)
            db_analysis.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(db_analysis)
        return db_analysis

    def delete(self, analysis_id: int) -> bool:
        """Delete an analysis record"""
        db_analysis = self.get_by_id(analysis_id)
        if db_analysis:
            self.db.delete(db_analysis)
            self.db.commit()
            return True
        return False
