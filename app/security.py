from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

from app.config import get_settings
settings = get_settings()

# Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
PASSWORD_STRENGTH_MESSAGE = (
    "Password must include at least one uppercase letter, one lowercase letter, "
    "one number, and one special character."
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> None:
    if not any(char.isupper() for char in password):
        raise ValueError(PASSWORD_STRENGTH_MESSAGE)
    if not any(char.islower() for char in password):
        raise ValueError(PASSWORD_STRENGTH_MESSAGE)
    if not any(char.isdigit() for char in password):
        raise ValueError(PASSWORD_STRENGTH_MESSAGE)
    if not any(not char.isalnum() for char in password):
        raise ValueError(PASSWORD_STRENGTH_MESSAGE)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"iat": issued_at, "exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def require_ingestion_management_access(current_user, detail: str = "Only admins can manage recording ingestion.") -> None:
    from app.permissions import Permission, require_permission

    require_permission(current_user, Permission.MANAGE_RECORDING_INGESTION, detail=detail)
