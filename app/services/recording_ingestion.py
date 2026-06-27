from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
from queue import Empty, Queue
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Protocol
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.config import get_settings
from app.models import AuditEvent, Campaign, CampaignStatus, Employee
from app.models import (
    Call,
    CallStatus,
    RecordingIngestionAttempt,
    RecordingIngestionAttemptPhase,
    RecordingIngestionAttemptStatus,
    RecordingIngestionInspectionStatus,
    RecordingIngestionRecord,
    RecordingIngestionRecordStatus,
    RecordingIngestionRun,
    RecordingIngestionRunStatus,
    RecordingIngestionRunTrigger,
)
from app.services.employee_identity import normalize_employee_code


logging.getLogger("httpx").setLevel(logging.WARNING)

SUPPORTED_AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"})
MAX_REDIRECTS = 5
WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/webm": ".webm",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "application/octet-stream": ".audio",
}
CLAMD_STREAM_CHUNK_SIZE = 64 * 1024
MEDIA_VERIFIER_MAX_OUTPUT_BYTES = 256 * 1024
RETRY_BACKOFF_MINUTES = (1, 5, 15)
AUTOMATIC_RETRYABLE_CATEGORIES = frozenset(
    {
        "download_timeout",
        "rate_limited",
        "server_error",
        "storage_failed",
        "inspection_queue_failed",
        "handoff_queue_failed",
    }
)
MANUAL_RETRYABLE_CATEGORIES = AUTOMATIC_RETRYABLE_CATEGORIES | frozenset(
    {
        "access_denied",
        "recording_not_found",
        "download_failed",
    }
)
MANUAL_RETRYABLE_STATUSES = frozenset(
    {
        RecordingIngestionRecordStatus.FAILED,
        RecordingIngestionRecordStatus.RETRY_SCHEDULED,
        RecordingIngestionRecordStatus.REQUIRES_REVIEW,
    }
)
HANDOFF_RECONCILIATION_CLAIM_CATEGORY = "handoff_dispatching"
HANDOFF_RECONCILIATION_CLAIM_DETAIL = "Call handoff reconciliation is in progress."
HANDOFF_RECONCILIATION_LEASE_SECONDS = 300
SENSITIVE_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
SENSITIVE_WINDOWS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\(?:[^\\/:*?\"<>|\r\n]+\\)*[^\\/:*?\"<>|\r\n]*")
SENSITIVE_UNIX_PATH_PATTERN = re.compile(r"(?:^|[\s(])(/[^)\s]+)")
SENSITIVE_SECRET_PATTERN = re.compile(r"(?i)\b(token|secret|password|api[_-]?key)\s*[:=]\s*\S+")
REMOTE_MEDIA_VERIFIER_ERROR_CATEGORIES = frozenset(
    {
        "media_verification_failed",
        "media_verification_timeout",
        "media_verification_unavailable",
    }
)
INGESTION_AUDIT_MANUAL_START = "RECORDING_INGESTION_MANUAL_START"
INGESTION_AUDIT_RETRY = "RECORDING_INGESTION_RETRY"
INGESTION_AUDIT_REJECTED = "RECORDING_INGESTION_RECORD_REJECTED"
INGESTION_AUDIT_ACCEPTED = "RECORDING_INGESTION_ACCEPTED_STORAGE"
INGESTION_AUDIT_HANDOFF = "RECORDING_INGESTION_HANDOFF"
INGESTION_AUDIT_RECONCILIATION = "RECORDING_INGESTION_RECONCILIATION"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sanitize_ingestion_text(value: str | None) -> str | None:
    if value is None:
        return None

    sanitized = value.strip()
    if not sanitized:
        return None

    sanitized = SENSITIVE_SECRET_PATTERN.sub(lambda match: f"{match.group(1)}=[redacted]", sanitized)
    sanitized = SENSITIVE_URL_PATTERN.sub("[redacted-url]", sanitized)
    sanitized = SENSITIVE_WINDOWS_PATH_PATTERN.sub("[redacted-path]", sanitized)
    sanitized = SENSITIVE_UNIX_PATH_PATTERN.sub(
        lambda match: match.group(0).replace(match.group(1), "[redacted-path]"),
        sanitized,
    )
    return sanitized


def _sanitize_audit_payload(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, datetime):
        coerced = _coerce_utc_datetime(value)
        return coerced.isoformat() if coerced is not None else None
    if isinstance(value, Path):
        return _sanitize_ingestion_text(str(value))
    if hasattr(value, "value") and isinstance(getattr(value, "value"), str):
        return getattr(value, "value")
    if isinstance(value, str):
        return _sanitize_ingestion_text(value)
    if isinstance(value, dict):
        return {str(key): _sanitize_audit_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_audit_payload(item) for item in value]
    return _sanitize_ingestion_text(str(value))


def _serialize_audit_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    sanitized = _sanitize_audit_payload(payload)
    return json.dumps(sanitized, ensure_ascii=False, sort_keys=True)


def add_recording_ingestion_audit_event(
    db: Session,
    *,
    action: str,
    actor_id: int | None = None,
    actor_email: str | None = None,
    target: str | None = None,
    before_state: Any = None,
    after_state: Any = None,
    reason: str | None = None,
    success: bool = True,
) -> AuditEvent:
    if actor_email is None and actor_id is not None:
        actor = db.get(Employee, actor_id)
        if actor is not None:
            actor_email = actor.email

    event = AuditEvent(
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        target=_sanitize_ingestion_text(target),
        before_state=_serialize_audit_payload(before_state),
        after_state=_serialize_audit_payload(after_state),
        reason=_sanitize_ingestion_text(reason),
        success=success,
    )
    db.add(event)
    db.flush()
    return event


class RecordingIngestionSecurityError(RuntimeError):
    def __init__(self, category: str, detail: str):
        super().__init__(detail)
        self.category = category
        self.detail = detail


@dataclass(frozen=True)
class RecordingStorageLayout:
    quarantine_dir: Path
    accepted_dir: Path
    rejected_dir: Path
    state_dir: Path


@dataclass(frozen=True)
class QuarantinedRecording:
    quarantine_path: Path
    safe_filename: str
    byte_size: int
    file_sha256: str
    content_type: str | None
    final_url: str


@dataclass(frozen=True)
class MalwareScanResult:
    status: RecordingIngestionInspectionStatus
    scanner_name: str
    scanner_version: str | None = None
    error_category: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class MediaVerificationResult:
    status: RecordingIngestionInspectionStatus
    duration_seconds: float | None = None
    error_category: str | None = None
    error_detail: str | None = None


@dataclass(frozen=True)
class SourceSheetValidationError:
    row_number: int | None
    category: str
    detail: str


@dataclass(frozen=True)
class SourceSheetRow:
    row_number: int
    raw_values: dict[str, str]
    normalized_values: dict[str, str]


@dataclass(frozen=True)
class SourceSheetReadResult:
    spreadsheet_id: str
    worksheet_name: str
    cell_range: str
    headers: tuple[str, ...]
    rows: list[SourceSheetRow]
    errors: list[SourceSheetValidationError]


@dataclass(frozen=True)
class SourceEmployeeResolution:
    employee_id: int
    employee_code: str
    match_type: str


@dataclass(frozen=True)
class SourceCampaignPreflight:
    id: int
    campaign_name: str
    status: str


@dataclass(frozen=True)
class SourceRowMapping:
    source_name: str
    source_key: str
    source_row_number: int
    source_payload: dict[str, str]
    recording_url: str
    recording_url_fingerprint: str
    source_call_date: datetime | None
    source_score: float | None
    source_quality_notes: str | None
    employee_id: int
    campaign_id: int


@dataclass(frozen=True)
class SourceRecordClaim:
    record: RecordingIngestionRecord
    created: bool
    disposition: RecordingIngestionRecordStatus


@dataclass(frozen=True)
class IngestionRowOutcome:
    row_number: int
    source_reference: str
    outcome: str
    record_id: int | None = None
    record_status: RecordingIngestionRecordStatus | None = None
    error_category: str | None = None
    error_detail: str | None = None
    created: bool = False
    retryable: bool = False


REQUIRED_SOURCE_HEADERS = ("DATE", "CODE", "CRDTS", "NAME", "CALL LINK", "SCORE", "WEAKNESS")
REQUIRED_SOURCE_ROW_FIELDS = ("DATE", "CODE", "NAME", "CALL LINK", "SCORE", "WEAKNESS")
SOURCE_PAYLOAD_FIELDS = (*REQUIRED_SOURCE_HEADERS, "QUALITY FEEDBACK")
SOURCE_PAYLOAD_PREFIXES = ("QUALITY FEEDBACK",)


class MalwareScanner(Protocol):
    def scan(self, path: Path, timeout_seconds: int) -> MalwareScanResult:
        ...


class MediaVerifier(Protocol):
    def verify(self, path: Path, timeout_seconds: int) -> MediaVerificationResult:
        ...


def _normalize_sheet_header(header: str | None) -> str:
    return " ".join((header or "").strip().upper().split())


def _normalize_sheet_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_person_name(value: str | None) -> str:
    return " ".join((value or "").strip().split()).casefold()


def _parse_boolish_text(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _sheet_range_with_worksheet(worksheet_name: str, cell_range: str) -> str:
    escaped = worksheet_name.replace("'", "''")
    return f"'{escaped}'!{cell_range}"


def _sheet_range_start_row(cell_range: str) -> int:
    range_part = cell_range.split("!", 1)[-1]
    start_part = range_part.split(":", 1)[0]
    match = re.search(r"(\d+)", start_part)
    return int(match.group(1)) if match else 1


def _build_google_sheets_service() -> Any:
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - dependency availability is validated in deployment
        raise RecordingIngestionSecurityError(
            "google_sheets_unavailable",
            "Google Sheets client dependencies are unavailable.",
        ) from exc

    settings = get_settings()
    credentials_file = settings.GOOGLE_SERVICE_ACCOUNT_FILE.strip()
    if not credentials_file:
        raise RecordingIngestionSecurityError(
            "missing_sheet_credentials",
            "GOOGLE_SERVICE_ACCOUNT_FILE is not configured.",
        )

    scopes = ("https://www.googleapis.com/auth/spreadsheets.readonly",)
    credentials = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _validate_source_headers(headers: list[str]) -> list[SourceSheetValidationError]:
    normalized_headers = {_normalize_sheet_header(header) for header in headers if _normalize_sheet_header(header)}
    missing = [header for header in REQUIRED_SOURCE_HEADERS if header not in normalized_headers]
    if not missing:
        return []
    return [
        SourceSheetValidationError(
            row_number=None,
            category="missing_required_columns",
            detail="Missing required columns: " + ", ".join(missing),
        )
    ]


def _map_sheet_row(
    headers: list[str],
    row_values: list[Any],
    *,
    row_number: int,
) -> SourceSheetRow | SourceSheetValidationError:
    if not headers:
        return SourceSheetValidationError(
            row_number=row_number,
            category="missing_required_columns",
            detail="The source sheet must contain a header row.",
        )

    padded_values = [_normalize_sheet_value(value) for value in row_values]
    if len(padded_values) > len(headers):
        headers = [
            *headers,
            *[f"UNNAMED COLUMN {index}" for index in range(len(headers) + 1, len(padded_values) + 1)],
        ]

    raw_values = {
        headers[index]: padded_values[index] if index < len(padded_values) else ""
        for index in range(len(headers))
    }
    normalized_values = {_normalize_sheet_header(header): value for header, value in raw_values.items() if _normalize_sheet_header(header)}
    missing_fields = [
        field for field in REQUIRED_SOURCE_ROW_FIELDS if not (normalized_values.get(field) or "").strip()
    ]
    if missing_fields:
        return SourceSheetValidationError(
            row_number=row_number,
            category="missing_required_row_fields",
            detail="Missing required values: " + ", ".join(missing_fields),
        )
    return SourceSheetRow(row_number=row_number, raw_values=raw_values, normalized_values=normalized_values)


def read_source_sheet_rows(
    *,
    spreadsheet_id: str | None = None,
    worksheet_name: str | None = None,
    cell_range: str | None = None,
    service: Any | None = None,
) -> SourceSheetReadResult:
    settings = get_settings()
    source_spreadsheet_id = (spreadsheet_id or settings.CALL_INGEST_GOOGLE_SHEET_ID).strip()
    source_worksheet_name = (worksheet_name or settings.CALL_INGEST_WORKSHEET).strip()
    source_cell_range = (cell_range or settings.CALL_INGEST_RANGE).strip()
    if not source_spreadsheet_id:
        raise RecordingIngestionSecurityError("missing_sheet_configuration", "CALL_INGEST_GOOGLE_SHEET_ID is not configured.")
    if not source_worksheet_name:
        raise RecordingIngestionSecurityError("missing_sheet_configuration", "CALL_INGEST_WORKSHEET is not configured.")
    if not source_cell_range:
        raise RecordingIngestionSecurityError("missing_sheet_configuration", "CALL_INGEST_RANGE is not configured.")

    active_service = service or _build_google_sheets_service()
    request_range = _sheet_range_with_worksheet(source_worksheet_name, source_cell_range)
    response = (
        active_service.spreadsheets()
        .values()
        .get(spreadsheetId=source_spreadsheet_id, range=request_range, majorDimension="ROWS")
        .execute()
    )

    values = response.get("values") or []
    if not values:
        raise RecordingIngestionSecurityError("empty_sheet", "The configured source sheet is empty.")

    headers = [_normalize_sheet_value(header) for header in values[0]]
    header_errors = _validate_source_headers(headers)
    if header_errors:
        raise RecordingIngestionSecurityError("missing_required_columns", header_errors[0].detail)

    start_row = _sheet_range_start_row(response.get("range") or request_range)
    rows: list[SourceSheetRow] = []
    errors: list[SourceSheetValidationError] = []
    for offset, row_values in enumerate(values[1:], start=1):
        mapped = _map_sheet_row(headers, row_values, row_number=start_row + offset)
        if isinstance(mapped, SourceSheetValidationError):
            errors.append(mapped)
        else:
            rows.append(mapped)

    return SourceSheetReadResult(
        spreadsheet_id=source_spreadsheet_id,
        worksheet_name=source_worksheet_name,
        cell_range=source_cell_range,
        headers=tuple(_normalize_sheet_header(header) for header in headers),
        rows=rows,
        errors=errors,
    )


def _row_to_source_payload(row: SourceSheetRow) -> dict[str, str]:
    return dict(row.raw_values)


def _source_recording_url(row: SourceSheetRow) -> str:
    return (row.normalized_values.get("CALL LINK") or "").strip()


def _source_row_text(row: SourceSheetRow, field_name: str) -> str:
    return (row.normalized_values.get(field_name) or "").strip()


def _source_call_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _source_score(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _source_quality_notes(row: SourceSheetRow) -> str | None:
    notes = []
    for field_name in ("WEAKNESS", "QUALITY FEEDBACK"):
        value = (row.raw_values.get(field_name) or "").strip()
        if value:
            notes.append(value)
    extra_feedback = [
        value.strip()
        for key, value in row.raw_values.items()
        if _normalize_sheet_header(key).startswith("QUALITY FEEDBACK") and _normalize_sheet_header(key) != "QUALITY FEEDBACK" and value.strip()
    ]
    notes.extend(extra_feedback)
    return "\n".join(notes) if notes else None


def preflight_active_campaign(db: Session) -> SourceCampaignPreflight:
    settings = get_settings()
    campaign_id = int(settings.CALL_INGEST_DEFAULT_CAMPAIGN_ID)
    if campaign_id <= 0:
        raise RecordingIngestionSecurityError(
            "missing_campaign",
            "CALL_INGEST_DEFAULT_CAMPAIGN_ID must be configured before reading source rows.",
        )

    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise RecordingIngestionSecurityError(
            "missing_campaign",
            f"Configured campaign {campaign_id} does not exist.",
        )
    if campaign.status != CampaignStatus.ACTIVE:
        raise RecordingIngestionSecurityError(
            "inactive_campaign",
            f"Configured campaign {campaign_id} is not active.",
    )
    return SourceCampaignPreflight(id=campaign.id, campaign_name=campaign.name, status=campaign.status.value)


def _require_active_campaign(db: Session, campaign: Campaign | None = None) -> SourceCampaignPreflight:
    if campaign is None:
        return preflight_active_campaign(db)

    if campaign.status != CampaignStatus.ACTIVE:
        raise RecordingIngestionSecurityError(
            "inactive_campaign",
            f"Configured campaign {campaign.id} is not active.",
        )
    return SourceCampaignPreflight(id=campaign.id, campaign_name=campaign.name, status=campaign.status.value)


def resolve_source_employee(db: Session, *, row: dict[str, str]) -> SourceEmployeeResolution:
    code = normalize_employee_code(row.get("CODE", ""))
    if code:
        employee = db.query(Employee).filter(Employee.employee_code == code).one_or_none()
        if employee:
            return SourceEmployeeResolution(employee_id=employee.id, employee_code=employee.employee_code, match_type="code")

    normalized_name = _normalize_person_name(row.get("NAME", ""))
    if not normalized_name:
        raise RecordingIngestionSecurityError("missing_employee_mapping", "Source NAME is required when CODE does not resolve.")

    matches = [
        employee
        for employee in db.query(Employee).filter(Employee.status == "active").all()
        if _normalize_person_name(employee.name) == normalized_name
    ]
    if not matches:
        raise RecordingIngestionSecurityError("missing_employee_mapping", "Source NAME does not resolve to a known employee.")
    if len(matches) > 1:
        raise RecordingIngestionSecurityError("ambiguous_employee_mapping", "Source NAME is ambiguous and resolves to multiple employees.")

    employee = matches[0]
    return SourceEmployeeResolution(employee_id=employee.id, employee_code=employee.employee_code, match_type="name")


def _source_key_from_row(source_name: str, row: SourceSheetRow) -> str:
    crdts = _source_row_text(row, "CRDTS")
    if crdts:
        return f"{source_name}:{crdts}"
    identity = "|".join(
        [
            _source_row_text(row, "DATE"),
            _source_row_text(row, "CODE"),
            _source_row_text(row, "NAME"),
            _source_recording_url(row),
        ]
    )
    return f"{source_name}:{identity}"


def map_source_row(
    *,
    db: Session,
    row: dict[str, str] | SourceSheetRow,
    row_number: int,
    source_name: str,
    campaign: Campaign | None = None,
) -> SourceRowMapping:
    if isinstance(row, SourceSheetRow):
        source_row = row
    else:
        raw_row = {str(key): _normalize_sheet_value(value) for key, value in row.items()}
        normalized_row = {_normalize_sheet_header(key): value for key, value in raw_row.items() if _normalize_sheet_header(key)}
        source_row = SourceSheetRow(row_number=row_number, raw_values=raw_row, normalized_values=normalized_row)

    validation_errors = [
        field for field in REQUIRED_SOURCE_ROW_FIELDS if not _source_row_text(source_row, field)
    ]
    if validation_errors:
        raise RecordingIngestionSecurityError(
            "missing_required_row_fields",
            "Missing required values: " + ", ".join(validation_errors),
        )

    active_campaign = _require_active_campaign(db, campaign=campaign)
    employee = resolve_source_employee(db, row=source_row.normalized_values)
    source_payload = _row_to_source_payload(source_row)
    recording_url = _source_recording_url(source_row)
    return SourceRowMapping(
        source_name=source_name,
        source_key=_source_key_from_row(source_name, source_row),
        source_row_number=row_number,
        source_payload=source_payload,
        recording_url=recording_url,
        recording_url_fingerprint=hashlib.sha256(recording_url.encode("utf-8")).hexdigest(),
        source_call_date=_source_call_date(_source_row_text(source_row, "DATE")),
        source_score=_source_score(_source_row_text(source_row, "SCORE")),
        source_quality_notes=_source_quality_notes(source_row),
        employee_id=employee.employee_id,
        campaign_id=active_campaign.id,
    )


def _build_recording_claim_record(
    *,
    run: RecordingIngestionRun,
    mapping: SourceRowMapping,
) -> RecordingIngestionRecord:
    return RecordingIngestionRecord(
        ingestion_run_id=run.id,
        source_name=mapping.source_name,
        source_key=mapping.source_key,
        source_row_number=mapping.source_row_number,
        source_payload=mapping.source_payload,
        recording_url=mapping.recording_url,
        recording_url_fingerprint=mapping.recording_url_fingerprint,
        source_call_date=mapping.source_call_date,
        source_score=mapping.source_score,
        source_quality_notes=mapping.source_quality_notes,
        employee_id=mapping.employee_id,
        campaign_id=mapping.campaign_id,
        status=RecordingIngestionRecordStatus.DOWNLOADING,
        attempt_count=1,
    )


def _record_duplicate_claim_attempt(
    db: Session,
    *,
    record: RecordingIngestionRecord,
    run: RecordingIngestionRun,
) -> None:
    """Keep repeat evaluations auditable without overwriting successful state."""
    record.attempt_count = max(record.attempt_count, 0) + 1
    attempt = create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.VALIDATION)
    _finalize_attempt(attempt, RecordingIngestionAttemptStatus.SKIPPED_DUPLICATE)


def _classify_existing_record_claim(
    db: Session,
    record: RecordingIngestionRecord,
    *,
    run: RecordingIngestionRun,
    mapping: SourceRowMapping,
) -> SourceRecordClaim:
    if record.status in {
        RecordingIngestionRecordStatus.SUBMITTED,
        RecordingIngestionRecordStatus.DUPLICATE,
        RecordingIngestionRecordStatus.REQUIRES_REVIEW,
    }:
        disposition = (
            RecordingIngestionRecordStatus.DUPLICATE
            if record.recording_url_fingerprint == mapping.recording_url_fingerprint
            else RecordingIngestionRecordStatus.REQUIRES_REVIEW
        )
        _record_duplicate_claim_attempt(db, record=record, run=run)
        db.flush()
        return SourceRecordClaim(record=record, created=False, disposition=disposition)
    return SourceRecordClaim(record=record, created=False, disposition=record.status)


def claim_source_record(
    db: Session,
    *,
    run: RecordingIngestionRun,
    mapping: SourceRowMapping,
) -> SourceRecordClaim:
    existing = (
        db.query(RecordingIngestionRecord)
        .filter(
            RecordingIngestionRecord.source_name == mapping.source_name,
            RecordingIngestionRecord.source_key == mapping.source_key,
        )
        .one_or_none()
    )
    if existing is not None:
        return _classify_existing_record_claim(db, existing, run=run, mapping=mapping)

    record = _build_recording_claim_record(run=run, mapping=mapping)
    try:
        db.add(record)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(RecordingIngestionRecord)
            .filter(
                RecordingIngestionRecord.source_name == mapping.source_name,
                RecordingIngestionRecord.source_key == mapping.source_key,
            )
            .one_or_none()
        )
        if existing is None:
            raise
        return _classify_existing_record_claim(db, existing, run=run, mapping=mapping)

    return SourceRecordClaim(record=record, created=True, disposition=record.status)


def create_ingestion_run(
    db: Session,
    *,
    source_name: str,
    trigger: RecordingIngestionRunTrigger,
    requested_by_employee_id: int | None = None,
) -> RecordingIngestionRun:
    active_run = find_active_ingestion_run(db, source_name=source_name)
    if active_run is not None:
        raise RecordingIngestionSecurityError(
            "active_run_exists",
            f"Source {source_name} already has an active ingestion run.",
        )

    run = RecordingIngestionRun(
        source_name=source_name,
        trigger=trigger,
        status=RecordingIngestionRunStatus.REQUESTED,
        requested_by_employee_id=requested_by_employee_id,
        rows_seen=0,
        new_count=0,
        duplicate_count=0,
        success_count=0,
        failed_count=0,
        retryable_count=0,
    )
    db.add(run)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        active_run = find_active_ingestion_run(db, source_name=source_name)
        if active_run is not None:
            raise RecordingIngestionSecurityError(
                "active_run_exists",
                f"Source {source_name} already has an active ingestion run.",
            ) from exc
        raise
    return run


def find_active_ingestion_run(
    db: Session,
    *,
    source_name: str,
) -> RecordingIngestionRun | None:
    return (
        db.query(RecordingIngestionRun)
        .filter(
            RecordingIngestionRun.source_name == source_name,
            RecordingIngestionRun.status.in_(
                (
                    RecordingIngestionRunStatus.REQUESTED,
                    RecordingIngestionRunStatus.READING_SOURCE,
                    RecordingIngestionRunStatus.PROCESSING,
                )
            ),
        )
        .order_by(RecordingIngestionRun.created_at.desc())
        .first()
    )


def _build_ingestion_storage_layout() -> RecordingStorageLayout:
    settings = get_settings()
    layout = build_storage_layout(
        quarantine_dir=settings.CALL_INGEST_QUARANTINE_DIR,
        accepted_dir=settings.CALL_INGEST_ACCEPTED_DIR,
        rejected_dir=settings.CALL_INGEST_REJECTED_DIR,
    )
    if settings.CALL_INGEST_RUNTIME_ROLE == "downloader":
        layout.quarantine_dir.mkdir(parents=True, exist_ok=True)
        return layout
    return ensure_storage_layout(layout)


def _build_ingestion_allowed_hosts() -> set[str]:
    return {host.strip().lower() for host in get_settings().call_ingest_allowed_recording_hosts_list if host.strip()}


def _classify_claim_outcome(claim: SourceRecordClaim) -> str:
    record = claim.record
    if claim.created:
        return "new"
    if claim.disposition == RecordingIngestionRecordStatus.REQUIRES_REVIEW:
        return "requires_review"
    if claim.disposition == RecordingIngestionRecordStatus.DUPLICATE:
        return "duplicate"
    if record.status in {
        RecordingIngestionRecordStatus.DUPLICATE,
        RecordingIngestionRecordStatus.SUBMITTED,
        RecordingIngestionRecordStatus.PENDING,
        RecordingIngestionRecordStatus.DOWNLOADING,
        RecordingIngestionRecordStatus.QUARANTINED,
        RecordingIngestionRecordStatus.INSPECTING,
        RecordingIngestionRecordStatus.ACCEPTED,
        RecordingIngestionRecordStatus.HANDOFF_PENDING,
    }:
        return "duplicate"
    if record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED:
        return "retryable"
    if record.status == RecordingIngestionRecordStatus.FAILED:
        return "failed"
    return record.status.value


def _queue_call_processing(call_id: int) -> None:
    from app.worker import queue_call_audio_processing

    queue_call_audio_processing(call_id)


def _record_row_failure(
    *,
    row_number: int,
    source_reference: str,
    category: str,
    detail: str,
    record: RecordingIngestionRecord | None = None,
    created: bool = False,
    retryable: bool = False,
) -> IngestionRowOutcome:
    return IngestionRowOutcome(
        row_number=row_number,
        source_reference=source_reference,
        outcome="retryable" if retryable else "failed",
        record_id=record.id if record is not None else None,
        record_status=record.status if record is not None else None,
        error_category=category,
        error_detail=_sanitize_ingestion_text(detail),
        created=created,
        retryable=retryable,
    )


def _record_row_success(
    *,
    row_number: int,
    source_reference: str,
    outcome: str,
    record: RecordingIngestionRecord | None = None,
    created: bool = False,
) -> IngestionRowOutcome:
    return IngestionRowOutcome(
        row_number=row_number,
        source_reference=source_reference,
        outcome=outcome,
        record_id=record.id if record is not None else None,
        record_status=record.status if record is not None else None,
        created=created,
    )


def _retry_delay_seconds_for_attempt(attempt_number: int) -> int | None:
    index = max(attempt_number - 1, 0)
    if index >= len(RETRY_BACKOFF_MINUTES):
        return None
    return RETRY_BACKOFF_MINUTES[index] * 60


def _classify_download_exception(exc: Exception) -> tuple[str, str, int | None]:
    if isinstance(exc, RecordingIngestionSecurityError):
        return exc.category, exc.detail, None
    if isinstance(exc, httpx.TimeoutException):
        return "download_timeout", "Recording download timed out.", None
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        if status_code in {401, 403}:
            category = "access_denied"
        elif status_code == 404:
            category = "recording_not_found"
        elif status_code == 429:
            category = "rate_limited"
        elif status_code >= 500:
            category = "server_error"
        else:
            category = "download_failed"
        return category, f"Recording endpoint returned HTTP {status_code}.", status_code
    if isinstance(exc, OSError):
        return "storage_failed", "Recording could not be written to guest storage.", None
    return "download_failed", _sanitize_ingestion_text(str(exc)) or "Recording download failed.", None


def _apply_failure_policy(
    record: RecordingIngestionRecord,
    *,
    category: str,
    detail: str,
    attempt: RecordingIngestionAttempt | None = None,
) -> int | None:
    sanitized_detail = _sanitize_ingestion_text(detail) or "Recording ingestion failed."
    delay_seconds = (
        _retry_delay_seconds_for_attempt(record.attempt_count)
        if category in AUTOMATIC_RETRYABLE_CATEGORIES
        else None
    )
    record.last_error_category = category
    record.last_error_detail = sanitized_detail
    record.completed_at = utcnow()

    if delay_seconds is None:
        record.status = RecordingIngestionRecordStatus.FAILED
        record.next_retry_at = None
        if attempt is not None:
            _finalize_attempt(
                attempt,
                RecordingIngestionAttemptStatus.FAILED,
                error_category=category,
                error_detail=sanitized_detail,
            )
        return None

    record.status = RecordingIngestionRecordStatus.RETRY_SCHEDULED
    record.next_retry_at = utcnow() + timedelta(seconds=delay_seconds)
    if attempt is not None:
        _finalize_attempt(
            attempt,
            RecordingIngestionAttemptStatus.RETRY_SCHEDULED,
            error_category=category,
            error_detail=sanitized_detail,
        )
    return delay_seconds


def _queue_retry_if_needed(
    retry_queue: Callable[[int, int], Any] | None,
    *,
    record_id: int,
    delay_seconds: int | None,
) -> None:
    if retry_queue is None or delay_seconds is None:
        return
    retry_queue(record_id, delay_seconds)


def create_call_for_accepted_recording(db: Session, record: RecordingIngestionRecord) -> Call:
    if record.stored_file_path is None:
        raise RecordingIngestionSecurityError("missing_accepted_file", "Accepted recording file path is missing.")
    if record.employee_id is None or record.campaign_id is None:
        raise RecordingIngestionSecurityError("missing_call_linkage", "Accepted recording is missing employee or campaign linkage.")

    existing_call = record.call or (db.get(Call, record.call_id) if record.call_id else None)
    if existing_call is not None:
        return existing_call

    accepted_path = Path(record.stored_file_path)
    if not accepted_path.is_file():
        raise RecordingIngestionSecurityError("missing_accepted_file", "Accepted recording file is missing from storage.")

    call = Call(
        employee_id=record.employee_id,
        campaign_id=record.campaign_id,
        audio_file_path=str(accepted_path),
        original_filename=accepted_path.name,
        audio_duration=None,
        source="sheet_ingestion",
        status=CallStatus.PENDING,
    )
    db.add(call)
    db.flush()
    record.call = call
    return call


def handoff_accepted_recording(
    db: Session,
    record: RecordingIngestionRecord,
    *,
    run: RecordingIngestionRun | None = None,
    queue_task: Any | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> Call:
    run = run or record.ingestion_run or db.get(RecordingIngestionRun, record.ingestion_run_id)
    call = create_call_for_accepted_recording(db, record)
    if record.pipeline_queued_at is not None and record.status == RecordingIngestionRecordStatus.SUBMITTED:
        return call

    handoff_attempt = (
        create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.HANDOFF)
        if run is not None
        else None
    )
    record.status = RecordingIngestionRecordStatus.HANDOFF_PENDING
    record.last_error_category = None
    record.last_error_detail = None
    db.flush()
    db.commit()

    queue_task = queue_task or _queue_call_processing
    try:
        queue_task(call.id)
    except Exception as exc:
        delay_seconds = _apply_failure_policy(
            record,
            category="handoff_queue_failed",
            detail=_sanitize_ingestion_text(str(exc)) or "Call processing queue dispatch failed.",
            attempt=handoff_attempt,
        )
        db.commit()
        _queue_retry_if_needed(retry_queue, record_id=record.id, delay_seconds=delay_seconds)
        return call

    record.pipeline_queued_at = utcnow()
    record.status = RecordingIngestionRecordStatus.SUBMITTED
    record.last_error_category = None
    record.last_error_detail = None
    record.next_retry_at = None
    record.completed_at = utcnow()
    if handoff_attempt is not None:
        _finalize_attempt(handoff_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)
    add_recording_ingestion_audit_event(
        db,
        action=INGESTION_AUDIT_HANDOFF,
        target=f"Call #{call.id}",
        after_state={
            "run_id": record.ingestion_run_id,
            "record_id": record.id,
            "call_id": call.id,
            "status": record.status,
            "pipeline_queued_at": record.pipeline_queued_at,
        },
        success=True,
    )
    db.commit()
    return call


def _sheet_row_detail(row: SourceSheetValidationError) -> str:
    return f"Row {row.row_number or 'header'}: {row.category} - {row.detail}"

def _validate_absolute_guest_path(path_value: str, field_name: str) -> Path:
    stripped = path_value.strip()
    native_path = Path(stripped)
    if native_path.is_absolute():
        normalized = native_path
    else:
        posix_path = PurePosixPath(stripped)
        if not posix_path.is_absolute():
            raise RecordingIngestionSecurityError("unsafe_storage_path", f"{field_name} must be an absolute guest path.")
        normalized = Path(posix_path.as_posix())
    if len(normalized.parts) < 2:
        raise RecordingIngestionSecurityError("unsafe_storage_path", f"{field_name} must not point at the filesystem root.")
    return normalized


def _paths_overlap(first: Path, second: Path) -> bool:
    first_parts = first.parts
    second_parts = second.parts
    shorter, longer = (first_parts, second_parts) if len(first_parts) <= len(second_parts) else (second_parts, first_parts)
    return shorter == longer[: len(shorter)]


def _common_parent(paths: list[Path]) -> Path:
    common = os.path.commonpath([str(path) for path in paths])
    return Path(common)


def build_storage_layout(
    quarantine_dir: str | Path | None = None,
    accepted_dir: str | Path | None = None,
    rejected_dir: str | Path | None = None,
) -> RecordingStorageLayout:
    settings = get_settings()
    quarantine = _validate_absolute_guest_path(str(quarantine_dir or settings.CALL_INGEST_QUARANTINE_DIR), "CALL_INGEST_QUARANTINE_DIR")
    accepted = _validate_absolute_guest_path(str(accepted_dir or settings.CALL_INGEST_ACCEPTED_DIR), "CALL_INGEST_ACCEPTED_DIR")
    rejected = _validate_absolute_guest_path(str(rejected_dir or settings.CALL_INGEST_REJECTED_DIR), "CALL_INGEST_REJECTED_DIR")

    for left, right in ((quarantine, accepted), (quarantine, rejected), (accepted, rejected)):
        if _paths_overlap(left, right):
            raise RecordingIngestionSecurityError("unsafe_storage_path", "Ingestion storage directories must not overlap or be nested.")

    root = _common_parent([quarantine, accepted, rejected])
    state_dir = root / "state"
    if any(_paths_overlap(state_dir, other) for other in (quarantine, accepted, rejected)):
        raise RecordingIngestionSecurityError("unsafe_storage_path", "Derived state directory must not overlap quarantine, accepted, or rejected storage.")

    return RecordingStorageLayout(
        quarantine_dir=quarantine,
        accepted_dir=accepted,
        rejected_dir=rejected,
        state_dir=state_dir,
    )


def ensure_storage_layout(layout: RecordingStorageLayout) -> RecordingStorageLayout:
    for path in (layout.quarantine_dir, layout.accepted_dir, layout.rejected_dir, layout.state_dir):
        path.mkdir(parents=True, exist_ok=True)
        try:
            path.chmod(0o750)
        except OSError:
            pass
    return layout


def _read_file_prefix(path: Path, length: int) -> bytes:
    with path.open("rb") as handle:
        return handle.read(length)


def _stream_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_existing_path_within(base_dir: Path, candidate: Path, *, field_name: str) -> Path:
    try:
        base_resolved = base_dir.resolve(strict=True)
    except FileNotFoundError as exc:
        raise RecordingIngestionSecurityError("unsafe_storage_path", f"{field_name} base directory does not exist.") from exc

    candidate_absolute = candidate if candidate.is_absolute() else base_resolved / candidate
    try:
        candidate_resolved = candidate_absolute.resolve(strict=True)
    except FileNotFoundError as exc:
        raise RecordingIngestionSecurityError("missing_quarantine_file", f"{field_name} does not exist.") from exc

    try:
        candidate_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise RecordingIngestionSecurityError("unsafe_storage_path", f"{field_name} must stay inside {base_resolved}.") from exc

    if candidate_absolute.is_symlink():
        raise RecordingIngestionSecurityError("unsafe_storage_path", f"{field_name} must not be a symbolic link.")

    return candidate_resolved


def _ensure_same_filesystem(source_path: Path, destination_dir: Path) -> None:
    if source_path.stat().st_dev != destination_dir.stat().st_dev:
        raise RecordingIngestionSecurityError(
            "unsafe_storage_path",
            "Atomic promotion requires quarantine, accepted, and rejected directories on the same filesystem.",
        )


def sanitize_source_filename(filename: str) -> str:
    raw_name = Path(filename).name or filename
    stem = Path(raw_name).stem
    suffix = Path(raw_name).suffix.lower()
    cleaned_stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", stem).strip().rstrip(". ")
    if not cleaned_stem:
        cleaned_stem = "recording"
    if cleaned_stem.upper() in WINDOWS_RESERVED_FILENAMES:
        cleaned_stem = f"_{cleaned_stem}"
    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        suffix = ""
    return f"{cleaned_stem}{suffix}"


def validate_recording_url(url: str, allowed_hosts: set[str]) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RecordingIngestionSecurityError("invalid_recording_url", "Recording link must use HTTPS.")
    if parsed.hostname.lower() not in allowed_hosts:
        raise RecordingIngestionSecurityError("disallowed_recording_host", f"Recording host '{parsed.hostname}' is not allowed.")


def _extension_from_response(response: httpx.Response, final_url: str) -> str:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type in CONTENT_TYPE_EXTENSIONS:
        extension = CONTENT_TYPE_EXTENSIONS[content_type]
        if extension != ".audio":
            return extension
    candidate = Path(urlparse(final_url).path).suffix.lower()
    if candidate in SUPPORTED_AUDIO_EXTENSIONS:
        return candidate
    return ".bin"


def _validate_content_type(response: httpx.Response) -> str | None:
    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower().strip()
    if content_type and not (content_type.startswith("audio/") or content_type == "application/octet-stream"):
        raise RecordingIngestionSecurityError("unsupported_content_type", f"Recording endpoint returned unsupported content type '{content_type}'.")
    return content_type or None


def _safe_streaming_response(client: httpx.Client, url: str, allowed_hosts: set[str]) -> tuple[httpx.Response, str]:
    current_url = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_recording_url(current_url, allowed_hosts)
        request = client.build_request("GET", current_url)
        response = client.send(request, stream=True, follow_redirects=False)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response, current_url

        location = response.headers.get("location")
        response.close()
        if not location:
            raise RecordingIngestionSecurityError("invalid_redirect", "Recording endpoint returned a redirect without a destination.")
        current_url = urljoin(current_url, location)

    raise RecordingIngestionSecurityError("redirect_limit_exceeded", f"Recording link exceeded the {MAX_REDIRECTS} redirect limit.")


def _sha_reference(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _filename_from_response(final_url: str, extension: str, source_reference: str) -> str:
    raw_name = Path(urlparse(final_url).path).name
    if raw_name:
        candidate = sanitize_source_filename(raw_name)
        candidate_extension = Path(candidate).suffix.lower()
        if candidate_extension in SUPPORTED_AUDIO_EXTENSIONS:
            return candidate

    safe_reference = sanitize_source_filename(source_reference)[:60]
    if not Path(safe_reference).suffix and extension in SUPPORTED_AUDIO_EXTENSIONS:
        return f"{safe_reference}{extension}"
    return f"{safe_reference or 'recording'}{extension if extension in SUPPORTED_AUDIO_EXTENSIONS else '.bin'}"


def _unique_destination(directory: Path, filename: str, source_reference: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    return directory / f"{stem}-{_sha_reference(source_reference)[:8]}{suffix}"


def stream_to_quarantine(
    client: httpx.Client,
    recording_url: str,
    source_reference: str,
    allowed_hosts: set[str],
    layout: RecordingStorageLayout,
    max_bytes: int,
) -> QuarantinedRecording:
    if get_settings().CALL_INGEST_RUNTIME_ROLE not in {"all", "downloader"}:
        raise RecordingIngestionSecurityError("runtime_role_violation", "The inspection runtime cannot download recordings.")
    # Download-only containers intentionally mount only this directory. Do not
    # require access to accepted or rejected storage at the network boundary.
    layout.quarantine_dir.mkdir(parents=True, exist_ok=True)
    response, final_url = _safe_streaming_response(client, recording_url, allowed_hosts)
    try:
        response.raise_for_status()
        content_type = _validate_content_type(response)
        extension = _extension_from_response(response, final_url)
        safe_filename = _filename_from_response(final_url, extension, source_reference)
        final_path = _unique_destination(layout.quarantine_dir, safe_filename, source_reference)
        temporary_handle = tempfile.NamedTemporaryFile(
            prefix=".ingestion-",
            suffix=".part",
            dir=layout.quarantine_dir,
            delete=False,
        )
        temporary_path = Path(temporary_handle.name)
        bytes_written = 0
        digest = hashlib.sha256()

        try:
            with temporary_handle:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise RecordingIngestionSecurityError("file_too_large", "Recording exceeds the configured maximum file size.")
                    temporary_handle.write(chunk)
                    digest.update(chunk)
            if bytes_written == 0:
                raise RecordingIngestionSecurityError("empty_recording", "Recording download was empty.")
            detect_audio_signature(temporary_path)
            os.replace(temporary_path, final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        return QuarantinedRecording(
            quarantine_path=final_path,
            safe_filename=final_path.name,
            byte_size=bytes_written,
            file_sha256=digest.hexdigest(),
            content_type=content_type,
            final_url=final_url,
        )
    finally:
        response.close()


def detect_audio_signature(path: Path) -> tuple[str, str]:
    header = _read_file_prefix(path, 64)
    lowered = header.lower()
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "wav", "audio/wav"
    if header.startswith(b"ID3") or header[:2] == b"\xff\xfb" or header[:2] == b"\xff\xf3" or header[:2] == b"\xff\xf2":
        if b"<html" in lowered or b"<!doctype" in lowered:
            raise RecordingIngestionSecurityError("unsupported_signature", "Downloaded content does not match an approved audio signature.")
        return "mp3", "audio/mpeg"
    if header.startswith(b"OggS"):
        return "ogg", "audio/ogg"
    if header.startswith(b"fLaC"):
        return "flac", "audio/flac"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "m4a", "audio/mp4"
    if header.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm", "audio/webm"
    raise RecordingIngestionSecurityError("unsupported_signature", "Downloaded content does not match an approved audio signature.")


class ClamdScannerAdapter:
    def __init__(self, endpoint: str | None = None, scanner_name: str = "clamd") -> None:
        self.endpoint = endpoint or get_settings().CALL_INGEST_SCANNER_ENDPOINT
        self.scanner_name = scanner_name

    def _connect(self, timeout_seconds: int) -> socket.socket:
        if self.endpoint.startswith("unix:"):
            address = self.endpoint.removeprefix("unix:")
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        elif self.endpoint.startswith("/"):
            address = self.endpoint
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        else:
            parsed = urlparse(self.endpoint)
            if parsed.scheme not in {"tcp", "clamd"} or not parsed.hostname:
                raise RecordingIngestionSecurityError("scanner_unavailable", "Scanner endpoint is not configured safely.")
            address = (parsed.hostname, parsed.port or 3310)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        sock.settimeout(timeout_seconds)
        sock.connect(address)
        return sock

    @staticmethod
    def _read_response(sock: socket.socket) -> str:
        payload = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            payload.extend(chunk)
            if b"\0" in chunk or b"\n" in chunk or len(payload) >= 16 * 1024:
                break
        return bytes(payload).split(b"\0", 1)[0].decode("utf-8", errors="replace").strip()

    def _get_version(self, timeout_seconds: int) -> str | None:
        try:
            with self._connect(timeout_seconds) as sock:
                sock.sendall(b"zVERSION\0")
                response = self._read_response(sock)
        except Exception:
            return None
        return response or None

    def _instream_scan(self, path: Path, timeout_seconds: int) -> str:
        with self._connect(timeout_seconds) as sock:
            sock.sendall(b"zINSTREAM\0")
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(CLAMD_STREAM_CHUNK_SIZE), b""):
                    sock.sendall(struct.pack(">I", len(chunk)))
                    sock.sendall(chunk)
            sock.sendall(struct.pack(">I", 0))
            return self._read_response(sock)

    @staticmethod
    def _normalize_scan_result(response: str) -> tuple[RecordingIngestionInspectionStatus, str | None, str | None]:
        normalized = response.upper()
        if " OK" in normalized or normalized.endswith("OK"):
            return RecordingIngestionInspectionStatus.PASSED, None, None
        if "FOUND" in normalized:
            return RecordingIngestionInspectionStatus.REJECTED, "malware_detected", "Malware scanner rejected the recording."
        return RecordingIngestionInspectionStatus.UNAVAILABLE, "scanner_unavailable", "Malware scanner returned an unexpected result."

    def scan(self, path: Path, timeout_seconds: int) -> MalwareScanResult:
        version = self._get_version(timeout_seconds)
        try:
            response = self._instream_scan(path, timeout_seconds)
        except socket.timeout:
            return MalwareScanResult(
                status=RecordingIngestionInspectionStatus.UNAVAILABLE,
                scanner_name=self.scanner_name,
                scanner_version=version,
                error_category="scanner_timeout",
                error_detail="Malware scanner timed out.",
            )
        except RecordingIngestionSecurityError as exc:
            return MalwareScanResult(
                status=RecordingIngestionInspectionStatus.UNAVAILABLE,
                scanner_name=self.scanner_name,
                scanner_version=version,
                error_category=exc.category,
                error_detail=exc.detail,
            )
        except Exception:
            return MalwareScanResult(
                status=RecordingIngestionInspectionStatus.UNAVAILABLE,
                scanner_name=self.scanner_name,
                scanner_version=version,
                error_category="scanner_unavailable",
                error_detail="Malware scanner is unavailable.",
            )

        status, error_category, error_detail = self._normalize_scan_result(response)
        return MalwareScanResult(
            status=status,
            scanner_name=self.scanner_name,
            scanner_version=version,
            error_category=error_category,
            error_detail=error_detail,
        )


def _ffprobe_preexec(timeout_seconds: int):
    try:
        import resource
    except ImportError:  # pragma: no cover - unavailable on some development hosts
        return None

    def _apply_limits():
        os.setsid()
        cpu_limit = max(1, int(timeout_seconds))
        memory_limit_bytes = 256 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
        resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, memory_limit_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (MEDIA_VERIFIER_MAX_OUTPUT_BYTES, MEDIA_VERIFIER_MAX_OUTPUT_BYTES))
        resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

    return _apply_limits


def _build_ffprobe_command(path: Path) -> list[str] | None:
    ffprobe_path = shutil.which("ffprobe")
    if not ffprobe_path:
        return None
    return [
        ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, 9)
        else:  # pragma: no cover - verifier runs in the Linux guest
            process.kill()
    except ProcessLookupError:
        pass


def _run_bounded_command(command: list[str], timeout_seconds: int) -> tuple[int | None, bytes, bool, bool]:
    """Run one parser with a wall-clock timeout and a hard combined output cap."""
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=_ffprobe_preexec(timeout_seconds),
    )
    # Bound the reader backlog as well as the retained output. Otherwise a
    # hostile parser could outpace the parent and turn the queue into memory
    # growth before the byte cap is observed.
    output_queue: Queue[bytes | None] = Queue(maxsize=32)

    def _drain(stream) -> None:
        try:
            while chunk := stream.read(8192):
                output_queue.put(chunk)
        finally:
            output_queue.put(None)

    threads = [threading.Thread(target=_drain, args=(stream,), daemon=True) for stream in (process.stdout, process.stderr)]
    for thread in threads:
        thread.start()

    output = bytearray()
    completed_streams = 0
    deadline = time.monotonic() + timeout_seconds
    timed_out = False
    too_much_output = False
    while completed_streams < len(threads):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            _terminate_process(process)
            break
        try:
            chunk = output_queue.get(timeout=remaining)
        except Empty:
            timed_out = True
            _terminate_process(process)
            break
        if chunk is None:
            completed_streams += 1
            continue
        output.extend(chunk)
        if len(output) > MEDIA_VERIFIER_MAX_OUTPUT_BYTES:
            too_much_output = True
            _terminate_process(process)
            break

    try:
        return_code = process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        _terminate_process(process)
        return_code = process.wait(timeout=1)
    return return_code, bytes(output[:MEDIA_VERIFIER_MAX_OUTPUT_BYTES]), timed_out, too_much_output


class FfprobeMediaVerifier:
    """Local verifier for the dedicated no-network media-verifier container."""

    def verify(self, path: Path, timeout_seconds: int) -> MediaVerificationResult:
        command = _build_ffprobe_command(path)
        if not command:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_unavailable",
                error_detail="Media verification sandbox is unavailable.",
            )

        try:
            return_code, stdout, timed_out, too_much_output = _run_bounded_command(command, timeout_seconds)
        except Exception:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_unavailable",
                error_detail="Media verification sandbox could not be executed.",
            )

        if timed_out:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_timeout",
                error_detail="Media verification timed out.",
            )
        if too_much_output:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification produced too much output.",
            )
        if return_code != 0:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification rejected the recording.",
            )

        try:
            payload = json.loads(stdout.decode("utf-8", errors="replace") or "{}")
        except json.JSONDecodeError:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification produced invalid output.",
            )

        streams = payload.get("streams") or []
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
        if not audio_stream:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification found no approved audio stream.",
            )

        duration_value = audio_stream.get("duration") or (payload.get("format") or {}).get("duration")
        try:
            duration_seconds = float(duration_value)
        except (TypeError, ValueError):
            duration_seconds = 0.0
        if duration_seconds <= 0:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification found zero duration audio.",
            )

        return MediaVerificationResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            duration_seconds=duration_seconds,
        )


class RemoteMediaVerifier:
    """Ask the dedicated no-network verifier to inspect a quarantined filename."""

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = (endpoint or get_settings().CALL_INGEST_MEDIA_VERIFIER_ENDPOINT).rstrip("/")

    def verify(self, path: Path, timeout_seconds: int) -> MediaVerificationResult:
        if path.name != str(path) or path.name in {"", ".", ".."}:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_unavailable",
                error_detail="Media verification received an unsafe filename.",
            )
        try:
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(f"{self.endpoint}/verify", json={"filename": path.name})
            response.raise_for_status()
            payload = response.json()
            status = RecordingIngestionInspectionStatus(payload["status"])
            duration = payload.get("duration_seconds")
            error_category = payload.get("error_category")
            if error_category not in REMOTE_MEDIA_VERIFIER_ERROR_CATEGORIES:
                error_category = "media_verification_failed"
            return MediaVerificationResult(
                status=status,
                duration_seconds=float(duration) if duration is not None else None,
                error_category=error_category,
                error_detail=payload.get("error_detail"),
            )
        except Exception:
            return MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_unavailable",
                error_detail="Media verification service is unavailable.",
            )


def create_ingestion_attempt(
    db: Session,
    record: RecordingIngestionRecord,
    run: RecordingIngestionRun,
    phase: RecordingIngestionAttemptPhase,
) -> RecordingIngestionAttempt:
    attempt_number = max(record.attempt_count, 1)
    attempt = RecordingIngestionAttempt(
        ingestion_record_id=record.id,
        ingestion_run_id=run.id,
        attempt_number=attempt_number,
        phase=phase,
        status=RecordingIngestionAttemptStatus.STARTED,
        started_at=utcnow(),
    )
    db.add(attempt)
    db.flush()
    return attempt


def _finalize_attempt(
    attempt: RecordingIngestionAttempt,
    status: RecordingIngestionAttemptStatus,
    *,
    error_category: str | None = None,
    error_detail: str | None = None,
) -> None:
    attempt.status = status
    attempt.error_category = error_category
    attempt.error_detail = error_detail
    attempt.completed_at = utcnow()


def _move_within_layout(source_path: Path, destination_dir: Path, source_reference: str) -> Path:
    _ensure_same_filesystem(source_path, destination_dir)
    destination = _unique_destination(destination_dir, sanitize_source_filename(source_path.name), source_reference)
    os.replace(source_path, destination)
    return destination


def reject_recording(
    db: Session,
    *,
    record: RecordingIngestionRecord,
    layout: RecordingStorageLayout,
    source_reference: str,
    category: str,
    detail: str,
) -> None:
    quarantine_path = Path(record.quarantine_file_path) if record.quarantine_file_path else None
    if quarantine_path:
        try:
            quarantine_path = _resolve_existing_path_within(
                layout.quarantine_dir,
                quarantine_path,
                field_name="quarantine_file_path",
            )
        except RecordingIngestionSecurityError:
            quarantine_path = None
    if quarantine_path and quarantine_path.exists():
        rejected_path = _move_within_layout(quarantine_path, layout.rejected_dir, source_reference)
        record.quarantine_file_path = str(rejected_path)
    record.status = RecordingIngestionRecordStatus.REJECTED
    record.next_retry_at = None
    record.last_error_category = category
    record.last_error_detail = detail
    record.completed_at = utcnow()
    record.inspection_completed_at = utcnow()
    add_recording_ingestion_audit_event(
        db,
        action=INGESTION_AUDIT_REJECTED,
        target=f"RecordingIngestionRecord #{record.id}",
        after_state={
            "run_id": record.ingestion_run_id,
            "record_id": record.id,
            "status": record.status,
            "error_category": category,
            "inspection_completed_at": record.inspection_completed_at,
        },
        reason=detail,
        success=False,
    )


def inspect_quarantined_recording(
    db: Session,
    record: RecordingIngestionRecord,
    run: RecordingIngestionRun,
    *,
    layout: RecordingStorageLayout,
    scanner: MalwareScanner | None = None,
    media_verifier: MediaVerifier | None = None,
) -> RecordingIngestionRecord:
    if get_settings().CALL_INGEST_RUNTIME_ROLE not in {"all", "inspector"}:
        raise RecordingIngestionSecurityError("runtime_role_violation", "The download runtime cannot inspect or promote recordings.")
    # Promotion containers deliberately do not mount the state directory.
    # Preparing only their three data paths preserves that mount boundary.
    for directory in (layout.quarantine_dir, layout.accepted_dir, layout.rejected_dir):
        directory.mkdir(parents=True, exist_ok=True)
    if not record.quarantine_file_path:
        raise RecordingIngestionSecurityError("missing_quarantine_file", "No quarantine file is available for inspection.")

    source_reference = record.source_key or f"record-{record.id}"
    try:
        quarantine_path = _resolve_existing_path_within(
            layout.quarantine_dir,
            Path(record.quarantine_file_path),
            field_name="quarantine_file_path",
        )
    except RecordingIngestionSecurityError as exc:
        record.status = RecordingIngestionRecordStatus.REJECTED
        record.next_retry_at = None
        record.last_error_category = exc.category
        record.last_error_detail = exc.detail
        record.completed_at = utcnow()
        record.inspection_completed_at = utcnow()
        add_recording_ingestion_audit_event(
            db,
            action=INGESTION_AUDIT_REJECTED,
            target=f"RecordingIngestionRecord #{record.id}",
            after_state={
                "run_id": record.ingestion_run_id,
                "record_id": record.id,
                "status": record.status,
                "error_category": exc.category,
                "inspection_completed_at": record.inspection_completed_at,
            },
            reason=exc.detail,
            success=False,
        )
        db.flush()
        return record

    scanner = scanner or ClamdScannerAdapter()
    media_verifier = media_verifier or RemoteMediaVerifier()
    inspection_timeout = get_settings().CALL_INGEST_INSPECTION_TIMEOUT_SECONDS
    media_timeout = get_settings().CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS

    record.status = RecordingIngestionRecordStatus.INSPECTING
    record.next_retry_at = None
    db.flush()

    signature_attempt = create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.SIGNATURE_CHECK)
    try:
        _, detected_content_type = detect_audio_signature(quarantine_path)
        record.signature_status = RecordingIngestionInspectionStatus.PASSED
        if not record.content_type:
            record.content_type = detected_content_type
        _finalize_attempt(signature_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)
    except RecordingIngestionSecurityError as exc:
        record.signature_status = RecordingIngestionInspectionStatus.REJECTED
        _finalize_attempt(signature_attempt, RecordingIngestionAttemptStatus.FAILED, error_category=exc.category, error_detail=exc.detail)
        reject_recording(db, record=record, layout=layout, source_reference=source_reference, category=exc.category, detail=exc.detail)
        db.flush()
        return record

    scan_attempt = create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.MALWARE_SCAN)
    scan_result = scanner.scan(quarantine_path, inspection_timeout)
    record.scanner_name = scan_result.scanner_name
    record.scanner_version = scan_result.scanner_version
    record.malware_scan_status = scan_result.status
    if scan_result.status != RecordingIngestionInspectionStatus.PASSED:
        _finalize_attempt(
            scan_attempt,
            RecordingIngestionAttemptStatus.FAILED,
            error_category=scan_result.error_category,
            error_detail=scan_result.error_detail,
        )
        reject_recording(
            db,
            record=record,
            layout=layout,
            source_reference=source_reference,
            category=scan_result.error_category or "scanner_rejected",
            detail=scan_result.error_detail or "Malware scanner rejected the recording.",
        )
        db.flush()
        return record
    _finalize_attempt(scan_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)

    media_attempt = create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.MEDIA_VERIFICATION)
    media_result = media_verifier.verify(quarantine_path, media_timeout)
    record.media_verification_status = media_result.status
    if media_result.status != RecordingIngestionInspectionStatus.PASSED:
        _finalize_attempt(
            media_attempt,
            RecordingIngestionAttemptStatus.FAILED,
            error_category=media_result.error_category,
            error_detail=media_result.error_detail,
        )
        reject_recording(
            db,
            record=record,
            layout=layout,
            source_reference=source_reference,
            category=media_result.error_category or "media_verification_failed",
            detail=media_result.error_detail or "Media verification rejected the recording.",
        )
        db.flush()
        return record
    _finalize_attempt(media_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)

    storage_attempt = create_ingestion_attempt(db, record, run, RecordingIngestionAttemptPhase.STORAGE)
    try:
        accepted_path = _move_within_layout(quarantine_path, layout.accepted_dir, source_reference)
    except Exception:
        _apply_failure_policy(
            record,
            category="storage_failed",
            detail="Recording could not be promoted into accepted storage.",
            attempt=storage_attempt,
        )
        db.flush()
        return record
    record.status = RecordingIngestionRecordStatus.ACCEPTED
    record.stored_file_path = str(accepted_path)
    record.quarantine_file_path = None
    record.byte_size = accepted_path.stat().st_size
    if not record.file_sha256:
        record.file_sha256 = _stream_sha256(accepted_path)
    record.inspection_completed_at = utcnow()
    record.completed_at = utcnow()
    record.last_error_category = None
    record.last_error_detail = None
    _finalize_attempt(storage_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)
    add_recording_ingestion_audit_event(
        db,
        action=INGESTION_AUDIT_ACCEPTED,
        target=f"RecordingIngestionRecord #{record.id}",
        after_state={
            "run_id": run.id,
            "record_id": record.id,
            "status": record.status,
            "file_sha256": record.file_sha256,
            "byte_size": record.byte_size,
            "content_type": record.content_type,
            "inspection_completed_at": record.inspection_completed_at,
        },
        success=True,
    )
    db.flush()
    return record


def _mark_record_failed(
    record: RecordingIngestionRecord,
    *,
    category: str,
    detail: str,
) -> None:
    record.status = RecordingIngestionRecordStatus.FAILED
    record.next_retry_at = None
    record.last_error_category = category
    record.last_error_detail = _sanitize_ingestion_text(detail)
    record.completed_at = utcnow()


def _continue_claimed_record_processing(
    *,
    worker_db: Session,
    run: RecordingIngestionRun,
    record: RecordingIngestionRecord,
    row_number: int,
    source_reference: str,
    client_factory,
    layout: RecordingStorageLayout,
    allowed_hosts: set[str],
    max_bytes: int,
    scanner_factory,
    media_verifier_factory,
    inspection_queue: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> IngestionRowOutcome:
    if record.status in {
        RecordingIngestionRecordStatus.DOWNLOADING,
        RecordingIngestionRecordStatus.PENDING,
    }:
        download_attempt = create_ingestion_attempt(worker_db, record, run, RecordingIngestionAttemptPhase.DOWNLOAD)
        client = None
        try:
            client = client_factory()
            quarantined = stream_to_quarantine(
                client,
                record.recording_url,
                source_reference=source_reference,
                allowed_hosts=allowed_hosts,
                layout=layout,
                max_bytes=max_bytes,
            )
            record.status = RecordingIngestionRecordStatus.QUARANTINED
            record.quarantine_file_path = str(quarantined.quarantine_path)
            record.content_type = quarantined.content_type
            record.byte_size = quarantined.byte_size
            record.file_sha256 = quarantined.file_sha256
            record.next_retry_at = None
            record.last_error_category = None
            record.last_error_detail = None
            _finalize_attempt(download_attempt, RecordingIngestionAttemptStatus.SUCCEEDED)
        except Exception as exc:
            category, detail, http_status = _classify_download_exception(exc)
            download_attempt.http_status = http_status
            delay_seconds = _apply_failure_policy(
                record,
                category=category,
                detail=detail,
                attempt=download_attempt,
            )
            worker_db.commit()
            _queue_retry_if_needed(retry_queue, record_id=record.id, delay_seconds=delay_seconds)
            return _record_row_failure(
                row_number=row_number,
                source_reference=source_reference,
                category=category,
                detail=detail,
                record=record,
                created=True,
                retryable=delay_seconds is not None,
            )
        finally:
            if client is not None and hasattr(client, "close"):
                client.close()

        worker_db.commit()

    if record.status == RecordingIngestionRecordStatus.QUARANTINED and inspection_queue is not None:
        try:
            inspection_queue(record.id)
        except Exception:
            delay_seconds = _apply_failure_policy(
                record,
                category="inspection_queue_failed",
                detail="Recording inspection could not be queued.",
            )
            worker_db.commit()
            _queue_retry_if_needed(retry_queue, record_id=record.id, delay_seconds=delay_seconds)
            return _record_row_failure(
                row_number=row_number,
                source_reference=source_reference,
                category="inspection_queue_failed",
                detail="Recording inspection could not be queued.",
                record=record,
                created=True,
                retryable=delay_seconds is not None,
            )
        return _record_row_success(
            row_number=row_number,
            source_reference=source_reference,
            outcome=RecordingIngestionRecordStatus.QUARANTINED.value,
            record=record,
            created=True,
        )

    if record.status == RecordingIngestionRecordStatus.QUARANTINED:
        try:
            inspect_quarantined_recording(
                worker_db,
                record,
                run,
                layout=layout,
                scanner=scanner_factory(),
                media_verifier=media_verifier_factory(),
            )
        except Exception as exc:
            category = exc.category if isinstance(exc, RecordingIngestionSecurityError) else "inspection_failed"
            detail = exc.detail if isinstance(exc, RecordingIngestionSecurityError) else "Recording inspection failed."
            _mark_record_failed(record, category=category, detail=detail)
            worker_db.commit()
            return _record_row_failure(
                row_number=row_number,
                source_reference=source_reference,
                category=category,
                detail=detail,
                record=record,
                created=True,
            )

        worker_db.commit()
        if record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED:
            delay_seconds = None
            retry_at = _coerce_utc_datetime(record.next_retry_at)
            if retry_at is not None:
                delay_seconds = max(int((retry_at - utcnow()).total_seconds()), 0)
            _queue_retry_if_needed(retry_queue, record_id=record.id, delay_seconds=delay_seconds)
            return _record_row_failure(
                row_number=row_number,
                source_reference=source_reference,
                category=record.last_error_category or "storage_failed",
                detail=record.last_error_detail or "Recording inspection failed.",
                record=record,
                created=True,
                retryable=True,
            )

    if record.status == RecordingIngestionRecordStatus.ACCEPTED:
        handoff_accepted_recording(
            worker_db,
            record,
            run=run,
            retry_queue=retry_queue,
        )
        if record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED:
            delay_seconds = None
            retry_at = _coerce_utc_datetime(record.next_retry_at)
            if retry_at is not None:
                delay_seconds = max(int((retry_at - utcnow()).total_seconds()), 0)
            return _record_row_failure(
                row_number=row_number,
                source_reference=source_reference,
                category=record.last_error_category or "handoff_queue_failed",
                detail=record.last_error_detail or "Call handoff was not queued.",
                record=record,
                created=True,
                retryable=delay_seconds is not None,
            )
        if record.status == RecordingIngestionRecordStatus.SUBMITTED:
            return _record_row_success(
                row_number=row_number,
                source_reference=source_reference,
                outcome=record.status.value,
                record=record,
                created=True,
            )

    if record.status == RecordingIngestionRecordStatus.REJECTED:
        return _record_row_failure(
            row_number=row_number,
            source_reference=source_reference,
            category=record.last_error_category or "rejected",
            detail=record.last_error_detail or "Recording rejected during inspection.",
            record=record,
            created=True,
        )

    if record.status == RecordingIngestionRecordStatus.SUBMITTED:
        return _record_row_success(
            row_number=row_number,
            source_reference=source_reference,
            outcome=record.status.value,
            record=record,
            created=True,
        )

    return _record_row_failure(
        row_number=row_number,
        source_reference=source_reference,
        category=record.last_error_category or "record_processing_failed",
        detail=record.last_error_detail or "Recording could not be processed.",
        record=record,
        created=True,
        retryable=record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED,
    )


def inspect_and_handoff_record(
    db: Session,
    *,
    record_id: int,
    queue_task: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
    layout: RecordingStorageLayout | None = None,
    scanner_factory=None,
    media_verifier_factory=None,
) -> RecordingIngestionRecord | None:
    """Run the promotion boundary for one committed quarantine record."""
    record = db.get(RecordingIngestionRecord, record_id)
    if record is None or record.status != RecordingIngestionRecordStatus.QUARANTINED:
        return record

    run = db.get(RecordingIngestionRun, record.ingestion_run_id)
    if run is None:
        _mark_record_failed(record, category="missing_run", detail="The ingestion run no longer exists.")
        db.commit()
        return record

    try:
        layout = layout or _build_ingestion_storage_layout()
        scanner = (scanner_factory or ClamdScannerAdapter)()
        media_verifier = (media_verifier_factory or RemoteMediaVerifier)()
        inspect_quarantined_recording(
            db,
            record,
            run,
            layout=layout,
            scanner=scanner,
            media_verifier=media_verifier,
        )
    except Exception:
        _mark_record_failed(record, category="inspection_failed", detail="Recording inspection failed.")
        db.commit()
        return record

    if record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED and record.next_retry_at is not None:
        db.commit()
        retry_at = _coerce_utc_datetime(record.next_retry_at)
        delay_seconds = max(int((retry_at - utcnow()).total_seconds()), 0) if retry_at is not None else None
        _queue_retry_if_needed(retry_queue, record_id=record.id, delay_seconds=delay_seconds)
    elif record.status == RecordingIngestionRecordStatus.ACCEPTED:
        handoff_accepted_recording(db, record, run=run, queue_task=queue_task, retry_queue=retry_queue)
    else:
        db.commit()
    return record


def _set_run_summary(run: RecordingIngestionRun) -> None:
    run.failure_summary = "; ".join(
        (
            f"rows_seen={run.rows_seen}",
            f"new={run.new_count}",
            f"duplicate={run.duplicate_count}",
            f"success={run.success_count}",
            f"failed={run.failed_count}",
            f"retryable={run.retryable_count}",
        )
    )


def finalize_ingestion_run_if_ready(db: Session, run: RecordingIngestionRun) -> RecordingIngestionRun:
    """Close an asynchronously inspected run only after every new record is terminal."""
    if run.completed_at is not None:
        return run

    active_statuses = {
        RecordingIngestionRecordStatus.PENDING,
        RecordingIngestionRecordStatus.DOWNLOADING,
        RecordingIngestionRecordStatus.QUARANTINED,
        RecordingIngestionRecordStatus.INSPECTING,
        RecordingIngestionRecordStatus.ACCEPTED,
        RecordingIngestionRecordStatus.HANDOFF_PENDING,
    }
    active_count = (
        db.query(func.count(RecordingIngestionRecord.id))
        .filter(
            RecordingIngestionRecord.ingestion_run_id == run.id,
            RecordingIngestionRecord.status.in_(active_statuses),
        )
        .scalar()
    )
    if active_count:
        run.status = RecordingIngestionRunStatus.PROCESSING
        db.flush()
        return run

    source_row_failures = run.failed_count
    status_counts = dict(
        db.query(RecordingIngestionRecord.status, func.count(RecordingIngestionRecord.id))
        .filter(RecordingIngestionRecord.ingestion_run_id == run.id)
        .group_by(RecordingIngestionRecord.status)
        .all()
    )
    run.success_count = status_counts.get(RecordingIngestionRecordStatus.SUBMITTED, 0)
    run.retryable_count = status_counts.get(RecordingIngestionRecordStatus.RETRY_SCHEDULED, 0)
    run.failed_count = source_row_failures + sum(
        status_counts.get(status, 0)
        for status in {RecordingIngestionRecordStatus.FAILED, RecordingIngestionRecordStatus.REJECTED}
    )
    run.status = (
        RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS
        if run.failed_count or run.retryable_count
        else RecordingIngestionRunStatus.COMPLETED
    )
    run.completed_at = utcnow()
    _set_run_summary(run)
    db.flush()
    return run


def _process_ingestion_row(
    *,
    run_id: int,
    source_name: str,
    row: SourceSheetRow,
    session_factory,
    client_factory,
    layout: RecordingStorageLayout,
    allowed_hosts: set[str],
    max_bytes: int,
    scanner_factory,
    media_verifier_factory,
    inspection_queue: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> IngestionRowOutcome:
    source_reference = f"row-{row.row_number}"
    record: RecordingIngestionRecord | None = None
    with session_factory() as worker_db:
        run = worker_db.get(RecordingIngestionRun, run_id)
        if run is None:
            return _record_row_failure(
                row_number=row.row_number,
                source_reference=source_reference,
                category="missing_run",
                detail="The ingestion run no longer exists.",
            )

        try:
            mapping = map_source_row(db=worker_db, row=row, row_number=row.row_number, source_name=source_name)
            source_reference = mapping.source_key
            claim = claim_source_record(worker_db, run=run, mapping=mapping)
            record = claim.record
        except RecordingIngestionSecurityError as exc:
            worker_db.flush()
            worker_db.commit()
            return _record_row_failure(
                row_number=row.row_number,
                source_reference=source_reference,
                category=exc.category,
                detail=exc.detail,
            )

        if not claim.created:
            worker_db.flush()
            worker_db.commit()
            return _record_row_success(
                row_number=row.row_number,
                source_reference=source_reference,
                outcome=_classify_claim_outcome(claim),
                record=record,
                created=False,
            )
        return _continue_claimed_record_processing(
            worker_db=worker_db,
            run=run,
            record=record,
            row_number=row.row_number,
            source_reference=source_reference,
            client_factory=client_factory,
            layout=layout,
            allowed_hosts=allowed_hosts,
            max_bytes=max_bytes,
            scanner_factory=scanner_factory,
            media_verifier_factory=media_verifier_factory,
            inspection_queue=inspection_queue,
            retry_queue=retry_queue,
        )


def _apply_ingestion_results(
    db: Session,
    run: RecordingIngestionRun,
    results: list[IngestionRowOutcome],
    *,
    rows_seen: int,
    defer_completion: bool = False,
) -> RecordingIngestionRun:
    new_count = sum(1 for result in results if result.created)
    duplicate_count = sum(1 for result in results if result.outcome in {"duplicate", "requires_review"})
    success_count = sum(1 for result in results if result.outcome in {"accepted", "submitted"})
    failed_count = sum(1 for result in results if result.outcome in {"failed", "rejected"})
    retryable_count = sum(1 for result in results if result.outcome == "retryable" or result.retryable)

    run.rows_seen = rows_seen
    run.new_count = new_count
    run.duplicate_count = duplicate_count
    run.success_count = success_count
    run.failed_count = sum(
        1
        for result in results
        if result.record_id is None and result.outcome in {"failed", "rejected"}
    ) if defer_completion else failed_count
    run.retryable_count = retryable_count

    _set_run_summary(run)

    if defer_completion:
        return finalize_ingestion_run_if_ready(db, run)

    if failed_count or retryable_count:
        run.status = RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS
    else:
        run.status = RecordingIngestionRunStatus.COMPLETED
    run.completed_at = utcnow()
    db.flush()
    return run


def run_recording_ingestion(
    db: Session,
    *,
    source_name: str = "vicdi_tests",
    trigger: RecordingIngestionRunTrigger = RecordingIngestionRunTrigger.SCHEDULED,
    requested_by_employee_id: int | None = None,
    sheet_service: Any | None = None,
    session_factory=SessionLocal,
    client_factory=None,
    scanner_factory=None,
    media_verifier_factory=None,
    layout: RecordingStorageLayout | None = None,
    max_workers: int | None = None,
    inspection_queue: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> RecordingIngestionRun:
    run = create_ingestion_run(
        db,
        source_name=source_name,
        trigger=trigger,
        requested_by_employee_id=requested_by_employee_id,
    )
    db.commit()
    return continue_ingestion_run(
        db,
        run_id=run.id,
        session_factory=session_factory,
        sheet_service=sheet_service,
        client_factory=client_factory,
        scanner_factory=scanner_factory,
        media_verifier_factory=media_verifier_factory,
        layout=layout,
        max_workers=max_workers,
        inspection_queue=inspection_queue,
        retry_queue=retry_queue,
    )


def continue_ingestion_run(
    db: Session,
    *,
    run_id: int,
    session_factory=SessionLocal,
    sheet_service: Any | None = None,
    client_factory=None,
    scanner_factory=None,
    media_verifier_factory=None,
    layout: RecordingStorageLayout | None = None,
    max_workers: int | None = None,
    inspection_queue: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> RecordingIngestionRun:
    run = db.get(RecordingIngestionRun, run_id)
    if run is None:
        raise RecordingIngestionSecurityError("missing_run", "The ingestion run does not exist.")
    if run.status != RecordingIngestionRunStatus.REQUESTED:
        raise RecordingIngestionSecurityError(
            "run_not_requestable",
            "Only requested ingestion runs can be started.",
        )

    settings = get_settings()
    layout = layout or _build_ingestion_storage_layout()
    allowed_hosts = _build_ingestion_allowed_hosts()
    if not allowed_hosts:
        raise RecordingIngestionSecurityError("missing_host_allowlist", "At least one allowed recording host is required.")

    if client_factory is None:
        request_timeout = httpx.Timeout(settings.CALL_INGEST_REQUEST_TIMEOUT_SECONDS)

        def client_factory() -> httpx.Client:  # type: ignore[no-redef]
            return httpx.Client(timeout=request_timeout)

    if scanner_factory is None:
        scanner_factory = ClamdScannerAdapter
    if media_verifier_factory is None:
        media_verifier_factory = RemoteMediaVerifier

    run.started_at = utcnow()
    run.status = RecordingIngestionRunStatus.READING_SOURCE
    db.commit()

    try:
        sheet_service = sheet_service or _build_google_sheets_service()
        read_result = read_source_sheet_rows(
            service=sheet_service,
            spreadsheet_id=settings.CALL_INGEST_GOOGLE_SHEET_ID,
            worksheet_name=settings.CALL_INGEST_WORKSHEET,
            cell_range=settings.CALL_INGEST_RANGE,
        )
    except Exception as exc:
        run.status = RecordingIngestionRunStatus.FAILED
        run.completed_at = utcnow()
        run.failure_summary = _sanitize_ingestion_text(str(exc)) or "Source sheet read failed."
        db.commit()
        return run

    rows_seen = len(read_result.rows) + len(read_result.errors)
    run.rows_seen = rows_seen
    run.status = RecordingIngestionRunStatus.PROCESSING
    db.commit()

    outcomes: list[IngestionRowOutcome] = [
        _record_row_failure(
            row_number=error.row_number or 0,
            source_reference=f"row-{error.row_number}" if error.row_number is not None else "header",
            category=error.category,
            detail=error.detail,
        )
        for error in read_result.errors
    ]

    if read_result.rows:
        worker_count = max(1, min(max_workers or settings.CALL_INGEST_DOWNLOAD_CONCURRENCY, len(read_result.rows)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(
                    _process_ingestion_row,
                    run_id=run.id,
                    source_name=run.source_name,
                    row=row,
                    session_factory=session_factory,
                    client_factory=client_factory,
                    layout=layout,
                    allowed_hosts=allowed_hosts,
                    max_bytes=settings.max_file_size_bytes,
                    scanner_factory=scanner_factory,
                    media_verifier_factory=media_verifier_factory,
                    inspection_queue=inspection_queue,
                    retry_queue=retry_queue,
                ): row
                for row in read_result.rows
            }
            for future in as_completed(future_map):
                row = future_map[future]
                try:
                    outcomes.append(future.result())
                except Exception:
                    outcomes.append(
                        _record_row_failure(
                            row_number=row.row_number,
                            source_reference=f"row-{row.row_number}",
                            category="row_processing_failed",
                            detail="Recording row processing failed.",
                        )
                    )

    run = _apply_ingestion_results(
        db,
        run,
        outcomes,
        rows_seen=rows_seen,
        defer_completion=inspection_queue is not None,
    )
    db.commit()
    db.refresh(run)
    return run


def _prepare_record_for_retry(
    record: RecordingIngestionRecord,
    *,
    run: RecordingIngestionRun,
) -> None:
    record.ingestion_run_id = run.id
    record.attempt_count = max(record.attempt_count, 0) + 1
    record.next_retry_at = None
    record.last_error_category = None
    record.last_error_detail = None
    record.completed_at = None

    if record.call_id is not None and record.stored_file_path and record.pipeline_queued_at is None:
        record.status = RecordingIngestionRecordStatus.ACCEPTED
        return

    if record.quarantine_file_path:
        record.status = RecordingIngestionRecordStatus.QUARANTINED
        record.signature_status = RecordingIngestionInspectionStatus.PENDING
        record.malware_scan_status = RecordingIngestionInspectionStatus.PENDING
        record.media_verification_status = RecordingIngestionInspectionStatus.PENDING
        record.scanner_name = None
        record.scanner_version = None
        record.inspection_completed_at = None
        return

    record.status = RecordingIngestionRecordStatus.DOWNLOADING
    record.quarantine_file_path = None
    record.stored_file_path = None
    record.pipeline_queued_at = None
    record.content_type = None
    record.byte_size = None
    record.file_sha256 = None
    record.signature_status = RecordingIngestionInspectionStatus.PENDING
    record.malware_scan_status = RecordingIngestionInspectionStatus.PENDING
    record.media_verification_status = RecordingIngestionInspectionStatus.PENDING
    record.scanner_name = None
    record.scanner_version = None
    record.inspection_completed_at = None


def _validate_record_retry_eligibility(
    record: RecordingIngestionRecord,
    *,
    manual: bool,
) -> None:
    category = record.last_error_category or ""
    if record.status == RecordingIngestionRecordStatus.SUBMITTED:
        raise RecordingIngestionSecurityError("record_not_retryable", "Submitted records are not eligible for retry.")
    if record.status == RecordingIngestionRecordStatus.REJECTED:
        raise RecordingIngestionSecurityError("record_not_retryable", "Rejected inspection results are not eligible for retry.")
    if manual:
        if record.status not in MANUAL_RETRYABLE_STATUSES:
            raise RecordingIngestionSecurityError(
                "record_not_retryable",
                "Only failed, scheduled retry, or review-required records are eligible for manual retry.",
            )
        if record.status == RecordingIngestionRecordStatus.FAILED and category not in MANUAL_RETRYABLE_CATEGORIES:
            raise RecordingIngestionSecurityError("record_not_retryable", "This failure requires review before another retry.")
        return

    if record.status != RecordingIngestionRecordStatus.RETRY_SCHEDULED:
        raise RecordingIngestionSecurityError("retry_not_due", "Automatic retry is only allowed for scheduled retry records.")
    next_retry_at = _coerce_utc_datetime(record.next_retry_at)
    if next_retry_at is not None and next_retry_at > utcnow():
        raise RecordingIngestionSecurityError("retry_not_due", "The record is not due for retry yet.")


def _handoff_reconciliation_claim_filter(*, claim_cutoff: datetime):
    return or_(
        RecordingIngestionRecord.last_error_category.is_(None),
        RecordingIngestionRecord.last_error_category != HANDOFF_RECONCILIATION_CLAIM_CATEGORY,
        RecordingIngestionRecord.updated_at <= claim_cutoff,
    )


def retry_ingestion_record(
    db: Session,
    *,
    record_id: int,
    requested_by_employee_id: int | None = None,
    manual: bool = False,
    client_factory=None,
    scanner_factory=None,
    media_verifier_factory=None,
    layout: RecordingStorageLayout | None = None,
    inspection_queue: Callable[[int], Any] | None = None,
    retry_queue: Callable[[int, int], Any] | None = None,
) -> RecordingIngestionRecord:
    record = prepare_ingestion_record_retry(
        db,
        record_id=record_id,
        requested_by_employee_id=requested_by_employee_id,
        manual=manual,
    )

    settings = get_settings()
    layout = layout or _build_ingestion_storage_layout()
    allowed_hosts = _build_ingestion_allowed_hosts()
    if not allowed_hosts:
        raise RecordingIngestionSecurityError("missing_host_allowlist", "At least one allowed recording host is required.")

    if client_factory is None:
        request_timeout = httpx.Timeout(settings.CALL_INGEST_REQUEST_TIMEOUT_SECONDS)

        def client_factory() -> httpx.Client:  # type: ignore[no-redef]
            return httpx.Client(timeout=request_timeout)

    if scanner_factory is None:
        scanner_factory = ClamdScannerAdapter
    if media_verifier_factory is None:
        media_verifier_factory = RemoteMediaVerifier

    run = create_ingestion_run(
        db,
        source_name=record.source_name,
        trigger=RecordingIngestionRunTrigger.RETRY,
        requested_by_employee_id=requested_by_employee_id,
    )
    run.started_at = utcnow()
    run.status = RecordingIngestionRunStatus.PROCESSING
    _prepare_record_for_retry(record, run=run)
    db.commit()
    db.refresh(run)
    db.refresh(record)
    try:
        outcome = _continue_claimed_record_processing(
            worker_db=db,
            run=run,
            record=record,
            row_number=record.source_row_number,
            source_reference=record.source_key or f"record-{record.id}",
            client_factory=client_factory,
            layout=layout,
            allowed_hosts=allowed_hosts,
            max_bytes=settings.max_file_size_bytes,
            scanner_factory=scanner_factory,
            media_verifier_factory=media_verifier_factory,
            inspection_queue=inspection_queue,
            retry_queue=retry_queue,
        )

        run = _apply_ingestion_results(
            db,
            run,
            [outcome],
            rows_seen=1,
            defer_completion=inspection_queue is not None and outcome.outcome == RecordingIngestionRecordStatus.QUARANTINED.value,
        )
        db.commit()
        db.refresh(record)
        db.refresh(run)
        return record
    except Exception as exc:
        run.status = RecordingIngestionRunStatus.FAILED
        run.completed_at = utcnow()
        run.failure_summary = _sanitize_ingestion_text(str(exc)) or "Record retry failed."
        db.commit()
        raise


def prepare_ingestion_record_retry(
    db: Session,
    *,
    record_id: int,
    requested_by_employee_id: int | None = None,
    manual: bool = False,
) -> RecordingIngestionRecord:
    del requested_by_employee_id

    record = db.get(RecordingIngestionRecord, record_id)
    if record is None:
        raise RecordingIngestionSecurityError("missing_record", "The ingestion record does not exist.")

    _validate_record_retry_eligibility(record, manual=manual)

    active_run = find_active_ingestion_run(db, source_name=record.source_name)
    if active_run is not None:
        raise RecordingIngestionSecurityError(
            "active_run_exists",
            f"Source {record.source_name} already has an active ingestion run.",
        )

    return record


def reconcile_committed_call_handoffs(
    db: Session,
    *,
    queue_task: Callable[[int], Any] | None = None,
) -> list[int]:
    queue_task = queue_task or _queue_call_processing
    queued_call_ids: list[int] = []
    eligible_statuses = (
        RecordingIngestionRecordStatus.ACCEPTED,
        RecordingIngestionRecordStatus.HANDOFF_PENDING,
    )
    claim_cutoff = utcnow() - timedelta(seconds=HANDOFF_RECONCILIATION_LEASE_SECONDS)
    records = (
        db.query(RecordingIngestionRecord)
        .filter(
            RecordingIngestionRecord.call_id.isnot(None),
            RecordingIngestionRecord.pipeline_queued_at.is_(None),
            RecordingIngestionRecord.status.in_(eligible_statuses),
            _handoff_reconciliation_claim_filter(claim_cutoff=claim_cutoff),
        )
        .order_by(RecordingIngestionRecord.id.asc())
        .all()
    )

    for record in records:
        if record.call_id is None:
            continue

        prior_status = record.status
        claimed = (
            db.query(RecordingIngestionRecord)
            .filter(
                RecordingIngestionRecord.id == record.id,
                RecordingIngestionRecord.call_id.isnot(None),
                RecordingIngestionRecord.pipeline_queued_at.is_(None),
                RecordingIngestionRecord.status.in_(eligible_statuses),
                _handoff_reconciliation_claim_filter(claim_cutoff=claim_cutoff),
            )
            .update(
                {
                    RecordingIngestionRecord.status: RecordingIngestionRecordStatus.HANDOFF_PENDING,
                    RecordingIngestionRecord.last_error_category: HANDOFF_RECONCILIATION_CLAIM_CATEGORY,
                    RecordingIngestionRecord.last_error_detail: HANDOFF_RECONCILIATION_CLAIM_DETAIL,
                },
                synchronize_session=False,
            )
        )
        if not claimed:
            db.rollback()
            continue
        db.commit()

        try:
            queue_task(record.call_id)
        except Exception as exc:
            claimed_record = db.get(RecordingIngestionRecord, record.id)
            if claimed_record is None:
                continue
            claimed_record.status = prior_status
            claimed_record.last_error_category = "handoff_queue_failed"
            claimed_record.last_error_detail = _sanitize_ingestion_text(str(exc)) or "Call processing queue dispatch failed."
            db.commit()
            continue

        claimed_record = db.get(RecordingIngestionRecord, record.id)
        if claimed_record is None or claimed_record.call_id is None:
            continue

        claimed_record.pipeline_queued_at = utcnow()
        claimed_record.status = RecordingIngestionRecordStatus.SUBMITTED
        claimed_record.last_error_category = None
        claimed_record.last_error_detail = None
        claimed_record.next_retry_at = None
        if claimed_record.completed_at is None:
            claimed_record.completed_at = utcnow()
        add_recording_ingestion_audit_event(
            db,
            action=INGESTION_AUDIT_RECONCILIATION,
            target=f"Call #{claimed_record.call_id}",
            after_state={
                "run_id": claimed_record.ingestion_run_id,
                "record_id": claimed_record.id,
                "call_id": claimed_record.call_id,
                "status": claimed_record.status,
                "pipeline_queued_at": claimed_record.pipeline_queued_at,
            },
            success=True,
        )
        queued_call_ids.append(claimed_record.call_id)
        db.commit()

    return queued_call_ids
