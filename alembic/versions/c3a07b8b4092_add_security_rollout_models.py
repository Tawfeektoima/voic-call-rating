"""add security rollout models

Revision ID: c3a07b8b4092
Revises: f16a2c7d9e10
Create Date: 2026-06-18 05:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a07b8b4092"
down_revision: Union[str, Sequence[str], None] = "f16a2c7d9e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add device_id_hash to login_otp_challenges
    with op.batch_alter_table("login_otp_challenges") as batch_op:
        batch_op.add_column(sa.Column("device_id_hash", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_login_otp_challenges_device_id_hash", ["device_id_hash"], unique=False)

    # 2. Create employee_shifts
    op.create_table(
        "employee_shifts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("shift_start", sa.Time(), nullable=True),
        sa.Column("shift_end", sa.Time(), nullable=True),
        sa.Column("grace_before_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("grace_after_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_employee_shift_date")
    )
    op.create_index("ix_employee_shifts_id", "employee_shifts", ["id"], unique=False)
    op.create_index("ix_employee_shifts_employee_id", "employee_shifts", ["employee_id"], unique=False)
    op.create_index("ix_employee_shifts_work_date", "employee_shifts", ["work_date"], unique=False)
    op.create_index("ix_employee_shifts_status", "employee_shifts", ["status"], unique=False)
    op.create_index("ix_employee_shifts_employee_id_work_date", "employee_shifts", ["employee_id", "work_date"], unique=False)
    op.create_index("ix_employee_shifts_status_work_date", "employee_shifts", ["status", "work_date"], unique=False)

    # 3. Create trusted_devices
    op.create_table(
        "trusted_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("device_id_hash", sa.String(length=128), nullable=False),
        sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("device_label", sa.String(length=255), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["approved_by_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "device_id_hash", name="uq_trusted_device_employee_device")
    )
    op.create_index("ix_trusted_devices_id", "trusted_devices", ["id"], unique=False)
    op.create_index("ix_trusted_devices_employee_id", "trusted_devices", ["employee_id"], unique=False)
    op.create_index("ix_trusted_devices_device_id_hash", "trusted_devices", ["device_id_hash"], unique=False)
    op.create_index("ix_trusted_devices_is_trusted", "trusted_devices", ["is_trusted"], unique=False)
    op.create_index("ix_trusted_devices_employee_id_is_trusted", "trusted_devices", ["employee_id", "is_trusted"], unique=False)

    # 4. Create user_sessions
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("trusted_device_id", sa.Integer(), nullable=True),
        sa.Column("sid", sa.String(length=64), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("device_id_hash", sa.String(length=128), nullable=False),
        sa.Column("device_fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["trusted_device_id"], ["trusted_devices.id"]),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("ix_user_sessions_id", "user_sessions", ["id"], unique=False)
    op.create_index("ix_user_sessions_employee_id", "user_sessions", ["employee_id"], unique=False)
    op.create_index("ix_user_sessions_trusted_device_id", "user_sessions", ["trusted_device_id"], unique=False)
    op.create_index("ix_user_sessions_sid", "user_sessions", ["sid"], unique=True)
    op.create_index("ix_user_sessions_jti", "user_sessions", ["jti"], unique=True)
    op.create_index("ix_user_sessions_device_id_hash", "user_sessions", ["device_id_hash"], unique=False)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False)
    op.create_index("ix_user_sessions_is_active", "user_sessions", ["is_active"], unique=False)
    op.create_index("ix_user_sessions_employee_id_is_active", "user_sessions", ["employee_id", "is_active"], unique=False)
    op.create_index("ix_user_sessions_employee_device_active", "user_sessions", ["employee_id", "device_id_hash", "is_active"], unique=False)


def downgrade() -> None:
    # 1. Drop user_sessions indexes and table
    op.drop_index("ix_user_sessions_employee_device_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_employee_id_is_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_is_active", table_name="user_sessions")
    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_device_id_hash", table_name="user_sessions")
    op.drop_index("ix_user_sessions_jti", table_name="user_sessions")
    op.drop_index("ix_user_sessions_sid", table_name="user_sessions")
    op.drop_index("ix_user_sessions_trusted_device_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_employee_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_id", table_name="user_sessions")
    op.drop_table("user_sessions")

    # 2. Drop trusted_devices indexes and table
    op.drop_index("ix_trusted_devices_employee_id_is_trusted", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_is_trusted", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_device_id_hash", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_employee_id", table_name="trusted_devices")
    op.drop_index("ix_trusted_devices_id", table_name="trusted_devices")
    op.drop_table("trusted_devices")

    # 3. Drop employee_shifts indexes and table
    op.drop_index("ix_employee_shifts_status_work_date", table_name="employee_shifts")
    op.drop_index("ix_employee_shifts_employee_id_work_date", table_name="employee_shifts")
    op.drop_index("ix_employee_shifts_status", table_name="employee_shifts")
    op.drop_index("ix_employee_shifts_work_date", table_name="employee_shifts")
    op.drop_index("ix_employee_shifts_employee_id", table_name="employee_shifts")
    op.drop_index("ix_employee_shifts_id", table_name="employee_shifts")
    op.drop_table("employee_shifts")

    # 4. Remove device_id_hash from login_otp_challenges
    with op.batch_alter_table("login_otp_challenges") as batch_op:
        batch_op.drop_index("ix_login_otp_challenges_device_id_hash")
        batch_op.drop_column("device_id_hash")
