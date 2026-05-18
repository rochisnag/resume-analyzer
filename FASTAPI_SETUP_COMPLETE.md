# FastAPI + SQLAlchemy + PostgreSQL - Complete Setup Guide

## 🎯 What You're Getting

You now have a **production-ready Python FastAPI backend** with:

- **FastAPI**: Modern async web framework with auto-documentation
- **SQLAlchemy ORM**: Type-safe database operations
- **PostgreSQL**: Persistent data storage
- **Pydantic**: Request/response validation
- **Repository Pattern**: Clean data access abstraction
- **Service Layer**: Organized business logic
- **Full CRUD Operations**: Create, Read, Update, Delete analyses
- **Analytics Queries**: Statistics and aggregations
- **Automatic Documentation**: Swagger UI and ReDoc

---

## 📁 Backend Structure

```
backend/
├── main.py                 # FastAPI app with 5 endpoints
├── models.py               # SQLAlchemy ORM models
├── schemas.py              # Pydantic validation schemas
├── database.py             # Database config & session management
├── repository.py           # Data access layer (Repository pattern)
├── service.py              # Business logic layer
├── analyzer.py             # Resume analysis (existing)
├── requirements.txt        # Python dependencies (updated)
├── .env.example            # Environment variables template
├── docker-compose.yml      # PostgreSQL + Adminer containers
├── setup-postgres.sh       # Linux/macOS setup
├── setup-postgres.ps1      # Windows PowerShell setup
└── README.md               # Backend documentation
```

---

## 🚀 Installation (Choose One Method)

### **Method 1: Docker (Recommended - Works Everywhere)**

```bash
cd backend

# 1. Start PostgreSQL container
docker-compose up -d

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Create .env from template
cp .env.example .env

# 4. Start FastAPI server
python main.py
```

**Access Points:**
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Database UI: http://localhost:8080 (Adminer)

---

### **Method 2: Windows Native Setup**

```powershell
cd backend

# 1. Setup PostgreSQL (auto-creates database and user)
.\setup-postgres.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
Copy-Item .env.example .env

# 4. Start server
python main.py
```

**Manual Setup (if script fails):**
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Install with default settings (superuser password: `postgres`)
3. Run in PowerShell:
   ```powershell
   psql -U postgres <<EOF
   CREATE USER resume_user WITH PASSWORD 'resume_password';
   CREATE DATABASE resume_analyzer_db OWNER resume_user;
   GRANT ALL PRIVILEGES ON DATABASE resume_analyzer_db TO resume_user;
   EOF
   ```

---

### **Method 3: Linux/macOS Native Setup**

```bash
cd backend

# 1. Setup PostgreSQL
chmod +x setup-postgres.sh
./setup-postgres.sh

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
cp .env.example .env

# 4. Start server
python main.py
```

---

## ⚙️ Configuration

### Environment File (`.env`)

```bash
# Copy template
cp .env.example .env
```

Edit `.env` with your settings:

```env
# PostgreSQL Connection String
# Format: postgresql://[user]:[password]@[host]:[port]/[database]
DATABASE_URL=postgresql://resume_user:resume_password@localhost:5432/resume_analyzer_db

# Groq API Key (optional - app works without it with fallback analysis)
GROQ_API_KEY=your_groq_api_key_here

# Application Settings
DEBUG=False
ENVIRONMENT=development
```

**Connection String Examples:**
```
Local Docker:     postgresql://resume_user:resume_password@localhost:5432/resume_analyzer_db
AWS RDS:          postgresql://user:pass@mydb.abc123.us-east-1.rds.amazonaws.com:5432/db
Railway:          postgresql://user:pass@monorail.proxy.rlwy.net:5432/db
Heroku Postgres:  postgresql://user:pass@ec2-xyz.compute-1.amazonaws.com:5432/db
```

---

## 🔌 API Endpoints

### 1. Analyze Resume
```bash
curl -X POST http://localhost:8000/analyze \
  -F "resume=@path/to/resume.pdf" \
  -F "job_description=Senior Python Developer with AWS and FastAPI experience..."
```

**Response:**
```json
{
  "overall_score": 82.5,
  "tfidf_score": 78.0,
  "embeddings_score": 80.5,
  "skill_match": {
    "percentage": 85.0,
    "matched_skills": ["python", "fastapi", "postgresql"],
    "missing_skills": ["kubernetes"],
    "project_linked_skills": ["python", "fastapi"]
  },
  "keyword_boost": 90.0,
  "ats_score": 80.0,
  "summary": "Strong match for the position...",
  "strengths": [
    "Excellent Python skills match",
    "FastAPI and PostgreSQL experience demonstrated"
  ],
  "improvements": [
    "Consider gaining Kubernetes experience"
  ],
  "interview_likelihood": "High",
  "experience_match": "Excellent",
  "analysis_id": 1
}
```

### 2. Get Analysis History
```bash
# Get all analyses
curl http://localhost:8000/analyze/history

# Filter by resume name
curl "http://localhost:8000/analyze/history?resume_name=john_doe"

# With pagination
curl "http://localhost:8000/analyze/history?skip=0&limit=50"
```

### 3. Get Specific Analysis
```bash
curl http://localhost:8000/analyze/1
```

### 4. Get Statistics
```bash
curl http://localhost:8000/statistics
```

Response:
```json
{
  "total_analyses": 42,
  "average_score": 75.3,
  "max_score": 95.5,
  "min_score": 32.1
}
```

### 5. Health Check
```bash
curl http://localhost:8000/health
```

---

## 📊 Using the Database Directly

### Connect with psql
```bash
psql -U resume_user -d resume_analyzer_db -h localhost
```

### Useful Queries
```sql
-- View all analyses
SELECT id, resume_name, overall_score, interview_likelihood, created_at 
FROM resume_analysis 
ORDER BY created_at DESC;

-- Get high-scoring matches
SELECT * FROM resume_analysis 
WHERE overall_score >= 75 
ORDER BY overall_score DESC;

-- Get recent analyses (last 7 days)
SELECT * FROM resume_analysis 
WHERE created_at >= NOW() - INTERVAL '7 days' 
ORDER BY created_at DESC;

-- Statistics
SELECT 
  COUNT(*) as total,
  AVG(overall_score) as avg_score,
  MAX(overall_score) as max_score,
  MIN(overall_score) as min_score
FROM resume_analysis;

-- Analyses by interview likelihood
SELECT 
  interview_likelihood,
  COUNT(*) as count,
  AVG(overall_score) as avg_score
FROM resume_analysis
GROUP BY interview_likelihood;

-- Find analyses for specific job title
SELECT * FROM resume_analysis 
WHERE job_title ILIKE '%python%' 
ORDER BY created_at DESC;
```

---

## 🧪 Python Script Examples

### Example 1: Query Database Programmatically
```python
from database import SessionLocal
from repository import ResumeAnalysisRepository

# Get database session
db = SessionLocal()

# Create repository
repo = ResumeAnalysisRepository(db)

# Get top 10 high-scoring analyses
top_scores = repo.get_high_scoring(min_score=80, limit=10)
for analysis in top_scores:
    print(f"ID: {analysis.id}")
    print(f"Resume: {analysis.resume_name}")
    print(f"Score: {analysis.overall_score}")
    print(f"Interview Likelihood: {analysis.interview_likelihood}")
    print("---")

# Get statistics
stats = repo.get_statistics()
print(f"\nTotal Analyses: {stats['total_analyses']}")
print(f"Average Score: {stats['average_score']}")
print(f"Max Score: {stats['max_score']}")
print(f"Min Score: {stats['min_score']}")

db.close()
```

### Example 2: Using Service Layer
```python
from database import SessionLocal
from service import AnalysisService

db = SessionLocal()
service = AnalysisService(db)

# Get specific analysis
analysis = service.get_analysis(1)
if analysis:
    print(f"Resume: {analysis.resume_name}")
    print(f"Summary: {analysis.summary}")
    print(f"Interview Likelihood: {analysis.interview_likelihood}")

# Get history
history = service.get_analysis_history(resume_name="john", skip=0, limit=50)
print(f"Total matches: {history['total']}")
for analysis in history['analyses']:
    print(f"- {analysis.resume_name}: {analysis.overall_score}")

db.close()
```

### Example 3: Batch Processing
```python
from database import SessionLocal
from repository import ResumeAnalysisRepository
from datetime import datetime, timedelta

db = SessionLocal()
repo = ResumeAnalysisRepository(db)

# Get recent analyses
start_date = datetime.utcnow() - timedelta(days=30)
end_date = datetime.utcnow()
count = repo.count_by_date_range(start_date, end_date)

print(f"Analyses in last 30 days: {count}")

# Get recent
recent = repo.get_recent(days=7, limit=100)
for analysis in recent:
    print(f"{analysis.created_at} - {analysis.resume_name}: {analysis.overall_score}")

db.close()
```

---

## 🔄 Data Flow Diagram

```
┌─────────────────────────────────────────────────────┐
│ Frontend (React + Vite)                             │
│ - Upload resume                                     │
│ - Enter job description                             │
└────────────────┬────────────────────────────────────┘
                 │ HTTP POST /analyze
                 ▼
┌─────────────────────────────────────────────────────┐
│ FastAPI Application (main.py)                       │
│ - Receive multipart form data                       │
│ - Validate with Pydantic                            │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ Analyzer (analyzer.py)                              │
│ - Extract text from resume                          │
│ - Calculate all scores                              │
│ - Get LLM insights                                  │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ Service Layer (service.py)                          │
│ - Prepare data for database                         │
│ - Call repository save method                       │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ Repository Layer (repository.py)                    │
│ - Convert DTO to ORM model                          │
│ - Insert into database                              │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ SQLAlchemy ORM (models.py)                          │
│ - Generate SQL INSERT statement                     │
│ - Execute query                                     │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────┐
│ PostgreSQL Database                                 │
│ - Store analysis result                             │
│ - Return ID                                         │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼ (Response with analysis_id)
         Frontend displays results
         User can view history anytime
```

---

## 🎯 Repository Methods Available

```python
repo = ResumeAnalysisRepository(db)

# CRUD Operations
repo.create(analysis_data)              # Create new
repo.get_by_id(1)                       # Read by ID
repo.update(1, updated_data)            # Update
repo.delete(1)                          # Delete

# Query Operations
repo.get_all(skip=0, limit=100)        # All (paginated)
repo.get_by_resume_name("john")         # Filter by name
repo.get_by_job_title("python")         # Filter by title
repo.get_by_interview_likelihood("High") # Filter by likelihood

# Analytics
repo.get_high_scoring(min_score=80)    # High scores
repo.get_recent(days=7)                 # Recent analyses
repo.get_top_scored(limit=10)           # Top 10
repo.get_statistics()                   # Stats (count, avg, max, min)
repo.count_by_date_range(start, end)   # Count in range
```

---

## 🐛 Troubleshooting

### Error: "Connection refused" for PostgreSQL
```bash
# Check PostgreSQL is running
psql -U postgres -c "SELECT 1"

# If not running, start it:
# Docker:
docker-compose up -d

# macOS:
brew services start postgresql@15

# Linux:
sudo systemctl start postgresql
```

### Error: "Module not found" (ModuleNotFoundError)
```bash
# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|sqlalchemy|pydantic"
```

### Error: "Permission denied" (setup script)
```bash
# Make scripts executable
chmod +x backend/setup-postgres.sh

# Then run
./backend/setup-postgres.sh
```

### Error: "Port 8000 already in use"
```bash
# Use different port in main.py
# Change last line:
uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

# Or kill existing process:
# Linux/macOS:
lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Error: "Tables not created"
```bash
# Tables auto-create on first run
# If not, manually initialize:
python -c "from database import init_db; init_db()"
```

---

## 📚 Tech Stack Reference

| Technology | Version | Purpose |
|-----------|---------|---------|
| **FastAPI** | 0.115.0 | Web framework |
| **Uvicorn** | 0.30.6 | ASGI server |
| **SQLAlchemy** | 2.0.23 | ORM |
| **Pydantic** | 2.5.0 | Validation |
| **psycopg2** | 2.9.9 | PostgreSQL driver |
| **PostgreSQL** | 15 | Database |
| **Python** | 3.9+ | Runtime |

---

## ✨ Key Features Enabled

✅ **Full CRUD Operations** - Create, Read, Update, Delete analyses  
✅ **Advanced Queries** - Filtering, sorting, pagination  
✅ **Analytics** - Statistics, aggregations, trending  
✅ **Data Persistence** - Permanent storage in PostgreSQL  
✅ **Type Safety** - Pydantic + SQLAlchemy  
✅ **Auto Documentation** - Swagger UI + ReDoc  
✅ **Async Support** - Non-blocking FastAPI  
✅ **Error Handling** - Comprehensive messages  
✅ **Logging** - Debug and info levels  
✅ **Connection Pooling** - Optimized performance  
✅ **Migration Ready** - Production-ready setup  
✅ **Docker Support** - Easy containerization  

---

## 🚀 Production Deployment

### Using Gunicorn (Production ASGI Server)
```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker Deployment
```bash
# Build image
docker build -t resume-analyzer .

# Run container
docker run -e DATABASE_URL=postgresql://... \
  -p 8000:8000 \
  resume-analyzer
```

### Cloud Deployment (Railway, Render, Heroku)
1. Push code to GitHub
2. Connect repository to hosting platform
3. Set environment variables (DATABASE_URL, GROQ_API_KEY)
4. Deploy!

---

## ✅ Verification Checklist

- [ ] PostgreSQL installed and running
- [ ] Database `resume_analyzer_db` created
- [ ] User `resume_user` created with password
- [ ] Python dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created from `.env.example`
- [ ] `.env` contains valid DATABASE_URL
- [ ] Application starts: `python main.py`
- [ ] No errors in console output
- [ ] Health endpoint works: `curl http://localhost:8000/health`
- [ ] Swagger UI loads: http://localhost:8000/docs
- [ ] Can upload resume via Swagger
- [ ] Results display correctly
- [ ] Analysis ID returned
- [ ] Results persist in `/analyze/history`
- [ ] Data appears in PostgreSQL

---

## 🎉 You're Ready!

Your Resume Analyzer backend now has:

✅ FastAPI with 5 RESTful endpoints  
✅ SQLAlchemy ORM for PostgreSQL  
✅ Pydantic validation on all inputs  
✅ Repository pattern for clean data access  
✅ Service layer for business logic  
✅ Full CRUD operations  
✅ Advanced query capabilities  
✅ Analytics and statistics  
✅ Automatic API documentation  
✅ Docker and native setup options  
✅ Production-ready architecture  

**Next Step**: Start the backend and upload your first resume!

```bash
python main.py
# Visit http://localhost:8000/docs
```

Happy analyzing! 🚀
