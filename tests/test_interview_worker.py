from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

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
from app.schemas import EvaluationResult
from app.worker import process_interview_answer_task


def _seed_interview_answer_fixture(*, completed_session: bool, audio_file_path: str | None = None, transcript_text: str | None = None) -> int:
    db: Session = SessionLocal()
    try:
        hr = Employee(
            name="Interview Worker HR",
            email=f"interview_worker_hr_{datetime.now().timestamp()}@example.com",
            role=UserRole.HR_MANAGER,
            employee_code=f"INT_WRK_HR_{int(datetime.now().timestamp() * 1000)}",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name=f"Interview Worker Campaign {datetime.now().timestamp()}",
            evaluation_prompt="Prompt long enough for worker interview tests.",
            color="#445566",
        )
        db.add_all([hr, campaign])
        db.commit()
        db.refresh(hr)
        db.refresh(campaign)

        team = Team(
            name=f"Interview Worker Team {datetime.now().timestamp()}",
            campaign_id=campaign.id,
            manager_id=hr.id,
            leader_id=hr.id,
            is_active=True,
        )
        db.add(team)
        db.commit()
        db.refresh(team)

        job = InterviewJob(
            title="Retention Specialist",
            description="Interview worker evaluation path.",
            department="HR",
            team_id=team.id,
            campaign_id=campaign.id,
            status=InterviewJobStatus.OPEN,
            base_questions=["Tell me about a difficult customer interaction."],
            created_by_id=hr.id,
            updated_by_id=hr.id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        candidate = InterviewCandidate(
            job_id=job.id,
            full_name="Interview Worker Candidate",
            contact_email=f"interview_worker_candidate_{datetime.now().timestamp()}@example.com",
            contact_email_normalized=f"interview_worker_candidate_{datetime.now().timestamp()}@example.com",
            status=InterviewCandidateStatus.INTERVIEWING,
            created_by_id=hr.id,
        )
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

        session = InterviewSession(
            candidate_id=candidate.id,
            job_id=job.id,
            session_token_hash=f"worker-token-{candidate.id}",
            status=InterviewSessionStatus.COMPLETED if completed_session else InterviewSessionStatus.IN_PROGRESS,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
            question_count=1,
            completed_at=datetime.now(timezone.utc) if completed_session else None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        question = InterviewQuestion(
            job_id=job.id,
            session_id=session.id,
            candidate_id=candidate.id,
            question_text="Tell me about a difficult customer interaction.",
            expected_skills_tags=["communication", "problem solving"],
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
            audio_file_path=audio_file_path,
            transcribed_text=transcript_text,
            status=InterviewAnswerStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
        )
        db.add(answer)
        db.commit()
        return answer.id
    finally:
        db.close()


def test_process_interview_answer_task_evaluates_transcript_answer_and_finalizes_candidate():
    answer_id = _seed_interview_answer_fixture(
        completed_session=True,
        transcript_text="I de-escalated the issue, clarified the problem, and kept the customer engaged until resolution.",
    )
    eval_result = EvaluationResult(
        reasoning="Candidate stayed relevant, clear, and practical.",
        score=86.0,
        strengths=[{"issue": "Relevant answer", "detail": "Strong alignment to the scenario"}],
        weaknesses=[{"issue": "Could quantify impact", "detail": "Needed stronger metrics", "deduction": 4.0}],
        summary="Strong answer with clear communication and practical ownership.",
    )

    with patch("app.worker.check_redis_health", return_value=(True, "")), \
        patch("app.worker.evaluate_transcript", return_value=eval_result), \
        patch("app.worker.release_worker_model_resources"), \
        patch("app.worker.print_worker_vram"):
        process_interview_answer_task(answer_id)

    db: Session = SessionLocal()
    try:
        answer = db.query(InterviewAnswer).filter(InterviewAnswer.id == answer_id).first()
        candidate = answer.candidate if answer is not None else None
        assert answer is not None
        assert answer.status == InterviewAnswerStatus.EVALUATED
        assert answer.overall_score == 86.0
        assert "Strong answer" in (answer.ai_summary or "")
        assert candidate is not None
        assert candidate.status == InterviewCandidateStatus.EVALUATED
        assert candidate.final_score == 86.0
        assert db.query(InterviewWorkflowEvent).filter(
            InterviewWorkflowEvent.candidate_id == candidate.id,
            InterviewWorkflowEvent.event_type == "CANDIDATE_EVALUATED",
        ).count() == 1
    finally:
        db.close()


def test_process_interview_answer_task_transcribes_audio_before_evaluation(tmp_path: Path):
    audio_path = tmp_path / "interview-answer.wav"
    audio_path.write_bytes(b"fake-audio")
    answer_id = _seed_interview_answer_fixture(
        completed_session=False,
        audio_file_path=str(audio_path),
        transcript_text=None,
    )
    eval_result = EvaluationResult(
        reasoning="Candidate provided a usable answer.",
        score=74.0,
        strengths=[{"issue": "Clear structure", "detail": "Easy to follow"}],
        weaknesses=[],
        summary="Usable answer with decent clarity.",
    )
    raw_segments = [
        {"speaker": "SPEAKER_00", "start": 0.0, "text": "I listened carefully and resolved the issue step by step."},
    ]

    with patch("app.worker.check_redis_health", return_value=(True, "")), \
        patch("app.worker.transcriber.process_audio", return_value=(raw_segments, 6.0)), \
        patch("app.worker.evaluate_transcript", return_value=eval_result), \
        patch("app.worker.release_worker_model_resources"), \
        patch("app.worker.print_worker_vram"):
        process_interview_answer_task(answer_id)

    db: Session = SessionLocal()
    try:
        answer = db.query(InterviewAnswer).filter(InterviewAnswer.id == answer_id).first()
        candidate = answer.candidate if answer is not None else None
        assert answer is not None
        assert answer.status == InterviewAnswerStatus.EVALUATED
        assert "resolved the issue step by step" in (answer.transcribed_text or "")
        assert candidate is not None
        assert candidate.status == InterviewCandidateStatus.INTERVIEWING
        assert candidate.final_score == 74.0
    finally:
        db.close()


def test_process_interview_answer_task_continues_when_redis_health_is_unavailable():
    answer_id = _seed_interview_answer_fixture(
        completed_session=True,
        transcript_text="I handled the escalation calmly and closed the loop with the customer.",
    )
    eval_result = EvaluationResult(
        reasoning="Candidate stayed composed and relevant.",
        score=81.0,
        strengths=[{"issue": "Relevant answer", "detail": "Good ownership"}],
        weaknesses=[],
        summary="Good answer despite infrastructure warning.",
    )

    with patch("app.worker.check_redis_health", return_value=(False, "Redis unavailable")), \
        patch("app.worker.evaluate_transcript", return_value=eval_result), \
        patch("app.worker.release_worker_model_resources"), \
        patch("app.worker.print_worker_vram"):
        process_interview_answer_task(answer_id)

    db: Session = SessionLocal()
    try:
        answer = db.query(InterviewAnswer).filter(InterviewAnswer.id == answer_id).first()
        assert answer is not None
        assert answer.status == InterviewAnswerStatus.EVALUATED
        assert answer.overall_score == 81.0
    finally:
        db.close()
