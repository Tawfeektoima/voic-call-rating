from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Employee,
    RecordingIngestionRecord,
    RecordingIngestionRun,
    RecordingIngestionRunStatus,
    RecordingIngestionRunTrigger,
)
from app.permissions import require_ingestion_management_access
from app.routers.auth import get_current_user
from app.schemas import (
    RecordingIngestionRecordOut,
    RecordingIngestionRunDetailOut,
    RecordingIngestionRunListOut,
    RecordingIngestionRunOut,
    RecordingIngestionRetryOut,
    RecordingIngestionRetryRequest,
)
from app.services.recording_ingestion import (
    INGESTION_AUDIT_MANUAL_START,
    INGESTION_AUDIT_RETRY,
    RecordingIngestionSecurityError,
    _build_ingestion_allowed_hosts,
    add_recording_ingestion_audit_event,
    create_ingestion_run,
    prepare_ingestion_record_retry,
    utcnow,
)
from app.worker import queue_recording_ingestion_run, queue_recording_retry


router = APIRouter(prefix="/api/recording-ingestion", tags=["Recording Ingestion"])


def _map_retry_error(exc: RecordingIngestionSecurityError) -> HTTPException:
    if exc.category == "missing_record":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)


def _ensure_ingestion_source_ready() -> None:
    settings = get_settings()
    required_values = (
        settings.CALL_INGEST_GOOGLE_SHEET_ID.strip(),
        settings.CALL_INGEST_WORKSHEET.strip(),
        settings.CALL_INGEST_RANGE.strip(),
        settings.GOOGLE_SERVICE_ACCOUNT_FILE.strip(),
    )
    if not all(required_values):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording ingestion source configuration is unavailable.",
        )
    if not _build_ingestion_allowed_hosts():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording ingestion source configuration is unavailable.",
        )


def _map_run_error(exc: RecordingIngestionSecurityError) -> HTTPException:
    if exc.category == "active_run_exists":
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail)
    if exc.category == "missing_run":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)


@router.post(
    "/runs",
    response_model=RecordingIngestionRunOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_recording_ingestion_run_endpoint(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    require_ingestion_management_access(current_user)
    _ensure_ingestion_source_ready()

    try:
        run = create_ingestion_run(
            db,
            source_name="vicdi_tests",
            trigger=RecordingIngestionRunTrigger.MANUAL,
            requested_by_employee_id=current_user.id,
        )
        db.commit()
        db.refresh(run)
    except RecordingIngestionSecurityError as exc:
        raise _map_run_error(exc) from exc

    try:
        queue_recording_ingestion_run(
            run_id=run.id,
            source_name=run.source_name,
            trigger=RecordingIngestionRunTrigger.MANUAL.value,
            requested_by_employee_id=current_user.id,
        )
        add_recording_ingestion_audit_event(
            db,
            action=INGESTION_AUDIT_MANUAL_START,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target=f"RecordingIngestionRun #{run.id}",
            after_state={
                "run_id": run.id,
                "source_name": run.source_name,
                "trigger": run.trigger,
                "status": run.status,
            },
            success=True,
        )
        db.commit()
    except Exception as exc:
        run.status = RecordingIngestionRunStatus.FAILED
        run.completed_at = utcnow()
        run.failure_summary = "Ingestion queue is unavailable."
        add_recording_ingestion_audit_event(
            db,
            action=INGESTION_AUDIT_MANUAL_START,
            actor_id=current_user.id,
            actor_email=current_user.email,
            target=f"RecordingIngestionRun #{run.id}",
            after_state={
                "run_id": run.id,
                "source_name": run.source_name,
                "trigger": run.trigger,
                "status": run.status,
            },
            reason="Ingestion queue is unavailable.",
            success=False,
        )
        db.commit()
        db.refresh(run)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recording ingestion queue is unavailable.",
        ) from exc

    return RecordingIngestionRunOut.model_validate(run)


@router.get(
    "/runs",
    response_model=RecordingIngestionRunListOut,
)
def list_recording_ingestion_runs_endpoint(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    require_ingestion_management_access(current_user)
    runs = (
        db.query(RecordingIngestionRun)
        .order_by(RecordingIngestionRun.created_at.desc(), RecordingIngestionRun.id.desc())
        .limit(limit)
        .all()
    )
    return RecordingIngestionRunListOut(items=[RecordingIngestionRunOut.model_validate(run) for run in runs])


@router.get(
    "/runs/{run_id}",
    response_model=RecordingIngestionRunDetailOut,
)
def get_recording_ingestion_run_detail_endpoint(
    run_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    require_ingestion_management_access(current_user)
    run = db.get(RecordingIngestionRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The ingestion run does not exist.")

    records_query = (
        db.query(RecordingIngestionRecord)
        .filter(RecordingIngestionRecord.ingestion_run_id == run_id)
        .order_by(RecordingIngestionRecord.source_row_number.asc(), RecordingIngestionRecord.id.asc())
    )
    total = records_query.count()
    records = records_query.offset(offset).limit(limit).all()
    return RecordingIngestionRunDetailOut(
        run=RecordingIngestionRunOut.model_validate(run),
        records=[RecordingIngestionRecordOut.model_validate(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/records/{record_id}/retry",
    response_model=RecordingIngestionRetryOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_recording_ingestion_record_endpoint(
    record_id: int,
    payload: RecordingIngestionRetryRequest | None = None,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    require_ingestion_management_access(current_user)

    try:
        record = prepare_ingestion_record_retry(
            db,
            record_id=record_id,
            requested_by_employee_id=current_user.id,
            manual=True,
        )
    except RecordingIngestionSecurityError as exc:
        raise _map_retry_error(exc) from exc

    try:
        queue_recording_retry(
            record.id,
            requested_by_employee_id=current_user.id,
            manual=True,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Retry queue is unavailable.",
        ) from exc

    retry_requested_at = datetime.now(timezone.utc)
    add_recording_ingestion_audit_event(
        db,
        action=INGESTION_AUDIT_RETRY,
        actor_id=current_user.id,
        actor_email=current_user.email,
        target=f"RecordingIngestionRecord #{record.id}",
        after_state={
            "run_id": record.ingestion_run_id,
            "record_id": record.id,
            "status": record.status,
            "error_category": record.last_error_category,
            "retry_requested_at": retry_requested_at,
        },
        reason=payload.reason if payload is not None else None,
        success=True,
    )
    db.commit()
    response = RecordingIngestionRetryOut.model_validate(record)
    return response.model_copy(update={"retry_requested_at": retry_requested_at})
