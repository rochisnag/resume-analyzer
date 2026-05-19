import hashlib
import os

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import User


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return f"pbkdf2_sha256${salt.hex()}${digest.hex()}"


def seed_default_user(db: Session):
    default_email = "TEK-1"
    default_password = "Tek@12345"
    legacy_email = "rochisna.g@tektalis.com"

    existing_user = db.query(User).filter(func.lower(User.email) == default_email.lower()).first()
    legacy_user = db.query(User).filter(func.lower(User.email) == legacy_email.lower()).first()
    if existing_user:
        existing_user.hashed_password = hash_password(default_password)
        existing_user.role = "admin"
        existing_user.is_active = True
        db.commit()
        print("Default admin user updated.")
    elif legacy_user:
        legacy_user.email = default_email
        legacy_user.hashed_password = hash_password(default_password)
        legacy_user.role = "admin"
        legacy_user.is_active = True
        db.commit()
        print("Default admin user migrated and updated.")
    else:
        default_user = User(
            email=default_email,
            hashed_password=hash_password(default_password),
            role="admin",
            is_active=True
        )
        db.add(default_user)
        db.commit()
        print("Default admin user created.")


if __name__ == "__main__":
    from database import SessionLocal

    db = SessionLocal()
    seed_default_user(db)
    db.close()
