from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from analyzer import ResumeAnalyzer
import asyncio
import base64
import io
import os
import json
import imaplib
import smtplib
import hashlib
import secrets
import string
import email
import httpx
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parseaddr, parsedate_to_datetime
from dotenv import load_dotenv
from database import SessionLocal, get_db, init_db
from service import AnalysisService
from schemas import AnalysisHistory, AuthResponse, ErrorResponse, JobRolesSaveRequest, MailPullRequest, ShortlistEmailRequest, UserCreate, UserForgotPassword, UserLogin, UserRead
from models import JobRole, JobRoleRequirement, ResumeAnalysis, User, InboundEmail
from typing import Optional
import logging
from pathlib import Path
from uuid import uuid4
import re
from datetime import datetime, timezone

load_dotenv(override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
TOKEN_CACHE_PATH = Path(__file__).resolve().parent / ".msal_token_cache.bin"
MAIL_POLL_INTERVAL_SECONDS = int(os.getenv("MAIL_POLL_INTERVAL_SECONDS", "120"))
MAIL_AUTO_POLL_ENABLED = os.getenv("MAIL_AUTO_POLL_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
mail_poll_task = None
mail_poll_lock = asyncio.Lock()


def safe_upload_name(filename: str) -> str:
    """Create a local filename that keeps the original extension."""
    original = Path(filename or "resume").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original).stem).strip("._") or "resume"
    suffix = Path(original).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        suffix = ".txt"
    return f"{uuid4().hex}_{stem}{suffix}"


def decode_mail_header(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for text, encoding in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(text)
    return "".join(parts)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = hashed_password.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            120000,
        )
        return digest.hex() == digest_hex
    except Exception:
        return False


def find_user_by_login_identifier(db, identifier: str):
    login_id = identifier.lower().strip()
    if not login_id:
        return None

    lookup_values = [login_id]
    if "@" not in login_id:
        lookup_values.append(f"{login_id}@tektalis.com")

    return db.query(User).filter(User.email.in_(lookup_values)).first()


def is_user_creation_admin(user: User | None) -> bool:
    return bool(
        user
        and user.is_active
        and user.role == "admin"
    )


def generate_temporary_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def score_analysis_payload(
    result: dict,
    resume_name: str,
    saved_resume_path: Path,
    job_description: str,
    role_title: str | None,
    db,
    received_at: datetime | None = None,
):
    llm_analysis = result.get("llm_analysis", {})
    skills = result.get("skills", {})
    skill_project_analysis = result.get("skill_project_analysis", {})

    def skill_names(items):
        return [
            item.get("skill", str(item)) if isinstance(item, dict) else str(item)
            for item in items or []
        ]

    matched_skill_names = skill_names(skills.get("matched_in_skills") or skills.get("matched"))
    missing_skill_names = skill_names(skills.get("missing"))
    project_skill_names = skill_names(
        (skill_project_analysis.get("skills_in_both") or [])
        + (skill_project_analysis.get("skills_in_projects_only") or [])
    )

    service = AnalysisService(db)
    analysis_data = {
        "resume_name": resume_name,
        "resume_file_path": str(saved_resume_path),
        "candidate_name": result.get("candidate_name"),
        "email": result.get("email"),
        "phone_number": result.get("phone_number"),
        "experience_years": result.get("experience_years"),
        "experience_level": result.get("experience_level"),
        "job_title": (role_title or "Unassigned role")[:255],
        "overall_score": llm_analysis.get("overall_score", result.get("weighted_score", 0)),
        "tfidf_score": result.get("tfidf_similarity", 0),
        "embeddings_score": result.get("embeddings_similarity", 0),
        "skill_match_percentage": skills.get("skill_match_percentage", 0),
        "exposure_score": skill_project_analysis.get("exposure_score", 0),
        "keyword_boost": result.get("score_breakdown", {}).get("keyword_boost", 0),
        "ats_score": llm_analysis.get("ats_score", 0),
        "matched_skills": ",".join(matched_skill_names),
        "missing_skills": ",".join(missing_skill_names),
        "project_linked_skills": ",".join(project_skill_names),
        "strengths": "; ".join(llm_analysis.get("strengths", [])),
        "improvements": "; ".join(llm_analysis.get("improvements", [])),
        "interview_likelihood": llm_analysis.get("interview_likelihood", ""),
        "experience_match": llm_analysis.get("experience_match", ""),
        "summary": llm_analysis.get("summary", ""),
        "resume_text": result.get("resume_text", ""),
        "job_description": job_description,
    }
    if received_at:
        analysis_data["created_at"] = received_at
        analysis_data["updated_at"] = received_at
    saved = service.save_analysis(analysis_data)
    result["analysis_id"] = saved.id
    return saved, result


def role_payload_to_job_description(role: dict) -> str:
    weights = role.get("weights") or {}
    return "\n".join([
        role.get("jobDescription") or "",
        f"Configured role: {role.get('roleTitle') or 'Selected role'}.",
        f"Experience level: {role.get('experienceLevel') or 'junior'}.",
        f"Experience years: {role.get('minExperience') or 0}.",
        (
            "Scoring weights: "
            f"projects {weights.get('projects', 0)}%, "
            f"skills {weights.get('skills', 0)}%, "
            f"education {weights.get('education', 0)}%."
        ),
    ])


def match_role_for_resume(resume_text: str, roles: list[dict]) -> dict | None:
    if not roles:
        return None

    resume_lower = resume_text.lower()
    best_role = None
    best_score = -1.0
    resume_level = analyzer.classify_experience_level(resume_text, "")

    for role in roles:
        title = str(role.get("roleTitle") or "")
        skills = [str(skill) for skill in role.get("requiredSkills") or []]
        keywords = [str(keyword) for keyword in role.get("projectKeywords") or []]
        description = str(role.get("jobDescription") or "")
        role_text = " ".join([title, description, *skills, *keywords])
        role_level = str(role.get("experienceLevel") or "junior").lower()

        title_score = 25 if title and title.lower() in resume_lower else 0
        skill_hits = sum(1 for skill in skills if skill and skill.lower() in resume_lower)
        keyword_hits = sum(1 for keyword in keywords if keyword and keyword.lower() in resume_lower)
        skill_score = (skill_hits / max(len(skills), 1)) * 55
        keyword_score = (keyword_hits / max(len(keywords), 1)) * 15
        semantic_score = analyzer.compute_tfidf_similarity(resume_text, role_text) * 0.05 if role_text.strip() else 0
        experience_score = 30 if role_level == resume_level else -35
        score = title_score + skill_score + keyword_score + semantic_score + experience_score

        if score > best_score:
            best_score = score
            best_role = role

    return best_role


def parse_roles_json(roles_json: str | None) -> list[dict]:
    if not roles_json:
        return []
    try:
        parsed_roles = json.loads(roles_json)
        return parsed_roles if isinstance(parsed_roles, list) else []
    except json.JSONDecodeError:
        return []


def active_role_payloads(db) -> list[dict]:
    roles = (
        db.query(JobRole)
        .filter(JobRole.intake_paused == False)  # noqa: E712
        .order_by(JobRole.created_at.asc(), JobRole.id.asc())
        .all()
    )
    return [role_to_payload(role) for role in roles]


def automatic_mail_payload(db) -> MailPullRequest | None:
    roles = active_role_payloads(db)
    if not roles:
        return None
    primary_role = roles[0]
    return MailPullRequest(
        job_description=primary_role.get("jobDescription") or role_payload_to_job_description(primary_role),
        role_title=primary_role.get("roleTitle"),
        roles_json=json.dumps(roles),
        expected_experience_level=primary_role.get("experienceLevel") or "junior",
        min_fit_score=float(primary_role.get("minFitScore") or 80),
        max_messages=20,
        send_shortlist_emails=False,
    )


def parse_graph_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def matched_mail_role(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    payload: MailPullRequest,
) -> tuple[str, str | None, float]:
    job_description = payload.job_description
    role_title = payload.role_title
    min_fit_score = payload.min_fit_score
    roles = parse_roles_json(payload.roles_json)
    if not roles:
        return job_description, role_title, min_fit_score

    resume_text = analyzer.extract_text(io.BytesIO(file_bytes), filename, content_type or "")
    matched_role = match_role_for_resume(resume_text, roles)
    if matched_role:
        job_description = role_payload_to_job_description(matched_role)
        role_title = matched_role.get("roleTitle") or role_title
        min_fit_score = float(matched_role.get("minFitScore") or min_fit_score)
    return job_description, role_title, min_fit_score


def mail_settings() -> dict:
    return {
        "imap_host": os.getenv("IMAP_HOST", "outlook.office365.com"),
        "imap_port": int(os.getenv("IMAP_PORT", "993")),
        "smtp_host": os.getenv("SMTP_HOST", "smtp.office365.com"),
        "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        "auth_method": os.getenv("MAIL_AUTH_METHOD", "basic").lower(),
        "username": os.getenv("MAIL_USERNAME", ""),
        "password": os.getenv("MAIL_PASSWORD", ""),
        "from_email": os.getenv("MAIL_FROM", os.getenv("MAIL_USERNAME", "")),
        "tenant_id": os.getenv("MS_TENANT_ID", "common"),
        "client_id": os.getenv("MS_CLIENT_ID", ""),
        "client_secret": os.getenv("MS_CLIENT_SECRET", ""),
    }


def get_microsoft_access_token(settings: dict, scopes: list[str]) -> str:
    try:
        import msal
    except ImportError as exc:
        raise RuntimeError("Install msal first: pip install -r backend/requirements.txt") from exc

    if not settings["client_id"]:
        raise RuntimeError("MS_CLIENT_ID must be configured for Microsoft OAuth2 mail login")

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())

    app = msal.PublicClientApplication(
        settings["client_id"],
        authority=f"https://login.microsoftonline.com/{settings['tenant_id']}",
        token_cache=cache,
    )

    accounts = app.get_accounts(username=settings["username"])
    result = app.acquire_token_silent(scopes, account=accounts[0] if accounts else None)
    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Could not start Microsoft device login: {flow}")
        logger.warning(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    if cache.has_state_changed:
        TOKEN_CACHE_PATH.write_text(cache.serialize())

    if "access_token" not in result:
        raise RuntimeError(result.get("error_description") or "Microsoft OAuth2 token request failed")
    return result["access_token"]


def xoauth2_string(username: str, access_token: str) -> str:
    return f"user={username}\x01auth=Bearer {access_token}\x01\x01"


def get_graph_access_token(settings: dict, delegated_scopes: list[str]) -> tuple[str, bool]:
    try:
        import msal
    except ImportError as exc:
        raise RuntimeError("Install msal first: pip install -r backend/requirements.txt") from exc

    if not settings["client_id"]:
        raise RuntimeError("MS_CLIENT_ID must be configured for Microsoft Graph mail")

    authority = f"https://login.microsoftonline.com/{settings['tenant_id']}"
    if settings.get("client_secret"):
        app = msal.ConfidentialClientApplication(
            settings["client_id"],
            authority=authority,
            client_credential=settings["client_secret"],
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" not in result:
            raise RuntimeError(result.get("error_description") or "Microsoft Graph app token request failed")
        return result["access_token"], True

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_PATH.exists():
        cache.deserialize(TOKEN_CACHE_PATH.read_text())

    scopes = [scope if scope.startswith("https://") else f"https://graph.microsoft.com/{scope}" for scope in delegated_scopes]
    app = msal.PublicClientApplication(
        settings["client_id"],
        authority=authority,
        token_cache=cache,
    )

    accounts = app.get_accounts(username=settings["username"])
    result = app.acquire_token_silent(scopes, account=accounts[0] if accounts else None)
    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Could not start Microsoft device login: {flow}")
        logger.warning(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    if cache.has_state_changed:
        TOKEN_CACHE_PATH.write_text(cache.serialize())

    if "access_token" not in result:
        raise RuntimeError(result.get("error_description") or "Microsoft Graph delegated token request failed")
    return result["access_token"], False


def graph_user_path(settings: dict, app_token: bool) -> str:
    if app_token:
        return f"/users/{settings['username']}"
    return "/me"


def graph_request(method: str, path_or_url: str, token: str, **kwargs):
    url = path_or_url if path_or_url.startswith("https://") else f"https://graph.microsoft.com/v1.0{path_or_url}"
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(timeout=45) as client:
        response = client.request(method, url, headers=headers, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(f"Graph API {method} {url} failed: {response.status_code} {response.text}")
    return response


def graph_send_shortlist_email(
    settings: dict,
    token: str,
    app_token: bool,
    to_email: str,
    candidate_name: str | None,
    role_title: str | None,
    score: float,
):
    name = candidate_name or "Candidate"
    body = (
        f"Hi {name},\n\n"
        f"Thank you for applying. Your resume has been shortlisted for {role_title or 'the role'} "
        f"with a fit score of {round(score, 1)}.\n\n"
        "Our team will contact you with the next steps.\n\n"
        "Regards,\nRecruitment Team"
    )
    payload = {
        "message": {
            "subject": f"Shortlisted for {role_title or 'the role'}",
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": True,
    }
    graph_request("POST", f"{graph_user_path(settings, app_token)}/sendMail", token, json=payload)


def graph_send_password_reset_email(
    settings: dict,
    token: str,
    app_token: bool,
    to_email: str,
    temporary_password: str,
):
    payload = {
        "message": {
            "subject": "Resume Analyzer password reset",
            "body": {
                "contentType": "Text",
                "content": (
                    "Hi,\n\n"
                    "Your Resume Analyzer password was reset.\n\n"
                    f"Temporary password: {temporary_password}\n\n"
                    "Use this password to sign in, then keep it somewhere secure.\n\n"
                    "Regards,\nResume Analyzer Team"
                ),
            },
            "toRecipients": [{"emailAddress": {"address": to_email}}],
        },
        "saveToSentItems": True,
    }
    graph_request("POST", f"{graph_user_path(settings, app_token)}/sendMail", token, json=payload)


def authenticate_imap(mailbox: imaplib.IMAP4_SSL, settings: dict):
    if settings["auth_method"] == "oauth2":
        token = get_microsoft_access_token(
            settings,
            ["https://outlook.office.com/IMAP.AccessAsUser.All", "offline_access"],
        )
        mailbox.authenticate("XOAUTH2", lambda _: xoauth2_string(settings["username"], token))
        return
    mailbox.login(settings["username"], settings["password"])


def authenticate_smtp(smtp: smtplib.SMTP, settings: dict):
    if settings["auth_method"] == "oauth2":
        token = get_microsoft_access_token(
            settings,
            ["https://outlook.office.com/SMTP.Send", "offline_access"],
        )
        auth = base64.b64encode(xoauth2_string(settings["username"], token).encode()).decode()
        code, response = smtp.docmd("AUTH", "XOAUTH2 " + auth)
        if code != 235:
            raise RuntimeError(f"SMTP OAuth2 authentication failed: {code} {response!r}")
        return
    smtp.login(settings["username"], settings["password"])


def send_shortlist_email(to_email: str, candidate_name: str | None, role_title: str | None, score: float):
    settings = mail_settings()
    if not settings["username"] or not settings["from_email"]:
        raise RuntimeError("MAIL_USERNAME and MAIL_FROM must be configured")
    if settings["auth_method"] == "graph":
        token, app_token = get_graph_access_token(settings, ["Mail.Send", "offline_access"])
        graph_send_shortlist_email(settings, token, app_token, to_email, candidate_name, role_title, score)
        return
    if settings["auth_method"] != "oauth2" and not settings["password"]:
        raise RuntimeError("MAIL_PASSWORD must be configured for basic mail login")

    message = EmailMessage()
    message["From"] = settings["from_email"]
    message["To"] = to_email
    message["Subject"] = f"Shortlisted for {role_title or 'the role'}"
    name = candidate_name or "Candidate"
    message.set_content(
        f"Hi {name},\n\n"
        f"Thank you for applying. Your resume has been shortlisted for {role_title or 'the role'} "
        f"with a fit score of {round(score, 1)}.\n\n"
        "Our team will contact you with the next steps.\n\n"
        "Regards,\nRecruitment Team"
    )

    with smtplib.SMTP(settings["smtp_host"], settings["smtp_port"], timeout=30) as smtp:
        smtp.starttls()
        authenticate_smtp(smtp, settings)
        smtp.send_message(message)


def send_password_reset_email(to_email: str, temporary_password: str):
    settings = mail_settings()
    if not settings["username"] or not settings["from_email"]:
        raise RuntimeError("MAIL_USERNAME and MAIL_FROM must be configured")
    if settings["auth_method"] == "graph":
        token, app_token = get_graph_access_token(settings, ["Mail.Send", "offline_access"])
        graph_send_password_reset_email(settings, token, app_token, to_email, temporary_password)
        return
    if settings["auth_method"] != "oauth2" and not settings["password"]:
        raise RuntimeError("MAIL_PASSWORD must be configured for basic mail login")

    message = EmailMessage()
    message["From"] = settings["from_email"]
    message["To"] = to_email
    message["Subject"] = "Resume Analyzer password reset"
    message.set_content(
        "Hi,\n\n"
        "Your Resume Analyzer password was reset.\n\n"
        f"Temporary password: {temporary_password}\n\n"
        "Use this password to sign in, then keep it somewhere secure.\n\n"
        "Regards,\nResume Analyzer Team"
    )

    with smtplib.SMTP(settings["smtp_host"], settings["smtp_port"], timeout=30) as smtp:
        smtp.starttls()
        authenticate_smtp(smtp, settings)
        smtp.send_message(message)


def role_to_payload(role: JobRole) -> dict:
    requirements = role.requirements or []
    return {
        "id": str(role.id),
        "active": not role.intake_paused,
        "roleTitle": role.title,
        "minExperience": str(role.min_experience or 0),
        "experienceLevel": (role.filter_experience_levels or "junior").split(",")[0] or "junior",
        "minFitScore": role.min_fit_score if role.min_fit_score is not None else 80,
        "requiredSkills": [
            item.label for item in requirements if item.req_type == "skill"
        ],
        "projectKeywords": [
            item.label for item in requirements if item.req_type == "keyword"
        ],
        "weights": {
            "projects": role.weight_projects,
            "skills": role.weight_skills,
            "education": role.weight_education,
        },
        "jobDescription": role.description or "",
    }


def upsert_role_requirements(db, role: JobRole, labels: list[str], req_type: str):
    existing = {item.label.lower(): item for item in role.requirements if item.req_type == req_type}
    wanted = []
    for label in labels:
        clean = str(label).strip()
        if clean and clean.lower() not in {item.lower() for item in wanted}:
            wanted.append(clean)

    for item in list(role.requirements):
        if item.req_type == req_type and item.label.lower() not in {label.lower() for label in wanted}:
            db.delete(item)

    for label in wanted:
        if label.lower() not in existing:
            db.add(JobRoleRequirement(
                job_role_id=role.id,
                label=label,
                weight=1.0,
                req_type=req_type,
            ))

app = FastAPI(
    title="Resume Analyzer API",
    version="1.0.0",
    description="Resume analysis with FastAPI, SQLAlchemy ORM, and PostgreSQL"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analyzer
analyzer = ResumeAnalyzer()


async def run_automatic_mail_poll_once():
    if mail_poll_lock.locked():
        logger.info("Skipping mail poll because a previous poll is still running")
        return
    async with mail_poll_lock:
        db = SessionLocal()
        try:
            settings = mail_settings()
            if settings["auth_method"] != "graph":
                logger.info("Automatic mail poll skipped because MAIL_AUTH_METHOD is %s", settings["auth_method"])
                return
            if not settings["username"] or not settings["client_id"]:
                logger.info("Automatic mail poll skipped because Graph mailbox settings are incomplete")
                return
            payload = automatic_mail_payload(db)
            if not payload:
                logger.info("Automatic mail poll skipped because no active job roles are configured")
                return
            result = await pull_mail_graph(payload, settings, db)
            logger.info(
                "Automatic mail poll complete: processed=%s saved=%s skipped=%s",
                result.get("processed_count", 0),
                result.get("saved_analysis_count", 0),
                len(result.get("skipped", [])),
            )
        except Exception as exc:
            logger.error("Automatic mail poll failed: %s", exc)
        finally:
            db.close()


async def automatic_mail_poll_loop():
    while True:
        await run_automatic_mail_poll_once()
        await asyncio.sleep(MAIL_POLL_INTERVAL_SECONDS)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    global mail_poll_task
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    logger.info(f"Mail auth method: {mail_settings()['auth_method']}")
    if MAIL_AUTO_POLL_ENABLED and mail_poll_task is None:
        mail_poll_task = asyncio.create_task(automatic_mail_poll_loop())
        logger.info("Automatic Graph mail poller started; interval=%s seconds", MAIL_POLL_INTERVAL_SECONDS)


@app.on_event("shutdown")
async def shutdown_event():
    global mail_poll_task
    if mail_poll_task:
        mail_poll_task.cancel()
        try:
            await mail_poll_task
        except asyncio.CancelledError:
            pass
        mail_poll_task = None


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"message": "Resume Analyzer API is running"}


@app.get("/health", tags=["Health"])
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/admin/users", response_model=list[UserRead], tags=["Admin"])
async def list_users(db = Depends(get_db)):
    return db.query(User).order_by(User.created_at.desc()).all()


@app.post("/admin/users", response_model=UserRead, tags=["Admin"])
async def create_user(
    payload: UserCreate,
    db = Depends(get_db),
    x_user_email: str | None = Header(None),
):
    current_user = find_user_by_login_identifier(db, x_user_email or "")
    if not is_user_creation_admin(current_user):
        raise HTTPException(status_code=403, detail="Only admin users can create users")

    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="A user with this username already exists")

    user = User(
        email=payload.email.lower().strip(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=AuthResponse, tags=["Auth"])
async def login(payload: UserLogin, db = Depends(get_db)):
    user = find_user_by_login_identifier(db, payload.email)
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"user": user}


@app.post("/auth/forgot-password", tags=["Auth"])
async def forgot_password(payload: UserForgotPassword, db = Depends(get_db)):
    user = find_user_by_login_identifier(db, payload.email)
    if user and user.is_active:
        temporary_password = generate_temporary_password()
        send_password_reset_email(user.email, temporary_password)
        user.hashed_password = hash_password(temporary_password)
        db.commit()
    return {
        "message": (
            "If this account exists, a new temporary password has "
            "been sent to the registered email."
        )
    }


@app.get("/job-roles", tags=["Job Roles"])
async def list_job_roles(db = Depends(get_db)):
    roles = db.query(JobRole).order_by(JobRole.created_at.asc(), JobRole.id.asc()).all()
    return {"roles": [role_to_payload(role) for role in roles]}


@app.put("/job-roles", tags=["Job Roles"])
async def save_job_roles(payload: JobRolesSaveRequest, db = Depends(get_db)):
    saved_roles = []
    incoming_ids = set()

    for item in payload.roles:
        role_id = None
        if item.id and str(item.id).isdigit():
            role_id = int(item.id)
            incoming_ids.add(role_id)

        role = db.query(JobRole).filter(JobRole.id == role_id).first() if role_id else None
        if role is None:
            role = JobRole(title=item.roleTitle)
            db.add(role)
            db.flush()
            incoming_ids.add(role.id)

        weights = item.weights or {}
        role.title = item.roleTitle.strip()
        role.description = item.jobDescription
        role.min_experience = int(float(item.minExperience or 0))
        role.filter_experience_levels = item.experienceLevel or "junior"
        role.weight_projects = int(weights.get("projects", 50))
        role.weight_skills = int(weights.get("skills", 30))
        role.weight_education = int(weights.get("education", 20))
        role.min_fit_score = item.minFitScore
        role.intake_paused = not item.active
        db.flush()

        upsert_role_requirements(db, role, item.requiredSkills, "skill")
        upsert_role_requirements(db, role, item.projectKeywords, "keyword")
        saved_roles.append(role)

    for role in db.query(JobRole).all():
        if role.id not in incoming_ids:
            db.delete(role)

    db.commit()
    roles = db.query(JobRole).order_by(JobRole.created_at.asc(), JobRole.id.asc()).all()
    return {"roles": [role_to_payload(role) for role in roles]}


async def pull_mail_graph(payload: MailPullRequest, settings: dict, db):
    if not settings["client_id"]:
        raise HTTPException(
            status_code=400,
            detail="MS_CLIENT_ID must be configured in backend/.env for Graph mail",
        )

    processed = []
    skipped = []
    sent_emails = []
    failed_emails = []

    try:
        token, app_token = get_graph_access_token(
            settings,
            ["Mail.ReadWrite", "Mail.Send", "offline_access"],
        )
        user_path = graph_user_path(settings, app_token)
        response = graph_request(
            "GET",
            f"{user_path}/mailFolders/inbox/messages",
            token,
            params={
                "$top": payload.max_messages,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,internetMessageId,hasAttachments,receivedDateTime",
            },
            headers={"Prefer": 'outlook.body-content-type="text"'},
        )
        messages = response.json().get("value", [])
        logger.info("Graph mail pull found %s inbox message(s)", len(messages))

        for graph_message in messages:
            graph_id = graph_message["id"]
            mail_message_id = graph_message.get("internetMessageId") or graph_id
            sender = (
                graph_message.get("from", {})
                .get("emailAddress", {})
                .get("address", "")
            )
            subject = graph_message.get("subject") or ""
            received_at = parse_graph_datetime(graph_message.get("receivedDateTime"))

            existing_mail = db.query(InboundEmail).filter(
                InboundEmail.message_id == mail_message_id
            ).first()
            if existing_mail:
                skipped.append({"message_id": mail_message_id, "reason": "already processed"})
                continue

            inbound = InboundEmail(
                message_id=mail_message_id,
                sender_email=sender,
                subject=subject,
                received_at=received_at or datetime.now(timezone.utc),
                status="new",
            )
            db.add(inbound)
            db.commit()
            db.refresh(inbound)

            attachment_paths = []
            attachment_results = []
            try:
                if not graph_message.get("hasAttachments"):
                    skipped.append({"message_id": mail_message_id, "reason": "no attachment"})
                else:
                    attachments_response = graph_request(
                        "GET",
                        f"{user_path}/messages/{graph_id}/attachments",
                        token,
                    )
                    attachments = attachments_response.json().get("value", [])

                    for attachment in attachments:
                        filename = attachment.get("name") or "resume.txt"
                        suffix = Path(filename).suffix.lower()
                        if suffix not in {".pdf", ".docx", ".txt"}:
                            skipped.append({"message_id": mail_message_id, "filename": filename, "reason": "unsupported attachment"})
                            continue

                        content_bytes = attachment.get("contentBytes")
                        if content_bytes:
                            file_bytes = base64.b64decode(content_bytes)
                        else:
                            raw_response = graph_request(
                                "GET",
                                f"{user_path}/messages/{graph_id}/attachments/{attachment['id']}/$value",
                                token,
                            )
                            file_bytes = raw_response.content

                        if not file_bytes:
                            skipped.append({"message_id": mail_message_id, "filename": filename, "reason": "empty attachment"})
                            continue

                        saved_resume_path = UPLOAD_DIR / safe_upload_name(filename)
                        saved_resume_path.write_bytes(file_bytes)
                        attachment_paths.append(str(saved_resume_path))

                        content_type = attachment.get("contentType") or "application/octet-stream"
                        effective_job_description, effective_role_title, effective_min_fit_score = matched_mail_role(
                            file_bytes,
                            filename,
                            content_type,
                            payload,
                        )
                        result = await analyzer.analyze(
                            file_obj=io.BytesIO(file_bytes),
                            filename=filename,
                            content_type=content_type,
                            job_description=effective_job_description,
                        )
                        saved, result = score_analysis_payload(
                            result,
                            filename,
                            saved_resume_path,
                            effective_job_description,
                            effective_role_title,
                            db,
                            received_at,
                        )

                        score = result.get("llm_analysis", {}).get("overall_score", result.get("weighted_score", 0))
                        candidate_email = result.get("email") or sender
                        email_sent = False
                        if payload.send_shortlist_emails and score >= effective_min_fit_score and candidate_email:
                            try:
                                graph_send_shortlist_email(
                                    settings,
                                    token,
                                    app_token,
                                    candidate_email,
                                    result.get("candidate_name"),
                                    effective_role_title,
                                    score,
                                )
                                sent_emails.append(candidate_email)
                                email_sent = True
                            except Exception as exc:
                                failed_emails.append({"email": candidate_email, "error": str(exc)})

                        attachment_results.append({
                            "analysis_id": saved.id,
                            "filename": filename,
                            "candidate": result.get("candidate_name"),
                            "email": candidate_email,
                            "score": score,
                            "role_title": effective_role_title,
                            "experience_level": result.get("experience_level"),
                            "shortlist_email_sent": email_sent,
                        })

                inbound.raw_file_paths = json.dumps(attachment_paths)
                inbound.status = "processed" if attachment_results else "no_attachment"
                db.commit()
                logger.info(
                    "Graph mail processed message %s with %s saved attachment analysis(es)",
                    mail_message_id,
                    len(attachment_results),
                )
                processed.append({
                    "message_id": mail_message_id,
                    "sender": sender,
                    "subject": subject,
                    "received_at": received_at.isoformat() if received_at else None,
                    "attachments": attachment_results,
                })
                try:
                    graph_request("PATCH", f"{user_path}/messages/{graph_id}", token, json={"isRead": True})
                except Exception as exc:
                    logger.warning("Graph mail read marker failed for %s: %s", mail_message_id, exc)
            except Exception as exc:
                inbound.status = "failed"
                inbound.error_message = str(exc)
                db.commit()
                processed.append({
                    "message_id": mail_message_id,
                    "sender": sender,
                    "subject": subject,
                    "error": str(exc),
                })

        return {
            "processed_count": len(processed),
            "saved_analysis_count": sum(
                len(item.get("attachments") or [])
                for item in processed
            ),
            "processed": processed,
            "skipped": skipped,
            "sent_emails": sent_emails,
            "failed_emails": failed_emails,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Graph mail pull failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Graph mail pull failed: {exc}")


@app.post("/mail/pull", tags=["Mail"])
async def pull_mail(payload: MailPullRequest, db = Depends(get_db)):
    settings = mail_settings()
    logger.info(f"Pulling mail with auth method: {settings['auth_method']}")
    if not settings["username"]:
        raise HTTPException(
            status_code=400,
            detail="MAIL_USERNAME must be configured in backend/.env",
        )
    if settings["auth_method"] == "graph":
        return await pull_mail_graph(payload, settings, db)
    if settings["auth_method"] not in {"oauth2", "graph"} and not settings["password"]:
        raise HTTPException(
            status_code=400,
            detail="MAIL_PASSWORD must be configured in backend/.env for basic mail login",
        )

    processed = []
    skipped = []
    sent_emails = []
    failed_emails = []

    try:
        mailbox = imaplib.IMAP4_SSL(settings["imap_host"], settings["imap_port"])
        authenticate_imap(mailbox, settings)
        mailbox.select("INBOX")
        _, search_data = mailbox.search(None, "UNSEEN")
        message_ids = search_data[0].split()[: payload.max_messages]

        for message_id in message_ids:
            _, message_data = mailbox.fetch(message_id, "(RFC822)")
            if not message_data or not message_data[0]:
                continue

            raw_message = message_data[0][1]
            message = email.message_from_bytes(raw_message)
            mail_message_id = message.get("Message-ID") or message_id.decode("utf-8")
            sender = parseaddr(message.get("From", ""))[1]
            subject = decode_mail_header(message.get("Subject"))
            try:
                received_at = parsedate_to_datetime(message.get("Date"))
                if received_at and received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                received_at = None

            existing_mail = db.query(InboundEmail).filter(
                InboundEmail.message_id == mail_message_id
            ).first()
            if existing_mail:
                skipped.append({"message_id": mail_message_id, "reason": "already processed"})
                continue

            inbound = InboundEmail(
                message_id=mail_message_id,
                sender_email=sender,
                subject=subject,
                received_at=received_at or datetime.now(timezone.utc),
                status="new",
            )
            db.add(inbound)
            db.commit()
            db.refresh(inbound)

            attachment_paths = []
            attachment_results = []
            try:
                for part in message.walk():
                    if part.get_content_disposition() != "attachment":
                        continue

                    filename = decode_mail_header(part.get_filename()) or "resume.txt"
                    suffix = Path(filename).suffix.lower()
                    if suffix not in {".pdf", ".docx", ".txt"}:
                        skipped.append({"message_id": mail_message_id, "filename": filename, "reason": "unsupported attachment"})
                        continue

                    file_bytes = part.get_payload(decode=True) or b""
                    if not file_bytes:
                        skipped.append({"message_id": mail_message_id, "filename": filename, "reason": "empty attachment"})
                        continue

                    saved_resume_path = UPLOAD_DIR / safe_upload_name(filename)
                    saved_resume_path.write_bytes(file_bytes)
                    attachment_paths.append(str(saved_resume_path))

                    content_type = part.get_content_type() or "application/octet-stream"
                    effective_job_description, effective_role_title, effective_min_fit_score = matched_mail_role(
                        file_bytes,
                        filename,
                        content_type,
                        payload,
                    )
                    result = await analyzer.analyze(
                        file_obj=io.BytesIO(file_bytes),
                        filename=filename,
                        content_type=content_type,
                        job_description=effective_job_description,
                    )
                    saved, result = score_analysis_payload(
                        result,
                        filename,
                        saved_resume_path,
                        effective_job_description,
                        effective_role_title,
                        db,
                        received_at,
                    )

                    score = result.get("llm_analysis", {}).get("overall_score", result.get("weighted_score", 0))
                    candidate_email = result.get("email") or sender
                    email_sent = False
                    if payload.send_shortlist_emails and score >= effective_min_fit_score and candidate_email:
                        try:
                            send_shortlist_email(
                                candidate_email,
                                result.get("candidate_name"),
                                effective_role_title,
                                score,
                            )
                            sent_emails.append(candidate_email)
                            email_sent = True
                        except Exception as exc:
                            failed_emails.append({"email": candidate_email, "error": str(exc)})

                    attachment_results.append({
                        "analysis_id": saved.id,
                        "filename": filename,
                        "candidate": result.get("candidate_name"),
                        "email": candidate_email,
                        "score": score,
                        "role_title": effective_role_title,
                        "experience_level": result.get("experience_level"),
                        "shortlist_email_sent": email_sent,
                    })

                inbound.raw_file_paths = json.dumps(attachment_paths)
                inbound.status = "processed" if attachment_results else "no_attachment"
                db.commit()
                processed.append({
                    "message_id": mail_message_id,
                    "sender": sender,
                    "subject": subject,
                    "received_at": received_at.isoformat() if received_at else None,
                    "attachments": attachment_results,
                })
                mailbox.store(message_id, "+FLAGS", "\\Seen")
            except Exception as exc:
                inbound.status = "failed"
                inbound.error_message = str(exc)
                db.commit()
                processed.append({
                    "message_id": mail_message_id,
                    "sender": sender,
                    "subject": subject,
                    "error": str(exc),
                })

        mailbox.logout()
        return {
            "processed_count": len(processed),
            "saved_analysis_count": sum(
                len(item.get("attachments") or [])
                for item in processed
            ),
            "processed": processed,
            "skipped": skipped,
            "sent_emails": sent_emails,
            "failed_emails": failed_emails,
        }
    except HTTPException:
        raise
    except imaplib.IMAP4.error as exc:
        logger.error(f"Mail login failed: {exc}")
        raise HTTPException(
            status_code=401,
            detail=(
                "Mail inbox login failed. Check MAIL_USERNAME and MAIL_PASSWORD, "
                "and make sure IMAP access is enabled for this mailbox."
            ),
        )
    except Exception as exc:
        logger.error(f"Mail pull failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Mail pull failed: {exc}")


@app.post("/mail/send-shortlisted", tags=["Mail"])
async def send_shortlisted_mail(payload: ShortlistEmailRequest, db = Depends(get_db)):
    settings = mail_settings()
    if not settings["username"] or not settings["from_email"]:
        raise HTTPException(
            status_code=400,
            detail="MAIL_USERNAME and MAIL_FROM must be configured in backend/.env",
        )
    if settings["auth_method"] != "oauth2" and not settings["password"]:
        raise HTTPException(
            status_code=400,
            detail="MAIL_PASSWORD must be configured in backend/.env for basic mail login",
        )

    analyses = (
        db.query(ResumeAnalysis)
        .filter(ResumeAnalysis.overall_score >= payload.min_fit_score)
        .order_by(ResumeAnalysis.overall_score.desc(), ResumeAnalysis.created_at.desc())
        .limit(payload.limit)
        .all()
    )

    sent_emails = []
    failed_emails = []
    skipped = []

    for analysis in analyses:
        if not analysis.email:
            skipped.append({
                "analysis_id": analysis.id,
                "candidate": analysis.candidate_name or analysis.resume_name,
                "reason": "email not found",
            })
            continue

        try:
            send_shortlist_email(
                analysis.email,
                analysis.candidate_name,
                payload.role_title,
                analysis.overall_score,
            )
            sent_emails.append({
                "analysis_id": analysis.id,
                "candidate": analysis.candidate_name or analysis.resume_name,
                "email": analysis.email,
                "score": analysis.overall_score,
            })
        except Exception as exc:
            failed_emails.append({
                "analysis_id": analysis.id,
                "candidate": analysis.candidate_name or analysis.resume_name,
                "email": analysis.email,
                "error": str(exc),
            })

    return {
        "eligible_count": len(analyses),
        "sent_count": len(sent_emails),
        "failed_count": len(failed_emails),
        "skipped_count": len(skipped),
        "sent_emails": sent_emails,
        "failed_emails": failed_emails,
        "skipped": skipped,
    }


@app.post("/analyze", tags=["Analysis"])
async def analyze_resume(
    resume: UploadFile = File(..., description="Resume file (PDF, DOCX, or TXT)"),
    job_description: str = Form("", description="Job description text"),
    role_title: Optional[str] = Form(None, description="Matched or selected job role title"),
    roles_json: Optional[str] = Form(None, description="Configured job roles for automatic role matching"),
    min_fit_score: float = Form(80, description="Minimum score required to send a shortlist email"),
    send_shortlist_email_enabled: bool = Form(True, description="Send email automatically when shortlisted"),
    db = Depends(get_db),
):
    """
    Analyze a resume against a job description.
    
    Returns analysis scores, skill matching, and AI-generated insights.
    Results are stored in PostgreSQL for historical tracking.
    """
    try:
        # Validate file type
        allowed_types = [
            "application/pdf",
            "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        
        if (resume.content_type not in allowed_types and 
            not resume.filename.endswith(('.pdf', '.txt', '.docx'))):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Use PDF, TXT, or DOCX."
            )

        roles = []
        if roles_json:
            try:
                parsed_roles = json.loads(roles_json)
                roles = parsed_roles if isinstance(parsed_roles, list) else []
            except json.JSONDecodeError:
                roles = []

        if not job_description.strip() and not roles:
            raise HTTPException(
                status_code=400,
                detail="Job description or configured roles cannot be empty."
            )

        # Extract and analyze resume
        file_bytes = await resume.read()
        saved_resume_path = UPLOAD_DIR / safe_upload_name(resume.filename)
        saved_resume_path.write_bytes(file_bytes)
        file_obj = io.BytesIO(file_bytes)

        if roles:
            resume_text = analyzer.extract_text(io.BytesIO(file_bytes), resume.filename, resume.content_type or "")
            matched_role = match_role_for_resume(resume_text, roles)
            if matched_role:
                job_description = role_payload_to_job_description(matched_role)
                role_title = matched_role.get("roleTitle") or role_title
                min_fit_score = float(matched_role.get("minFitScore") or min_fit_score)

        logger.info(f"Analyzing resume: {resume.filename}")
        result = await analyzer.analyze(
            file_obj=file_obj,
            filename=resume.filename,
            content_type=resume.content_type,
            job_description=job_description
        )

        saved, result = score_analysis_payload(
            result,
            resume.filename,
            saved_resume_path,
            job_description,
            role_title,
            db,
        )
        logger.info(f"Analysis saved with ID: {saved.id}")

        score = result.get("llm_analysis", {}).get("overall_score", result.get("weighted_score", 0))
        candidate_email = result.get("email")
        result["shortlist_email_sent"] = False
        result["shortlist_email_error"] = None
        result["shortlist_threshold"] = min_fit_score

        if send_shortlist_email_enabled and score >= min_fit_score:
            if candidate_email:
                try:
                    send_shortlist_email(
                        candidate_email,
                        result.get("candidate_name"),
                        role_title,
                        score,
                    )
                    result["shortlist_email_sent"] = True
                    logger.info(f"Shortlist email sent to {candidate_email} for analysis ID: {saved.id}")
                except Exception as exc:
                    result["shortlist_email_error"] = str(exc)
                    logger.error(f"Shortlist email failed for analysis ID {saved.id}: {exc}")
            else:
                result["shortlist_email_error"] = "Candidate email not found in resume"

        return result

    except HTTPException:
        raise
    except RuntimeError as e:
        error_msg = str(e)
        if "does not appear to be a resume" in error_msg:
            raise HTTPException(status_code=400, detail=error_msg)
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.get("/analyze/history", response_model=AnalysisHistory, tags=["Analysis"])
async def get_analysis_history(
    resume_name: Optional[str] = Query(None, description="Filter by resume name"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db = Depends(get_db),
):
    """
    Get analysis history from database.
    
    Optionally filter by resume name and use pagination.
    """
    try:
        service = AnalysisService(db)
        history = service.get_analysis_history(resume_name, skip, limit)
        logger.info(f"Retrieved {len(history['analyses'])} analyses from history")
        return history
    except Exception as e:
        logger.error(f"Error retrieving history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve history"
        )


@app.get("/analyze/{analysis_id}", tags=["Analysis"])
async def get_analysis(
    analysis_id: int,
    db = Depends(get_db),
):
    """
    Get a specific analysis by ID.
    """
    try:
        service = AnalysisService(db)
        analysis = service.get_analysis(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID {analysis_id} not found"
            )
        
        logger.info(f"Retrieved analysis: {analysis_id}")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analysis"
        )


@app.get("/statistics", tags=["Analytics"])
async def get_statistics(db = Depends(get_db)):
    """
    Get analysis statistics from database.
    """
    try:
        service = AnalysisService(db)
        stats = service.get_statistics()
        logger.info("Retrieved statistics")
        return stats
    except Exception as e:
        logger.error(f"Error retrieving statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve statistics"
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
