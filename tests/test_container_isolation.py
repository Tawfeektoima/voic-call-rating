from __future__ import annotations

from pathlib import Path

import yaml


def test_prod_compose_separates_ingestion_runtime_from_api_and_general_worker():
    compose = yaml.safe_load(Path("docker-compose.prod.yml").read_text(encoding="utf-8"))

    api = compose["services"]["api"]
    worker = compose["services"]["worker"]
    downloader = compose["services"]["ingestion-downloader"]
    inspector = compose["services"]["ingestion-inspector"]
    scheduler = compose["services"]["ingestion-scheduler"]
    scanner = compose["services"]["scanner"]
    scanner_updater = compose["services"]["scanner-updater"]
    media_verifier = compose["services"]["media-verifier"]
    volumes = compose["volumes"]
    networks = compose["networks"]

    assert "call-uploads" in volumes
    assert "clamav-db" in volumes
    assert "ingestion-quarantine" in volumes
    assert "ingestion-accepted" in volumes
    assert "ingestion-rejected" in volumes
    assert "ingestion-state" in volumes
    assert "scanner-internal" in networks
    assert "verifier-internal" in networks
    assert "data-internal" in networks
    assert networks["scanner-internal"]["internal"] is True
    assert networks["verifier-internal"]["internal"] is True
    assert networks["data-internal"]["internal"] is True

    assert api["read_only"] is True
    assert worker["read_only"] is True
    assert downloader["read_only"] is True
    assert inspector["read_only"] is True
    assert scheduler["read_only"] is True
    assert scanner["read_only"] is True
    assert scanner_updater["read_only"] is True
    assert media_verifier["read_only"] is True

    assert "no-new-privileges:true" in api["security_opt"]
    assert "no-new-privileges:true" in worker["security_opt"]
    assert "no-new-privileges:true" in downloader["security_opt"]
    assert "no-new-privileges:true" in inspector["security_opt"]
    assert "no-new-privileges:true" in scanner["security_opt"]
    assert "no-new-privileges:true" in media_verifier["security_opt"]

    assert "ALL" in api["cap_drop"]
    assert "ALL" in worker["cap_drop"]
    assert "ALL" in downloader["cap_drop"]
    assert "ALL" in inspector["cap_drop"]
    assert "ALL" in scheduler["cap_drop"]
    assert "ALL" in scanner["cap_drop"]
    assert "ALL" in media_verifier["cap_drop"]

    assert set(api["networks"]) == {"backend", "data-internal"}
    assert set(worker["networks"]) == {"backend", "data-internal"}
    assert set(downloader["networks"]) == {"backend", "data-internal"}
    assert set(inspector["networks"]) == {"data-internal", "scanner-internal", "verifier-internal"}
    assert scheduler["networks"] == ["data-internal"]
    assert scanner["networks"] == ["scanner-internal"]
    assert scanner_updater["networks"] == ["backend"]
    assert media_verifier["networks"] == ["verifier-internal"]
    assert "backend" not in inspector["networks"]

    assert any(volume == "call-uploads:/app/uploads" for volume in api["volumes"])
    assert any(volume == "call-uploads:/app/uploads" for volume in worker["volumes"])
    assert api["environment"]["CALL_INGEST_RUNTIME_ROLE"] == "api"
    assert worker["environment"]["CALL_INGEST_RUNTIME_ROLE"] == "gpu_worker"
    assert downloader["environment"]["CALL_INGEST_RUNTIME_ROLE"] == "downloader"
    assert inspector["environment"]["CALL_INGEST_RUNTIME_ROLE"] == "inspector"
    assert scheduler["environment"]["CALL_INGEST_RUNTIME_ROLE"] == "scheduler"
    assert downloader["command"][6] == "ingestion-download"
    assert inspector["command"][6] == "ingestion-inspection"
    assert scheduler["command"][3] == "beat"
    assert api["ports"] == ["127.0.0.1:8000:8000"]

    assert not any("/var/lib/call-rating" in str(volume) for volume in api.get("volumes", []))
    assert "ingestion-accepted:/var/lib/call-rating/accepted:ro" in worker.get("volumes", [])
    assert not any("/var/lib/call-rating/quarantine" in str(volume) for volume in worker.get("volumes", []))
    assert scanner.get("volumes") == ["clamav-db:/var/lib/clamav:ro"]

    assert inspector["environment"]["CALL_INGEST_SCANNER_ENDPOINT"] == "clamd://scanner:3310"
    assert inspector["environment"]["CALL_INGEST_MEDIA_VERIFIER_ENDPOINT"] == "http://media-verifier:8090"
    assert scanner["user"] == "clamav:clamav"
    assert "freshclam" not in " ".join(scanner["command"])
    assert "freshclam" in " ".join(scanner_updater["command"])

    downloader_volumes = set(downloader["volumes"])
    inspector_volumes = set(inspector["volumes"])
    assert downloader_volumes == {
        "ingestion-quarantine:/var/lib/call-rating/quarantine",
        "ingestion-state:/var/lib/call-rating/state",
    }
    assert "ingestion-accepted:/var/lib/call-rating/accepted" not in downloader_volumes
    assert inspector_volumes == {
        "ingestion-quarantine:/var/lib/call-rating/quarantine",
        "ingestion-accepted:/var/lib/call-rating/accepted",
        "ingestion-rejected:/var/lib/call-rating/rejected",
        "ingestion-state:/var/lib/call-rating/state",
    }
    assert media_verifier["volumes"] == ["ingestion-quarantine:/var/lib/call-rating/quarantine:ro"]
    assert downloader["environment"]["GOOGLE_SERVICE_ACCOUNT_FILE"] == "/run/secrets/vicdi-sheets-reader.json"
    assert downloader["secrets"][0]["source"] == "vicdi-sheets-reader"
    assert "vicdi-sheets-reader" in compose["secrets"]
    assert "healthcheck" in api
    assert "healthcheck" in worker
    assert "healthcheck" in downloader
    assert "healthcheck" in inspector
    assert "healthcheck" in scheduler
    assert not any(isinstance(volume, dict) for volume in downloader["volumes"])
    assert not any(isinstance(volume, dict) for volume in inspector["volumes"])


def test_dockerfile_runs_as_non_root_app_user_and_prepares_ingestion_storage():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "useradd --uid 10001 --gid app" in dockerfile
    assert "COPY --chown=app:app . ." in dockerfile
    assert "/var/lib/call-rating/quarantine" in dockerfile
    assert "ffmpeg" in dockerfile
    assert "\nUSER app\n" in dockerfile
