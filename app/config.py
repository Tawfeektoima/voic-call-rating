"""
Application configuration loaded from environment variables.
"""

import os
import socket
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Callable
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from pydantic import ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    """Central configuration — values are read from .env automatically."""
    # Security
    SECRET_KEY: str  # No default, must be provided in .env

    # Security Policy Rollout
    SECURITY_POLICY_MODE: str = "off"
    SECURITY_TIMEZONE: str = "Africa/Cairo"
    DEFAULT_SHIFT_GRACE_BEFORE_MINUTES: int = 10
    DEFAULT_SHIFT_GRACE_AFTER_MINUTES: int = 10
    SECURITY_WS_REVALIDATION_INTERVAL_SECONDS: int = 15

    # Feature Flags
    ENVIRONMENT: str = "development"  # Set to "production" in prod .env
    LIVE_PIPELINE_ENABLED: bool = False
    ENABLE_STARTUP_RECOVERY: bool = False  # Set True only when needed

    # Call ingestion
    CALL_INGEST_ENABLED: bool = False
    CALL_INGEST_GOOGLE_SHEET_ID: str = ""
    CALL_INGEST_WORKSHEET: str = "الورقة1"
    CALL_INGEST_RANGE: str = "A:ZZ"
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE_HOST: str = ""
    CALL_INGEST_DEFAULT_CAMPAIGN_ID: int = 0
    CALL_INGEST_ALLOWED_RECORDING_HOSTS: str = "archive.dial-fusion.com"
    CALL_INGEST_INTERVAL_MINUTES: int = 15
    CALL_INGEST_DOWNLOAD_CONCURRENCY: int = 4
    CALL_INGEST_RETRY_LIMIT: int = 3
    CALL_INGEST_REQUEST_TIMEOUT_SECONDS: int = 30
    CALL_INGEST_QUARANTINE_DIR: str = "/var/lib/call-rating/quarantine"
    CALL_INGEST_ACCEPTED_DIR: str = "/var/lib/call-rating/accepted"
    CALL_INGEST_REJECTED_DIR: str = "/var/lib/call-rating/rejected"
    CALL_INGEST_SCANNER: str = "clamd"
    CALL_INGEST_SCANNER_ENDPOINT: str = "/run/clamav/clamd.ctl"
    CALL_INGEST_MEDIA_VERIFIER_ENDPOINT: str = "http://media-verifier:8090"
    CALL_INGEST_VM_STORAGE_ROOT: str = "/var/lib/call-rating"
    CALL_INGEST_RUNTIME_ROLE: str = "all"
    CALL_INGEST_INSPECTION_TIMEOUT_SECONDS: int = 60
    CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS: int = 60

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
    FRONTEND_URL: str = "http://localhost:5173"
    INTERVIEW_DOCUMENT_MAX_FILE_SIZE_MB: int = 10
    INTERVIEW_DOCUMENT_ALLOWED_EXTENSIONS: str = ".pdf,.txt,.md,.docx"
    INTERVIEW_ARCHIVE_RETENTION_DAYS: int = 90
    INTERVIEW_SESSION_EXPIRY_HOURS: int = 24
    INTERVIEW_APPLICATION_COOLDOWN_DAYS: int = 30
    INTERVIEW_DUPLICATE_WINDOW_SECONDS: int = 600
    INTERVIEW_QUESTION_TIME_LIMIT_SECONDS: int = 180
    PUBLIC_BASE_URL: str = ""
    INTERVIEW_PORTAL_PATH: str = "/interview-portal"
    REQUIRE_PUBLIC_BASE_URL_FOR_INTERVIEWS: bool = False
    ENABLE_PUBLIC_BASE_URL_HEALTHCHECK: bool = False

    # Employee identity
    GENERATED_EMAIL_DOMAIN: str = "EIACS.com"
    GENERATED_EMAIL_PREFIX: str = "emp"

    # Login OTP
    LOGIN_OTP_REQUIRED: bool = False
    LOGIN_OTP_EXPIRE_MINUTES: int = 5
    LOGIN_OTP_MAX_ATTEMPTS: int = 5
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    # Password hashing/onboarding
    BCRYPT_ROUNDS: int = 12
    DEFAULT_EMPLOYEE_PASSWORD: str = "Eiacs$1234#"

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

    @field_validator("SECURITY_POLICY_MODE")
    @classmethod
    def validate_security_policy_mode(cls, v: str) -> str:
        normalized = v.lower()
        if normalized not in ("off", "audit", "enforce"):
            raise ValueError(
                f"Invalid SECURITY_POLICY_MODE: '{v}'. "
                "Allowed modes are: 'off', 'audit', 'enforce'."
            )
        return normalized

    @field_validator("SECURITY_TIMEZONE")
    @classmethod
    def validate_security_timezone(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception as e:
            raise ValueError(
                f"Invalid SECURITY_TIMEZONE: '{v}'. "
                "Must be a valid IANA timezone name."
            )
        return v

    @field_validator("DEFAULT_SHIFT_GRACE_BEFORE_MINUTES", "DEFAULT_SHIFT_GRACE_AFTER_MINUTES")
    @classmethod
    def validate_grace_minutes(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Grace minutes must be greater than or equal to 0.")
        if v > 240:
            raise ValueError("Grace minutes cannot exceed 240 minutes.")
        return v

    @field_validator("SECURITY_WS_REVALIDATION_INTERVAL_SECONDS")
    @classmethod
    def validate_ws_revalidation_interval(cls, v: int) -> int:
        if v < 0:
            raise ValueError("WebSocket revalidation interval must be greater than or equal to 0.")
        return v

    @field_validator(
        "CALL_INGEST_GOOGLE_SHEET_ID",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_SERVICE_ACCOUNT_FILE_HOST",
    )
    @classmethod
    def validate_required_ingestion_identifier(cls, v: str, info) -> str:
        normalized = v.strip()
        if not normalized:
            return normalized
        if normalized.startswith("<") and normalized.endswith(">"):
            raise ValueError(f"{info.field_name} must not be a placeholder value.")
        if any(char in normalized for char in ("/", "?", "#")) and info.field_name == "CALL_INGEST_GOOGLE_SHEET_ID":
            raise ValueError("CALL_INGEST_GOOGLE_SHEET_ID must be a raw Google Sheet ID, not a URL.")
        return normalized

    @field_validator(
        "CALL_INGEST_INTERVAL_MINUTES",
        "CALL_INGEST_DOWNLOAD_CONCURRENCY",
        "CALL_INGEST_RETRY_LIMIT",
        "CALL_INGEST_REQUEST_TIMEOUT_SECONDS",
        "CALL_INGEST_INSPECTION_TIMEOUT_SECONDS",
        "CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS",
    )
    @classmethod
    def validate_positive_ingestion_limits(cls, v: int, info) -> int:
        if v <= 0:
            raise ValueError(f"{info.field_name} must be greater than 0.")
        return v

    @field_validator(
        "CALL_INGEST_WORKSHEET",
        "CALL_INGEST_RANGE",
        "CALL_INGEST_ALLOWED_RECORDING_HOSTS",
        "CALL_INGEST_SCANNER",
    )
    @classmethod
    def validate_non_empty_ingestion_strings(cls, v: str, info) -> str:
        normalized = v.strip()
        if not normalized:
            raise ValueError(f"{info.field_name} must not be empty.")
        if info.field_name == "CALL_INGEST_RANGE" and ":" not in normalized:
            raise ValueError("CALL_INGEST_RANGE must be an A1-style range such as A:ZZ.")
        return normalized

    @field_validator("CALL_INGEST_ALLOWED_RECORDING_HOSTS")
    @classmethod
    def validate_allowed_recording_hosts(cls, v: str) -> str:
        return cls._normalize_host_allowlist(v, "CALL_INGEST_ALLOWED_RECORDING_HOSTS")

    @field_validator("CALL_INGEST_SCANNER_ENDPOINT")
    @classmethod
    def validate_scanner_endpoint(cls, v: str) -> str:
        normalized = v.strip()
        if not normalized:
            raise ValueError("CALL_INGEST_SCANNER_ENDPOINT must not be empty.")
        if normalized.startswith("unix:"):
            socket_path = normalized.removeprefix("unix:")
            if not socket_path.startswith("/"):
                raise ValueError("CALL_INGEST_SCANNER_ENDPOINT unix sockets must use an absolute path.")
            return normalized
        if "://" in normalized:
            parsed = urlsplit(normalized)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("CALL_INGEST_SCANNER_ENDPOINT must include a network location.")
            return normalized
        if not normalized.startswith("/"):
            raise ValueError("CALL_INGEST_SCANNER_ENDPOINT must be an absolute path or URI.")
        return normalized

    @field_validator("CALL_INGEST_MEDIA_VERIFIER_ENDPOINT")
    @classmethod
    def validate_media_verifier_endpoint(cls, v: str) -> str:
        normalized = v.strip()
        parsed = urlsplit(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("CALL_INGEST_MEDIA_VERIFIER_ENDPOINT must be an unauthenticated HTTP(S) endpoint.")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("CALL_INGEST_MEDIA_VERIFIER_ENDPOINT must not include a path, query, or fragment.")
        return normalized.rstrip("/")

    @field_validator("CALL_INGEST_RUNTIME_ROLE")
    @classmethod
    def validate_ingestion_runtime_role(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in {"all", "api", "gpu_worker", "downloader", "inspector", "scheduler"}:
            raise ValueError(
                "CALL_INGEST_RUNTIME_ROLE must be all, api, gpu_worker, downloader, inspector, or scheduler."
            )
        return normalized

    @field_validator(
        "CALL_INGEST_QUARANTINE_DIR",
        "CALL_INGEST_ACCEPTED_DIR",
        "CALL_INGEST_REJECTED_DIR",
        "CALL_INGEST_VM_STORAGE_ROOT",
    )
    @classmethod
    def validate_guest_local_directory(cls, v: str, info) -> str:
        normalized = cls._normalize_guest_path(v, info.field_name)
        return normalized

    @staticmethod
    def _normalize_host_allowlist(value: str, field_name: str) -> str:
        hosts = [host for host in (part.strip().lower() for part in value.replace(",", " ").split()) if host]
        if not hosts:
            raise ValueError(f"{field_name} must not be empty.")

        normalized_hosts = []
        for host in hosts:
            if any(char in host for char in ("://", "/", "?", "#", "@", ":")):
                raise ValueError(f"{field_name} entries must be bare hostnames or IP addresses.")
            if host.startswith(".") or host.endswith("."):
                raise ValueError(f"{field_name} entries must not start or end with a dot.")
            normalized_hosts.append(host)

        return ",".join(dict.fromkeys(normalized_hosts))

    @staticmethod
    def _normalize_guest_path(path_value: str, field_name: str) -> str:
        normalized = PurePosixPath(path_value.strip())
        if not normalized.is_absolute():
            raise ValueError(f"{field_name} must be an absolute guest path.")
        if len(normalized.parts) < 2:
            raise ValueError(f"{field_name} must not point at the filesystem root.")
        return normalized.as_posix()

    @staticmethod
    def _paths_overlap(first: str, second: str) -> bool:
        first_parts = PurePosixPath(first).parts
        second_parts = PurePosixPath(second).parts
        shorter, longer = (first_parts, second_parts) if len(first_parts) <= len(second_parts) else (second_parts, first_parts)
        return shorter == longer[: len(shorter)]

    @staticmethod
    def _path_is_within_root(path_value: str, root_value: str) -> bool:
        path_parts = PurePosixPath(path_value).parts
        root_parts = PurePosixPath(root_value).parts
        return len(path_parts) >= len(root_parts) and path_parts[: len(root_parts)] == root_parts

    @property
    def call_ingest_allowed_recording_hosts_list(self) -> list[str]:
        return [host for host in (part.strip() for part in self.CALL_INGEST_ALLOWED_RECORDING_HOSTS.split(",")) if host]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def interview_document_allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.INTERVIEW_DOCUMENT_ALLOWED_EXTENSIONS.split(",") if ext.strip()]

    @property
    def interview_document_max_file_size_bytes(self) -> int:
        return self.INTERVIEW_DOCUMENT_MAX_FILE_SIZE_MB * 1024 * 1024

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

        ingest_paths = {
            "CALL_INGEST_QUARANTINE_DIR": self.CALL_INGEST_QUARANTINE_DIR,
            "CALL_INGEST_ACCEPTED_DIR": self.CALL_INGEST_ACCEPTED_DIR,
            "CALL_INGEST_REJECTED_DIR": self.CALL_INGEST_REJECTED_DIR,
        }
        if len({*ingest_paths.values()}) != len(ingest_paths):
            raise ValueError("CALL_INGEST_QUARANTINE_DIR, CALL_INGEST_ACCEPTED_DIR, and CALL_INGEST_REJECTED_DIR must be different paths.")

        path_items = list(ingest_paths.items())
        for index, (field_name, path_value) in enumerate(path_items):
            for other_field_name, other_path_value in path_items[index + 1 :]:
                if self._paths_overlap(path_value, other_path_value):
                    raise ValueError(
                        f"{field_name} and {other_field_name} must not overlap or be nested."
                    )

        if self.CALL_INGEST_ENABLED:
            required_ingest_values = {
                "CALL_INGEST_ALLOWED_RECORDING_HOSTS": self.CALL_INGEST_ALLOWED_RECORDING_HOSTS.strip(),
            }
            if self.CALL_INGEST_RUNTIME_ROLE in {"all", "downloader"}:
                required_ingest_values.update(
                    {
                        "CALL_INGEST_GOOGLE_SHEET_ID": self.CALL_INGEST_GOOGLE_SHEET_ID.strip(),
                        "GOOGLE_SERVICE_ACCOUNT_FILE": self.GOOGLE_SERVICE_ACCOUNT_FILE.strip(),
                    }
                )
            if self.CALL_INGEST_RUNTIME_ROLE in {"all", "inspector"}:
                required_ingest_values["CALL_INGEST_SCANNER_ENDPOINT"] = self.CALL_INGEST_SCANNER_ENDPOINT.strip()
                required_ingest_values["CALL_INGEST_MEDIA_VERIFIER_ENDPOINT"] = self.CALL_INGEST_MEDIA_VERIFIER_ENDPOINT.strip()
            for field_name, value in required_ingest_values.items():
                if not value:
                    raise ValueError(f"{field_name} must be set before enabling call ingestion.")
            if self.CALL_INGEST_DEFAULT_CAMPAIGN_ID <= 0:
                raise ValueError("CALL_INGEST_DEFAULT_CAMPAIGN_ID must be greater than 0 before enabling call ingestion.")

        if self.is_production and self.CALL_INGEST_ENABLED:
            if self.CALL_INGEST_RUNTIME_ROLE == "all":
                raise ValueError(
                    "CALL_INGEST_RUNTIME_ROLE must not be 'all' in production. "
                    "Use api, gpu_worker, downloader, inspector, or scheduler."
                )

            for field_name, path_value in ingest_paths.items():
                if not self._path_is_within_root(path_value, self.CALL_INGEST_VM_STORAGE_ROOT):
                    raise ValueError(
                        f"{field_name} must stay under CALL_INGEST_VM_STORAGE_ROOT in production."
                    )

            upload_dir = self.UPLOAD_DIR.strip()
            if upload_dir.startswith("/"):
                for field_name, path_value in ingest_paths.items():
                    if self._paths_overlap(upload_dir, path_value):
                        raise ValueError(
                            f"UPLOAD_DIR must not overlap with {field_name} in production."
                        )

            if self.CALL_INGEST_RUNTIME_ROLE == "downloader":
                if not self.GOOGLE_SERVICE_ACCOUNT_FILE.startswith("/run/secrets/"):
                    raise ValueError(
                        "GOOGLE_SERVICE_ACCOUNT_FILE must point to a read-only /run/secrets path in production."
                    )
                if not self.GOOGLE_SERVICE_ACCOUNT_FILE_HOST:
                    raise ValueError(
                        "GOOGLE_SERVICE_ACCOUNT_FILE_HOST must be set in production for the downloader service."
                    )
                if not self._path_is_within_root(
                    self.GOOGLE_SERVICE_ACCOUNT_FILE_HOST,
                    self.CALL_INGEST_VM_STORAGE_ROOT,
                ):
                    raise ValueError(
                        "GOOGLE_SERVICE_ACCOUNT_FILE_HOST must stay under CALL_INGEST_VM_STORAGE_ROOT in production."
                    )

        return self


def _probe_tcp_endpoint(hostname: str, port: int, timeout_seconds: float) -> None:
    with socket.create_connection((hostname, port), timeout=timeout_seconds):
        return None


def _probe_http_healthcheck(url: str, timeout_seconds: float) -> int:
    with urlopen(url, timeout=timeout_seconds) as response:  # noqa: S310 - startup probes only approved internal services
        return int(getattr(response, "status", 200))


def validate_recording_ingestion_runtime_startup(
    settings: Settings,
    *,
    path_exists: Callable[[str], bool] = os.path.exists,
    tcp_probe: Callable[[str, int, float], None] = _probe_tcp_endpoint,
    http_probe: Callable[[str, float], int] = _probe_http_healthcheck,
) -> None:
    if not settings.is_production or not settings.CALL_INGEST_ENABLED:
        return

    role = settings.CALL_INGEST_RUNTIME_ROLE
    if role == "all":
        raise RuntimeError(
            "Production recording ingestion runtime must use split service roles, not CALL_INGEST_RUNTIME_ROLE=all."
        )

    if role == "downloader":
        credential_path = settings.GOOGLE_SERVICE_ACCOUNT_FILE.strip()
        if not credential_path or not path_exists(credential_path):
            raise RuntimeError(
                "Production recording ingestion downloader startup failed: the mounted Google service-account secret is missing."
            )
        return

    if role != "inspector":
        return

    scanner_endpoint = settings.CALL_INGEST_SCANNER_ENDPOINT.strip()
    parsed_scanner = urlsplit(scanner_endpoint)
    timeout_seconds = float(settings.CALL_INGEST_INSPECTION_TIMEOUT_SECONDS)

    try:
        if scanner_endpoint.startswith("unix:"):
            if not path_exists(scanner_endpoint.removeprefix("unix:")):
                raise RuntimeError(
                    "Production recording ingestion inspector startup failed: scanner socket is missing."
                )
        elif scanner_endpoint.startswith("/"):
            if not path_exists(scanner_endpoint):
                raise RuntimeError(
                    "Production recording ingestion inspector startup failed: scanner socket is missing."
                )
        else:
            hostname = parsed_scanner.hostname
            port = parsed_scanner.port or 3310
            if not hostname:
                raise RuntimeError(
                    "Production recording ingestion inspector startup failed: scanner endpoint is invalid."
                )
            tcp_probe(hostname, int(port), timeout_seconds)
    except OSError as exc:
        raise RuntimeError(
            "Production recording ingestion inspector startup failed: scanner health probe did not succeed."
        ) from exc

    healthcheck_url = settings.CALL_INGEST_MEDIA_VERIFIER_ENDPOINT.rstrip("/") + "/healthz"
    try:
        status_code = http_probe(healthcheck_url, timeout_seconds)
    except (OSError, URLError) as exc:
        raise RuntimeError(
            "Production recording ingestion inspector startup failed: media verifier health probe did not succeed."
        ) from exc

    if status_code < 200 or status_code >= 300:
        raise RuntimeError(
            "Production recording ingestion inspector startup failed: media verifier health probe returned a non-success status."
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
