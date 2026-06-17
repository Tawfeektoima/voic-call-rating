"""backfill interview role permissions

Revision ID: f14e0a5c8b32
Revises: f13d9c4b7a21
Create Date: 2026-06-14 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f14e0a5c8b32"
down_revision: Union[str, Sequence[str], None] = "f13d9c4b7a21"
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
    "hr.interviews.jobs.manage",
    "hr.interviews.candidates.view",
    "hr.interviews.candidates.manage",
    "hr.interviews.evaluations.review",
    "hr.interviews.candidates.convert",
    "hr.interviews.export",
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
        "hr.dashboard.view",
        "hr.onboarding.manage",
        "employees.view",
        "employees.manage",
        "employees.change_role",
        "employees.change_status",
        "hr.interviews.jobs.manage",
        "hr.interviews.candidates.view",
        "hr.interviews.candidates.manage",
        "hr.interviews.evaluations.review",
        "hr.interviews.candidates.convert",
        "hr.interviews.export",
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
        "exports.run",
        "notes.view",
    ],
    "OPS_MANAGER": [
        "ops.reports.view",
        "notes.view",
    ],
    "ADMIN": PERMISSIONS,
}


def _permission_description(permission_key: str) -> str:
    return permission_key.replace("_", " ").replace(".", " ")


def upgrade() -> None:
    bind = op.get_bind()

    for permission in PERMISSIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO app_permissions (key, description, is_active)
                SELECT :key, :description, :is_active
                WHERE NOT EXISTS (
                    SELECT 1 FROM app_permissions WHERE key = :key
                )
                """
            ),
            {
                "key": permission,
                "description": _permission_description(permission),
                "is_active": True,
            },
        )

    for role, permissions in ROLE_PERMISSIONS.items():
        for permission in permissions:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role, permission_id)
                    SELECT :role, app_permissions.id
                    FROM app_permissions
                    WHERE app_permissions.key = :permission
                      AND NOT EXISTS (
                          SELECT 1
                          FROM role_permissions
                          WHERE role_permissions.role = :role
                            AND role_permissions.permission_id = app_permissions.id
                      )
                    """
                ),
                {"role": role, "permission": permission},
            )


def downgrade() -> None:
    bind = op.get_bind()

    interview_permissions = [
        "hr.interviews.jobs.manage",
        "hr.interviews.candidates.view",
        "hr.interviews.candidates.manage",
        "hr.interviews.evaluations.review",
        "hr.interviews.candidates.convert",
        "hr.interviews.export",
    ]

    for permission in interview_permissions:
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM app_permissions WHERE key = :permission
                )
                """
            ),
            {"permission": permission},
        )
        bind.execute(
            sa.text("DELETE FROM app_permissions WHERE key = :permission"),
            {"permission": permission},
        )
