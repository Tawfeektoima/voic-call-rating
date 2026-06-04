from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app.database import SessionLocal
from app.main import app
from app.models import (
    AgentViolation,
    Call,
    CallOutcome,
    CallQAPair,
    CallStatus,
    Campaign,
    CandidateStatus,
    Employee,
    GoldenPairCandidate,
    UserRole,
)
from app.worker import process_call_audio_task


def _seed_worker_call():
    db = SessionLocal()
    try:
        employee = Employee(
            name="Worker Agent",
            email="worker_agent@example.com",
            role=UserRole.AGENT,
            employee_code="WORKER_AGENT",
            hashed_password="fake",
            status="active",
        )
        campaign = Campaign(
            name="WORKER_IDEMPOTENCY_CAMPAIGN",
            evaluation_prompt="Evaluate the call.",
            color="#000000",
        )
        db.add_all([employee, campaign])
        db.commit()
        db.refresh(employee)
        db.refresh(campaign)

        audio_path = Path("test_uploads") / "worker_idempotency.wav"
        audio_path.write_bytes(b"fake-audio-bytes")

        call = Call(
            id=100,
            employee_id=employee.id,
            campaign_id=campaign.id,
            audio_file_path=str(audio_path),
            original_filename="worker_idempotency.wav",
            status=CallStatus.PENDING,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call.id
    finally:
        db.close()


def test_process_call_audio_is_idempotent():
    call_id = _seed_worker_call()

    raw_segments = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "hello there", "needs_review": False}
    ]
    eval_result = SimpleNamespace(
        reasoning="Reasoning",
        summary="Summary",
        score=92.0,
        strengths=[],
        weaknesses=[],
            qa_pairs=[
                SimpleNamespace(
                    objection="Need help",
                    response="This is a sufficiently detailed golden response for the idempotency regression test case and it should clearly qualify for the review queue.",
                    customer_emotion_at="neutral",
                    customer_emotion_after="calm",
                    is_golden=True,
                )
        ],
        opening_ok=True,
        closing_ok=True,
        dob_verified=False,
        primary_outcome="qualified",
        outcome_value=25.0,
        follow_up_required=False,
        follow_up_date=None,
        campaign_specific_data={},
        raw_sales_data={},
            raw_violations=[
                {
                    "violation_id": "dead_air",
                    "severity": "low",
                    "timestamp": "00:05",
                    "evidence": "Silence detected",
                }
            ],
        )

    with patch("app.worker.check_redis_health", return_value=(True, "")), \
        patch("app.worker.psutil.disk_usage") as mock_disk_usage, \
        patch("app.worker.force_cuda_cleanup"), \
        patch("app.worker.transcriber.process_audio", return_value=(raw_segments, 4.0)) as mock_transcribe, \
        patch("app.worker.acoustic_analyzer.analyze_segments", return_value=[{"time": 0.0, "emotion": "calm", "intensity": 95.0, "speaker": "SPEAKER_00"}]) as mock_acoustic, \
        patch("app.worker.assign_speakers", return_value={"SPEAKER_00": "Agent"}) as mock_assign, \
        patch("app.worker.evaluate_transcript", return_value=eval_result) as mock_eval, \
        patch("app.services.aggregation.update_agent_mastery_stats") as mock_stats, \
        patch("app.worker.redis_client.publish") as mock_publish:
        mock_disk_usage.return_value.percent = 10.0
        process_call_audio_task(call_id)

        db = SessionLocal()
        try:
            assert db.query(CallOutcome).filter(CallOutcome.call_id == call_id).count() == 1
            assert db.query(AgentViolation).filter(AgentViolation.call_id == call_id).count() == 1
            assert db.query(CallQAPair).filter(CallQAPair.call_id == call_id).count() == 1
            assert db.query(GoldenPairCandidate).filter(GoldenPairCandidate.call_id == call_id).count() == 1

            call = db.query(Call).filter(Call.id == call_id).first()
            call.status = CallStatus.TRANSCRIBED
            db.commit()
        finally:
            db.close()

        process_call_audio_task(call_id)

    db = SessionLocal()
    try:
        assert db.query(CallOutcome).filter(CallOutcome.call_id == call_id).count() == 1
        assert db.query(AgentViolation).filter(AgentViolation.call_id == call_id).count() == 1
        assert db.query(CallQAPair).filter(CallQAPair.call_id == call_id).count() == 1
        assert db.query(GoldenPairCandidate).filter(GoldenPairCandidate.call_id == call_id).count() == 1

        call = db.query(Call).filter(Call.id == call_id).first()
        assert call.status == CallStatus.EVALUATED
    finally:
        db.close()

    assert mock_transcribe.call_count == 1
    assert mock_acoustic.call_count == 1
    assert mock_assign.call_count == 1
    assert mock_eval.call_count == 1
    assert mock_stats.call_count == 1
    assert mock_publish.call_count >= 1
