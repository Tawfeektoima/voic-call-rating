"""add login otp challenges

Revision ID: d34e5f6a7b89
Revises: f95b791ad75b
Create Date: 2026-06-14 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d34e5f6a7b89"
down_revision: Union[str, Sequence[str], None] = "f95b791ad75b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("otp_email", sa.String(length=255), nullable=True))
        batch_op.create_index("ix_employees_otp_email", ["otp_email"], unique=False)

    op.create_table(
        "login_otp_challenges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("destination_email", sa.String(length=255), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_otp_challenges_id", "login_otp_challenges", ["id"], unique=False)
    op.create_index("ix_login_otp_challenges_employee_id", "login_otp_challenges", ["employee_id"], unique=False)
    op.create_index("ix_login_otp_challenges_expires_at", "login_otp_challenges", ["expires_at"], unique=False)
    op.create_index(
        "ix_login_otp_employee_active",
        "login_otp_challenges",
        ["employee_id", "used_at", "expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_login_otp_employee_active", table_name="login_otp_challenges")
    op.drop_index("ix_login_otp_challenges_expires_at", table_name="login_otp_challenges")
    op.drop_index("ix_login_otp_challenges_employee_id", table_name="login_otp_challenges")
    op.drop_index("ix_login_otp_challenges_id", table_name="login_otp_challenges")
    op.drop_table("login_otp_challenges")

    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_index("ix_employees_otp_email")
        batch_op.drop_column("otp_email")
