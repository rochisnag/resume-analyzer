# PostgreSQL Database Schema for Resume Analyzer

## 📊 **Database Design Overview**

This schema supports:
- **100+ Resume Processing**: Scalable storage and analysis
- **Outlook Email Integration**: Email-triggered analysis workflows
- **Multi-JD Analysis**: Compare resumes against multiple job descriptions
- **Historical Tracking**: Analysis history and performance metrics
- **Skill Intelligence**: Dynamic skill extraction and categorization

---

## 🗂️ **Core Tables**

### **1. candidates**
```sql
CREATE TABLE candidates (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(50),
    linkedin_url VARCHAR(500),
    github_url VARCHAR(500),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_candidates_email ON candidates(email);
CREATE INDEX idx_candidates_created_at ON candidates(created_at);
```

### **2. resumes**
```sql
CREATE TABLE resumes (
    id SERIAL PRIMARY KEY,
    candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000),
    file_size_bytes INTEGER,
    content_type VARCHAR(100),
    extracted_text TEXT,
    word_count INTEGER,
    validation_confidence DECIMAL(5,2), -- 0.00 to 100.00
    validation_reasons JSONB, -- Array of validation reasons
    upload_source VARCHAR(50) DEFAULT 'web', -- 'web', 'email', 'api'
    email_message_id VARCHAR(500), -- Outlook Message-ID for email integration
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending' -- 'pending', 'processing', 'completed', 'failed'
);

-- Indexes
CREATE INDEX idx_resumes_candidate_id ON resumes(candidate_id);
CREATE INDEX idx_resumes_status ON resumes(status);
CREATE INDEX idx_resumes_created_at ON resumes(created_at);
CREATE INDEX idx_resumes_email_message_id ON resumes(email_message_id);
```

### **3. job_descriptions**
```sql
CREATE TABLE job_descriptions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    description TEXT NOT NULL,
    requirements TEXT,
    location VARCHAR(255),
    salary_range VARCHAR(100),
    job_type VARCHAR(50), -- 'full-time', 'part-time', 'contract', 'freelance'
    experience_level VARCHAR(50), -- 'entry', 'mid', 'senior', 'lead', 'executive'
    source VARCHAR(50) DEFAULT 'manual', -- 'manual', 'api', 'scraped'
    source_url VARCHAR(1000),
    created_by INTEGER REFERENCES candidates(id), -- Who created this JD
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_job_descriptions_company ON job_descriptions(company);
CREATE INDEX idx_job_descriptions_is_active ON job_descriptions(is_active);
CREATE INDEX idx_job_descriptions_created_at ON job_descriptions(created_at);
```

---

## 📈 **Analysis Results Tables**

### **4. analysis_results**
```sql
CREATE TABLE analysis_results (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE CASCADE,
    job_description_id INTEGER REFERENCES job_descriptions(id) ON DELETE CASCADE,

    -- Core Scores
    overall_score DECIMAL(5,2) CHECK (overall_score >= 0 AND overall_score <= 100),
    ats_score DECIMAL(5,2) CHECK (ats_score >= 0 AND ats_score <= 100),
    tfidf_similarity DECIMAL(5,2) CHECK (tfidf_similarity >= 0 AND tfidf_similarity <= 100),
    embeddings_similarity DECIMAL(5,2) CHECK (embeddings_similarity >= 0 AND embeddings_similarity <= 100),

    -- Component Breakdown
    score_breakdown JSONB, -- Detailed component scores
    skill_match_percentage DECIMAL(5,2),
    exposure_score DECIMAL(5,2),
    keyword_boost DECIMAL(5,2),

    -- LLM Analysis Results
    llm_summary TEXT,
    llm_strengths JSONB, -- Array of strengths
    llm_improvements JSONB, -- Array of improvements
    experience_match VARCHAR(20), -- 'Poor', 'Fair', 'Good', 'Excellent'
    education_match VARCHAR(20),
    interview_likelihood VARCHAR(20), -- 'Low', 'Medium', 'High', 'Very High'
    project_exposure_feedback TEXT,
    keyword_gaps JSONB, -- Array of missing keywords
    recommended_additions TEXT,

    -- Metadata
    processing_time_seconds DECIMAL(5,2),
    model_version VARCHAR(50) DEFAULT 'v1.0',
    llm_model_used VARCHAR(100) DEFAULT 'llama-3.3-70b-versatile',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(resume_id, job_description_id) -- One analysis per resume-JD pair
);

-- Indexes
CREATE INDEX idx_analysis_results_resume_id ON analysis_results(resume_id);
CREATE INDEX idx_analysis_results_jd_id ON analysis_results(job_description_id);
CREATE INDEX idx_analysis_results_overall_score ON analysis_results(overall_score);
CREATE INDEX idx_analysis_results_created_at ON analysis_results(created_at);
```

---

## 🛠️ **Skill & Project Intelligence Tables**

### **5. skills_master**
```sql
CREATE TABLE skills_master (
    id SERIAL PRIMARY KEY,
    skill_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL, -- 'Programming Languages', 'Web Frameworks', etc.
    synonyms JSONB, -- Array of synonyms/alternatives
    importance_level INTEGER DEFAULT 1 CHECK (importance_level >= 1 AND importance_level <= 5),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_skills_master_category ON skills_master(category);
CREATE INDEX idx_skills_master_name ON skills_master(skill_name);
```

### **6. resume_skills**
```sql
CREATE TABLE resume_skills (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills_master(id) ON DELETE CASCADE,
    source VARCHAR(20) NOT NULL, -- 'extracted', 'matched', 'manual'
    confidence DECIMAL(3,2) DEFAULT 1.0, -- 0.00 to 1.00
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(resume_id, skill_id)
);

-- Indexes
CREATE INDEX idx_resume_skills_resume_id ON resume_skills(resume_id);
CREATE INDEX idx_resume_skills_skill_id ON resume_skills(skill_id);
```

### **7. projects**
```sql
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    resume_id INTEGER REFERENCES resumes(id) ON DELETE CASCADE,
    title VARCHAR(500),
    description TEXT,
    technologies JSONB, -- Array of technologies used
    duration_months INTEGER,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT false,
    project_url VARCHAR(1000),
    github_url VARCHAR(1000),
    extracted_text TEXT, -- Raw extracted project text
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_projects_resume_id ON projects(resume_id);
CREATE INDEX idx_projects_start_date ON projects(start_date);
```

### **8. project_skills**
```sql
CREATE TABLE project_skills (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skills_master(id) ON DELETE CASCADE,
    evidence_text TEXT, -- The text that proves this skill was used
    confidence DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(project_id, skill_id)
);

-- Indexes
CREATE INDEX idx_project_skills_project_id ON project_skills(project_id);
CREATE INDEX idx_project_skills_skill_id ON project_skills(skill_id);
```

---

## 📧 **Email Integration Tables**

### **9. email_triggers**
```sql
CREATE TABLE email_triggers (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(500) UNIQUE NOT NULL, -- Outlook Message-ID
    sender_email VARCHAR(255) NOT NULL,
    subject VARCHAR(1000),
    received_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'

    -- Linked entities
    candidate_id INTEGER REFERENCES candidates(id),
    resume_id INTEGER REFERENCES resumes(id),
    job_description_id INTEGER REFERENCES job_descriptions(id),

    -- Processing results
    analysis_result_id INTEGER REFERENCES analysis_results(id),
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_email_triggers_message_id ON email_triggers(message_id);
CREATE INDEX idx_email_triggers_status ON email_triggers(status);
CREATE INDEX idx_email_triggers_received_at ON email_triggers(received_at);
```

### **10. email_attachments**
```sql
CREATE TABLE email_attachments (
    id SERIAL PRIMARY KEY,
    email_trigger_id INTEGER REFERENCES email_triggers(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(1000),
    content_type VARCHAR(100),
    file_size_bytes INTEGER,
    is_resume BOOLEAN DEFAULT false, -- Whether this attachment is a resume
    processed_resume_id INTEGER REFERENCES resumes(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_email_attachments_email_trigger_id ON email_attachments(email_trigger_id);
CREATE INDEX idx_email_attachments_is_resume ON email_attachments(is_resume);
```

---

## 📊 **Analytics & Reporting Tables**

### **11. analysis_metrics**
```sql
CREATE TABLE analysis_metrics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_resumes_processed INTEGER DEFAULT 0,
    total_analyses_performed INTEGER DEFAULT 0,
    average_processing_time DECIMAL(5,2),
    average_overall_score DECIMAL(5,2),
    top_skills_detected JSONB, -- Most common skills found
    common_keyword_gaps JSONB, -- Most common missing keywords
    llm_usage_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(date)
);

-- Indexes
CREATE INDEX idx_analysis_metrics_date ON analysis_metrics(date);
```

### **12. system_logs**
```sql
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'DEBUG'
    component VARCHAR(100), -- 'analyzer', 'email_processor', 'api', etc.
    message TEXT NOT NULL,
    metadata JSONB, -- Additional context data
    user_id INTEGER REFERENCES candidates(id),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_system_logs_level ON system_logs(level);
CREATE INDEX idx_system_logs_component ON system_logs(component);
CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_user_id ON system_logs(user_id);
```

---

## 🔗 **Relationships & Constraints**

### **Foreign Key Relationships:**
- `resumes.candidate_id` → `candidates.id`
- `analysis_results.resume_id` → `resumes.id`
- `analysis_results.job_description_id` → `job_descriptions.id`
- `resume_skills.resume_id` → `resumes.id`
- `resume_skills.skill_id` → `skills_master.id`
- `projects.resume_id` → `resumes.id`
- `project_skills.project_id` → `projects.id`
- `project_skills.skill_id` → `skills_master.id`
- `email_triggers.candidate_id` → `candidates.id`
- `email_triggers.resume_id` → `resumes.id`
- `email_triggers.job_description_id` → `job_descriptions.id`
- `email_attachments.email_trigger_id` → `email_triggers.id`

### **Unique Constraints:**
- `(resume_id, job_description_id)` in `analysis_results`
- `(resume_id, skill_id)` in `resume_skills`
- `(project_id, skill_id)` in `project_skills`
- `email_triggers.message_id` unique

---

## 🚀 **Usage Patterns**

### **Email-Triggered Analysis Flow:**
1. **Email Received** → Store in `email_triggers`
2. **Attachment Processing** → Extract resume → Store in `resumes`
3. **Candidate Matching** → Find/create `candidates` record
4. **Analysis Execution** → Generate `analysis_results`
5. **Report Generation** → Email results back

### **Bulk Resume Processing:**
1. **Batch Upload** → Multiple `resumes` records
2. **Parallel Analysis** → Multiple `analysis_results` per JD
3. **Skill Aggregation** → Populate `resume_skills` and `project_skills`
4. **Metrics Update** → Update `analysis_metrics`

### **Reporting Queries:**
```sql
-- Top candidates for a job
SELECT c.*, ar.overall_score, ar.interview_likelihood
FROM candidates c
JOIN resumes r ON c.id = r.candidate_id
JOIN analysis_results ar ON r.id = ar.resume_id
WHERE ar.job_description_id = ?
ORDER BY ar.overall_score DESC;

-- Skill gap analysis
SELECT sm.skill_name, COUNT(*) as gap_count
FROM skills_master sm
JOIN resume_skills rs ON sm.id = rs.skill_id
WHERE rs.resume_id NOT IN (
    SELECT resume_id FROM analysis_results
    WHERE skill_match_percentage > 80
)
GROUP BY sm.skill_name
ORDER BY gap_count DESC;
```

---

## 🛠 **Database Optimization**

### **Partitioning Strategy:**
```sql
-- Partition analysis_results by month for performance
CREATE TABLE analysis_results_y2024m01 PARTITION OF analysis_results
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Partition system_logs by month
CREATE TABLE system_logs_y2024m01 PARTITION OF system_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### **Materialized Views for Reporting:**
```sql
CREATE MATERIALIZED VIEW candidate_rankings AS
SELECT
    c.id,
    c.first_name || ' ' || c.last_name as full_name,
    c.email,
    AVG(ar.overall_score) as avg_score,
    MAX(ar.created_at) as last_analysis,
    COUNT(ar.id) as total_analyses
FROM candidates c
JOIN resumes r ON c.id = r.candidate_id
JOIN analysis_results ar ON r.id = ar.resume_id
GROUP BY c.id, c.first_name, c.last_name, c.email;

-- Refresh daily
REFRESH MATERIALIZED VIEW CONCURRENTLY candidate_rankings;
```

This schema provides a robust foundation for scaling to 100+ resumes with comprehensive analysis tracking, email integration, and advanced reporting capabilities.</content>
<parameter name="filePath">c:\Users\Dell\Downloads\resume-analyzer\DATABASE_SCHEMA.md