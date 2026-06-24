import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import yaml

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.models import (
    AuditEvent,
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
from app.routers.auth import get_current_user
from app.services import recording_ingestion as recording_ingestion_service


client = TestClient(app)


def _mock_user(*, employee_id: int, role: UserRole) -> Employee:
    return Employee(
        id=employee_id,
        name=f"User {employee_id}",
        email=f"user{employee_id}@example.com",
        employee_code=f"EMP{employee_id}",
        hashed_password="hashed",
        role=role,
        status="active",
    )


def _seed_retry_record(
    *,
    record_id: int,
    status: RecordingIngestionRecordStatus,
    last_error_category: str | None = "access_denied",
    last_error_detail: str | None = None,
) -> RecordingIngestionRecord:
    db = SessionLocal()
    try:
        run = RecordingIngestionRun(
            id=record_id + 1000,
            source_name=f"api-retry-source-{record_id}",
            trigger=RecordingIngestionRunTrigger.MANUAL,
            status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
            rows_seen=1,
            new_count=1,
            duplicate_count=0,
            success_count=0,
            failed_count=1,
            retryable_count=1,
        )
        record = RecordingIngestionRecord(
            id=record_id,
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key=f"{run.source_name}:record",
            source_row_number=2,
            source_payload={"CALL LINK": "https://archive.dial-fusion.com/private.mp3"},
            recording_url="https://archive.dial-fusion.com/private.mp3",
            recording_url_fingerprint=f"fingerprint-{record_id}",
            status=status,
            attempt_count=1,
            last_error_category=last_error_category,
            last_error_detail=last_error_detail,
        )
        db.add_all([run, record])
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def _seed_run(
    *,
    run_id: int,
    status: RecordingIngestionRunStatus,
    trigger: RecordingIngestionRunTrigger = RecordingIngestionRunTrigger.MANUAL,
    source_name: str = "vicdi_tests",
    failure_summary: str | None = None,
    created_at: datetime | None = None,
    requested_by_employee_id: int | None = None,
) -> RecordingIngestionRun:
    db = SessionLocal()
    try:
        run = RecordingIngestionRun(
            id=run_id,
            source_name=source_name,
            trigger=trigger,
            status=status,
            rows_seen=0,
            new_count=0,
            duplicate_count=0,
            success_count=0,
            failed_count=0,
            retryable_count=0,
            failure_summary=failure_summary,
            created_at=created_at or datetime.now(timezone.utc),
            requested_by_employee_id=requested_by_employee_id,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()


def _seed_run_record(
    *,
    record_id: int,
    run_id: int,
    status: RecordingIngestionRecordStatus,
    row_number: int = 2,
    source_payload: dict | None = None,
    last_error_category: str | None = None,
    last_error_detail: str | None = None,
    call_id: int | None = None,
) -> RecordingIngestionRecord:
    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            id=record_id,
            ingestion_run_id=run_id,
            source_name="vicdi_tests",
            source_key=f"vicdi_tests:{record_id}",
            source_row_number=row_number,
            source_payload=source_payload or {"CRDTS": f"CRDTS-{record_id}", "CALL LINK": f"https://archive.dial-fusion.com/{record_id}.mp3"},
            recording_url=f"https://archive.dial-fusion.com/{record_id}.mp3",
            recording_url_fingerprint=f"fingerprint-{record_id}",
            status=status,
            attempt_count=1,
            last_error_category=last_error_category,
            last_error_detail=last_error_detail,
            call_id=call_id,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    finally:
        db.close()


def test_recording_ingestion_contract_paths_are_exposed():
    contract = yaml.safe_load(
        Path("D:/voic call rating/specs/001-call-recording-ingestion/contracts/recording-ingestion.openapi.yaml").read_text(
            encoding="utf-8"
        )
    )
    app_schema = app.openapi()

    for path, methods in contract["paths"].items():
        assert path in app_schema["paths"]
        for method in methods:
            assert method in app_schema["paths"][path]

    contract_detail = contract["paths"]["/api/recording-ingestion/runs/{run_id}"]["get"]
    assert {parameter["$ref"] for parameter in contract_detail["parameters"]} == {
        "#/components/parameters/RunId",
        "#/components/parameters/Limit",
        "#/components/parameters/Offset",
    }
    contract_detail_schema = contract_detail["responses"]["200"]["content"]["application/json"]["schema"]
    assert set(contract_detail_schema["required"]) == {"run", "records", "total", "limit", "offset"}

    generated_parameters = {
        parameter["name"]: parameter
        for parameter in app_schema["paths"]["/api/recording-ingestion/runs/{run_id}"]["get"]["parameters"]
    }
    assert generated_parameters["limit"]["schema"].items() >= {
        "type": "integer",
        "maximum": 100,
        "minimum": 1,
        "default": 50,
    }.items()
    assert generated_parameters["offset"]["schema"].items() >= {
        "type": "integer",
        "minimum": 0,
        "default": 0,
    }.items()


def test_manual_run_endpoint_queues_requested_run(monkeypatch):
    admin = _mock_user(employee_id=98020, role=UserRole.ADMIN)
    captured: dict[str, object] = {}

    def fake_queue(**kwargs):
        captured.update(kwargs)
        return None

    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr("app.routers.recording_ingestion._ensure_ingestion_source_ready", lambda: None)
    monkeypatch.setattr("app.routers.recording_ingestion.queue_recording_ingestion_run", fake_queue)

    try:
        response = client.post("/api/recording-ingestion/runs")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 202
    payload = response.json()
    assert payload["source_name"] == "vicdi_tests"
    assert payload["trigger"] == RecordingIngestionRunTrigger.MANUAL.value
    assert payload["status"] == RecordingIngestionRunStatus.REQUESTED.value
    assert captured["run_id"] == payload["id"]
    assert captured["source_name"] == "vicdi_tests"
    assert captured["trigger"] == RecordingIngestionRunTrigger.MANUAL.value
    assert captured["requested_by_employee_id"] == admin.id

    db = SessionLocal()
    try:
        run = db.get(RecordingIngestionRun, payload["id"])
        assert run is not None
        assert run.status == RecordingIngestionRunStatus.REQUESTED
        assert run.requested_by_employee_id == admin.id
    finally:
        db.close()


def test_manual_run_endpoint_returns_conflict_for_active_run(monkeypatch):
    _seed_run(run_id=98021, status=RecordingIngestionRunStatus.PROCESSING, source_name="vicdi_tests")
    admin = _mock_user(employee_id=98022, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr("app.routers.recording_ingestion._ensure_ingestion_source_ready", lambda: None)

    try:
        response = client.post("/api/recording-ingestion/runs")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 409


def test_manual_run_endpoint_marks_run_failed_when_queue_is_unavailable(monkeypatch):
    admin = _mock_user(employee_id=98023, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr("app.routers.recording_ingestion._ensure_ingestion_source_ready", lambda: None)
    monkeypatch.setattr(
        "app.routers.recording_ingestion.queue_recording_ingestion_run",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("queue down")),
    )

    try:
        response = client.post("/api/recording-ingestion/runs")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 503

    db = SessionLocal()
    try:
        latest_run = (
            db.query(RecordingIngestionRun)
            .filter(RecordingIngestionRun.requested_by_employee_id == admin.id)
            .order_by(RecordingIngestionRun.id.desc())
            .first()
        )
        assert latest_run is not None
        assert latest_run.status == RecordingIngestionRunStatus.FAILED
        assert latest_run.completed_at is not None
        assert latest_run.failure_summary == "Ingestion queue is unavailable."
    finally:
        db.close()


def test_list_runs_endpoint_returns_recent_sanitized_runs():
    now = datetime.now(timezone.utc)
    _seed_run(
        run_id=98024,
        status=RecordingIngestionRunStatus.FAILED,
        source_name="vicdi_tests_failed",
        failure_summary="Failed at https://secret.example.com/file and D:\\guest\\quarantine\\bad.mp3",
        created_at=now - timedelta(minutes=5),
    )
    _seed_run(
        run_id=98025,
        status=RecordingIngestionRunStatus.COMPLETED,
        source_name="vicdi_tests_completed",
        created_at=now,
    )
    admin = _mock_user(employee_id=98024, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.get("/api/recording-ingestion/runs?limit=2")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload)
    assert [item["id"] for item in payload["items"]] == [98025, 98024]
    assert payload["items"][1]["failure_summary"] == "Failed at [redacted-url] and [redacted-path]"
    assert "https://secret.example.com/file" not in serialized
    assert "D:\\guest\\quarantine\\bad.mp3" not in serialized


def test_run_detail_endpoint_returns_paginated_records_with_safe_fields():
    _seed_run(run_id=98026, status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS)
    _seed_run_record(
        record_id=980260,
        run_id=98026,
        row_number=2,
        status=RecordingIngestionRecordStatus.SUBMITTED,
        source_payload={"CRDTS": "SAFE-CRDTS-1", "CALL LINK": "https://archive.dial-fusion.com/one.mp3"},
        call_id=7001,
    )
    _seed_run_record(
        record_id=980261,
        run_id=98026,
        row_number=3,
        status=RecordingIngestionRecordStatus.FAILED,
        source_payload={"CRDTS": "SAFE-CRDTS-2", "CALL LINK": "https://archive.dial-fusion.com/two.mp3"},
        last_error_category="download_failed",
        last_error_detail="Denied by https://private.example.com/two and D:\\guest\\accepted\\two.mp3",
    )
    admin = _mock_user(employee_id=98025, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.get("/api/recording-ingestion/runs/98026?limit=1&offset=1")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload)
    assert payload["run"]["id"] == 98026
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert len(payload["records"]) == 1
    assert payload["records"][0]["id"] == 980261
    assert payload["records"][0]["source_reference"] == "SAFE-CRDTS-2"
    assert payload["records"][0]["error_category"] == "download_failed"
    assert payload["records"][0]["error_detail"] == "Denied by [redacted-url] and [redacted-path]"
    assert "https://archive.dial-fusion.com/two.mp3" not in serialized
    assert "D:\\guest\\accepted\\two.mp3" not in serialized


def test_run_detail_endpoint_replaces_unsafe_error_categories():
    _seed_run(run_id=980262, status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS)
    _seed_run_record(
        record_id=9802620,
        run_id=980262,
        status=RecordingIngestionRecordStatus.FAILED,
        last_error_category="https://private.example.com/token=topsecret",
        last_error_detail="Recording inspection failed.",
    )
    admin = _mock_user(employee_id=980262, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.get("/api/recording-ingestion/runs/980262")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    serialized = json.dumps(payload)
    assert payload["records"][0]["error_category"] == "unclassified_error"
    assert "https://private.example.com/token=topsecret" not in serialized


def test_remote_media_verifier_replaces_untrusted_error_category(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "status": "rejected",
                "error_category": "https://private.example.com/token=topsecret",
                "error_detail": "Verifier rejected the file.",
            }

    class FakeClient:
        def __init__(self, **kwargs):
            del kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            del args, kwargs
            return FakeResponse()

    monkeypatch.setattr(recording_ingestion_service.httpx, "Client", FakeClient)

    result = recording_ingestion_service.RemoteMediaVerifier("http://media-verifier").verify(
        Path("safe-recording.mp3"),
        timeout_seconds=5,
    )

    assert result.error_category == "media_verification_failed"
    assert "private.example.com" not in (result.error_category or "")


def test_ingestion_audit_event_sanitizes_target():
    sensitive_url = "https://private.example.com/token=topsecret"
    sensitive_path = r"D:\guest\quarantine\private-call.mp3"
    db = SessionLocal()
    try:
        event = recording_ingestion_service.add_recording_ingestion_audit_event(
            db,
            action="RECORDING_INGESTION_TEST",
            target=f"Record from {sensitive_url} at {sensitive_path}",
        )
        db.commit()
        db.refresh(event)

        assert event.target == "Record from [redacted-url] at [redacted-path]"
        assert sensitive_url not in (event.target or "")
        assert sensitive_path not in (event.target or "")
    finally:
        db.close()


def test_run_detail_endpoint_returns_not_found_for_missing_run():
    admin = _mock_user(employee_id=98026, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.get("/api/recording-ingestion/runs/999998")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_run_operations_require_ingestion_management_access():
    agent = _mock_user(employee_id=98027, role=UserRole.AGENT)
    app.dependency_overrides[get_current_user] = lambda: agent

    try:
        list_response = client.get("/api/recording-ingestion/runs")
        create_response = client.post("/api/recording-ingestion/runs")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert list_response.status_code == 403
    assert create_response.status_code == 403


def test_run_detail_endpoint_returns_mixed_run_totals_traceability_and_timestamps():
    run = _seed_run(
        run_id=98028,
        status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
        source_name="mixed-run-audit-source",
    )

    db = SessionLocal()
    try:
        run.started_at = datetime.now(timezone.utc) - timedelta(minutes=2)
        run.completed_at = datetime.now(timezone.utc)
        run.rows_seen = 3
        run.new_count = 2
        run.duplicate_count = 1
        run.success_count = 1
        run.failed_count = 1
        run.retryable_count = 1
        db.merge(run)
        db.commit()
    finally:
        db.close()

    _seed_run_record(
        record_id=980280,
        run_id=98028,
        status=RecordingIngestionRecordStatus.SUBMITTED,
        source_payload={"CRDTS": "TRACE-CALL-1", "CALL LINK": "https://archive.dial-fusion.com/trace-1.mp3"},
        call_id=8011,
    )
    _seed_run_record(
        record_id=980281,
        run_id=98028,
        status=RecordingIngestionRecordStatus.FAILED,
        source_payload={"CRDTS": "TRACE-CALL-2", "CALL LINK": "https://archive.dial-fusion.com/trace-2.mp3"},
        last_error_category="download_timeout",
    )
    admin = _mock_user(employee_id=98028, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.get("/api/recording-ingestion/runs/98028")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["run"]["rows_seen"] == 3
    assert payload["run"]["new_count"] == 2
    assert payload["run"]["duplicate_count"] == 1
    assert payload["run"]["success_count"] == 1
    assert payload["run"]["failed_count"] == 1
    assert payload["run"]["retryable_count"] == 1
    assert payload["run"]["started_at"] is not None
    assert payload["run"]["completed_at"] is not None
    assert payload["run"]["created_at"] is not None
    assert {item["source_reference"] for item in payload["records"]} == {"TRACE-CALL-1", "TRACE-CALL-2"}
    assert {item["call_id"] for item in payload["records"] if item["call_id"] is not None} == {8011}


def test_ingestion_audit_feed_masks_sensitive_values_across_events(
    monkeypatch,
    tmp_path,
    recording_ingestion_fixture_paths,
):
    sensitive_url = "https://sensitive.example.com/token=topsecret"
    sensitive_path = r"D:\guest\quarantine\private-call.mp3"
    admin = _mock_user(employee_id=98029, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        monkeypatch.setattr("app.routers.recording_ingestion._ensure_ingestion_source_ready", lambda: None)
        monkeypatch.setattr("app.routers.recording_ingestion.queue_recording_ingestion_run", lambda **kwargs: None)
        monkeypatch.setattr("app.routers.recording_ingestion.queue_recording_retry", lambda *args, **kwargs: None)

        run_response = client.post("/api/recording-ingestion/runs")
        assert run_response.status_code == 202

        _seed_retry_record(
            record_id=980290,
            status=RecordingIngestionRecordStatus.FAILED,
            last_error_category="access_denied",
            last_error_detail=f"Denied from {sensitive_url} and {sensitive_path}",
        )
        retry_response = client.post(
            "/api/recording-ingestion/records/980290/retry",
            json={"reason": f"Retry requested for {sensitive_url} at {sensitive_path}"},
        )
        assert retry_response.status_code == 202

        audio_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()
        settings_for_inspection = SimpleNamespace(
            CALL_INGEST_RUNTIME_ROLE="all",
            CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
            CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        )
        monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_inspection)
        layout = recording_ingestion_service.ensure_storage_layout(
            recording_ingestion_service.build_storage_layout(
                quarantine_dir=tmp_path / "quarantine",
                accepted_dir=tmp_path / "accepted",
                rejected_dir=tmp_path / "rejected",
            )
        )

        reject_quarantine = layout.quarantine_dir / "reject.mp3"
        reject_quarantine.write_bytes(audio_bytes)
        accept_quarantine = layout.quarantine_dir / "accept.mp3"
        accept_quarantine.write_bytes(audio_bytes)

        db = SessionLocal()
        try:
            employee = Employee(
                id=980291,
                name="Audit Feed Agent",
                email="audit.feed.agent@example.com",
                employee_code="980291",
                hashed_password="hashed-password",
                role=UserRole.AGENT,
                status="active",
            )
            campaign = Campaign(
                id=980291,
                name="AUDIT_FEED_CAMPAIGN",
                evaluation_prompt="Audit feed campaign prompt long enough for ingestion tests.",
                status=CampaignStatus.ACTIVE,
            )
            run_reject = RecordingIngestionRun(
                id=980291,
                source_name="audit-reject-source",
                trigger=RecordingIngestionRunTrigger.MANUAL,
                status=RecordingIngestionRunStatus.PROCESSING,
                rows_seen=1,
                new_count=1,
                duplicate_count=0,
                success_count=0,
                failed_count=0,
                retryable_count=0,
            )
            run_accept = RecordingIngestionRun(
                id=980292,
                source_name="audit-accept-source",
                trigger=RecordingIngestionRunTrigger.MANUAL,
                status=RecordingIngestionRunStatus.PROCESSING,
                rows_seen=1,
                new_count=1,
                duplicate_count=0,
                success_count=0,
                failed_count=0,
                retryable_count=0,
            )
            run_reconcile = RecordingIngestionRun(
                id=980293,
                source_name="audit-reconcile-source",
                trigger=RecordingIngestionRunTrigger.MANUAL,
                status=RecordingIngestionRunStatus.COMPLETED,
                rows_seen=1,
                new_count=1,
                duplicate_count=0,
                success_count=1,
                failed_count=0,
                retryable_count=0,
            )
            reject_record = RecordingIngestionRecord(
                id=980291,
                ingestion_run_id=run_reject.id,
                source_name=run_reject.source_name,
                source_key="audit-reject-source:record",
                source_row_number=2,
                source_payload={"CRDTS": "AUDIT-REJECT-1", "CALL LINK": sensitive_url},
                recording_url=sensitive_url,
                recording_url_fingerprint="audit-reject-fingerprint",
                status=RecordingIngestionRecordStatus.QUARANTINED,
                quarantine_file_path=str(reject_quarantine),
                content_type="audio/mpeg",
            )
            accept_record = RecordingIngestionRecord(
                id=980292,
                ingestion_run_id=run_accept.id,
                source_name=run_accept.source_name,
                source_key="audit-accept-source:record",
                source_row_number=2,
                source_payload={"CRDTS": "AUDIT-ACCEPT-1", "CALL LINK": sensitive_url},
                recording_url=sensitive_url,
                recording_url_fingerprint="audit-accept-fingerprint",
                employee_id=employee.id,
                campaign_id=campaign.id,
                status=RecordingIngestionRecordStatus.QUARANTINED,
                quarantine_file_path=str(accept_quarantine),
                content_type="audio/mpeg",
            )
            reconcile_call = Call(
                id=980293,
                employee_id=employee.id,
                campaign_id=campaign.id,
                audio_file_path=str(layout.accepted_dir / "reconcile.mp3"),
                original_filename="reconcile.mp3",
                status=CallStatus.PENDING,
                source="sheet_ingestion",
            )
            reconcile_record = RecordingIngestionRecord(
                id=980293,
                ingestion_run_id=run_reconcile.id,
                source_name=run_reconcile.source_name,
                source_key="audit-reconcile-source:record",
                source_row_number=2,
                source_payload={"CRDTS": "AUDIT-RECONCILE-1", "CALL LINK": sensitive_url},
                recording_url=sensitive_url,
                recording_url_fingerprint="audit-reconcile-fingerprint",
                employee_id=employee.id,
                campaign_id=campaign.id,
                status=RecordingIngestionRecordStatus.ACCEPTED,
                call_id=reconcile_call.id,
            )
            db.add_all(
                [
                    employee,
                    campaign,
                    run_reject,
                    run_accept,
                    run_reconcile,
                    reject_record,
                    accept_record,
                    reconcile_call,
                    reconcile_record,
                ]
            )
            db.commit()

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
                        duration_seconds=0.25,
                    )

            class RejectedScanner:
                def scan(self, path, timeout_seconds):
                    return recording_ingestion_service.MalwareScanResult(
                        status=recording_ingestion_service.RecordingIngestionInspectionStatus.REJECTED,
                        error_category="scanner_rejected",
                        error_detail=f"Blocked {sensitive_url} and {sensitive_path}",
                        scanner_name="clamd",
                        scanner_version="1.0",
                    )

            reject_record = db.get(RecordingIngestionRecord, 980291)
            accept_record = db.get(RecordingIngestionRecord, 980292)
            reconcile_record = db.get(RecordingIngestionRecord, 980293)
            run_reject = db.get(RecordingIngestionRun, 980291)
            run_accept = db.get(RecordingIngestionRun, 980292)

            assert reject_record is not None and accept_record is not None and reconcile_record is not None
            assert run_reject is not None and run_accept is not None

            recording_ingestion_service.inspect_quarantined_recording(
                db,
                reject_record,
                run_reject,
                layout=layout,
                scanner=RejectedScanner(),
                media_verifier=PassedVerifier(),
            )
            db.commit()

            recording_ingestion_service.inspect_quarantined_recording(
                db,
                accept_record,
                run_accept,
                layout=layout,
                scanner=PassedScanner(),
                media_verifier=PassedVerifier(),
            )
            db.commit()
            recording_ingestion_service.handoff_accepted_recording(
                db,
                accept_record,
                run=run_accept,
                queue_task=lambda call_id: None,
            )
            recording_ingestion_service.reconcile_committed_call_handoffs(
                db,
                queue_task=lambda call_id: None,
            )
            db.commit()
        finally:
            db.close()

        audit_response = client.get("/api/admin/audits?limit=50")
        assert audit_response.status_code == 200
        payload = audit_response.json()
        serialized = json.dumps(payload)

        actions = {item["action"] for item in payload}
        assert {
            recording_ingestion_service.INGESTION_AUDIT_MANUAL_START,
            recording_ingestion_service.INGESTION_AUDIT_RETRY,
            recording_ingestion_service.INGESTION_AUDIT_REJECTED,
            recording_ingestion_service.INGESTION_AUDIT_ACCEPTED,
            recording_ingestion_service.INGESTION_AUDIT_HANDOFF,
            recording_ingestion_service.INGESTION_AUDIT_RECONCILIATION,
        }.issubset(actions)

        assert sensitive_url not in serialized
        assert sensitive_path not in serialized
        assert str(reject_quarantine) not in serialized
        assert str(accept_quarantine) not in serialized
        assert "[redacted-url]" in serialized
        assert "[redacted-path]" in serialized

        latest_reject_audit = next(item for item in payload if item["action"] == recording_ingestion_service.INGESTION_AUDIT_REJECTED)
        assert latest_reject_audit["success"] is False
        assert "\"record_id\": 980291" in (latest_reject_audit["after_state"] or "")
        assert "\"run_id\": 980291" in (latest_reject_audit["after_state"] or "")
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_retry_endpoint_authorizes_and_returns_sanitized_record(monkeypatch):
    _seed_retry_record(
        record_id=98001,
        status=RecordingIngestionRecordStatus.FAILED,
        last_error_category="access_denied",
        last_error_detail="Source denied at https://dialer.example.com/token=secret and D:\\secure\\recording.mp3",
    )
    admin = _mock_user(employee_id=98011, role=UserRole.ADMIN)
    captured: dict[str, object] = {}

    def fake_queue(record_id: int, *, requested_by_employee_id: int | None = None, manual: bool = False, countdown_seconds=None):
        captured["record_id"] = record_id
        captured["requested_by_employee_id"] = requested_by_employee_id
        captured["manual"] = manual
        captured["countdown_seconds"] = countdown_seconds
        return None

    app.dependency_overrides[get_current_user] = lambda: admin
    monkeypatch.setattr("app.routers.recording_ingestion.queue_recording_retry", fake_queue)

    try:
        response = client.post(
            "/api/recording-ingestion/records/98001/retry",
            json={"reason": "try again"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 202
    payload = response.json()
    serialized = json.dumps(payload)

    assert payload["id"] == 98001
    assert payload["status"] == RecordingIngestionRecordStatus.FAILED.value
    assert payload["retry_requested_at"] is not None
    assert payload["error_category"] == "access_denied"
    assert "[redacted-url]" in (payload["error_detail"] or "")
    assert "[redacted-path]" in (payload["error_detail"] or "")
    assert "https://archive.dial-fusion.com/private.mp3" not in serialized
    assert "D:\\secure\\recording.mp3" not in serialized
    assert captured == {
        "record_id": 98001,
        "requested_by_employee_id": 98011,
        "manual": True,
        "countdown_seconds": None,
    }


def test_retry_endpoint_rejects_unauthorized_users():
    _seed_retry_record(record_id=98002, status=RecordingIngestionRecordStatus.FAILED)
    agent = _mock_user(employee_id=98012, role=UserRole.AGENT)
    app.dependency_overrides[get_current_user] = lambda: agent

    try:
        response = client.post("/api/recording-ingestion/records/98002/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 403


def test_retry_endpoint_returns_not_found_for_missing_record():
    admin = _mock_user(employee_id=98013, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.post("/api/recording-ingestion/records/999999/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404


def test_retry_endpoint_returns_safe_eligibility_error_for_submitted_record():
    _seed_retry_record(
        record_id=98003,
        status=RecordingIngestionRecordStatus.SUBMITTED,
        last_error_detail="Queue already submitted from https://sensitive.example.com/path",
    )
    admin = _mock_user(employee_id=98014, role=UserRole.ADMIN)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        response = client.post("/api/recording-ingestion/records/98003/retry")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 400
    assert "https://sensitive.example.com/path" not in response.text
