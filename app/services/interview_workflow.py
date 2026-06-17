from sqlalchemy.orm import Session

from app.models import (
    InterviewAnswerStatus,
    InterviewCandidate,
    InterviewCandidateStatus,
    InterviewSessionStatus,
    InterviewWorkflowEvent,
    InterviewMcqSubmission,
)


def create_interview_workflow_event(
    db: Session,
    *,
    candidate_id: int,
    event_type: str,
    actor_id: int | None = None,
    from_status: str | None = None,
    to_status: str | None = None,
    note: str | None = None,
    event_payload: dict | None = None,
) -> InterviewWorkflowEvent:
    event = InterviewWorkflowEvent(
        candidate_id=candidate_id,
        actor_id=actor_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        note=note,
        event_payload=event_payload,
    )
    db.add(event)
    db.flush()
    return event


def sync_candidate_interview_state(db: Session, candidate: InterviewCandidate) -> tuple[str | None, str]:
    evaluated_scores = [
        answer.overall_score
        for answer in candidate.answers
        if answer.status == InterviewAnswerStatus.EVALUATED and answer.overall_score is not None
    ]
    candidate.final_score = (
        sum(evaluated_scores) / len(evaluated_scores)
        if evaluated_scores
        else None
    )

    completed_sessions = [
        session for session in candidate.sessions if session.status == InterviewSessionStatus.COMPLETED
    ]
    if not completed_sessions:
        return candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status), candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)

    completed_session_ids = {session.id for session in completed_sessions}
    expected_answers = sum(max(session.question_count or 0, 0) for session in completed_sessions)
    submitted_answers = [
        answer for answer in candidate.answers if answer.session_id in completed_session_ids
    ]
    all_terminal = all(
        answer.status in {InterviewAnswerStatus.EVALUATED, InterviewAnswerStatus.FAILED}
        for answer in submitted_answers
    )

    # Check if MCQ is completed when enabled
    has_mcq_if_enabled = True
    if candidate.job and candidate.job.mcq_enabled:
        mcq_sub = db.query(InterviewMcqSubmission).filter(InterviewMcqSubmission.candidate_id == candidate.id).first()
        has_mcq_if_enabled = mcq_sub is not None

    ready_for_evaluation = expected_answers > 0 and len(submitted_answers) >= expected_answers and all_terminal and has_mcq_if_enabled

    before_status = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)
    if ready_for_evaluation and candidate.status == InterviewCandidateStatus.INTERVIEWING:
        candidate.status = InterviewCandidateStatus.EVALUATED
    after_status = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)
    db.flush()
    return before_status, after_status
