import hashlib
import re
import secrets

from app.security import SECRET_KEY


def normalize_interview_email(email: str | None) -> str:
    value = str(email or "").strip()
    if value.count("@") != 1:
        raise ValueError("Invalid candidate email format.")

    local, domain = value.split("@", 1)
    local = local.strip().lower()
    domain = domain.strip().lower().lstrip(".").rstrip(".")
    if not local or not domain or "." not in domain:
        raise ValueError("Invalid candidate email format.")
    return f"{local}@{domain}"


def normalize_interview_phone(phone_number: str | None) -> str | None:
    value = re.sub(r"\D+", "", str(phone_number or ""))
    return value or None


def national_id_last4(national_id: str | None) -> str | None:
    value = re.sub(r"\D+", "", str(national_id or ""))
    if not value:
        return None
    return value[-4:]


def generate_interview_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_interview_session_token(token: str) -> str:
    normalized = str(token or "").strip()
    if not normalized:
        raise ValueError("Session token is required.")
    return hashlib.sha256(f"{SECRET_KEY}:interview-session:{normalized}".encode("utf-8")).hexdigest()
