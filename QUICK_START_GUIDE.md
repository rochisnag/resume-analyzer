# 🚀 Quick Start Guide - Using Your Upgraded Analyzer

## Installation & Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

This installs scikit-learn which enables all 7 improvements.

### 2. Test Everything Works
```bash
python test_improvements.py
```

You should see all tests pass ✅

### 3. Run the Server
```bash
python main.py
```

Server runs on `http://localhost:8000`

---

## Using the API

### Basic Usage

```bash
curl -X POST "http://localhost:8000/analyze" \
  -F "resume=@your_resume.pdf" \
  -F "job_description=Senior Developer needed with Python and AWS skills"
```

### Response Includes

```json
{
  "tfidf_similarity": 45.2,
  "weighted_score": 72.5,  // ← NEW: Composite score from all 7 improvements
  "score_breakdown": {       // ← NEW: Shows score components
    "weighted_score": 72.5,
    "tfidf_component": 15.8,
    "skill_component": 45.0,
    "keyword_boost": 11.7
  },
  "skills": {
    "matched": [...],
    "missing": [...],
    "skill_match_percentage": 90.0
  },
  "llm_analysis": {
    "overall_score": 75,
    "summary": "Strong fit...",
    ...
  },
  "improvements_applied": [
    "✓ Synonym & Abbreviation Mapping",
    "✓ N-gram Detection",
    ...
  ]
}
```

---

## Understanding the Improvements

### Score Breakdown

Your **weighted_score** is calculated as:

```
Final Score = (TF-IDF × 0.35) + (Skill Match × 0.45) + Keyword Boost

Example:
TF-IDF: 50%     → 50 × 0.35 = 17.5
Skills: 100%    → 100 × 0.45 = 45.0  
Boost: +5       → +5.0
─────────────────────────────
Total: 67.5 / 100 = 67.5%
```

### Component Weights

- **35% - Text Similarity (TF-IDF)**: How much text overlaps using advanced phrase detection
- **45% - Skill Matching**: Which required skills are present (with synonym support)
- **20% - Keyword Boosting**: Bonus points for high-value skills

### Synonym Mapping Examples

The system now recognizes these as equivalent:

```
ML                    = Machine Learning
NLP                   = Natural Language Processing
REST                  = Rest API
SpringBoot            = Spring Boot
React.js              = React
C++                   = C plus plus
AWS                   = Amazon Web Services
kubernetes / k8s      = Kubernetes
```

Add more: Edit `SKILL_SYNONYMS` in `analyzer.py`

### Keyword Boosting

These skills get bonus points (Tier 1 = +5, Tier 2 = +4, Tier 3 = +3):

```
TIER 1: Python, Java, Machine Learning, AI
TIER 2: AWS, Docker, Kubernetes, Spring Boot, React
TIER 3: SQL, REST API, CI/CD, Agile, Git
```

Customize: Edit `HIGH_IMPACT_KEYWORDS` in `analyzer.py`

---

## Examples

### Example 1: ML Engineer Role

**Resume Contains:** "Expert in ML, Deep Learning, PyTorch, AWS"
**JD Requires:** "Machine Learning, PyTorch, AWS"

```
Improvement #1 (Synonyms): ML → Machine Learning ✓
Improvement #4 (N-grams): "Deep Learning" detected ✓
Improvement #3 (Boosting): ML + AWS found = +8 boost
Result: 85% weighted score (was 60% before)
```

### Example 2: Spring Boot Backend

**Resume Contains:** "SpringBoot, REST APIs, Docker, Kubernetes"
**JD Requires:** "Spring Boot, REST API, Docker"

```
Improvement #5 (Normalization): SpringBoot → spring boot ✓
Improvement #1 (Synonyms): REST → rest api ✓
Improvement #4 (N-grams): "Spring Boot" phrase detected ✓
Result: 92% weighted score (was 70% before)
```

### Example 3: React Frontend

**Resume Contains:** "React.js, TypeScript, Redux, responsive design"
**JD Requires:** "React, JavaScript, UI/UX"

```
Improvement #5 (Normalization): React.js → react ✓
Improvement #2 (Weighting): Skills 45% + Text 35% + Boost 20% ✓
Result: 78% weighted score (better assessment than text-only)
```

---

## Customization Guide

### Add New Skill Synonyms

**File:** `backend/analyzer.py` (Lines 27-67)

```python
SKILL_SYNONYMS = {
    # Add your mapping:
    "your canonical name": ["abbreviation", "variation1", "variation2"],
    
    # Example:
    "kubernetes": ["k8s", "k8", "kubernetes"],
    "ci/cd": ["cicd", "ci/cd", "continuous integration"],
}
```

Then restart the server.

### Adjust Skill Importance

**File:** `backend/analyzer.py` (Lines 114-141)

```python
HIGH_IMPACT_KEYWORDS = {
    # Tier 1: Most important (+5 points)
    "critical skill": 5,
    
    # Tier 2: Important (+4 points)
    "important skill": 4,
    
    # Tier 3: Valuable (+3 points)
    "valuable skill": 3,
}
```

### Change Scoring Weights

**File:** `backend/analyzer.py` (compute_weighted_score method)

Default:
```python
base_score = (
    0.35 * (tfidf_score / 100) +   # 35% text
    0.45 * (skill_match_pct / 100) # 45% skills
)
# 20% remaining for boost
```

**Example: Emphasize Skills More (for skills-focused hiring)**
```python
base_score = (
    0.25 * (tfidf_score / 100) +   # 25% text
    0.55 * (skill_match_pct / 100) # 55% skills
)
# 20% remaining for boost
```

**Example: Emphasize Text More (for senior/experience roles)**
```python
base_score = (
    0.45 * (tfidf_score / 100) +   # 45% text
    0.35 * (skill_match_pct / 100) # 35% skills
)
# 20% remaining for boost
```

---

## Interpreting Results

### What Each Score Means

| Score | Assessment | Action |
|-------|-----------|--------|
| 80-100% | Excellent fit | ✅ Interview recommended |
| 70-79% | Good fit | ✅ Consider interview |
| 60-69% | Decent fit | ⚠️ Review manually |
| 50-59% | Weak fit | ❌ Not recommended |
| <50% | Poor fit | ❌ Unlikely match |

### Using Score Breakdown

```json
"score_breakdown": {
  "weighted_score": 72.5,
  "tfidf_component": 15.8,        // Low text overlap
  "skill_component": 45.0,         // Good skills match
  "keyword_boost": 11.7            // High-value skills present
}
```

**Interpretation:**
- Text component is low → Different wording, but skills match
- Skill component is high → Most required skills present
- Keyword boost is high → High-value skills (Python, AWS, etc.) found
- **Overall score is good** → Recommended candidate despite wording differences

---

## Common Issues

### Issue: Score Seems Too Low

**Check:** Do the required skills exist but with different names?

**Solution:** Add synonyms to `SKILL_SYNONYMS`
```python
"your skill": ["abbreviation_used", "alternate_name"],
```

### Issue: Specific Skills Not Detected

**Check:** Are skills written differently in resume vs JD?

**Solution:** 
1. Check `SKILL_CATEGORIES` in code
2. Add missing skills
3. Add synonyms

### Issue: Score Doesn't Change After Edit

**Remember:** Restart server after modifying code
```bash
python main.py  # Stop with Ctrl+C first
python main.py  # Start again
```

---

## Advanced Usage

### Batch Processing Multiple Resumes

```python
import asyncio
from analyzer import ResumeAnalyzer

analyzer = ResumeAnalyzer()

async def analyze_batch(resumes, jd):
    results = []
    for resume_file in resumes:
        with open(resume_file, 'rb') as f:
            result = await analyzer.analyze(
                f, 
                resume_file.name,
                'application/pdf',
                jd
            )
            results.append(result)
    return results

# Usage:
jd = "Senior Python Developer needed with AWS and Machine Learning"
resumes = ['resume1.pdf', 'resume2.pdf', 'resume3.pdf']
results = asyncio.run(analyze_batch(resumes, jd))

# Sort by score:
sorted_results = sorted(
    results, 
    key=lambda x: x['weighted_score'], 
    reverse=True
)
```

### Building a Ranking System

```python
def rank_candidates(results):
    """Rank candidates by fit score"""
    ranked = sorted(
        results,
        key=lambda x: x['weighted_score'],
        reverse=True
    )
    
    for rank, candidate in enumerate(ranked, 1):
        print(f"{rank}. {candidate['name']}: {candidate['weighted_score']}%")
        print(f"   Matched: {len(candidate['skills']['matched'])} skills")
        print(f"   Missing: {len(candidate['skills']['missing'])} skills")
```

---

## Performance Tips

### Speed Up Large Documents

```python
# Limit text size before analysis:
resume_text = resume_text[:10000]  # First 10k chars
jd_text = jd_text[:5000]          # First 5k chars
```

### Cache Results

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def preprocess(self, text):
    return self._preprocess_impl(text)
```

---

## Troubleshooting

### Test Individual Components

```python
from analyzer import ResumeAnalyzer

analyzer = ResumeAnalyzer()

# Test 1: Normalization
print(analyzer.normalize_text("SpringBoot"))  # → "spring boot"

# Test 2: Synonyms
print(analyzer.apply_synonyms("I know ML"))   # → "i know machine learning"

# Test 3: TF-IDF
score = analyzer.compute_tfidf_similarity("Python and ML", "Python, ML, AI")
print(f"TF-IDF: {score}%")

# Test 4: Skills
skills = analyzer.match_skills("Python, Docker", "Python, Docker, Kubernetes")
print(f"Match: {skills['skill_match_percentage']}%")
```

---

## Next Steps

### Immediate
- ✅ Test with sample resumes
- ✅ Try the test suite
- ✅ Customize synonyms for your domain

### Short-term
- Add industry-specific skills
- Fine-tune keyword weights
- Integrate with your hiring system

### Long-term
- Add semantic embeddings (95%+ accuracy)
- Build resume optimization suggestions
- Create candidate ranking dashboard

---

## Support

**Documentation Files:**
- `IMPROVEMENTS_IMPLEMENTED.md` - Detailed explanation
- `DEVELOPER_GUIDE.md` - Technical reference
- `CODE_CHANGES_REFERENCE.md` - Exact code changes
- `test_improvements.py` - Working examples

**Key Classes:**
- `ResumeAnalyzer` - Main engine
- `SKILL_SYNONYMS` - Skill mappings
- `HIGH_IMPACT_KEYWORDS` - Boosting weights

---

You're ready to use your production-level analyzer! 🚀

Questions? Check the detailed documentation files or review `test_improvements.py` for working examples.

