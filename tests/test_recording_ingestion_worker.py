from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import worker
from app.database import Base, SessionLocal
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
from app.services import recording_ingestion as recording_ingestion_service


RECORDING_URL = "https://archive.dial-fusion.com/archive/20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17.mp3"


def _seed_employee(*, employee_id: int, code: str, name: str) -> Employee:
    db = SessionLocal()
    try:
        employee = Employee(
            id=employee_id,
            name=name,
            email=f"{code.lower()}@example.com",
            employee_code=code,
            hashed_password="hashed-password",
            role=UserRole.AGENT,
            status="active",
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee
    finally:
        db.close()


def _seed_campaign(*, campaign_id: int, status: CampaignStatus = CampaignStatus.ACTIVE) -> Campaign:
    db = SessionLocal()
    try:
        campaign = Campaign(
            id=campaign_id,
            name=f"INGEST_CAMPAIGN_{campaign_id}",
            evaluation_prompt="Test evaluation prompt long enough for worker ingestion tests.",
            status=status,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    finally:
        db.close()


def test_scheduled_worker_ingests_rows_without_live_google_or_dial_fusion_access(
    monkeypatch,
    recording_ingestion_fixture_paths: dict[str, Path],
    tmp_path: Path,
):
    campaign = _seed_campaign(campaign_id=93034)
    valid_employee = _seed_employee(employee_id=93034, code="600", name="Valid Agent")
    duplicate_employee = _seed_employee(employee_id=93035, code="601", name="Duplicate Agent")
    inaccessible_employee = _seed_employee(employee_id=93036, code="602", name="Broken Agent")

    duplicate_url = "https://archive.dial-fusion.com/duplicate-worker.mp3"
    inaccessible_url = "https://archive.dial-fusion.com/missing-worker.mp3"
    duplicate_row = {
        "DATE": "2026-05-04",
        "CODE": duplicate_employee.employee_code,
        "CRDTS": "88190",
        "NAME": "Duplicate Agent",
        "CALL LINK": duplicate_url,
        "SCORE": "95",
        "WEAKNESS": "None",
        "QUALITY FEEDBACK": "Already processed",
    }
    valid_row = {
        "DATE": "2026-05-04",
        "CODE": valid_employee.employee_code,
        "CRDTS": "88191",
        "NAME": "Valid Agent",
        "CALL LINK": RECORDING_URL,
        "SCORE": "91",
        "WEAKNESS": "Follow up",
        "QUALITY FEEDBACK": "Clear and complete",
    }
    invalid_row = {
        "DATE": "2026-05-04",
        "CODE": "999",
        "CRDTS": "88192",
        "NAME": "Unknown Agent",
        "CALL LINK": "https://archive.dial-fusion.com/unknown-worker.mp3",
        "SCORE": "88",
        "WEAKNESS": "Missing mapping",
        "QUALITY FEEDBACK": "Needs review",
    }
    inaccessible_row = {
        "DATE": "2026-05-04",
        "CODE": inaccessible_employee.employee_code,
        "CRDTS": "88193",
        "NAME": "Broken Agent",
        "CALL LINK": inaccessible_url,
        "SCORE": "83",
        "WEAKNESS": "Transport failure",
        "QUALITY FEEDBACK": "Needs retry",
    }

    settings_for_run = SimpleNamespace(
        CALL_INGEST_DEFAULT_CAMPAIGN_ID=campaign.id,
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_GOOGLE_SHEET_ID="sheet-id",
        CALL_INGEST_WORKSHEET="Calls",
        CALL_INGEST_RANGE="A:ZZ",
        CALL_INGEST_DOWNLOAD_CONCURRENCY=1,
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_QUARANTINE_DIR=tmp_path / "quarantine",
        CALL_INGEST_ACCEPTED_DIR=tmp_path / "accepted",
        CALL_INGEST_REJECTED_DIR=tmp_path / "rejected",
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)

    db = SessionLocal()
    try:
        historic_run = RecordingIngestionRun(
            id=94034,
            source_name="historic_worker_run",
            trigger=RecordingIngestionRunTrigger.MANUAL,
            status=RecordingIngestionRunStatus.COMPLETED,
            rows_seen=0,
            new_count=0,
            duplicate_count=0,
            success_count=0,
            failed_count=0,
            retryable_count=0,
        )
        duplicate_mapping = recording_ingestion_service.map_source_row(
            db=db,
            row=duplicate_row,
            row_number=3,
            source_name="vicdi_tests",
        )
        existing = RecordingIngestionRecord(
            ingestion_run_id=historic_run.id,
            source_name="vicdi_tests",
            source_key=duplicate_mapping.source_key,
            source_row_number=3,
            source_payload=duplicate_mapping.source_payload,
            recording_url=duplicate_mapping.recording_url,
            recording_url_fingerprint=duplicate_mapping.recording_url_fingerprint,
            source_call_date=duplicate_mapping.source_call_date,
            source_score=duplicate_mapping.source_score,
            source_quality_notes=duplicate_mapping.source_quality_notes,
            employee_id=duplicate_mapping.employee_id,
            campaign_id=duplicate_mapping.campaign_id,
            status=RecordingIngestionRecordStatus.SUBMITTED,
            attempt_count=1,
        )
        db.add_all([historic_run, existing])
        db.commit()
    finally:
        db.close()

    rows = [valid_row, duplicate_row, invalid_row, inaccessible_row]

    class FakeValues:
        def get(self, **kwargs):
            return self

        def execute(self):
            return {
                "range": "'Calls'!A1:H5",
                "values": [
                    ["DATE", "CODE", "CRDTS", "NAME", "CALL LINK", "SCORE", "WEAKNESS", "QUALITY FEEDBACK"],
                    *[
                        [row["DATE"], row["CODE"], row["CRDTS"], row["NAME"], row["CALL LINK"], row["SCORE"], row["WEAKNESS"], row["QUALITY FEEDBACK"]]
                        for row in rows
                    ],
                ],
            }

    fake_service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: FakeValues()))
    fixture_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()
    requested_urls: list[str] = []
    queued_call_ids: list[int] = []
    queued_inspection_record_ids: list[int] = []
    real_httpx_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        url = str(request.url)
        if url in {RECORDING_URL, duplicate_url}:
            return httpx.Response(200, content=fixture_bytes, headers={"content-type": "audio/mpeg"})
        if url == inaccessible_url:
            return httpx.Response(404, text="missing")
        raise AssertionError(f"Unexpected URL: {url}")

    def client_factory(*args, **kwargs):
        return real_httpx_client(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout"))

    class PassedScanner:
        def scan(self, path, timeout_seconds):
            return recording_ingestion_service.MalwareScanResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                scanner_name="clamd",
                scanner_version="1.0",
            )

    class PassedVerifier:
        def verify(self, path, timeout_seconds):
            return recording_ingestion_service.MediaVerificationResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                duration_seconds=0.1,
            )

    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    monkeypatch.setattr(recording_ingestion_service, "_build_google_sheets_service", lambda: fake_service, raising=False)
    monkeypatch.setattr(recording_ingestion_service.httpx, "Client", client_factory)
    monkeypatch.setattr(recording_ingestion_service, "ClamdScannerAdapter", PassedScanner, raising=False)
    monkeypatch.setattr(recording_ingestion_service, "RemoteMediaVerifier", PassedVerifier, raising=False)
    monkeypatch.setattr("app.worker.queue_call_audio_processing", lambda call_id: queued_call_ids.append(call_id))
    monkeypatch.setattr(worker, "queue_recording_inspection", queued_inspection_record_ids.append)

    result = worker.run_scheduled_recording_ingestion()

    assert result["status"] == "completed"
    assert result["run_status"] == RecordingIngestionRunStatus.PROCESSING.value
    assert queued_call_ids == []
    assert len(queued_inspection_record_ids) == 1
    assert requested_urls.count(RECORDING_URL) == 1
    assert duplicate_url not in requested_urls
    assert all(url.startswith("https://archive.dial-fusion.com/") for url in requested_urls)

    settings_for_run.CALL_INGEST_RUNTIME_ROLE = "inspector"
    inspection_result = worker.inspect_recording_ingestion_record_task(queued_inspection_record_ids[0])

    assert inspection_result["status"] == "completed"
    assert inspection_result["run_status"] == RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS.value
    assert queued_call_ids and len(queued_call_ids) == 1

    verify_db = SessionLocal()
    try:
        calls = verify_db.query(Call).all()
        records = verify_db.query(RecordingIngestionRecord).all()
        accepted_records = [record for record in records if record.call_id is not None]

        assert len(calls) == 1
        assert len(accepted_records) == 1

        accepted_call = calls[0]
        accepted_record = accepted_records[0]
        assert accepted_call.id == queued_call_ids[0]
        assert accepted_call.status == CallStatus.PENDING
        assert accepted_call.source == "sheet_ingestion"
        assert accepted_call.audio_file_path is not None
        assert Path(accepted_call.audio_file_path).is_file()

        assert accepted_record.status == RecordingIngestionRecordStatus.SUBMITTED
        assert accepted_record.pipeline_queued_at is not None
        assert accepted_record.stored_file_path is not None
        assert Path(accepted_record.stored_file_path).is_file()
        assert accepted_record.source_payload["CALL LINK"] == RECORDING_URL
        assert accepted_record.file_sha256 is not None
        assert not list((tmp_path / "quarantine").glob("*.part"))
    finally:
        verify_db.close()


def test_retry_worker_recovers_a_transient_timeout_without_creating_duplicate_calls(
    monkeypatch,
    recording_ingestion_fixture_paths: dict[str, Path],
    tmp_path: Path,
):
    campaign = _seed_campaign(campaign_id=93044)
    employee = _seed_employee(employee_id=93044, code="93044", name="Retry Worker Agent")
    settings_for_run = SimpleNamespace(
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        CALL_INGEST_QUARANTINE_DIR=tmp_path / "quarantine",
        CALL_INGEST_ACCEPTED_DIR=tmp_path / "accepted",
        CALL_INGEST_REJECTED_DIR=tmp_path / "rejected",
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)

    historic_run = RecordingIngestionRun(
        id=94044,
        source_name="retry-worker-source-history",
        trigger=RecordingIngestionRunTrigger.MANUAL,
        status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
        rows_seen=1,
        new_count=1,
        duplicate_count=0,
        success_count=0,
        failed_count=1,
        retryable_count=1,
    )
    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            id=97044,
            ingestion_run_id=historic_run.id,
            source_name="retry-worker-source",
            source_key="retry-worker-source:record",
            source_row_number=2,
            source_payload={"CALL LINK": RECORDING_URL},
            recording_url=RECORDING_URL,
            recording_url_fingerprint="retry-worker-source-record",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.RETRY_SCHEDULED,
            attempt_count=1,
            next_retry_at=recording_ingestion_service.utcnow() - timedelta(minutes=1),
            last_error_category="download_timeout",
            last_error_detail="Temporary timeout at https://archive.dial-fusion.com/private.mp3",
        )
        db.add_all([historic_run, record])
        db.commit()
    finally:
        db.close()

    fixture_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()
    queued_record_ids: list[int] = []
    queued_call_ids: list[int] = []
    real_httpx_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == RECORDING_URL
        return httpx.Response(200, content=fixture_bytes, headers={"content-type": "audio/mpeg"})

    def client_factory(*args, **kwargs):
        return real_httpx_client(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout"))

    class PassedScanner:
        def scan(self, path, timeout_seconds):
            return recording_ingestion_service.MalwareScanResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                scanner_name="clamd",
                scanner_version="1.0",
            )

    class PassedVerifier:
        def verify(self, path, timeout_seconds):
            return recording_ingestion_service.MediaVerificationResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                duration_seconds=0.1,
            )

    monkeypatch.setattr(recording_ingestion_service.httpx, "Client", client_factory)
    monkeypatch.setattr(recording_ingestion_service, "ClamdScannerAdapter", PassedScanner, raising=False)
    monkeypatch.setattr(recording_ingestion_service, "RemoteMediaVerifier", PassedVerifier, raising=False)
    monkeypatch.setattr(worker, "queue_recording_inspection", queued_record_ids.append)
    monkeypatch.setattr("app.worker.queue_call_audio_processing", lambda call_id: queued_call_ids.append(call_id))

    retry_result = worker.retry_recording_ingestion_record(97044)

    assert retry_result["status"] == "completed"
    assert retry_result["record_id"] == 97044
    assert queued_record_ids == [97044]

    inspection_result = worker.inspect_recording_ingestion_record_task(97044)

    assert inspection_result["status"] == "completed"
    assert queued_call_ids and len(queued_call_ids) == 1

    verify_db = SessionLocal()
    try:
        final_record = verify_db.get(RecordingIngestionRecord, 97044)
        calls = verify_db.query(Call).all()
        assert final_record is not None
        assert final_record.status == RecordingIngestionRecordStatus.SUBMITTED
        assert final_record.call_id == queued_call_ids[0]
        assert final_record.pipeline_queued_at is not None
        assert final_record.last_error_detail is None or "https://" not in final_record.last_error_detail
        assert len(calls) == 1
        assert calls[0].id == queued_call_ids[0]
    finally:
        verify_db.close()


def test_retry_worker_skips_exhausted_retry_records(monkeypatch):
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)
    historic_run = RecordingIngestionRun(
        id=94045,
        source_name="retry-worker-exhausted",
        trigger=RecordingIngestionRunTrigger.MANUAL,
        status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
        rows_seen=1,
        new_count=1,
        duplicate_count=0,
        success_count=0,
        failed_count=1,
        retryable_count=0,
    )
    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            id=97045,
            ingestion_run_id=historic_run.id,
            source_name="retry-worker-exhausted",
            source_key="retry-worker-exhausted:record",
            source_row_number=2,
            source_payload={"CALL LINK": RECORDING_URL},
            recording_url=RECORDING_URL,
            recording_url_fingerprint="retry-worker-exhausted-record",
            status=RecordingIngestionRecordStatus.FAILED,
            attempt_count=3,
            last_error_category="download_timeout",
            last_error_detail="Retries exhausted for https://archive.dial-fusion.com/exhausted.mp3",
        )
        db.add_all([historic_run, record])
        db.commit()
    finally:
        db.close()

    result = worker.retry_recording_ingestion_record(97045)

    assert result == {"status": "skipped", "reason": "retry_not_due", "record_id": 97045}


@pytest.mark.parametrize(
    ("record_status", "record_id", "call_id", "run_id", "employee_id", "campaign_id"),
    (
        (RecordingIngestionRecordStatus.HANDOFF_PENDING, 97031, 95031, 96031, 94031, 94031),
        (RecordingIngestionRecordStatus.ACCEPTED, 97032, 95032, 96032, 94032, 94032),
    ),
)
def test_reconcile_committed_call_handoffs_queues_same_call_id_without_duplicate_calls(
    monkeypatch,
    record_status,
    record_id,
    call_id,
    run_id,
    employee_id,
    campaign_id,
):
    db = SessionLocal()
    try:
        employee = Employee(
            id=employee_id,
            name="Queue Agent",
            email=f"queue.agent{employee_id}@example.com",
            employee_code=str(employee_id),
            hashed_password="hashed-password",
            role=UserRole.AGENT,
            status="active",
        )
        campaign = Campaign(
            id=campaign_id,
            name=f"QUEUE_CAMPAIGN_{campaign_id}",
            evaluation_prompt="Test evaluation prompt long enough for worker handoff coverage.",
            status=CampaignStatus.ACTIVE,
        )
        call = Call(
            id=call_id,
            employee_id=employee.id,
            campaign_id=campaign.id,
            audio_file_path=f"D:\\voic call rating\\uploads\\accepted\\queue-call-{call_id}.mp3",
            original_filename=f"queue-call-{call_id}.mp3",
            status=CallStatus.PENDING,
            source="sheet_ingestion",
        )
        run = RecordingIngestionRun(
            id=run_id,
            source_name=f"vicdi_tests_{record_id}",
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
            id=record_id,
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key=f"queue-call-{record_id}",
            source_row_number=2,
            source_payload={"CALL LINK": f"https://example.com/queue-call-{record_id}.mp3"},
            recording_url=f"https://example.com/queue-call-{record_id}.mp3",
            recording_url_fingerprint=f"queue-fingerprint-{record_id}",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=record_status,
            call_id=call.id,
        )
        db.add_all([employee, campaign, call, run, record])
        db.commit()
    finally:
        db.close()

    queued_call_ids: list[int] = []

    def fake_delay(queued_call_id: int):
        queued_call_ids.append(queued_call_id)
        return None

    monkeypatch.setattr(worker.process_call_audio_task, "delay", fake_delay, raising=False)

    result = worker.reconcile_committed_call_handoffs()

    assert result == [call_id]
    assert queued_call_ids == [call_id]

    verify_db = SessionLocal()
    try:
        final_record = verify_db.get(RecordingIngestionRecord, record_id)
        final_call = verify_db.get(Call, call_id)
        calls = verify_db.query(Call).filter(Call.id == call_id).all()
        assert final_record is not None
        assert final_record.status == RecordingIngestionRecordStatus.SUBMITTED
        assert final_record.pipeline_queued_at is not None
        assert final_record.last_error_category is None
        assert final_call is not None
        assert final_call.status == CallStatus.PENDING
        assert len(calls) == 1
    finally:
        verify_db.close()


def test_scheduled_worker_processes_100_records_with_bounded_download_concurrency(
    monkeypatch,
    recording_ingestion_fixture_paths: dict[str, Path],
    tmp_path: Path,
):
    database_path = tmp_path / "performance-worker.sqlite"
    performance_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    PerformanceSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=performance_engine)
    Base.metadata.create_all(bind=performance_engine)

    monkeypatch.setattr(worker, "SessionLocal", PerformanceSessionLocal)
    monkeypatch.setattr(recording_ingestion_service, "SessionLocal", PerformanceSessionLocal)

    db = PerformanceSessionLocal()
    try:
        campaign = Campaign(
            id=93100,
            name="INGEST_CAMPAIGN_93100",
            evaluation_prompt="Test evaluation prompt long enough for worker ingestion tests.",
            status=CampaignStatus.ACTIVE,
        )
        db.add(campaign)
        db.add_all(
            [
                Employee(
                    id=93100 + index,
                    name=f"Performance Agent {index:03d}",
                    email=f"perf-agent-{index:03d}@example.com",
                    employee_code=f"P{index:03d}",
                    hashed_password="hashed-password",
                    role=UserRole.AGENT,
                    status="active",
                )
                for index in range(100)
            ]
        )
        db.commit()
    finally:
        db.close()

        fixture_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()

        settings_for_run = SimpleNamespace(
        CALL_INGEST_DEFAULT_CAMPAIGN_ID=93100,
            CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_GOOGLE_SHEET_ID="sheet-id",
        CALL_INGEST_WORKSHEET="Calls",
        CALL_INGEST_RANGE="A:ZZ",
        CALL_INGEST_DOWNLOAD_CONCURRENCY=4,
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_QUARANTINE_DIR=tmp_path / "quarantine",
        CALL_INGEST_ACCEPTED_DIR=tmp_path / "accepted",
        CALL_INGEST_REJECTED_DIR=tmp_path / "rejected",
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    monkeypatch.setattr(worker.settings, "CALL_INGEST_ENABLED", True, raising=False)

    queued_inspection_record_ids: list[int] = []
    queued_call_ids: list[int] = []
    concurrency_lock = threading.Lock()
    active_downloads = 0
    peak_requests = 0
    requested_urls: list[str] = []

    rows = [
        {
            "DATE": "2026-05-04",
            "CODE": f"P{index:03d}",
            "CRDTS": f"PERF-{index:03d}",
            "NAME": f"Performance Agent {index:03d}",
            "CALL LINK": f"https://archive.dial-fusion.com/perf-{index:03d}.mp3",
            "SCORE": "90",
            "WEAKNESS": "Synthetic fixture",
            "QUALITY FEEDBACK": "Performance validation fixture",
        }
        for index in range(100)
    ]

    class FakeValues:
        def get(self, **kwargs):
            return self

        def execute(self):
            return {
                "range": "'Calls'!A1:H101",
                "values": [
                    ["DATE", "CODE", "CRDTS", "NAME", "CALL LINK", "SCORE", "WEAKNESS", "QUALITY FEEDBACK"],
                    *[
                        [
                            row["DATE"],
                            row["CODE"],
                            row["CRDTS"],
                            row["NAME"],
                            row["CALL LINK"],
                            row["SCORE"],
                            row["WEAKNESS"],
                            row["QUALITY FEEDBACK"],
                        ]
                        for row in rows
                    ],
                ],
            }

    fake_service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: FakeValues()))
    real_httpx_client = httpx.Client

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active_downloads, peak_requests
        with concurrency_lock:
            active_downloads += 1
            peak_requests = max(peak_requests, active_downloads)
        try:
            time.sleep(0.01)
            requested_urls.append(str(request.url))
            return httpx.Response(
                200,
                content=fixture_bytes,
                headers={"content-type": "audio/mpeg"},
            )
        finally:
            with concurrency_lock:
                active_downloads -= 1

    def client_factory(*args, **kwargs):
        return real_httpx_client(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout"))

    class PassedScanner:
        def scan(self, path, timeout_seconds):
            return recording_ingestion_service.MalwareScanResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                scanner_name="clamd",
                scanner_version="1.0",
            )

    class PassedVerifier:
        def verify(self, path, timeout_seconds):
            return recording_ingestion_service.MediaVerificationResult(
                status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                duration_seconds=0.1,
            )

    monkeypatch.setattr(recording_ingestion_service, "_build_google_sheets_service", lambda: fake_service, raising=False)
    monkeypatch.setattr(recording_ingestion_service.httpx, "Client", client_factory)
    monkeypatch.setattr(recording_ingestion_service, "ClamdScannerAdapter", PassedScanner, raising=False)
    monkeypatch.setattr(recording_ingestion_service, "RemoteMediaVerifier", PassedVerifier, raising=False)
    monkeypatch.setattr(worker, "queue_recording_inspection", queued_inspection_record_ids.append)
    monkeypatch.setattr("app.worker.queue_call_audio_processing", lambda call_id: queued_call_ids.append(call_id))

    started_at = time.perf_counter()
    result = worker.run_scheduled_recording_ingestion()
    download_elapsed = time.perf_counter() - started_at

    assert result["status"] == "completed"
    assert result["run_status"] == RecordingIngestionRunStatus.PROCESSING.value
    assert len(queued_inspection_record_ids) == 100
    assert len(set(queued_inspection_record_ids)) == 100
    assert len(requested_urls) == 100
    assert len(set(requested_urls)) == 100
    assert peak_requests <= 4
    assert download_elapsed < 15

    settings_for_run.CALL_INGEST_RUNTIME_ROLE = "inspector"
    end_to_end_started_at = time.perf_counter()
    inspection_results = [
        worker.inspect_recording_ingestion_record_task(record_id)
        for record_id in queued_inspection_record_ids
    ]
    end_to_end_elapsed = time.perf_counter() - end_to_end_started_at + download_elapsed

    assert all(item["status"] == "completed" for item in inspection_results)
    assert inspection_results[-1]["run_status"] == RecordingIngestionRunStatus.COMPLETED.value
    assert len(queued_call_ids) == 100
    assert len(set(queued_call_ids)) == 100
    assert end_to_end_elapsed < 15

    verify_db = PerformanceSessionLocal()
    try:
        latest_run = verify_db.query(RecordingIngestionRun).order_by(RecordingIngestionRun.id.desc()).first()
        records = verify_db.query(RecordingIngestionRecord).order_by(RecordingIngestionRecord.id.asc()).all()
        calls = verify_db.query(Call).order_by(Call.id.asc()).all()

        assert latest_run is not None
        assert latest_run.rows_seen == 100
        assert latest_run.new_count == 100
        assert latest_run.success_count == 100
        assert latest_run.failed_count == 0
        assert latest_run.retryable_count == 0
        assert latest_run.status == RecordingIngestionRunStatus.COMPLETED
        assert len(records) == 100
        assert all(record.status == RecordingIngestionRecordStatus.SUBMITTED for record in records)
        assert all(record.pipeline_queued_at is not None for record in records)
        assert all(record.call_id is not None for record in records)
        assert all(record.byte_size == len(fixture_bytes) for record in records)
        assert sum(record.byte_size or 0 for record in records) == len(fixture_bytes) * 100
        assert len(calls) == 100
        assert all(call.status == CallStatus.PENDING for call in calls)
        assert all(call.source == "sheet_ingestion" for call in calls)
        assert all(call.audio_file_path and Path(call.audio_file_path).is_file() for call in calls)
        assert len(list((tmp_path / "accepted").iterdir())) == 100
        assert not list((tmp_path / "quarantine").glob("*.part"))
        assert not list((tmp_path / "rejected").iterdir())
    finally:
        verify_db.close()
        performance_engine.dispose()
