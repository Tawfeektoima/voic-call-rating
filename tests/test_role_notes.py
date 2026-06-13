import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Employee, UserRole, Campaign, Team, EmployeeTeamAssignment, Call, CallStatus, RoleNote
from app.routers.auth import get_current_user
from app.database import SessionLocal

client = TestClient(app)

# Helper mock users
mock_admin = Employee(
    id=8800,
    name="Admin User",
    email="admin_notes@example.com",
    role=UserRole.ADMIN,
    employee_code="ADM_NTS",
    hashed_password="fake",
    status="active"
)

mock_tm1 = Employee(
    id=8801,
    name="Team Manager 1",
    email="tm1_notes@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM1_NTS",
    hashed_password="fake",
    status="active"
)

mock_tm2 = Employee(
    id=8802,
    name="Team Manager 2",
    email="tm2_notes@example.com",
    role=UserRole.TEAM_MANAGER,
    employee_code="TM2_NTS",
    hashed_password="fake",
    status="active"
)

mock_ops = Employee(
    id=8803,
    name="Ops Manager",
    email="ops_notes@example.com",
    role=UserRole.OPS_MANAGER,
    employee_code="OPS_NTS",
    hashed_password="fake",
    status="active"
)

mock_qa = Employee(
    id=8804,
    name="QA Reviewer",
    email="qa_notes@example.com",
    role=UserRole.QA,
    employee_code="QA_NTS",
    hashed_password="fake",
    status="active"
)

mock_hr = Employee(
    id=8805,
    name="HR Manager",
    email="hr_notes@example.com",
    role=UserRole.HR_MANAGER,
    employee_code="HR_NTS",
    hashed_password="fake",
    status="active"
)

mock_agent1 = Employee(
    id=8806,
    name="Agent 1",
    email="agt1_notes@example.com",
    role=UserRole.AGENT,
    employee_code="AGT1_NTS",
    hashed_password="fake",
    status="active"
)

mock_agent2 = Employee(
    id=8807,
    name="Agent 2",
    email="agt2_notes@example.com",
    role=UserRole.AGENT,
    employee_code="AGT2_NTS",
    hashed_password="fake",
    status="active"
)

mock_tl_sender = Employee(
    id=8816,
    name="Team Leader Sender",
    email="tl_sender@example.com",
    role=UserRole.TEAM_LEADER,
    employee_code="TL_SENDER",
    hashed_password="fake",
    status="active"
)

def setup_notes_data():
    db = SessionLocal()
    try:
        # Save employees
        for emp in (mock_admin, mock_tm1, mock_tm2, mock_ops, mock_qa, mock_hr, mock_agent1, mock_agent2):
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
        
        # Campaign
        camp = db.query(Campaign).filter(Campaign.id == 8800).first()
        if not camp:
            camp = Campaign(
                id=8800,
                name="Notes Campaign",
                evaluation_prompt="Standard Prompt standard Prompt Standard Prompt standard Prompt",
                color="#ABC"
            )
            db.add(camp)
        db.commit()

        # Teams
        t1 = db.query(Team).filter(Team.id == 8801).first()
        if not t1:
            t1 = Team(id=8801, name="Team 1 TM1", campaign_id=camp.id, manager_id=mock_tm1.id, is_active=True)
            db.add(t1)
            
        t2 = db.query(Team).filter(Team.id == 8802).first()
        if not t2:
            t2 = Team(id=8802, name="Team 2 TM2", campaign_id=camp.id, manager_id=mock_tm2.id, is_active=True)
            db.add(t2)
        db.commit()

        # Assignments
        a1 = db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id == 8801).first()
        if not a1:
            a1 = EmployeeTeamAssignment(id=8801, employee_id=mock_agent1.id, team_id=t1.id, is_active=True)
            db.add(a1)
            
        a2 = db.query(EmployeeTeamAssignment).filter(EmployeeTeamAssignment.id == 8802).first()
        if not a2:
            a2 = EmployeeTeamAssignment(id=8802, employee_id=mock_agent2.id, team_id=t2.id, is_active=True)
            db.add(a2)
        db.commit()

        # Call
        c1 = db.query(Call).filter(Call.id == 8801).first()
        if not c1:
            c1 = Call(id=8801, employee_id=mock_agent1.id, campaign_id=camp.id, status=CallStatus.EVALUATED, evaluation_score=95.0, audio_file_path="f1", original_filename="f1")
            db.add(c1)
        db.commit()
    finally:
        db.close()


# 1. test_team_manager_can_create_note_for_managed_agent
def test_team_manager_can_create_note_for_managed_agent():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "recipient_role": "QA",
            "employee_id": mock_agent1.id,
            "team_id": 8801,
            "title": "Agent coaching required",
            "body": "Coaching body content here.",
            "note_type": "GENERAL",
            "priority": "NORMAL"
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["sender_id"] == mock_tm1.id
        assert data["agent_name_snapshot"] == mock_agent1.name
        assert data["team_name_snapshot"] == "Team 1 TM1"
    finally:
        app.dependency_overrides.clear()


# 2. test_team_manager_cannot_create_note_for_out_of_scope_agent
def test_team_manager_cannot_create_note_for_out_of_scope_agent():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        payload = {
            "recipient_role": "QA",
            "employee_id": mock_agent2.id,
            "team_id": 8802,
            "title": "Agent coaching required",
            "body": "Coaching body content here.",
            "note_type": "GENERAL"
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# 3. test_ops_manager_can_send_kpi_alert_to_team_manager
def test_ops_manager_can_send_kpi_alert_to_team_manager():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        payload = {
            "recipient_id": mock_tm1.id,
            "team_id": 8801,
            "title": "KPI alert for conversion rate",
            "body": "Conversion rate dropped below 20%.",
            "note_type": "KPI_ALERT",
            "kpi_key": "conversion_rate",
            "kpi_label": "Conversion Rate",
            "current_value": 18.5,
            "target_value": 25.0
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "OPEN"
        assert data["recipient_id"] == mock_tm1.id
        assert data["kpi_key"] == "conversion_rate"
    finally:
        app.dependency_overrides.clear()


# 4. test_kpi_alert_requires_team_id_and_kpi_key
def test_kpi_alert_requires_team_id_and_kpi_key():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        # Missing team_id and KPI fields
        payload = {
            "recipient_id": mock_tm1.id,
            "title": "KPI Alert",
            "body": "Missing team",
            "note_type": "KPI_ALERT"
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


# 5. test_kpi_alert_resolves_recipient_from_team_manager
def test_kpi_alert_resolves_recipient_from_team_manager():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        response = client.get("/api/notes/recipients?note_type=KPI_ALERT&team_id=8801")
        assert response.status_code == 200
        recipients = response.json()
        assert len(recipients) == 1
        assert recipients[0]["id"] == mock_tm1.id
        assert recipients[0]["role"] == "TEAM_MANAGER"
        assert recipients[0]["reason"] == "Team manager for KPI alert"
    finally:
        app.dependency_overrides.clear()


def test_team_manager_can_resolve_kpi_follow_up_recipient():
    setup_notes_data()
    db = SessionLocal()
    try:
        leader = db.query(Employee).filter(Employee.id == 8815).first()
        if not leader:
            leader = Employee(
                id=8815,
                name="Team Leader Notes",
                email="tl_notes@example.com",
                role=UserRole.TEAM_LEADER,
                employee_code="TL_NOTES",
                hashed_password="fake",
                status="active",
            )
            db.add(leader)
            db.commit()

        team = db.query(Team).filter(Team.id == 8801).first()
        team.leader_id = leader.id
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/notes/recipients?note_type=KPI_FOLLOW_UP&team_id=8801")
        assert response.status_code == 200
        recipients = response.json()
        assert len(recipients) == 1
        assert recipients[0]["role"] == "TEAM_LEADER"
        assert recipients[0]["reason"] == "Team leader for KPI follow-up"
    finally:
        app.dependency_overrides.clear()


def test_team_leader_can_resolve_kpi_follow_up_recipient():
    setup_notes_data()
    db = SessionLocal()
    try:
        leader = db.query(Employee).filter(Employee.id == mock_tl_sender.id).first()
        if not leader:
            db.add(Employee(
                id=mock_tl_sender.id,
                name=mock_tl_sender.name,
                email=mock_tl_sender.email,
                role=mock_tl_sender.role,
                employee_code=mock_tl_sender.employee_code,
                hashed_password=mock_tl_sender.hashed_password,
                status=mock_tl_sender.status,
            ))
            db.commit()

        team = db.query(Team).filter(Team.id == 8801).first()
        team.leader_id = mock_tl_sender.id
        team.manager_id = mock_tm1.id
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_current_user] = lambda: mock_tl_sender
    try:
        response = client.get("/api/notes/recipients?note_type=KPI_FOLLOW_UP&team_id=8801")
        assert response.status_code == 200
        recipients = response.json()
        assert len(recipients) == 1
        assert recipients[0]["id"] == mock_tm1.id
        assert recipients[0]["role"] == "TEAM_MANAGER"
        assert recipients[0]["reason"] == "Team manager for KPI follow-up"
    finally:
        app.dependency_overrides.clear()


# 6. test_qa_can_receive_and_reply_to_qa_review_request
def test_qa_can_receive_and_reply_to_qa_review_request():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8850,
            sender_id=mock_tm1.id,
            recipient_role="QA",
            title="QA review request",
            body="Please check call score.",
            note_type="QA_REVIEW_REQUEST",
            call_id=8801,
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_qa
    try:
        # QA reviews detail
        response = client.get("/api/notes/8850")
        assert response.status_code == 200
        
        # QA replies
        reply_payload = {
            "title": "RE: QA review request",
            "body": "I have reviewed it, score is correct.",
            "note_type": "GENERAL"
        }
        response = client.post("/api/notes/8850/reply", json=reply_payload)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["parent_note_id"] == 8850
        assert data["recipient_id"] == mock_tm1.id
    finally:
        app.dependency_overrides.clear()


# 7. test_direct_recipient_can_view_note
def test_direct_recipient_can_view_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8851,
            sender_id=mock_tm1.id,
            recipient_id=mock_tm2.id,
            title="Direct Note",
            body="Secrets",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm2
    try:
        response = client.get("/api/notes/8851")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


# 8. test_role_recipient_can_view_scoped_note
def test_role_recipient_can_view_scoped_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8852,
            sender_id=mock_ops.id,
            recipient_role="TEAM_MANAGER",
            team_id=8801,
            title="Scoped Note",
            body="For TM1",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/notes/8852")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


# 9. test_non_recipient_cannot_view_note
def test_non_recipient_cannot_view_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8853,
            sender_id=mock_ops.id,
            recipient_role="TEAM_MANAGER",
            team_id=8802, # linked to TM2 scope
            title="Scoped Note",
            body="For TM2",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    # TM1 (unlinked) should receive 403
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/notes/8853")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# 10. test_sender_can_view_sent_note
def test_sender_can_view_sent_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8854,
            sender_id=mock_tm1.id,
            recipient_id=mock_tm2.id,
            title="Sent Note",
            body="Sender checks",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/notes/sent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 8854
    finally:
        app.dependency_overrides.clear()


# 11. test_reply_creates_threaded_note
def test_reply_creates_threaded_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8855,
            sender_id=mock_tm1.id,
            recipient_id=mock_ops.id,
            title="Thread Root",
            body="Initial discussion",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        reply_payload = {
            "title": "RE: Thread Root",
            "body": "First reply",
            "note_type": "GENERAL"
        }
        response = client.post("/api/notes/8855/reply", json=reply_payload)
        assert response.status_code == 200
        
        # Verify parent status updated to WAITING_REPLY
        db_s = SessionLocal()
        try:
            parent_note = db_s.query(RoleNote).filter(RoleNote.id == 8855).first()
            assert parent_note.status == "WAITING_REPLY"
        finally:
            db_s.close()
    finally:
        app.dependency_overrides.clear()


# 12. test_recipient_can_mark_note_read
def test_recipient_can_mark_note_read():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8856,
            sender_id=mock_tm1.id,
            recipient_id=mock_ops.id,
            title="Mark Read Target",
            body="Please read",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        response = client.patch("/api/notes/8856/read")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "READ"
        assert data["read_at"] is not None
    finally:
        app.dependency_overrides.clear()


# 13. test_authorized_user_can_change_status
def test_authorized_user_can_change_status():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8857,
            sender_id=mock_tm1.id,
            recipient_id=mock_ops.id,
            title="Status Change Target",
            body="Review status",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        response = client.patch("/api/notes/8857/status", json={"status": "IN_PROGRESS"})
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"
    finally:
        app.dependency_overrides.clear()


# 14. test_authorized_user_can_resolve_note
def test_authorized_user_can_resolve_note():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8858,
            sender_id=mock_tm1.id,
            recipient_id=mock_ops.id,
            title="Resolve target",
            body="Finish me",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_ops
    try:
        response = client.patch("/api/notes/8858/resolve")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "RESOLVED"
        assert data["resolved_by_id"] == mock_ops.id
    finally:
        app.dependency_overrides.clear()


# 15. test_admin_can_view_all_notes
def test_admin_can_view_all_notes():
    setup_notes_data()
    db = SessionLocal()
    try:
        note = RoleNote(
            id=8859,
            sender_id=mock_tm1.id,
            recipient_id=mock_ops.id,
            title="Admin Bypass Target",
            body="Protected detail",
            status="OPEN"
        )
        db.add(note)
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    try:
        response = client.get("/api/notes/8859")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


# 16. test_invalid_role_flow_is_rejected
def test_invalid_role_flow_is_rejected():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        # TM sending KPI_ALERT to Ops is invalid role transition
        payload = {
            "recipient_id": mock_ops.id,
            "team_id": 8801,
            "title": "KPI Alert",
            "body": "Drop",
            "note_type": "KPI_ALERT",
            "kpi_key": "conversion_rate",
            "kpi_label": "Conversion Rate",
            "current_value": 15.0,
            "target_value": 20.0
        }
        response = client.post("/api/notes", json=payload)
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


# 17. test_recipient_resolver_returns_only_allowed_recipients
def test_recipient_resolver_returns_only_allowed_recipients():
    setup_notes_data()
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        response = client.get("/api/notes/recipients?note_type=QA_REVIEW_REQUEST&call_id=8801")
        assert response.status_code == 200
        recipients = response.json()
        roles = {r["role"] for r in recipients}
        # TM can only request QA reviews to QA role
        assert "QA" in roles
        assert "ADMIN" not in roles
    finally:
        app.dependency_overrides.clear()


# 18. test_inbox_filters_and_pagination_work
def test_inbox_filters_and_pagination_work():
    setup_notes_data()
    db = SessionLocal()
    try:
        note1 = RoleNote(
            id=8860,
            sender_id=mock_ops.id,
            recipient_id=mock_tm1.id,
            title="Note 1",
            body="Inbox content 1",
            note_type="GENERAL",
            priority="HIGH",
            status="OPEN"
        )
        note2 = RoleNote(
            id=8861,
            sender_id=mock_ops.id,
            recipient_id=mock_tm1.id,
            title="Note 2",
            body="Inbox content 2",
            note_type="KPI_ALERT",
            priority="NORMAL",
            status="OPEN"
        )
        db.add_all([note1, note2])
        db.commit()
    finally:
        db.close()
        
    app.dependency_overrides[get_current_user] = lambda: mock_tm1
    try:
        # Filter by note_type
        response = client.get("/api/notes/inbox?note_type=KPI_ALERT")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 8861
        
        # Filter by priority
        response_p = client.get("/api/notes/inbox?priority=HIGH")
        assert response_p.status_code == 200
        data_p = response_p.json()
        assert len(data_p) == 1
        assert data_p[0]["id"] == 8860
        
        # Pagination
        response_pag = client.get("/api/notes/inbox?limit=1")
        assert response_pag.status_code == 200
        assert len(response_pag.json()) == 1
    finally:
        app.dependency_overrides.clear()
