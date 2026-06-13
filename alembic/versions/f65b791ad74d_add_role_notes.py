"""add_role_notes

Revision ID: f65b791ad74d
Revises: f65b791ad74c
Create Date: 2026-06-06 05:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f65b791ad74d'
down_revision: Union[str, Sequence[str], None] = 'f65b791ad74c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('role_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=True),
        sa.Column('recipient_role', sa.String(length=50), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('call_id', sa.Integer(), nullable=True),
        sa.Column('parent_note_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('note_type', sa.String(length=50), nullable=False, server_default='GENERAL'),
        sa.Column('priority', sa.String(length=50), nullable=False, server_default='NORMAL'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('kpi_key', sa.String(length=100), nullable=True),
        sa.Column('kpi_label', sa.String(length=255), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('target_value', sa.Float(), nullable=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_name_snapshot', sa.String(length=255), nullable=True),
        sa.Column('team_name_snapshot', sa.String(length=255), nullable=True),
        sa.Column('campaign_name_snapshot', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['sender_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['recipient_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ),
        sa.ForeignKeyConstraint(['parent_note_id'], ['role_notes.id'], ),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_role_notes_sender_id', 'role_notes', ['sender_id'], unique=False)
    op.create_index('ix_role_notes_recipient_id', 'role_notes', ['recipient_id'], unique=False)
    op.create_index('ix_role_notes_recipient_role', 'role_notes', ['recipient_role'], unique=False)
    op.create_index('ix_role_notes_team_id', 'role_notes', ['team_id'], unique=False)
    op.create_index('ix_role_notes_campaign_id', 'role_notes', ['campaign_id'], unique=False)
    op.create_index('ix_role_notes_employee_id', 'role_notes', ['employee_id'], unique=False)
    op.create_index('ix_role_notes_call_id', 'role_notes', ['call_id'], unique=False)
    op.create_index('ix_role_notes_status', 'role_notes', ['status'], unique=False)
    op.create_index('ix_role_notes_note_type', 'role_notes', ['note_type'], unique=False)
    op.create_index('ix_role_notes_priority', 'role_notes', ['priority'], unique=False)
    op.create_index('ix_role_notes_created_at', 'role_notes', ['created_at'], unique=False)
    op.create_index('ix_role_notes_parent_note_id', 'role_notes', ['parent_note_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_role_notes_parent_note_id', table_name='role_notes')
    op.drop_index('ix_role_notes_created_at', table_name='role_notes')
    op.drop_index('ix_role_notes_priority', table_name='role_notes')
    op.drop_index('ix_role_notes_note_type', table_name='role_notes')
    op.drop_index('ix_role_notes_status', table_name='role_notes')
    op.drop_index('ix_role_notes_call_id', table_name='role_notes')
    op.drop_index('ix_role_notes_employee_id', table_name='role_notes')
    op.drop_index('ix_role_notes_campaign_id', table_name='role_notes')
    op.drop_index('ix_role_notes_team_id', table_name='role_notes')
    op.drop_index('ix_role_notes_recipient_role', table_name='role_notes')
    op.drop_index('ix_role_notes_recipient_id', table_name='role_notes')
    op.drop_index('ix_role_notes_sender_id', table_name='role_notes')
    op.drop_table('role_notes')
