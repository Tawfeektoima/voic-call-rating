from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace
from pathlib import Path

import httpx
import pytest
from sqlalchemy.exc import IntegrityError

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
from app.services import recording_ingestion as recording_ingestion_service
from app.services.recording_ingestion import RecordingIngestionSecurityError


RECORDING_URL = "https://archive.dial-fusion.com/archive/20260504_15030300m45s_5209776179_NoCallerOnLine_Agent17.mp3"


def _source_row(**overrides: str) -> dict[str, str]:
    row = {
        "DATE": "2026-05-04",
        "CODE": "489",
        "CRDTS": "67191",
        "NAME": "Agent One",
        "CALL LINK": RECORDING_URL,
        "SCORE": "91",
        "WEAKNESS": "Follow up",
        "QUALITY FEEDBACK": "Clear and complete",
        "EXTRA FEEDBACK": "Leave voicemail next time",
    }
    row.update(overrides)
    return row


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
            evaluation_prompt="Test evaluation prompt long enough for ingestion tests.",
            status=status,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    finally:
        db.close()


def _seed_run(
    *,
    run_id: int,
    source_name: str = "vicdi_tests",
    status: RecordingIngestionRunStatus = RecordingIngestionRunStatus.REQUESTED,
) -> RecordingIngestionRun:
    db = SessionLocal()
    try:
        run = RecordingIngestionRun(
            id=run_id,
            source_name=source_name,
            trigger=RecordingIngestionRunTrigger.MANUAL,
            status=status,
            rows_seen=0,
            new_count=0,
            duplicate_count=0,
            success_count=0,
            failed_count=0,
            retryable_count=0,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    finally:
        db.close()


def _call_service(function_name: str, /, **kwargs):
    func = getattr(recording_ingestion_service, function_name)
    return func(**kwargs)


def _exception_text(exc: BaseException) -> str:
    detail = getattr(exc, "detail", None)
    return str(detail if detail is not None else exc)


def _value(result, field_name: str):
    if hasattr(result, field_name):
        return getattr(result, field_name)
    return result[field_name]


def _set_default_campaign(monkeypatch, campaign_id: int) -> None:
    monkeypatch.setattr(
        recording_ingestion_service,
        "get_settings",
        lambda: SimpleNamespace(CALL_INGEST_DEFAULT_CAMPAIGN_ID=campaign_id),
    )


def test_source_row_mapping_requires_confirmed_columns_and_keeps_sensitive_data_out_of_errors(capsys, monkeypatch):
    row = _source_row()
    del row["NAME"]
    row["QUALITY FEEDBACK"] = "token=abc123"
    _seed_employee(employee_id=92000, code="489", name="Agent One")
    campaign = _seed_campaign(campaign_id=93000)
    _set_default_campaign(monkeypatch, campaign.id)

    db = SessionLocal()
    try:
        with pytest.raises((RecordingIngestionSecurityError, ValueError)) as exc_info:
            _call_service(
                "map_source_row",
                db=db,
                row=row,
                row_number=2,
                source_name="vicdi_tests",
            )
    finally:
        db.close()

    message = _exception_text(exc_info.value)
    captured = capsys.readouterr()

    assert "NAME" in message
    assert RECORDING_URL not in message
    assert "token=abc123" not in message
    assert RECORDING_URL not in captured.out
    assert "token=abc123" not in captured.out
    assert RECORDING_URL not in captured.err
    assert "token=abc123" not in captured.err


def test_source_row_mapping_preserves_source_payload_and_prefers_crdts_for_the_source_key(monkeypatch):
    employee = _seed_employee(employee_id=92001, code="489", name="Agent One")
    campaign = _seed_campaign(campaign_id=93001)
    _set_default_campaign(monkeypatch, campaign.id)
    row = _source_row(
        NAME="Agent One",
        CODE=employee.employee_code,
        CRDTS="67191",
        SCORE="91",
        WEAKNESS="Follow up",
        **{"QUALITY FEEDBACK": "Clear and complete", "EXTRA FEEDBACK": "Leave voicemail next time"},
    )
    db = SessionLocal()
    try:
        result = _call_service(
            "map_source_row",
            db=db,
            row=row,
            row_number=2,
            source_name="vicdi_tests",
        )
    finally:
        db.close()

    assert "67191" in str(_value(result, "source_key"))
    assert "Agent One" not in str(_value(result, "source_key"))
    payload = _value(result, "source_payload")
    assert payload["DATE"] == "2026-05-04"
    assert payload["CODE"] == "489"
    assert payload["CRDTS"] == "67191"
    assert payload["NAME"] == "Agent One"
    assert payload["CALL LINK"] == RECORDING_URL
    assert payload["SCORE"] == "91"
    assert payload["WEAKNESS"] == "Follow up"
    assert payload["QUALITY FEEDBACK"] == "Clear and complete"
    assert payload["EXTRA FEEDBACK"] == "Leave voicemail next time"
    assert _value(result, "source_row_number") == 2
    assert _value(result, "employee_id") == employee.id
    assert _value(result, "campaign_id") == campaign.id


def test_source_row_mapping_uses_fallback_identity_when_crdts_is_blank(monkeypatch):
    employee = _seed_employee(employee_id=92002, code="490", name="Agent Two")
    campaign = _seed_campaign(campaign_id=93002)
    _set_default_campaign(monkeypatch, campaign.id)
    row = _source_row(
        CRDTS="",
        CODE=employee.employee_code,
        NAME="Agent Two",
        **{"QUALITY FEEDBACK": "Call back later"},
    )
    db = SessionLocal()
    try:
        result = _call_service(
            "map_source_row",
            db=db,
            row=row,
            row_number=3,
            source_name="vicdi_tests",
        )
    finally:
        db.close()

    source_key = str(_value(result, "source_key"))
    assert "67191" not in source_key
    assert "2026-05-04" in source_key
    assert "490" in source_key
    assert "Agent Two" in source_key
    assert RECORDING_URL in source_key


def test_agent_resolution_prefers_employee_code_then_unique_normalized_name_and_rejects_ambiguity(monkeypatch):
    code_employee = _seed_employee(employee_id=92003, code="491", name="Code Match Agent")
    unique_name_employee = _seed_employee(employee_id=92004, code="492", name="Unique Name Agent")
    ambiguous_first = _seed_employee(employee_id=92005, code="493", name="Jordan Smith")
    _seed_employee(employee_id=92006, code="494", name="JORDAN   SMITH")
    campaign = _seed_campaign(campaign_id=93003)
    _set_default_campaign(monkeypatch, campaign.id)

    db = SessionLocal()
    try:
        code_first_result = _call_service(
            "resolve_source_employee",
            db=db,
            row=_source_row(CODE=code_employee.employee_code, NAME="Different Name"),
        )
        unique_name_result = _call_service(
            "resolve_source_employee",
            db=db,
            row=_source_row(CODE="", NAME=" unique name agent "),
        )
        with pytest.raises((RecordingIngestionSecurityError, ValueError)) as exc_info:
            _call_service(
                "resolve_source_employee",
                db=db,
                row=_source_row(CODE="", NAME="Jordan Smith"),
            )
    finally:
        db.close()

    assert _value(code_first_result, "employee_id") == code_employee.id
    assert _value(unique_name_result, "employee_id") == unique_name_employee.id
    assert _value(code_first_result, "employee_id") != ambiguous_first.id
    assert "ambiguous" in _exception_text(exc_info.value).lower()


def test_active_campaign_preflight_rejects_missing_and_inactive_campaigns(monkeypatch):
    active_campaign = _seed_campaign(campaign_id=93010, status=CampaignStatus.ACTIVE)
    _seed_campaign(campaign_id=93011, status=CampaignStatus.PAUSED)
    db = SessionLocal()
    try:
        monkeypatch.setattr(
            recording_ingestion_service,
            "get_settings",
            lambda: SimpleNamespace(CALL_INGEST_DEFAULT_CAMPAIGN_ID=active_campaign.id),
        )
        active_result = _call_service("preflight_active_campaign", db=db)

        monkeypatch.setattr(
            recording_ingestion_service,
            "get_settings",
            lambda: SimpleNamespace(CALL_INGEST_DEFAULT_CAMPAIGN_ID=999999),
        )
        with pytest.raises((RecordingIngestionSecurityError, ValueError)) as missing_exc_info:
            _call_service("preflight_active_campaign", db=db)

        monkeypatch.setattr(
            recording_ingestion_service,
            "get_settings",
            lambda: SimpleNamespace(CALL_INGEST_DEFAULT_CAMPAIGN_ID=93011),
        )
        with pytest.raises((RecordingIngestionSecurityError, ValueError)) as inactive_exc_info:
            _call_service("preflight_active_campaign", db=db)
    finally:
        db.close()

    assert _value(active_result, "id") == active_campaign.id
    assert _value(active_result, "status") == CampaignStatus.ACTIVE
    assert "campaign" in _exception_text(missing_exc_info.value).lower()
    assert "active" in _exception_text(inactive_exc_info.value).lower()


def test_source_row_mapping_rejects_inactive_campaign_even_when_provided(monkeypatch):
    _seed_employee(employee_id=92007, code="495", name="Inactive Campaign Agent")
    inactive_campaign = _seed_campaign(campaign_id=93012, status=CampaignStatus.PAUSED)
    row = _source_row(CODE="495", NAME="Inactive Campaign Agent")

    db = SessionLocal()
    try:
        with pytest.raises((RecordingIngestionSecurityError, ValueError)) as exc_info:
            _call_service(
                "map_source_row",
                db=db,
                row=row,
                row_number=4,
                source_name="vicdi_tests",
                campaign=inactive_campaign,
            )
    finally:
        db.close()

    message = _exception_text(exc_info.value).lower()
    assert "active" in message
    assert "93012" in message


def test_claim_source_record_creates_one_downloading_record_and_reuses_it(monkeypatch):
    employee = _seed_employee(employee_id=92008, code="496", name="Claim Agent")
    campaign = _seed_campaign(campaign_id=93013)
    _set_default_campaign(monkeypatch, campaign.id)
    run = _seed_run(run_id=94001)
    row = _source_row(CODE=employee.employee_code, NAME="Claim Agent", CRDTS="77191")

    db = SessionLocal()
    try:
        mapping = _call_service(
            "map_source_row",
            db=db,
            row=row,
            row_number=2,
            source_name="vicdi_tests",
        )
        first_claim = _call_service("claim_source_record", db=db, run=run, mapping=mapping)
        second_claim = _call_service("claim_source_record", db=db, run=run, mapping=mapping)
        db.commit()
        record_count = db.query(RecordingIngestionRecord).filter(
            RecordingIngestionRecord.source_name == "vicdi_tests",
            RecordingIngestionRecord.source_key == _value(mapping, "source_key"),
        ).count()
    finally:
        db.close()

    assert _value(first_claim, "created") is True
    assert _value(first_claim, "disposition") == RecordingIngestionRecordStatus.DOWNLOADING
    assert _value(second_claim, "created") is False
    assert _value(second_claim, "disposition") == RecordingIngestionRecordStatus.DOWNLOADING
    assert record_count == 1


def test_claim_source_record_marks_submitted_same_fingerprint_as_duplicate(monkeypatch):
    employee = _seed_employee(employee_id=92009, code="497", name="Duplicate Agent")
    campaign = _seed_campaign(campaign_id=93014)
    _set_default_campaign(monkeypatch, campaign.id)
    run = _seed_run(run_id=94002)
    row = _source_row(CODE=employee.employee_code, NAME="Duplicate Agent", CRDTS="77192")

    db = SessionLocal()
    try:
        mapping = _call_service(
            "map_source_row",
            db=db,
            row=row,
            row_number=2,
            source_name="vicdi_tests",
        )
        existing = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name="vicdi_tests",
            source_key=_value(mapping, "source_key"),
            source_row_number=2,
            source_payload=_value(mapping, "source_payload"),
            recording_url=_value(mapping, "recording_url"),
            recording_url_fingerprint=_value(mapping, "recording_url_fingerprint"),
            source_call_date=_value(mapping, "source_call_date"),
            source_score=_value(mapping, "source_score"),
            source_quality_notes=_value(mapping, "source_quality_notes"),
            employee_id=_value(mapping, "employee_id"),
            campaign_id=_value(mapping, "campaign_id"),
            status=RecordingIngestionRecordStatus.SUBMITTED,
            attempt_count=1,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

        claim = _call_service("claim_source_record", db=db, run=run, mapping=mapping)
        db.commit()
        db.refresh(existing)
    finally:
        db.close()

    assert _value(claim, "created") is False
    assert _value(claim, "disposition") == RecordingIngestionRecordStatus.DUPLICATE
    assert existing.status == RecordingIngestionRecordStatus.SUBMITTED
    assert existing.last_error_category is None
    assert existing.completed_at is None


def test_claim_source_record_marks_changed_submitted_link_requires_review(monkeypatch):
    employee = _seed_employee(employee_id=92010, code="498", name="Review Agent")
    campaign = _seed_campaign(campaign_id=93015)
    _set_default_campaign(monkeypatch, campaign.id)
    run = _seed_run(run_id=94003)
    row = _source_row(CODE=employee.employee_code, NAME="Review Agent", CRDTS="77193")

    db = SessionLocal()
    try:
        mapping = _call_service(
            "map_source_row",
            db=db,
            row=row,
            row_number=2,
            source_name="vicdi_tests",
        )
        changed_mapping = _call_service(
            "map_source_row",
            db=db,
            row=_source_row(
                CODE=employee.employee_code,
                NAME="Review Agent",
                CRDTS="77193",
                **{"CALL LINK": RECORDING_URL.replace(".mp3", "-replacement.mp3")},
            ),
            row_number=2,
            source_name="vicdi_tests",
        )
        existing = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name="vicdi_tests",
            source_key=_value(mapping, "source_key"),
            source_row_number=2,
            source_payload=_value(mapping, "source_payload"),
            recording_url=_value(mapping, "recording_url"),
            recording_url_fingerprint=_value(mapping, "recording_url_fingerprint"),
            source_call_date=_value(mapping, "source_call_date"),
            source_score=_value(mapping, "source_score"),
            source_quality_notes=_value(mapping, "source_quality_notes"),
            employee_id=_value(mapping, "employee_id"),
            campaign_id=_value(mapping, "campaign_id"),
            status=RecordingIngestionRecordStatus.SUBMITTED,
            attempt_count=1,
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

        claim = _call_service("claim_source_record", db=db, run=run, mapping=changed_mapping)
        db.commit()
        db.refresh(existing)
    finally:
        db.close()

    assert _value(claim, "created") is False
    assert _value(claim, "disposition") == RecordingIngestionRecordStatus.REQUIRES_REVIEW
    assert existing.status == RecordingIngestionRecordStatus.SUBMITTED
    assert existing.last_error_category is None
    assert existing.completed_at is None


def test_duplicate_claim_does_not_hide_a_later_changed_link(monkeypatch):
    employee = _seed_employee(employee_id=92015, code="503", name="Repeat Agent")
    campaign = _seed_campaign(campaign_id=93018)
    _set_default_campaign(monkeypatch, campaign.id)
    historic_run = _seed_run(run_id=94004, source_name="historic_repeat", status=RecordingIngestionRunStatus.COMPLETED)
    review_run = _seed_run(run_id=94005)
    row = _source_row(CODE=employee.employee_code, NAME=employee.name, CRDTS="77194")

    db = SessionLocal()
    try:
        mapping = _call_service("map_source_row", db=db, row=row, row_number=2, source_name="vicdi_tests")
        existing = RecordingIngestionRecord(
            ingestion_run_id=historic_run.id,
            source_name="vicdi_tests",
            source_key=_value(mapping, "source_key"),
            source_row_number=2,
            source_payload=_value(mapping, "source_payload"),
            recording_url=_value(mapping, "recording_url"),
            recording_url_fingerprint=_value(mapping, "recording_url_fingerprint"),
            source_call_date=_value(mapping, "source_call_date"),
            source_score=_value(mapping, "source_score"),
            source_quality_notes=_value(mapping, "source_quality_notes"),
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.SUBMITTED,
            attempt_count=1,
        )
        db.add(existing)
        db.commit()

        duplicate = _call_service("claim_source_record", db=db, run=review_run, mapping=mapping)
        changed_mapping = _call_service(
            "map_source_row",
            db=db,
            row=_source_row(
                CODE=employee.employee_code,
                NAME=employee.name,
                CRDTS="77194",
                **{"CALL LINK": RECORDING_URL.replace(".mp3", "-replacement.mp3")},
            ),
            row_number=2,
            source_name="vicdi_tests",
        )
        changed = _call_service("claim_source_record", db=db, run=review_run, mapping=changed_mapping)
        db.commit()
        db.refresh(existing)
    finally:
        db.close()

    assert _value(duplicate, "disposition") == RecordingIngestionRecordStatus.DUPLICATE
    assert _value(changed, "disposition") == RecordingIngestionRecordStatus.REQUIRES_REVIEW
    assert existing.status == RecordingIngestionRecordStatus.SUBMITTED
    assert existing.attempt_count == 3


def test_run_closes_when_google_client_creation_fails(monkeypatch, tmp_path):
    settings_for_run = SimpleNamespace(
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_DOWNLOAD_CONCURRENCY=1,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    monkeypatch.setattr(
        recording_ingestion_service,
        "_build_google_sheets_service",
        lambda: (_ for _ in ()).throw(RecordingIngestionSecurityError("missing_sheet_credentials", "Credentials unavailable.")),
    )

    db = SessionLocal()
    try:
        run = _call_service(
            "run_recording_ingestion",
            db=db,
            source_name="google-client-failure",
            layout=recording_ingestion_service.ensure_storage_layout(
                recording_ingestion_service.build_storage_layout(
                    quarantine_dir=tmp_path / "quarantine",
                    accepted_dir=tmp_path / "accepted",
                    rejected_dir=tmp_path / "rejected",
                )
            ),
        )
        db.refresh(run)
    finally:
        db.close()

    assert run.status == RecordingIngestionRunStatus.FAILED
    assert run.completed_at is not None
    assert "Credentials unavailable" in (run.failure_summary or "")


def test_downloader_queues_inspection_after_committing_quarantine(monkeypatch, recording_ingestion_fixture_paths, tmp_path):
    employee = _seed_employee(employee_id=92016, code="504", name="Queue Inspector")
    campaign = _seed_campaign(campaign_id=93019)
    run = _seed_run(run_id=94006, source_name="queue-inspection")
    settings_for_run = SimpleNamespace(
        CALL_INGEST_DEFAULT_CAMPAIGN_ID=campaign.id,
        CALL_INGEST_RUNTIME_ROLE="downloader",
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    row_values = _source_row(CODE=employee.employee_code, NAME=employee.name, CRDTS="77195")
    row = recording_ingestion_service._map_sheet_row(list(row_values), list(row_values.values()), row_number=2)
    assert not isinstance(row, recording_ingestion_service.SourceSheetValidationError)
    layout = recording_ingestion_service.ensure_storage_layout(
        recording_ingestion_service.build_storage_layout(
            quarantine_dir=tmp_path / "quarantine",
            accepted_dir=tmp_path / "accepted",
            rejected_dir=tmp_path / "rejected",
        )
    )
    audio_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()
    queued_record_ids: list[int] = []

    def client_factory():
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=audio_bytes, headers={"content-type": "audio/mpeg"})
            )
        )

    outcome = recording_ingestion_service._process_ingestion_row(
        run_id=run.id,
        source_name="queue-inspection",
        row=row,
        session_factory=SessionLocal,
        client_factory=client_factory,
        layout=layout,
        allowed_hosts={"archive.dial-fusion.com"},
        max_bytes=settings_for_run.max_file_size_bytes,
        scanner_factory=lambda: (_ for _ in ()).throw(AssertionError("downloader must not scan")),
        media_verifier_factory=lambda: (_ for _ in ()).throw(AssertionError("downloader must not verify")),
        inspection_queue=queued_record_ids.append,
    )

    db = SessionLocal()
    try:
        record = db.get(RecordingIngestionRecord, outcome.record_id)
    finally:
        db.close()

    assert outcome.outcome == RecordingIngestionRecordStatus.QUARANTINED.value
    assert queued_record_ids == [outcome.record_id]
    assert record is not None
    assert record.status == RecordingIngestionRecordStatus.QUARANTINED
    assert record.quarantine_file_path is not None
    assert Path(record.quarantine_file_path).is_file()


def test_run_recording_ingestion_processes_rows_and_closes_with_errors(monkeypatch, recording_ingestion_fixture_paths, tmp_path):
    campaign = _seed_campaign(campaign_id=93016)
    _set_default_campaign(monkeypatch, campaign.id)
    valid_employee = _seed_employee(employee_id=92011, code="499", name="Valid Agent")
    duplicate_employee = _seed_employee(employee_id=92012, code="500", name="Duplicate Agent")
    inaccessible_employee = _seed_employee(employee_id=92013, code="501", name="Broken Agent")
    _seed_employee(employee_id=92014, code="502", name="Review Agent")
    batch_source_name = "vicdi_tests_batch"

    duplicate_url = "https://archive.dial-fusion.com/duplicate.mp3"
    inaccessible_url = "https://archive.dial-fusion.com/missing.mp3"
    duplicate_row = {
        "DATE": "2026-05-04",
        "CODE": duplicate_employee.employee_code,
        "CRDTS": "77190",
        "NAME": "Duplicate Agent",
        "CALL LINK": duplicate_url,
        "SCORE": "95",
        "WEAKNESS": "None",
        "QUALITY FEEDBACK": "Already processed",
    }
    valid_row = {
        "DATE": "2026-05-04",
        "CODE": valid_employee.employee_code,
        "CRDTS": "77191",
        "NAME": "Valid Agent",
        "CALL LINK": RECORDING_URL,
        "SCORE": "91",
        "WEAKNESS": "Follow up",
        "QUALITY FEEDBACK": "Clear and complete",
    }
    invalid_row = {
        "DATE": "2026-05-04",
        "CODE": "999",
        "CRDTS": "77192",
        "NAME": "Unknown Agent",
        "CALL LINK": "https://archive.dial-fusion.com/unknown.mp3",
        "SCORE": "88",
        "WEAKNESS": "Missing mapping",
        "QUALITY FEEDBACK": "Needs review",
    }
    inaccessible_row = {
        "DATE": "2026-05-04",
        "CODE": inaccessible_employee.employee_code,
        "CRDTS": "77193",
        "NAME": "Broken Agent",
        "CALL LINK": inaccessible_url,
        "SCORE": "83",
        "WEAKNESS": "Transport failure",
        "QUALITY FEEDBACK": "Needs retry",
    }

    db = SessionLocal()
    try:
        duplicate_mapping = _call_service(
            "map_source_row",
            db=db,
            row=duplicate_row,
            row_number=3,
            source_name=batch_source_name,
        )
        existing = RecordingIngestionRecord(
            ingestion_run_id=_seed_run(run_id=94010, source_name="historic_ingestion", status=RecordingIngestionRunStatus.COMPLETED).id,
            source_name=batch_source_name,
            source_key=_value(duplicate_mapping, "source_key"),
            source_row_number=3,
            source_payload=_value(duplicate_mapping, "source_payload"),
            recording_url=_value(duplicate_mapping, "recording_url"),
            recording_url_fingerprint=_value(duplicate_mapping, "recording_url_fingerprint"),
            source_call_date=_value(duplicate_mapping, "source_call_date"),
            source_score=_value(duplicate_mapping, "source_score"),
            source_quality_notes=_value(duplicate_mapping, "source_quality_notes"),
            employee_id=_value(duplicate_mapping, "employee_id"),
            campaign_id=_value(duplicate_mapping, "campaign_id"),
            status=RecordingIngestionRecordStatus.SUBMITTED,
            attempt_count=1,
        )
        db.add(existing)
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
    queued_call_ids: list[int] = []

    settings_for_run = SimpleNamespace(
        CALL_INGEST_DEFAULT_CAMPAIGN_ID=campaign.id,
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_GOOGLE_SHEET_ID="sheet-id",
        CALL_INGEST_WORKSHEET="Calls",
        CALL_INGEST_RANGE="A:ZZ",
        CALL_INGEST_DOWNLOAD_CONCURRENCY=2,
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    monkeypatch.setattr(
        recording_ingestion_service,
        "_build_google_sheets_service",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected live Google Sheets access")),
        raising=False,
    )

    def fake_queue_call_audio_processing(call_id: int) -> None:
        queued_call_ids.append(call_id)

    monkeypatch.setattr("app.worker.queue_call_audio_processing", fake_queue_call_audio_processing)

    def client_factory():
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == RECORDING_URL:
                return httpx.Response(200, content=fixture_bytes, headers={"content-type": "audio/mpeg"})
            if url == duplicate_url:
                return httpx.Response(200, content=fixture_bytes, headers={"content-type": "audio/mpeg"})
            if url == inaccessible_url:
                return httpx.Response(404, text="missing")
            raise AssertionError(f"Unexpected URL: {url}")

        return httpx.Client(transport=httpx.MockTransport(handler))

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

    db = SessionLocal()
    try:
        run = _call_service(
            "run_recording_ingestion",
            db=db,
            source_name=batch_source_name,
            trigger=recording_ingestion_service.RecordingIngestionRunTrigger.MANUAL,
            sheet_service=fake_service,
            session_factory=SessionLocal,
            client_factory=client_factory,
            scanner_factory=PassedScanner,
            media_verifier_factory=PassedVerifier,
                layout=recording_ingestion_service.ensure_storage_layout(
                    recording_ingestion_service.build_storage_layout(
                        quarantine_dir=tmp_path / "quarantine",
                        accepted_dir=tmp_path / "accepted",
                        rejected_dir=tmp_path / "rejected",
                    )
                ),
                max_workers=1,
            )
        db.refresh(run)
    finally:
        db.close()

    assert run.status == RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS
    assert run.rows_seen == 4
    assert run.new_count == 2
    assert run.duplicate_count == 1
    assert run.success_count == 1
    assert run.failed_count == 2
    assert run.retryable_count == 0
    assert run.started_at is not None
    assert run.completed_at is not None
    assert "https://archive.dial-fusion.com" not in (run.failure_summary or "")
    assert queued_call_ids and len(queued_call_ids) == 1

    verify_db = SessionLocal()
    try:
        calls = verify_db.query(Call).all()
        accepted_records = verify_db.query(RecordingIngestionRecord).filter(
            RecordingIngestionRecord.call_id.isnot(None)
        ).all()
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
    finally:
        verify_db.close()

def test_create_ingestion_run_rejects_active_run(monkeypatch):
    campaign = _seed_campaign(campaign_id=93017)
    _set_default_campaign(monkeypatch, campaign.id)
    _seed_run(run_id=94020)

    db = SessionLocal()
    try:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            _call_service(
                "create_ingestion_run",
                db=db,
                source_name="vicdi_tests",
                trigger=recording_ingestion_service.RecordingIngestionRunTrigger.MANUAL,
            )
    finally:
        db.close()

    assert "active" in _exception_text(exc_info.value).lower()


def test_create_ingestion_run_normalizes_integrity_conflict_into_active_run(monkeypatch):
    _seed_run(run_id=940201, source_name="vicdi-race-source", status=RecordingIngestionRunStatus.PROCESSING)

    db = SessionLocal()
    active_lookup_count = {"count": 0}
    original_find_active = recording_ingestion_service.find_active_ingestion_run

    def fake_find_active(session, *, source_name):
        active_lookup_count["count"] += 1
        if active_lookup_count["count"] == 1 and source_name == "vicdi-race-source":
            return None
        return original_find_active(session, source_name=source_name)

    def fake_flush():
        raise IntegrityError("insert into recording_ingestion_runs", {}, Exception("duplicate active run"))

    monkeypatch.setattr(recording_ingestion_service, "find_active_ingestion_run", fake_find_active)
    monkeypatch.setattr(db, "flush", fake_flush)

    try:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            recording_ingestion_service.create_ingestion_run(
                db,
                source_name="vicdi-race-source",
                trigger=RecordingIngestionRunTrigger.MANUAL,
            )
    finally:
        db.close()

    assert exc_info.value.category == "active_run_exists"


def test_read_source_sheet_rows_normalizes_headers_row_numbers_and_reports_row_errors(monkeypatch):
    captured_request: dict[str, object] = {}

    class FakeValues:
        def get(self, **kwargs):
            captured_request.update(kwargs)
            return self

        def execute(self):
            return {
                "range": "'Calls'!A1:H3",
                "values": [
                    [" DATE ", "CODE", "CRDTS", "NAME", "CALL LINK", "SCORE", "WEAKNESS", "QUALITY FEEDBACK"],
                    ["2026-05-04", "489", "67191", "Agent One", RECORDING_URL, "91", "Follow up", "Clear"],
                    ["2026-05-05", "490", "67192", "Agent Two", "", "88", "Missing call link", "Needs follow-up"],
                ],
            }

    fake_service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: FakeValues()))
    _set_default_campaign(monkeypatch, 93020)

    result = _call_service(
        "read_source_sheet_rows",
        service=fake_service,
        spreadsheet_id="sheet-id",
        worksheet_name="Calls",
        cell_range="A:ZZ",
    )

    assert captured_request["spreadsheetId"] == "sheet-id"
    assert captured_request["range"] == "'Calls'!A:ZZ"
    assert captured_request["majorDimension"] == "ROWS"
    assert result.headers[:5] == ("DATE", "CODE", "CRDTS", "NAME", "CALL LINK")
    assert [row.row_number for row in result.rows] == [2]
    assert result.rows[0].normalized_values["CALL LINK"] == RECORDING_URL
    assert [error.row_number for error in result.errors] == [3]
    assert "CALL LINK" in result.errors[0].detail
    assert RECORDING_URL not in result.errors[0].detail


def test_read_source_sheet_rows_rejects_missing_required_headers(monkeypatch):
    class FakeValues:
        def get(self, **kwargs):
            return self

        def execute(self):
            return {
                "range": "'Calls'!A1:G2",
                "values": [
                    ["DATE", "CODE", "CRDTS", "CALL LINK", "SCORE", "WEAKNESS", "QUALITY FEEDBACK"],
                    ["2026-05-04", "489", "67191", RECORDING_URL, "91", "Follow up", "Clear"],
                ],
            }

    fake_service = SimpleNamespace(spreadsheets=lambda: SimpleNamespace(values=lambda: FakeValues()))
    _set_default_campaign(monkeypatch, 93021)

    with pytest.raises(RecordingIngestionSecurityError) as exc_info:
        _call_service(
            "read_source_sheet_rows",
            service=fake_service,
            spreadsheet_id="sheet-id",
            worksheet_name="Calls",
            cell_range="A:ZZ",
        )

    message = _exception_text(exc_info.value)
    assert "NAME" in message
    assert RECORDING_URL not in message


def test_handoff_accepted_recording_creates_call_after_commit_and_queues_same_call_id(tmp_path):
    campaign = _seed_campaign(campaign_id=93022)
    employee = _seed_employee(employee_id=93022, code="93022", name="Accepted Agent")
    run = _seed_run(run_id=94022)
    accepted_path = tmp_path / "accepted-call.mp3"
    accepted_path.write_bytes(b"accepted-audio")

    db = SessionLocal()
    queued_call_ids: list[int] = []
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name="vicdi_tests",
            source_key="call-93022",
            source_row_number=2,
            source_payload=_source_row(),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="fingerprint-93022",
            source_call_date=None,
            source_score=91.0,
            source_quality_notes="Clear and complete",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.ACCEPTED,
            stored_file_path=str(accepted_path),
            signature_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
            malware_scan_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
            media_verification_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        def queue_task(call_id: int) -> None:
            queued_call_ids.append(call_id)
            verify_db = SessionLocal()
            try:
                queued_record = verify_db.get(RecordingIngestionRecord, record.id)
                queued_call = verify_db.get(Call, call_id)
                assert queued_record is not None
                assert queued_record.call_id == call_id
                assert queued_record.status == RecordingIngestionRecordStatus.HANDOFF_PENDING
                assert queued_record.pipeline_queued_at is None
                assert queued_call is not None
                assert queued_call.status == CallStatus.PENDING
                assert queued_call.audio_file_path == str(accepted_path)
                assert queued_call.original_filename == accepted_path.name
            finally:
                verify_db.close()

        call = recording_ingestion_service.handoff_accepted_recording(
            db,
            db.get(RecordingIngestionRecord, record.id),
            queue_task=queue_task,
        )
        db.commit()
        db.refresh(call)
        db.refresh(record)
    finally:
        db.close()

    assert queued_call_ids == [call.id]
    assert call.status == CallStatus.PENDING
    assert call.audio_file_path == str(accepted_path)
    assert call.original_filename == accepted_path.name

    verify_db = SessionLocal()
    try:
        final_record = verify_db.get(RecordingIngestionRecord, record.id)
        final_call = verify_db.get(Call, call.id)
        assert final_record is not None
        assert final_record.status == RecordingIngestionRecordStatus.SUBMITTED
        assert final_record.pipeline_queued_at is not None
        assert final_record.call_id == call.id
        assert final_call is not None
        assert final_call.status == CallStatus.PENDING
        assert final_call.audio_file_path == str(accepted_path)
        assert final_call.original_filename == accepted_path.name
    finally:
        verify_db.close()


@pytest.mark.parametrize(
    ("category", "expected_status", "expected_delay_minutes"),
    [
        ("download_timeout", RecordingIngestionRecordStatus.RETRY_SCHEDULED, 1),
        ("rate_limited", RecordingIngestionRecordStatus.RETRY_SCHEDULED, 1),
        ("storage_failed", RecordingIngestionRecordStatus.RETRY_SCHEDULED, 1),
        ("handoff_queue_failed", RecordingIngestionRecordStatus.RETRY_SCHEDULED, 1),
        ("missing_required_row_fields", RecordingIngestionRecordStatus.FAILED, None),
        ("missing_employee_mapping", RecordingIngestionRecordStatus.FAILED, None),
        ("inactive_campaign", RecordingIngestionRecordStatus.FAILED, None),
        ("access_denied", RecordingIngestionRecordStatus.FAILED, None),
    ],
)
def test_apply_failure_policy_classifies_retryable_and_terminal_categories(
    category,
    expected_status,
    expected_delay_minutes,
):
    run = _seed_run(run_id=94023, source_name=f"failure-policy-{category}")
    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key=f"{run.source_name}:record",
            source_row_number=2,
            source_payload=_source_row(),
            recording_url=RECORDING_URL,
            recording_url_fingerprint=f"fingerprint-{category}",
            status=RecordingIngestionRecordStatus.DOWNLOADING,
            attempt_count=1,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        delay_seconds = recording_ingestion_service._apply_failure_policy(
            record,
            category=category,
            detail="Simulated failure.",
        )
    finally:
        db.close()

    assert record.status == expected_status
    if expected_delay_minutes is None:
        assert delay_seconds is None
        assert record.next_retry_at is None
    else:
        assert delay_seconds == expected_delay_minutes * 60
        assert record.next_retry_at is not None
        remaining = (record.next_retry_at - recording_ingestion_service.utcnow()).total_seconds()
        assert 0 < remaining <= delay_seconds


def test_apply_failure_policy_uses_one_five_fifteen_backoff_and_then_stops():
    run = _seed_run(run_id=94024, source_name="retry-backoff-sequence")
    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="retry-backoff-sequence:record",
            source_row_number=2,
            source_payload=_source_row(),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="retry-sequence",
            status=RecordingIngestionRecordStatus.DOWNLOADING,
            attempt_count=1,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        first_delay = recording_ingestion_service._apply_failure_policy(
            record,
            category="download_timeout",
            detail="Timeout 1.",
        )
        record.attempt_count = 2
        second_delay = recording_ingestion_service._apply_failure_policy(
            record,
            category="download_timeout",
            detail="Timeout 2.",
        )
        record.attempt_count = 3
        third_delay = recording_ingestion_service._apply_failure_policy(
            record,
            category="download_timeout",
            detail="Timeout 3.",
        )
        record.attempt_count = 4
        exhausted_delay = recording_ingestion_service._apply_failure_policy(
            record,
            category="download_timeout",
            detail="Timeout 4.",
        )
    finally:
        db.close()

    assert first_delay == 60
    assert second_delay == 5 * 60
    assert third_delay == 15 * 60
    assert exhausted_delay is None
    assert record.status == RecordingIngestionRecordStatus.FAILED
    assert record.next_retry_at is None


def test_scanner_and_media_rejections_stay_terminal_without_retry(monkeypatch, recording_ingestion_fixture_paths, tmp_path):
    run = _seed_run(run_id=94025, source_name="inspection-terminal")
    settings_for_run = SimpleNamespace(
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    layout = recording_ingestion_service.ensure_storage_layout(
        recording_ingestion_service.build_storage_layout(
            quarantine_dir=tmp_path / "quarantine",
            accepted_dir=tmp_path / "accepted",
            rejected_dir=tmp_path / "rejected",
        )
    )
    quarantine_path = layout.quarantine_dir / "scanner-case.mp3"
    quarantine_path.write_bytes(recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes())

    scanner_record_id = None
    media_record_id = None
    db = SessionLocal()
    try:
        scanner_record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="inspection-terminal:scanner",
            source_row_number=2,
            source_payload=_source_row(),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="scanner-terminal",
            status=RecordingIngestionRecordStatus.QUARANTINED,
            attempt_count=1,
            quarantine_file_path=str(quarantine_path),
        )
        db.add(scanner_record)
        db.commit()
        db.refresh(scanner_record)
        scanner_record_id = scanner_record.id

        class ScannerUnavailable:
            def scan(self, path, timeout_seconds):
                return recording_ingestion_service.MalwareScanResult(
                    status=recording_ingestion_service.RecordingIngestionInspectionStatus.UNAVAILABLE,
                    scanner_name="clamd",
                    scanner_version="1.0",
                    error_category="scanner_timeout",
                    error_detail="Scanner timed out.",
                )

        class PassedVerifier:
            def verify(self, path, timeout_seconds):
                return recording_ingestion_service.MediaVerificationResult(
                    status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                    duration_seconds=0.1,
                )

        recording_ingestion_service.inspect_quarantined_recording(
            db,
            scanner_record,
            db.get(RecordingIngestionRun, run.id),
            layout=layout,
            scanner=ScannerUnavailable(),
            media_verifier=PassedVerifier(),
        )
        db.commit()
        db.refresh(scanner_record)

        second_quarantine = layout.quarantine_dir / "media-case.mp3"
        second_quarantine.write_bytes(recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes())
        media_record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="inspection-terminal:media",
            source_row_number=3,
            source_payload=_source_row(CRDTS="media-terminal"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="media-terminal",
            status=RecordingIngestionRecordStatus.QUARANTINED,
            attempt_count=1,
            quarantine_file_path=str(second_quarantine),
        )
        db.add(media_record)
        db.commit()
        db.refresh(media_record)
        media_record_id = media_record.id

        class PassedScanner:
            def scan(self, path, timeout_seconds):
                return recording_ingestion_service.MalwareScanResult(
                    status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
                    scanner_name="clamd",
                    scanner_version="1.0",
                )

        class FailedVerifier:
            def verify(self, path, timeout_seconds):
                return recording_ingestion_service.MediaVerificationResult(
                    status=recording_ingestion_service.RecordingIngestionInspectionStatus.REJECTED,
                    error_category="media_verification_failed",
                    error_detail="Verifier rejected the recording.",
                )

        recording_ingestion_service.inspect_quarantined_recording(
            db,
            media_record,
            db.get(RecordingIngestionRun, run.id),
            layout=layout,
            scanner=PassedScanner(),
            media_verifier=FailedVerifier(),
        )
        db.commit()
        db.refresh(media_record)
    finally:
        db.close()

    verify_db = SessionLocal()
    try:
        scanner_record = verify_db.get(RecordingIngestionRecord, scanner_record_id)
        media_record = verify_db.get(RecordingIngestionRecord, media_record_id)
        assert scanner_record is not None
        assert media_record is not None
        assert scanner_record.status == RecordingIngestionRecordStatus.REJECTED
        assert scanner_record.last_error_category == "scanner_timeout"
        assert scanner_record.next_retry_at is None
        assert media_record.status == RecordingIngestionRecordStatus.REJECTED
        assert media_record.last_error_category == "media_verification_failed"
        assert media_record.next_retry_at is None
    finally:
        verify_db.close()


def test_handoff_queue_failure_schedules_retry_and_preserves_single_call(tmp_path):
    campaign = _seed_campaign(campaign_id=93023)
    employee = _seed_employee(employee_id=93023, code="93023", name="Retry Handoff Agent")
    run = _seed_run(run_id=94026, source_name="handoff-retry")
    accepted_path = tmp_path / "handoff-retry.mp3"
    accepted_path.write_bytes(b"accepted-audio")

    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="handoff-retry:record",
            source_row_number=2,
            source_payload=_source_row(CRDTS="handoff-retry"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="handoff-retry",
            source_score=91.0,
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.ACCEPTED,
            attempt_count=1,
            stored_file_path=str(accepted_path),
            signature_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
            malware_scan_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
            media_verification_status=recording_ingestion_service.RecordingIngestionInspectionStatus.PASSED,
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        recording_ingestion_service.handoff_accepted_recording(
            db,
            record,
            run=db.get(RecordingIngestionRun, run.id),
            queue_task=lambda call_id: (_ for _ in ()).throw(RuntimeError("queue offline")),
        )
        db.refresh(record)
        calls = db.query(Call).all()
    finally:
        db.close()

    assert len(calls) == 1
    assert record.call_id == calls[0].id
    assert record.status == RecordingIngestionRecordStatus.RETRY_SCHEDULED
    assert record.last_error_category == "handoff_queue_failed"
    assert record.next_retry_at is not None


def test_retry_ingestion_record_reuses_the_same_record_after_timeout_recovery(
    monkeypatch,
    recording_ingestion_fixture_paths,
    tmp_path,
):
    campaign = _seed_campaign(campaign_id=93024)
    employee = _seed_employee(employee_id=93024, code="93024", name="Recovered Agent")
    settings_for_run = SimpleNamespace(
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    layout = recording_ingestion_service.ensure_storage_layout(
        recording_ingestion_service.build_storage_layout(
            quarantine_dir=tmp_path / "quarantine",
            accepted_dir=tmp_path / "accepted",
            rejected_dir=tmp_path / "rejected",
        )
    )
    historic_run = _seed_run(
        run_id=94027,
        source_name="retry-source-history",
        status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
    )
    queued_call_ids: list[int] = []
    monkeypatch.setattr("app.worker.queue_call_audio_processing", lambda call_id: queued_call_ids.append(call_id))

    audio_bytes = recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes()

    def client_factory():
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, content=audio_bytes, headers={"content-type": "audio/mpeg"})
            )
        )

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

    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
                ingestion_run_id=historic_run.id,
                source_name="retry-source",
                source_key="retry-source:record",
            source_row_number=2,
            source_payload=_source_row(CODE=employee.employee_code, NAME=employee.name, CRDTS="retry-source-record"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="retry-source-record",
            source_score=91.0,
            source_quality_notes="Needs retry",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.RETRY_SCHEDULED,
            attempt_count=1,
            next_retry_at=recording_ingestion_service.utcnow() - timedelta(minutes=1),
            last_error_category="download_timeout",
            last_error_detail="Previous timeout.",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        retried = recording_ingestion_service.retry_ingestion_record(
            db,
            record_id=record.id,
            client_factory=client_factory,
            scanner_factory=PassedScanner,
            media_verifier_factory=PassedVerifier,
            layout=layout,
        )
        db.refresh(retried)
        db.refresh(record)
        calls = db.query(Call).all()
        latest_run = db.get(RecordingIngestionRun, retried.ingestion_run_id)
        record_count = db.query(RecordingIngestionRecord).filter(
            RecordingIngestionRecord.source_name == "retry-source",
            RecordingIngestionRecord.source_key == record.source_key,
        ).count()
    finally:
        db.close()

    assert retried.id == record.id
    assert retried.status == RecordingIngestionRecordStatus.SUBMITTED
    assert retried.attempt_count == 2
    assert retried.next_retry_at is None
    assert latest_run is not None
    assert latest_run.trigger == RecordingIngestionRunTrigger.RETRY
    assert latest_run.status == RecordingIngestionRunStatus.COMPLETED
    assert queued_call_ids and len(queued_call_ids) == 1
    assert len(calls) == 1
    assert record_count == 1


def test_retry_ingestion_record_respects_active_run_lock(monkeypatch, tmp_path):
    campaign = _seed_campaign(campaign_id=93025)
    employee = _seed_employee(employee_id=93025, code="93025", name="Locked Retry Agent")
    settings_for_run = SimpleNamespace(
        CALL_INGEST_ALLOWED_RECORDING_HOSTS="archive.dial-fusion.com",
        call_ingest_allowed_recording_hosts_list=["archive.dial-fusion.com"],
        CALL_INGEST_RUNTIME_ROLE="all",
        CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30,
        CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60,
        CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60,
        max_file_size_bytes=1024 * 1024,
    )
    monkeypatch.setattr(recording_ingestion_service, "get_settings", lambda: settings_for_run)
    layout = recording_ingestion_service.ensure_storage_layout(
        recording_ingestion_service.build_storage_layout(
            quarantine_dir=tmp_path / "quarantine",
            accepted_dir=tmp_path / "accepted",
            rejected_dir=tmp_path / "rejected",
        )
    )
    _seed_run(run_id=94028, source_name="locked-retry-source", status=RecordingIngestionRunStatus.PROCESSING)
    historic_run = _seed_run(run_id=94029, source_name="locked-retry-source-previous", status=RecordingIngestionRunStatus.COMPLETED)

    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=historic_run.id,
            source_name="locked-retry-source",
            source_key="locked-retry-source:record",
            source_row_number=2,
            source_payload=_source_row(CODE=employee.employee_code, NAME=employee.name, CRDTS="locked-retry-source-record"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="locked-retry-source-record",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.RETRY_SCHEDULED,
            attempt_count=1,
            next_retry_at=recording_ingestion_service.utcnow() - timedelta(minutes=1),
            last_error_category="download_timeout",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            recording_ingestion_service.retry_ingestion_record(
                db,
                record_id=record.id,
                layout=layout,
                manual=True,
            )
        db.refresh(record)
    finally:
        db.close()

    assert exc_info.value.category == "active_run_exists"
    assert record.attempt_count == 1


@pytest.mark.parametrize(
    "record_status",
    (
        RecordingIngestionRecordStatus.PENDING,
        RecordingIngestionRecordStatus.DOWNLOADING,
        RecordingIngestionRecordStatus.QUARANTINED,
        RecordingIngestionRecordStatus.INSPECTING,
        RecordingIngestionRecordStatus.ACCEPTED,
        RecordingIngestionRecordStatus.HANDOFF_PENDING,
        RecordingIngestionRecordStatus.DUPLICATE,
    ),
)
def test_prepare_ingestion_record_retry_rejects_manual_retry_for_non_retry_states(record_status):
    historic_run = _seed_run(
        run_id=940300 + tuple(RecordingIngestionRecordStatus).index(record_status),
        source_name=f"manual-retry-{record_status.value}",
        status=RecordingIngestionRunStatus.COMPLETED_WITH_ERRORS,
    )

    db = SessionLocal()
    try:
        record = RecordingIngestionRecord(
            ingestion_run_id=historic_run.id,
            source_name=historic_run.source_name,
            source_key=f"{historic_run.source_name}:record",
            source_row_number=2,
            source_payload=_source_row(CRDTS=f"manual-retry-{record_status.value}"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint=f"manual-retry-{record_status.value}",
            status=record_status,
            attempt_count=1,
            last_error_category="download_timeout",
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            recording_ingestion_service.prepare_ingestion_record_retry(
                db,
                record_id=record.id,
                requested_by_employee_id=77,
                manual=True,
            )
    finally:
        db.close()

    assert exc_info.value.category == "record_not_retryable"


def test_reconcile_committed_call_handoffs_claim_blocks_immediate_duplicate_dispatch():
    employee = _seed_employee(employee_id=93040, code="93040", name="Reconcile Agent")
    campaign = _seed_campaign(campaign_id=93040)
    db = SessionLocal()
    try:
        call = Call(
            id=95040,
            employee_id=employee.id,
            campaign_id=campaign.id,
            audio_file_path="D:\\voic call rating\\uploads\\accepted\\reconcile-claim.mp3",
            original_filename="reconcile-claim.mp3",
            status=CallStatus.PENDING,
            source="sheet_ingestion",
        )
        run = RecordingIngestionRun(
            id=96040,
            source_name="reconcile-claim-source",
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
            id=97040,
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="reconcile-claim-source:record",
            source_row_number=2,
            source_payload=_source_row(CRDTS="reconcile-claim-source-record"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="reconcile-claim-source-record",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.ACCEPTED,
            call_id=call.id,
        )
        db.add_all([call, run, record])
        db.commit()
    finally:
        db.close()

    nested_queued_call_ids: list[int] = []
    queued_call_ids: list[int] = []

    def queue_task(call_id: int):
        queued_call_ids.append(call_id)
        nested_db = SessionLocal()
        try:
            nested_result = recording_ingestion_service.reconcile_committed_call_handoffs(
                nested_db,
                queue_task=nested_queued_call_ids.append,
            )
        finally:
            nested_db.close()
        assert nested_result == []

    worker_db = SessionLocal()
    try:
        result = recording_ingestion_service.reconcile_committed_call_handoffs(worker_db, queue_task=queue_task)
    finally:
        worker_db.close()

    assert result == [95040]
    assert queued_call_ids == [95040]
    assert nested_queued_call_ids == []


def test_reconcile_committed_call_handoffs_reclaims_stale_dispatch_claim():
    employee = _seed_employee(employee_id=93041, code="93041", name="Stale Claim Agent")
    campaign = _seed_campaign(campaign_id=93041)
    stale_claim_time = recording_ingestion_service.utcnow() - timedelta(
        seconds=recording_ingestion_service.HANDOFF_RECONCILIATION_LEASE_SECONDS + 30
    )
    db = SessionLocal()
    try:
        call = Call(
            id=95041,
            employee_id=employee.id,
            campaign_id=campaign.id,
            audio_file_path="D:\\voic call rating\\uploads\\accepted\\stale-claim.mp3",
            original_filename="stale-claim.mp3",
            status=CallStatus.PENDING,
            source="sheet_ingestion",
        )
        run = RecordingIngestionRun(
            id=96041,
            source_name="reconcile-stale-claim",
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
            id=97041,
            ingestion_run_id=run.id,
            source_name=run.source_name,
            source_key="reconcile-stale-claim:record",
            source_row_number=2,
            source_payload=_source_row(CRDTS="reconcile-stale-claim-record"),
            recording_url=RECORDING_URL,
            recording_url_fingerprint="reconcile-stale-claim-record",
            employee_id=employee.id,
            campaign_id=campaign.id,
            status=RecordingIngestionRecordStatus.HANDOFF_PENDING,
            call_id=call.id,
            last_error_category=recording_ingestion_service.HANDOFF_RECONCILIATION_CLAIM_CATEGORY,
            last_error_detail=recording_ingestion_service.HANDOFF_RECONCILIATION_CLAIM_DETAIL,
            updated_at=stale_claim_time,
        )
        db.add_all([call, run, record])
        db.commit()
    finally:
        db.close()

    queued_call_ids: list[int] = []
    worker_db = SessionLocal()
    try:
        result = recording_ingestion_service.reconcile_committed_call_handoffs(
            worker_db,
            queue_task=queued_call_ids.append,
        )
    finally:
        worker_db.close()

    assert result == [95041]
    assert queued_call_ids == [95041]
