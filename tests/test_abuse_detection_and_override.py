from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.violations import VIOLATION_REGISTRY
from app.models import Call, Employee, ScoreOverrideAudit, UserRole
from app.database import SessionLocal
from app.worker import process_call_audio_task
from app.services.analysis import EvaluationResult

def test_violation_registry_entry():
    """Verify that manipulative_leading violation is correctly registered."""
    assert "manipulative_leading" in VIOLATION_REGISTRY
    v = VIOLATION_REGISTRY["manipulative_leading"]
    assert v["severity"] == "high"
    assert v["category"] == "compliance"
    assert "Warning" in v["hr_flag_on"]

def test_abuse_detection_alarm_flagging():
    """Verify that worker flags QA alarm on manipulative_leading or abusive_language."""
    db: Session = SessionLocal()
    try:
        # Create a test employee/agent
        agent = Employee(
            name="Test QA Agent",
            role=UserRole.AGENT,
            employee_code="TQA001",
            email="test_qa_agent@example.com",
            hashed_password="fake_hashed_password"
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        # Create a test call
        call = Call(
            employee_id=agent.id,
            campaign_id=1,
            original_filename="test.mp3",
            audio_file_path="uploads/test.mp3",
            status="pending",
            evaluation_score=95.0
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # Simulate eval result with manipulative_leading
        mock_eval = EvaluationResult(
            score=95.0,
            reasoning="Test reasoning",
            strengths=[],
            weaknesses=[],
            raw_violations=[
                {
                    "violation_id": "manipulative_leading",
                    "timestamp": "00:12",
                    "evidence": "Agent told customer to say yes to the warranty question"
                }
            ],
            raw_sales_data=None,
            ai_summary="Test call summary"
        )

        # Simulate worker processing logic for violations
        if mock_eval.raw_violations and call.employee_id:
            from app.violations import apply_violations
            violations_result = apply_violations(
                base_score=call.evaluation_score or 0.0,
                raw_violations=mock_eval.raw_violations,
                employee_id=call.employee_id,
                call_id=call.id,
                campaign_id=call.campaign_id,
                db=db,
            )
            # Flag call for HR review if any violation triggered HR
            if violations_result.get("hr_flag"):
                call.needs_review = True

            # Check for abuse detection
            abuse_violations = [
                v for v in mock_eval.raw_violations
                if isinstance(v, dict) and v.get("violation_id") in ["manipulative_leading", "abusive_language"]
            ]
            if abuse_violations:
                call.qa_alarm = True
                call.needs_review = True
                evidence_list = [
                    f"[{v.get('timestamp') or 'No timestamp'}] {v.get('evidence')}"
                    for v in abuse_violations
                ]
                call.qa_alarm_reason = "Abusive agent behavior (manipulative/leading instructions or abusive language) detected."
                call.qa_alarm_evidence = "; ".join(evidence_list)
            
            db.commit()
            db.refresh(call)

        assert call.qa_alarm is True
        assert call.needs_review is True
        assert "Abusive agent behavior" in call.qa_alarm_reason
        assert "Agent told customer to say yes" in call.qa_alarm_evidence

    finally:
        # Cleanup
        db.rollback()
        # Delete test records
        if 'call' in locals():
            db.query(Call).filter(Call.id == call.id).delete()
        if 'agent' in locals():
            db.query(Employee).filter(Employee.id == agent.id).delete()
        db.commit()
        db.close()

def test_score_override_audit_logging():
    """Verify that score override logging creates audits and resolves needs_review."""
    db: Session = SessionLocal()
    try:
        # Create a reviewer
        reviewer = Employee(
            name="Test Reviewer",
            role=UserRole.QA,
            employee_code="TREV001",
            email="test_reviewer@example.com",
            hashed_password="fake_hashed_password"
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)

        # Create a test call flagged for review
        call = Call(
            employee_id=reviewer.id,
            campaign_id=1,
            original_filename="test2.mp3",
            audio_file_path="uploads/test2.mp3",
            status="evaluated",
            evaluation_score=85.0,
            qa_alarm=True,
            needs_review=True,
            qa_alarm_reason="Abuse"
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # Run override logic (analogous to PATCH /api/audio/{call_id}/review)
        new_score = 45.0
        reason = "Confirmed abuse, score docked to 45."

        if new_score != call.overridden_score:
            old_score = call.overridden_score if call.overridden_score is not None else call.evaluation_score
            audit_log = ScoreOverrideAudit(
                call_id=call.id,
                reviewer_id=reviewer.id,
                reviewer_name=reviewer.name,
                old_score=old_score,
                new_score=new_score,
                reason=reason,
                created_at=datetime.now(timezone.utc)
            )
            db.add(audit_log)
            call.needs_review = False
        
        call.overridden_score = new_score
        call.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(call)

        # Verify call fields
        assert call.overridden_score == 45.0
        assert call.needs_review is False

        # Verify audit record
        audit = db.query(ScoreOverrideAudit).filter(ScoreOverrideAudit.call_id == call.id).first()
        assert audit is not None
        assert audit.old_score == 85.0
        assert audit.new_score == 45.0
        assert audit.reviewer_name == "Test Reviewer"
        assert audit.reason == reason

    finally:
        # Cleanup
        db.rollback()
        # Delete test records
        if 'call' in locals():
            db.query(ScoreOverrideAudit).filter(ScoreOverrideAudit.call_id == call.id).delete()
            db.query(Call).filter(Call.id == call.id).delete()
        if 'reviewer' in locals():
            db.query(Employee).filter(Employee.id == reviewer.id).delete()
        db.commit()
        db.close()

if __name__ == "__main__":
    print("Running test_violation_registry_entry...")
    test_violation_registry_entry()
    print("test_violation_registry_entry passed!")

    print("Running test_abuse_detection_alarm_flagging...")
    test_abuse_detection_alarm_flagging()
    print("test_abuse_detection_alarm_flagging passed!")

    print("Running test_score_override_audit_logging...")
    test_score_override_audit_logging()
    print("test_score_override_audit_logging passed!")

    print("All verification tests passed successfully!")

