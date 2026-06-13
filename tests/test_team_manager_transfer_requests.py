import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, UserRole, Campaign, Team, EmployeeTeamAssignment, AgentTransferRequest
from app.routers.auth import get_current_user
from app.database import SessionLocal

client = TestClient(app)

# Helper mock users
mock_admin = Employee(
    id=8700,
    name="Admin User",
    email="admin_tr@example.com",
    role=UserRole.ADMIN,
    employee_code="ADM_TR",
    hashed_password="fake",
    status="active"
)

mock_tm1 = Employee(
    id=8701,
    name="Team Manager 1",
    email="tm1_tr@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM1_TR",
    hashed_password="fake",
    status="active"
)

mock_tm2 = Employee(
    id=8702,
    name="Team Manager 2",
    email="tm2_tr@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM2_TR",
    hashed_password="fake",
    status="active"
)

mock_agent1 = Employee(
    id=8703,
    name="Agent 1",
    email="agt1_tr@example.com",
    role=UserRole.AGENT,
    employee_code="AGT1_TR",
    hashed_password="fake",
    status="active"
)

mock_agent2 = Employee(
    id=8704,
    name="Agent 2",
    email="agt2_tr@example.com",
    role=UserRole.AGENT,
    employee_code="AGT2_TR",
    hashed_password="fake",
    status="active"
)

def setup_transfer_data():
    db = SessionLocal()
    try:
        # Save employees
        for emp in (mock_admin, mock_tm1, mock_tm2, mock_agent1, mock_agent2):
            exist = db.query(Employee).filter(Employee.id == emp.id).first()
            if not exist:
                new_emp = Employee(
                    id=emp.id,
                    name=emp.name,
                    email=emp.email,
                    role=emp.role,
                    employee_code=emp.employee_code,
                    hashed_password=emp.hashed_password,
                    status=emp.status
                )
                db.add(new_emp)
        
        # Campaigns
        camp = db.query(Campaign).filter(Campaign.id == 8700).first()
        if not camp:
            camp = Campaign(
                id=8700,
                name="Transfer Campaign",
                evaluation_prompt="Standard Prompt standard Prompt Standard Prompt standard Prompt",
                color="#ABC"
            )
            db.add(camp)
        db.commit()

        # Teams
        t1 = db.query(Team).filter(Team.id == 8701).first()
        if not t1:
            t1 = Team(id=8701, name="Team 1 TM1", campaign_id=camp.id, manager_id=mock_tm1.id, is_active=True)
            db.add(t1)
            
        t2 = db.query(Team).filter(Team.id == 8702).first()
        if not t2:
            t2 = Team(id=8702, name="Team 2 TM2", campaign_id=camp.id, manager_id=mock_tm2.id, is_active=True)
            db.add(t2)
            
        t_inactive = db.query(Team).filter(Team.id == 8703).first()
        if not t_inactive:
            t_inactive = Team(id=8703, name="Inactive Team", campaign_id=camp.id, manager_id=mock_tm1.id, is_active=False)
            db.add(t_inactive)
            
        db.commit()

        # Assignments
        # agent1 in t1 (active)
        a1 = db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id == 8701).first()
        if not a1:
            a1 = EmployeeTeamAssignment(id=8701, employee_id=mock_agent1.id, team_id=t1.id, is_active=True)
            db.add(a1)
            
        # agent2 in t2 (active)
        a2 = db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id == 8702).first()
        if not a2:
            a2 = EmployeeTeamAssignment(id=8702, employee_id=mock_agent2.id, team_id=t2.id, is_active=True)
            db.add(a2)
            
        db.commit()
    finally:
        db.close()

# 1. test_team_manager_can_create_transfer_request
def test_team_manager_can_create_transfer_request():
    setup_transfer_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "agent_id": mock_agent1.id,
            "from_team_id": 8701,
            "to_team_id": 8702,
            "reason": "Needs training on Team 2 tools."
        }
        response = client.post("/api/team-manager/transfer-requests", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["agent_id"] == mock_agent1.id
        assert data["from_team_id"] == 8701
        assert data["to_team_id"] == 8702
        assert data["status"] == "PENDING"
        assert data["requested_by_id"] == mock_tm1.id
    finally:
        app.dependency_overrides.clear()

# 2. test_team_manager_cannot_request_transfer_for_out_of_scope_agent
def test_team_manager_cannot_request_transfer_for_out_of_scope_agent():
    setup_transfer_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "agent_id": mock_agent2.id,
            "from_team_id": 8702,
            "to_team_id": 8701,
            "reason": "Intrusion attempt"
        }
        response = client.post("/api/team-manager/transfer-requests", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

# 3. test_team_manager_cannot_request_same_team_transfer
def test_team_manager_cannot_request_same_team_transfer():
    setup_transfer_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "agent_id": mock_agent1.id,
            "from_team_id": 8701,
            "to_team_id": 8701,
            "reason": "Same team"
        }
        response = client.post("/api/team-manager/transfer-requests", json=payload)
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()

# 4. test_team_manager_cannot_create_duplicate_pending_request
def test_team_manager_cannot_create_duplicate_pending_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8750,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Original"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "agent_id": mock_agent1.id,
            "from_team_id": 8701,
            "to_team_id": 8702,
            "reason": "Duplicate"
        }
        response = client.post("/api/team-manager/transfer-requests", json=payload)
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()

# 5. test_admin_can_approve_transfer_request
def test_admin_can_approve_transfer_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8751,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "APPROVED",
            "review_note": "Approved by admin"
        }
        response = client.patch(f"/api/admin/transfer-requests/8751/review", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "APPROVED"
        assert data["reviewed_by_id"] == mock_admin.id
        assert data["review_note"] == "Approved by admin"
    finally:
        app.dependency_overrides.clear()

# 6. test_admin_can_reject_transfer_request
def test_admin_can_reject_transfer_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8752,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "REJECTED",
            "review_note": "Rejected"
        }
        response = client.patch(f"/api/admin/transfer-requests/8752/review", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "REJECTED"
    finally:
        app.dependency_overrides.clear()

# 7. test_approve_transfer_closes_old_assignment_and_creates_new_one
def test_approve_transfer_closes_old_assignment_and_creates_new_one():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8753,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "APPROVED",
            "review_note": "Approved"
        }
        response = client.patch(f"/api/admin/transfer-requests/8753/review", json=payload)
        assert response.status_code == 200
        
        db_session = SessionLocal()
        try:
            # Old assignment closed
            old_assignment = db_session.query(EmployeeTeamAssignment).filter(
                EmployeeTeamAssignment.id == 8701
            ).first()
            assert old_assignment.is_active is False
            assert old_assignment.ended_at is not None
            
            # New assignment created
            new_assignment = db_session.query(EmployeeTeamAssignment).filter(
                EmployeeTeamAssignment.employee_id == mock_agent1.id,
                EmployeeTeamAssignment.is_active == True
            ).first()
            assert new_assignment is not None
            assert new_assignment.team_id == 8702
            assert new_assignment.created_by_id == mock_admin.id
        finally:
            db_session.close()
    finally:
        app.dependency_overrides.clear()

# 8. test_reject_transfer_does_not_change_assignments
def test_reject_transfer_does_not_change_assignments():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8754,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "REJECTED",
            "review_note": "Rejected"
        }
        response = client.patch(f"/api/admin/transfer-requests/8754/review", json=payload)
        assert response.status_code == 200
        
        db_session = SessionLocal()
        try:
            old_assignment = db_session.query(EmployeeTeamAssignment).filter(
                EmployeeTeamAssignment.id == 8701
            ).first()
            assert old_assignment.is_active is True
            assert old_assignment.ended_at is None
            
            new_assignment = db_session.query(EmployeeTeamAssignment).filter(
                EmployeeTeamAssignment.employee_id == mock_agent1.id,
                EmployeeTeamAssignment.team_id == 8702
            ).first()
            assert new_assignment is None
        finally:
            db_session.close()
    finally:
        app.dependency_overrides.clear()

# 9. test_non_admin_cannot_review_transfer_request
def test_non_admin_cannot_review_transfer_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8755,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "status": "APPROVED",
            "review_note": "TM trying to approve"
        }
        response = client.patch(f"/api/admin/transfer-requests/8755/review", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

# 10. test_reviewed_request_cannot_be_reviewed_twice
def test_reviewed_request_cannot_be_reviewed_twice():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8756,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="APPROVED",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "REJECTED",
            "review_note": "Double review"
        }
        response = client.patch(f"/api/admin/transfer-requests/8756/review", json=payload)
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()

# 11. test_team_manager_request_list_is_scoped
def test_team_manager_request_list_is_scoped():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req1 = AgentTransferRequest(
            id=8757,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        req2 = AgentTransferRequest(
            id=8758,
            agent_id=mock_agent2.id,
            from_team_id=8702,
            to_team_id=8701,
            requested_by_id=mock_tm2.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add_all([req1, req2])
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/team-manager/transfer-requests")
        assert response.status_code == 200
        data = response.json()
        ids = [r["id"] for r in data]
        assert 8757 in ids
        assert 8758 not in ids
    finally:
        app.dependency_overrides.clear()

# 12. test_team_manager_cannot_view_out_of_scope_transfer_request
def test_team_manager_cannot_view_out_of_scope_transfer_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req2 = AgentTransferRequest(
            id=8759,
            agent_id=mock_agent2.id,
            from_team_id=8702,
            to_team_id=8701,
            requested_by_id=mock_tm2.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req2)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/team-manager/transfer-requests/8759")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()

# 13. test_admin_cannot_approve_transfer_when_agent_assignment_changed_after_request
def test_admin_cannot_approve_transfer_when_agent_assignment_changed_after_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8760,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
        
        assign = db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id == 8701).first()
        assign.is_active = False
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        payload = {
            "status": "APPROVED",
            "review_note": "Approve after assignment change"
        }
        response = client.patch(f"/api/admin/transfer-requests/8760/review", json=payload)
        assert response.status_code == 400
        assert "Agent must have exactly one active assignment" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

# 14. test_team_manager_can_cancel_pending_request
def test_team_manager_can_cancel_pending_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8761,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.patch("/api/team-manager/transfer-requests/8761/cancel")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "CANCELED"
        
        db_session = SessionLocal()
        try:
            db_req = db_session.query(AgentTransferRequest).filter(AgentTransferRequest.id == 8761).first()
            assert db_req.status == "CANCELED"
        finally:
            db_session.close()
    finally:
        app.dependency_overrides.clear()

# 15. test_team_manager_cannot_cancel_reviewed_request
def test_team_manager_cannot_cancel_reviewed_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8762,
            agent_id=mock_agent1.id,
            from_team_id=8701,
            to_team_id=8702,
            requested_by_id=mock_tm1.id,
            status="APPROVED",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.patch("/api/team-manager/transfer-requests/8762/cancel")
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()

# 16. test_team_manager_cannot_cancel_another_manager_request
def test_team_manager_cannot_cancel_another_manager_request():
    setup_transfer_data()
    db = SessionLocal()
    try:
        req = AgentTransferRequest(
            id=8763,
            agent_id=mock_agent2.id,
            from_team_id=8702,
            to_team_id=8701,
            requested_by_id=mock_tm2.id,
            status="PENDING",
            reason="Good reason"
        )
        db.add(req)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.patch("/api/team-manager/transfer-requests/8763/cancel")
        assert response.status_code == 403
        assert "Cannot cancel another manager's request" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
