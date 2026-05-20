import sys
import os
from sqlalchemy.orm import Session

# Add current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import ResumeAnalysis, Candidate, Resume, ResumeVersion
from analyzer import ResumeAnalyzer

def update_experience_in_db():
    db: Session = SessionLocal()
    analyzer = ResumeAnalyzer()
    
    print("Starting database experience level updates...")
    
    # 1. Update ResumeAnalysis table
    analyses = db.query(ResumeAnalysis).all()
    print(f"Found {len(analyses)} records in resume_analysis table.")
    updated_analyses_count = 0
    for analysis in analyses:
        if not analysis.resume_text:
            continue
        
        old_level = analysis.experience_level
        old_years = analysis.experience_years
        
        new_level = analyzer.classify_experience_level(analysis.resume_text, analysis.job_description or "")
        new_years = analyzer.extract_experience_years(analysis.resume_text)
        
        # Format years like standard parsing does
        new_years_str = new_years if new_years else "0 years"
        
        if old_level != new_level or old_years != new_years_str:
            print(f"Updating Analysis ID {analysis.id} ({analysis.candidate_name}):")
            print(f"  Level: {old_level} -> {new_level}")
            print(f"  Years: {old_years} -> {new_years_str}")
            analysis.experience_level = new_level
            analysis.experience_years = new_years_str
            updated_analyses_count += 1
            
    # 2. Update Candidate table
    candidates = db.query(Candidate).all()
    print(f"Found {len(candidates)} records in candidates table.")
    updated_candidates_count = 0
    for candidate in candidates:
        # Find raw text from current resume version
        if not candidate.current_version_id:
            continue
            
        resume_version = db.query(ResumeVersion).filter(ResumeVersion.id == candidate.current_version_id).first()
        if not resume_version or not resume_version.resume:
            continue
            
        raw_text = resume_version.resume.raw_text
        if not raw_text:
            continue
            
        old_level = candidate.experience_level
        old_years = candidate.years_experience
        
        new_level = analyzer.classify_experience_level(raw_text, "")
        new_years_num = analyzer.extract_experience_number(raw_text) or 0.0
        
        if old_level != new_level or old_years != new_years_num:
            print(f"Updating Candidate ID {candidate.id} ({candidate.name}):")
            print(f"  Level: {old_level} -> {new_level}")
            print(f"  Years: {old_years} -> {new_years_num}")
            candidate.experience_level = new_level
            candidate.years_experience = new_years_num
            updated_candidates_count += 1

    if updated_analyses_count > 0 or updated_candidates_count > 0:
        db.commit()
        print(f"Database updated successfully! Committed changes for {updated_analyses_count} analyses and {updated_candidates_count} candidates.")
    else:
        print("No updates needed. Database is already up to date with the latest logic.")
        
    db.close()

if __name__ == "__main__":
    update_experience_in_db()
