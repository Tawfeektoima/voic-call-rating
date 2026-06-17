import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    InterviewAnswer,
    InterviewAnswerStatus,
    InterviewCandidate,
    InterviewCandidateStatus,
    InterviewCandidateDocument,
    InterviewJob,
    InterviewJobStatus,
    InterviewMcqSubmission,
    InterviewQuestion,
    InterviewSession,
    InterviewSessionStatus,
)
from app.schemas import (
    InterviewAnswerSubmitOut,
    InterviewMcqPortalOut,
    InterviewMcqSubmissionOut,
    InterviewMcqSubmitRequest,
    InterviewPortalAnswerHistoryOut,
    InterviewPortalDashboardOut,
    InterviewPortalJobOut,
    InterviewPortalMcqResultOut,
    InterviewPortalRegistrationOut,
    InterviewPortalSessionOut,
    InterviewQuestionStartOut,
    InterviewQuestionOut,
)
from app.services.employee_identity import hash_national_id
from app.services.interview_documents import extract_text_from_document
from app.services.interview_eligibility import (
    parse_candidate_date_of_birth,
    resolve_public_candidate_eligibility,
    validate_candidate_age,
)
from app.services.interview_file_crypto import encrypt_file_in_place, encrypt_text_value
from app.services.interview_identity import (
    generate_interview_session_token,
    hash_interview_session_token,
    national_id_last4,
    normalize_interview_email,
    normalize_interview_phone,
)
from app.services.interview_mcq import get_job_mcq_bank, get_safe_mcq_bank, grade_mcq_answers
from app.services.interview_question_builder import build_hybrid_interview_questions
from app.services.interview_workflow import create_interview_workflow_event, sync_candidate_interview_state
from app.services.public_links import build_interview_invite_url
from app.worker import process_interview_answer_task

router = APIRouter(prefix="/api/interview-portal", tags=["Interview Portal"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _get_current_interview_session(
    x_interview_session_token: str = Header(..., alias="X-Interview-Session-Token"),
    db: Session = Depends(get_db),
) -> InterviewSession:
    token_hash = hash_interview_session_token(x_interview_session_token)
    session = db.query(InterviewSession).filter(InterviewSession.session_token_hash == token_hash).first()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid interview session token.")
    if _as_aware_utc(session.expires_at) < _utcnow():
        session.status = InterviewSessionStatus.EXPIRED
        if session.candidate.status == InterviewCandidateStatus.INTERVIEWING:
            session.candidate.status = InterviewCandidateStatus.EVALUATED
        db.commit()
        raise HTTPException(status_code=401, detail="Interview session has expired.")
    if session.status == InterviewSessionStatus.CANCELLED:
        raise HTTPException(status_code=403, detail="Interview session is cancelled.")
    return session


def _validate_public_cv_file(file: UploadFile | None) -> None:
    if file is None or not file.filename:
        return
    settings = get_settings()
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in settings.interview_document_allowed_extensions_list:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CV type. Allowed: {settings.INTERVIEW_DOCUMENT_ALLOWED_EXTENSIONS}",
        )


async def _store_public_cv_document(
    db: Session,
    *,
    candidate: InterviewCandidate,
    file: UploadFile | None,
) -> tuple[InterviewCandidateDocument | None, str]:
    if file is None or not file.filename:
        return None, ""

    _validate_public_cv_file(file)
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.interview_document_max_file_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"CV exceeds max size of {settings.INTERVIEW_DOCUMENT_MAX_FILE_SIZE_MB}MB",
        )

    documents_dir = os.path.join(settings.UPLOAD_DIR, "interview_documents")
    os.makedirs(documents_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "cv_upload").replace("\x00", "") or f"cv_{uuid4().hex}.txt"
    storage_name = f"{candidate.id}_{int(_utcnow().timestamp())}_{uuid4().hex}_{safe_name}"
    storage_path = os.path.join(documents_dir, storage_name)
    with open(storage_path, "wb") as output_file:
        output_file.write(content)

    document = InterviewCandidateDocument(
        candidate_id=candidate.id,
        document_type="cv",
        original_filename=safe_name,
        storage_path=storage_path,
        content_type=file.content_type,
        file_size_bytes=len(content),
        extraction_status="pending",
    )
    db.add(document)
    db.flush()

    extracted_text = ""
    try:
        extracted_text = extract_text_from_document(storage_path, file.content_type, safe_name)
        document.extracted_text = encrypt_text_value(extracted_text)
        document.extraction_status = "complete" if extracted_text else "empty"
        document.extraction_error = None
    except ValueError as exc:
        document.extraction_status = "failed"
        document.extraction_error = str(exc)

    try:
        encrypt_file_in_place(storage_path)
        document.is_encrypted = True
    except Exception as exc:
        try:
            if os.path.isfile(storage_path):
                os.remove(storage_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Failed to secure uploaded CV: {exc}") from exc

    return document, extracted_text


def _create_registered_interview_session(
    db: Session,
    *,
    candidate: InterviewCandidate,
    job: InterviewJob,
    cv_text: str,
) -> tuple[InterviewSession, str]:
    for existing_session in candidate.sessions:
        if existing_session.status not in {
            InterviewSessionStatus.COMPLETED,
            InterviewSessionStatus.CANCELLED,
            InterviewSessionStatus.EXPIRED,
        }:
            existing_session.status = InterviewSessionStatus.CANCELLED

    settings = get_settings()
    session_token = generate_interview_session_token()
    session = InterviewSession(
        candidate_id=candidate.id,
        job_id=job.id,
        session_token_hash=hash_interview_session_token(session_token),
        status=InterviewSessionStatus.INVITED,
        expires_at=_utcnow() + timedelta(hours=settings.INTERVIEW_SESSION_EXPIRY_HOURS),
    )
    db.add(session)
    db.flush()

    combined_questions = build_hybrid_interview_questions(job.base_questions or [], cv_text)
    if not combined_questions:
        raise HTTPException(status_code=400, detail="Interview job must have at least one question before registration.")

    for index, (question_text, source) in enumerate(combined_questions, start=1):
        db.add(
            InterviewQuestion(
                job_id=job.id,
                session_id=session.id,
                candidate_id=candidate.id,
                question_text=question_text,
                source=source,
                display_order=index,
            )
        )
    session.question_count = len(combined_questions)
    return session, session_token


@router.get("/jobs", response_model=list[InterviewPortalJobOut])
def list_public_interview_jobs(db: Session = Depends(get_db)):
    jobs = (
        db.query(InterviewJob)
        .filter(InterviewJob.status == InterviewJobStatus.OPEN)
        .order_by(InterviewJob.created_at.desc(), InterviewJob.id.desc())
        .all()
    )
    return [
        InterviewPortalJobOut(
            id=job.id,
            title=job.title,
            description=job.description,
            department=job.department,
            mcq_enabled=job.mcq_enabled,
        )
        for job in jobs
    ]


@router.post("/register", response_model=InterviewPortalRegistrationOut)
async def register_public_interview_candidate(
    job_id: int = Form(...),
    full_name: str = Form(...),
    contact_email: str = Form(...),
    phone_number: str | None = Form(default=None),
    national_id: str | None = Form(default=None),
    date_of_birth: str | None = Form(default=None),
    address: str | None = Form(default=None),
    manual_experience: str | None = Form(default=None),
    cv_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    job = db.query(InterviewJob).filter(InterviewJob.id == job_id).first()
    if job is None or job.status != InterviewJobStatus.OPEN:
        raise HTTPException(status_code=404, detail="Open interview job not found.")

    normalized_email = normalize_interview_email(contact_email)
    normalized_phone = normalize_interview_phone(phone_number)
    national_id_hash = hash_national_id(national_id)
    parsed_dob = parse_candidate_date_of_birth(date_of_birth)
    validate_candidate_age(parsed_dob)

    eligibility = resolve_public_candidate_eligibility(
        db,
        job_id=job.id,
        normalized_email=normalized_email,
        normalized_phone=normalized_phone,
        national_id_hash=national_id_hash,
    )

    if eligibility.candidate is not None and eligibility.should_reuse_candidate:
        candidate = eligibility.candidate
        previous_status = candidate.status.value
        candidate.job_id = job.id
        candidate.full_name = full_name.strip()
        candidate.contact_email = normalized_email
        candidate.contact_email_normalized = normalized_email
        candidate.phone_number = phone_number
        candidate.phone_normalized = normalized_phone
        candidate.national_id_hash = national_id_hash
        candidate.national_id_last4 = national_id_last4(national_id)
        candidate.date_of_birth_encrypted = encrypt_text_value(parsed_dob.isoformat()) if parsed_dob else None
        candidate.address_encrypted = encrypt_text_value(address.strip()) if address and address.strip() else None
        candidate.registration_source = "public"
        candidate.status = InterviewCandidateStatus.APPLIED
        candidate.final_score = None
        candidate.global_percentile = None
        candidate.completed_at = None
        candidate.archived_at = None
        candidate.applied_at = _utcnow()
    else:
        existing_job_email = (
            db.query(InterviewCandidate)
            .filter(
                InterviewCandidate.job_id == job.id,
                func.lower(InterviewCandidate.contact_email_normalized) == normalized_email,
            )
            .first()
        )
        if existing_job_email is not None:
            raise HTTPException(status_code=400, detail="Candidate email already exists for this interview job.")
        previous_status = None
        candidate = InterviewCandidate(
            job_id=job.id,
            full_name=full_name.strip(),
            contact_email=normalized_email,
            contact_email_normalized=normalized_email,
            phone_number=phone_number,
            phone_normalized=normalized_phone,
            national_id_hash=national_id_hash,
            national_id_last4=national_id_last4(national_id),
            date_of_birth_encrypted=encrypt_text_value(parsed_dob.isoformat()) if parsed_dob else None,
            address_encrypted=encrypt_text_value(address.strip()) if address and address.strip() else None,
            registration_source="public",
            status=InterviewCandidateStatus.APPLIED,
            created_by_id=None,
        )
        db.add(candidate)
        db.flush()

    document, extracted_cv_text = await _store_public_cv_document(db, candidate=candidate, file=cv_file)
    cv_text = extracted_cv_text or (manual_experience or "").strip()
    session, session_token = _create_registered_interview_session(db, candidate=candidate, job=job, cv_text=cv_text)

    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        event_type="PUBLIC_CANDIDATE_REGISTERED",
        from_status=previous_status,
        to_status=candidate.status.value,
        note="Candidate registered from the public interview portal",
        event_payload={
            "job_id": job.id,
            "session_id": session.id,
            "duplicate_recent": eligibility.duplicate_recent,
            "document_id": document.id if document else None,
            "document_extraction_status": document.extraction_status if document else None,
        },
    )
    try:
        invite_url = build_interview_invite_url(session_token, settings=get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    db.commit()
    db.refresh(candidate)
    db.refresh(session)

    return InterviewPortalRegistrationOut(
        candidate_id=candidate.id,
        candidate_name=candidate.full_name,
        job_id=job.id,
        job_title=job.title,
        session_id=session.id,
        session_token=session_token,
        invite_url=invite_url,
        expires_at=session.expires_at,
        question_count=session.question_count,
        duplicate_recent=eligibility.duplicate_recent,
        document_id=document.id if document else None,
        document_extraction_status=document.extraction_status if document else None,
    )


@router.get("/session", response_model=InterviewPortalSessionOut)
def read_interview_session(session: InterviewSession = Depends(_get_current_interview_session)):
    mcq_bank = get_job_mcq_bank(session.job) if session.job.mcq_enabled else []
    return InterviewPortalSessionOut(
        candidate_id=session.candidate_id,
        candidate_name=session.candidate.full_name,
        job_id=session.job_id,
        job_title=session.job.title,
        session_id=session.id,
        status=session.status.value,
        expires_at=session.expires_at,
        question_count=session.question_count,
        mcq_enabled=session.job.mcq_enabled,
        mcq_completed=session.mcq_submission is not None,
        mcq_question_count=len(mcq_bank),
        question_time_limit_seconds=get_settings().INTERVIEW_QUESTION_TIME_LIMIT_SECONDS,
    )


@router.get("/dashboard", response_model=InterviewPortalDashboardOut)
def read_candidate_dashboard(
    db: Session = Depends(get_db),
    session: InterviewSession = Depends(_get_current_interview_session),
):
    answers = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id == session.id,
            InterviewAnswer.submitted_at.isnot(None),
        )
        .order_by(InterviewAnswer.submitted_at.asc().nullslast(), InterviewAnswer.id.asc())
        .all()
    )
    scored_answers = [answer.overall_score for answer in answers if answer.overall_score is not None]
    average_score = round(sum(scored_answers) / len(scored_answers), 1) if scored_answers else None

    breakdown = session.mcq_submission.breakdown or {} if session.mcq_submission is not None else {}
    objective_breakdown = breakdown.get("objective") or {}
    personality_breakdown = breakdown.get("traits") or {}

    return InterviewPortalDashboardOut(
        candidate_id=session.candidate_id,
        candidate_name=session.candidate.full_name,
        job_id=session.job_id,
        job_title=session.job.title,
        session_id=session.id,
        session_status=session.status.value,
        completed_at=session.completed_at,
        question_count=session.question_count,
        submitted_answers=len(answers),
        evaluated_answers=len(scored_answers),
        average_score=average_score,
        answers=[
            InterviewPortalAnswerHistoryOut(
                answer_id=answer.id,
                question_id=answer.question_id,
                question_text=answer.question.question_text if answer.question is not None else f"Question #{answer.question_id}",
                status=answer.status.value,
                overall_score=answer.overall_score,
                ai_summary=answer.ai_summary,
                submitted_at=answer.submitted_at,
                evaluated_at=answer.evaluated_at,
            )
            for answer in answers
        ],
        mcq_result=InterviewPortalMcqResultOut(
            completed=session.mcq_submission is not None,
            score=session.mcq_submission.score if session.mcq_submission is not None else None,
            total_questions=session.mcq_submission.total_questions if session.mcq_submission is not None else None,
            percentage=session.mcq_submission.percentage if session.mcq_submission is not None else None,
            completed_at=session.mcq_submission.completed_at if session.mcq_submission is not None else None,
            objective_breakdown={key: float(value) for key, value in objective_breakdown.items()},
            personality_breakdown={key: int(value) for key, value in personality_breakdown.items()},
        ),
    )


@router.get("/questions", response_model=list[InterviewQuestionOut])
def list_interview_questions(session: InterviewSession = Depends(_get_current_interview_session)):
    return sorted(session.questions, key=lambda item: (item.display_order, item.id))


@router.post("/questions/{question_id}/start", response_model=InterviewQuestionStartOut)
def start_interview_question(
    question_id: int,
    db: Session = Depends(get_db),
    session: InterviewSession = Depends(_get_current_interview_session),
):
    question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.session_id == session.id,
        )
        .first()
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Interview question not found for this session.")

    existing = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id == session.id,
            InterviewAnswer.question_id == question_id,
        )
        .first()
    )
    if existing is not None:
        if existing.submitted_at is not None:
            raise HTTPException(status_code=400, detail="This interview question already has a submitted answer.")
        return InterviewQuestionStartOut(
            answer_id=existing.id,
            session_id=session.id,
            question_id=question.id,
            status=existing.status.value,
            started_at=existing.started_at or _utcnow(),
            time_limit_seconds=get_settings().INTERVIEW_QUESTION_TIME_LIMIT_SECONDS,
        )

    if session.status == InterviewSessionStatus.INVITED:
        session.status = InterviewSessionStatus.IN_PROGRESS
        session.started_at = session.started_at or _utcnow()

    answer = InterviewAnswer(
        session_id=session.id,
        candidate_id=session.candidate_id,
        question_id=question.id,
        status=InterviewAnswerStatus.PENDING,
        started_at=_utcnow(),
        ai_summary="Question timer started.",
    )
    db.add(answer)
    create_interview_workflow_event(
        db,
        candidate_id=session.candidate_id,
        event_type="QUESTION_TIMER_STARTED",
        note=f"Question {question.id} timer started",
        event_payload={
            "question_id": question.id,
            "time_limit_seconds": get_settings().INTERVIEW_QUESTION_TIME_LIMIT_SECONDS,
        },
    )
    db.commit()
    db.refresh(answer)
    return InterviewQuestionStartOut(
        answer_id=answer.id,
        session_id=session.id,
        question_id=question.id,
        status=answer.status.value,
        started_at=answer.started_at,
        time_limit_seconds=get_settings().INTERVIEW_QUESTION_TIME_LIMIT_SECONDS,
    )


@router.get("/mcq", response_model=InterviewMcqPortalOut)
def get_interview_mcq_questions(session: InterviewSession = Depends(_get_current_interview_session)):
    if not session.job.mcq_enabled:
        return InterviewMcqPortalOut(mcq_enabled=False, mcq_completed=False, question_count=0, questions=[])

    mcq_bank = get_job_mcq_bank(session.job)
    return InterviewMcqPortalOut(
        mcq_enabled=True,
        mcq_completed=session.mcq_submission is not None,
        question_count=len(mcq_bank),
        questions=get_safe_mcq_bank(mcq_bank),
    )


@router.post("/mcq", response_model=InterviewMcqSubmissionOut)
def submit_interview_mcq(
    payload: InterviewMcqSubmitRequest,
    db: Session = Depends(get_db),
    session: InterviewSession = Depends(_get_current_interview_session),
):
    if not session.job.mcq_enabled:
        raise HTTPException(status_code=400, detail="Written assessment is not enabled for this interview job.")
    if session.mcq_submission is not None:
        raise HTTPException(status_code=400, detail="Written assessment has already been submitted for this session.")

    mcq_bank = get_job_mcq_bank(session.job)
    if not mcq_bank:
        raise HTTPException(status_code=400, detail="Written assessment is enabled but no MCQ questions are configured.")

    try:
        grading = grade_mcq_answers(mcq_bank, payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session.status == InterviewSessionStatus.INVITED:
        session.status = InterviewSessionStatus.IN_PROGRESS
        session.started_at = session.started_at or _utcnow()

    submission = InterviewMcqSubmission(
        session_id=session.id,
        candidate_id=session.candidate_id,
        job_id=session.job_id,
        answers=grading["answers"],
        question_bank_snapshot=grading["question_bank_snapshot"],
        breakdown=grading["breakdown"],
        score=grading["score"],
        total_questions=grading["total_questions"],
        percentage=grading["percentage"],
        completed_at=_utcnow(),
    )
    db.add(submission)
    create_interview_workflow_event(
        db,
        candidate_id=session.candidate_id,
        event_type="INTERVIEW_MCQ_SUBMITTED",
        note="Candidate completed the written assessment step",
        event_payload={
            "session_id": session.id,
            "score": submission.score,
            "total_questions": submission.total_questions,
            "percentage": submission.percentage,
        },
    )
    
    before_status, after_status = sync_candidate_interview_state(db, session.candidate)
    if before_status != after_status and after_status == InterviewCandidateStatus.EVALUATED.value:
        create_interview_workflow_event(
            db,
            candidate_id=session.candidate_id,
            event_type="CANDIDATE_EVALUATED",
            from_status=before_status,
            to_status=after_status,
            note="Candidate transitioned to evaluated after MCQ submission",
            event_payload={"final_score": session.candidate.final_score},
        )
    
    db.commit()
    db.refresh(submission)
    return submission


@router.post("/questions/{question_id}/answer", response_model=InterviewAnswerSubmitOut)
async def submit_interview_answer(
    question_id: int,
    transcript_text: str | None = Form(default=None),
    audio_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    session: InterviewSession = Depends(_get_current_interview_session),
):
    question = (
        db.query(InterviewQuestion)
        .filter(
            InterviewQuestion.id == question_id,
            InterviewQuestion.session_id == session.id,
        )
        .first()
    )
    if question is None:
        raise HTTPException(status_code=404, detail="Interview question not found for this session.")

    existing = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id == session.id,
            InterviewAnswer.question_id == question_id,
        )
        .first()
    )
    if existing is not None and existing.submitted_at is not None:
        raise HTTPException(status_code=400, detail="This interview question already has a submitted answer.")

    file_path = None
    if audio_file is not None:
        settings = get_settings()
        uploads_dir = os.path.join(settings.UPLOAD_DIR, "interview_answers")
        os.makedirs(uploads_dir, exist_ok=True)
        filename = f"{session.candidate_id}_{question_id}_{uuid4().hex}_{audio_file.filename or 'answer.webm'}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as output_file:
            output_file.write(await audio_file.read())

    if transcript_text is not None:
        transcript_text = transcript_text.strip() or None
    if not transcript_text and not file_path:
        raise HTTPException(status_code=400, detail="Answer submission must include transcript text or an audio file.")

    if session.status == InterviewSessionStatus.INVITED:
        session.status = InterviewSessionStatus.IN_PROGRESS
        session.started_at = session.started_at or _utcnow()

    now = _utcnow()
    answer = existing or InterviewAnswer(
        session_id=session.id,
        candidate_id=session.candidate_id,
        question_id=question.id,
        status=InterviewAnswerStatus.PENDING,
        started_at=now,
    )
    if existing is None:
        db.add(answer)

    started_at = answer.started_at or now
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    elapsed_seconds = (now - started_at).total_seconds()
    time_limit_seconds = get_settings().INTERVIEW_QUESTION_TIME_LIMIT_SECONDS

    answer.audio_file_path = file_path
    answer.transcribed_text = transcript_text
    answer.submitted_at = now
    answer.started_at = answer.started_at or started_at
    answer.evaluated_at = None
    answer.overall_score = None
    answer.status = InterviewAnswerStatus.PENDING
    answer.ai_summary = "Interview answer queued for AI evaluation."
    db.flush()

    create_interview_workflow_event(
        db,
        candidate_id=session.candidate_id,
        event_type="ANSWER_SUBMITTED",
        note=f"Question {question.id} answered",
        event_payload={"question_id": question.id, "has_audio": bool(file_path), "status": answer.status.value},
    )

    if elapsed_seconds > time_limit_seconds:
        answer.status = InterviewAnswerStatus.EVALUATED
        answer.relevance_score = 0.0
        answer.fluency_score = 0.0
        answer.grammar_score = 0.0
        answer.overall_score = 0.0
        answer.ai_summary = "Time limit exceeded. Response rejected by server."
        answer.evaluated_at = now
        create_interview_workflow_event(
            db,
            candidate_id=session.candidate_id,
            event_type="ANSWER_TIMEOUT",
            note=f"Question {question.id} exceeded the time limit",
            event_payload={
                "question_id": question.id,
                "answer_id": answer.id,
                "elapsed_seconds": elapsed_seconds,
                "time_limit_seconds": time_limit_seconds,
            },
        )
        db.commit()
        db.refresh(answer)
        return InterviewAnswerSubmitOut(
            answer_id=answer.id,
            session_id=session.id,
            question_id=question.id,
            status="timeout",
            transcribed_text=answer.transcribed_text,
        )

    db.commit()
    db.refresh(answer)
    try:
        process_interview_answer_task.delay(answer.id)
    except Exception as exc:
        answer.status = InterviewAnswerStatus.FAILED
        answer.error_message = f"Failed to queue interview evaluation task: {exc}"
        create_interview_workflow_event(
            db,
            candidate_id=session.candidate_id,
            event_type="ANSWER_EVALUATION_QUEUE_FAILED",
            note="Interview answer could not be queued for evaluation",
            event_payload={"question_id": question.id, "answer_id": answer.id},
        )
        db.commit()
        db.refresh(answer)
    return InterviewAnswerSubmitOut(
        answer_id=answer.id,
        session_id=session.id,
        question_id=question.id,
        status=answer.status.value,
        transcribed_text=answer.transcribed_text,
    )


@router.post("/complete")
def complete_interview_session(
    db: Session = Depends(get_db),
    session: InterviewSession = Depends(_get_current_interview_session),
):
    candidate: InterviewCandidate = session.candidate
    submitted_answer_count = (
        db.query(InterviewAnswer)
        .filter(
            InterviewAnswer.session_id == session.id,
            InterviewAnswer.submitted_at.isnot(None),
        )
        .count()
    )
    if submitted_answer_count < session.question_count:
        raise HTTPException(status_code=400, detail="Submit all interview answers before finishing the interview session.")
    if session.job.mcq_enabled and session.mcq_submission is None:
        raise HTTPException(status_code=400, detail="Complete the written assessment before finishing the interview session.")
    if session.status == InterviewSessionStatus.COMPLETED:
        return {"status": "already_completed", "session_id": session.id}

    session.status = InterviewSessionStatus.COMPLETED
    session.completed_at = _utcnow()
    candidate.completed_at = session.completed_at
    previous_status = candidate.status.value if hasattr(candidate.status, "value") else str(candidate.status)
    current_status = previous_status
    create_interview_workflow_event(
        db,
        candidate_id=candidate.id,
        event_type="INTERVIEW_COMPLETED",
        from_status=previous_status,
        to_status=current_status,
        note="Candidate completed interview session",
        event_payload={"session_id": session.id, "awaiting_evaluation": current_status != InterviewCandidateStatus.EVALUATED.value},
    )
    db.commit()
    return {"status": "completed", "session_id": session.id, "candidate_status": current_status}
