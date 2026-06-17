from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Campaign,
    Employee,
    InterviewAnswer,
    InterviewAnswerStatus,
    InterviewCandidate,
    InterviewCandidateStatus,
    InterviewJob,
    InterviewJobStatus,
    InterviewQuestion,
    InterviewQuestionSource,
    InterviewSession,
    InterviewSessionStatus,
    InterviewWorkflowEvent,
    Team,
    UserRole,
)
from app.permissions import Permission, ROLE_PERMISSIONS
from app.services.role_permissions import get_role_permission_values


def seed_interview_fixture() -> dict[str, int]:
    db: Session = SessionLocal()
    try:
        hr = Employee(
            name="Interview HR",
            email="interview_hr@example.com",
            role=UserRole.HR_MANAGER,
            employee_code="INT_HR",
            hashed_password="fake",
            status="active",
        )
        converted_employee = Employee(
            name="Interview Employee",
            email="interview_employee@example.com",
            role=UserRole.AGENT,
            employee_code="INT_EMP",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name="Interview Campaign",
            evaluation_prompt="Prompt long enough for interview test campaign.",
            color="#123456",
        )
        db.add_all([hr, converted_employee, campaign])
        db.commit()
        db.refresh(hr)
        db.refresh(converted_employee)
        db.refresh(campaign)

        team = Team(
            name="Interview Team",
            campaign_id=campaign.id,
            manager_id=hr.id,
            leader_id=hr.id,
            is_active=True,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        job = InterviewJob(
            title="Sales Recruiter",
            description="Evaluate voice and interview readiness.",
            department="HR",
            team_id=team.id,
            campaign_id=campaign.id,
            status=InterviewJobStatus.OPEN,
            base_questions=["Tell me about yourself"],
            created_by_id=hr.id,
            updated_by_id=hr.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return {
            "hr_id": hr.id,
            "converted_employee_id": converted_employee.id,
            "campaign_id": campaign.id,
            "team_id": team.id,
            "job_id": job.id,
        }
    finally:
        db.close()


def test_hr_manager_role_permissions_include_interview_permissions():
    db = SessionLocal()
    try:
        permissions = set(get_role_permission_values(db, UserRole.HR_MANAGER))
    finally:
        db.close()

    assert Permission.MANAGE_INTERVIEW_JOBS.value in permissions
    assert Permission.VIEW_INTERVIEW_CANDIDATES.value in permissions
    assert Permission.MANAGE_INTERVIEW_CANDIDATES.value in permissions
    assert Permission.REVIEW_INTERVIEW_EVALUATIONS.value in permissions
    assert Permission.CONVERT_INTERVIEW_CANDIDATES.value in permissions
    assert Permission.EXPORT_INTERVIEW_DATA.value in permissions
    assert Permission.MANAGE_INTERVIEW_JOBS in ROLE_PERMISSIONS[UserRole.HR_MANAGER]


def test_interview_candidate_unique_email_per_job():
    fixture = seed_interview_fixture()
    db = SessionLocal()
    try:
        first = InterviewCandidate(
            job_id=fixture["job_id"],
            full_name="Candidate One",
            contact_email="candidate@example.com",
            contact_email_normalized="candidate@example.com",
            phone_number="01000000001",
            phone_normalized="01000000001",
            national_id_hash="hash-1",
            national_id_last4="1234",
            status=InterviewCandidateStatus.APPLIED,
            created_by_id=fixture["hr_id"],
        )
        db.add(first)
        db.commit()

        duplicate = InterviewCandidate(
            job_id=fixture["job_id"],
            full_name="Candidate Two",
            contact_email="Candidate@example.com",
            contact_email_normalized="candidate@example.com",
            status=InterviewCandidateStatus.SCREENING,
            created_by_id=fixture["hr_id"],
        )
        db.add(duplicate)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_interview_candidate_converted_employee_must_be_unique():
    fixture = seed_interview_fixture()
    db = SessionLocal()
    try:
        first = InterviewCandidate(
            job_id=fixture["job_id"],
            full_name="Candidate One",
            contact_email="one@example.com",
            contact_email_normalized="one@example.com",
            converted_employee_id=fixture["converted_employee_id"],
            created_by_id=fixture["hr_id"],
        )
        second = InterviewCandidate(
            job_id=fixture["job_id"],
            full_name="Candidate Two",
            contact_email="two@example.com",
            contact_email_normalized="two@example.com",
            converted_employee_id=fixture["converted_employee_id"],
            created_by_id=fixture["hr_id"],
        )
        db.add(first)
        db.commit()
        db.add(second)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_interview_session_answer_and_workflow_relationships_persist():
    fixture = seed_interview_fixture()
    db = SessionLocal()
    try:
        candidate = InterviewCandidate(
            job_id=fixture["job_id"],
            full_name="Candidate Three",
            contact_email="three@example.com",
            contact_email_normalized="three@example.com",
            created_by_id=fixture["hr_id"],
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        session = InterviewSession(
            candidate_id=candidate.id,
            job_id=fixture["job_id"],
            session_token_hash="token-hash-1",
            status=InterviewSessionStatus.INVITED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        question = InterviewQuestion(
            job_id=fixture["job_id"],
            session_id=session.id,
            candidate_id=candidate.id,
            question_text="Introduce yourself.",
            expected_skills_tags=["communication", "confidence"],
            source=InterviewQuestionSource.BASE,
            display_order=1,
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        answer = InterviewAnswer(
            session_id=session.id,
            candidate_id=candidate.id,
            question_id=question.id,
            status=InterviewAnswerStatus.EVALUATED,
            transcribed_text="My name is candidate three.",
            overall_score=88.5,
        )
        event = InterviewWorkflowEvent(
            candidate_id=candidate.id,
            actor_id=fixture["hr_id"],
            event_type="CANDIDATE_CREATED",
            to_status=InterviewCandidateStatus.APPLIED.value,
            event_payload={"source": "hr_manual"},
        )
        db.add_all([answer, event])
        db.commit()

        stored_candidate = db.query(InterviewCandidate).filter(InterviewCandidate.id == candidate.id).first()
        assert stored_candidate is not None
        assert stored_candidate.sessions[0].session_token_hash == "token-hash-1"
        assert stored_candidate.answers[0].overall_score == 88.5
        assert stored_candidate.workflow_events[0].event_payload == {"source": "hr_manual"}
    finally:
        db.close()
