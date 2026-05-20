import os
import sys
import io
from pathlib import Path

# Ensure project root is in path for imports
sys.path.append(str(Path(__file__).resolve().parent))

from database import SessionLocal
from analyzer import ResumeAnalyzer
from service import AnalysisService
from schemas import ResumeAnalysisCreate

UPLOAD_DIR = Path(__file__).resolve().parent / 'uploads'

def main():
    db = SessionLocal()
    analyzer = ResumeAnalyzer()
    service = AnalysisService(db)
    files = [f for f in UPLOAD_DIR.iterdir() if f.is_file()]
    print(f"Found {len(files)} resume files to process.")
    for f in files:
        try:
            with open(f, 'rb') as fp:
                file_bytes = fp.read()
                result = analyzer.analyze(
                    file_obj=io.BytesIO(file_bytes) if hasattr(io, "BytesIO") else _io.BytesIO(file_bytes),
                    filename=f.name,
                    content_type='application/pdf'  # simple default; analyzer will detect type
                )
            saved, _ = service.save_analysis({
                "resume_name": f.name,
                "resume_file_path": str(f),
                "candidate_name": result.get('candidate_name'),
                "email": result.get('email'),
                "phone_number": result.get('phone_number'),
                "experience_years": result.get('experience_years'),
                "experience_level": result.get('experience_level'),
                "job_title": result.get('job_title') or 'Unassigned',
                "overall_score": result.get('llm_analysis', {}).get('overall_score', result.get('weighted_score', 0)),
                "tfidf_score": result.get('tfidf_similarity', 0),
                "embeddings_score": result.get('embeddings_similarity', 0),
                "skill_match_percentage": result.get('skills', {}).get('skill_match_percentage', 0),
                "exposure_score": result.get('skill_project_analysis', {}).get('exposure_score', 0),
                "keyword_boost": result.get('score_breakdown', {}).get('keyword_boost', 0),
                "ats_score": result.get('llm_analysis', {}).get('ats_score', 0),
                "matched_skills": ",".join([s.get('skill') if isinstance(s, dict) else str(s) for s in (result.get('skills', {}).get('matched_in_skills') or [] )]),
                "missing_skills": ",".join([s.get('skill') if isinstance(s, dict) else str(s) for s in (result.get('skills', {}).get('missing') or [] )]),
                "project_linked_skills": ",".join([s.get('skill') if isinstance(s, dict) else str(s) for s in (result.get('skill_project_analysis', {}).get('skills_in_both') or [] )]),
                "strengths": "; ".join(result.get('llm_analysis', {}).get('strengths', [])),
                "improvements": "; ".join(result.get('llm_analysis', {}).get('improvements', [])),
                "interview_likelihood": result.get('llm_analysis', {}).get('interview_likelihood', ''),
                "experience_match": result.get('llm_analysis', {}).get('experience_match', ''),
                "summary": result.get('llm_analysis', {}).get('summary', ''),
                "resume_text": result.get('resume_text', ''),
                "job_description": ''
            })
            print(f"Processed {f.name}: saved ID {saved.id}, level {saved.experience_level}")
        except Exception as e:
            print(f"Error processing {f.name}: {e}")
    db.close()

if __name__ == '__main__':
    main()
