from sqlalchemy.orm import Session
from models import ResumeAnalysis
from schemas import ResumeAnalysisCreate, ResumeAnalysisRead
from repository import ResumeAnalysisRepository


class AnalysisService:
    """Service layer for analysis operations"""
    
    def __init__(self, db: Session):
        self.repository = ResumeAnalysisRepository(db)

    def save_analysis(self, analysis_data: dict) -> ResumeAnalysisRead:
        """Save analysis results to database"""
        create_schema = ResumeAnalysisCreate(**analysis_data)
        db_analysis = self.repository.create(create_schema)
        return ResumeAnalysisRead.from_orm(db_analysis)

    def get_analysis(self, analysis_id: int) -> ResumeAnalysisRead:
        """Get analysis by ID"""
        analysis = self.repository.get_by_id(analysis_id)
        if analysis:
            return ResumeAnalysisRead.from_orm(analysis)
        return None

    def get_analysis_history(self, resume_name: str = None, skip: int = 0, limit: int = 100):
        """Get analysis history"""
        if resume_name:
            analyses = self.repository.get_by_resume_name(resume_name, skip, limit)
        else:
            analyses = self.repository.get_all(skip, limit)
        
        return {
            "total": len(analyses),
            "analyses": [ResumeAnalysisRead.from_orm(a) for a in analyses]
        }

    def get_high_scoring_analyses(self, min_score: float = 75.0, limit: int = 50):
        """Get high-scoring analyses"""
        analyses = self.repository.get_high_scoring(min_score, limit)
        return [ResumeAnalysisRead.from_orm(a) for a in analyses]

    def get_statistics(self):
        """Get analysis statistics"""
        return self.repository.get_statistics()
