"""add recording ingestion tables

Revision ID: b2c9a1d8e4f7
Revises: c3a07b8b4092
Create Date: 2026-06-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c9a1d8e4f7"
down_revision: Union[str, Sequence[str], None] = "c3a07b8b4092"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


recording_ingestion_run_trigger_enum = sa.Enum(
    "scheduled",
    "manual",
    "retry",
    "reconciliation",
    name="recordingingestionruntrigger",
)
recording_ingestion_run_status_enum = sa.Enum(
    "requested",
    "reading_source",
    "processing",
    "completed",
    "completed_with_errors",
    "failed",
    name="recordingingestionrunstatus",
)
recording_ingestion_record_status_enum = sa.Enum(
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
    name="recordingingestionrecordstatus",
)
recording_ingestion_inspection_status_enum = sa.Enum(
    "pending",
    "passed",
    "rejected",
    "unavailable",
    name="recordingingestioninspectionstatus",
)
recording_ingestion_attempt_phase_enum = sa.Enum(
    "validation",
    "download",
    "signature_check",
    "malware_scan",
    "media_verification",
    "storage",
    "handoff",
    name="recordingingestionattemptphase",
)
recording_ingestion_attempt_status_enum = sa.Enum(
    "started",
    "succeeded",
    "failed",
    "skipped_duplicate",
    "retry_scheduled",
    name="recordingingestionattemptstatus",
)


def _create_enums(bind) -> None:
    for enum_type in (
        recording_ingestion_run_trigger_enum,
        recording_ingestion_run_status_enum,
        recording_ingestion_record_status_enum,
        recording_ingestion_inspection_status_enum,
        recording_ingestion_attempt_phase_enum,
        recording_ingestion_attempt_status_enum,
    ):
        enum_type.create(bind, checkfirst=True)


def _drop_enums(bind) -> None:
    for enum_type in (
        recording_ingestion_attempt_status_enum,
        recording_ingestion_attempt_phase_enum,
        recording_ingestion_inspection_status_enum,
        recording_ingestion_record_status_enum,
        recording_ingestion_run_status_enum,
        recording_ingestion_run_trigger_enum,
    ):
        enum_type.drop(bind, checkfirst=True)


def upgrade() -> None:
    bind = op.get_bind()
    _create_enums(bind)

    op.create_table(
        "recording_ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False, server_default="vicdi_tests"),
        sa.Column("trigger", recording_ingestion_run_trigger_enum, nullable=False, server_default="scheduled"),
        sa.Column("status", recording_ingestion_run_status_enum, nullable=False, server_default="requested"),
        sa.Column("requested_by_employee_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retryable_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("rows_seen >= 0", name="ck_recording_ingestion_runs_rows_seen_non_negative"),
        sa.CheckConstraint("new_count >= 0", name="ck_recording_ingestion_runs_new_count_non_negative"),
        sa.CheckConstraint("duplicate_count >= 0", name="ck_recording_ingestion_runs_duplicate_count_non_negative"),
        sa.CheckConstraint("success_count >= 0", name="ck_recording_ingestion_runs_success_count_non_negative"),
        sa.CheckConstraint("failed_count >= 0", name="ck_recording_ingestion_runs_failed_count_non_negative"),
        sa.CheckConstraint("retryable_count >= 0", name="ck_recording_ingestion_runs_retryable_count_non_negative"),
        sa.ForeignKeyConstraint(["requested_by_employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recording_ingestion_runs_source_name", "recording_ingestion_runs", ["source_name"], unique=False)
    op.create_index("ix_recording_ingestion_runs_trigger", "recording_ingestion_runs", ["trigger"], unique=False)
    op.create_index("ix_recording_ingestion_runs_status", "recording_ingestion_runs", ["status"], unique=False)
    op.create_index(
        "ix_recording_ingestion_runs_requested_by_employee_id",
        "recording_ingestion_runs",
        ["requested_by_employee_id"],
        unique=False,
    )
    op.create_index("ix_recording_ingestion_runs_started_at", "recording_ingestion_runs", ["started_at"], unique=False)
    op.create_index("ix_recording_ingestion_runs_completed_at", "recording_ingestion_runs", ["completed_at"], unique=False)
    op.create_index("ix_recording_ingestion_runs_created_at", "recording_ingestion_runs", ["created_at"], unique=False)
    op.create_index("ix_recording_ingestion_runs_updated_at", "recording_ingestion_runs", ["updated_at"], unique=False)
    op.create_index("ix_recording_ingestion_runs_source_status", "recording_ingestion_runs", ["source_name", "status"], unique=False)
    op.create_index("ix_recording_ingestion_runs_source_started_at", "recording_ingestion_runs", ["source_name", "started_at"], unique=False)
    op.create_index(
        "uq_recording_ingestion_runs_active_source",
        "recording_ingestion_runs",
        ["source_name"],
        unique=True,
        postgresql_where=sa.text("status IN ('requested', 'reading_source', 'processing')"),
    )

    op.create_table(
        "recording_ingestion_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=False, server_default="vicdi_tests"),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("recording_url", sa.Text(), nullable=False),
        sa.Column("recording_url_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("source_call_date", sa.Date(), nullable=True),
        sa.Column("source_score", sa.Float(), nullable=True),
        sa.Column("source_quality_notes", sa.Text(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("status", recording_ingestion_record_status_enum, nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quarantine_file_path", sa.String(length=500), nullable=True),
        sa.Column("stored_file_path", sa.String(length=500), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("byte_size", sa.Integer(), nullable=True),
        sa.Column("file_sha256", sa.String(length=128), nullable=True),
        sa.Column("signature_status", recording_ingestion_inspection_status_enum, nullable=False, server_default="pending"),
        sa.Column("malware_scan_status", recording_ingestion_inspection_status_enum, nullable=False, server_default="pending"),
        sa.Column("media_verification_status", recording_ingestion_inspection_status_enum, nullable=False, server_default="pending"),
        sa.Column("scanner_name", sa.String(length=100), nullable=True),
        sa.Column("scanner_version", sa.String(length=100), nullable=True),
        sa.Column("inspection_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("call_id", sa.Integer(), nullable=True),
        sa.Column("pipeline_queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_category", sa.String(length=100), nullable=True),
        sa.Column("last_error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source_row_number > 0", name="ck_recording_ingestion_records_source_row_positive"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_recording_ingestion_records_attempt_count_non_negative"),
        sa.CheckConstraint("byte_size IS NULL OR byte_size >= 0", name="ck_recording_ingestion_records_byte_size_non_negative"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["recording_ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_name", "source_key", name="uq_recording_ingestion_records_source_key"),
        sa.UniqueConstraint("call_id", name="uq_recording_ingestion_records_call_id"),
    )
    op.create_index(
        "ix_recording_ingestion_records_ingestion_run_id",
        "recording_ingestion_records",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index("ix_recording_ingestion_records_source_name", "recording_ingestion_records", ["source_name"], unique=False)
    op.create_index("ix_recording_ingestion_records_source_key", "recording_ingestion_records", ["source_key"], unique=False)
    op.create_index(
        "ix_recording_ingestion_records_source_row_number",
        "recording_ingestion_records",
        ["source_row_number"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_recording_url_fingerprint",
        "recording_ingestion_records",
        ["recording_url_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_source_call_date",
        "recording_ingestion_records",
        ["source_call_date"],
        unique=False,
    )
    op.create_index("ix_recording_ingestion_records_status", "recording_ingestion_records", ["status"], unique=False)
    op.create_index(
        "ix_recording_ingestion_records_next_retry_at",
        "recording_ingestion_records",
        ["next_retry_at"],
        unique=False,
    )
    op.create_index("ix_recording_ingestion_records_employee_id", "recording_ingestion_records", ["employee_id"], unique=False)
    op.create_index("ix_recording_ingestion_records_call_id", "recording_ingestion_records", ["call_id"], unique=False)
    op.create_index("ix_recording_ingestion_records_source_status_retry", "recording_ingestion_records", ["source_name", "status", "next_retry_at"], unique=False)
    op.create_index("ix_recording_ingestion_records_file_sha256", "recording_ingestion_records", ["file_sha256"], unique=False)
    op.create_index(
        "ix_recording_ingestion_records_signature_status",
        "recording_ingestion_records",
        ["signature_status"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_malware_scan_status",
        "recording_ingestion_records",
        ["malware_scan_status"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_media_verification_status",
        "recording_ingestion_records",
        ["media_verification_status"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_inspection_completed_at",
        "recording_ingestion_records",
        ["inspection_completed_at"],
        unique=False,
    )
    op.create_index(
        "ix_recording_ingestion_records_pipeline_queued_at",
        "recording_ingestion_records",
        ["pipeline_queued_at"],
        unique=False,
    )
    op.create_index("ix_recording_ingestion_records_created_at", "recording_ingestion_records", ["created_at"], unique=False)
    op.create_index("ix_recording_ingestion_records_updated_at", "recording_ingestion_records", ["updated_at"], unique=False)
    op.create_index("ix_recording_ingestion_records_completed_at", "recording_ingestion_records", ["completed_at"], unique=False)

    op.create_table(
        "recording_ingestion_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ingestion_record_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("phase", recording_ingestion_attempt_phase_enum, nullable=False),
        sa.Column("status", recording_ingestion_attempt_status_enum, nullable=False, server_default="started"),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("bytes_downloaded", sa.Integer(), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="ck_recording_ingestion_attempts_attempt_number_positive"),
        sa.CheckConstraint("bytes_downloaded IS NULL OR bytes_downloaded >= 0", name="ck_recording_ingestion_attempts_bytes_downloaded_non_negative"),
        sa.ForeignKeyConstraint(["ingestion_record_id"], ["recording_ingestion_records.id"]),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["recording_ingestion_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ingestion_record_id",
            "attempt_number",
            "phase",
            name="uq_recording_ingestion_attempts_record_attempt_phase",
        ),
    )
    op.create_index("ix_recording_ingestion_attempts_run_id", "recording_ingestion_attempts", ["ingestion_run_id"], unique=False)
    op.create_index("ix_recording_ingestion_attempts_record_id", "recording_ingestion_attempts", ["ingestion_record_id"], unique=False)
    op.create_index("ix_recording_ingestion_attempts_phase", "recording_ingestion_attempts", ["phase"], unique=False)
    op.create_index("ix_recording_ingestion_attempts_status", "recording_ingestion_attempts", ["status"], unique=False)
    op.create_index("ix_recording_ingestion_attempts_started_at", "recording_ingestion_attempts", ["started_at"], unique=False)
    op.create_index("ix_recording_ingestion_attempts_completed_at", "recording_ingestion_attempts", ["completed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_recording_ingestion_attempts_completed_at", table_name="recording_ingestion_attempts")
    op.drop_index("ix_recording_ingestion_attempts_started_at", table_name="recording_ingestion_attempts")
    op.drop_index("ix_recording_ingestion_attempts_status", table_name="recording_ingestion_attempts")
    op.drop_index("ix_recording_ingestion_attempts_phase", table_name="recording_ingestion_attempts")
    op.drop_index("ix_recording_ingestion_attempts_record_id", table_name="recording_ingestion_attempts")
    op.drop_index("ix_recording_ingestion_attempts_run_id", table_name="recording_ingestion_attempts")
    op.drop_table("recording_ingestion_attempts")

    op.drop_index("ix_recording_ingestion_records_completed_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_updated_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_created_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_pipeline_queued_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_inspection_completed_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_media_verification_status", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_malware_scan_status", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_signature_status", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_file_sha256", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_next_retry_at", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_status", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_source_call_date", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_recording_url_fingerprint", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_source_row_number", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_source_key", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_source_name", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_ingestion_run_id", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_call_id", table_name="recording_ingestion_records")
    op.drop_index("ix_recording_ingestion_records_employee_id", table_name="recording_ingestion_records")
    op.drop_table("recording_ingestion_records")

    op.drop_index("uq_recording_ingestion_runs_active_source", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_updated_at", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_created_at", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_completed_at", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_started_at", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_requested_by_employee_id", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_status", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_trigger", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_source_name", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_source_status", table_name="recording_ingestion_runs")
    op.drop_index("ix_recording_ingestion_runs_source_started_at", table_name="recording_ingestion_runs")
    op.drop_table("recording_ingestion_runs")

    bind = op.get_bind()
    _drop_enums(bind)
