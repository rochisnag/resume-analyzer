from dotenv import load_dotenv
load_dotenv()

import re
import json
import asyncio
from typing import Optional
import io

# Text extraction
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# NLP - NOW USING SKLEARN FOR PROPER TF-IDF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Embeddings for semantic similarity
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False

# LLM
from groq import Groq


# ── 🔥 IMPROVEMENT #1: SYNONYM / SKILL MAPPING ──────────────────────────────
# Map abbreviations and variations to canonical forms
SKILL_SYNONYMS = {
    # AI & Machine Learning
    "machine learning": ["ml", "machine learning", "ml engineering"],
    "nlp": ["nlp", "natural language processing", "nlp engineering"],
    "deep learning": ["deep learning", "dl", "neural networks"],
    "computer vision": ["cv", "computer vision", "image processing"],
    "ai": ["ai", "artificial intelligence", "ml"],
    
    # Web & REST
    "rest": ["rest", "rest api", "restful", "rest apis"],
    "rest api": ["rest api", "restful api", "api"],
    
    # JavaScript Ecosystem
    "react": ["react", "react.js", "reactjs"],
    "next.js": ["next.js", "nextjs", "next"],
    "vue": ["vue", "vue.js", "vuejs"],
    "angular": ["angular", "angular.js", "angularjs"],
    
    # Java Ecosystem
    "spring": ["spring", "spring framework", "spring boot"],
    "spring boot": ["spring boot", "springboot", "boot"],
    
    # Python Frameworks
    "django": ["django", "django framework"],
    "flask": ["flask", "flask framework"],
    "fastapi": ["fastapi", "fast api"],
    
    # Cloud Platforms
    "aws": ["aws", "amazon web services", "amazon"],
    "azure": ["azure", "microsoft azure"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    
    # Databases
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo"],
    
    # DevOps & Infrastructure
    "kubernetes": ["kubernetes", "k8s", "k8"],
    "ci/cd": ["ci/cd", "cicd", "continuous integration", "continuous deployment"],
    
    # Languages
    "c++": ["c++", "cpp", "c plus plus"],
    "c#": ["c#", "csharp", "c sharp"],
    
    # Data
    "spark": ["spark", "apache spark"],
    "hadoop": ["hadoop", "apache hadoop"],
}

# ── Common tech skills dictionary ──────────────────────────────────────────
SKILL_CATEGORIES = {
    "Programming Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl"
    ],
    "Web Frameworks": [
        "react", "angular", "vue", "next.js", "nextjs", "django", "flask", "fastapi",
        "express", "spring", "laravel", "rails", "svelte", "nuxt"
    ],
    "Databases": [
        "postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle", "cassandra",
        "elasticsearch", "dynamodb", "neo4j", "firebase", "supabase", "postgres"
    ],
    "Cloud & DevOps": [
        "aws", "azure", "gcp", "kubernetes", "terraform", "ansible",
        "jenkins", "github actions", "ci/cd", "linux", "nginx", "kafka"
    ],
    "AI & Data": [
        "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
        "pandas", "numpy", "nlp", "computer vision", "langchain", "openai", "llm",
        "data science", "spark", "hadoop", "tableau", "power bi"
    ],
    "Soft Skills": [
        "leadership", "communication", "teamwork", "problem solving", "agile",
        "scrum", "project management", "collaboration", "mentoring", "presentations"
    ],
}

ALL_SKILLS = {skill: cat for cat, skills in SKILL_CATEGORIES.items() for skill in skills}


# ── 🔥 IMPROVEMENT #3: KEYWORD BOOSTING ────────────────────────────────────
# High-impact skills that should get extra weight
HIGH_IMPACT_KEYWORDS = {
    # Tier 1: Highly Valued
    "python": 5,
    "java": 5,
    "machine learning": 5,
    "deep learning": 5,
    "cloud": 4,
    "aws": 4,
    "kubernetes": 4,
    "spring boot": 4,
    "react": 4,
    "ai": 4,
    "typescript": 4,
    "fastapi": 4,
    "nlp": 4,
    
    # Tier 2: Important
    "sql": 3,
    "rest api": 3,
    "microservices": 3,
    "agile": 3,
    "scrum": 3,
    "git": 3,
    "ci/cd": 3,
    "redis": 3,
    "scikit-learn": 3,
    "pandas": 3,
    "numpy": 3,
    "langchain": 3,
    "linux": 3,
    "nginx": 3,
    "github actions": 3,
    "next.js": 3,
    
    # Tier 3: Valuable
    "mongodb": 2,
    "postgresql": 2,
    "node.js": 2,
    "angular": 2,
    "terraform": 2,
    "elasticsearch": 2,
    "django": 2,
    "communication": 2,
    "teamwork": 2,
    "mentoring": 2,
    "leadership": 2,
    "problem solving": 2,
}


class ResumeAnalyzer:
    def __init__(self):
        import os
        # Check if API key exists before creating client
        if os.getenv("GROQ_API_KEY"):
            try:
                self.client = Groq()
                self.llm_available = True
            except Exception as e:
                self.client = None
                self.llm_available = False
                print(f"[WARNING] LLM init failed: {e}")
        else:
            self.client = None
            self.llm_available = False
            print(f"[WARNING] LLM not available (no API key). Using 6-layer analysis without Claude enhancement.")
        
        # TF-IDF vectorizer with n-grams (1-2 word phrases)
        self.tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            lowercase=True,
            stop_words='english',
            min_df=1,
            max_df=1.0  # Must be 1.0 for 2-document comparison; 0.95 filters ALL overlapping terms
        )
        
        # Initialize embeddings model
        if EMBEDDINGS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    local_files_only=True,
                )
                self.embeddings_available = True
                print("[INFO] Embeddings model loaded successfully.")
            except Exception as e:
                self.embedding_model = None
                self.embeddings_available = False
                print(f"[WARNING] Embeddings model failed to load: {e}")
        else:
            self.embedding_model = None
            self.embeddings_available = False
            print("[WARNING] sentence-transformers not installed. Embeddings will be unavailable.")

    # ── 🔥 IMPROVEMENT #5: TEXT NORMALIZATION ─────────────────────────────
    def normalize_text(self, text: str) -> str:
        """Normalize text to handle variations like SpringBoot → spring boot"""
        # Handle camelCase and PascalCase
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
        
        # Handle dots (React.js → React js)
        text = re.sub(r'\.(\w)', r' \1', text)
        
        # Handle plus signs (C++ → C plus plus)
        text = text.replace('++', ' plus plus')
        text = text.replace('#', ' sharp')
        
        # Convert to lowercase
        text = text.lower()
        
        return text

    # ── 🔥 IMPROVEMENT #1: APPLY SYNONYM MAPPING ────────────────────────────
    def apply_synonyms(self, text: str) -> str:
        """Map synonyms to canonical forms"""
        text_lower = text.lower()
        
        for canonical, synonyms in SKILL_SYNONYMS.items():
            for synonym in synonyms:
                # Use word boundary to match whole words/phrases
                pattern = r'\b' + re.escape(synonym) + r'\b'
                text_lower = re.sub(pattern, canonical, text_lower)
        
        return text_lower

    # ── 1. Text Extraction ──────────────────────────────────────────────────
    def extract_text(self, file_obj: io.BytesIO, filename: str, content_type: str) -> str:
        ext = filename.lower().split(".")[-1]

        if ext == "pdf" or "pdf" in content_type:
            return self._extract_pdf(file_obj)
        elif ext == "docx" or "wordprocessing" in content_type:
            return self._extract_docx(file_obj)
        else:
            return file_obj.read().decode("utf-8", errors="ignore")

    def _extract_pdf(self, file_obj: io.BytesIO) -> str:
        if not PDF_SUPPORT:
            raise RuntimeError("pdfplumber not installed. Run: pip install pdfplumber")
        text = ""
        with pdfplumber.open(file_obj) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _extract_docx(self, file_obj: io.BytesIO) -> str:
        if not DOCX_SUPPORT:
            raise RuntimeError("python-docx not installed. Run: pip install python-docx")
        doc = DocxDocument(file_obj)
        return "\n".join([para.text for para in doc.paragraphs])

    def extract_candidate_name(self, text: str) -> Optional[str]:
        """Best-effort candidate name extraction from the first resume lines."""
        section_titles = {
            "resume", "curriculum vitae", "career objective", "objective", "summary",
            "professional summary", "education", "experience", "skills", "projects",
        }

        for raw_line in text.splitlines()[:15]:
            line = re.sub(r"\s+", " ", raw_line).strip()
            if not line:
                continue

            lowered = line.lower()
            if lowered in section_titles:
                continue
            if any(token in lowered for token in ["@", "linkedin", "github", "http", ".com", "+91"]):
                continue
            if re.search(r"\d{4,}", line):
                continue

            words = line.split()
            if 2 <= len(words) <= 5 and re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", line):
                return line

        return None

    def extract_email(self, text: str) -> Optional[str]:
        """Extract the first email address from resume text."""
        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', text)
        return match.group(0) if match else None

    def extract_phone(self, text: str) -> Optional[str]:
        """Extract a likely phone number from resume text."""
        match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{4}\b', text)
        return match.group(0).strip() if match else None

    def extract_experience_years(self, text: str) -> Optional[str]:
        """Extract an explicit years-of-experience phrase when present."""
        match = re.search(r'\b(\d{1,2}\+?)\s*(?:years?|yrs?)\b', text, re.IGNORECASE)
        return f"{match.group(1)} years" if match else None

    def extract_experience_number(self, text: str) -> Optional[float]:
        """Extract a numeric years-of-experience value when present."""
        match = re.search(r'\b(\d{1,2})(?:\+)?\s*(?:years?|yrs?)\b', text, re.IGNORECASE)
        return float(match.group(1)) if match else None

    def is_fresher_role(self, job_description: str) -> bool:
        """Return True when the role explicitly targets freshers or entry-level candidates."""
        jd_lower = job_description.lower()
        fresher_patterns = [
            r"\bfreshers?\b",
            r"\bfresh graduates?\b",
            r"\bnew graduates?\b",
            r"\bgraduate trainees?\b",
            r"\bentry[-\s]?level\b",
            r"\bno\s+(?:prior\s+)?experience\s+(?:required|needed)\b",
            r"\b0\s*(?:-\s*1)?\s*(?:years?|yrs?)\b",
        ]
        return any(re.search(pattern, jd_lower) for pattern in fresher_patterns)

    def classify_experience_level(self, resume_text: str, job_description: str = "") -> str:
        """Classify candidates for leaderboard segregation."""
        combined = f"{resume_text}\n{job_description}".lower()
        if self.is_fresher_role(job_description):
            return "junior"

        years = self.extract_experience_number(resume_text)
        if years is not None:
            if years <= 2:
                return "junior"
            if years <= 5:
                return "mid"
            if years <= 10:
                return "senior"
            return "executive"

        if re.search(r"\b(executive|director|head of|vp|vice president|principal)\b", combined):
            return "executive"
        if re.search(r"\b(senior|sr\.?|lead|staff)\b", combined):
            return "senior"

        if re.search(r"\b(intern|internship|fresher|entry[-\s]?level|junior)\b", combined):
            return "junior"
        return "junior"

    # ── 🔥 NEW: Resume Validation ───────────────────────────────────────────
    def validate_resume(self, text: str, filename: str) -> dict:
        """
        Validate if the uploaded document is likely a resume by checking for:
        - Resume-specific keywords and sections
        - Personal information patterns
        - Professional experience indicators
        - File type validation
        """
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        validation_result = {
            "is_resume": False,
            "confidence": 0.0,
            "reasons": [],
            "warnings": []
        }
        
        # File type check
        valid_extensions = ['.pdf', '.docx', '.doc']
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext not in valid_extensions:
            validation_result["warnings"].append(f"Unsupported file type: {file_ext}. Supported: PDF, DOCX")
        
        # Resume section keywords (weighted)
        section_keywords = {
            "experience": ["experience", "work experience", "professional experience", "employment", "work history"],
            "education": ["education", "academic", "degree", "university", "college", "school"],
            "skills": ["skills", "technical skills", "competencies", "expertise", "proficiencies"],
            "projects": ["projects", "portfolio", "personal projects", "professional projects"],
            "contact": ["contact", "phone", "email", "address", "linkedin", "github"],
            "summary": ["summary", "objective", "profile", "about", "professional summary"]
        }
        
        section_score = 0
        found_sections = []
        for section, keywords in section_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                section_score += 1
                found_sections.append(section)
        
        # Personal information patterns
        personal_patterns = [
            r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone number
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{5}(?:[-\s]\d{4})?\b',  # ZIP code
            r'\b(?:linkedin|github)\.com/[^\s]+\b',  # Social links
        ]
        
        personal_score = sum(1 for pattern in personal_patterns if re.search(pattern, text_lower))
        
        # Professional keywords
        professional_keywords = [
            "engineer", "developer", "analyst", "manager", "director", "specialist",
            "consultant", "architect", "scientist", "researcher", "lead", "senior",
            "junior", "intern", "freelance", "contractor", "full-time", "part-time"
        ]
        
        professional_score = sum(1 for keyword in professional_keywords if keyword in text_lower)
        
        # Length check (resumes are typically 300-2000 words)
        word_count = len(text.split())
        length_score = 1 if 200 <= word_count <= 3000 else 0
        
        # Calculate confidence score (0-100)
        total_score = (
            (section_score / len(section_keywords)) * 40 +  # 40% weight for sections
            (personal_score / len(personal_patterns)) * 20 +  # 20% weight for personal info
            (professional_score / len(professional_keywords)) * 20 +  # 20% weight for professional terms
            length_score * 20  # 20% weight for appropriate length
        )
        
        validation_result["confidence"] = round(total_score, 1)
        validation_result["is_resume"] = total_score >= 30  # 30% threshold
        
        # Build reasons
        if found_sections:
            validation_result["reasons"].append(f"Found resume sections: {', '.join(found_sections)}")
        if personal_score > 0:
            validation_result["reasons"].append(f"Contains personal contact information ({personal_score} patterns)")
        if professional_score > 0:
            validation_result["reasons"].append(f"Contains professional keywords ({professional_score} matches)")
        if length_score:
            validation_result["reasons"].append(f"Appropriate resume length ({word_count} words)")
        
        # Warnings for low confidence
        if section_score < 2:
            validation_result["warnings"].append("Few resume sections detected")
        if personal_score == 0:
            validation_result["warnings"].append("No contact information found")
        if word_count < 200:
            validation_result["warnings"].append("Document is very short for a resume")
        elif word_count > 3000:
            validation_result["warnings"].append("Document is very long for a resume")
        
        return validation_result

    # ── 2. Text Preprocessing ───────────────────────────────────────────────
    def preprocess(self, text: str) -> str:
        """Preprocess: normalize → apply synonyms → clean"""
        # Step 1: Normalize variations
        text = self.normalize_text(text)
        
        # Step 2: Apply synonym mapping
        text = self.apply_synonyms(text)
        
        # Step 3: Basic cleaning (remove special chars except +#.)
        text = re.sub(r'[^\w\s\+\#\.]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    # ── 3. Feature Extraction (TF-IDF with N-GRAMS) ────────────────────────
    # 🔥 IMPROVEMENT #4: N-GRAMS SUPPORT
    def compute_tfidf_similarity(self, resume_text: str, jd_text: str) -> float:
        """
        Compute TF-IDF similarity with n-grams (1-2 word phrases)
        This detects phrases like "machine learning", "spring boot" etc.
        """
        try:
            # Vectorize both texts
            tfidf_matrix = self.tfidf_vectorizer.fit_transform([resume_text, jd_text])
            
            # Compute cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return round(float(similarity) * 100, 1)
        except Exception as e:
            # Fallback to simple Jaccard if TF-IDF fails
            resume_words = set(resume_text.split())
            jd_words = set(jd_text.split())
            intersection = resume_words & jd_words
            union = resume_words | jd_words
            if not union:
                return 0.0
            return round(len(intersection) / len(union) * 100, 1)

    # ── 🔥 NEW: Semantic Embeddings Similarity ────────────────────────────
    def compute_embeddings_similarity(self, resume_text: str, jd_text: str) -> float:
        """
        Compute semantic similarity using sentence transformers embeddings.
        Better than TF-IDF for understanding meaning and context.
        """
        if not self.embeddings_available or self.embedding_model is None:
            print("[WARNING] Embeddings not available, falling back to TF-IDF")
            return self.compute_tfidf_similarity(resume_text, jd_text)
        
        try:
            # Encode both texts to embeddings
            resume_embedding = self.embedding_model.encode(resume_text, convert_to_tensor=True)
            jd_embedding = self.embedding_model.encode(jd_text, convert_to_tensor=True)
            
            # Compute cosine similarity
            similarity = cosine_similarity(
                resume_embedding.reshape(1, -1), 
                jd_embedding.reshape(1, -1)
            )[0][0]
            
            return round(float(similarity) * 100, 1)
        except Exception as e:
            print(f"[WARNING] Embeddings similarity failed: {e}, falling back to TF-IDF")
            return self.compute_tfidf_similarity(resume_text, jd_text)

    # ── 4. Keyword Extraction ───────────────────────────────────────────────
    def extract_keywords(self, text: str, top_n: int = 15) -> list[str]:
        words = re.findall(r'\b\w+\b', self.preprocess(text))
        stop_words = set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'])
        word_count = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_count[word] = word_count.get(word, 0) + 1
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]

    # ── 5. Skill Matching with Synonym Support ─────────────────────────────
    def _preprocess_skill_name(self, skill: str) -> str:
        """Preprocess a skill name the same way we preprocess text,
        so that the regex pattern matches correctly in preprocessed text."""
        processed = self.normalize_text(skill)
        processed = self.apply_synonyms(processed)
        processed = re.sub(r'[^\w\s\+\#\.]', ' ', processed)
        processed = re.sub(r'\s+', ' ', processed).strip()
        return processed

    def extract_skills_from_jd(self, jd_text: str) -> list:
        """Dynamically extract skills from job description instead of using hardcoded list"""
        jd_clean = self.preprocess(jd_text)
        jd_lower = jd_text.lower()
        
        extracted_skills = []
        
        # Search through all known skills to find matches in JD
        for skill in ALL_SKILLS:
            skill_processed = self._preprocess_skill_name(skill)
            pattern_processed = r'\b' + re.escape(skill_processed) + r'\b'
            pattern_original = r'\b' + re.escape(skill) + r'\b'
            
            if re.search(pattern_processed, jd_clean) or re.search(pattern_original, jd_lower):
                extracted_skills.append(skill)
        
        # Also look for technical terms not in hardcoded list using pattern matching
        # Look for common technology patterns
        tech_patterns = [
            r'\b(?:python|java|javascript|typescript|golang|rust|csharp|php|ruby|kotlin|scala)\b',
            r'\b(?:react|angular|vue|svelte|nextjs?|nuxt)\b',
            r'\b(?:node\.?js|express|django|flask|fastapi|spring|rails|laravel)\b',
            r'\b(?:postgres|mysql|mongodb|redis|elasticsearch|dynamodb|cassandra|firebase)\b',
            r'\b(?:aws|azure|gcp|kubernetes|terraform|ansible|jenkins)\b',
            r'\b(?:tensorflow|pytorch|scikit-learn|pandas|numpy|langchain|openai)\b',
            r'\b(?:git|github|gitlab|bitbucket|rest api|graphql|grpc)\b',
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, jd_lower, re.IGNORECASE)
            for match in matches:
                # Normalize the match
                normalized = match.lower().replace('.', '').replace('js', '')
                if normalized not in [s.lower() for s in extracted_skills]:
                    # Try to find the proper casing from ALL_SKILLS
                    for skill in ALL_SKILLS:
                        if normalized in skill.lower().replace('.', '').replace('js', ''):
                            if skill not in extracted_skills:
                                extracted_skills.append(skill)
                            break
        
        return list(set(extracted_skills))  # Remove duplicates

    def match_skills(self, resume_text: str, jd_text: str) -> dict:
        # Preprocess with normalization and synonyms
        resume_clean = self.preprocess(resume_text)
        jd_clean = self.preprocess(jd_text)

        # Also search in original lowercased text for skills with special chars
        resume_lower = resume_text.lower()
        jd_lower = jd_text.lower()

        # 🔥 NEW: Extract skills dynamically from JD instead of using hardcoded list
        jd_skills = self.extract_skills_from_jd(jd_text)

        matched_in_skills = []
        missing = []
        for skill in jd_skills:
            skill_processed = self._preprocess_skill_name(skill)
            pattern_processed = r'\b' + re.escape(skill_processed) + r'\b'
            pattern_original = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern_processed, resume_clean) or re.search(pattern_original, resume_lower):
                matched_in_skills.append({"skill": skill, "category": ALL_SKILLS[skill]})
            else:
                missing.append({"skill": skill, "category": ALL_SKILLS[skill]})

        # Also find resume skills not in JD
        extra_skills = []
        jd_skill_names = set(s for s in jd_skills)
        for skill in ALL_SKILLS:
            if skill not in jd_skill_names:
                skill_processed = self._preprocess_skill_name(skill)
                pattern_processed = r'\b' + re.escape(skill_processed) + r'\b'
                pattern_original = r'\b' + re.escape(skill) + r'\b'
                if re.search(pattern_processed, resume_clean) or re.search(pattern_original, resume_lower):
                    extra_skills.append({"skill": skill, "category": ALL_SKILLS[skill]})

        skill_match_pct = round(len(matched_in_skills) / max(len(jd_skills), 1) * 100, 1)

        return {
            "matched_in_skills": matched_in_skills,
            "missing": missing,
            "extra": extra_skills,
            "skill_match_percentage": skill_match_pct,
            "total_jd_skills": len(jd_skills),
        }

    # ── 🔥 IMPROVEMENT #2 & #3: WEIGHTED SCORING SYSTEM + KEYWORD BOOSTING ──
    def compute_weighted_score(self, 
                               tfidf_score: float, 
                               embeddings_score: float,
                               skill_match_pct: float, 
                               exposure_score: float,
                               resume_text: str,
                               jd_text: str) -> dict:
        """
        Compute final score using advanced weighted combination:
        - 20% TF-IDF (n-gram based text similarity)
        - 20% Embeddings (semantic similarity)
        - 30% Skill Matching (now with synonyms) 
        - 20% Real-time Exposure (skills in projects)
        - 10% Keyword Boosting (high-impact keywords)
        Weights sum to 1.0 for proper 0-100 range.
        """
        # Normalize components to 0-1 range
        tfidf_norm = tfidf_score / 100.0
        embeddings_norm = embeddings_score / 100.0
        skill_norm = skill_match_pct / 100.0
        exposure_norm = exposure_score / 100.0
        
        # 🔥 Apply keyword boosting — compute as a 0-1 ratio
        boost_earned = 0.0
        max_boost = 0.0
        resume_lower = self.preprocess(resume_text)
        jd_lower = self.preprocess(jd_text)
        
        for keyword, boost_value in HIGH_IMPACT_KEYWORDS.items():
            # Check if keyword appears in JD first
            kw_processed = self._preprocess_skill_name(keyword)
            in_jd = (re.search(r'\b' + re.escape(keyword) + r'\b', jd_lower) or
                     re.search(r'\b' + re.escape(kw_processed) + r'\b', jd_lower))
            
            if in_jd:
                max_boost += boost_value
                # Check if keyword is also in resume
                in_resume = (re.search(r'\b' + re.escape(keyword) + r'\b', resume_lower) or
                             re.search(r'\b' + re.escape(kw_processed) + r'\b', resume_lower))
                if in_resume:
                    boost_earned += boost_value
        
        # Normalize boost to 0-1 range
        boost_norm = (boost_earned / max_boost) if max_boost > 0 else 0.0
        
        # Final weighted score (0-100)
        final_score = (
            0.20 * tfidf_norm +
            0.20 * embeddings_norm +
            0.30 * skill_norm +
            0.20 * exposure_norm +
            0.10 * boost_norm
        ) * 100
        
        final_score = min(100, max(0, final_score))  # Clamp to 0-100
        
        return {
            "weighted_score": round(final_score, 1),
            "tfidf_component": round(tfidf_norm * 20, 1),
            "embeddings_component": round(embeddings_norm * 20, 1),
            "skill_component": round(skill_norm * 30, 1),
            "exposure_component": round(exposure_norm * 20, 1),
            "keyword_boost": round(boost_norm * 10, 1),
            "breakdown": {
                "tfidf_weight": 0.20,
                "embeddings_weight": 0.20,
                "skill_weight": 0.30,
                "exposure_weight": 0.20,
                "boost_weight": 0.10,
                "boost_keywords_matched": int(boost_earned),
                "boost_keywords_total": int(max_boost),
            }
        }

    # ── 8. PROJECT EXTRACTION & SKILL VERIFICATION ──────────────────────────
    def extract_projects(self, text: str) -> list:
        """Extract project information from resume with improved pattern matching"""
        projects = []
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Look for project sections with various patterns
        project_patterns = [
            r'(?:PROJECT|PROJECTS)\s*[:\-]?\s*\n(.*?)(?=\n(?:EDUCATION|SKILLS|EXPERIENCE|WORK|$))',
            r'(?:BUILT|DEVELOPED|CREATED|WORKED)\s+(?:ON|WITH)\s+(.+?)(?:\n|,|\.|$)'
        ]
        
        for pattern in project_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                project_text = match.group(1) if match.lastindex else match.group(0)
                if len(project_text.strip()) > 10:  # More meaningful content
                    projects.append(project_text.strip())
        
        # Also look for bullet points under project-like headers
        lines = text.split('\n')
        current_project = ""
        in_project_section = False
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line indicates a project
            if any(keyword in line_lower for keyword in ['project', 'built', 'developed', 'created', 'portfolio']):
                if current_project:
                    projects.append(current_project.strip())
                current_project = line.strip()
                in_project_section = True
            elif in_project_section and line.strip().startswith('-'):
                current_project += '\n' + line.strip()
            elif in_project_section and line.strip() and not line.startswith(' '):
                # End of project section
                if current_project:
                    projects.append(current_project.strip())
                current_project = ""
                in_project_section = False
        
        if current_project:
            projects.append(current_project.strip())
        
        return projects[:5]  # Limit to 5 projects

    def link_skills_to_projects(self, resume_text: str, skill_data: dict) -> dict:
        """Link JD required skills to projects in resume for real-time exposure analysis"""
        resume_lower = self.preprocess(resume_text)
        projects = self.extract_projects(resume_text)
        
        result = {
            "skills_in_both": [],  # Skills mentioned in skill set AND used in projects
            "skills_in_skills_only": [],  # Skills in skill set but NOT in projects
            "skills_in_projects_only": [],  # Skills NOT in skill set but used in projects (bonus)
            "skills_neither": [],  # Required skills NOT in skill set AND NOT in projects
            "projects_count": len(projects),
        }
        
        # Get all required skills from JD
        jd_skills = skill_data['matched_in_skills'] + skill_data['missing']
        jd_skill_names = set(s['skill'] for s in jd_skills)
        
        # Check each required skill
        for skill_info in jd_skills:
            skill_name = skill_info['skill']
            in_skill_set = skill_info in skill_data['matched_in_skills']
            
            # Check if skill is mentioned in any project
            in_project = False
            project_evidence = ""
            for project in projects:
                if skill_name.lower() in project.lower():
                    in_project = True
                    project_evidence = project[:200]
                    break
            
            # Categorize based on presence in skill set and projects
            skill_entry = {
                "skill": skill_name,
                "category": skill_info['category']
            }
            
            if in_skill_set and in_project:
                skill_entry["project_evidence"] = project_evidence
                result["skills_in_both"].append(skill_entry)
            elif in_skill_set and not in_project:
                result["skills_in_skills_only"].append(skill_entry)
            elif not in_skill_set and in_project:
                skill_entry["project_evidence"] = project_evidence
                result["skills_in_projects_only"].append(skill_entry)
            else:  # not in_skill_set and not in_project
                result["skills_neither"].append(skill_entry)
        
        # Calculate scores
        total_required = len(jd_skills)
        both_count = len(result["skills_in_both"])
        skills_only_count = len(result["skills_in_skills_only"])
        projects_only_count = len(result["skills_in_projects_only"])
        neither_count = len(result["skills_neither"])
        
        # Real-time exposure score: prioritizes skills with project evidence
        # Both: 2 points, Skills only: 1 point, Projects only: 1.5 points, Neither: 0
        exposure_score = round(
            ((both_count * 2) + (skills_only_count * 1) + (projects_only_count * 1.5)) / 
            max(total_required * 2, 1) * 100, 1
        )
        
        result["exposure_score"] = min(100, exposure_score)
        result["breakdown"] = {
            "total_required_skills": total_required,
            "in_both": both_count,
            "in_skills_only": skills_only_count,
            "in_projects_only": projects_only_count,
            "neither": neither_count,
            "exposure_percentage": result["exposure_score"]
        }
        
        return result

    # ── 6. LLM Enhancement ─────────────────────────────────────────────────
    async def llm_enhance(
        self,
        resume_text: str,
        jd_text: str,
        weighted_score: float,
        skill_data: dict,
        skill_project_data: dict,
        is_fresher_role: bool = False,
    ) -> dict:
        # If no LLM client available, return structured analysis without Claude
        if not self.llm_available or self.client is None:
            return self._fallback_analysis(weighted_score, skill_data, skill_project_data, is_fresher_role)

        experience_rule = (
            'This is a fresher or entry-level role. Do not penalize the candidate for no work experience. Set experience_match to "Not required".'
            if is_fresher_role
            else "Evaluate experience normally for this role."
        )
        
        prompt = f"""You are an expert ATS (Applicant Tracking System) and career coach. Analyze this resume against the job description with focus on real-time skill exposure in projects.

RESUME:
{resume_text[:3000]}

JOB DESCRIPTION:
{jd_text[:2000]}

ADVANCED SCORING ANALYSIS:
This analysis uses a 5-layer scoring system:
- TF-IDF similarity (20% weight)
- Semantic embeddings (20% weight)  
- Skill matching with synonym mapping (30% weight)
- Real-time project exposure (20% weight)
- Keyword boosting for high-impact skills (10% weight)

PRELIMINARY SCORES:
- Final Weighted Composite Score: {weighted_score}%
- Skill Match: {skill_data['skill_match_percentage']}%
- Real-time Exposure Score: {skill_project_data['exposure_score']}%

SKILL ANALYSIS:
- Skills in both skill set AND projects: {len(skill_project_data['skills_in_both'])}
- Skills in skill set only: {len(skill_project_data['skills_in_skills_only'])}
- Skills in projects only: {len(skill_project_data['skills_in_projects_only'])}
- Skills neither: {len(skill_project_data['skills_neither'])}

EXPERIENCE RULE:
{experience_rule}

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "overall_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "summary": "<2-3 sentence honest assessment focusing on real project experience>",
  "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
  "improvements": ["<specific improvement 1>", "<specific improvement 2>", "<specific improvement 3>"],
  "experience_match": "<Poor|Fair|Good|Excellent|Not required>",
  "education_match": "<Poor|Fair|Good|Excellent>",
  "keyword_gaps": ["<missing keyword 1>", "<missing keyword 2>", "<missing keyword 3>"],
  "recommended_additions": "<1-2 sentences on what to add to resume, emphasizing project experience>",
  "interview_likelihood": "<Low|Medium|High|Very High>",
  "project_exposure_feedback": "<assessment of how well skills are demonstrated through projects>"
}}"""

        loop = asyncio.get_event_loop()

        def call_groq():
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            return response.choices[0].message.content

        try:
            response_text = await loop.run_in_executor(None, call_groq)
            # Clean and parse JSON
            response_text = response_text.strip()
            if response_text.startswith("```"): 
                response_text = re.sub(r'^```\w*\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
            return json.loads(response_text)
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return self._fallback_analysis(weighted_score, skill_data, skill_project_data, is_fresher_role)

    def _fallback_analysis(
        self,
        weighted_score: float,
        skill_data: dict,
        skill_project_data: dict,
        is_fresher_role: bool = False,
    ) -> dict:
        """Fallback analysis when LLM is not available"""
        skill_pct = skill_data['skill_match_percentage']
        exposure_pct = skill_project_data['exposure_score']
        matched_count = len(skill_data['matched_in_skills'])
        missing_count = len(skill_data['missing'])
        total_skills = skill_data['total_jd_skills']
        
        both_count = len(skill_project_data['skills_in_both'])
        skills_only_count = len(skill_project_data['skills_in_skills_only'])
        projects_only_count = len(skill_project_data['skills_in_projects_only'])
        
        # Overall score: blend weighted_score with skill match and exposure for robustness
        overall = round(weighted_score * 0.5 + skill_pct * 0.3 + exposure_pct * 0.2)
        overall = min(100, max(0, overall))
        
        # ATS score: focus more on keyword/skill coverage (what real ATS systems do)
        ats_score = round(skill_pct * 0.6 + exposure_pct * 0.4)
        ats_score = min(100, max(0, ats_score))
        
        # Determine interview likelihood
        if overall >= 80:
            likelihood = "Very High"
        elif overall >= 65:
            likelihood = "High"
        elif overall >= 50:
            likelihood = "Medium"
        else:
            likelihood = "Low"
        
        # Determine experience match. Freshers should not be penalized for no work history.
        if is_fresher_role:
            exp_match = "Not required"
        elif exposure_pct >= 80:
            exp_match = "Excellent"
        elif exposure_pct >= 65:
            exp_match = "Good"
        elif exposure_pct >= 45:
            exp_match = "Fair"
        else:
            exp_match = "Poor"
        
        # Build dynamic strengths based on actual data
        strengths = []
        if both_count > 0:
            strengths.append(f"Strong real-time exposure with {both_count} skills demonstrated in projects")
        if skill_pct >= 60:
            strengths.append(f"Strong skill coverage with {skill_pct}% match ({matched_count}/{total_skills} skills)")
        else:
            strengths.append(f"Partial skill coverage with {skill_pct}% match ({matched_count}/{total_skills} skills)")
        
        if matched_count >= 10:
            strengths.append(f"Broad technical expertise across {matched_count} required skills")
        elif matched_count >= 5:
            strengths.append(f"Solid foundation with {matched_count} matching skills")
        
        strengths.append("Well-aligned technical background")
        
        # Build dynamic improvements
        improvements = []
        if missing_count > 0:
            missing_names = [s['skill'] for s in skill_data['missing'][:3]]
            improvements.append(f"Add these missing skills to your resume: {', '.join(missing_names)}")
        if skills_only_count > 0:
            improvements.append(f"Demonstrate {skills_only_count} skills through project examples for real-time exposure")
        if missing_count > 3:
            improvements.append(f"{missing_count - 3} more skills could be highlighted or developed")
        improvements.append("Quantify achievements with metrics (e.g., improved X by Y%)")
        improvements.append("Tailor resume keywords to match the job description more closely")
        
        project_feedback = f"Project exposure analysis: {both_count} skills in both skill set and projects, {skills_only_count} skills need project demonstration, {projects_only_count} bonus skills found in projects."
        
        return {
            "overall_score": int(overall),
            "ats_score": int(ats_score),
            "summary": f"Analysis shows {matched_count} matched skills out of {total_skills} required with {exposure_pct}% real-time exposure through projects. {'Strong match for this role.' if overall >= 65 else 'Consider addressing the skill gaps and adding project examples.'}",
            "strengths": strengths[:3],
            "improvements": improvements[:3],
            "experience_match": exp_match,
            "education_match": "Good",
            "keyword_gaps": [s['skill'] for s in skill_data['missing'][:5]],
            "recommended_additions": f"Focus on adding: {', '.join([s['skill'] for s in skill_data['missing'][:3]])} and demonstrate skills through project examples." if skill_data['missing'] else "Resume is well-aligned with the job requirements. Consider adding more project details to showcase real-time exposure.",
            "interview_likelihood": likelihood,
            "project_exposure_feedback": project_feedback
        }

    # ── Main Pipeline ───────────────────────────────────────────────────────
    async def analyze(self, file_obj: io.BytesIO, filename: str, content_type: str, job_description: str) -> dict:
        # Step 1: Extract
        resume_text = self.extract_text(file_obj, filename, content_type)
        if not resume_text.strip():
            raise RuntimeError("Could not extract text from resume. Please use a text-based PDF or DOCX.")

        # Step 1.5: 🔥 NEW - Validate if document is a resume
        resume_validation = self.validate_resume(resume_text, filename)
        if not resume_validation["is_resume"]:
            raise RuntimeError(f"Uploaded document does not appear to be a resume. Confidence: {resume_validation['confidence']}%. Reasons: {', '.join(resume_validation['reasons'])}. Warnings: {', '.join(resume_validation['warnings'])}")

        # Step 2: Preprocess (with normalization & synonyms)
        fresher_role = self.is_fresher_role(job_description)
        experience_level = self.classify_experience_level(resume_text, job_description)
        resume_clean = self.preprocess(resume_text)
        jd_clean = self.preprocess(job_description)

        # Step 3: TF-IDF with n-grams
        tfidf_score = self.compute_tfidf_similarity(resume_clean, jd_clean)
        
        # Step 4: 🔥 NEW - Semantic embeddings similarity
        embeddings_score = self.compute_embeddings_similarity(resume_clean, jd_clean)
        
        # Step 5: Extract keywords
        resume_keywords = self.extract_keywords(resume_clean, top_n=12)
        jd_keywords = self.extract_keywords(jd_clean, top_n=12)

        # Step 6: Skill matching (with synonym support)
        skill_data = self.match_skills(resume_text, job_description)

        # Step 7: 🔥 NEW - Link skills to projects (real-time exposure analysis)
        skill_project_data = self.link_skills_to_projects(resume_text, skill_data)

        # Step 8: 🔥 NEW - Advanced weighted scoring system
        weighted_analysis = self.compute_weighted_score(
            tfidf_score,
            embeddings_score,
            skill_data["skill_match_percentage"],
            skill_project_data["exposure_score"],
            resume_clean,
            jd_clean
        )

        # Step 9: LLM enhancement (pass all new data)
        llm_data = await self.llm_enhance(
            resume_text, 
            job_description, 
            weighted_analysis["weighted_score"],
            skill_data,
            skill_project_data,
            fresher_role
        )

        return {
            "resume_name": filename,
            "candidate_name": self.extract_candidate_name(resume_text),
            "email": self.extract_email(resume_text),
            "phone_number": self.extract_phone(resume_text),
            "experience_years": None if fresher_role else self.extract_experience_years(resume_text),
            "experience_level": experience_level,
            "is_fresher_role": fresher_role,
            "tfidf_similarity": tfidf_score,
            "embeddings_similarity": embeddings_score,
            "weighted_score": weighted_analysis["weighted_score"],
            "score_breakdown": weighted_analysis,
            "skills": skill_data,
            "skill_project_analysis": skill_project_data,
            "resume_keywords": resume_keywords,
            "jd_keywords": jd_keywords,
            "llm_analysis": llm_data,
            "resume_length": len(resume_text.split()),
            "resume_text": resume_text,
            "resume_validation": resume_validation,
            "improvements_applied": [
                "✓ Synonym & Abbreviation Mapping (ML → Machine Learning)",
                "✓ N-gram Detection (phrases like 'Spring Boot', 'Machine Learning')",
                "✓ Text Normalization (SpringBoot → spring boot)",
                "✓ Semantic Embeddings (better than TF-IDF for meaning)",
                "✓ Advanced Weighted Scoring (TF-IDF + Embeddings + Skills + Exposure + Boost)",
                "✓ Real-time Project Exposure Analysis (skills in both skill set & projects)",
                "✓ LLM-powered Reasoning & Recommendations",
                "✓ Resume Document Validation",
            ]
        }
