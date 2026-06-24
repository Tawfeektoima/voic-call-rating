# Quickstart: Automated Call Recording Ingestion

## Prerequisites

1. Provision a dedicated Ubuntu Server LTS VM using Hyper-V Generation 2 with NAT, or VirtualBox with NAT when Hyper-V is unavailable. The VM needs at least 4 vCPU, 8 GB RAM, and 80 GB encrypted persistent storage. Install and run Docker/Compose only inside that VM.
2. Disable VM shared folders, host-drive mounts, shared clipboard, drag-and-drop, USB passthrough, and public/inbound remote access. Do not expose its recording directories to the Windows host.
3. Use PostgreSQL and Redis inside the VM. SQLite is suitable for isolated tests only; it is not safe for the scheduled ingestion and GPU-worker combination.
4. Create a Google service account, enable Google Sheets access for the deployment, and share only the `VICDI_TESTS` spreadsheet with that service-account email as Viewer.
5. Store the service-account credential outside the repository and mount it read-only into the guest service that reads the sheet. Do not place its JSON content in `.env`, source code, logs, or test fixtures.
6. Identify the active platform campaign that imported calls should use. Confirm `CODE` values in the sheet match the intended platform `employee_code` values; resolve mismatches before enabling scheduled runs.
7. Ensure `archive.dial-fusion.com` remains an approved retrieval host and that the guest has authorized network access to the recordings. Configure default-deny inbound networking and allow outbound destinations only for the sheet, approved recording hosts, resolver/NTP/update services, and approved internal endpoints.

## Configuration

Add documented non-secret defaults to `.env.example`; set actual values only in the deployment environment:

```text
CALL_INGEST_ENABLED=false
CALL_INGEST_GOOGLE_SHEET_ID=1baKabi2vI-e9jS-UhKmuLrwQrslwJw59y6iVTqvjzXA
CALL_INGEST_WORKSHEET=الورقة1
CALL_INGEST_RANGE=A:ZZ
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/vicdi-sheets-reader.json
GOOGLE_SERVICE_ACCOUNT_FILE_HOST=/var/lib/call-rating/secrets/vicdi-sheets-reader.json
CALL_INGEST_VM_STORAGE_ROOT=/var/lib/call-rating
CALL_INGEST_DEFAULT_CAMPAIGN_ID=<existing-active-campaign-id>
CALL_INGEST_ALLOWED_RECORDING_HOSTS=archive.dial-fusion.com
CALL_INGEST_INTERVAL_MINUTES=15
CALL_INGEST_DOWNLOAD_CONCURRENCY=4
CALL_INGEST_RETRY_LIMIT=3
CALL_INGEST_REQUEST_TIMEOUT_SECONDS=30
CALL_INGEST_QUARANTINE_DIR=/var/lib/call-rating/quarantine
CALL_INGEST_ACCEPTED_DIR=/var/lib/call-rating/accepted
CALL_INGEST_REJECTED_DIR=/var/lib/call-rating/rejected
CALL_INGEST_SCANNER=clamd
CALL_INGEST_INSPECTION_TIMEOUT_SECONDS=60
CALL_INGEST_MEDIA_VERIFY_TIMEOUT_SECONDS=60
```

Keep `CALL_INGEST_ENABLED=false` until the first manual run completes successfully. In production, mount the Google credential only as the downloader's read-only Compose secret; mount quarantine only into downloader and inspector; mount accepted storage read-only into the GPU worker. The API does not mount recording storage, and the Windows host never mounts any recording directory.
The hardened Compose deployment separates `ingestion-downloader` from `ingestion-inspector`. The downloader can write only the guest-local `quarantine` path and queues inspection after its download commit; the inspector is on internal data/scanner/verifier networks and is the only service that can atomically promote to `accepted` or `rejected`. `ingestion-scheduler` runs Celery Beat without source credentials. `scanner-updater` has the approved definition-update egress; `scanner` itself is internal-only.
Production services must use split roles: `api`, `gpu_worker`, `downloader`, `inspector`, and `scheduler`. Do not use `CALL_INGEST_RUNTIME_ROLE=all` in production.

## Start the services

Apply schema changes before enabling ingestion:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Inside the VM, start the existing API and GPU worker, then start the CPU/I/O ingestion worker and scheduler separately:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
.\.venv\Scripts\python.exe -m celery -A app.worker worker --queues=ingestion-download --loglevel=info -P solo -n "ingestion-downloader@$(hostname)"
.\.venv\Scripts\python.exe -m celery -A app.worker worker --queues=ingestion-inspection --loglevel=info -P solo -n "ingestion-inspector@$(hostname)"
.\.venv\Scripts\python.exe -m celery -A app.worker beat --loglevel=info
```

The scheduler must enqueue only the ingestion task; it must not run downloads inside the API process. The GPU worker continues to receive existing call-processing tasks.

For the VM production topology, use Compose:

```bash
docker compose -f docker-compose.prod.yml up -d postgres redis scanner-updater scanner media-verifier api worker ingestion-downloader ingestion-inspector
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

Only after the manual validation passes:

```bash
docker compose -f docker-compose.prod.yml up -d ingestion-scheduler
```

## Validate before production enablement

1. Confirm the host has no recording-directory share or guest-drive mount, the guest uses NAT, and the dialer has no inbound route to the guest.
2. Configure a test worksheet and test recording host with one valid row, one duplicate row, one malformed link, one unknown `CODE`, one non-audio response claiming to be audio, and one temporary retrieval failure.
3. As an administrator, request `POST /api/recording-ingestion/runs` using the existing platform authentication.
4. Confirm `GET /api/recording-ingestion/runs/{run_id}` reports each row, with the raw recording link, scanner output, and filesystem paths absent from the response.
5. Confirm only the valid row passes quarantine, signature validation, antimalware scan, and media verification; it alone creates one `Call`, writes an accepted audio file under the VM-local upload root, and queues the existing call processor exactly once.
6. Confirm the malformed and scanner-unavailable scenarios are rejected, create no `Call`, and do not reach the accepted directory.
7. Request the same run again and confirm the submitted row is classified as a duplicate with no second `Call` or Celery submission.
8. Restore the transient retrieval failure and use `POST /api/recording-ingestion/records/{record_id}/retry`; confirm it succeeds without duplicating any already-submitted record.
9. Enable `CALL_INGEST_ENABLED=true` only after the manual validation, audit entries, worker visibility, inspection results, VM isolation checks, and release evidence block all pass.
10. Roll back by stopping `ingestion-scheduler` first, then restoring the VM snapshot recorded in `docs/vm-isolation-verification.md` if the guest needs to be reset.

## Automated test suite

Run the feature tests without live Google or Dial Fusion access:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_recording_ingestion_service.py tests/test_recording_ingestion_api.py tests/test_recording_ingestion_worker.py tests/test_recording_ingestion_security.py tests/test_worker_idempotency.py
```

Expected results include sheet-column validation, agent/campaign mapping failures, duplicate and concurrent-run protection, retry categorization, safe redirect/content/size rejection, quarantine cleanup, signature/antimalware/media-verification rejection, one-call handoff only after acceptance, authorized retry, and masked operational responses.
