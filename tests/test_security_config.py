import os
import pytest
from pydantic import ValidationError
from app.config import get_settings, Settings

@pytest.fixture(autouse=True)
def clear_settings_cache():
    # Clear settings cache and save original environment
    get_settings.cache_clear()
    original_env = dict(os.environ)
    yield
    # Restore environment and clear cache after test
    os.environ.clear()
    os.environ.update(original_env)
    get_settings.cache_clear()


def test_default_settings_load():
    # Ensure any environment variables that might interfere are removed for the default test
    for key in [
        "SECURITY_POLICY_MODE",
        "SECURITY_TIMEZONE",
        "DEFAULT_SHIFT_GRACE_BEFORE_MINUTES",
        "DEFAULT_SHIFT_GRACE_AFTER_MINUTES",
        "CALL_INGEST_ENABLED",
        "CALL_INGEST_GOOGLE_SHEET_ID",
        "CALL_INGEST_WORKSHEET",
        "CALL_INGEST_RANGE",
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "GOOGLE_SERVICE_ACCOUNT_FILE_HOST",
        "CALL_INGEST_DEFAULT_CAMPAIGN_ID",
        "CALL_INGEST_ALLOWED_RECORDING_HOSTS",
        "CALL_INGEST_INTERVAL_MINUTES",
        "CALL_INGEST_DOWNLOAD_CONCURRENCY",
        "CALL_INGEST_RETRY_LIMIT",
        "CALL_INGEST_REQUEST_TIMEOUT_SECONDS",
        "CALL_INGEST_QUARANTINE_DIR",
        "CALL_INGEST_ACCEPTED_DIR",
        "CALL_INGEST_REJECTED_DIR",
        "CALL_INGEST_SCANNER",
        "CALL_INGEST_SCANNER_ENDPOINT",
        "CALL_INGEST_VM_STORAGE_ROOT",
        "CALL_INGEST_INSPECTION_TIMEOUT_SECONDS",
        "CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS",
    ]:
        os.environ.pop(key, None)

    settings = get_settings()
    assert settings.SECURITY_POLICY_MODE == "off"
    assert settings.SECURITY_TIMEZONE == "Africa/Cairo"
    assert settings.DEFAULT_SHIFT_GRACE_BEFORE_MINUTES == 10
    assert settings.DEFAULT_SHIFT_GRACE_AFTER_MINUTES == 10
    assert settings.CALL_INGEST_ENABLED is False
    assert settings.CALL_INGEST_GOOGLE_SHEET_ID == ""
    assert settings.CALL_INGEST_WORKSHEET == "الورقة1"
    assert settings.CALL_INGEST_RANGE == "A:ZZ"
    assert settings.CALL_INGEST_ALLOWED_RECORDING_HOSTS == "archive.dial-fusion.com"
    assert settings.call_ingest_allowed_recording_hosts_list == ["archive.dial-fusion.com"]
    assert settings.GOOGLE_SERVICE_ACCOUNT_FILE_HOST == ""
    assert settings.CALL_INGEST_INTERVAL_MINUTES == 15
    assert settings.CALL_INGEST_DOWNLOAD_CONCURRENCY == 4
    assert settings.CALL_INGEST_RETRY_LIMIT == 3
    assert settings.CALL_INGEST_REQUEST_TIMEOUT_SECONDS == 30
    assert settings.CALL_INGEST_QUARANTINE_DIR == "/var/lib/call-rating/quarantine"
    assert settings.CALL_INGEST_ACCEPTED_DIR == "/var/lib/call-rating/accepted"
    assert settings.CALL_INGEST_REJECTED_DIR == "/var/lib/call-rating/rejected"
    assert settings.CALL_INGEST_SCANNER == "clamd"
    assert settings.CALL_INGEST_SCANNER_ENDPOINT == "/run/clamav/clamd.ctl"
    assert settings.CALL_INGEST_VM_STORAGE_ROOT == "/var/lib/call-rating"
    assert settings.CALL_INGEST_INSPECTION_TIMEOUT_SECONDS == 60
    assert settings.CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS == 60


def test_security_policy_mode_audit():
    os.environ["SECURITY_POLICY_MODE"] = "audit"
    settings = get_settings()
    assert settings.SECURITY_POLICY_MODE == "audit"


def test_security_policy_mode_enforce():
    os.environ["SECURITY_POLICY_MODE"] = "enforce"
    settings = get_settings()
    assert settings.SECURITY_POLICY_MODE == "enforce"


def test_security_policy_mode_normalization():
    os.environ["SECURITY_POLICY_MODE"] = "ENFORCE"
    settings = get_settings()
    assert settings.SECURITY_POLICY_MODE == "enforce"


def test_security_policy_mode_invalid():
    os.environ["SECURITY_POLICY_MODE"] = "strict"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Invalid SECURITY_POLICY_MODE" in str(exc_info.value)


def test_security_timezone_valid():
    os.environ["SECURITY_TIMEZONE"] = "Europe/London"
    settings = get_settings()
    assert settings.SECURITY_TIMEZONE == "Europe/London"


def test_security_timezone_invalid():
    os.environ["SECURITY_TIMEZONE"] = "Invalid/Timezone"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Invalid SECURITY_TIMEZONE" in str(exc_info.value)


def test_grace_minutes_negative():
    os.environ["DEFAULT_SHIFT_GRACE_BEFORE_MINUTES"] = "-5"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Grace minutes must be greater than or equal to 0" in str(exc_info.value)


def test_grace_minutes_too_high():
    os.environ["DEFAULT_SHIFT_GRACE_AFTER_MINUTES"] = "250"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Grace minutes cannot exceed 240 minutes" in str(exc_info.value)


def test_call_ingest_allowlist_cannot_be_blank():
    os.environ["CALL_INGEST_ALLOWED_RECORDING_HOSTS"] = "   "
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "CALL_INGEST_ALLOWED_RECORDING_HOSTS must not be empty" in str(exc_info.value)


def test_call_ingest_allowlist_rejects_urls():
    os.environ["CALL_INGEST_ALLOWED_RECORDING_HOSTS"] = "https://archive.dial-fusion.com"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "bare hostnames or IP addresses" in str(exc_info.value)


def test_call_ingest_limits_must_be_positive():
    os.environ["CALL_INGEST_DOWNLOAD_CONCURRENCY"] = "0"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "CALL_INGEST_DOWNLOAD_CONCURRENCY must be greater than 0" in str(exc_info.value)


def test_call_ingest_sheet_id_rejects_url():
    os.environ["CALL_INGEST_GOOGLE_SHEET_ID"] = "https://docs.google.com/spreadsheets/d/example"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "raw Google Sheet ID" in str(exc_info.value)


def test_call_ingest_directories_must_not_overlap():
    os.environ["CALL_INGEST_ACCEPTED_DIR"] = "/var/lib/call-rating/quarantine/archive"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "must not overlap or be nested" in str(exc_info.value)


def test_call_ingest_enabled_requires_source_secrets():
    os.environ["CALL_INGEST_ENABLED"] = "true"
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "must be set before enabling call ingestion" in str(exc_info.value)


def test_production_can_leave_call_ingestion_disabled_without_source_secrets():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/call_rating"
    os.environ["REDIS_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CELERY_BROKER_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CALL_INGEST_ENABLED"] = "false"

    settings = Settings()

    assert settings.is_production is True
    assert settings.CALL_INGEST_ENABLED is False


def test_production_call_ingest_rejects_combined_runtime_role():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/call_rating"
    os.environ["REDIS_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CELERY_BROKER_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CALL_INGEST_ENABLED"] = "true"
    os.environ["CALL_INGEST_RUNTIME_ROLE"] = "all"
    os.environ["CALL_INGEST_DEFAULT_CAMPAIGN_ID"] = "1"
    os.environ["CALL_INGEST_GOOGLE_SHEET_ID"] = "sheet-id"
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = "/run/secrets/vicdi-sheets-reader.json"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "must not be 'all' in production" in str(exc_info.value)


def test_production_downloader_requires_vm_local_secret_path():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/call_rating"
    os.environ["REDIS_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CELERY_BROKER_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CALL_INGEST_ENABLED"] = "true"
    os.environ["CALL_INGEST_RUNTIME_ROLE"] = "downloader"
    os.environ["CALL_INGEST_DEFAULT_CAMPAIGN_ID"] = "1"
    os.environ["CALL_INGEST_GOOGLE_SHEET_ID"] = "sheet-id"
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = "/tmp/not-a-secret.json"
    os.environ["GOOGLE_SERVICE_ACCOUNT_FILE_HOST"] = "/var/lib/call-rating/secrets/vicdi-sheets-reader.json"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "/run/secrets" in str(exc_info.value)


def test_production_ingest_storage_must_stay_under_vm_root():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/call_rating"
    os.environ["REDIS_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CELERY_BROKER_URL"] = "redis://:password@localhost:6379/0"
    os.environ["CALL_INGEST_ENABLED"] = "true"
    os.environ["CALL_INGEST_RUNTIME_ROLE"] = "scheduler"
    os.environ["CALL_INGEST_DEFAULT_CAMPAIGN_ID"] = "1"
    os.environ["CALL_INGEST_QUARANTINE_DIR"] = "/srv/quarantine"

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "CALL_INGEST_QUARANTINE_DIR must stay under CALL_INGEST_VM_STORAGE_ROOT" in str(exc_info.value)
