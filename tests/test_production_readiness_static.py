from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def test_production_guards_are_present():
    main_text = _read("app/main.py")
    config_text = _read("app/config.py")

    assert 'if settings.ENVIRONMENT.lower() != "production":' in main_text
    assert "Base.metadata.create_all(bind=engine)" in main_text
    assert "SQLite is not allowed in production" in config_text
    assert "must include Redis authentication in production" in config_text


def test_ci_runs_release_gates():
    workflow = _read(".github/workflows/ci.yml")

    assert "python -m compileall app" in workflow
    assert "python -m pytest -q tests" in workflow
    assert "npm run test" in workflow
    assert "npm run build" in workflow


def test_docs_cover_deployment_checklist():
    readiness = _read("docs/production_readiness.md")
    readme = _read("README.md")
    env_example = _read(".env.example")
    runbook = _read("docs/vm-ingestion-runbook.md")
    quickstart = _read("specs/001-call-recording-ingestion/quickstart.md")
    isolation_verification = _read("docs/vm-isolation-verification.md")
    tasks = _read("specs/001-call-recording-ingestion/tasks.md")

    assert "alembic upgrade head" in readiness
    assert "docker compose -f docker-compose.prod.yml up -d postgres redis" in readiness
    assert "celery -A app.worker.celery_app worker --loglevel=info" in readiness
    assert "npm run build" in readiness
    assert "/api/system/metrics" in readiness
    assert "python run_smoke_test.py" in readiness
    assert "PUBLIC_BASE_URL" in readiness

    assert "python -m compileall app" in readme
    assert "python -m pytest -q tests" in readme
    assert "npm test && npm run build" in readme
    assert "PUBLIC_BASE_URL" in readme
    assert "ingestion-downloader" in readme
    assert "ingestion-inspector" in readme
    assert "CALL_INGEST_RUNTIME_ROLE=all" in readme
    assert "ingestion-scheduler" in readme

    assert "SECRET_KEY=" in env_example
    assert "ENVIRONMENT=" in env_example
    assert "DATABASE_URL=" in env_example
    assert "REDIS_PASSWORD=" in env_example
    assert "FRONTEND_URL=" in env_example
    assert "PUBLIC_BASE_URL=" in env_example
    assert "GOOGLE_SERVICE_ACCOUNT_FILE_HOST=" in env_example
    assert "CALL_INGEST_VM_STORAGE_ROOT=" in env_example

    assert "Validation Sequence" in runbook
    assert "Rollback" in runbook
    assert "Release Evidence" in runbook
    assert "Validation date: 2026-06-24" in isolation_verification
    assert "Baseline snapshot ID: `call-rating-ingestion-baseline-2026-06-23`" in isolation_verification
    assert "No shared folders." in isolation_verification
    assert "No clipboard integration." in isolation_verification
    assert "No drag-and-drop integration." in isolation_verification
    assert "No USB passthrough." in isolation_verification
    assert "- [X] T023 [US4] Verify VM isolation controls" in tasks
    assert "ingestion-scheduler" in quickstart
    assert "CALL_INGEST_ENABLED=true" in quickstart


def test_smoke_runner_covers_core_release_flow():
    smoke = _read("run_smoke_test.py")

    assert "/api/auth/login" in smoke
    assert "/api/auth/me" in smoke
    assert "/api/audio/upload" in smoke
    assert "/api/audio/" in smoke
    assert "/api/export/csv" in smoke
