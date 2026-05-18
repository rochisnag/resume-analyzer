from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    database_url: str = os.getenv("DATABASE_URL", "postgresql://resume_user:resume_password@localhost:5432/resume_analyzer_db")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# SQLAlchemy base class for models
Base = declarative_base()

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Test connections before using them
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    ensure_resume_analysis_columns()


def ensure_resume_analysis_columns():
    """Add newer leaderboard fields when an existing local database is reused."""
    inspector = inspect(engine)
    if "resume_analysis" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("resume_analysis")
    }
    required_columns = {
        "resume_file_path": "VARCHAR(500)",
        "candidate_name": "VARCHAR(255)",
        "email": "VARCHAR(255)",
        "phone_number": "VARCHAR(50)",
        "experience_years": "VARCHAR(50)",
        "experience_level": "VARCHAR(20)",
    }
    missing_columns = [
        (name, column_type)
        for name, column_type in required_columns.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return

    with engine.begin() as connection:
        for name, column_type in missing_columns:
            connection.execute(
                text(f"ALTER TABLE resume_analysis ADD COLUMN {name} {column_type}")
            )
