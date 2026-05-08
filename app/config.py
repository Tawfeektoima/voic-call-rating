"""
Application configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration — values are read from .env automatically."""
    # Feature Flags
    LIVE_PIPELINE_ENABLED: bool = False

    # Database
    DATABASE_URL: str = "sqlite:///./call_rating.db"

    # HuggingFace token (Pyannote diarization)
    HF_TOKEN: str = ""

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Audio uploads
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".wav,.mp3,.m4a,.ogg,.flac,.webm"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"

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
