"""
Basic release-readiness smoke test for the Voice Call Rating Platform.

This runner uses an isolated SQLite database and FastAPI TestClient so another
engineer can verify the core product flow without booting Redis, Celery, or the
frontend dev server.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


def _configure_env(temp_root: Path) -> None:
    os.environ["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY",
        "smoke-test-secret-key-abcdefghijklmnopqrstuvwxyz",
    )
    os.environ["ENVIRONMENT"] = "development"
    os.environ["DATABASE_URL"] = f"sqlite:///{(temp_root / 'smoke.db').as_posix()}"
    os.environ["UPLOAD_DIR"] = str(temp_root / "uploads")


def _bootstrap_app():
    from fastapi.testclient import TestClient
    import app.config

    app.config.get_settings.cache_clear()

    import app.database
    import app.models  # noqa: F401
    import app.security
    import app.main

    return {
        "app": app.main.app,
        "Base": app.database.Base,
        "engine": app.database.engine,
        "SessionLocal": app.database.SessionLocal,
        "TestClient": TestClient,
        "get_password_hash": app.security.get_password_hash,
    }


def _seed_data(session_local, password_hash_fn):
    from app.models import Campaign, Employee, UserRole

    db = session_local()
    try:
        admin = Employee(
            name="Smoke Admin",
            email="smoke_admin@example.com",
            role=UserRole.ADMIN,
            employee_code="SMOKE_ADMIN",
            hashed_password=password_hash_fn("smoke-password"),
            status="active",
        )
        campaign = Campaign(
            name="SMOKE_CAMPAIGN",
            evaluation_prompt="Score the call accurately.",
            color="#123456",
        )
        db.add_all([admin, campaign])
        db.commit()
        db.refresh(admin)
        db.refresh(campaign)
        return admin.id, campaign.id
    finally:
        db.close()


def _mark_call_complete(session_local, call_id: int) -> None:
    from app.models import Call, CallStatus

    db = session_local()
    try:
        call = db.query(Call).filter(Call.id == call_id).first()
        call.status = CallStatus.EVALUATED
        call.audio_duration = 12.5
        call.evaluation_score = 88.0
        call.call_summary = "Smoke test summary"
        call.transcript = [
            {
                "id": "0",
                "start": 0.0,
                "end": 2.0,
                "speaker": "Agent",
                "text": "Hello and welcome.",
                "emotion": "calm",
                "needs_review": False,
            }
        ]
        call.processed_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _expect(response, status_code: int, label: str) -> None:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{label} failed: expected {status_code}, got {response.status_code}: {response.text}"
        )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="voiceqa-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        _configure_env(temp_root)
        modules = _bootstrap_app()
        modules["Base"].metadata.create_all(bind=modules["engine"])

        admin_id, campaign_id = _seed_data(
            modules["SessionLocal"],
            modules["get_password_hash"],
        )

        client = modules["TestClient"](modules["app"])

        with patch("app.routers.audio.process_call_audio_task.delay") as mock_delay:
            login = client.post(
                "/api/auth/login",
                json={"email": "smoke_admin@example.com", "password": "smoke-password"},
            )
            _expect(login, 200, "login")
            token = login.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            me = client.get("/api/auth/me", headers=headers)
            _expect(me, 200, "protected me endpoint")

            upload = client.post(
                "/api/audio/upload",
                headers=headers,
                data={"employee_id": str(admin_id), "campaign_id": str(campaign_id)},
                files={"file": ("smoke.wav", io.BytesIO(b"RIFFsmoke-audio"), "audio/wav")},
            )
            _expect(upload, 200, "call upload")
            call_id = upload.json()["call_id"]
            if mock_delay.call_count != 1:
                raise RuntimeError("upload did not enqueue exactly one background task")

            pending = client.get(f"/api/audio/{call_id}", headers=headers)
            _expect(pending, 200, "pending call detail")

            _mark_call_complete(modules["SessionLocal"], call_id)

            result_view = client.get(f"/api/audio/{call_id}", headers=headers)
            _expect(result_view, 200, "result view")
            result_payload = result_view.json()
            if result_payload["status"] != "evaluated":
                raise RuntimeError("result view did not return an evaluated call")

            export = client.get(f"/api/export/csv?campaign_id={campaign_id}", headers=headers)
            _expect(export, 200, "csv export")
            if "call_id,date,agent_id,campaign_id" not in export.text:
                raise RuntimeError("export did not return the expected CSV header")

        print("Smoke test passed:")
        print("  1. Login succeeded")
        print("  2. Protected /api/auth/me succeeded")
        print("  3. Audio upload created a pending call")
        print("  4. Result view returned an evaluated call")
        print("  5. CSV export succeeded")
        modules["engine"].dispose()
        return 0


if __name__ == "__main__":
    sys.exit(main())
