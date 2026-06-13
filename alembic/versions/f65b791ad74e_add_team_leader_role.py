"""add_team_leader_role

Revision ID: f65b791ad74e
Revises: f65b791ad74d
Create Date: 2026-06-06 13:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f65b791ad74e'
down_revision: Union[str, Sequence[str], None] = 'f65b791ad74d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support TEAM_LEADER enum value."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE 'TEAM_LEADER'")

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', 'TEAM_LEADER', name='userrole'),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', 'TEAM_LEADER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', name='userrole'),
               existing_nullable=False)
