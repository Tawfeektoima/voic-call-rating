import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import Employee, UserRole, AuditEvent, Call, Campaign, CampaignType, CampaignStatus, ScoreOverrideAudit
from app.routers.auth import get_current_user

client = TestClient(app)

def cleanup_db():
    db: Session = SessionLocal()
    try:
        db.query(Employee).filter(Employee.email.like("test_audit_%")).delete(synchronize_session=False)
        db.query(AuditEvent).delete(synchronize_session=False)
        
        # Clean up related ScoreOverrideAudit records to prevent database pollution
        test_calls = db.query(Call).filter(Call.original_filename.like("test_audit_%")).all()
        test_call_ids = [c.id for c in test_calls]
        if test_call_ids:
            db.query(ScoreOverrideAudit).filter(ScoreOverrideAudit.call_id.in_(test_call_ids)).delete(synchronize_session=False)
        
        # Clean up any orphaned override audits from previous runs
        db.query(ScoreOverrideAudit).filter(~ScoreOverrideAudit.call_id.in_(db.query(Call.id))).delete(synchronize_session=False)

        db.query(Call).filter(Call.original_filename.like("test_audit_%")).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.name.like("test_audit_%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()

@pytest.fixture(autouse=True)
def setup_teardown():
    cleanup_db()
    yield
    cleanup_db()

def test_role_and_status_changes_generate_audit_events():
    """Verify that updating role or status produces corresponding AuditEvent records."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    db: Session = SessionLocal()
    try:
        user = Employee(
            name="Test Audit Target",
            email="test_audit_target@example.com",
            role=UserRole.AGENT,
            employee_code="AUDIT_TARGET",
            status="active",
            hashed_password="fake"
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    # Update role to QA
    response = client.put(f"/api/admin/employees/{user_id}", json={"role": "qa"})
    assert response.status_code == 200

    # Update status to suspended
    response = client.put(f"/api/admin/employees/{user_id}", json={"status": "suspended"})
    assert response.status_code == 200

    # Query audits
    audits_response = client.get("/api/admin/audits")
    assert audits_response.status_code == 200
    audits = audits_response.json()
    assert len(audits) == 2

    # Verify role change audit details
    role_audit = next(a for a in audits if a["action"] == "ROLE_CHANGE")
    assert role_audit["actor_email"] == "test_audit_admin@example.com"
    assert "test_audit_target@example.com" in role_audit["target"]
    assert role_audit["before_state"] == "AGENT"
    assert role_audit["after_state"] == "QA"

    # Verify status change audit details
    status_audit = next(a for a in audits if a["action"] == "STATUS_CHANGE")
    assert status_audit["actor_email"] == "test_audit_admin@example.com"
    assert "test_audit_target@example.com" in status_audit["target"]
    assert status_audit["before_state"] == "active"
    assert status_audit["after_state"] == "suspended"
    assert status_audit["success"] is True

    app.dependency_overrides.clear()

def test_registration_generates_audit_event():
    """Verify that admin-assisted user registration is audited."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Test Audit Registrant",
            "email": "test_audit_register@example.com",
            "password": "password123",
            "role": "AGENT"
        }
    )
    assert response.status_code == 200

    audits_response = client.get("/api/admin/audits")
    assert audits_response.status_code == 200
    audits = audits_response.json()
    register_audit = next(a for a in audits if a["action"] == "REGISTER")
    assert register_audit["actor_email"] == "test_audit_admin@example.com"
    assert "test_audit_register@example.com" in register_audit["target"]
    assert register_audit["success"] is True

    app.dependency_overrides.clear()

def test_score_override_generates_audit_event():
    """Verify that overriding a score produces a SCORE_OVERRIDE audit event."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    db: Session = SessionLocal()
    try:
        campaign = Campaign(
            name="test_audit_campaign",
            type=CampaignType.CUSTOMER_SERVICE,
            status=CampaignStatus.ACTIVE,
            evaluation_prompt="Some evaluation prompt"
        )
        db.add(campaign)
        db.commit()

        agent = Employee(
            name="Test Audit Agent",
            email="test_audit_agent_user@example.com",
            role=UserRole.AGENT,
            employee_code="AUDIT_AGENT",
            status="active",
            hashed_password="fake"
        )
        db.add(agent)
        db.commit()

        call = Call(
            employee_id=agent.id,
            campaign_id=campaign.id,
            audio_file_path="fake/path/test_audit_call.wav",
            original_filename="test_audit_call.wav",
            evaluation_score=85.0,
            status="evaluated"
        )
        db.add(call)
        db.commit()
        call_id = call.id
    finally:
        db.close()

    # Override score
    response = client.patch(
        f"/api/audio/{call_id}/review",
        json={"overridden_score": 90.0, "reviewer_notes": "Great performance", "reason": "Better objection handling"}
    )
    assert response.status_code == 200

    # Query audits
    audits_response = client.get("/api/admin/audits")
    assert audits_response.status_code == 200
    audits = audits_response.json()
    assert len(audits) == 1
    
    score_audit = audits[0]
    assert score_audit["action"] == "SCORE_OVERRIDE"
    assert score_audit["actor_email"] == "test_audit_admin@example.com"
    assert f"Call #{call_id}" in score_audit["target"]
    assert score_audit["before_state"] == "85.0"
    assert score_audit["after_state"] == "90.0"
    assert score_audit["reason"] == "Better objection handling"
    assert score_audit["success"] is True

    app.dependency_overrides.clear()

def test_export_action_generates_audit_event():
    """Verify that executing a data export produces an EXPORT audit event."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    # Perform CSV export
    response = client.get("/api/export/csv")
    assert response.status_code == 200

    # Query audits
    audits_response = client.get("/api/admin/audits")
    assert audits_response.status_code == 200
    audits = audits_response.json()
    assert len(audits) == 1
    
    export_audit = audits[0]
    assert export_audit["action"] == "EXPORT"
    assert export_audit["actor_email"] == "test_audit_admin@example.com"
    assert export_audit["target"] == "CSV Export"
    assert export_audit["success"] is True

    app.dependency_overrides.clear()

def test_denied_export_attempt_generates_audit_event():
    """Verify that denied export attempts are written to the audit trail."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9902,
        name="Mock Agent Auditor",
        email="test_audit_agent@example.com",
        role=UserRole.AGENT,
        employee_code="TEST_AUDIT_AGENT",
        status="active",
        hashed_password="fake"
    )

    response = client.get("/api/export/csv?department=Sales")
    assert response.status_code == 403

    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    audits_response = client.get("/api/admin/audits")
    assert audits_response.status_code == 200
    audits = audits_response.json()
    assert len(audits) == 1
    audit = audits[0]
    assert audit["action"] == "EXPORT"
    assert audit["actor_email"] == "test_audit_agent@example.com"
    assert audit["target"] == "CSV Export"
    assert audit["success"] is False
    assert "Department: Sales" in audit["after_state"]

    app.dependency_overrides.clear()

def test_audit_logs_immutability():
    """Verify that audit records are append-only and cannot be deleted or updated."""
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=9901,
        name="Mock Admin Auditor",
        email="test_audit_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="TEST_AUDIT_ADMIN",
        status="active",
        hashed_password="fake"
    )

    # PUT on /audits should fail
    response_put = client.put("/api/admin/audits", json={})
    assert response_put.status_code == 405  # Method Not Allowed

    # DELETE on /audits should fail
    response_delete = client.delete("/api/admin/audits")
    assert response_delete.status_code == 405  # Method Not Allowed

    # DELETE on individual audit event ID should fail with 404 (does not exist)
    response_delete_id = client.delete("/api/admin/audits/1")
    assert response_delete_id.status_code == 404

    app.dependency_overrides.clear()
