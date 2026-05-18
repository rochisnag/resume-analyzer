# Resume Analyzer - FastAPI + SQLAlchemy ORM + PostgreSQL

## 🎯 Architecture Overview

```
FastAPI (Web Framework)
    ↓
Pydantic (Validation & Serialization)
    ↓
SQLAlchemy ORM (Database Abstraction)
    ↓
PostgreSQL (Data Storage)
```

## 📋 Project Structure

```
backend/
├── main.py                 # FastAPI application & endpoints
├── database.py             # Database configuration & session management
├── models.py               # SQLAlchemy ORM models
├── schemas.py              # Pydantic validation schemas
├── repository.py           # Repository pattern for data access
├── service.py              # Business logic layer
├── analyzer.py             # Resume analysis logic (existing)
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── setup-postgres.sh       # Linux/macOS setup script
└── setup-postgres.ps1      # Windows setup script
```

## 🛠️ Key Components

### 1. **FastAPI Application** (`main.py`)
- RESTful API endpoints
- CORS middleware configuration
- Database dependency injection
- Request/response validation with Pydantic
- Error handling and logging

### 2. **Database Layer** (`database.py`)
- SQLAlchemy engine configuration
- Session factory with connection pooling
- Database initialization
- Dependency injection for getting sessions

### 3. **ORM Models** (`models.py`)
- `ResumeAnalysis` SQLAlchemy model
- Auto-generated table schema
- Indexes for query optimization
- Timestamps (created_at, updated_at)

### 4. **Pydantic Schemas** (`schemas.py`)
- `AnalysisRequest` - Request validation
- `AnalysisResponse` - Response serialization
- `ResumeAnalysisCreate` - Create DTO
- `ResumeAnalysisRead` - Read DTO with ORM conversion
- `SkillMatchDetail` - Nested skill details

### 5. **Repository Layer** (`repository.py`)
- `ResumeAnalysisRepository` class
- CRUD operations (Create, Read, Update, Delete)
- Custom queries (filtering, sorting, pagination)
- Statistics and analytics queries
- Follows Repository Pattern for data access abstraction

### 6. **Service Layer** (`service.py`)
- `AnalysisService` business logic
- Orchestrates repository operations
- Converts between DTOs and models
- High-level API for application logic

## 🚀 Quick Start

### Native PostgreSQL

**Windows (PowerShell):**
```powershell
# Setup PostgreSQL
.\setup-postgres.ps1

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run application
python main.py
```

**Linux/macOS (Bash):**
```bash
# Setup PostgreSQL
chmod +x setup-postgres.sh
./setup-postgres.sh

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run application
python main.py
```

## 📊 Database Schema

### resume_analysis Table

```sql
CREATE TABLE resume_analysis (
    id SERIAL PRIMARY KEY,
    resume_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    overall_score FLOAT NOT NULL,
    tfidf_score FLOAT NOT NULL,
    embeddings_score FLOAT NOT NULL,
    skill_match_percentage FLOAT NOT NULL,
    exposure_score FLOAT NOT NULL,
    keyword_boost FLOAT NOT NULL,
    ats_score FLOAT NOT NULL,
    matched_skills TEXT,
    missing_skills TEXT,
    project_linked_skills TEXT,
    strengths TEXT,
    improvements TEXT,
    interview_likelihood VARCHAR(50),
    experience_match VARCHAR(50),
    summary TEXT,
    resume_text TEXT,
    job_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_resume_name ON resume_analysis(resume_name);
CREATE INDEX idx_job_title ON resume_analysis(job_title);
CREATE INDEX idx_overall_score_desc ON resume_analysis(overall_score DESC);
CREATE INDEX idx_created_at_desc ON resume_analysis(created_at DESC);
CREATE INDEX idx_interview_likelihood ON resume_analysis(interview_likelihood);
```

## 🔌 API Endpoints

### POST /analyze
Analyze a resume against a job description.

**Request:**
```bash
curl -X POST http://localhost:8000/analyze \
  -F "resume=@resume.pdf" \
  -F "job_description=Senior Developer with Python and AWS experience..."
```

**Response:**
```json
{
  "overall_score": 82.5,
  "tfidf_score": 78.0,
  "embeddings_score": 80.5,
  "skill_match": {
    "percentage": 85.0,
    "matched_skills": ["python", "aws"],
    "missing_skills": ["kubernetes"],
    "project_linked_skills": ["python"]
  },
  "keyword_boost": 90.0,
  "ats_score": 80.0,
  "summary": "Strong match...",
  "strengths": [...],
  "improvements": [...],
  "interview_likelihood": "High",
  "experience_match": "Excellent",
  "analysis_id": 1
}
```

### GET /analyze/history
Get analysis history with optional filtering.

```bash
# Get all analyses
curl http://localhost:8000/analyze/history

# Filter by resume name
curl "http://localhost:8000/analyze/history?resume_name=john"

# With pagination
curl "http://localhost:8000/analyze/history?skip=0&limit=50"
```

### GET /analyze/{analysis_id}
Get specific analysis by ID.

```bash
curl http://localhost:8000/analyze/1
```

### GET /statistics
Get analysis statistics.

```bash
curl http://localhost:8000/statistics
```

Returns:
```json
{
  "total_analyses": 42,
  "average_score": 75.3,
  "max_score": 95.5,
  "min_score": 32.1
}
```

## 🔐 Environment Configuration

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# PostgreSQL Connection
DATABASE_URL=postgresql://resume_user:resume_password@localhost:5432/resume_analyzer_db

# Groq API Key (optional)
GROQ_API_KEY=your_api_key_here

# Application Settings
DEBUG=False
ENVIRONMENT=development
```

## 📦 Dependencies

```
FastAPI==0.115.0              # Web framework
uvicorn==0.30.6               # ASGI server
SQLAlchemy==2.0.23            # ORM
psycopg2-binary==2.9.9        # PostgreSQL driver
Pydantic==2.5.0               # Validation & serialization
pydantic-settings==2.1.0      # Settings management
python-dotenv==1.0.0          # Environment variables
pdfplumber==0.11.4            # PDF extraction
python-docx==1.1.2            # DOCX extraction
scikit-learn==1.5.1           # TF-IDF vectorization
sentence-transformers==3.0.1  # Semantic embeddings
groq==0.9.0                   # LLM API
```

## 🔍 Data Flow

```
1. User uploads resume + job description
   ↓
2. FastAPI receives request
   ↓
3. Pydantic validates input
   ↓
4. Analyzer processes resume
   ↓
5. Analysis results created
   ↓
6. Service saves to database via Repository
   ↓
7. SQLAlchemy ORM inserts to PostgreSQL
   ↓
8. Response returned with analysis_id
   ↓
9. Results persisted in database
```

## 🎯 Design Patterns Used

### 1. **Repository Pattern**
- `ResumeAnalysisRepository` abstracts database operations
- Clean separation of data access logic
- Easy to test and mock

### 2. **Service Layer Pattern**
- `AnalysisService` contains business logic
- Orchestrates repository operations
- Converts between DTOs and models

### 3. **Dependency Injection**
- FastAPI's `Depends()` for session injection
- Clean and testable code
- Resources properly managed

### 4. **DTO (Data Transfer Object)**
- Pydantic schemas separate API contracts from models
- Request/response validation
- Type safety and documentation

### 5. **ORM Pattern**
- SQLAlchemy abstracts SQL operations
- Type-safe database access
- Query builder for complex queries

## 🧪 Example Queries

### Get high-scoring analyses
```python
from database import SessionLocal
from repository import ResumeAnalysisRepository

db = SessionLocal()
repo = ResumeAnalysisRepository(db)
high_scores = repo.get_high_scoring(min_score=75, limit=10)
```

### Get recent analyses
```python
from datetime import datetime, timedelta

recent = repo.get_recent(days=7, limit=50)
```

### Get by resume name
```python
analyses = repo.get_by_resume_name("john_doe", skip=0, limit=100)
```

### Get statistics
```python
stats = repo.get_statistics()
print(f"Total: {stats['total_analyses']}, Avg Score: {stats['average_score']}")
```

## 🐛 Troubleshooting

### Error: "Could not connect to database"
```bash
# Check PostgreSQL is running
psql -U resume_user -d resume_analyzer_db

# Verify DATABASE_URL in .env
cat .env
```

### Error: "Module not found"
```bash
# Install dependencies
pip install -r requirements.txt
```

### Port already in use
```bash
# Use different port
python main.py --port 8001

# Or edit main.py last line
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
```

### Database tables not created
```bash
# Python will auto-create on first run
# If not, manually initialize:
python -c "from database import init_db; init_db()"
```

## 📚 Documentation

- **FastAPI Docs**: http://localhost:8000/docs (Swagger UI)
- **FastAPI ReDoc**: http://localhost:8000/redoc (ReDoc UI)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## ✨ Key Features

✅ **Type-Safe ORM**: SQLAlchemy with full type hints  
✅ **Input Validation**: Pydantic for request/response  
✅ **Data Persistence**: All results stored in PostgreSQL  
✅ **Query Optimization**: Indexes on frequently queried columns  
✅ **Repository Pattern**: Clean data access abstraction  
✅ **Service Layer**: Business logic separated from API  
✅ **Dependency Injection**: Clean request handling  
✅ **Async Support**: FastAPI async/await  
✅ **Auto Documentation**: Swagger UI and ReDoc  
✅ **Error Handling**: Comprehensive error messages  
✅ **Logging**: Debug and info level logging  
✅ **Local PostgreSQL**: Native database setup  

## 🚀 Production Deployment

### Environment Variables
```bash
export DATABASE_URL=postgresql://user:pass@prod-host:5432/db
export GROQ_API_KEY=your_api_key
export ENVIRONMENT=production
```

### Run with Gunicorn (Production ASGI Server)
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

---

**Status**: ✨ Ready for production!
