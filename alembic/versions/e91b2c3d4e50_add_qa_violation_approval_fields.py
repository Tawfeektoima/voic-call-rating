"""add qa violation approval fields

Revision ID: e91b2c3d4e50
Revises: e89a1b2c3d40
Create Date: 2026-06-14 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e91b2c3d4e50"
down_revision: Union[str, Sequence[str], None] = "e89a1b2c3d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("agent_violations") as batch_op:
        batch_op.add_column(sa.Column("qa_approved", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("qa_approved_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("qa_approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("qa_approval_note", sa.Text(), nullable=True))
        batch_op.create_index("ix_agent_violations_qa_approved", ["qa_approved"], unique=False)
        batch_op.create_index("ix_agent_violations_qa_approved_by_id", ["qa_approved_by_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_agent_violations_qa_approved_by_id_employees",
            "employees",
            ["qa_approved_by_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_violations") as batch_op:
        batch_op.drop_constraint("fk_agent_violations_qa_approved_by_id_employees", type_="foreignkey")
        batch_op.drop_index("ix_agent_violations_qa_approved_by_id")
        batch_op.drop_index("ix_agent_violations_qa_approved")
        batch_op.drop_column("qa_approval_note")
        batch_op.drop_column("qa_approved_at")
        batch_op.drop_column("qa_approved_by_id")
        batch_op.drop_column("qa_approved")
