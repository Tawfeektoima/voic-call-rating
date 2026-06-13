"""add_role_notes

Revision ID: f95b791ad75b
Revises: ea7ab85f8491
Create Date: 2026-06-06 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f95b791ad75b"
down_revision: Union[str, Sequence[str], None] = "ea7ab85f8491"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column("recipient_id", sa.Integer(), nullable=True),
        sa.Column("recipient_role", sa.String(length=50), nullable=True),
        sa.Column("visibility", sa.Enum("INTERNAL", "RECIPIENT_VISIBLE", "AGENT_VISIBLE", name="rolenotevisibility"), nullable=False, server_default="INTERNAL"),
        sa.Column("team_id", sa.Integer(), nullable=True),
        sa.Column("campaign_id", sa.Integer(), nullable=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("call_id", sa.Integer(), nullable=True),
        sa.Column("parent_note_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("note_type", sa.Enum(
            "GENERAL", "COACHING_NOTE", "COACHING_ESCALATION", "QA_REVIEW_REQUEST", "QA_DISPUTE",
            "OPS_ESCALATION", "KPI_ALERT", "KPI_FOLLOW_UP", "TRANSFER_CONTEXT", "HR_COMPLIANCE",
            "CANDIDATE_REVIEW", "AI_DETECTION_REVIEW", "SYSTEM_ISSUE", name="rolenotetype"
        ), nullable=False, server_default="GENERAL"),
        sa.Column("priority", sa.Enum("LOW", "NORMAL", "HIGH", "URGENT", name="rolenotepriority"), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.Enum("OPEN", "READ", "IN_PROGRESS", "WAITING_REPLY", "RESOLVED", "ARCHIVED", "DELETED", name="rolenotestatus"), nullable=False, server_default="OPEN"),
        sa.Column("kpi_key", sa.String(length=100), nullable=True),
        sa.Column("kpi_label", sa.String(length=255), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("agent_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("team_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("campaign_name_snapshot", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_id", sa.Integer(), nullable=True),
        sa.Column("delete_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["recipient_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["call_id"], ["calls.id"]),
        sa.ForeignKeyConstraint(["parent_note_id"], ["role_notes.id"]),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["deleted_by_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_role_notes_sender_id", ["sender_id"]),
        ("ix_role_notes_recipient_id", ["recipient_id"]),
        ("ix_role_notes_recipient_role", ["recipient_role"]),
        ("ix_role_notes_visibility", ["visibility"]),
        ("ix_role_notes_team_id", ["team_id"]),
        ("ix_role_notes_campaign_id", ["campaign_id"]),
        ("ix_role_notes_employee_id", ["employee_id"]),
        ("ix_role_notes_call_id", ["call_id"]),
        ("ix_role_notes_parent_note_id", ["parent_note_id"]),
        ("ix_role_notes_note_type", ["note_type"]),
        ("ix_role_notes_priority", ["priority"]),
        ("ix_role_notes_status", ["status"]),
        ("ix_role_notes_created_at", ["created_at"]),
        ("ix_role_notes_deleted_at", ["deleted_at"]),
    ):
        op.create_index(index_name, "role_notes", columns, unique=False)


def downgrade() -> None:
    for index_name in (
        "ix_role_notes_deleted_at",
        "ix_role_notes_created_at",
        "ix_role_notes_status",
        "ix_role_notes_priority",
        "ix_role_notes_note_type",
        "ix_role_notes_parent_note_id",
        "ix_role_notes_call_id",
        "ix_role_notes_employee_id",
        "ix_role_notes_campaign_id",
        "ix_role_notes_team_id",
        "ix_role_notes_visibility",
        "ix_role_notes_recipient_role",
        "ix_role_notes_recipient_id",
        "ix_role_notes_sender_id",
    ):
        op.drop_index(index_name, table_name="role_notes")
    op.drop_table("role_notes")
