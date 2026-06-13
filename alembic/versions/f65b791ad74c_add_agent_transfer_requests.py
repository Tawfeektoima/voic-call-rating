"""add_agent_transfer_requests

Revision ID: f65b791ad74c
Revises: f65b791ad74b
Create Date: 2026-06-06 04:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f65b791ad74c'
down_revision: Union[str, Sequence[str], None] = 'f65b791ad74b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('agent_transfer_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('from_team_id', sa.Integer(), nullable=False),
        sa.Column('to_team_id', sa.Integer(), nullable=True),
        sa.Column('requested_by_id', sa.Integer(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['from_team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['to_team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['requested_by_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_transfer_requests_agent_id', 'agent_transfer_requests', ['agent_id'], unique=False)
    op.create_index('ix_agent_transfer_requests_from_team_id', 'agent_transfer_requests', ['from_team_id'], unique=False)
    op.create_index('ix_agent_transfer_requests_to_team_id', 'agent_transfer_requests', ['to_team_id'], unique=False)
    op.create_index('ix_agent_transfer_requests_requested_by_id', 'agent_transfer_requests', ['requested_by_id'], unique=False)
    op.create_index('ix_agent_transfer_requests_status', 'agent_transfer_requests', ['status'], unique=False)
    op.create_index('ix_agent_transfer_requests_created_at', 'agent_transfer_requests', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_agent_transfer_requests_created_at', table_name='agent_transfer_requests')
    op.drop_index('ix_agent_transfer_requests_status', table_name='agent_transfer_requests')
    op.drop_index('ix_agent_transfer_requests_requested_by_id', table_name='agent_transfer_requests')
    op.drop_index('ix_agent_transfer_requests_to_team_id', table_name='agent_transfer_requests')
    op.drop_index('ix_agent_transfer_requests_from_team_id', table_name='agent_transfer_requests')
    op.drop_index('ix_agent_transfer_requests_agent_id', table_name='agent_transfer_requests')
    op.drop_table('agent_transfer_requests')
