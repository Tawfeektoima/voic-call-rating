from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import httpx
import pytest

from app.config import validate_recording_ingestion_runtime_startup
from app.database import SessionLocal
from app.models import (
    RecordingIngestionInspectionStatus,
    RecordingIngestionRecord,
    RecordingIngestionRecordStatus,
    RecordingIngestionRun,
    RecordingIngestionRunStatus,
    RecordingIngestionRunTrigger,
)
from app.services.recording_ingestion import (
    FfprobeMediaVerifier,
    MalwareScanResult,
    MediaVerificationResult,
    RecordingIngestionSecurityError,
    build_storage_layout,
    ensure_storage_layout,
    inspect_quarantined_recording,
    sanitize_source_filename,
    stream_to_quarantine,
)


class FakeScanner:
    def __init__(self, result: MalwareScanResult):
        self.result = result
        self.calls = 0

    def scan(self, path: Path, timeout_seconds: int) -> MalwareScanResult:
        self.calls += 1
        return self.result


class FakeVerifier:
    def __init__(self, result: MediaVerificationResult):
        self.result = result
        self.calls = 0

    def verify(self, path: Path, timeout_seconds: int) -> MediaVerificationResult:
        self.calls += 1
        return self.result


@pytest.fixture
def ingestion_layout(tmp_path: Path):
    layout = build_storage_layout(
        quarantine_dir=tmp_path / "quarantine",
        accepted_dir=tmp_path / "accepted",
        rejected_dir=tmp_path / "rejected",
    )
    return ensure_storage_layout(layout)


def _seed_run_and_record(quarantine_file_path: str, source_payload: dict | None = None) -> tuple[RecordingIngestionRun, RecordingIngestionRecord]:
    db = SessionLocal()
    try:
        run = RecordingIngestionRun(
            source_name="vicdi_tests",
            trigger=RecordingIngestionRunTrigger.MANUAL,
            status=RecordingIngestionRunStatus.PROCESSING,
            rows_seen=1,
            new_count=1,
            success_count=0,
            failed_count=0,
            retryable_count=0,
        )
        db.add(run)
        db.flush()

        record = RecordingIngestionRecord(
            ingestion_run_id=run.id,
            source_name="vicdi_tests",
            source_key="row-100",
            source_row_number=2,
            source_payload=source_payload or {"CALL LINK": "https://archive.dial-fusion.com/audio.mp3"},
            recording_url="https://archive.dial-fusion.com/audio.mp3",
            recording_url_fingerprint="fp-100",
            status=RecordingIngestionRecordStatus.QUARANTINED,
            attempt_count=1,
            quarantine_file_path=quarantine_file_path,
        )
        db.add(record)
        db.commit()
        db.refresh(run)
        db.refresh(record)
        return run, record
    finally:
        db.close()


def test_stream_to_quarantine_rejects_redirect_escape(ingestion_layout: Path):
    start_url = "https://archive.dial-fusion.com/audio.mp3"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == start_url:
            return httpx.Response(302, headers={"location": "https://evil.example.com/payload.mp3"})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            stream_to_quarantine(
                client,
                start_url,
                "row-2",
                {"archive.dial-fusion.com"},
                ingestion_layout,
                max_bytes=1024 * 1024,
            )

    assert exc_info.value.category == "disallowed_recording_host"
    assert list(ingestion_layout.quarantine_dir.iterdir()) == []
    assert list(ingestion_layout.accepted_dir.iterdir()) == []


def test_stream_to_quarantine_rejects_html_content_type_and_cleans_partial(ingestion_layout):
    url = "https://archive.dial-fusion.com/audio.mp3"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>nope</html>", headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            stream_to_quarantine(
                client,
                url,
                "row-2",
                {"archive.dial-fusion.com"},
                ingestion_layout,
                max_bytes=1024 * 1024,
            )

    assert exc_info.value.category == "unsupported_content_type"
    assert list(ingestion_layout.quarantine_dir.iterdir()) == []


def test_stream_to_quarantine_rejects_non_audio_bytes_even_with_audio_header(
    ingestion_layout,
    recording_ingestion_fixture_paths: dict[str, Path],
):
    url = "https://archive.dial-fusion.com/audio.mp3"
    spoofed_bytes = recording_ingestion_fixture_paths["html_audio_header"].read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=spoofed_bytes, headers={"content-type": "audio/mpeg"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            stream_to_quarantine(
                client,
                url,
                "row-2",
                {"archive.dial-fusion.com"},
                ingestion_layout,
                max_bytes=1024 * 1024,
            )

    assert exc_info.value.category == "unsupported_signature"
    assert list(ingestion_layout.quarantine_dir.iterdir()) == []


def test_stream_to_quarantine_rejects_oversize_and_empty_cleanup(ingestion_layout):
    url = "https://archive.dial-fusion.com/audio.mp3"

    def empty_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"", headers={"content-type": "audio/mpeg"})

    with httpx.Client(transport=httpx.MockTransport(empty_handler)) as client:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            stream_to_quarantine(
                client,
                url,
                "row-2",
                {"archive.dial-fusion.com"},
                ingestion_layout,
                max_bytes=1024,
            )
    assert exc_info.value.category == "empty_recording"
    assert list(ingestion_layout.quarantine_dir.iterdir()) == []

    def oversize_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"ID3" + (b"x" * 2048), headers={"content-type": "audio/mpeg"})

    with httpx.Client(transport=httpx.MockTransport(oversize_handler)) as client:
        with pytest.raises(RecordingIngestionSecurityError) as exc_info:
            stream_to_quarantine(
                client,
                url,
                "row-2",
                {"archive.dial-fusion.com"},
                ingestion_layout,
                max_bytes=128,
            )
    assert exc_info.value.category == "file_too_large"
    assert list(ingestion_layout.quarantine_dir.iterdir()) == []


def test_sanitize_source_filename_blocks_unsafe_names():
    assert sanitize_source_filename("../AUX?.mp3") == "AUX_.mp3"
    assert sanitize_source_filename("..\\folder\\call name.wav") == "call name.wav"


def test_inspection_pipeline_accepts_valid_audio(
    ingestion_layout,
    recording_ingestion_fixture_paths: dict[str, Path],
):
    source_file = recording_ingestion_fixture_paths["valid_audio_mp3"]
    quarantined = ingestion_layout.quarantine_dir / "valid_tiny_audio.mp3"
    quarantined.write_bytes(source_file.read_bytes())

    run, record = _seed_run_and_record(str(quarantined))
    scanner = FakeScanner(
        MalwareScanResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            scanner_name="clamd",
            scanner_version="1.0",
        )
    )
    verifier = FakeVerifier(
        MediaVerificationResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            duration_seconds=0.1,
        )
    )

    db = SessionLocal()
    try:
        db_record = db.get(RecordingIngestionRecord, record.id)
        db_run = db.get(RecordingIngestionRun, run.id)
        inspect_quarantined_recording(db, db_record, db_run, layout=ingestion_layout, scanner=scanner, media_verifier=verifier)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()

    assert scanner.calls == 1
    assert verifier.calls == 1
    assert db_record.status == RecordingIngestionRecordStatus.ACCEPTED
    assert db_record.signature_status == RecordingIngestionInspectionStatus.PASSED
    assert db_record.malware_scan_status == RecordingIngestionInspectionStatus.PASSED
    assert db_record.media_verification_status == RecordingIngestionInspectionStatus.PASSED
    assert db_record.stored_file_path is not None
    assert Path(db_record.stored_file_path).is_file()
    assert not quarantined.exists()
    assert list(ingestion_layout.rejected_dir.iterdir()) == []


def test_inspection_pipeline_rejects_content_type_spoof_without_handoff(
    ingestion_layout,
    recording_ingestion_fixture_paths: dict[str, Path],
):
    quarantined = ingestion_layout.quarantine_dir / "spoofed.mp3"
    quarantined.write_bytes(recording_ingestion_fixture_paths["html_audio_header"].read_bytes())

    run, record = _seed_run_and_record(str(quarantined))
    scanner = FakeScanner(
        MalwareScanResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            scanner_name="clamd",
            scanner_version="1.0",
        )
    )
    verifier = FakeVerifier(
        MediaVerificationResult(
            status=RecordingIngestionInspectionStatus.REJECTED,
            error_category="media_verification_failed",
            error_detail="Media verification rejected the recording.",
        )
    )

    db = SessionLocal()
    try:
        db_record = db.get(RecordingIngestionRecord, record.id)
        db_run = db.get(RecordingIngestionRun, run.id)
        inspect_quarantined_recording(db, db_record, db_run, layout=ingestion_layout, scanner=scanner, media_verifier=verifier)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()

    assert db_record.status == RecordingIngestionRecordStatus.REJECTED
    assert db_record.signature_status == RecordingIngestionInspectionStatus.REJECTED
    assert db_record.media_verification_status == RecordingIngestionInspectionStatus.PENDING
    assert db_record.stored_file_path is None
    assert db_record.next_retry_at is None
    assert verifier.calls == 0
    assert list(ingestion_layout.accepted_dir.iterdir()) == []
    assert len(list(ingestion_layout.rejected_dir.iterdir())) == 1


@pytest.mark.parametrize(
    ("scan_result", "expected_category"),
    [
        (
            MalwareScanResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                scanner_name="clamd",
                scanner_version="1.0",
                error_category="malware_detected",
                error_detail="Malware scanner rejected the recording.",
            ),
            "malware_detected",
        ),
        (
            MalwareScanResult(
                status=RecordingIngestionInspectionStatus.UNAVAILABLE,
                scanner_name="clamd",
                scanner_version="1.0",
                error_category="scanner_timeout",
                error_detail="Malware scanner timed out.",
            ),
            "scanner_timeout",
        ),
        (
            MalwareScanResult(
                status=RecordingIngestionInspectionStatus.UNAVAILABLE,
                scanner_name="clamd",
                scanner_version="1.0",
                error_category="scanner_unavailable",
                error_detail="Malware scanner is unavailable.",
            ),
            "scanner_unavailable",
        ),
    ],
)
def test_inspection_pipeline_rejects_non_clean_scanner_results(
    ingestion_layout,
    recording_ingestion_fixture_paths: dict[str, Path],
    scan_result: MalwareScanResult,
    expected_category: str,
):
    quarantined = ingestion_layout.quarantine_dir / "valid_tiny_audio.mp3"
    quarantined.write_bytes(recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes())
    run, record = _seed_run_and_record(str(quarantined))
    scanner = FakeScanner(scan_result)
    verifier = FakeVerifier(MediaVerificationResult(status=RecordingIngestionInspectionStatus.PASSED, duration_seconds=0.1))

    db = SessionLocal()
    try:
        db_record = db.get(RecordingIngestionRecord, record.id)
        db_run = db.get(RecordingIngestionRun, run.id)
        inspect_quarantined_recording(db, db_record, db_run, layout=ingestion_layout, scanner=scanner, media_verifier=verifier)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()

    assert db_record.status == RecordingIngestionRecordStatus.REJECTED
    assert db_record.malware_scan_status == scan_result.status
    assert db_record.last_error_category == expected_category
    assert db_record.stored_file_path is None
    assert verifier.calls == 0
    assert list(ingestion_layout.accepted_dir.iterdir()) == []


@pytest.mark.parametrize(
    ("verification_result", "expected_category"),
    [
        (
            MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_failed",
                error_detail="Media verification rejected the recording.",
            ),
            "media_verification_failed",
        ),
        (
            MediaVerificationResult(
                status=RecordingIngestionInspectionStatus.REJECTED,
                error_category="media_verification_timeout",
                error_detail="Media verification timed out.",
            ),
            "media_verification_timeout",
        ),
    ],
)
def test_inspection_pipeline_rejects_media_failures(
    ingestion_layout,
    recording_ingestion_fixture_paths: dict[str, Path],
    verification_result: MediaVerificationResult,
    expected_category: str,
):
    quarantined = ingestion_layout.quarantine_dir / "valid_tiny_audio.mp3"
    quarantined.write_bytes(recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes())
    run, record = _seed_run_and_record(str(quarantined))
    scanner = FakeScanner(
        MalwareScanResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            scanner_name="clamd",
            scanner_version="1.0",
        )
    )
    verifier = FakeVerifier(verification_result)

    db = SessionLocal()
    try:
        db_record = db.get(RecordingIngestionRecord, record.id)
        db_run = db.get(RecordingIngestionRun, run.id)
        inspect_quarantined_recording(db, db_record, db_run, layout=ingestion_layout, scanner=scanner, media_verifier=verifier)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()

    assert db_record.status == RecordingIngestionRecordStatus.REJECTED
    assert db_record.last_error_category == expected_category
    assert db_record.stored_file_path is None
    assert list(ingestion_layout.accepted_dir.iterdir()) == []


def test_inspection_pipeline_rejects_quarantine_path_escape_without_scanning(
    ingestion_layout,
    tmp_path: Path,
    recording_ingestion_fixture_paths: dict[str, Path],
):
    escaped_file = tmp_path / "escaped.mp3"
    escaped_file.write_bytes(recording_ingestion_fixture_paths["valid_audio_mp3"].read_bytes())
    run, record = _seed_run_and_record(str(escaped_file))
    scanner = FakeScanner(
        MalwareScanResult(
            status=RecordingIngestionInspectionStatus.PASSED,
            scanner_name="clamd",
        )
    )
    verifier = FakeVerifier(MediaVerificationResult(status=RecordingIngestionInspectionStatus.PASSED, duration_seconds=0.1))

    db = SessionLocal()
    try:
        db_record = db.get(RecordingIngestionRecord, record.id)
        db_run = db.get(RecordingIngestionRun, run.id)
        inspect_quarantined_recording(db, db_record, db_run, layout=ingestion_layout, scanner=scanner, media_verifier=verifier)
        db.commit()
        db.refresh(db_record)
    finally:
        db.close()

    assert db_record.status == RecordingIngestionRecordStatus.REJECTED
    assert db_record.last_error_category == "unsafe_storage_path"
    assert scanner.calls == 0
    assert verifier.calls == 0


def test_ffprobe_verifier_fails_closed_when_sandbox_is_unavailable(monkeypatch, tmp_path: Path):
    audio_file = tmp_path / "sample.mp3"
    audio_file.write_bytes(b"ID3" + (b"x" * 32))

    monkeypatch.setattr("app.services.recording_ingestion.shutil.which", lambda _: None)

    result = FfprobeMediaVerifier().verify(audio_file, timeout_seconds=1)

    assert result.status == RecordingIngestionInspectionStatus.REJECTED
    assert result.error_category == "media_verification_unavailable"


def test_ffprobe_verifier_stops_parser_when_output_limit_is_exceeded(monkeypatch, tmp_path: Path):
    audio_file = tmp_path / "sample.mp3"
    audio_file.write_bytes(b"ID3" + (b"x" * 32))
    monkeypatch.setattr(
        "app.services.recording_ingestion._build_ffprobe_command",
        lambda _: [sys.executable, "-c", "import sys; sys.stdout.write('x' * 300000)"],
    )

    result = FfprobeMediaVerifier().verify(audio_file, timeout_seconds=5)

    assert result.status == RecordingIngestionInspectionStatus.REJECTED
    assert result.error_category == "media_verification_failed"
    assert result.error_detail == "Media verification produced too much output."


def test_runtime_roles_block_cross_boundary_operations(monkeypatch, ingestion_layout):
    monkeypatch.setattr(
        "app.services.recording_ingestion.get_settings",
        lambda: SimpleNamespace(CALL_INGEST_RUNTIME_ROLE="inspector"),
    )
    with pytest.raises(RecordingIngestionSecurityError, match="cannot download"):
        stream_to_quarantine(None, "https://archive.dial-fusion.com/audio.mp3", "row-2", set(), ingestion_layout, 1024)

    monkeypatch.setattr(
        "app.services.recording_ingestion.get_settings",
        lambda: SimpleNamespace(CALL_INGEST_RUNTIME_ROLE="downloader"),
    )
    with pytest.raises(RecordingIngestionSecurityError, match="cannot inspect"):
        inspect_quarantined_recording(None, None, None, layout=ingestion_layout)

    monkeypatch.setattr(
        "app.services.recording_ingestion.get_settings",
        lambda: SimpleNamespace(CALL_INGEST_RUNTIME_ROLE="scheduler"),
    )
    with pytest.raises(RecordingIngestionSecurityError, match="cannot download"):
        stream_to_quarantine(None, "https://archive.dial-fusion.com/audio.mp3", "row-2", set(), ingestion_layout, 1024)


def _production_runtime_settings(**overrides):
    defaults = {
        "ENVIRONMENT": "production",
        "CALL_INGEST_ENABLED": True,
        "CALL_INGEST_RUNTIME_ROLE": "downloader",
        "CALL_INGEST_SCANNER_ENDPOINT": "clamd://scanner:3310",
        "CALL_INGEST_MEDIA_VERIFIER_ENDPOINT": "http://media-verifier:8090",
        "CALL_INGEST_INSPECTION_TIMEOUT_SECONDS": 5,
        "GOOGLE_SERVICE_ACCOUNT_FILE": "/run/secrets/vicdi-sheets-reader.json",
        "is_production": True,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_production_runtime_validation_skips_when_ingestion_is_disabled():
    validate_recording_ingestion_runtime_startup(
        _production_runtime_settings(CALL_INGEST_ENABLED=False),
    )


def test_production_runtime_validation_rejects_missing_downloader_secret():
    settings = _production_runtime_settings(CALL_INGEST_RUNTIME_ROLE="downloader")

    with pytest.raises(RuntimeError, match="service-account secret is missing"):
        validate_recording_ingestion_runtime_startup(settings, path_exists=lambda _: False)


def test_production_runtime_validation_rejects_unhealthy_scanner():
    settings = _production_runtime_settings(CALL_INGEST_RUNTIME_ROLE="inspector")

    with pytest.raises(RuntimeError, match="scanner health probe"):
        validate_recording_ingestion_runtime_startup(
            settings,
            tcp_probe=lambda host, port, timeout: (_ for _ in ()).throw(OSError(f"{host}:{port} down")),
            http_probe=lambda url, timeout: 200,
        )


def test_production_runtime_validation_rejects_unhealthy_media_verifier():
    settings = _production_runtime_settings(CALL_INGEST_RUNTIME_ROLE="inspector")

    with pytest.raises(RuntimeError, match="media verifier health probe"):
        validate_recording_ingestion_runtime_startup(
            settings,
            tcp_probe=lambda host, port, timeout: None,
            http_probe=lambda url, timeout: 503,
        )


def test_production_runtime_validation_accepts_healthy_inspector_dependencies():
    settings = _production_runtime_settings(CALL_INGEST_RUNTIME_ROLE="inspector")

    validate_recording_ingestion_runtime_startup(
        settings,
        tcp_probe=lambda host, port, timeout: None,
        http_probe=lambda url, timeout: 200,
    )
