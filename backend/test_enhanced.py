#!/usr/bin/env python3
"""
Test script for the enhanced resume analyzer
"""
import asyncio
import io
from analyzer import ResumeAnalyzer

async def test_analyzer():
    analyzer = ResumeAnalyzer()

    # Sample resume text
    resume_text = """
    John Doe
    Software Engineer

    SKILLS
    Python, JavaScript, React, Node.js, SQL, Git

    EXPERIENCE
    Software Engineer at Tech Corp (2020-Present)
    - Developed web applications using Python and Django
    - Built REST APIs with FastAPI
    - Deployed backend applications to cloud services
    - Used React for frontend development

    PROJECTS
    E-commerce Platform
    - Built with Python, Django, PostgreSQL
    - Implemented payment integration
    - Deployed using cloud services

    Machine Learning Dashboard
    - Created ML models with scikit-learn
    - Built dashboard with React and Node.js
    - Used pandas for data processing
    """

    # Sample job description
    jd_text = """
    Senior Python Developer

    Requirements:
    - Python programming
    - Django or FastAPI
    - React or similar frontend framework
    - Cloud deployment
    - SQL databases
    - Git version control
    - REST API development
    - Machine learning experience preferred
    """

    # Create a fake file object
    file_obj = io.BytesIO(resume_text.encode('utf-8'))

    try:
        result = await analyzer.analyze(file_obj, "resume.txt", "text/plain", jd_text)
        print("✅ Analysis completed successfully!")
        print(f"Overall Score: {result['weighted_score']}")
        print(f"TF-IDF: {result['tfidf_similarity']}")
        print(f"Embeddings: {result['embeddings_similarity']}")
        print(f"Skills Match: {result['skills']['skill_match_percentage']}%")
        print(f"Project Exposure: {result['skill_project_analysis']['exposure_score']}%")

        print("\nSkill Analysis:")
        spa = result['skill_project_analysis']
        print(f"- Skills in both: {len(spa['skills_in_both'])}")
        print(f"- Skills in skills only: {len(spa['skills_in_skills_only'])}")
        print(f"- Skills in projects only: {len(spa['skills_in_projects_only'])}")
        print(f"- Skills neither: {len(spa['skills_neither'])}")

        print("\nLLM Analysis:")
        llm = result['llm_analysis']
        print(f"- Overall: {llm['overall_score']}")
        print(f"- Summary: {llm['summary'][:100]}...")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analyzer())
