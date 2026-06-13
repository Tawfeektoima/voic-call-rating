"""add_team_manager_foundations

Revision ID: f65b791ad74b
Revises: 7ae8b506fa69
Create Date: 2026-06-06 04:21:37.587815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f65b791ad74b'
down_revision: Union[str, Sequence[str], None] = '7ae8b506fa69'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE userrole ADD VALUE 'TEAM_MANAGER'")

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', name='userrole'),
               existing_nullable=False)

    op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('campaign_id', sa.Integer(), nullable=True),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('leader_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['leader_id'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_teams_campaign_id', 'teams', ['campaign_id'], unique=False)
    op.create_index('ix_teams_is_active', 'teams', ['is_active'], unique=False)
    op.create_index('ix_teams_leader_id', 'teams', ['leader_id'], unique=False)
    op.create_index('ix_teams_manager_id', 'teams', ['manager_id'], unique=False)

    op.create_table('employee_team_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_employee_team_assignments_employee_id', 'employee_team_assignments', ['employee_id'], unique=False)
    op.create_index('ix_employee_team_assignments_team_id', 'employee_team_assignments', ['team_id'], unique=False)
    op.create_index('ix_employee_team_assignments_employee_active', 'employee_team_assignments', ['employee_id', 'is_active'], unique=False)
    op.create_index('ix_employee_team_assignments_team_active', 'employee_team_assignments', ['team_id', 'is_active'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_employee_team_assignments_team_active', table_name='employee_team_assignments')
    op.drop_index('ix_employee_team_assignments_employee_active', table_name='employee_team_assignments')
    op.drop_index('ix_employee_team_assignments_team_id', table_name='employee_team_assignments')
    op.drop_index('ix_employee_team_assignments_employee_id', table_name='employee_team_assignments')
    op.drop_table('employee_team_assignments')

    op.drop_index('ix_teams_manager_id', table_name='teams')
    op.drop_index('ix_teams_leader_id', table_name='teams')
    op.drop_index('ix_teams_is_active', table_name='teams')
    op.drop_index('ix_teams_campaign_id', table_name='teams')
    op.drop_table('teams')

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('role',
               existing_type=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', 'TEAM_MANAGER', name='userrole'),
               type_=sa.Enum('AGENT', 'QA', 'ADMIN', 'HR_MANAGER', 'OPS_MANAGER', name='userrole'),
               existing_nullable=False)

