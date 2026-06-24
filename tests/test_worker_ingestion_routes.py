from datetime import timedelta
from types import SimpleNamespace

from app.database import SessionLocal
from app.models import (
    Call,
    CallStatus,
    Campaign,
    CampaignStatus,
    Employee,
    RecordingIngestionRecord,
    RecordingIngestionRecordStatus,
    RecordingIngestionRun,
    RecordingIngestionRunStatus,
    RecordingIngestionRunTrigger,
    UserRole,
)
from app import worker
from app.services.recording_ingestion import RecordingIngestionSecurityError


def test_ingestion_routes_target_the_dedicated_queue():
    routes = worker.celery_app.conf.task_routes

    assert routes["recording_ingestion.download_*"]["queue"] == worker.INGESTION_DOWNLOAD_QUEUE_NAME
    assert routes["recording_ingestion.inspect_*"]["queue"] == worker.INGESTION_INSPECTION_QUEUE_NAME
    assert routes["recording_ingestion.run_scheduled"]["queue"] == worker.INGESTION_QUEUE_NAME
    assert routes["recording_ingestion.retry_*"]["queue"] == worker.INGESTION_DOWNLOAD_QUEUE_NAME
    assert routes["recording_ingestion.reconcile_*"]["queue"] == worker.INGESTION_DOWNLOAD_QUEUE_NAME
    assert worker.INGESTION_QUEUE_NAME in {queue.name for queue in worker.celery_app.conf.task_queues}
    assert worker.INGESTION_SCHEDULE_TASK_NAME in worker.celery_app.tasks
    assert worker.INGESTION_INSPECT_RECORD_TASK_NAME in worker.celery_app.tasks
    assert worker.INGESTION_RETRY_TASK_NAME in worker.celery_app.tasks
    assert worker.INGESTION_RECONCILE_TASK_NAME in worker.celery_app.tasks


def test_ingestion_beat_schedule_is_opt_in(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", False, raising=False)
    assert worker._build_ingestion_beat_schedule() == {}

    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    monkeypatch.setattr(worker.settings, "CALL_INGEST_INTERVAL_MINUTES", 30, raising=False)

    schedule = worker._build_ingestion_beat_schedule()

    assert "recording-ingestion-scheduled-run" in schedule
    assert schedule["recording-ingestion-scheduled-run"]["task"] == worker.INGESTION_SCHEDULE_TASK_NAME
    assert schedule["recording-ingestion-scheduled-run"]["options"]["queue"] == worker.INGESTION_QUEUE_NAME
    assert schedule["recording-ingestion-scheduled-run"]["schedule"] == timedelta(minutes=30)


def test_scheduled_ingestion_task_is_safe_when_feature_is_disabled(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", False, raising=False)

    result = worker.run_scheduled_recording_ingestion()

    assert result == {"status": "skipped", "reason": "disabled"}


def test_scheduled_ingestion_task_invokes_service_when_enabled(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)

    captured: dict[str, object] = {}

    def fake_run_recording_ingestion(
        db,
        *,
        source_name,
        trigger,
        requested_by_employee_id,
        session_factory,
        inspection_queue,
        retry_queue,
    ):
        captured["source_name"] = source_name
        captured["trigger"] = trigger
        captured["requested_by_employee_id"] = requested_by_employee_id
        captured["session_factory"] = session_factory
        captured["inspection_queue"] = inspection_queue
        captured["retry_queue"] = retry_queue
        db.close()
        return SimpleNamespace(id=4321, status=SimpleNamespace(value="completed"))

    monkeypatch.setattr("app.services.recording_ingestion.run_recording_ingestion", fake_run_recording_ingestion)

    result = worker.run_scheduled_recording_ingestion()

    assert result == {"status": "completed", "run_id": 4321, "run_status": "completed"}
    assert captured["source_name"] == "vicdi_tests"
    assert getattr(captured["trigger"], "value", captured["trigger"]) == "scheduled"
    assert captured["requested_by_employee_id"] is None
    assert captured["session_factory"] is SessionLocal
    assert captured["inspection_queue"] is worker.queue_recording_inspection
    assert callable(captured["retry_queue"])


def test_queue_recording_ingestion_run_enqueues_manual_request(monkeypatch):
    captured: dict[str, object] = {}

    def fake_apply_async(*, kwargs):
        captured["kwargs"] = kwargs
        return "queued"

    monkeypatch.setattr(worker.run_scheduled_recording_ingestion, "apply_async", fake_apply_async)

    result = worker.queue_recording_ingestion_run(
        run_id=4322,
        source_name="vicdi_tests",
        trigger="manual",
        requested_by_employee_id=77,
    )

    assert result == "queued"
    assert captured["kwargs"] == {
        "run_id": 4322,
        "source_name": "vicdi_tests",
        "trigger": "manual",
        "requested_by_employee_id": 77,
    }


def test_manual_ingestion_task_resumes_requested_run_when_feature_flag_is_disabled(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", False, raising=False)
    captured: dict[str, object] = {}

    def fake_continue(db, *, run_id, session_factory, inspection_queue, retry_queue):
        captured["run_id"] = run_id
        captured["session_factory"] = session_factory
        captured["inspection_queue"] = inspection_queue
        captured["retry_queue"] = retry_queue
        db.close()
        return SimpleNamespace(id=run_id, status=SimpleNamespace(value="processing"))

    monkeypatch.setattr("app.services.recording_ingestion.continue_ingestion_run", fake_continue)

    result = worker.run_scheduled_recording_ingestion(
        run_id=7654,
        trigger=RecordingIngestionRunTrigger.MANUAL.value,
        requested_by_employee_id=88,
    )

    assert result == {"status": "completed", "run_id": 7654, "run_status": "processing"}
    assert captured["run_id"] == 7654
    assert captured["session_factory"] is SessionLocal
    assert captured["inspection_queue"] is worker.queue_recording_inspection
    assert callable(captured["retry_queue"])


def test_inspection_task_uses_the_inspector_service_and_closes_ready_run(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    run = SimpleNamespace(new_count=1, status=SimpleNamespace(value="completed_with_errors"))
    record = SimpleNamespace(id=4322, ingestion_run_id=4323, status=SimpleNamespace(value="submitted"))
    captured: dict[str, object] = {}

    def fake_inspect(db, *, record_id, retry_queue):
        captured["record_id"] = record_id
        captured["retry_queue"] = retry_queue
        return record

    def fake_finalize(db, active_run):
        captured["run"] = active_run
        return active_run

    monkeypatch.setattr("app.services.recording_ingestion.inspect_and_handoff_record", fake_inspect)
    monkeypatch.setattr("app.services.recording_ingestion.finalize_ingestion_run_if_ready", fake_finalize)
    monkeypatch.setattr(worker, "SessionLocal", lambda: SimpleNamespace(get=lambda model, key: run, commit=lambda: None, close=lambda: None))

    result = worker.inspect_recording_ingestion_record_task(4322)

    assert result == {"status": "completed", "record_id": 4322, "record_status": "submitted", "run_status": "completed_with_errors"}
    assert captured["record_id"] == 4322
    assert captured["run"] == run
    assert callable(captured["retry_queue"])


def test_recording_retry_task_invokes_service_when_enabled(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    captured: dict[str, object] = {}

    def fake_retry_record(db, *, record_id, requested_by_employee_id, manual, inspection_queue, retry_queue):
        captured["record_id"] = record_id
        captured["requested_by_employee_id"] = requested_by_employee_id
        captured["manual"] = manual
        captured["inspection_queue"] = inspection_queue
        captured["retry_queue"] = retry_queue
        return SimpleNamespace(id=12345, status=SimpleNamespace(value="submitted"), ingestion_run_id=991)

    monkeypatch.setattr("app.services.recording_ingestion.retry_ingestion_record", fake_retry_record)

    result = worker.retry_recording_ingestion_record(12345, requested_by_employee_id=77, manual=True)

    assert result == {"status": "completed", "record_id": 12345, "record_status": "submitted", "run_id": 991}
    assert captured["record_id"] == 12345
    assert captured["requested_by_employee_id"] == 77
    assert captured["manual"] is True
    assert captured["inspection_queue"] is worker.queue_recording_inspection
    assert callable(captured["retry_queue"])


def test_recording_retry_task_returns_skipped_for_safe_retry_conflicts(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    monkeypatch.setattr(
        "app.services.recording_ingestion.retry_ingestion_record",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RecordingIngestionSecurityError("active_run_exists", "Retry is already in progress.")
        ),
    )

    result = worker.retry_recording_ingestion_record(12345)

    assert result == {"status": "skipped", "reason": "active_run_exists", "record_id": 12345}


def test_recording_retry_task_sanitizes_unexpected_failure_logs(monkeypatch, caplog):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)

    def boom(*args, **kwargs):
        raise RuntimeError("download failed for https://secret.example.com/file.mp3 at D:\\sensitive\\file.mp3")

    monkeypatch.setattr("app.services.recording_ingestion.retry_ingestion_record", boom)

    with caplog.at_level("ERROR", logger="app.worker"):
        result = worker.retry_recording_ingestion_record(12346)

    assert result == {"status": "failed", "record_id": 12346}
    assert "https://secret.example.com/file.mp3" not in caplog.text
    assert "D:\\sensitive\\file.mp3" not in caplog.text
    assert "RuntimeError" in caplog.text


def test_reconciliation_task_wraps_the_existing_helper(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    monkeypatch.setattr(worker, "reconcile_committed_call_handoffs", lambda: [11, 12], raising=False)

    result = worker.reconcile_committed_call_handoffs_task()

    assert result == {"status": "completed", "queued_call_ids": [11, 12]}


def test_reconcile_committed_call_handoffs_queues_same_call_id(monkeypatch):
    db = SessionLocal()
    try:
        employee = Employee(
            id=94031,
            name="Queue Agent",
            email="queue.agent@example.com",
            employee_code="94031",
            hashed_password="hashed-password",
            role=UserRole.AGENT,
            status="active",
        )
        campaign = Campaign(
            id=94031,
            name="QUEUE_CAMPAIGN_94031",
            evaluation_prompt="Test evaluation prompt long enough for worker handoff coverage.",
            status=CampaignStatus.ACTIVE,
        )
        call = Call(
            id=95031,
            employee_id=employee.id,
            campaign_id=campaign.id,
            audio_file_path="D:\\voic call rating\\uploads\\accepted\\queue-call.mp3",
            original_filename="queue-call.mp3",
            status=CallStatus.PENDING,
            source="sheet_ingestion",
        )
        run = RecordingIngestionRun(
            id=96031,
            source_name="vicdi_tests",
            trigger=RecordingIngestionRunTrigger.MANUAL,
            status=RecordingIngestionRunStatus.COMPLETED,
            rows_seen=1,
            new_count=1,
            duplicate_count=0,
            success_count=1,
            failed_count=0,
            retryable_count=0,
        )
        record = RecordingIngestionRecord(
            id=97031,
            ingestion_run_id=run.id,
            source_name="vicdi_tests",
            source_key="queue-call-97031",
            source_row_number=2,
            source_payload={"CALL LINK": "https://example.com/queue-call.mp3"},
            recording_url="https://example.com/queue-call.mp3",
            recording_url_fingerprint="queue-fingerprint-97031",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.HANDOFF_PENDING,
            call_id=call.id,
        )
        db.add_all([employee, campaign, call, run, record])
        db.commit()
    finally:
        db.close()

    queued_call_ids: list[int] = []

    def fake_delay(call_id: int):
        queued_call_ids.append(call_id)
        return None

    monkeypatch.setattr(worker.process_call_audio_task, "delay", fake_delay, raising=False)

    result = worker.reconcile_committed_call_handoffs()

    assert result == [95031]
    assert queued_call_ids == [95031]

    verify_db = SessionLocal()
    try:
        final_record = verify_db.get(RecordingIngestionRecord, 97031)
        final_call = verify_db.get(Call, 95031)
        assert final_record is not None
        assert final_record.status == RecordingIngestionRecordStatus.SUBMITTED
        assert final_record.pipeline_queued_at is not None
        assert final_record.last_error_category is None
        assert final_call is not None
        assert final_call.status == CallStatus.PENDING
    finally:
        verify_db.close()
