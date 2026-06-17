from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.models import (
    AgentViolation,
    AuditEvent,
    Call,
    Campaign,
    Employee,
    EmployeeTeamAssignment,
    Team,
    UserRole,
)
from app.routers.auth import get_current_user


client = TestClient(app)

FIXTURE_IDS = {
    "campaign": 97200,
    "team_alpha": 97201,
    "team_beta": 97202,
    "hr_user": 97210,
    "qa_user": 97211,
    "agent_alpha": 97220,
    "agent_beta": 97221,
    "call_alpha": 97230,
    "call_beta": 97231,
    "violation_alpha": 97240,
    "violation_beta": 97241,
    "assignment_alpha_old": 97250,
    "assignment_alpha_new": 97251,
    "assignment_beta": 97252,
}


def cleanup_fixture() -> None:
    db: Session = SessionLocal()
    try:
        db.query(AuditEvent).filter(
            AuditEvent.action == "HR_VIOLATION_APPROVE",
            AuditEvent.target.in_(["Violation #97240", "Violation #97241"]),
        ).delete(synchronize_session=False)
        db.query(AgentViolation).filter(AgentViolation.id.in_([FIXTURE_IDS["violation_alpha"], FIXTURE_IDS["violation_beta"]])).delete(synchronize_session=False)
        db.query(Call).filter(Call.id.in_([FIXTURE_IDS["call_alpha"], FIXTURE_IDS["call_beta"]])).delete(synchronize_session=False)
        db.query(EmployeeTeamAssignment).filter(
            EmployeeTeamAssignment.id.in_([
                FIXTURE_IDS["assignment_alpha_old"],
                FIXTURE_IDS["assignment_alpha_new"],
                FIXTURE_IDS["assignment_beta"],
            ])
        ).delete(synchronize_session=False)
        db.query(Team).filter(Team.id.in_([FIXTURE_IDS["team_alpha"], FIXTURE_IDS["team_beta"]])).delete(synchronize_session=False)
        db.query(Campaign).filter(Campaign.id == FIXTURE_IDS["campaign"]).delete(synchronize_session=False)
        db.query(Employee).filter(
            Employee.id.in_([
                FIXTURE_IDS["hr_user"],
                FIXTURE_IDS["qa_user"],
                FIXTURE_IDS["agent_alpha"],
                FIXTURE_IDS["agent_beta"],
            ])
        ).delete(synchronize_session=False)
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


def seed_violation_fixture() -> dict[str, int]:
    db: Session = SessionLocal()
    try:
        campaign = Campaign(
            id=FIXTURE_IDS["campaign"],
            name="HR Scope Campaign",
            evaluation_prompt="Prompt long enough for validation checks",
            color="#1f2937",
        )
        team_alpha = Team(id=FIXTURE_IDS["team_alpha"], name="Alpha Team", campaign_id=campaign.id, is_active=True)
        team_beta = Team(id=FIXTURE_IDS["team_beta"], name="Beta Team", campaign_id=campaign.id, is_active=True)

        hr_user = Employee(
            id=FIXTURE_IDS["hr_user"],
            name="HR Approver",
            email="test_hr_scope_approver@example.com",
            role=UserRole.HR_MANAGER,
            employee_code="HR_SCOPE_APPROVER",
            hashed_password="fake",
            status="active",
        )
        qa_user = Employee(
            id=FIXTURE_IDS["qa_user"],
            name="QA Viewer",
            email="test_hr_scope_qa@example.com",
            role=UserRole.QA,
            employee_code="HR_SCOPE_QA",
            hashed_password="fake",
            status="active",
        )
        agent_alpha = Employee(
            id=FIXTURE_IDS["agent_alpha"],
            name="Agent Alpha",
            email="test_hr_scope_agent_alpha@example.com",
            role=UserRole.AGENT,
            employee_code="HR_SCOPE_A",
            hashed_password="fake",
            status="active",
        )
        agent_beta = Employee(
            id=FIXTURE_IDS["agent_beta"],
            name="Agent Beta",
            email="test_hr_scope_agent_beta@example.com",
            role=UserRole.AGENT,
            employee_code="HR_SCOPE_B",
            hashed_password="fake",
            status="active",
        )

        call_alpha = Call(
            id=FIXTURE_IDS["call_alpha"],
            employee_id=agent_alpha.id,
            campaign_id=campaign.id,
            status="evaluated",
            original_filename="test_hr_scope_alpha.wav",
            created_at=datetime(2026, 6, 1, 11, 0, tzinfo=timezone.utc),
        )
        call_beta = Call(
            id=FIXTURE_IDS["call_beta"],
            employee_id=agent_beta.id,
            campaign_id=campaign.id,
            status="evaluated",
            original_filename="test_hr_scope_beta.wav",
            created_at=datetime(2026, 6, 5, 9, 0, tzinfo=timezone.utc),
        )

        assignments = [
            EmployeeTeamAssignment(
                id=FIXTURE_IDS["assignment_alpha_old"],
                employee_id=agent_alpha.id,
                team_id=team_alpha.id,
                assigned_at=datetime(2026, 5, 1, 8, 0, tzinfo=timezone.utc),
                ended_at=datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc),
                is_active=False,
            ),
            EmployeeTeamAssignment(
                id=FIXTURE_IDS["assignment_alpha_new"],
                employee_id=agent_alpha.id,
                team_id=team_beta.id,
                assigned_at=datetime(2026, 6, 3, 8, 0, tzinfo=timezone.utc),
                is_active=True,
            ),
            EmployeeTeamAssignment(
                id=FIXTURE_IDS["assignment_beta"],
                employee_id=agent_beta.id,
                team_id=team_beta.id,
                assigned_at=datetime(2026, 5, 15, 8, 0, tzinfo=timezone.utc),
                is_active=True,
            ),
        ]

        violations = [
            AgentViolation(
                id=FIXTURE_IDS["violation_alpha"],
                employee_id=agent_alpha.id,
                call_id=call_alpha.id,
                campaign_id=campaign.id,
                violation_id="late_disclosure",
                severity="high",
                occurrence=1,
                penalty_tier="1 HR",
                score_deduction=10.0,
                hr_flagged=True,
                qa_approved=True,
                qa_approved_by_id=hr_user.id,
                qa_approved_at=datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc),
                hr_approved=False,
                evidence="Alpha historical team violation",
                created_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
            ),
            AgentViolation(
                id=FIXTURE_IDS["violation_beta"],
                employee_id=agent_beta.id,
                call_id=call_beta.id,
                campaign_id=campaign.id,
                violation_id="script_skip",
                severity="medium",
                occurrence=2,
                penalty_tier="Warning",
                score_deduction=4.0,
                hr_flagged=True,
                qa_approved=False,
                hr_approved=False,
                evidence="Beta active team violation",
                created_at=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
            ),
        ]

        db.add_all([
            campaign,
            team_alpha,
            team_beta,
            hr_user,
            qa_user,
            agent_alpha,
            agent_beta,
            call_alpha,
            call_beta,
            *assignments,
            *violations,
        ])
        db.commit()
        return {
            "team_alpha": team_alpha.id,
            "team_beta": team_beta.id,
            "violation_alpha": violations[0].id,
            "violation_beta": violations[1].id,
            "agent_alpha": agent_alpha.id,
        }
    finally:
        db.close()


def test_pending_violations_team_filter_uses_violation_time_assignment():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["hr_user"],
        name="HR Approver",
        email="test_hr_scope_approver@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="HR_SCOPE_APPROVER",
        hashed_password="fake",
        status="active",
    )

    alpha_response = client.get(f"/api/hr/violations/pending?team_id={fixture['team_alpha']}")
    assert alpha_response.status_code == 200
    alpha_data = alpha_response.json()
    assert len(alpha_data) == 1
    assert alpha_data[0]["violation_id"] == fixture["violation_alpha"]
    assert alpha_data[0]["team_id"] == fixture["team_alpha"]

    beta_response = client.get(f"/api/hr/violations/pending?team_id={fixture['team_beta']}")
    assert beta_response.status_code == 200
    beta_data = beta_response.json()
    assert beta_data == []


def test_qa_pending_queue_only_shows_items_not_yet_approved_by_quality():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["qa_user"],
        name="QA Viewer",
        email="test_hr_scope_qa@example.com",
        role=UserRole.QA,
        employee_code="HR_SCOPE_QA",
        hashed_password="fake",
        qa_scope_team_id=fixture["team_beta"],
        status="active",
    )

    response = client.get(f"/api/hr/violations/qa-pending?team_id={fixture['team_beta']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["violation_id"] == fixture["violation_beta"]


def test_violation_summary_team_filter_excludes_agents_moved_after_violation():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["hr_user"],
        name="HR Approver",
        email="test_hr_scope_approver@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="HR_SCOPE_APPROVER",
        hashed_password="fake",
        status="active",
    )

    response = client.get(f"/api/hr/violations/summary?team_id={fixture['team_beta']}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_name"] == "Agent Beta"
    assert data[0]["hr_flagged_count"] == 0


def test_hr_can_approve_violation_and_audit_is_recorded():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["hr_user"],
        name="HR Approver",
        email="test_hr_scope_approver@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="HR_SCOPE_APPROVER",
        hashed_password="fake",
        status="active",
    )

    response = client.patch(
        f"/api/hr/violations/{fixture['violation_alpha']}/approve",
        json={"note": "Approved after HR review"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hr_approved"] is True
    assert body["hr_approved_by_id"] == FIXTURE_IDS["hr_user"]
    assert body["hr_approval_note"] == "Approved after HR review"

    pending_response = client.get(f"/api/hr/violations/pending?team_id={fixture['team_alpha']}")
    assert pending_response.status_code == 200
    assert pending_response.json() == []

    db: Session = SessionLocal()
    try:
        violation = db.query(AgentViolation).filter(AgentViolation.id == fixture["violation_alpha"]).first()
        assert violation is not None
        assert violation.hr_approved is True
        assert violation.hr_approved_at is not None

        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "HR_VIOLATION_APPROVE",
            AuditEvent.target == f"Violation #{fixture['violation_alpha']}",
        ).first()
        assert audit is not None
        assert audit.actor_id == FIXTURE_IDS["hr_user"]
        assert audit.success is True
    finally:
        db.close()


def test_hr_cannot_approve_before_qa_stage():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["hr_user"],
        name="HR Approver",
        email="test_hr_scope_approver@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="HR_SCOPE_APPROVER",
        hashed_password="fake",
        status="active",
    )

    response = client.patch(f"/api/hr/violations/{fixture['violation_beta']}/approve", json={})
    assert response.status_code == 400
    assert response.json()["detail"] == "Violation must be approved by QA first."


def test_qa_can_approve_violation_and_it_moves_to_hr_queue():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["qa_user"],
        name="QA Viewer",
        email="test_hr_scope_qa@example.com",
        role=UserRole.QA,
        employee_code="HR_SCOPE_QA",
        hashed_password="fake",
        qa_scope_team_id=fixture["team_beta"],
        status="active",
    )

    response = client.patch(
        f"/api/hr/violations/{fixture['violation_beta']}/qa-approve",
        json={"note": "Reviewed by quality"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["qa_approved"] is True
    assert body["qa_approved_by_id"] == FIXTURE_IDS["qa_user"]
    assert body["qa_approval_note"] == "Reviewed by quality"

    qa_pending = client.get(f"/api/hr/violations/qa-pending?team_id={fixture['team_beta']}")
    assert qa_pending.status_code == 200
    assert qa_pending.json() == []

    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["hr_user"],
        name="HR Approver",
        email="test_hr_scope_approver@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="HR_SCOPE_APPROVER",
        hashed_password="fake",
        status="active",
    )

    hr_pending = client.get(f"/api/hr/violations/pending?team_id={fixture['team_beta']}")
    assert hr_pending.status_code == 200
    pending_rows = hr_pending.json()
    assert len(pending_rows) == 1
    assert pending_rows[0]["violation_id"] == fixture["violation_beta"]

    db: Session = SessionLocal()
    try:
        audit = db.query(AuditEvent).filter(
            AuditEvent.action == "QA_VIOLATION_APPROVE",
            AuditEvent.target == f"Violation #{fixture['violation_beta']}",
        ).first()
        assert audit is not None
        assert audit.actor_id == FIXTURE_IDS["qa_user"]
    finally:
        db.close()


def test_qa_cannot_approve_violation():
    fixture = seed_violation_fixture()
    app.dependency_overrides[get_current_user] = lambda: Employee(
        id=FIXTURE_IDS["qa_user"],
        name="QA Viewer",
        email="test_hr_scope_qa@example.com",
        role=UserRole.QA,
        employee_code="HR_SCOPE_QA",
        hashed_password="fake",
        qa_scope_team_id=fixture["team_beta"],
        status="active",
    )

    response = client.patch(f"/api/hr/violations/{fixture['violation_beta']}/approve", json={})
    assert response.status_code == 403
