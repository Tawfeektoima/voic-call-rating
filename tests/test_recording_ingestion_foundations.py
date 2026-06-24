from datetime import datetime, timezone
import importlib.util
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.models import (
    RecordingIngestionRecord,
    RecordingIngestionRecordStatus,
    RecordingIngestionRun,
)
from app.schemas import RecordingIngestionAttemptOut, RecordingIngestionRecordOut


def test_recording_ingestion_enums_store_lowercase_values():
    assert RecordingIngestionRun.__table__.c.trigger.type.enums == [
        "scheduled",
        "manual",
        "retry",
        "reconciliation",
    ]
    assert RecordingIngestionRun.__table__.c.status.type.enums == [
        "requested",
        "reading_source",
        "processing",
        "completed",
        "completed_with_errors",
        "failed",
    ]
    assert RecordingIngestionRecord.__table__.c.status.type.enums == [
        "pending",
        "downloading",
        "quarantined",
        "inspecting",
        "accepted",
        "handoff_pending",
        "submitted",
        "duplicate",
        "failed",
        "retry_scheduled",
        "requires_review",
        "rejected",
    ]


def test_active_run_index_is_limited_to_non_terminal_statuses():
    index = next(
        item for item in RecordingIngestionRun.__table__.indexes
        if item.name == "uq_recording_ingestion_runs_active_source"
    )

    where_clause = str(index.dialect_options["postgresql"]["where"])

    assert index.unique is True
    assert "requested" in where_clause
    assert "reading_source" in where_clause
    assert "processing" in where_clause


def test_record_schema_maps_last_error_fields_and_sanitizes_sensitive_text():
    record = RecordingIngestionRecord(
        id=1,
        ingestion_run_id=9,
        source_name="vicdi_tests",
        source_key="row-1",
        source_row_number=1,
        source_payload={"CALL LINK": "https://archive.dial-fusion.com/recording.mp3"},
        recording_url="https://archive.dial-fusion.com/recording.mp3",
        recording_url_fingerprint="fp-1",
        status=RecordingIngestionRecordStatus.FAILED,
        attempt_count=1,
        last_error_category="timeout",
        last_error_detail="See https://archive.dial-fusion.com/private and /var/lib/call-rating/quarantine/tmp.wav",
        source_quality_notes="Supervisor note with token=abc123 and C:\\quarantine\\recording.wav",
        created_at=datetime.now(timezone.utc),
    )

    payload = RecordingIngestionRecordOut.model_validate(record)

    assert payload.source_reference == "row-1"
    assert payload.error_category == "timeout"
    assert payload.error_detail == "See [redacted-url] and [redacted-path]"
    assert payload.source_quality_notes == "Supervisor note with token=[redacted] and [redacted-path]"


def test_attempt_schema_sanitizes_sensitive_error_detail():
    payload = RecordingIngestionAttemptOut.model_validate(
        {
            "id": 1,
            "ingestion_record_id": 11,
            "ingestion_run_id": 12,
            "attempt_number": 1,
            "phase": "download",
            "status": "failed",
            "error_category": "denied",
            "error_detail": "blocked by https://example.com/download at /tmp/file.wav",
            "started_at": datetime.now(timezone.utc),
            "completed_at": None,
            "http_status": 403,
            "bytes_downloaded": 0,
        }
    )

    assert payload.error_detail == "blocked by [redacted-url] at [redacted-path]"


def test_recording_ingestion_migration_revision_is_registered_for_upgrade_and_downgrade():
    config = Config(str(Path("alembic.ini").resolve()))
    scripts = ScriptDirectory.from_config(config)
    head_revision = scripts.get_current_head()
    ingestion_revision = scripts.get_revision("b2c9a1d8e4f7")

    assert head_revision == "b2c9a1d8e4f7"
    assert ingestion_revision is not None
    assert ingestion_revision.revision == "b2c9a1d8e4f7"
    assert ingestion_revision.down_revision == "c3a07b8b4092"


def test_recording_ingestion_migration_executes_clean_upgrade_and_downgrade(tmp_path):
    database_path = tmp_path / "recording-ingestion-alembic.sqlite"
    database_url = f"sqlite:///{database_path.as_posix()}"
    migration_path = Path("alembic/versions/b2c9a1d8e4f7_add_recording_ingestion_tables.py").resolve()
    module_spec = importlib.util.spec_from_file_location("recording_ingestion_migration", migration_path)
    assert module_spec is not None and module_spec.loader is not None
    migration_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(migration_module)

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE employees (id INTEGER PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE campaigns (id INTEGER PRIMARY KEY)"))
            connection.execute(text("CREATE TABLE calls (id INTEGER PRIMARY KEY)"))
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration_module.upgrade()

        upgraded_inspector = inspect(engine)
        upgraded_tables = set(upgraded_inspector.get_table_names())
        assert "recording_ingestion_runs" in upgraded_tables
        assert "recording_ingestion_records" in upgraded_tables
        assert "recording_ingestion_attempts" in upgraded_tables

        run_columns = {column["name"] for column in upgraded_inspector.get_columns("recording_ingestion_runs")}
        record_columns = {column["name"] for column in upgraded_inspector.get_columns("recording_ingestion_records")}
        attempt_columns = {column["name"] for column in upgraded_inspector.get_columns("recording_ingestion_attempts")}

        assert {"source_name", "trigger", "status", "rows_seen", "failure_summary"} <= run_columns
        assert {"source_key", "recording_url", "file_sha256", "pipeline_queued_at"} <= record_columns
        assert {"attempt_number", "phase", "status", "bytes_downloaded"} <= attempt_columns
        with engine.begin() as connection:
            context = MigrationContext.configure(connection)
            with Operations.context(context):
                migration_module.downgrade()

        downgraded_inspector = inspect(engine)
        downgraded_tables = set(downgraded_inspector.get_table_names())
        assert "recording_ingestion_runs" not in downgraded_tables
        assert "recording_ingestion_records" not in downgraded_tables
        assert "recording_ingestion_attempts" not in downgraded_tables
    finally:
        engine.dispose()
