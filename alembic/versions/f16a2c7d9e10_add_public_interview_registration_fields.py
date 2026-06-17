"""add public interview registration fields

Revision ID: f16a2c7d9e10
Revises: f15f1b6d9c43
Create Date: 2026-06-15 05:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f16a2c7d9e10"
down_revision: Union[str, Sequence[str], None] = "f15f1b6d9c43"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("interview_candidates", sa.Column("date_of_birth_encrypted", sa.Text(), nullable=True))
    op.add_column("interview_candidates", sa.Column("address_encrypted", sa.Text(), nullable=True))
    op.add_column(
        "interview_candidates",
        sa.Column("registration_source", sa.String(length=50), nullable=False, server_default="hr"),
    )
    op.create_index(
        "ix_interview_candidates_registration_source",
        "interview_candidates",
        ["registration_source"],
        unique=False,
    )
    op.alter_column("interview_candidates", "registration_source", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_interview_candidates_registration_source", table_name="interview_candidates")
    op.drop_column("interview_candidates", "registration_source")
    op.drop_column("interview_candidates", "address_encrypted")
    op.drop_column("interview_candidates", "date_of_birth_encrypted")
