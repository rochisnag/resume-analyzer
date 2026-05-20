import pdfplumber
import re
import os

def get_recent_education_years(text: str) -> bool:
    years = [int(y) for y in re.findall(r'\b(202[4-9]|2030)\b', text)]
    if years:
        for year in set(years):
            matches = re.finditer(r'\b' + str(year) + r'\b', text)
            for m in matches:
                start = max(0, m.start() - 100)
                end = min(len(text), m.end() + 100)
                context = text[start:end].lower()
                edu_keywords = [
                    "education", "degree", "bachelor", "master", "university", "college", 
                    "btech", "mtech", "b.tech", "m.tech", "bsc", "msc", "b.e", "b.s", "m.s", 
                    "m.sc", "b.sc", "graduate", "graduation", "class", "school"
                ]
                if any(ek in context for ek in edu_keywords):
                    return True
    return False

def extract_experience_number(text: str):
    matches = list(re.finditer(r'\b(\d{1,2})(?:\+)?\s*(?:years?|yrs?)\b', text, re.IGNORECASE))
    for match in matches:
        val = float(match.group(1))
        # Clamp/ignore false positives > 20 years
        if val > 20:
            continue
        return val
    return None

def has_professional_title(text: str, title_pattern: str) -> bool:
    text_lower = text.lower()
    matches = list(re.finditer(title_pattern, text_lower))
    for match in matches:
        word = match.group(1) if match.lastindex else match.group(0)
        start = match.start()
        end = match.end()
        
        context_start = max(0, start - 40)
        context_end = min(len(text_lower), end + 40)
        context = text_lower[context_start:context_end]
        
        student_keywords = ["student", "club", "society", "committee", "volunteer", "association", "extracurricular", "university", "college", "school", "forge"]
        if any(sk in context for sk in student_keywords):
            continue
            
        if word in ["senior", "sr"]:
            secondary_keywords = ["secondary", "school", "student", "year", "thesis", "project", "design", "sec", "seco", "secodary", "class", "12th", "xii"]
            if any(sk in context for sk in secondary_keywords):
                continue
            
        if word == "executive":
            summary_keywords = ["summary", "profile", "presence", "briefing", "report", "assistant", "support"]
            if any(sk in context for sk in summary_keywords):
                continue
        
        if word == "principal":
            tech_keywords = ["component", "components", "analysis", "investigator", "school", "college"]
            if any(tk in context for tk in tech_keywords):
                continue
                
        return True
    return False

def classify_experience_level_improved(resume_text: str, job_description: str = "") -> str:
    # 1. Fresher role check (based on job description)
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
    if any(re.search(pattern, jd_lower) for pattern in fresher_patterns):
        return "junior"

    # 2. Years of experience check
    years = extract_experience_number(resume_text)
    if years is not None:
        if years <= 2:
            return "junior"
        if years <= 5:
            return "mid"
        if years <= 10:
            return "senior"
        return "executive"

    # 3. Recent graduation/education check (2024-2030)
    # If education is completed or will be completed in 2024-2030, they are juniors/freshers
    if get_recent_education_years(resume_text):
        return "junior"

    # 4. Keyword matches
    is_exec = has_professional_title(resume_text, r"\b(executive|director|head of|vp|vice president|principal)\b")
    if is_exec:
        return "executive"
        
    is_senior = has_professional_title(resume_text, r"\b(senior|sr\.?|lead|staff)\b")
    if is_senior:
        return "senior"

    if re.search(r"\b(intern|internship|fresher|entry[-\s]?level|junior|student)\b", resume_text.lower()):
        return "junior"
        
    return "junior"

# Test on the batch of 15 resumes
files = [f for f in os.listdir("uploads") if f.endswith(".pdf")]
for idx, f in enumerate(files[:15]):
    pdf_path = os.path.join("uploads", f)
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        level = classify_experience_level_improved(text)
        years = extract_experience_number(text)
        print(f"File: {f.split('_', 1)[-1]:<40} -> Classified: {level:<10} (Years: {years})")
    except Exception as e:
        print(f"Error on {f}: {e}")
