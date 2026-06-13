import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.main import app
from app.models import (
    Employee, UserRole, Campaign, Team, EmployeeTeamAssignment,
    Call, CallStatus, CallOutcome, RoleNote
)
from app.routers.auth import get_current_user
from app.database import SessionLocal
from app.permissions import (
    require_team_leader_access,
    can_view_led_team,
    can_view_led_team_agent,
    can_view_led_team_call
)
from app.services.team_scope import (
    get_led_team_ids,
    get_team_leader_agent_ids,
    is_team_in_leader_scope,
    is_agent_in_leader_scope,
    scope_employee_query_to_team_leader,
    scope_call_query_to_team_leader
)

client = TestClient(app)

# Helper mock users
mock_admin = Employee(
    id=8600,
    name="Admin User",
    email="admin_scope_tl@example.com",
    role=UserRole.ADMIN,
    employee_code="ADM_TL_SCP",
    hashed_password="fake",
    status="active"
)

mock_tl = Employee(
    id=8601,
    name="Team Leader Scoped",
    email="tl_scope_test@example.com",
    role=UserRole.TEAM_LEADER,
    employee_code="TL_SCP",
    hashed_password="fake",
    status="active"
)

mock_tl_other = Employee(
    id=8602,
    name="Team Leader Other",
    email="tl_other_test@example.com",
    role=UserRole.TEAM_LEADER,
    employee_code="TL_OTH",
    hashed_password="fake",
    status="active"
)


def test_require_team_leader_access_allows_roles():
    # Admin and TL should pass
    require_team_leader_access(mock_tl)
    require_team_leader_access(mock_admin)

    # Others should raise 403
    for role in (UserRole.AGENT, UserRole.QA, UserRole.HR_MANAGER, UserRole.OPS_MANAGER, UserRole.TEAM_MANAGER):
        emp = Employee(role=role)
        with pytest.raises(HTTPException) as exc_info:
            require_team_leader_access(emp)
        assert exc_info.value.status_code == 403


def test_team_leader_scoping_helpers():
    db = SessionLocal()
    try:
        # Create campaign
        camp = Campaign(id=8600, name="Sales Camp", evaluation_prompt="Long enough prompt length", color="#123")
        db.add(camp)
        db.commit()

        # Create leaders
        tl1 = Employee(id=8611, name="TL 1", email="tl1@example.com", role=UserRole.TEAM_LEADER, employee_code="TL1", hashed_password="f", status="active")
        tl2 = Employee(id=8612, name="TL 2", email="tl2@example.com", role=UserRole.TEAM_LEADER, employee_code="TL2", hashed_password="f", status="active")
        
        # Create managers
        tm = Employee(id=8613, name="TM 1", email="tm1@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM1", hashed_password="f", status="active")
        
        db.add_all([tl1, tl2, tm])
        db.commit()

        # Create teams
        t1 = Team(id=8621, name="Team 1", campaign_id=camp.id, manager_id=tm.id, leader_id=tl1.id, is_active=True)
        t2 = Team(id=8622, name="Team 2", campaign_id=camp.id, manager_id=tm.id, leader_id=tl2.id, is_active=True)
        t3 = Team(id=8623, name="Inactive Team 3", campaign_id=camp.id, manager_id=tm.id, leader_id=tl1.id, is_active=False)
        db.add_all([t1, t2, t3])
        db.commit()

        # Create agents
        agent1 = Employee(id=8631, name="Agent 1", email="a1@example.com", role=UserRole.AGENT, employee_code="A1", hashed_password="f", status="active")
        agent2 = Employee(id=8632, name="Agent 2", email="a2@example.com", role=UserRole.AGENT, employee_code="A2", hashed_password="f", status="active")
        db.add_all([agent1, agent2])
        db.commit()

        # Assignments
        assign1 = EmployeeTeamAssignment(id=8641, employee_id=agent1.id, team_id=t1.id, is_active=True)
        assign2 = EmployeeTeamAssignment(id=8642, employee_id=agent2.id, team_id=t2.id, is_active=True)
        db.add_all([assign1, assign2])
        db.commit()

        # Test led team ids
        assert get_led_team_ids(db, tl1.id) == [t1.id]
        assert get_led_team_ids(db, tl2.id) == [t2.id]

        # Test led team agents
        assert get_team_leader_agent_ids(db, tl1.id) == [agent1.id]
        assert get_team_leader_agent_ids(db, tl2.id) == [agent2.id]

        # Test team scope check
        assert is_team_in_leader_scope(db, tl1.id, t1.id) is True
        assert is_team_in_leader_scope(db, tl1.id, t2.id) is False
        assert is_team_in_leader_scope(db, tl1.id, t3.id) is False  # inactive

        # Test agent scope check
        assert is_agent_in_leader_scope(db, tl1.id, agent1.id) is True
        assert is_agent_in_leader_scope(db, tl1.id, agent2.id) is False

        # Test query scoping
        eq = scope_employee_query_to_team_leader(db.query(Employee), db, tl1.id)
        assert eq.count() == 1
        assert eq.first().id == agent1.id

    finally:
        db.close()


def test_team_leader_can_view_led_team_dashboard():
    """Verify that a Team Leader can read their own dashboard statistics."""
    db = SessionLocal()
    try:
        # Create setup
        camp = Campaign(id=8700, name="Sales Camp 2", evaluation_prompt="Long enough prompt length", color="#123", type="sales")
        db.add(camp)
        db.commit()

        tl = Employee(id=8701, name="TL 1", email="tl_dash@example.com", role=UserRole.TEAM_LEADER, employee_code="TL_DSH", hashed_password="f", status="active")
        tm = Employee(id=8702, name="TM 1", email="tm_dash@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM_DSH", hashed_password="f", status="active")
        db.add_all([tl, tm])
        db.commit()

        team = Team(id=8711, name="Led Team", campaign_id=camp.id, manager_id=tm.id, leader_id=tl.id, is_active=True)
        db.add(team)
        db.commit()

        agent = Employee(id=8721, name="Agent 1", email="a1_dash@example.com", role=UserRole.AGENT, employee_code="A1_DSH", hashed_password="f", status="active")
        db.add(agent)
        db.commit()

        assign = EmployeeTeamAssignment(id=8731, employee_id=agent.id, team_id=team.id, is_active=True)
        db.add(assign)
        db.commit()

        # Add evaluated call
        call = Call(id=8741, employee_id=agent.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=85.0)
        db.add(call)
        db.commit()

        outcome = CallOutcome(id=8741, call_id=call.id, campaign_type="sales", primary_outcome="Sale Closed", outcome_value=150.0)
        db.add(outcome)
        db.commit()

        # Test request
        app.dependency_overrides[get_current_user] = lambda: tl
        response = client.get("/api/team-leader/dashboard")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["team_count"] == 1
        assert data["agent_count"] == 1
        assert data["average_qa_score"] == 85.0
        assert data["sales"] == 1.0
        assert data["revenue"] == 150.0
        assert data["conversion_rate"] == 100.0
    finally:
        db.close()
        app.dependency_overrides.clear()


def test_team_leader_cannot_view_other_team_agent():
    """Verify that a Team Leader gets 403 when trying to access an out-of-scope agent."""
    db = SessionLocal()
    try:
        camp = Campaign(id=8800, name="Sales Camp 3", evaluation_prompt="Long enough prompt length", color="#123")
        db.add(camp)
        db.commit()

        tl1 = Employee(id=8801, name="TL 1", email="tl1_sc@example.com", role=UserRole.TEAM_LEADER, employee_code="TL1_SC", hashed_password="f", status="active")
        tl2 = Employee(id=8802, name="TL 2", email="tl2_sc@example.com", role=UserRole.TEAM_LEADER, employee_code="TL2_SC", hashed_password="f", status="active")
        tm = Employee(id=8803, name="TM 1", email="tm1_sc@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM1_SC", hashed_password="f", status="active")
        db.add_all([tl1, tl2, tm])
        db.commit()

        t1 = Team(id=8811, name="Led Team 1", campaign_id=camp.id, manager_id=tm.id, leader_id=tl1.id, is_active=True)
        t2 = Team(id=8812, name="Led Team 2", campaign_id=camp.id, manager_id=tm.id, leader_id=tl2.id, is_active=True)
        db.add_all([t1, t2])
        db.commit()

        agent1 = Employee(id=8821, name="Agent 1", email="a1_sc@example.com", role=UserRole.AGENT, employee_code="A1_SC", hashed_password="f", status="active")
        agent2 = Employee(id=8822, name="Agent 2", email="a2_sc@example.com", role=UserRole.AGENT, employee_code="A2_SC", hashed_password="f", status="active")
        db.add_all([agent1, agent2])
        db.commit()

        db.add(EmployeeTeamAssignment(id=8831, employee_id=agent1.id, team_id=t1.id, is_active=True))
        db.add(EmployeeTeamAssignment(id=8832, employee_id=agent2.id, team_id=t2.id, is_active=True))
        db.commit()

        # TL1 logs in
        app.dependency_overrides[get_current_user] = lambda: tl1

        # Retrieve agents (t1 agent is in scope)
        response = client.get(f"/api/team-leader/agents/{agent1.id}")
        assert response.status_code == 200

        # Retrieve out-of-scope agent (agent2) -> should return 403
        response = client.get(f"/api/team-leader/agents/{agent2.id}")
        assert response.status_code == 403

        # Query agents filtered by t2 -> should return 403
        response = client.get(f"/api/team-leader/agents?team_id={t2.id}")
        assert response.status_code == 403

    finally:
        db.close()
        app.dependency_overrides.clear()


def test_team_leader_cannot_view_other_team_call():
    """Verify that a Team Leader gets 403 when trying to access an out-of-scope call."""
    db = SessionLocal()
    try:
        camp = Campaign(id=8900, name="Sales Camp 4", evaluation_prompt="Long enough prompt length", color="#123")
        db.add(camp)
        db.commit()

        tl1 = Employee(id=8901, name="TL 1", email="tl1_call@example.com", role=UserRole.TEAM_LEADER, employee_code="TL1_CL", hashed_password="f", status="active")
        tl2 = Employee(id=8902, name="TL 2", email="tl2_call@example.com", role=UserRole.TEAM_LEADER, employee_code="TL2_CL", hashed_password="f", status="active")
        tm = Employee(id=8903, name="TM 1", email="tm1_call@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM1_CL", hashed_password="f", status="active")
        db.add_all([tl1, tl2, tm])
        db.commit()

        t1 = Team(id=8911, name="Led Team 1", campaign_id=camp.id, manager_id=tm.id, leader_id=tl1.id, is_active=True)
        t2 = Team(id=8912, name="Led Team 2", campaign_id=camp.id, manager_id=tm.id, leader_id=tl2.id, is_active=True)
        db.add_all([t1, t2])
        db.commit()

        agent1 = Employee(id=8921, name="Agent 1", email="a1_call@example.com", role=UserRole.AGENT, employee_code="A1_CL", hashed_password="f", status="active")
        agent2 = Employee(id=8922, name="Agent 2", email="a2_call@example.com", role=UserRole.AGENT, employee_code="A2_CL", hashed_password="f", status="active")
        db.add_all([agent1, agent2])
        db.commit()

        db.add(EmployeeTeamAssignment(id=8931, employee_id=agent1.id, team_id=t1.id, is_active=True))
        db.add(EmployeeTeamAssignment(id=8932, employee_id=agent2.id, team_id=t2.id, is_active=True))
        db.commit()

        # Add evaluated calls
        c1 = Call(id=8941, employee_id=agent1.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=90.0)
        c2 = Call(id=8942, employee_id=agent2.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=92.0)
        db.add_all([c1, c2])
        db.commit()

        # TL1 logs in
        app.dependency_overrides[get_current_user] = lambda: tl1

        # View c1 -> 200
        response = client.get(f"/api/team-leader/calls/{c1.id}")
        assert response.status_code == 200

        # View c2 -> 403
        response = client.get(f"/api/team-leader/calls/{c2.id}")
        assert response.status_code == 403

    finally:
        db.close()
        app.dependency_overrides.clear()


def test_team_leader_cannot_export_raw_data():
    """Verify that a Team Leader is blocked from raw data exports."""
    # Try exporting
    app.dependency_overrides[get_current_user] = lambda: mock_tl
    try:
        response = client.get("/api/export/csv")
        # should fail since require_raw_export_access blocks TEAM_LEADER
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_team_leader_notes_recipient_scope():
    """Verify notes recipient scope restricts TEAM_LEADER to the Team Manager of the selected team context."""
    db = SessionLocal()
    try:
        camp = Campaign(id=9000, name="Sales Camp 5", evaluation_prompt="Long enough prompt length", color="#123")
        db.add(camp)
        db.commit()

        tl = Employee(id=9001, name="TL 1", email="tl_note@example.com", role=UserRole.TEAM_LEADER, employee_code="TL_NT", hashed_password="f", status="active")
        tm = Employee(id=9002, name="TM 1", email="tm_note@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM_NT", hashed_password="f", status="active")
        tm_other = Employee(id=9003, name="TM Other", email="tm_oth@example.com", role=UserRole.TEAM_MANAGER, employee_code="TM_OTH", hashed_password="f", status="active")
        
        db.add_all([tl, tm, tm_other])
        db.commit()

        team = Team(id=9011, name="Led Team", campaign_id=camp.id, manager_id=tm.id, leader_id=tl.id, is_active=True)
        db.add(team)
        db.commit()

        # Authenticate TL
        app.dependency_overrides[get_current_user] = lambda: tl

        # 1. Test get allowed note recipients for team context
        # should return only tm (id=9002)
        response = client.get(f"/api/notes/recipients?note_type=GENERAL&team_id={team.id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        recipients = response.json()
        assert len(recipients) == 1
        assert recipients[0]["id"] == tm.id

        # 2. Test validate note creation: trying to send to tm_other (id=9003) -> 400 Bad Request
        payload = {
            "recipient_id": tm_other.id,
            "title": "A Note",
            "body": "Hello",
            "note_type": "GENERAL",
            "team_id": team.id
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 400

        # Sending to tm (id=9002) -> 200 OK
        payload["recipient_id"] = tm.id
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 200

    finally:
        db.close()
        app.dependency_overrides.clear()
