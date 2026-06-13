"""add_kpi_threshold_config

Revision ID: a65b791ad75a
Revises: f65b791ad74e
Create Date: 2026-06-06 16:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a65b791ad75a'
down_revision: Union[str, Sequence[str], None] = 'f65b791ad74e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create kpi_threshold_configs table and indexes."""
    op.create_table(
        'kpi_threshold_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('kpi_key', sa.String(length=100), nullable=False),
        sa.Column('kpi_label', sa.String(length=255), nullable=False),
        sa.Column('threshold_type', sa.String(length=50), nullable=False),
        sa.Column('target_value', sa.Float(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes as requested
    op.create_index('ix_kpi_threshold_configs_id', 'kpi_threshold_configs', ['id'], unique=False)
    op.create_index('ix_kpi_threshold_configs_team_id', 'kpi_threshold_configs', ['team_id'], unique=False)
    op.create_index('ix_kpi_threshold_configs_campaign_id', 'kpi_threshold_configs', ['campaign_id'], unique=False)
    op.create_index('ix_kpi_threshold_configs_kpi_key', 'kpi_threshold_configs', ['kpi_key'], unique=False)
    op.create_index('ix_kpi_threshold_configs_is_active', 'kpi_threshold_configs', ['is_active'], unique=False)
    op.create_index('ix_kpi_threshold_configs_created_by_id', 'kpi_threshold_configs', ['created_by_id'], unique=False)
    op.create_index('ix_kpi_threshold_configs_created_at', 'kpi_threshold_configs', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop kpi_threshold_configs table and indexes."""
    op.drop_index('ix_kpi_threshold_configs_created_at', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_created_by_id', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_is_active', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_kpi_key', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_campaign_id', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_team_id', table_name='kpi_threshold_configs')
    op.drop_index('ix_kpi_threshold_configs_id', table_name='kpi_threshold_configs')
    op.drop_table('kpi_threshold_configs')
