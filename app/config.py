"""
Application configuration loaded from environment variables.
"""

from functools import lru_cache
from urllib.parse import quote, urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


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
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USERNAME: str = ""
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = ""
    CELERY_BROKER_URL: str = ""

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @staticmethod
    def _build_redis_url(
        host: str,
        port: int,
        db: int,
        username: str = "",
        password: str = "",
    ) -> str:
        auth = ""
        if username and password:
            auth = f"{quote(username)}:{quote(password)}@"
        elif password:
            auth = f":{quote(password)}@"
        elif username:
            auth = f"{quote(username)}@"

        return f"redis://{auth}{host}:{port}/{db}"

    @staticmethod
    def _redis_url_has_password(redis_url: str) -> bool:
        parsed = urlsplit(redis_url)
        return bool(parsed.password)

    @model_validator(mode="after")
    def normalize_redis_settings(self):
        if not self.REDIS_URL.strip() and not self.CELERY_BROKER_URL.strip():
            built_url = self._build_redis_url(
                host=self.REDIS_HOST,
                port=self.REDIS_PORT,
                db=self.REDIS_DB,
                username=self.REDIS_USERNAME,
                password=self.REDIS_PASSWORD,
            )
            self.REDIS_URL = built_url
            self.CELERY_BROKER_URL = built_url
        elif self.REDIS_URL.strip() and not self.CELERY_BROKER_URL.strip():
            self.CELERY_BROKER_URL = self.REDIS_URL
        elif self.CELERY_BROKER_URL.strip() and not self.REDIS_URL.strip():
            self.REDIS_URL = self.CELERY_BROKER_URL

        if self.is_production:
            if self.DATABASE_URL.startswith("sqlite"):
                raise ValueError(
                    "SQLite is not allowed in production. "
                    "Set DATABASE_URL to a PostgreSQL connection string in your .env file. "
                    "Example: postgresql://user:password@localhost:5432/call_rating"
                )

            redis_urls = {
                "REDIS_URL": self.REDIS_URL,
                "CELERY_BROKER_URL": self.CELERY_BROKER_URL,
            }
            for field_name, redis_url in redis_urls.items():
                if not redis_url.strip():
                    raise ValueError(f"{field_name} must be set in production.")
                if not self._redis_url_has_password(redis_url):
                    raise ValueError(
                        f"{field_name} must include Redis authentication in production."
                    )

        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
