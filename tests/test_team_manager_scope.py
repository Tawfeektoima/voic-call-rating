import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.main import app
from app.models import Employee, UserRole, Campaign, Team, EmployeeTeamAssignment, Call, CallStatus, CallOutcome, AttendanceRecord, CampaignType
from app.routers.auth import get_current_user
from app.database import SessionLocal
from app.permissions import (
    require_team_manager_access,
    can_view_team_reports,
    can_view_team,
    can_view_team_agent,
    can_request_agent_transfer,
    can_view_team_call
)
from app.services.team_scope import (
    get_managed_team_ids,
    get_led_team_ids,
    get_team_manager_agent_ids,
    is_team_in_manager_scope,
    is_agent_in_manager_scope,
    scope_employee_query_to_team_manager,
    scope_call_query_to_team_manager
)

client = TestClient(app)

# Helper mock users
mock_admin = Employee(
    id=8500,
    name="Admin User",
    email="admin_scope_test@example.com",
    role=UserRole.ADMIN,
    employee_code="ADM_SCP",
    hashed_password="fake",
    status="active"
)

mock_tm = Employee(
    id=8501,
    name="Team Manager User",
    email="tm_scope_test@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM_SCP",
    hashed_password="fake",
    status="active"
)

mock_agent = Employee(
    id=8502,
    name="Agent User",
    email="agent_scope_test@example.com",
    role=UserRole.AGENT,
    employee_code="AGT_SCP",
    hashed_password="fake",
    status="active"
)


# Test case 1: require_team_manager_access_allows_team_manager
def test_require_team_manager_access_allows_team_manager():
    # Should not raise any exception
    require_team_manager_access(mock_tm)


# Test case 2: require_team_manager_access_allows_admin
def test_require_team_manager_access_allows_admin():
    # Should not raise any exception
    require_team_manager_access(mock_admin)


# Test case 3: require_team_manager_access_rejects_non_manager_roles
def test_require_team_manager_access_rejects_non_manager_roles():
    for role in (UserRole.AGENT, UserRole.QA, UserRole.HR_MANAGER, UserRole.OPS_MANAGER):
        emp = Employee(role=role)
        with pytest.raises(HTTPException) as exc_info:
            require_team_manager_access(emp)
        assert exc_info.value.status_code == 403


# Test case 4: get_managed_team_ids_returns_only_owned_active_teams
def test_get_managed_team_ids_returns_only_owned_active_teams():
    db = SessionLocal()
    try:
        # Create campaign
        camp = Campaign(id=8500, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        
        # Create active team owned by tm
        t1 = Team(id=8501, name="Active Team 1", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        # Create inactive team owned by tm
        t2 = Team(id=8502, name="Inactive Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=False)
        # Create active team owned by other manager
        t3 = Team(id=8503, name="Active Team Other", campaign_id=camp.id, manager_id=9999, is_active=True)
        db.add_all([t1, t2, t3])
        db.commit()

        team_ids = get_managed_team_ids(db, mock_tm.id)
        assert team_ids == [t1.id]
    finally:
        db.close()


# Test case 5: get_team_manager_agent_ids_returns_only_active_assigned_agents
def test_get_team_manager_agent_ids_returns_only_active_assigned_agents():
    db = SessionLocal()
    try:
        camp = Campaign(id=8510, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        
        t1 = Team(id=8511, name="TM Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        db.add(t1)

        # Create agents
        agent1 = Employee(id=8512, name="Agent 1", email="a1@example.com", role=UserRole.AGENT, employee_code="A1", hashed_password="f", status="active")
        agent2 = Employee(id=8513, name="Agent 2", email="a2@example.com", role=UserRole.AGENT, employee_code="A2", hashed_password="f", status="active")
        agent3 = Employee(id=8514, name="Agent 3", email="a3@example.com", role=UserRole.AGENT, employee_code="A3", hashed_password="f", status="active")
        db.add_all([agent1, agent2, agent3])
        db.commit()

        # Active assignment for agent2 (id=8513) on t1
        assign1 = EmployeeTeamAssignment(id=8511, employee_id=agent2.id, team_id=t1.id, is_active=True)
        # Inactive/historical assignment for agent1 (id=8512) on t1
        assign2 = EmployeeTeamAssignment(id=8512, employee_id=agent1.id, team_id=t1.id, is_active=False)
        # Active assignment for agent3 (id=8514) on another team (not managed)
        t_other = Team(id=8515, name="Other Team", campaign_id=camp.id, manager_id=9999, is_active=True)
        db.add(t_other)
        db.commit()
        assign3 = EmployeeTeamAssignment(id=8513, employee_id=agent3.id, team_id=t_other.id, is_active=True)
        db.add_all([assign1, assign2, assign3])
        db.commit()

        agent_ids = get_team_manager_agent_ids(db, mock_tm.id)
        assert agent_ids == [agent2.id]
    finally:
        db.close()


# Test case 6: is_team_in_manager_scope_true_for_owned_team
def test_is_team_in_manager_scope_true_for_owned_team():
    db = SessionLocal()
    try:
        camp = Campaign(id=8520, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8521, name="Owned Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        db.add(t1)
        db.commit()

        assert is_team_in_manager_scope(db, mock_tm.id, t1.id) is True
    finally:
        db.close()


# Test case 7: is_team_in_manager_scope_false_for_unowned_team
def test_is_team_in_manager_scope_false_for_unowned_team():
    db = SessionLocal()
    try:
        camp = Campaign(id=8530, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8531, name="Unowned Team", campaign_id=camp.id, manager_id=9999, is_active=True)
        t2 = Team(id=8532, name="Owned Inactive", campaign_id=camp.id, manager_id=mock_tm.id, is_active=False)
        db.add_all([t1, t2])
        db.commit()

        assert is_team_in_manager_scope(db, mock_tm.id, t1.id) is False
        assert is_team_in_manager_scope(db, mock_tm.id, t2.id) is False
    finally:
        db.close()


# Test case 8: is_agent_in_manager_scope_true_for_managed_agent
def test_is_agent_in_manager_scope_true_for_managed_agent():
    db = SessionLocal()
    try:
        camp = Campaign(id=8540, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8541, name="Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        agent = Employee(id=8542, name="Agent", email="a@example.com", role=UserRole.AGENT, employee_code="A", hashed_password="f", status="active")
        db.add_all([t1, agent])
        db.commit()

        assign = EmployeeTeamAssignment(id=8541, employee_id=agent.id, team_id=t1.id, is_active=True)
        db.add(assign)
        db.commit()

        assert is_agent_in_manager_scope(db, mock_tm.id, agent.id) is True
    finally:
        db.close()


# Test case 9: is_agent_in_manager_scope_false_for_out_of_scope_agent
def test_is_agent_in_manager_scope_false_for_out_of_scope_agent():
    db = SessionLocal()
    try:
        camp = Campaign(id=8550, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8551, name="Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        agent = Employee(id=8552, name="Agent", email="a@example.com", role=UserRole.AGENT, employee_code="A", hashed_password="f", status="active")
        db.add_all([t1, agent])
        db.commit()

        # Assignment is inactive
        assign = EmployeeTeamAssignment(id=8551, employee_id=agent.id, team_id=t1.id, is_active=False)
        db.add(assign)
        db.commit()

        assert is_agent_in_manager_scope(db, mock_tm.id, agent.id) is False
    finally:
        db.close()


# Test case 10: scope_employee_query_to_team_manager_filters_employees
def test_scope_employee_query_to_team_manager_filters_employees():
    db = SessionLocal()
    try:
        camp = Campaign(id=8560, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8561, name="Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        agent1 = Employee(id=8562, name="Agent 1", email="a1@example.com", role=UserRole.AGENT, employee_code="A1", hashed_password="f", status="active")
        agent2 = Employee(id=8563, name="Agent 2", email="a2@example.com", role=UserRole.AGENT, employee_code="A2", hashed_password="f", status="active")
        db.add_all([t1, agent1, agent2])
        db.commit()

        # Only agent1 is actively assigned
        assign = EmployeeTeamAssignment(id=8561, employee_id=agent1.id, team_id=t1.id, is_active=True)
        db.add(assign)
        db.commit()

        # Query all employees
        base_query = db.query(Employee)
        scoped_query = scope_employee_query_to_team_manager(base_query, db, mock_tm.id)
        results = scoped_query.all()

        assert len(results) == 1
        assert results[0].id == agent1.id
    finally:
        db.close()


# Test case 11: scope_call_query_to_team_manager_filters_calls
def test_scope_call_query_to_team_manager_filters_calls():
    db = SessionLocal()
    try:
        camp = Campaign(id=8570, name="Camp1", evaluation_prompt="Dummy prompt length", color="#FFF")
        db.add(camp)
        t1 = Team(id=8571, name="Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        agent1 = Employee(id=8572, name="Agent 1", email="a1@example.com", role=UserRole.AGENT, employee_code="A1", hashed_password="f", status="active")
        agent2 = Employee(id=8573, name="Agent 2", email="a2@example.com", role=UserRole.AGENT, employee_code="A2", hashed_password="f", status="active")
        db.add_all([t1, agent1, agent2])
        db.commit()

        assign = EmployeeTeamAssignment(id=8571, employee_id=agent1.id, team_id=t1.id, is_active=True)
        db.add(assign)
        db.commit()

        c1 = Call(id=8571, employee_id=agent1.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=90.0, audio_file_path="f1", original_filename="f1")
        c2 = Call(id=8572, employee_id=agent2.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=80.0, audio_file_path="f2", original_filename="f2")
        db.add_all([c1, c2])
        db.commit()

        base_query = db.query(Call)
        scoped_query = scope_call_query_to_team_manager(base_query, db, mock_tm.id)
        results = scoped_query.all()

        assert len(results) == 1
        assert results[0].id == c1.id
    finally:
        db.close()


# Test case 12: test_team_manager_cannot_export_raw_data
def test_team_manager_cannot_export_raw_data():
    app.dependency_overrides[get_current_user] = lambda: mock_tm
    try:
        r1 = client.get("/api/export/csv")
        r2 = client.get("/api/export/xlsx")
        r3 = client.get("/api/export/transcripts")
        
        assert r1.status_code == 403
        assert r2.status_code == 403
        assert r3.status_code == 403
    finally:
        app.dependency_overrides.clear()


# Test case 13: test_team_manager_cannot_access_global_analytics_routes
def test_team_manager_cannot_access_global_analytics_routes():
    app.dependency_overrides[get_current_user] = lambda: mock_tm
    try:
        # Check /api/analytics/ranking route
        response = client.get("/api/analytics/ranking")
        assert response.status_code == 403
        
        # Check /api/analytics/search route
        response_search = client.get("/api/analytics/search")
        assert response_search.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_team_manager_kpis_support_custom_date_range():
    app.dependency_overrides[get_current_user] = lambda: mock_tm
    db = SessionLocal()
    try:
        camp = Campaign(
            id=8580,
            name="TM Dynamic Range Campaign",
            type=CampaignType.SALES,
            evaluation_prompt="Dummy prompt length for dynamic reports",
            color="#FFF",
        )
        team = Team(id=8581, name="TM Dynamic Team", campaign_id=camp.id, manager_id=mock_tm.id, is_active=True)
        agent = Employee(id=8582, name="Dynamic Agent", email="dynamic_agent@example.com", role=UserRole.AGENT, employee_code="DYN_A1", hashed_password="f", status="active")
        assignment = EmployeeTeamAssignment(id=8581, employee_id=agent.id, team_id=team.id, is_active=True)
        in_range_call = Call(
            id=8581,
            employee_id=agent.id,
            campaign_id=camp.id,
            status=CallStatus.EVALUATED,
            evaluation_score=90.0,
            audio_file_path="dyn1",
            original_filename="dyn1",
            created_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        )
        out_of_range_call = Call(
            id=8582,
            employee_id=agent.id,
            campaign_id=camp.id,
            status=CallStatus.EVALUATED,
            evaluation_score=70.0,
            audio_file_path="dyn2",
            original_filename="dyn2",
            created_at=datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
        )
        db.add_all([camp, team, agent, assignment, in_range_call, out_of_range_call])
        db.flush()
        db.add_all([
            CallOutcome(call_id=in_range_call.id, campaign_type="sales", primary_outcome="Sale Closed", outcome_value=100.0),
            CallOutcome(call_id=out_of_range_call.id, campaign_type="sales", primary_outcome="Sale Closed", outcome_value=250.0),
            AttendanceRecord(id=8581, employee_id=agent.id, attendance_date=datetime(2026, 1, 12, tzinfo=timezone.utc).date(), status="present"),
            AttendanceRecord(id=8582, employee_id=agent.id, attendance_date=datetime(2026, 2, 12, tzinfo=timezone.utc).date(), status="absent"),
        ])
        db.commit()
    finally:
        db.close()

    response = client.get("/api/team-manager/kpis?start_date=2026-01-01T00:00:00&end_date=2026-01-31T23:59:59")
    assert response.status_code == 200
    data = response.json()
    assert data["total_sales"] == 1
    assert data["total_revenue"] == 100.0
    assert data["attendance_rate"] == 100.0
    assert data["period_label"] == "2026-01-01 to 2026-01-31"

    agents_response = client.get("/api/team-manager/agents?start_date=2026-01-01T00:00:00&end_date=2026-01-31T23:59:59")
    assert agents_response.status_code == 200
    agents = agents_response.json()
    dynamic_agent = next(item for item in agents if item["agent_id"] == 8582)
    assert dynamic_agent["sales"] == 1
    assert dynamic_agent["revenue"] == 100.0
    assert dynamic_agent["attendance_rate"] == 100.0

    invalid_range = client.get("/api/team-manager/kpis?start_date=2026-02-01T00:00:00&end_date=2026-01-01T00:00:00")
    assert invalid_range.status_code == 400
    assert "start_date" in invalid_range.json()["detail"]

    app.dependency_overrides.clear()
