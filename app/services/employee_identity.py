import re
import hashlib

from app.config import get_settings
from app.security import SECRET_KEY


def canonical_email_domain() -> str:
    return get_settings().GENERATED_EMAIL_DOMAIN.strip().lower().lstrip(".").rstrip(".")


def generated_email_prefix() -> str:
    return get_settings().GENERATED_EMAIL_PREFIX.strip().lower().strip("-") or "emp"


def normalize_employee_code(employee_code: str) -> str:
    return str(employee_code or "").strip()


def generate_employee_email(employee_code: str) -> str:
    code = normalize_employee_code(employee_code)
    local_code = re.sub(r"[^a-zA-Z0-9._-]+", "-", code).strip(".-_").lower()
    if not local_code:
        raise ValueError("Employee code is required to generate email.")
    return f"{generated_email_prefix()}-{local_code}@{canonical_email_domain()}"


def normalize_employee_email(email: str | None, employee_code: str | None = None) -> str:
    value = str(email or "").strip()
    if not value:
        return generate_employee_email(employee_code or "")

    if value.count("@") != 1:
        raise ValueError("Invalid email format.")

    local, domain = value.split("@", 1)
    local = local.strip().lower()
    domain = domain.strip().lower().lstrip(".").rstrip(".")

    if not local or not domain or "." not in domain:
        raise ValueError("Invalid email format.")

    return f"{local}@{domain}"


def normalize_contact_email(email: str | None) -> str | None:
    value = str(email or "").strip()
    if not value:
        return None
    if value.count("@") != 1:
        raise ValueError("Invalid OTP email format.")
    local, domain = value.split("@", 1)
    local = local.strip().lower()
    domain = domain.strip().lower().lstrip(".").rstrip(".")
    if not local or not domain or "." not in domain:
        raise ValueError("Invalid OTP email format.")
    return f"{local}@{domain}"


def normalize_national_id(national_id: str | None) -> str | None:
    value = re.sub(r"\D+", "", str(national_id or ""))
    return value or None


def hash_national_id(national_id: str | None) -> str | None:
    normalized = normalize_national_id(national_id)
    if not normalized:
        return None
    return hashlib.sha256(f"{SECRET_KEY}:national-id:{normalized}".encode("utf-8")).hexdigest()
