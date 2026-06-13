"""add db backed role permissions

Revision ID: b12c7e9f4a31
Revises: a65b791ad75a
Create Date: 2026-06-13 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b12c7e9f4a31"
down_revision: Union[str, Sequence[str], None] = "a65b791ad75a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    "dashboard.view_own",
    "dashboard.view_global",
    "profile.view_own",
    "profiles.view_agents",
    "calls.view_own",
    "calls.view_raw",
    "calls.upload_own",
    "calls.review",
    "calls.update_leads",
    "campaigns.view",
    "campaigns.manage",
    "success_library.view",
    "business_intelligence.view",
    "data_center.view",
    "hr.dashboard.view",
    "hr.onboarding.manage",
    "employees.view",
    "employees.manage",
    "employees.change_role",
    "employees.change_status",
    "audit.view",
    "exports.run",
    "system.health.view",
    "system.alerts.resolve",
    "ops.reports.view",
    "team_manager.workspace.view",
    "team_leader.workspace.view",
    "notes.view",
    "kpi_thresholds.manage",
]

ROLE_PERMISSIONS = {
    "AGENT": [
        "dashboard.view_own",
        "profile.view_own",
        "calls.view_own",
        "calls.upload_own",
        "success_library.view",
        "notes.view",
    ],
    "TEAM_LEADER": [
        "team_leader.workspace.view",
        "profiles.view_agents",
        "success_library.view",
        "notes.view",
    ],
    "TEAM_MANAGER": [
        "team_manager.workspace.view",
        "profiles.view_agents",
        "notes.view",
    ],
    "HR_MANAGER": [
        "dashboard.view_global",
        "calls.view_raw",
        "calls.review",
        "calls.update_leads",
        "campaigns.view",
        "success_library.view",
        "profiles.view_agents",
        "business_intelligence.view",
        "data_center.view",
        "hr.dashboard.view",
        "hr.onboarding.manage",
        "employees.view",
        "employees.manage",
        "employees.change_role",
        "employees.change_status",
        "exports.run",
        "notes.view",
    ],
    "QA": [
        "dashboard.view_global",
        "calls.view_raw",
        "calls.review",
        "calls.update_leads",
        "campaigns.view",
        "success_library.view",
        "profiles.view_agents",
        "data_center.view",
        "hr.dashboard.view",
        "exports.run",
        "notes.view",
    ],
    "OPS_MANAGER": [
        "ops.reports.view",
        "notes.view",
    ],
    "ADMIN": PERMISSIONS,
}


def upgrade() -> None:
    op.create_table(
        "app_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_app_permissions_id", "app_permissions", ["id"], unique=False)
    op.create_index("ix_app_permissions_key", "app_permissions", ["key"], unique=True)
    op.create_index("ix_app_permissions_is_active", "app_permissions", ["is_active"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["permission_id"], ["app_permissions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role", "permission_id", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_id", "role_permissions", ["id"], unique=False)
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"], unique=False)
    op.create_index("ix_role_permissions_role", "role_permissions", ["role"], unique=False)

    bind = op.get_bind()
    for permission in PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO app_permissions (key, description, is_active) "
                "VALUES (:key, :description, :is_active)"
            ),
            {
                "key": permission,
                "description": permission.replace("_", " ").replace(".", " "),
                "is_active": True,
            },
        )

    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permissions (role, permission_id) "
                    "SELECT :role, id FROM app_permissions WHERE key = :permission"
                ),
                {"role": role, "permission": permission},
            )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_id", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_app_permissions_is_active", table_name="app_permissions")
    op.drop_index("ix_app_permissions_key", table_name="app_permissions")
    op.drop_index("ix_app_permissions_id", table_name="app_permissions")
    op.drop_table("app_permissions")
