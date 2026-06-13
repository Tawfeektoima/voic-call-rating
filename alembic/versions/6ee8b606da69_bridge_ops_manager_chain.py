"""bridge ops manager migration chain

Revision ID: 6ee8b606da69
Revises: 6f5e4d3c2b1a
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union


revision: str = "6ee8b606da69"
down_revision: Union[str, Sequence[str], None] = "6f5e4d3c2b1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
