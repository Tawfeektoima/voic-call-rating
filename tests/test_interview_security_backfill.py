from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Campaign,
    Employee,
    InterviewCandidate,
    InterviewCandidateDocument,
    InterviewCandidateStatus,
    InterviewJob,
    InterviewJobStatus,
    Team,
    UserRole,
)
from app.services.interview_file_crypto import decrypt_file_bytes, decrypt_text_value
from app.services.interview_security_backfill import backfill_interview_document_security


def test_interview_security_backfill_encrypts_legacy_files_and_text(tmp_path: Path):
    legacy_path = tmp_path / "legacy-resume.txt"
    legacy_path.write_text("legacy cv content", encoding="utf-8")

    db: Session = SessionLocal()
    try:
        hr = Employee(
            name="Backfill HR",
            email=f"backfill_hr_{datetime.now().timestamp()}@example.com",
            role=UserRole.HR_MANAGER,
            employee_code=f"BACKFILL_HR_{int(datetime.now().timestamp() * 1000)}",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name=f"Backfill Campaign {datetime.now().timestamp()}",
            evaluation_prompt="Prompt for backfill test.",
            color="#112233",
        )
        db.add_all([hr, campaign])
        db.commit()
        db.refresh(hr)
        db.refresh(campaign)

        team = Team(
            name=f"Backfill Team {datetime.now().timestamp()}",
            campaign_id=campaign.id,
            manager_id=hr.id,
            leader_id=hr.id,
            is_active=True,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        job = InterviewJob(
            title="Backfill Role",
            description="Backfill flow",
            department="HR",
            team_id=team.id,
            campaign_id=campaign.id,
            status=InterviewJobStatus.OPEN,
            base_questions=["Question"],
            created_by_id=hr.id,
            updated_by_id=hr.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        candidate = InterviewCandidate(
            job_id=job.id,
            full_name="Legacy Candidate",
            contact_email=f"legacy_candidate_{datetime.now().timestamp()}@example.com",
            contact_email_normalized=f"legacy_candidate_{datetime.now().timestamp()}@example.com",
            status=InterviewCandidateStatus.APPLIED,
            created_by_id=hr.id,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        document = InterviewCandidateDocument(
            candidate_id=candidate.id,
            document_type="cv",
            original_filename="legacy-resume.txt",
            storage_path=str(legacy_path),
            content_type="text/plain",
            file_size_bytes=legacy_path.stat().st_size,
            extraction_status="complete",
            extracted_text="legacy cv content",
            is_encrypted=False,
        )
        db.add(document)
        db.commit()

        summary = backfill_interview_document_security(db)
        db.commit()
        db.refresh(document)

        assert summary.encrypted_files == 1
        assert summary.encrypted_text_rows == 1
        assert document.is_encrypted is True
        assert document.extracted_text != "legacy cv content"
        assert decrypt_text_value(document.extracted_text) == "legacy cv content"
        assert decrypt_file_bytes(str(legacy_path)) == b"legacy cv content"
    finally:
        db.close()
