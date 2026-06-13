"""legacy duplicate role notes marker

Revision ID: f95b791ad75b
Revises: c23d4e5f6a78
Create Date: 2026-06-06 00:00:00.000000

This revision id existed as a duplicate branch that created role_notes a second
time. The canonical role_notes table is created on the main chain by
f65b791ad74d and completed by c23d4e5f6a78.
"""
from typing import Sequence, Union


revision: str = "f95b791ad75b"
down_revision: Union[str, Sequence[str], None] = "c23d4e5f6a78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
