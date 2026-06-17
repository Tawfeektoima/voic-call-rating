from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import AuditEvent, Call, Campaign, Employee, EmployeeTeamAssignment, Team, UserRole, CallStatus
from app.routers.auth import get_current_user


client = TestClient(app)

IDS = {
    "campaign_a": 97500,
    "campaign_b": 97501,
    "team_a": 97510,
    "team_b": 97511,
    "admin": 97520,
    "qa": 97521,
    "agent_a": 97530,
    "agent_b": 97531,
    "call_a": 97540,
    "call_b": 97541,
    "call_out_of_campaign": 97542,
    "assign_a": 97550,
    "assign_b": 97551,
}


def cleanup_fixture():
    db: Session = SessionLocal()
    try:
        db.query(AuditEvent).filter(
            AuditEvent.action == "QA_SCOPE_ASSIGNMENT_CHANGE",
            AuditEvent.target == "Employee test_qa_scope@example.com (ID: 97521)",
        ).delete(synchronize_session=False)
        db.query(Call).filter(Call.id.in_([IDS["call_a"], IDS["call_b"], IDS["call_out_of_campaign"]])).delete(synchronize_session=False)
        db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id.in_([IDS["assign_a"], IDS["assign_b"]])).delete(synchronize_session=False)
        db.query(Team).filter(Team.id.in_([IDS["team_a"], IDS["team_b"]])).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.id.in_([IDS["campaign_a"], IDS["campaign_b"]])).delete(synchronize_session=False)
        db.query(Employee).filter(Employee.id.in_([IDS["admin"], IDS["qa"], IDS["agent_a"], IDS["agent_b"]])).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_teardown():
    cleanup_fixture()
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()
    cleanup_fixture()


def seed_fixture():
    db: Session = SessionLocal()
    try:
        campaign_a = Campaign(id=IDS["campaign_a"], name="QA Scope Campaign A", evaluation_prompt="Prompt long enough for QA scope fixture", color="#111827")
        campaign_b = Campaign(id=IDS["campaign_b"], name="QA Scope Campaign B", evaluation_prompt="Prompt long enough for QA scope fixture B", color="#1f2937")
        team_a = Team(id=IDS["team_a"], name="QA Team A", campaign_id=campaign_a.id, is_active=True)
        team_b = Team(id=IDS["team_b"], name="QA Team B", campaign_id=campaign_b.id, is_active=True)
        admin = Employee(
            id=IDS["admin"],
            name="Scope Admin",
            email="test_qa_scope_admin@example.com",
            role=UserRole.ADMIN,
            employee_code="QA_SCOPE_ADMIN",
            hashed_password="fake",
            status="active",
        )
        qa = Employee(
            id=IDS["qa"],
            name="Scoped QA",
            email="test_qa_scope@example.com",
            role=UserRole.QA,
            employee_code="QA_SCOPE_QA",
            hashed_password="fake",
            status="active",
        )
        agent_a = Employee(
            id=IDS["agent_a"],
            name="Scoped Agent A",
            email="test_qa_scope_agent_a@example.com",
            role=UserRole.AGENT,
            employee_code="QA_SCOPE_A",
            hashed_password="fake",
            status="active",
        )
        agent_b = Employee(
            id=IDS["agent_b"],
            name="Scoped Agent B",
            email="test_qa_scope_agent_b@example.com",
            role=UserRole.AGENT,
            employee_code="QA_SCOPE_B",
            hashed_password="fake",
            status="active",
        )
        assign_a = EmployeeTeamAssignment(id=IDS["assign_a"], employee_id=agent_a.id, team_id=team_a.id, is_active=True)
        assign_b = EmployeeTeamAssignment(id=IDS["assign_b"], employee_id=agent_b.id, team_id=team_b.id, is_active=True)
        call_a = Call(
            id=IDS["call_a"],
            employee_id=agent_a.id,
            campaign_id=campaign_a.id,
            status=CallStatus.EVALUATED,
            original_filename="qa_scope_call_a.wav",
            created_at=datetime(2026, 6, 10, 9, 0, tzinfo=timezone.utc),
        )
        call_b = Call(
            id=IDS["call_b"],
            employee_id=agent_b.id,
            campaign_id=campaign_b.id,
            status=CallStatus.EVALUATED,
            original_filename="qa_scope_call_b.wav",
            created_at=datetime(2026, 6, 10, 10, 0, tzinfo=timezone.utc),
        )
        call_out_of_campaign = Call(
            id=IDS["call_out_of_campaign"],
            employee_id=agent_a.id,
            campaign_id=campaign_b.id,
            status=CallStatus.EVALUATED,
            original_filename="qa_scope_call_other_campaign.wav",
            created_at=datetime(2026, 6, 10, 11, 0, tzinfo=timezone.utc),
        )

        db.add_all([campaign_a, campaign_b, team_a, team_b, admin, qa, agent_a, agent_b, assign_a, assign_b, call_a, call_b, call_out_of_campaign])
        db.commit()
        return {
            "campaign_a": campaign_a.id,
            "campaign_b": campaign_b.id,
            "team_a": team_a.id,
            "team_b": team_b.id,
            "qa": qa.id,
            "agent_a": agent_a.id,
            "agent_b": agent_b.id,
            "call_a": call_a.id,
            "call_b": call_b.id,
            "call_out_of_campaign": call_out_of_campaign.id,
        }
    finally:
        db.close()


def _as_admin():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=IDS["admin"],
        name="Scope Admin",
        email="test_qa_scope_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="QA_SCOPE_ADMIN",
        hashed_password="fake",
        status="active",
    )


def _as_qa():
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=IDS["qa"],
        name="Scoped QA",
        email="test_qa_scope@example.com",
        role=UserRole.QA,
        employee_code="QA_SCOPE_QA",
        hashed_password="fake",
        status="active",
    )


def test_admin_can_assign_qa_scope_and_it_is_audited():
    fixture = seed_fixture()
    _as_admin()

    response = client.put(
        f"/api/admin/employees/{fixture['qa']}/qa-scope",
        json={"team_id": fixture["team_a"], "campaign_id": fixture["campaign_a"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["qa_scope_team_id"] == fixture["team_a"]
    assert body["qa_scope_campaign_id"] == fixture["campaign_a"]

    db: Session = SessionLocal()
    try:
        qa = db.query(Employee).filter(Employee.id == fixture["qa"]).first()
        assert qa is not None
        assert qa.qa_scope_team_id == fixture["team_a"]
        assert qa.qa_scope_campaign_id == fixture["campaign_a"]

        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "QA_SCOPE_ASSIGNMENT_CHANGE",
            AuditEvent.target == f"Employee {qa.email} (ID: {qa.id})",
        ).first()
        assert audit is not None
        assert audit.actor_id == IDS["admin"]
    finally:
        db.close()


def test_qa_only_sees_calls_within_assigned_team_and_campaign():
    fixture = seed_fixture()
    _as_admin()
    assign_response = client.put(
        f"/api/admin/employees/{fixture['qa']}/qa-scope",
        json={"team_id": fixture["team_a"], "campaign_id": fixture["campaign_a"]},
    )
    assert assign_response.status_code == 200

    _as_qa()
    response = client.get("/api/analytics/search")
    assert response.status_code == 200
    data = response.json()
    assert {row["id"] for row in data} == {fixture["call_a"]}


def test_qa_cannot_open_call_outside_scope():
    fixture = seed_fixture()
    _as_admin()
    assign_response = client.put(
        f"/api/admin/employees/{fixture['qa']}/qa-scope",
        json={"team_id": fixture["team_a"], "campaign_id": fixture["campaign_a"]},
    )
    assert assign_response.status_code == 200

    _as_qa()
    allowed = client.get(f"/api/audio/{fixture['call_a']}")
    assert allowed.status_code == 200

    blocked = client.get(f"/api/audio/{fixture['call_b']}")
    assert blocked.status_code == 403

    blocked_other_campaign = client.get(f"/api/audio/{fixture['call_out_of_campaign']}")
    assert blocked_other_campaign.status_code == 403


def test_qa_cannot_view_agent_profile_outside_team_scope():
    fixture = seed_fixture()
    _as_admin()
    assign_response = client.put(
        f"/api/admin/employees/{fixture['qa']}/qa-scope",
        json={"team_id": fixture["team_a"], "campaign_id": fixture["campaign_a"]},
    )
    assert assign_response.status_code == 200

    _as_qa()
    allowed = client.get(f"/api/analytics/agents/{fixture['agent_a']}")
    assert allowed.status_code == 200

    blocked = client.get(f"/api/analytics/agents/{fixture['agent_b']}")
    assert blocked.status_code == 403
