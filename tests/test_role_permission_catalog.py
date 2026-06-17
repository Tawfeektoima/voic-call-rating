import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import AgentViolation, AppPermission, AuditEvent, Call, CallStatus, Campaign, Employee, RolePermission, UserRole
from app.permissions import ROLE_PERMISSIONS
from app.routers.auth import get_current_user
from app.services.role_permissions import backfill_interview_role_permissions, get_role_permission_values, seed_role_permissions, set_role_permission_values

client = TestClient(app)


def cleanup_permission_tests():
    db: Session = SessionLocal()
    try:
        set_role_permission_values(
            db,
            UserRole.TEAM_MANAGER,
            [permission.value for permission in ROLE_PERMISSIONS[UserRole.TEAM_MANAGER]],
        )
        db.query(AgentViolation).filter(AgentViolation.violation_id.like("test_perm_%")).delete(synchronize_session=False)
        db.query(Call).filter(Call.original_filename.like("test_perm_%")).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.name.like("test_perm_%")).delete(synchronize_session=False)
        db.query(RolePermission).delete(synchronize_session=False)
        db.query(AppPermission).filter(AppPermission.key.like("hr.interviews.%")).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.target.like("Employee test_perm_%")).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.action == "PERMISSION_CHANGE", AuditEvent.target == "Role TEAM_MANAGER").delete(synchronize_session=False)
        db.query(Employee).filter(Employee.email.like("test_perm_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_teardown():
    cleanup_permission_tests()
    yield
    cleanup_permission_tests()
    app.dependency_overrides.clear()


def test_auth_me_returns_role_permissions():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91001,
        name="Permission Agent",
        email="test_perm_agent@example.com",
        role=UserRole.AGENT,
        employee_code="PERM_AGENT",
        hashed_password="fake",
        status="active",
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "AGENT"
    assert "calls.view_own" in data["permissions"]
    assert "employees.change_role" not in data["permissions"]


def test_approved_roles_catalog_marks_admin_not_hr_assignable():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91002,
        name="Permission Admin",
        email="test_perm_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="PERM_ADMIN",
        hashed_password="fake",
        status="active",
    )

    response = client.get("/api/auth/roles")

    assert response.status_code == 200
    roles = {item["role"]: item for item in response.json()}
    assert "AGENT" in roles
    assert "TEAM_LEADER" in roles
    assert "TEAM_MANAGER" in roles
    assert roles["ADMIN"]["assignable_by_hr"] is False
    assert "dashboard.view_own" in roles["AGENT"]["permissions"]


def test_admin_can_update_role_permissions_and_audit_change():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91007,
        name="Permission Admin",
        email="test_perm_permission_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="PERM_ADMIN_PERM",
        hashed_password="fake",
        status="active",
    )

    catalog = client.get("/api/admin/role-permissions")
    assert catalog.status_code == 200
    team_manager = next(item for item in catalog.json()["roles"] if item["role"] == "TEAM_MANAGER")
    assert "notes.view" in team_manager["permissions"]

    updated_permissions = [permission for permission in team_manager["permissions"] if permission != "notes.view"]
    response = client.put(
        "/api/admin/role-permissions/TEAM_MANAGER",
        json={"permissions": updated_permissions, "reason": "test permission governance"},
    )

    assert response.status_code == 200
    assert "notes.view" not in response.json()["permissions"]

    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91008,
        name="Permission Team Manager",
        email="test_perm_tm@example.com",
        role=UserRole.TEAM_MANAGER,
        employee_code="PERM_TM",
        hashed_password="fake",
        status="active",
    )
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert "notes.view" not in me.json()["permissions"]

    db = SessionLocal()
    try:
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "PERMISSION_CHANGE",
            AuditEvent.target == "Role TEAM_MANAGER",
        ).first()
        assert audit is not None
        assert "notes.view" in audit.before_state
        assert "test permission governance" == audit.reason
    finally:
        db.close()


def test_get_role_permission_values_restores_missing_permission_catalog_without_overwriting_custom_role_assignments():
    db: Session = SessionLocal()
    try:
        set_role_permission_values(
            db,
            UserRole.TEAM_MANAGER,
            ["team_manager.workspace.view", "profiles.view_agents"],
        )
        db.query(AppPermission).filter(AppPermission.key.like("hr.interviews.%")).delete(synchronize_session=False)
        db.commit()

        permissions = get_role_permission_values(db, UserRole.TEAM_MANAGER)

        assert "team_manager.workspace.view" in permissions
        assert "profiles.view_agents" in permissions
        assert "notes.view" not in permissions

        restored_keys = {
            item.key
            for item in db.query(AppPermission).filter(AppPermission.key.like("hr.interviews.%")).all()
        }
        assert restored_keys == {
            "hr.interviews.jobs.manage",
            "hr.interviews.candidates.view",
            "hr.interviews.candidates.manage",
            "hr.interviews.evaluations.review",
            "hr.interviews.candidates.convert",
            "hr.interviews.export",
        }
    finally:
        db.close()


def test_backfill_interview_role_permissions_restores_hr_interview_access():
    db: Session = SessionLocal()
    try:
        seed_role_permissions(db)
        db.commit()

        interview_manage = (
            db.query(AppPermission)
            .filter(AppPermission.key == "hr.interviews.jobs.manage")
            .first()
        )
        assert interview_manage is not None

        db.query(RolePermission).filter(
            RolePermission.role == UserRole.HR_MANAGER,
            RolePermission.permission_id == interview_manage.id,
        ).delete(synchronize_session=False)
        db.commit()

        backfill_interview_role_permissions(db)
        db.commit()

        restored = (
            db.query(RolePermission)
            .filter(
                RolePermission.role == UserRole.HR_MANAGER,
                RolePermission.permission_id == interview_manage.id,
            )
            .first()
        )
        assert restored is not None
    finally:
        db.close()


def test_hr_manager_can_update_non_admin_role_but_not_assign_admin():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91003,
        name="Permission HR",
        email="test_perm_hr@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="PERM_HR",
        hashed_password="fake",
        status="active",
    )

    db: Session = SessionLocal()
    try:
        target = Employee(
            name="Permission Target",
            email="test_perm_target@example.com",
            role=UserRole.AGENT,
            employee_code="PERM_TARGET",
            hashed_password="fake",
            status="active",
        )
        db.add(target)
        db.commit()
        target_id = target.id
    finally:
        db.close()

    response = client.put(f"/api/admin/employees/{target_id}", json={"role": "team_leader"})
    assert response.status_code == 200
    assert response.json()["role"] == "TEAM_LEADER"

    denied = client.put(f"/api/admin/employees/{target_id}", json={"role": "admin"})
    assert denied.status_code == 403

    db = SessionLocal()
    try:
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "ROLE_CHANGE",
            AuditEvent.target.like("Employee test_perm_target@example.com%"),
        ).first()
        assert audit is not None
        assert audit.before_state == "AGENT"
        assert audit.after_state == "TEAM_LEADER"
    finally:
        db.close()


def create_agent_violation_fixture(email_suffix: str = "agent") -> int:
    db: Session = SessionLocal()
    try:
        employee = Employee(
            name=f"Permission Violation {email_suffix}",
            email=f"test_perm_violation_{email_suffix}@example.com",
            role=UserRole.AGENT,
            employee_code=f"PERM_VIOL_{email_suffix.upper()}",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name=f"test_perm_campaign_{email_suffix}",
            evaluation_prompt="Test evaluation prompt",
            color="#111111",
        )
        db.add_all([employee, campaign])
        db.commit()
        db.refresh(employee)
        db.refresh(campaign)

        call = Call(
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=CallStatus.EVALUATED,
            audio_file_path=f"test_perm_{email_suffix}.wav",
            original_filename=f"test_perm_{email_suffix}.wav",
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        violation = AgentViolation(
            employee_id=employee.id,
            call_id=call.id,
            campaign_id=campaign.id,
            violation_id=f"test_perm_violation_{email_suffix}",
            severity="high",
            occurrence=1,
            penalty_tier="Warning",
            score_deduction=2.0,
            evidence="Test evidence",
        )
        db.add(violation)
        db.commit()
        return employee.id
    finally:
        db.close()


def test_hr_manager_can_view_agent_violation_history():
    agent_id = create_agent_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91004,
        name="Permission HR Viewer",
        email="test_perm_hr_viewer@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="PERM_HR_VIEW",
        hashed_password="fake",
        status="active",
    )

    response = client.get(f"/api/hr/violations/{agent_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == agent_id
    assert data["total_violations"] == 1
    assert data["violations"][0]["violation_id"] == "test_perm_violation_agent"


def test_hr_manager_permissions_are_limited_to_hr_workflows():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91009,
        name="Permission HR Guardrail",
        email="test_perm_hr_guardrail@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="PERM_HR_GUARD",
        hashed_password="fake",
        status="active",
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    permissions = set(response.json()["permissions"])
    assert "hr.dashboard.view" in permissions
    assert "employees.view" in permissions
    assert "notes.view" in permissions
    assert "campaigns.view" not in permissions
    assert "calls.view_raw" not in permissions
    assert "business_intelligence.view" not in permissions
    assert "data_center.view" not in permissions
    assert "success_library.view" not in permissions
    assert "profiles.view_agents" not in permissions


def test_qa_permissions_are_limited_to_quality_workflows():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91010,
        name="Permission QA Guardrail",
        email="test_perm_qa_guardrail@example.com",
        role=UserRole.QA,
        employee_code="PERM_QA_GUARD",
        hashed_password="fake",
        status="active",
    )

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    permissions = set(response.json()["permissions"])
    assert "dashboard.view_global" in permissions
    assert "calls.view_raw" in permissions
    assert "calls.review" in permissions
    assert "campaigns.view" in permissions
    assert "exports.run" in permissions
    assert "notes.view" in permissions
    assert "hr.dashboard.view" not in permissions
    assert "data_center.view" not in permissions


@pytest.mark.parametrize("role", [UserRole.TEAM_LEADER, UserRole.TEAM_MANAGER, UserRole.OPS_MANAGER])
def test_non_hr_roles_cannot_view_other_agent_violation_history(role: UserRole):
    agent_id = create_agent_violation_fixture(role.value.lower())
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91005,
        name="Permission Non HR Viewer",
        email="test_perm_non_hr_viewer@example.com",
        role=role,
        employee_code="PERM_NON_HR",
        hashed_password="fake",
        status="active",
    )

    response = client.get(f"/api/hr/violations/{agent_id}")

    assert response.status_code == 403


def test_agent_cannot_view_another_agent_violation_history():
    agent_id = create_agent_violation_fixture("target_agent")
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=91006,
        name="Permission Other Agent",
        email="test_perm_other_agent@example.com",
        role=UserRole.AGENT,
        employee_code="PERM_OTHER_AGENT",
        hashed_password="fake",
        status="active",
    )

    response = client.get(f"/api/hr/violations/{agent_id}")

    assert response.status_code == 403
