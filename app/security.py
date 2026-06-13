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
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
