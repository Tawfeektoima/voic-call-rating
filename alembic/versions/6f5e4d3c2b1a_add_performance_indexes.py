"""add performance indexes

Revision ID: 6f5e4d3c2b1a
Revises: 9d3c5f7a2e11
Create Date: 2026-06-04 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f5e4d3c2b1a"
down_revision: Union[str, Sequence[str], None] = "9d3c5f7a2e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_employees_role", "employees", ["role"], unique=False)
    op.create_index("ix_employees_status", "employees", ["status"], unique=False)
    op.create_index("ix_employees_role_status", "employees", ["role", "status"], unique=False)
    op.create_index("ix_employees_created_at", "employees", ["created_at"], unique=False)

    op.create_index("ix_calls_created_at", "calls", ["created_at"], unique=False)
    op.create_index("ix_calls_employee_created_at", "calls", ["employee_id", "created_at"], unique=False)
    op.create_index("ix_calls_campaign_created_at", "calls", ["campaign_id", "created_at"], unique=False)
    op.create_index("ix_calls_status_created_at", "calls", ["status", "created_at"], unique=False)
    op.create_index("ix_calls_lead_status_created_at", "calls", ["lead_status", "created_at"], unique=False)

    op.create_index("ix_agent_violations_created_at", "agent_violations", ["created_at"], unique=False)
    op.create_index("ix_agent_violations_employee_created_at", "agent_violations", ["employee_id", "created_at"], unique=False)
    op.create_index("ix_agent_violations_violation_created_at", "agent_violations", ["violation_id", "created_at"], unique=False)
    op.create_index("ix_agent_violations_severity_created_at", "agent_violations", ["severity", "created_at"], unique=False)
    op.create_index("ix_agent_violations_hr_flagged_created_at", "agent_violations", ["hr_flagged", "created_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_agent_violations_hr_flagged_created_at", table_name="agent_violations")
    op.drop_index("ix_agent_violations_severity_created_at", table_name="agent_violations")
    op.drop_index("ix_agent_violations_violation_created_at", table_name="agent_violations")
    op.drop_index("ix_agent_violations_employee_created_at", table_name="agent_violations")
    op.drop_index("ix_agent_violations_created_at", table_name="agent_violations")

    op.drop_index("ix_calls_lead_status_created_at", table_name="calls")
    op.drop_index("ix_calls_status_created_at", table_name="calls")
    op.drop_index("ix_calls_campaign_created_at", table_name="calls")
    op.drop_index("ix_calls_employee_created_at", table_name="calls")
    op.drop_index("ix_calls_created_at", table_name="calls")

    op.drop_index("ix_employees_created_at", table_name="employees")
    op.drop_index("ix_employees_role_status", table_name="employees")
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_role", table_name="employees")
