from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models import (
    AuditEvent,
    Campaign,
    Employee,
    InterviewAnswer,
    InterviewAnswerStatus,
    InterviewCandidate,
    InterviewCandidateDocument,
    InterviewCandidateStatus,
    InterviewJob,
    InterviewJobStatus,
    InterviewQuestion,
    InterviewQuestionSource,
    InterviewSession,
    InterviewSessionStatus,
    Team,
    UserRole,
)
from app.routers.auth import get_current_user

client = TestClient(app)


def _seed_archived_candidate_fixture(tmp_path: Path, *, archived_days_ago: int = 120) -> dict[str, int | str]:
    db: Session = SessionLocal()
    try:
        hr = Employee(
            name="Retention HR",
            email=f"retention_hr_{datetime.now().timestamp()}@example.com",
            role=UserRole.HR_MANAGER,
            employee_code=f"RET_HR_{int(datetime.now().timestamp() * 1000)}",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name=f"Retention Campaign {datetime.now().timestamp()}",
            evaluation_prompt="Prompt long enough for interview retention tests.",
            color="#556677",
        )
        db.add_all([hr, campaign])
        db.commit()
        db.refresh(hr)
        db.refresh(campaign)

        team = Team(
            name=f"Retention Team {datetime.now().timestamp()}",
            campaign_id=campaign.id,
            manager_id=hr.id,
            leader_id=hr.id,
            is_active=True,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        job = InterviewJob(
            title="Retention Job",
            description="Retention cleanup coverage.",
            department="HR",
            team_id=team.id,
            campaign_id=campaign.id,
            status=InterviewJobStatus.OPEN,
            base_questions=["Question one"],
            created_by_id=hr.id,
            updated_by_id=hr.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        candidate = InterviewCandidate(
            job_id=job.id,
            full_name="Archived Candidate",
            contact_email=f"retention_candidate_{datetime.now().timestamp()}@example.com",
            contact_email_normalized=f"retention_candidate_{datetime.now().timestamp()}@example.com",
            status=InterviewCandidateStatus.ARCHIVED,
            archived_at=datetime.now(timezone.utc) - timedelta(days=archived_days_ago),
            created_by_id=hr.id,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        session = InterviewSession(
            candidate_id=candidate.id,
            job_id=job.id,
            session_token_hash=f"retention-token-{candidate.id}",
            status=InterviewSessionStatus.COMPLETED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            question_count=1,
            completed_at=datetime.now(timezone.utc) - timedelta(days=archived_days_ago),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        question = InterviewQuestion(
            job_id=job.id,
            session_id=session.id,
            candidate_id=candidate.id,
            question_text="Question one",
            source=InterviewQuestionSource.BASE,
            display_order=1,
        )
        db.add(question)
        db.commit()
        db.refresh(question)

        document_path = tmp_path / f"candidate_{candidate.id}_cv.txt"
        document_path.write_text("cv content", encoding="utf-8")
        audio_path = tmp_path / f"candidate_{candidate.id}_answer.webm"
        audio_path.write_bytes(b"audio-content")

        document = InterviewCandidateDocument(
            candidate_id=candidate.id,
            document_type="cv",
            original_filename="cv.txt",
            storage_path=str(document_path),
            content_type="text/plain",
            file_size_bytes=10,
            extraction_status="pending",
        )
        answer = InterviewAnswer(
            session_id=session.id,
            candidate_id=candidate.id,
            question_id=question.id,
            audio_file_path=str(audio_path),
            transcribed_text="Archived answer",
            status=InterviewAnswerStatus.EVALUATED,
            overall_score=70.0,
        )
        db.add_all([document, answer])
        db.commit()
        return {
            "candidate_id": candidate.id,
            "hr_id": hr.id,
            "document_path": str(document_path),
            "audio_path": str(audio_path),
        }
    finally:
        db.close()


def test_interview_retention_purge_supports_dry_run_and_deletion(tmp_path: Path, monkeypatch):
    fixture = _seed_archived_candidate_fixture(tmp_path)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()

    hr = Employee(
        id=int(fixture["hr_id"]),
        name="Retention HR",
        email="retention_hr_test@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="RETENTION_HR_TEST",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: hr

    dry_run = client.post("/api/hr/interviews/retention/purge-archived", json={"older_than_days": 90, "dry_run": True})
    assert dry_run.status_code == 200
    dry_run_body = dry_run.json()
    assert dry_run_body["archived_candidates_matched"] == 1
    assert dry_run_body["candidates_deleted"] == 0
    assert dry_run_body["document_files_deleted"] == 1
    assert dry_run_body["answer_audio_files_deleted"] == 1
    assert Path(str(fixture["document_path"])).exists()
    assert Path(str(fixture["audio_path"])).exists()

    deletion = client.post("/api/hr/interviews/retention/purge-archived", json={"older_than_days": 90, "dry_run": False})
    assert deletion.status_code == 200
    deletion_body = deletion.json()
    assert deletion_body["archived_candidates_matched"] == 1
    assert deletion_body["candidates_deleted"] == 1
    assert deletion_body["document_files_deleted"] == 1
    assert deletion_body["answer_audio_files_deleted"] == 1
    assert not Path(str(fixture["document_path"])).exists()
    assert not Path(str(fixture["audio_path"])).exists()

    db: Session = SessionLocal()
    try:
        assert db.query(InterviewCandidate).filter(InterviewCandidate.id == int(fixture["candidate_id"])).first() is None
        audits = db.query(AuditEvent).filter(AuditEvent.action == "INTERVIEW_RETENTION_PURGE").all()
        assert len(audits) >= 2
        assert any("dry_run=True" in (audit.after_state or "") for audit in audits)
        assert any("dry_run=False" in (audit.after_state or "") for audit in audits)
    finally:
        db.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_interview_retention_purge_ignores_recent_archives(tmp_path: Path, monkeypatch):
    fixture = _seed_archived_candidate_fixture(tmp_path, archived_days_ago=7)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    from app.config import get_settings
    get_settings.cache_clear()

    hr = Employee(
        id=int(fixture["hr_id"]),
        name="Retention HR Recent",
        email="retention_hr_recent@example.com",
        role=UserRole.HR_MANAGER,
        employee_code="RETENTION_HR_RECENT",
        hashed_password="fake",
        status="active",
    )
    app.dependency_overrides[get_current_user] = lambda: hr

    response = client.post("/api/hr/interviews/retention/purge-archived", json={"older_than_days": 90, "dry_run": False})
    assert response.status_code == 200
    body = response.json()
    assert body["archived_candidates_matched"] == 0
    assert body["candidates_deleted"] == 0
    assert Path(str(fixture["document_path"])).exists()
    assert Path(str(fixture["audio_path"])).exists()

    db: Session = SessionLocal()
    try:
        assert db.query(InterviewCandidate).filter(InterviewCandidate.id == int(fixture["candidate_id"])).first() is not None
    finally:
        db.close()
        app.dependency_overrides.clear()
        get_settings.cache_clear()
