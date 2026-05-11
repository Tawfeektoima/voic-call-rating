"""add_agent_violations_table

Revision ID: 497c670a3f7d
Revises: ea7ab85f8491
Create Date: 2026-05-11 18:40:30.423720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '497c670a3f7d'
down_revision: Union[str, Sequence[str], None] = 'ea7ab85f8491'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check if table exists to avoid errors on SQLite where partial migrations might have happened
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    if 'agent_violations' not in tables:
        op.create_table('agent_violations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('call_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('violation_id', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('occurrence', sa.Integer(), nullable=False),
        sa.Column('penalty_tier', sa.String(length=20), nullable=False),
        sa.Column('score_deduction', sa.Float(), nullable=False),
        sa.Column('hr_flagged', sa.Boolean(), nullable=False),
        sa.Column('auto_fail', sa.Boolean(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('timestamp_in_call', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_agent_violations_call_id'), 'agent_violations', ['call_id'], unique=False)
        op.create_index(op.f('ix_agent_violations_employee_id'), 'agent_violations', ['employee_id'], unique=False)
        op.create_index(op.f('ix_agent_violations_id'), 'agent_violations', ['id'], unique=False)
        op.create_index(op.f('ix_agent_violations_violation_id'), 'agent_violations', ['violation_id'], unique=False)

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_violations_violation_id'), table_name='agent_violations')
    op.drop_index(op.f('ix_agent_violations_id'), table_name='agent_violations')
    op.drop_index(op.f('ix_agent_violations_employee_id'), table_name='agent_violations')
    op.drop_index(op.f('ix_agent_violations_call_id'), table_name='agent_violations')
    op.drop_table('agent_violations')
