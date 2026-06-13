"""add password reset identity

Revision ID: e45f6a7b8c90
Revises: d34e5f6a7b89
Create Date: 2026-06-14 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e45f6a7b8c90"
down_revision: Union[str, Sequence[str], None] = "d34e5f6a7b89"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("national_id_hash", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_employees_national_id_hash", ["national_id_hash"], unique=True)

    with op.batch_alter_table("login_otp_challenges") as batch_op:
        batch_op.add_column(sa.Column("purpose", sa.String(length=50), nullable=False, server_default="LOGIN"))
        batch_op.create_index("ix_login_otp_challenges_purpose", ["purpose"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("login_otp_challenges") as batch_op:
        batch_op.drop_index("ix_login_otp_challenges_purpose")
        batch_op.drop_column("purpose")

    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_index("ix_employees_national_id_hash")
        batch_op.drop_column("national_id_hash")
