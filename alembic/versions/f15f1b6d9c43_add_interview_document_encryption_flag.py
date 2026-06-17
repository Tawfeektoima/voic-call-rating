"""add interview document encryption flag

Revision ID: f15f1b6d9c43
Revises: f14e0a5c8b32
Create Date: 2026-06-14 19:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f15f1b6d9c43"
down_revision: Union[str, Sequence[str], None] = "f14e0a5c8b32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interview_candidate_documents",
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_interview_candidate_documents_is_encrypted",
        "interview_candidate_documents",
        ["is_encrypted"],
        unique=False,
    )
    op.alter_column("interview_candidate_documents", "is_encrypted", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_interview_candidate_documents_is_encrypted", table_name="interview_candidate_documents")
    op.drop_column("interview_candidate_documents", "is_encrypted")
