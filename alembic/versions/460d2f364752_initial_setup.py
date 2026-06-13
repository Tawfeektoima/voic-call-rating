"""initial_setup

Revision ID: 460d2f364752
Revises: 
Create Date: 2026-05-03 02:36:37.035372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '460d2f364752'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'employees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('employee_code', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_employees_id', 'employees', ['id'], unique=False)
    op.create_index('ix_employees_employee_code', 'employees', ['employee_code'], unique=True)

    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('evaluation_prompt', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_campaigns_id', 'campaigns', ['id'], unique=False)
    op.create_index('ix_campaigns_name', 'campaigns', ['name'], unique=True)

    op.create_table(
        'calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer(), nullable=False),
        sa.Column('audio_file_path', sa.String(length=500), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('audio_duration', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('evaluation_score', sa.Float(), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('weaknesses', sa.JSON(), nullable=True),
        sa.Column('overridden_score', sa.Float(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calls_id', 'calls', ['id'], unique=False)
    op.create_index('ix_calls_employee_id', 'calls', ['employee_id'], unique=False)
    op.create_index('ix_calls_campaign_id', 'calls', ['campaign_id'], unique=False)
    op.create_index('ix_calls_status', 'calls', ['status'], unique=False)

    op.create_table(
        'system_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('call_id', sa.Integer(), nullable=True),
        sa.Column('error_type', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_system_logs_id', 'system_logs', ['id'], unique=False)

    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target', sa.String(length=255), nullable=True),
        sa.Column('before_state', sa.Text(), nullable=True),
        sa.Column('after_state', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_events_id', 'audit_events', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_audit_events_id', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_index('ix_system_logs_id', table_name='system_logs')
    op.drop_table('system_logs')
    op.drop_index('ix_calls_status', table_name='calls')
    op.drop_index('ix_calls_campaign_id', table_name='calls')
    op.drop_index('ix_calls_employee_id', table_name='calls')
    op.drop_index('ix_calls_id', table_name='calls')
    op.drop_table('calls')
    op.drop_index('ix_campaigns_name', table_name='campaigns')
    op.drop_index('ix_campaigns_id', table_name='campaigns')
    op.drop_table('campaigns')
    op.drop_index('ix_employees_employee_code', table_name='employees')
    op.drop_index('ix_employees_id', table_name='employees')
    op.drop_table('employees')
