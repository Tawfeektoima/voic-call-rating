"""complete role notes schema

Revision ID: c23d4e5f6a78
Revises: b12c7e9f4a31
Create Date: 2026-06-13 23:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c23d4e5f6a78"
down_revision: Union[str, Sequence[str], None] = "b12c7e9f4a31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("role_notes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("visibility", sa.String(length=50), nullable=False, server_default="INTERNAL"))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("deleted_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("delete_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key("fk_role_notes_deleted_by_id_employees", "employees", ["deleted_by_id"], ["id"])

    op.create_index("ix_role_notes_visibility", "role_notes", ["visibility"], unique=False)
    op.create_index("ix_role_notes_deleted_at", "role_notes", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_role_notes_deleted_at", table_name="role_notes")
    op.drop_index("ix_role_notes_visibility", table_name="role_notes")

    with op.batch_alter_table("role_notes", schema=None) as batch_op:
        batch_op.drop_constraint("fk_role_notes_deleted_by_id_employees", type_="foreignkey")
        batch_op.drop_column("delete_reason")
        batch_op.drop_column("deleted_by_id")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("visibility")
