"""add audit_event success flag

Revision ID: 9d3c5f7a2e11
Revises: 497c670a3f7d
Create Date: 2026-06-04 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d3c5f7a2e11'
down_revision: Union[str, Sequence[str], None] = '497c670a3f7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'audit_events',
        sa.Column('success', sa.Boolean(), nullable=False, server_default=sa.true())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('audit_events', 'success')
