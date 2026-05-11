"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration — values are read from .env automatically."""
    # Security
    SECRET_KEY: str  # No default, must be provided in .env

    # Feature Flags
    ENVIRONMENT: str = "development"  # Set to "production" in prod .env
    LIVE_PIPELINE_ENABLED: bool = False
    ENABLE_STARTUP_RECOVERY: bool = False  # Set True only when needed

    # Database
    DATABASE_URL: str = "sqlite:///./call_rating.db"

    # HuggingFace token (Pyannote diarization)
    HF_TOKEN: str = ""

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Audio uploads
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".wav,.mp3,.m4a,.ogg,.flac,.webm"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str, info) -> str:
        # Pydantic v2 uses 'info.data' to access other fields
        env = info.data.get("ENVIRONMENT", "development")
        if env == "production" and v.startswith("sqlite"):
            raise ValueError(
                "SQLite is not allowed in production. "
                "Set DATABASE_URL to a PostgreSQL connection string in your .env file. "
                "Example: postgresql://user:password@localhost:5432/call_rating"
            )
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters. "
                "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if v == "your-super-secret-key-for-development":
            raise ValueError("SECRET_KEY is still set to the insecure default value.")
        return v

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
