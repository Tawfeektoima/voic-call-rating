"""add hr violation approval fields

Revision ID: e89a1b2c3d40
Revises: e45f6a7b8c90
Create Date: 2026-06-14 20:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e89a1b2c3d40"
down_revision: Union[str, Sequence[str], None] = "e45f6a7b8c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_violations") as batch_op:
        batch_op.add_column(sa.Column("hr_approved", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("hr_approved_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("hr_approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("hr_approval_note", sa.Text(), nullable=True))
        batch_op.create_index("ix_agent_violations_hr_approved", ["hr_approved"], unique=False)
        batch_op.create_index("ix_agent_violations_hr_approved_by_id", ["hr_approved_by_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_agent_violations_hr_approved_by_id_employees",
            "employees",
            ["hr_approved_by_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_violations") as batch_op:
        batch_op.drop_constraint("fk_agent_violations_hr_approved_by_id_employees", type_="foreignkey")
        batch_op.drop_index("ix_agent_violations_hr_approved_by_id")
        batch_op.drop_index("ix_agent_violations_hr_approved")
        batch_op.drop_column("hr_approval_note")
        batch_op.drop_column("hr_approved_at")
        batch_op.drop_column("hr_approved_by_id")
        batch_op.drop_column("hr_approved")
