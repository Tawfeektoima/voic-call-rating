import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import SessionLocal
from app.services.interview_file_crypto import decrypt_file_bytes, decrypt_text_value
from app.services.employee_identity import hash_national_id
from app.models import (
    AuditEvent,
    Employee,
    InterviewAnswer,
    InterviewAnswerStatus,
    InterviewCandidateDocument,
    InterviewCandidate,
    InterviewMcqSubmission,
    InterviewCandidateStatus,
    InterviewJob,
    InterviewQuestion,
    InterviewQuestionSource,
    InterviewSession,
    InterviewSessionStatus,
    InterviewWorkflowEvent,
    UserRole,
)
from app.routers.auth import get_current_user
from app.services.interview_mcq import DEFAULT_INTERVIEW_MCQ_BANK
from app.services.interview_workflow import sync_candidate_interview_state

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _seed_hr_user() -> Employee:
    db: Session = SessionLocal()
    try:
        hr = Employee(
            name="Interview HR API",
            email="interview_hr_api@example.com",
            role=UserRole.HR_MANAGER,
            employee_code="INT_HR_API",
            hashed_password="fake",
            status="active",
        )
        db.add(hr)
        db.commit()
        db.refresh(hr)
        return hr
    finally:
        db.close()


def test_hr_can_create_job_candidate_invite_and_candidate_can_complete_flow():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    with patch("app.routers.interview_portal.process_interview_answer_task.delay") as mock_delay:
        create_job = client.post(
            "/api/hr/interviews/jobs",
            json={
                "title": "Outbound Sales Agent",
                "description": "Voice-first interview screening.",
                "department": "HR",
                "status": "open",
                "base_questions": ["Introduce yourself", "Why do you want this role?"],
            },
        )
        assert create_job.status_code == 200
        job_id = create_job.json()["id"]

        create_candidate = client.post(
            "/api/hr/interviews/candidates",
            json={
                "job_id": job_id,
                "full_name": "Candidate API Flow",
                "contact_email": "candidate.api@example.com",
                "phone_number": "010-5555-0001",
                "national_id": "29801011234567",
            },
        )
        assert create_candidate.status_code == 200
        candidate_body = create_candidate.json()
        candidate_id = candidate_body["id"]
        assert candidate_body["contact_email_normalized"] == "candidate.api@example.com"
        assert candidate_body["national_id_last4"] == "4567"

        invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/invite",
            json={"expires_in_hours": 12},
        )
        assert invite.status_code == 200
        invite_body = invite.json()
        assert invite_body["question_count"] == 2
        session_token = invite_body["session_token"]
        assert invite_body["invite_url"] == f"http://localhost:5173/interview-portal?token={session_token}"

        portal_headers = {"X-Interview-Session-Token": session_token}
        portal_session = client.get("/api/interview-portal/session", headers=portal_headers)
        assert portal_session.status_code == 200
        assert portal_session.json()["candidate_name"] == "Candidate API Flow"
        assert portal_session.json()["status"] == "invited"

        questions = client.get("/api/interview-portal/questions", headers=portal_headers)
        assert questions.status_code == 200
        question_rows = questions.json()
        assert len(question_rows) == 2
        question_id = question_rows[0]["id"]

        submit = client.post(
            f"/api/interview-portal/questions/{question_id}/answer",
            headers=portal_headers,
            data={"transcript_text": "I have sales experience and strong communication skills."},
        )
        assert submit.status_code == 200
        assert submit.json()["status"] == "pending"

        audio_submit = client.post(
            f"/api/interview-portal/questions/{question_rows[1]['id']}/answer",
            headers=portal_headers,
            files={"audio_file": ("answer.webm", io.BytesIO(b"fake-audio"), "audio/webm")},
        )
        assert audio_submit.status_code == 200
        assert audio_submit.json()["status"] == "pending"

        complete = client.post("/api/interview-portal/complete", headers=portal_headers)
        assert complete.status_code == 200
        assert complete.json()["candidate_status"] == "interviewing"
        assert mock_delay.call_count == 2

    app.dependency_overrides[get_current_user] = lambda: hr
    answers_response = client.get(f"/api/hr/interviews/candidates/{candidate_id}/answers")
    assert answers_response.status_code == 200
    assert len(answers_response.json()) == 2

    db = SessionLocal()
    try:
        candidate = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        session = db.query(InterviewSession).filter(InterviewSession.id == invite_body["session_id"]).first()
        answers = db.query(InterviewAnswer).filter(InterviewAnswer.candidate_id == candidate_id).all()
        workflow_events = db.query(InterviewWorkflowEvent).filter(InterviewWorkflowEvent.candidate_id == candidate_id).all()
        assert candidate is not None
        assert candidate.status == InterviewCandidateStatus.INTERVIEWING
        assert session is not None
        assert session.status == InterviewSessionStatus.COMPLETED
        assert len(answers) == 2
        assert any(event.event_type == "INTERVIEW_COMPLETED" for event in workflow_events)
        assert db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_CANDIDATE_INVITE").count() == 1
    finally:
        db.close()


def test_agent_cannot_create_interview_job():
    agent = Employee(
        id=99991,
        name="Forbidden Agent",
        email="forbidden_agent@example.com",
        role=UserRole.AGENT,
        employee_code="FORBIDDEN_AGENT",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: agent

    response = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Blocked Job",
            "description": "This should not be allowed.",
            "status": "draft",
            "base_questions": ["Question"],
        },
    )

    assert response.status_code == 403


def test_candidate_cannot_reanswer_same_question():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Repeat Guard",
            "description": "Guard duplicate answers.",
            "status": "open",
            "base_questions": ["Tell me about a challenge"],
        },
    )
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Repeat Candidate",
            "contact_email": "repeat@example.com",
        },
    )
    invite = client.post(
        f"/api/hr/interviews/candidates/{candidate.json()['id']}/invite",
        json={"expires_in_hours": 12},
    )
    headers = {"X-Interview-Session-Token": invite.json()["session_token"]}
    question_id = client.get("/api/interview-portal/questions", headers=headers).json()[0]["id"]

    with patch("app.routers.interview_portal.process_interview_answer_task.delay"):
        first = client.post(
            f"/api/interview-portal/questions/{question_id}/answer",
            headers=headers,
            data={"transcript_text": "First answer"},
        )
        second = client.post(
            f"/api/interview-portal/questions/{question_id}/answer",
            headers=headers,
            data={"transcript_text": "Second answer"},
        )

    assert first.status_code == 200
    assert second.status_code == 400
    assert "already has a submitted answer" in second.json()["detail"]


def test_candidate_must_finish_soft_skills_assessment_before_completing_session():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Soft Skills Role",
            "description": "Interview flow with a written assessment.",
            "status": "open",
            "base_questions": ["Tell me about a challenge you solved."],
            "mcq_enabled": True,
            "mcq_questions": DEFAULT_INTERVIEW_MCQ_BANK,
        },
    )
    assert job.status_code == 200

    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Soft Skills Candidate",
            "contact_email": "soft.skills@example.com",
        },
    )
    assert candidate.status_code == 200

    invite = client.post(
        f"/api/hr/interviews/candidates/{candidate.json()['id']}/invite",
        json={"expires_in_hours": 12},
    )
    assert invite.status_code == 200
    headers = {"X-Interview-Session-Token": invite.json()["session_token"]}
    question_id = client.get("/api/interview-portal/questions", headers=headers).json()[0]["id"]

    with patch("app.routers.interview_portal.process_interview_answer_task.delay"):
        answer_response = client.post(
            f"/api/interview-portal/questions/{question_id}/answer",
            headers=headers,
            data={"transcript_text": "I handled a difficult customer calmly and collaboratively."},
        )
    assert answer_response.status_code == 200

    blocked_complete = client.post("/api/interview-portal/complete", headers=headers)
    assert blocked_complete.status_code == 400
    assert "written assessment" in blocked_complete.json()["detail"].lower()

    mcq = client.get("/api/interview-portal/mcq", headers=headers)
    assert mcq.status_code == 200
    mcq_body = mcq.json()
    assert mcq_body["mcq_enabled"] is True
    assert len(mcq_body["questions"]) == len(DEFAULT_INTERVIEW_MCQ_BANK)
    assert mcq_body["questions"][0]["correct"] is None
    assert mcq_body["questions"][0]["trait_tags"] == []

    answers = {str(question["id"]): 0 for question in mcq_body["questions"]}
    mcq_submit = client.post("/api/interview-portal/mcq", headers=headers, json={"answers": answers})
    assert mcq_submit.status_code == 200
    expected_score = float(
        sum(
            1
            for question in DEFAULT_INTERVIEW_MCQ_BANK
            if question.get("category") in {"iq", "computer"} and question.get("correct") == 0
        )
        + 5
    )
    assert mcq_submit.json()["score"] == expected_score

    complete = client.post("/api/interview-portal/complete", headers=headers)
    assert complete.status_code == 200

    candidate_dashboard = client.get("/api/interview-portal/dashboard", headers=headers)
    assert candidate_dashboard.status_code == 200
    dashboard_body = candidate_dashboard.json()
    assert dashboard_body["candidate_name"] == "Soft Skills Candidate"
    assert dashboard_body["session_status"] == "completed"
    assert dashboard_body["submitted_answers"] == 1
    assert dashboard_body["question_count"] == 1
    assert dashboard_body["mcq_result"]["completed"] is True
    assert dashboard_body["mcq_result"]["total_questions"] == 15
    assert len(dashboard_body["answers"]) == 1

    mcq_review = client.get(f"/api/hr/interviews/candidates/{candidate.json()['id']}/mcq")
    assert mcq_review.status_code == 200
    assert mcq_review.json()["candidate_id"] == candidate.json()["id"]

    mcq_results = client.get(f"/api/hr/interviews/candidates/{candidate.json()['id']}/mcq-results")
    assert mcq_results.status_code == 200
    mcq_results_body = mcq_results.json()
    assert mcq_results_body["status"] == "success"
    assert mcq_results_body["candidate_id"] == candidate.json()["id"]
    assert len(mcq_results_body["iq"]) == 5
    assert len(mcq_results_body["computer"]) == 5
    assert len(mcq_results_body["personality"]) == 5
    assert mcq_results_body["personality_breakdown"]["collaborative"] == 5
    assert mcq_results_body["iq"][1]["is_correct"] is True
    assert mcq_results_body["computer"][0]["is_correct"] is False
    assert mcq_results_body["personality"][0]["chosen_trait"] == "collaborative"

    candidates_list = client.get(f"/api/hr/interviews/candidates?job_id={job.json()['id']}")
    assert candidates_list.status_code == 200
    candidate_row = candidates_list.json()[0]
    assert candidate_row["mcq_score"] == expected_score
    assert candidate_row["mcq_total_questions"] == 15
    assert candidate_row["mcq_percentage"] is not None
    assert candidate_row["mcq_completed_at"] is not None

    db = SessionLocal()
    try:
        submission = db.query(InterviewMcqSubmission).filter(
            InterviewMcqSubmission.candidate_id == candidate.json()["id"]
        ).first()
        assert submission is not None
        assert submission.total_questions == len(DEFAULT_INTERVIEW_MCQ_BANK)
    finally:
        db.close()


def test_hr_can_load_unified_candidate_review_summary():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Review Summary Role",
            "description": "Unified candidate review page data.",
            "status": "open",
            "base_questions": ["Tell me about yourself", "How do you handle objections?"],
            "mcq_enabled": True,
            "mcq_questions": DEFAULT_INTERVIEW_MCQ_BANK,
        },
    )
    assert job.status_code == 200

    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Review Summary Candidate",
            "contact_email": "review.summary@example.com",
        },
    )
    assert candidate.status_code == 200

    invite = client.post(
        f"/api/hr/interviews/candidates/{candidate.json()['id']}/invite",
        json={"expires_in_hours": 12},
    )
    assert invite.status_code == 200
    headers = {"X-Interview-Session-Token": invite.json()["session_token"]}
    questions = client.get("/api/interview-portal/questions", headers=headers).json()

    with patch("app.routers.interview_portal.process_interview_answer_task.delay"):
        for question in questions:
            answer_response = client.post(
                f"/api/interview-portal/questions/{question['id']}/answer",
                headers=headers,
                data={"transcript_text": f"Answer for {question['question_text']}"},
            )
            assert answer_response.status_code == 200

    mcq = client.get("/api/interview-portal/mcq", headers=headers)
    assert mcq.status_code == 200
    answers = {str(question["id"]): 0 for question in mcq.json()["questions"]}
    mcq_submit = client.post("/api/interview-portal/mcq", headers=headers, json={"answers": answers})
    assert mcq_submit.status_code == 200

    complete = client.post("/api/interview-portal/complete", headers=headers)
    assert complete.status_code == 200

    db = SessionLocal()
    try:
        answer_rows = (
            db.query(InterviewAnswer)
            .filter(InterviewAnswer.candidate_id == candidate.json()["id"])
            .order_by(InterviewAnswer.id.asc())
            .all()
        )
        assert len(answer_rows) == 2
        answer_rows[0].status = "evaluated"
        answer_rows[0].overall_score = 86
        answer_rows[0].ai_summary = "Strong answer with clear structure."
        answer_rows[1].status = "evaluated"
        answer_rows[1].overall_score = 74
        answer_rows[1].ai_summary = "Solid answer with room for stronger detail."
        db.commit()
    finally:
        db.close()

    review = client.get(f"/api/hr/interviews/candidates/{candidate.json()['id']}/review")
    assert review.status_code == 200
    review_body = review.json()
    assert review_body["status"] == "success"
    assert review_body["candidate"]["full_name"] == "Review Summary Candidate"
    assert review_body["interview_metrics"]["evaluation_state"] == "Ready"
    assert review_body["interview_metrics"]["submitted_answers"] == 2
    assert review_body["interview_metrics"]["average_answer_score"] == 80.0
    assert review_body["mcq_summary"]["completed"] is True
    assert review_body["recommendation"]["label"] in {"Proceed", "Strong Hire"}
    assert review_body["recommendation"]["score"] is not None
    assert review_body["answers"][0]["question_text"] == "Tell me about yourself"
    assert review_body["answers"][0]["ai_summary"] == "Strong answer with clear structure."


def test_public_candidate_can_register_with_cv_and_cooldown_is_enforced():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Public Registration Role",
            "description": "Public candidate registration flow.",
            "status": "open",
            "base_questions": [
                "Introduce yourself",
                "Describe a difficult customer interaction",
                "How do you handle pressure?",
                "Why do you want this role?",
            ],
            "department": "Sales",
            "mcq_enabled": True,
            "mcq_questions": DEFAULT_INTERVIEW_MCQ_BANK,
        },
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    public_jobs = client.get("/api/interview-portal/jobs")
    assert public_jobs.status_code == 200
    assert public_jobs.json()[0]["id"] == job_id

    register = client.post(
        "/api/interview-portal/register",
        data={
            "job_id": str(job_id),
            "full_name": "Public Candidate",
            "contact_email": "public.candidate@example.com",
            "phone_number": "01022223333",
            "national_id": "29901011234567",
            "date_of_birth": "1999-01-01",
            "address": "Cairo",
            "manual_experience": "Skills: customer support and CRM systems. Experience: handled retention calls. Achievements: improved customer satisfaction.",
        },
        files={"cv_file": ("public-cv.txt", io.BytesIO(b"Skills: customer support and CRM systems. Experience: handled retention calls. Achievements: improved customer satisfaction."), "text/plain")},
    )
    assert register.status_code == 200
    register_body = register.json()
    assert register_body["candidate_name"] == "Public Candidate"
    assert register_body["session_token"]
    assert register_body["question_count"] == 5
    assert register_body["document_extraction_status"] == "complete"

    portal_headers = {"X-Interview-Session-Token": register_body["session_token"]}
    portal_session = client.get("/api/interview-portal/session", headers=portal_headers)
    assert portal_session.status_code == 200
    assert portal_session.json()["candidate_name"] == "Public Candidate"
    assert portal_session.json()["question_time_limit_seconds"] > 0

    questions = client.get("/api/interview-portal/questions", headers=portal_headers)
    assert questions.status_code == 200
    question_rows = questions.json()
    assert len([question for question in question_rows if question["source"] == "base"]) == 3
    assert len([question for question in question_rows if question["source"] == "cv_ai"]) == 2

    start = client.post(f"/api/interview-portal/questions/{question_rows[0]['id']}/start", headers=portal_headers)
    assert start.status_code == 200
    assert start.json()["question_id"] == question_rows[0]["id"]

    db = SessionLocal()
    try:
        answer_row = (
            db.query(InterviewAnswer)
            .filter(
                InterviewAnswer.candidate_id == register_body["candidate_id"],
                InterviewAnswer.question_id == question_rows[0]["id"],
            )
            .first()
        )
        assert answer_row is not None
        answer_row.started_at = answer_row.started_at - timedelta(seconds=portal_session.json()["question_time_limit_seconds"] + 5)
        db.commit()
    finally:
        db.close()

    timeout_submit = client.post(
        f"/api/interview-portal/questions/{question_rows[0]['id']}/answer",
        headers=portal_headers,
        data={"transcript_text": "This was submitted too late."},
    )
    assert timeout_submit.status_code == 200
    assert timeout_submit.json()["status"] == "timeout"

    db = SessionLocal()
    try:
        candidate_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == register_body["candidate_id"]).first()
        assert candidate_row is not None
        assert candidate_row.registration_source == "public"
        assert candidate_row.national_id_last4 == "4567"
        assert candidate_row.date_of_birth_encrypted != "1999-01-01"
        assert candidate_row.address_encrypted != "Cairo"
        candidate_row.completed_at = candidate_row.applied_at
        db.commit()
    finally:
        db.close()

    blocked = client.post(
        "/api/interview-portal/register",
        data={
            "job_id": str(job_id),
            "full_name": "Public Candidate",
            "contact_email": "public.candidate@example.com",
            "phone_number": "01022223333",
            "national_id": "29901011234567",
            "date_of_birth": "1999-01-01",
            "address": "Cairo",
        },
    )
    assert blocked.status_code == 403
    assert "recently completed" in blocked.json()["detail"].lower()


def test_hr_can_upload_document_reject_archive_and_convert_candidate():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Conversion Role",
            "description": "Candidate conversion flow.",
            "status": "open",
            "base_questions": ["Question one"],
            "department": "Sales",
        },
    )
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Conversion Candidate",
            "contact_email": "convert@example.com",
            "phone_number": "01098765432",
            "national_id": "30101011234567",
        },
    )
    candidate_id = candidate.json()["id"]

    upload = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/documents",
        data={"document_type": "cv"},
        files={"file": ("resume.txt", io.BytesIO(b"resume-content"), "text/plain")},
    )
    assert upload.status_code == 200
    assert upload.json()["document_type"] == "cv"
    assert "storage_path" not in upload.json()
    assert "extracted_text" not in upload.json()

    list_docs = client.get(f"/api/hr/interviews/candidates/{candidate_id}/documents")
    assert list_docs.status_code == 200
    assert len(list_docs.json()) == 1
    assert "storage_path" not in list_docs.json()[0]
    assert "extracted_text" not in list_docs.json()[0]

    reject = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/reject",
        json={"note": "Needs stronger communication"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REJECTED" or reject.json()["status"] == "rejected"

    archive = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/archive",
        json={"note": "Archived after rejection"},
    )
    assert archive.status_code == 200
    assert archive.json()["status"] == "ARCHIVED" or archive.json()["status"] == "archived"

    db = SessionLocal()
    try:
        candidate_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert candidate_row is not None
        candidate_row.status = InterviewCandidateStatus.ACCEPTED
        candidate_row.archived_at = None
        db.commit()
    finally:
        db.close()

    convert = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={
            "employee_code": "950",
            "role": "agent",
            "otp_email": "real.person@example.com",
            "password": "Eiacs$1234#",
        },
    )
    assert convert.status_code == 200
    body = convert.json()
    assert body["employee_code"] == "950"
    assert body["employee_email"] == "emp-950@eiacs.com"
    assert body["role"] == "AGENT"
    
    db = SessionLocal()
    try:
        candidate_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert candidate_row is not None
        assert candidate_row.status == InterviewCandidateStatus.ACCEPTED
        assert candidate_row.converted_employee_id is not None

        employee_row = db.query(Employee).filter(Employee.id == candidate_row.converted_employee_id).first()
        assert employee_row is not None
        assert employee_row.employee_code == "950"
        assert employee_row.email == "emp-950@eiacs.com"
        assert employee_row.otp_email == "real.person@example.com"
        assert employee_row.department == "Sales"
        assert employee_row.national_id_hash == candidate_row.national_id_hash

        doc_rows = db.query(InterviewCandidateDocument).filter(InterviewCandidateDocument.candidate_id == candidate_id).all()
        assert len(doc_rows) == 1
        assert doc_rows[0].is_encrypted is True
        assert doc_rows[0].extraction_status == "complete"
        assert doc_rows[0].extracted_text != "resume-content"
        assert decrypt_text_value(doc_rows[0].extracted_text) == "resume-content"
        assert decrypt_file_bytes(doc_rows[0].storage_path) == b"resume-content"
        assert db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_CANDIDATE_CONVERT").count() == 1
    finally:
        db.close()


def test_candidate_onboarding_readiness_reflects_status_and_duplicates():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Readiness Role",
            "description": "Readiness checks.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Readiness Candidate",
            "contact_email": "readiness@example.com",
            "phone_number": "01012345678",
            "national_id": "30101011234567",
        },
    )
    assert candidate.status_code == 200
    candidate_id = candidate.json()["id"]

    blocked = client.get(f"/api/hr/interviews/candidates/{candidate_id}/onboarding-readiness")
    assert blocked.status_code == 200
    blocked_body = blocked.json()
    assert blocked_body["is_ready"] is False
    assert any("accepted" in reason.lower() for reason in blocked_body["blocking_reasons"])
    assert blocked_body["candidate_identity_summary"]["contact_email_masked"].endswith("@example.com")
    assert blocked_body["suggested_employee_code"] == str(candidate_id)
    assert blocked_body["suggested_company_email"] == f"emp-{candidate_id}@eiacs.com"

    db = SessionLocal()
    try:
        row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert row is not None
        row.status = InterviewCandidateStatus.ACCEPTED
        db.commit()

        duplicate_employee = Employee(
            name="Duplicate Employee",
            email=f"emp-{candidate_id}@eiacs.com",
            otp_email="dup@example.com",
            employee_code=str(candidate_id),
            hashed_password="fake",
            role=UserRole.AGENT,
            status="active",
        )
        db.add(duplicate_employee)
        db.commit()
    finally:
        db.close()

    duplicate = client.get(f"/api/hr/interviews/candidates/{candidate_id}/onboarding-readiness")
    assert duplicate.status_code == 200
    duplicate_body = duplicate.json()
    assert duplicate_body["is_ready"] is False
    assert any("already registered" in reason.lower() for reason in duplicate_body["blocking_reasons"])
    assert duplicate_body["existing_employee_match"] is not None


def test_hr_can_bulk_archive_interview_candidates():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Bulk Archive Role",
            "description": "Bulk candidate operations.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    )
    assert job.status_code == 200

    candidate_ids = []
    for index in range(2):
      candidate = client.post(
          "/api/hr/interviews/candidates",
          json={
              "job_id": job.json()["id"],
              "full_name": f"Bulk Candidate {index}",
              "contact_email": f"bulk{index}@example.com",
          },
      )
      assert candidate.status_code == 200
      candidate_ids.append(candidate.json()["id"])

    response = client.post(
        "/api/hr/interviews/candidates/bulk-archive",
        json={"candidate_ids": candidate_ids, "note": "Bulk cleanup"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["requested"] == 2
    assert body["updated"] == 2
    assert body["skipped"] == 0

    db = SessionLocal()
    try:
        rows = db.query(InterviewCandidate).filter(InterviewCandidate.id.in_(candidate_ids)).all()
        assert {row.status for row in rows} == {InterviewCandidateStatus.ARCHIVED}
        assert db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_CANDIDATE_BULK_ARCHIVE").count() == 1
    finally:
        db.close()


def test_bulk_archive_enforces_permission_and_handles_edge_cases():
    agent = Employee(
        id=99992,
        name="Blocked Agent",
        email="blocked_bulk_agent@example.com",
        role=UserRole.AGENT,
        employee_code="BLOCKED_BULK_AGENT",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: agent
    forbidden = client.post(
        "/api/hr/interviews/candidates/bulk-archive",
        json={"candidate_ids": [1], "note": "Should fail"},
    )
    assert forbidden.status_code == 403

    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Bulk Edge Case Role",
            "description": "Edge case handling for bulk archive.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    )
    assert job.status_code == 200
    job_id = job.json()["id"]

    active_ids = []
    for index in range(3):
        candidate = client.post(
            "/api/hr/interviews/candidates",
            json={
                "job_id": job_id,
                "full_name": f"Edge Candidate {index}",
                "contact_email": f"edge{index}@example.com",
            },
        )
        assert candidate.status_code == 200
        active_ids.append(candidate.json()["id"])

    pre_archived_id = active_ids[0]
    archive_one = client.post(
        f"/api/hr/interviews/candidates/{pre_archived_id}/archive",
        json={"note": "Pre-archive"},
    )
    assert archive_one.status_code == 200

    missing_id = 9999999
    duplicate_payload = [active_ids[1], active_ids[1], active_ids[2], pre_archived_id, missing_id]
    response = client.post(
        "/api/hr/interviews/candidates/bulk-archive",
        json={"candidate_ids": duplicate_payload, "note": "Edge case bulk"},
    )
    assert response.status_code == 200
    body = response.json()
    unique_count = len(dict.fromkeys(duplicate_payload))
    assert body["requested"] == unique_count
    assert body["updated"] == 2
    assert body["skipped"] == 2
    assert set(body["candidate_ids"]) == {active_ids[1], active_ids[2]}

    db = SessionLocal()
    try:
        for cid in [active_ids[1], active_ids[2]]:
            row = db.query(InterviewCandidate).filter(InterviewCandidate.id == cid).first()
            assert row is not None
            assert row.status == InterviewCandidateStatus.ARCHIVED
            assert row.archived_at is not None

        pre_archived_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == pre_archived_id).first()
        assert pre_archived_row is not None
        assert pre_archived_row.status == InterviewCandidateStatus.ARCHIVED

        workflow_events = (
            db.query(InterviewWorkflowEvent)
            .filter(
                InterviewWorkflowEvent.candidate_id.in_([active_ids[1], active_ids[2]]),
                InterviewWorkflowEvent.event_type == "CANDIDATE_BULK_ARCHIVED"
            )
            .all()
        )
        assert len(workflow_events) == 2
        for event in workflow_events:
            assert event.event_type == "CANDIDATE_BULK_ARCHIVED"
            assert event.to_status == "archived"
            assert event.actor_id == hr.id

        audit = db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_CANDIDATE_BULK_ARCHIVE").first()
        assert audit is not None
        assert audit.actor_id == hr.id
        assert f"updated={2}" in (audit.after_state or "")
    finally:
        db.close()


def test_invite_appends_cv_ai_questions_when_cv_text_is_available():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "CV AI Role",
            "description": "CV-driven question generation.",
            "status": "open",
            "base_questions": ["Introduce yourself"],
            "department": "Sales",
        },
    )
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "CV Candidate",
            "contact_email": "cv-candidate@example.com",
        },
    )
    candidate_id = candidate.json()["id"]

    upload = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/documents",
        data={"document_type": "cv"},
        files={"file": ("resume.txt", io.BytesIO(b"Skills: negotiation, objection handling, CRM systems"), "text/plain")},
    )
    assert upload.status_code == 200

    invite = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/invite",
        json={"expires_in_hours": 12},
    )
    assert invite.status_code == 200
    assert invite.json()["question_count"] >= 2

    db = SessionLocal()
    try:
        questions = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.candidate_id == candidate_id)
            .order_by(InterviewQuestion.display_order.asc())
            .all()
        )
        cv_ai_questions = [question for question in questions if question.source == InterviewQuestionSource.CV_AI]
        assert cv_ai_questions
        assert all("[email]" not in question.question_text for question in cv_ai_questions)
        assert all("@" not in question.question_text for question in cv_ai_questions)
    finally:
        db.close()


def test_interview_document_upload_rejects_invalid_extension():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Upload Validation Role",
            "description": "Document validation flow.",
            "status": "open",
            "base_questions": ["Introduce yourself"],
            "department": "Sales",
        },
    )
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Upload Validation Candidate",
            "contact_email": "upload-validation@example.com",
        },
    )

    upload = client.post(
        f"/api/hr/interviews/candidates/{candidate.json()['id']}/documents",
        data={"document_type": "cv"},
        files={"file": ("resume.exe", io.BytesIO(b"fake"), "application/octet-stream")},
    )
    assert upload.status_code == 400
    assert "Invalid document type" in upload.json()["detail"]


def test_hr_export_of_interview_candidates_is_redacted_and_admin_can_request_full_pii():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Export Role",
            "description": "Export governance flow.",
            "status": "open",
            "base_questions": ["Question one"],
            "department": "Sales",
        },
    )
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job.json()["id"],
            "full_name": "Export Candidate",
            "contact_email": "export.candidate@example.com",
            "phone_number": "01098765432",
            "national_id": "30101011234567",
        },
    )
    candidate_id = candidate.json()["id"]

    redacted_export = client.get("/api/hr/interviews/export/candidates.csv")
    assert redacted_export.status_code == 200
    redacted_csv = redacted_export.text
    assert "export.candidate@example.com" not in redacted_csv
    assert "01098765432" not in redacted_csv
    assert "******5432" in redacted_csv
    assert ",4567," not in redacted_csv

    denied_full = client.get("/api/hr/interviews/export/candidates.csv?include_pii=true")
    assert denied_full.status_code == 403

    admin = Employee(
        id=99981,
        name="Interview Export Admin",
        email="interview_export_admin@example.com",
        role=UserRole.ADMIN,
        employee_code="INT_EXPORT_ADMIN",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    full_export = client.get("/api/hr/interviews/export/candidates.csv?include_pii=true")
    assert full_export.status_code == 200
    full_csv = full_export.text
    assert "export.candidate@example.com" in full_csv
    assert "01098765432" in full_csv
    assert ",4567," in full_csv

    db = SessionLocal()
    try:
        export_audits = db.query(AuditEvent).filter(AuditEvent.target == "Interview Candidate Export").all()
        assert len(export_audits) >= 3
        assert any(audit.success is False and audit.reason == "PII export requires admin role" for audit in export_audits)
        assert any(audit.success is True and "include_pii=False" in (audit.after_state or "") for audit in export_audits)
        assert any(audit.success is True and "include_pii=True" in (audit.after_state or "") for audit in export_audits)
        stored_candidate = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert stored_candidate is not None
    finally:
        db.close()


def test_candidate_notify_and_bulk_notify_flow():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create a job and candidates
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Notification Specialist",
            "description": "Handles communications.",
            "status": "open",
            "base_questions": ["What is your communication style?"],
        },
    ).json()
    job_id = job["id"]

    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Alice Communicator",
            "contact_email": "alice@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    # 2. Test single notify with a generic template (application_received)
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True) as mock_send:
        resp = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/notify",
            json={"template": "application_received", "context": {"job_title": "Custom Job Title"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["candidate_id"] == candidate_id
        assert body["template"] == "application_received"
        mock_send.assert_called_once_with(
            destination_email="alice@example.com",
            candidate_name="Alice Communicator",
            template="application_received",
            context={"job_title": "Custom Job Title"},
        )

    # Verify audit event and workflow event
    db = SessionLocal()
    try:
        w_event = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "INTERVIEW_EMAIL_SENT"
        ).first()
        assert w_event is not None
        assert w_event.event_payload["template"] == "application_received"

        a_event = db.query(AuditEvent).filter(
            AuditEvent.action == "INTERVIEW_EMAIL_SENT",
            AuditEvent.target == f"InterviewCandidate #{candidate_id}"
        ).first()
        assert a_event is not None
        assert a_event.success is True
    finally:
        db.close()

    # 3. Test single notify for interview_invite when NO invite exists yet.
    # This should automatically trigger the session creation sequence.
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True) as mock_send_invite:
        resp_invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/notify",
            json={"template": "interview_invite"},
        )
        assert resp_invite.status_code == 200
        body_invite = resp_invite.json()
        assert body_invite["success"] is True
        
        # Verify a session was created in DB
        db = SessionLocal()
        try:
            session = db.query(InterviewSession).filter(
                InterviewSession.candidate_id == candidate_id
            ).first()
            assert session is not None
            assert session.status == InterviewSessionStatus.INVITED
            
            # Check workflow event for invite
            invite_w_event = db.query(InterviewWorkflowEvent).filter(
                InterviewWorkflowEvent.candidate_id == candidate_id,
                InterviewWorkflowEvent.event_type == "CANDIDATE_INVITED"
            ).first()
            assert invite_w_event is not None
        finally:
            db.close()

    # 4. Test bulk notify
    candidate2 = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Bob Mailer",
            "contact_email": "bob@example.com",
        },
    ).json()
    candidate2_id = candidate2["id"]

    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True) as mock_send_bulk:
        bulk_resp = client.post(
            "/api/hr/interviews/candidates/bulk-notify",
            json={
                "candidate_ids": [candidate_id, candidate2_id],
                "template": "accepted",
            },
        )
        assert bulk_resp.status_code == 200
        bulk_body = bulk_resp.json()
        assert bulk_body["success_count"] == 2
        assert bulk_body["failed_count"] == 0
        assert bulk_body["total"] == 2
        assert len(bulk_body["results"]) == 2
        assert mock_send_bulk.call_count == 2

    # 5. Test access control: non-staff or staff without permission
    agent = Employee(
        id=99993,
        name="Regular Agent",
        email="agent_notify@example.com",
        role=UserRole.AGENT,
        employee_code="AGENT_NOTIFY",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: agent

    forbidden_single = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/notify",
        json={"template": "application_received"},
    )
    assert forbidden_single.status_code == 403

    forbidden_bulk = client.post(
        "/api/hr/interviews/candidates/bulk-notify",
        json={
            "candidate_ids": [candidate_id],
            "template": "application_received",
        },
    )
    assert forbidden_bulk.status_code == 403


def test_candidate_decision_pipeline_and_state_machine():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create a job
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Pipeline Architect",
            "description": "Build pipelines.",
            "status": "open",
            "base_questions": ["Tell us about pipelines."],
        },
    ).json()
    job_id = job["id"]

    # 2. Create a candidate (status: applied)
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Bob Builder",
            "contact_email": "bob@example.com",
        },
    ).json()
    candidate_id = candidate["id"]
    assert candidate["status"] == "applied"

    # 3. Test invalid transition (applied -> shortlisted) should return 400
    resp = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/shortlist",
        json={"note": "Try shortlist from applied"},
    )
    assert resp.status_code == 400
    assert "Invalid candidate status transition" in resp.json()["detail"]

    # 4. Invite candidate (applied -> interviewing)
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True):
        resp_invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/invite",
            json={"expires_in_hours": 24},
        )
        assert resp_invite.status_code == 200

    db = SessionLocal()
    try:
        cand_db = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert cand_db.status == InterviewCandidateStatus.INTERVIEWING
        
        # Manually transition candidate to evaluated to simulate answering
        cand_db.status = InterviewCandidateStatus.EVALUATED
        db.commit()
    finally:
        db.close()

    # 5. Transition to shortlisted (evaluated -> shortlisted)
    resp_shortlist = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/shortlist",
        json={"note": "Shortlisted candidate", "send_email": False},
    )
    assert resp_shortlist.status_code == 200
    assert resp_shortlist.json()["status"] == "shortlisted"

    # Verify audit event and workflow event for shortlisted
    db = SessionLocal()
    try:
        w_event = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_SHORTLISTED"
        ).first()
        assert w_event is not None
        assert w_event.note == "Shortlisted candidate"

        a_event = db.query(AuditEvent).filter(
            AuditEvent.action == "INTERVIEW_CANDIDATE_SHORTLISTED",
            AuditEvent.target == f"InterviewCandidate #{candidate_id}"
        ).first()
        assert a_event is not None
    finally:
        db.close()

    # 6. Archive candidate (shortlisted -> archived)
    resp_archive = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/archive",
        json={"note": "Archived candidate", "send_email": False},
    )
    assert resp_archive.status_code == 200
    assert resp_archive.json()["status"] == "archived"

    # 7. Attempt restore from archived (archived -> applied)
    resp_restore = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/restore",
        json={"note": "Restore from archive"},
    )
    assert resp_restore.status_code == 200
    assert resp_restore.json()["status"] == "applied"

    # Verify workflow event for restore
    db = SessionLocal()
    try:
        w_event = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_RESTORED"
        ).first()
        assert w_event is not None
        assert w_event.note == "Restore from archive"
    finally:
        db.close()


def test_candidate_convert_requires_accepted_status():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Conversion Gate Role",
            "description": "Conversion gatekeeping.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    ).json()
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "Gate Candidate",
            "contact_email": "gate@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    rejected = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={
            "employee_code": "901",
            "role": "agent",
            "otp_email": "gate@example.com",
            "password": "Eiacs$1234#",
        },
    )
    assert rejected.status_code == 400
    assert "accepted candidates" in rejected.json()["detail"].lower()


def test_candidate_auto_transition_to_evaluated_real_flow():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create a job with mcq_enabled = True and configured MCQ questions
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Outbound Call Representative",
            "description": "Sales representation.",
            "status": "open",
            "base_questions": ["What is your background?", "Handle a rejection."],
            "mcq_enabled": True,
            "mcq_questions": [
                {
                    "category": "iq",
                    "question": "What is 2+2?",
                    "options": ["3", "4", "5"],
                    "correct": 1,
                    "type": "pattern",
                }
            ],
        },
    ).json()
    job_id = job["id"]

    # 2. Create candidate
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "John Doe",
            "contact_email": "john.doe@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    # 3. Invite candidate (moves candidate to interviewing)
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True):
        invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/invite",
            json={"expires_in_hours": 24},
        ).json()
    session_token = invite["session_token"]
    portal_headers = {"X-Interview-Session-Token": session_token}

    # 4. Submit voice answers (starts as pending)
    questions = client.get("/api/interview-portal/questions", headers=portal_headers).json()
    for question in questions:
        submit_ans = client.post(
            f"/api/interview-portal/questions/{question['id']}/answer",
            headers=portal_headers,
            data={"transcript_text": "Answer transcript here"},
        )
        assert submit_ans.status_code == 200

    # 5. Submit MCQ
    submit_mcq = client.post(
        "/api/interview-portal/mcq",
        headers=portal_headers,
        json={"answers": {"1": 1}},
    )
    assert submit_mcq.status_code == 200

    db = SessionLocal()
    try:
        cand_db = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert cand_db.status == InterviewCandidateStatus.INTERVIEWING

        # 6. Complete the session
        complete = client.post("/api/interview-portal/complete", headers=portal_headers)
        assert complete.status_code == 200
        # Check that candidate status is still interviewing (awaiting evaluation of voice answers)
        assert complete.json()["candidate_status"] == "interviewing"

        # 7. Simulate background worker evaluating the answers
        answers = db.query(InterviewAnswer).filter(InterviewAnswer.candidate_id == candidate_id).all()
        assert len(answers) == 2
        for idx, ans in enumerate(answers):
            ans.status = InterviewAnswerStatus.EVALUATED
            ans.overall_score = 4.0 + idx

        # Trigger workflow sync as worker would do
        before, after = sync_candidate_interview_state(db, cand_db)
        db.commit()

        assert before == "interviewing"
        assert after == "evaluated"
        assert cand_db.status == InterviewCandidateStatus.EVALUATED
        assert cand_db.final_score == 4.5  # average of 4.0 and 5.0
    finally:
        db.close()


def test_candidate_auto_transition_to_evaluated_no_mcq():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create a job with mcq_enabled = False
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Voice Agent Specialist",
            "description": "Customer support by voice.",
            "status": "open",
            "base_questions": ["Introduce yourself.", "Describe a time you handled a difficult caller."],
            "mcq_enabled": False,
        },
    ).json()
    job_id = job["id"]

    # 2. Create candidate
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Alice Smith",
            "contact_email": "alice.smith@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    # 3. Invite candidate (moves candidate to interviewing)
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True):
        invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/invite",
            json={"expires_in_hours": 24},
        ).json()
    session_token = invite["session_token"]
    portal_headers = {"X-Interview-Session-Token": session_token}

    # 4. Submit voice answers
    questions = client.get("/api/interview-portal/questions", headers=portal_headers).json()
    for question in questions:
        submit_ans = client.post(
            f"/api/interview-portal/questions/{question['id']}/answer",
            headers=portal_headers,
            data={"transcript_text": "Alice voice answer"},
        )
        assert submit_ans.status_code == 200

    db = SessionLocal()
    try:
        cand_db = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert cand_db.status == InterviewCandidateStatus.INTERVIEWING

        # 5. Complete the session
        complete = client.post("/api/interview-portal/complete", headers=portal_headers)
        assert complete.status_code == 200
        assert complete.json()["candidate_status"] == "interviewing"

        # 6. Simulate evaluation of answers
        answers = db.query(InterviewAnswer).filter(InterviewAnswer.candidate_id == candidate_id).all()
        assert len(answers) == 2
        for idx, ans in enumerate(answers):
            ans.status = InterviewAnswerStatus.EVALUATED
            ans.overall_score = 5.0 + idx

        # Trigger workflow sync as worker would do and log CANDIDATE_EVALUATED
        from app.services.interview_workflow import create_interview_workflow_event
        before, after = sync_candidate_interview_state(db, cand_db)
        if before != after and after == InterviewCandidateStatus.EVALUATED.value:
            create_interview_workflow_event(
                db,
                candidate_id=candidate_id,
                event_type="CANDIDATE_EVALUATED",
                from_status=before,
                to_status=after,
                note="All interview answers reached terminal evaluation state",
                event_payload={"final_score": cand_db.final_score},
            )
        db.commit()

        assert before == "interviewing"
        assert after == "evaluated"
        assert cand_db.status == InterviewCandidateStatus.EVALUATED
        assert cand_db.final_score == 5.5

        # Check workflow event
        w_event = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_EVALUATED"
        ).first()
        assert w_event is not None
        assert w_event.event_payload["final_score"] == 5.5
    finally:
        db.close()


def test_candidate_mcq_gating_for_evaluated_transition():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create job with MCQ enabled
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "MCQ Gated Agent",
            "description": "Requires MCQ check.",
            "status": "open",
            "base_questions": ["What is your background?", "Handle a rejection."],
            "mcq_enabled": True,
            "mcq_questions": [
                {
                    "category": "iq",
                    "question": "What is 2+2?",
                    "options": ["3", "4", "5"],
                    "correct": 1,
                    "type": "pattern",
                }
            ],
        },
    ).json()
    job_id = job["id"]

    # 2. Create candidate
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Bob Jones",
            "contact_email": "bob.jones@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    # 3. Invite candidate (moves candidate to interviewing)
    with patch("app.routers.interviews.send_interview_candidate_email", return_value=True):
        invite = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/invite",
            json={"expires_in_hours": 24},
        ).json()
    session_token = invite["session_token"]
    portal_headers = {"X-Interview-Session-Token": session_token}

    # 4. Submit voice answers
    questions = client.get("/api/interview-portal/questions", headers=portal_headers).json()
    for question in questions:
        submit_ans = client.post(
            f"/api/interview-portal/questions/{question['id']}/answer",
            headers=portal_headers,
            data={"transcript_text": "Bob voice answer"},
        )
        assert submit_ans.status_code == 200

    db = SessionLocal()
    try:
        cand_db = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert cand_db.status == InterviewCandidateStatus.INTERVIEWING

        # 5. Manually complete the session in DB to bypass the /complete validation gate for testing MCQ-only transition
        from datetime import datetime, timezone
        session_db = db.query(InterviewSession).filter(InterviewSession.candidate_id == candidate_id).first()
        session_db.status = InterviewSessionStatus.COMPLETED
        session_db.completed_at = datetime.now(timezone.utc)
        cand_db.completed_at = session_db.completed_at
        db.commit()

        # 6. Evaluate all voice answers
        answers = db.query(InterviewAnswer).filter(InterviewAnswer.candidate_id == candidate_id).all()
        assert len(answers) == 2
        for idx, ans in enumerate(answers):
            ans.status = InterviewAnswerStatus.EVALUATED
            ans.overall_score = 6.0 + idx

        # Trigger workflow sync as worker would do.
        # Should remain interviewing because MCQ is enabled but not submitted.
        before, after = sync_candidate_interview_state(db, cand_db)
        db.commit()

        assert before == "interviewing"
        assert after == "interviewing"
        assert cand_db.status == InterviewCandidateStatus.INTERVIEWING

        # 7. Submit MCQ now. This endpoint calls sync_candidate_interview_state internally
        # and should trigger the transition to evaluated and log the CANDIDATE_EVALUATED workflow event.
        submit_mcq = client.post(
            "/api/interview-portal/mcq",
            headers=portal_headers,
            json={"answers": {"1": 1}},
        )
        assert submit_mcq.status_code == 200

        # Refresh candidate from DB
        db.refresh(cand_db)
        assert cand_db.status == InterviewCandidateStatus.EVALUATED
        assert cand_db.final_score == 6.5

        # Check workflow event from MCQ submission path
        w_event = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_EVALUATED"
        ).first()
        assert w_event is not None
        assert w_event.event_payload["final_score"] == 6.5
    finally:
        db.close()


def test_candidate_timeline_endpoint_and_sanitization():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    # 1. Create candidate
    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Timeline Specialist",
            "description": "Verification of logs.",
            "status": "open",
            "base_questions": ["What is logging?"],
            "mcq_enabled": False,
        },
    ).json()
    job_id = job["id"]

    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job_id,
            "full_name": "Charlie Log",
            "contact_email": "charlie.log@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    db = SessionLocal()
    try:
        # 2. Add workflow event with sensitive event_payload
        from app.services.interview_workflow import create_interview_workflow_event
        create_interview_workflow_event(
            db,
            candidate_id=candidate_id,
            actor_id=hr.id,
            event_type="TEST_TIMELINE_EVENT",
            note="Testing details",
            event_payload={
                "safe_score": 85.0,
                "sensitive_token": "secret_abc123",
                "nested": {
                    "sensitive_email": "hidden@example.com",
                    "safe_value": "all good"
                }
            }
        )
        db.commit()

        # 3. Request timeline (should succeed with VIEW_INTERVIEW_CANDIDATES role/permissions)
        resp = client.get(f"/api/hr/interviews/candidates/{candidate_id}/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        
        # Verify newest first (since we just created CANDIDATE_CREATED / TEST_TIMELINE_EVENT)
        # Verify event properties and sanitization
        target_event = [e for e in data if e["event_type"] == "TEST_TIMELINE_EVENT"][0]
        assert target_event["note"] == "Testing details"
        assert target_event["actor_name"] == hr.name
        
        payload = target_event["event_payload"]
        assert payload["safe_score"] == 85.0
        assert payload["sensitive_token"] == "[MASKED]"
        assert payload["nested"]["sensitive_email"] == "[MASKED]"
        assert payload["nested"]["safe_value"] == "all good"

        # 4. Verify limit query param
        resp_limit = client.get(f"/api/hr/interviews/candidates/{candidate_id}/timeline?limit=1")
        assert resp_limit.status_code == 200
        assert len(resp_limit.json()) == 1

        # 5. Verify event_type query param
        resp_type = client.get(f"/api/hr/interviews/candidates/{candidate_id}/timeline?event_type=TEST_TIMELINE_EVENT")
        assert resp_type.status_code == 200
        events_filtered = resp_type.json()
        assert all(e["event_type"] == "TEST_TIMELINE_EVENT" for e in events_filtered)

        # 6. Verify permission check (anonymous/insufficient role/permissions denied)
        # Clear override or set to a non-HR/non-staff user
        non_staff = Employee(
            name="Ordinary Agent",
            email="agent@example.com",
            role=UserRole.AGENT,
            employee_code="AGENT_001",
            hashed_password="fake",
            status="active"
        )
        app.dependency_overrides[get_current_user] = lambda: non_staff
        resp_denied = client.get(f"/api/hr/interviews/candidates/{candidate_id}/timeline")
        assert resp_denied.status_code == 403
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_conversion_rejects_malformed_employee_code():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Malformed Code Role",
            "description": "Reject bad codes.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    ).json()
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "Malformed Candidate",
            "contact_email": "malformed@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    db = SessionLocal()
    try:
        row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        row.status = InterviewCandidateStatus.ACCEPTED
        db.commit()
    finally:
        db.close()

    resp = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={"employee_code": "", "role": "agent", "password": "Eiacs$1234#"},
    )
    assert resp.status_code == 422, f"Expected 422 for empty employee_code, got {resp.status_code}"

    bad_codes_400 = ["   ", "code with spaces", "CODE@WITH@SYMBOLS"]
    for code in bad_codes_400:
        resp = client.post(
            f"/api/hr/interviews/candidates/{candidate_id}/convert",
            json={"employee_code": code, "role": "agent", "password": "Eiacs$1234#"},
        )
        assert resp.status_code == 400, f"Expected 400 for code={code!r}, got {resp.status_code}"

    resp = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={"employee_code": "a" * 51, "role": "agent", "password": "Eiacs$1234#"},
    )
    assert resp.status_code == 422, f"Expected 422 for overlong employee_code, got {resp.status_code}"


def test_conversion_rejects_duplicate_email_and_national_id():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Duplicate Check Role",
            "description": "Duplicate conflict checks.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    ).json()
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "Dup Check Candidate",
            "contact_email": "dupcheck@example.com",
            "national_id": "30101011234567",
        },
    ).json()
    candidate_id = candidate["id"]

    db = SessionLocal()
    try:
        row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        row.status = InterviewCandidateStatus.ACCEPTED
        db.commit()

        existing_emp = Employee(
            name="Existing Employee",
            email="emp-dupcheck@eiacs.com",
            employee_code="DUP_EXISTING",
            hashed_password="fake",
            role=UserRole.AGENT,
            status="active",
        )
        db.add(existing_emp)
        db.commit()
    finally:
        db.close()

    email_conflict = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={"employee_code": "dupcheck", "role": "agent", "password": "Eiacs$1234#"},
    )
    assert email_conflict.status_code == 409
    assert "email" in email_conflict.json()["detail"].lower()

    db = SessionLocal()
    try:
        cand_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        assert cand_row.converted_employee_id is None
    finally:
        db.close()

    national_candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "National ID Candidate",
            "contact_email": "national-conflict@example.com",
            "national_id": "30101011234567",
        },
    ).json()
    national_candidate_id = national_candidate["id"]

    db = SessionLocal()
    try:
        nat_row = db.query(InterviewCandidate).filter(InterviewCandidate.id == national_candidate_id).first()
        nat_row.status = InterviewCandidateStatus.ACCEPTED
        db.add(
            Employee(
                name="National ID Employee",
                email="emp-national@eiacs.com",
                employee_code="NAT_ID_EXISTING",
                hashed_password="fake",
                role=UserRole.AGENT,
                status="active",
                national_id_hash=hash_national_id("30101011234567"),
            )
        )
        db.commit()
    finally:
        db.close()

    national_conflict = client.post(
        f"/api/hr/interviews/candidates/{national_candidate_id}/convert",
        json={"employee_code": "NAT_CHECK", "role": "agent", "password": "Eiacs$1234#"},
    )
    assert national_conflict.status_code == 409
    assert "national id" in national_conflict.json()["detail"].lower()


def test_repeated_convert_call_is_idempotent_and_emits_events_once():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Idempotent Role",
            "description": "Idempotency checks.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    ).json()
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "Idempotent Candidate",
            "contact_email": "idempotent@example.com",
        },
    ).json()
    candidate_id = candidate["id"]

    db = SessionLocal()
    try:
        row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        row.status = InterviewCandidateStatus.ACCEPTED
        db.commit()
    finally:
        db.close()

    first = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={"employee_code": "IDEMPOTENT", "role": "agent", "password": "Eiacs$1234#"},
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["employee_code"] == "IDEMPOTENT"

    second = client.post(
        f"/api/hr/interviews/candidates/{candidate_id}/convert",
        json={"employee_code": "IDEMPOTENT", "role": "agent", "password": "Eiacs$1234#"},
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["employee_id"] == first_body["employee_id"]
    assert second_body["employee_code"] == "IDEMPOTENT"

    db = SessionLocal()
    try:
        convert_audits = db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_CANDIDATE_CONVERT").all()
        assert len(convert_audits) == 1

        convert_workflow = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_CONVERTED_TO_EMPLOYEE",
        ).all()
        assert len(convert_workflow) == 1

        handoff_workflow = db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate_id,
            InterviewWorkflowEvent.event_type == "ONBOARDING_HANDOFF",
        ).all()
        assert len(handoff_workflow) == 1
        assert handoff_workflow[0].event_payload is not None
        assert handoff_workflow[0].event_payload["employee_code"] == "IDEMPOTENT"
    finally:
        db.close()


def test_onboarding_readiness_reports_conflict_categories():
    hr = _seed_hr_user()
    app.dependency_overrides[get_current_user] = lambda: hr

    job = client.post(
        "/api/hr/interviews/jobs",
        json={
            "title": "Category Role",
            "description": "Category checks.",
            "status": "open",
            "base_questions": ["Question one"],
        },
    ).json()
    candidate = client.post(
        "/api/hr/interviews/candidates",
        json={
            "job_id": job["id"],
            "full_name": "Category Candidate",
            "contact_email": "category@example.com",
            "national_id": "40101011234567",
        },
    ).json()
    candidate_id = candidate["id"]

    db = SessionLocal()
    try:
        row = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate_id).first()
        row.status = InterviewCandidateStatus.ACCEPTED
        db.commit()

        db.add(
            Employee(
                name="Category Employee",
                email="emp-category@eiacs.com",
                employee_code=str(candidate_id),
                hashed_password="fake",
                role=UserRole.AGENT,
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/api/hr/interviews/candidates/{candidate_id}/onboarding-readiness")
    assert resp.status_code == 200
    body = resp.json()
    assert "employee_code" in body["blocking_categories"]
    assert any("employee code" in reason.lower() for reason in body["blocking_reasons"])
