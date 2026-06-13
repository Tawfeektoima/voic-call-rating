"""add_ops_manager_role_db_support

Revision ID: 7ae8b506fa69
Revises: 6ee8b606da69
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ae8b506fa69'
down_revision: Union[str, Sequence[str], None] = '6ee8b606da69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support OPS_MANAGER enum value."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE 'OPS_MANAGER'")

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', name='userrole'),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', name='userrole'),
               existing_nullable=False)
