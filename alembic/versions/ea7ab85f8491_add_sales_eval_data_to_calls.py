"""add sales_eval_data to calls

Revision ID: ea7ab85f8491
Revises: c42e9d755115
Create Date: 2026-05-07 20:54:22.911096

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'ea7ab85f8491'
down_revision: Union[str, Sequence[str], None] = 'c42e9d755115'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('calls', sa.Column('sales_eval_data', sa.JSON(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('calls') as batch_op:
        batch_op.drop_column('sales_eval_data')

