"""add qa scope to employees

Revision ID: e92c3d4e5f60
Revises: e91b2c3d4e50
Create Date: 2026-06-14 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e92c3d4e5f60"
down_revision: Union[str, Sequence[str], None] = "e91b2c3d4e50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.add_column(sa.Column("qa_scope_team_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("qa_scope_campaign_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_employees_qa_scope_team_id", ["qa_scope_team_id"], unique=False)
        batch_op.create_index("ix_employees_qa_scope_campaign_id", ["qa_scope_campaign_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_employees_qa_scope_team_id_teams",
            "teams",
            ["qa_scope_team_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_employees_qa_scope_campaign_id_campaigns",
            "campaigns",
            ["qa_scope_campaign_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("employees") as batch_op:
        batch_op.drop_constraint("fk_employees_qa_scope_campaign_id_campaigns", type_="foreignkey")
        batch_op.drop_constraint("fk_employees_qa_scope_team_id_teams", type_="foreignkey")
        batch_op.drop_index("ix_employees_qa_scope_campaign_id")
        batch_op.drop_index("ix_employees_qa_scope_team_id")
        batch_op.drop_column("qa_scope_campaign_id")
        batch_op.drop_column("qa_scope_team_id")
