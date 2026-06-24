# Tasks: Secure Automated Call Recording Ingestion

**Input**: Design documents from `/specs/001-call-recording-ingestion/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [security-deployment.md](./security-deployment.md), [quickstart.md](./quickstart.md), and [recording-ingestion.openapi.yaml](./contracts/recording-ingestion.openapi.yaml)

**Tests**: Required. The specification and implementation plan explicitly require mocked service, worker, API, security, and end-to-end validation. Tests must be written before the corresponding implementation task and must not contact the production sheet or dialer.

**Task format**: Every top-level checklist item is an executable AI-agent task. Its numbered substeps define the minimum completion work and verification; they are intentionally not separate checklist tasks so task IDs remain unambiguous.

## Phase 1: Decision Gates and Secure VM Setup

**Purpose**: Resolve deployment decisions that affect every later task and prepare an isolated VM without exposing production secrets or recordings.

- [X] T001 Decide and record GPU placement in `specs/001-call-recording-ingestion/security-deployment.md`
  1. Confirm that the existing GPU worker can run inside the selected VM with supported passthrough, or explicitly select CPU-only transcription for version 1.
  2. Record the selected option, capacity impact, and fallback; do not deploy an untested passthrough configuration.

- [X] T002 Decide and record the guest antimalware engine in `specs/001-call-recording-ingestion/security-deployment.md`
  1. Keep the Linux guest baseline and select `clamd`, or record the approved Windows guest/Defender exception with licensing and update ownership.
  2. Define the required scan result values and the fail-closed behavior when the engine is unavailable.

- [X] T003 [P] Create the host VM-provisioning helper in `scripts/provision-ingestion-vm.ps1`
  1. Create, but do not automatically start, a Hyper-V Generation 2 VM with the approved CPU, RAM, encrypted VHDX location, and NAT-only network configuration.
  2. Include preflight checks for Hyper-V availability and clear instructions to use the documented VirtualBox fallback when unavailable.

- [X] T004 [P] Create the guest hardening/bootstrap script in `deploy/ingestion-vm/bootstrap.sh`
  1. Create a non-root service account, guest-local storage roots, unattended security updates, and a default-deny inbound firewall.
  2. Disable password SSH by default and document the approved key-based management route; do not enable host mounts or desktop integration.

- [X] T005 [P] Create the operations runbook in `docs/vm-ingestion-runbook.md`
  1. Document VM creation, NAT, disabled shared folders/clipboard/drag-and-drop/USB, patching, snapshots, backup, and restore.
  2. Document the incident action: disable the guest schedule, preserve guest-local evidence, rotate credentials, and never copy a suspicious audio file to the Windows host.

**Checkpoint**: An approved isolation design exists before secrets, dialer access, or audio enters the VM.

---

## Phase 2: Foundational Platform Changes

**Purpose**: Add the shared settings, durable schema, permissions, queues, and test fixtures that block all user-story work.

**Critical rule**: No user-story implementation begins until this phase is complete.

- [X] T006 Extend ingestion and inspection settings in `app/config.py` and `.env.example`
  1. Add validated settings for source ID/range, approved hosts, schedule, concurrency, retry limits, VM-local quarantine/accepted/rejected directories, scanner endpoint, and inspection timeouts.
  2. Reject unsafe directory relationships, empty host allowlists, non-positive limits, and production defaults that would enable ingestion without explicit approval.

- [X] T007 [P] Add required runtime dependencies in `requirements.txt`, `Dockerfile`, and `docker-compose.prod.yml`
  1. Add pinned Google Sheets/auth dependencies and the selected scanner client dependency; keep FFmpeg/`ffprobe` available in the guest image.
  2. Add a scanner service or documented scanner socket, health check, and guest-local named volumes without exposing them to the Windows host.

- [X] T008 Define durable ingestion models and enums in `app/models.py`
  1. Add `RecordingIngestionRun`, `RecordingIngestionRecord`, and `RecordingIngestionAttempt` with unique source identity, protected URL field, hashes, inspection fields, counters, timestamps, and foreign keys from [data-model.md](./data-model.md).
  2. Encode the lifecycle `pending → downloading → quarantined → inspecting → accepted → handoff_pending → submitted`, plus duplicate, rejected, failed, retry, and review outcomes.

- [X] T009 Create the ingestion schema migration in `alembic/versions/<revision>_add_recording_ingestion.py`
  1. Create tables, indexes, unique constraints, check constraints, and nullable transition fields needed by `app/models.py`.
  2. Validate upgrade and downgrade against an empty development database; do not alter existing call data.

- [X] T010 Define safe request/response models in `app/schemas.py`
  1. Add run, record, attempt, retry, and inspection-status schemas that expose only sanitized fields, hashes, and outcome categories.
  2. Ensure raw recording URLs, credentials, absolute guest paths, scanner output, audio bytes, and raw transcripts have no response field.

- [X] T011 Update the operations API contract in `specs/001-call-recording-ingestion/contracts/recording-ingestion.openapi.yaml`
  1. Add the sanitized inspection state and timestamps needed to satisfy FR-020 without returning scanner output or file paths.
  2. Align status/error enums with `app/models.py` and `app/schemas.py`; validate the OpenAPI document parses as YAML.

- [X] T012 Add the ingestion-management permission and authorization helpers in `app/security.py`, `app/models.py`, and `app/schemas.py`
  1. Define `calls.ingestion.manage` using the repository's existing role/permission pattern and restrict manual run and retry operations to it.
  2. Add tests proving unauthorized callers cannot start, retry, or view sensitive ingestion details.

- [X] T013 Configure isolated Celery routes and scheduler hooks in `app/worker.py`
  1. Route ingestion/reconciliation work to a dedicated CPU/I/O queue and leave the existing audio/GPU queue independent.
  2. Add an opt-in schedule driven by validated settings, with one-active-run protection delegated to the database service.

- [X] T014 [P] Create reusable test fixtures in `tests/conftest.py` and `tests/fixtures/recording_ingestion/`
  1. Add local CSV/Sheet rows, valid tiny audio fixtures, malformed bytes, HTML-with-audio-header, redirect, timeout, and scanner-unavailable fixtures.
  2. Ensure all fixtures are synthetic and all HTTP, scanner, ffprobe, Sheets, Celery, and clock access can be mocked.

**Checkpoint**: Database, configuration, permissions, API shapes, queue boundaries, and test fixtures support safe feature work.

---

## Phase 3: User Story 4 — Contain and Inspect Untrusted Recordings (Priority: P1)

**Goal**: Raw recordings are confined to the VM, inspected fail-closed, and never reach transcription or processing until accepted.

**Independent test**: A valid synthetic recording is promoted from quarantine to accepted after all inspection stages. A malformed response, scanner finding/unavailability, or verifier timeout is rejected and creates neither a `Call` nor a processing task.

- [X] T015 [P] [US4] Write inspection security tests in `tests/test_recording_ingestion_security.py`
  1. Cover allowlisted URL validation, redirect escape rejection, content-type spoofing, unsafe filename handling, empty/oversize stream cleanup, and no accepted-file creation on failure.
  2. Cover scanner clean/finding/error/timeout and media verifier pass/failure/timeout with assertions that no Celery handoff occurs.

- [X] T016 [US4] Implement guest-local storage and atomic movement helpers in `app/services/recording_ingestion.py`
  1. Create and validate separate quarantine, accepted, rejected, and state paths under the configured guest root with restrictive permissions.
  2. Stream only to a temporary quarantine file; atomically move a file only between expected same-filesystem locations and sanitize all source filenames.

- [X] T017 [US4] Implement byte-signature validation in `app/services/recording_ingestion.py`
  1. Allow only the approved WAV, MP3, OGG, FLAC, M4A, and WebM signatures that match configured supported types; do not trust the suffix or HTTP header alone.
  2. Return a safe rejection category and retain only type/size/hash evidence in attempt records.

- [X] T018 [US4] Implement the antimalware adapter in `app/services/recording_ingestion.py`
  1. Invoke the approved guest scanner through a constrained, timeout-bound interface and normalize clean, finding, unavailable, and timeout results.
  2. Fail closed on any non-clean outcome, record only the sanitized result/tool version, and move the file to rejected storage.

- [X] T019 [US4] Implement bounded media verification in `app/services/recording_ingestion.py`
  1. Run `ffprobe` as a non-root, no-network child/container with explicit CPU, memory, output, and time limits.
  2. Require an approved audio stream and nonzero duration; handle parser errors, timeout, and unexpected output as rejected outcomes.

- [X] T020 [US4] Implement the quarantine inspection state machine in `app/services/recording_ingestion.py`
  1. Persist a separate attempt for signature, malware scan, and media verification, and make `accepted` reachable only when all are passed.
  2. Compute SHA-256 during streaming, save sanitized inspection evidence, atomically promote passing files, and prevent retry automation for a security rejection.

- [X] T021 [US4] Enforce least-privilege mounts and process restrictions in `docker-compose.prod.yml` and `Dockerfile`
  1. Add distinct guest volumes so API has no quarantine mount, downloader cannot write the accepted directory directly, and inspection has no general network access.
  2. Run ingestion/inspection as non-root, use read-only container filesystems where possible, drop unneeded capabilities, and set resource limits.

- [X] T022 [US4] Restrict transcript-driven behavior in `app/worker.py` and `app/services/transcription.py`
  1. Treat transcript and source metadata as untrusted strings, not workflow instructions; prohibit shell, browser, URL-fetch, and external-action selection from their values.
  2. Validate evaluation output against fixed application schemas before persistence and add regression tests for spoken prompt-injection text.

- [X] T023 [US4] Verify VM isolation controls against `docs/vm-ingestion-runbook.md` and `deploy/ingestion-vm/bootstrap.sh`
  1. Verify NAT/default-deny inbound, egress allowlist, no host drive mounts, no shared folders, no clipboard/drag-drop/USB integration, and non-root service ownership.
  2. Record the baseline snapshot ID and the validation date without storing production secrets in the repository.

**Checkpoint**: Accepted storage and processing are unreachable to an uninspected recording; the VM is ready for a source integration.

---

## Phase 4: User Story 1 — Ingest New Call Recordings (Priority: P1) 🎯 MVP

**Goal**: Read the configured private sheet, download new recordings once, retain source details, inspect them, create a call, and queue the existing processor exactly once.

**Independent test**: A mocked sheet with valid, duplicate, invalid, and inaccessible rows creates one accepted `Call` per valid new row, continues after individual failures, and enqueues each successful call once.

- [X] T024 [P] [US1] Write source-reader and row-mapping tests in `tests/test_recording_ingestion_service.py`
  1. Cover required columns, field preservation, `CRDTS`-first source keys, fallback identity, agent `CODE` mapping, ambiguous names, and active campaign preflight.
  2. Verify raw URLs and credentials are absent from expected errors and test output.

- [X] T025 [US1] Implement the private Google Sheet reader in `app/services/recording_ingestion.py`
  1. Authenticate with the read-only service-account file, read only the configured worksheet/range, and normalize headers and row numbers deterministically.
  2. Validate the exact source fields required by FR-002 and return per-row validation errors without modifying the source sheet.

- [X] T026 [US1] Implement source identity and metadata retention in `app/services/recording_ingestion.py`
  1. Prefer `CRDTS` with a source namespace; otherwise derive the documented normalized fallback key and fingerprint the recording URL without logging it.
  2. Preserve DATE, CODE, CRDTS, NAME, CALL LINK, SCORE, WEAKNESS, and extra feedback fields in protected source payload storage.

- [X] T027 [US1] Implement agent and campaign resolution in `app/services/recording_ingestion.py`
  1. Resolve `CODE` to `Employee.employee_code`, allow a unique normalized NAME fallback only when unambiguous, and reject unknown mappings safely.
  2. Validate the configured active campaign before downloading any row and report mapping errors per record.

- [X] T028 [US1] Implement safe recording retrieval in `app/services/recording_ingestion.py`
  1. Allow HTTPS only, validate every redirect destination, enforce request/stream/size limits, and reject empty/non-audio responses before quarantine finalization.
  2. Reuse the existing safe behaviors in `scripts/download_call_recordings.py` only after preserving its standalone CLI tests and filename behavior.

- [X] T029 [US1] Implement durable duplicate claims and lifecycle transitions in `app/services/recording_ingestion.py`
  1. Claim an ingestion record transactionally by source key and URL fingerprint so overlapping scheduled/manual runs cannot download or queue the same call twice.
  2. Classify unchanged submitted rows as duplicate and changed submitted links as `requires_review`, not an automatic second call.

- [X] T030 [US1] Implement the ingestion-run orchestrator in `app/services/recording_ingestion.py`
  1. Create a run, read rows, continue after per-row failure, use bounded parallel downloads, call the US4 inspection pipeline, and write sanitized counts.
  2. Preserve one non-terminal run per source and always close the run as completed, completed-with-errors, or failed with UTC timestamps.

- [X] T031 [US1] Implement accepted-file call creation and handoff in `app/services/recording_ingestion.py` and `app/worker.py`
  1. Create one `Call` only after the inspection status is accepted, retain source linkage, and set a stable storage reference without exposing the external URL.
  2. Queue `process_call_audio_task` only after commit; reconcile a committed call with no queued timestamp using the same call ID.

- [X] T032 [US1] Add Celery ingestion tasks and opt-in schedule execution in `app/worker.py`
  1. Add run, record-retry, and reconciliation tasks to the ingestion queue and use the configured interval only when ingestion is enabled.
  2. Ensure the API process and GPU worker never perform network downloads or source reads.

- [X] T033 [US1] Preserve the transitional standalone downloader in `scripts/download_call_recordings.py` and `tests/test_download_call_recordings.py`
  1. Keep the CLI as a local migration/diagnostic tool with allowlist, atomic write, dedupe, and original-name behavior.
  2. Refactor only shared pure helpers after unit tests prove no regression; the production worker must use database state rather than its JSON manifest.

- [X] T034 [US1] Complete end-to-end ingestion tests in `tests/test_recording_ingestion_service.py` and `tests/test_recording_ingestion_worker.py`
  1. Assert valid rows become accepted calls and one queued processing task, duplicate rows create no new file/call/task, and a bad row does not stop good rows.
  2. Assert failure categories, source field retention, atomic cleanup, hash persistence, and no external HTTP/Google access during tests.

**Checkpoint**: The platform can safely ingest a private test sheet inside the VM and hand off each valid new recording exactly once.

---

## Phase 5: User Story 2 — Resolve Problem Records (Priority: P2)

**Goal**: Operators can distinguish failed records, automatically retry only recoverable problems, and explicitly retry eligible records without duplication.

**Independent test**: A mixed run exposes distinct malformed, permission, timeout, storage, scanner, and handoff outcomes; restoring a temporary failure and retrying it creates exactly one accepted call.

- [X] T035 [P] [US2] Write retry and error-taxonomy tests in `tests/test_recording_ingestion_service.py`
  1. Cover malformed input, agent/campaign mapping, access denied, timeout, rate limit, storage, scanner, media validation, and handoff failure categories.
  2. Assert retry eligibility, `next_retry_at`, backoff sequence, rejection no-retry behavior, and duplicate protection.

- [X] T036 [US2] Implement retry classification and backoff in `app/services/recording_ingestion.py`
  1. Use bounded exponential delays of 1, 5, and 15 minutes for the recoverable categories defined in [data-model.md](./data-model.md).
  2. Mark input/mapping/security rejection failures non-retryable until an authorized review/action creates a new eligible attempt.

- [X] T037 [US2] Implement manual record retry orchestration in `app/services/recording_ingestion.py` and `app/worker.py`
  1. Validate the record state, create a traceable retry run/attempt, and reuse the existing source key instead of creating a second record.
  2. Lock/reclaim work safely when a scheduled retry and manual retry arrive together.

- [X] T038 [US2] Add the authorized retry endpoint in `app/routers/recording_ingestion.py` and `app/schemas.py`
  1. Implement `POST /api/recording-ingestion/records/{record_id}/retry` from the contract with permission checks and safe eligibility errors.
  2. Return the sanitized record result only; never include a raw link, path, scanner output, or credential.

- [X] T039 [US2] Add reconciliation for interrupted handoffs in `app/services/recording_ingestion.py` and `app/worker.py`
  1. Find accepted/committed calls lacking a queued timestamp and enqueue the existing call ID exactly once.
  2. Keep scan/media failures and rejected files out of reconciliation candidates.

- [X] T040 [US2] Verify recovery behavior in `tests/test_recording_ingestion_api.py` and `tests/test_recording_ingestion_worker.py`
  1. Test authorized/unauthorized retries, transient recovery, exhausted retries, same-ID handoff reconciliation, and no duplicate Call creation.
  2. Assert all returned/logged errors remain sanitized.

**Checkpoint**: Recoverable operational failures can recover automatically or through controlled retry, while unsafe content never bypasses inspection.

---

## Phase 6: User Story 3 — Audit Ingestion Activity (Priority: P3)

**Goal**: Administrators can reconcile runs and records through authenticated, sanitized API responses and audit events.

**Independent test**: An authorized operator can list a mixed run and see correct counts/statuses and trace a submitted record to its call; unauthorized users and normal status responses reveal no sensitive source or storage data.

- [X] T041 [P] [US3] Write API contract tests in `tests/test_recording_ingestion_api.py`
  1. Cover manual run request, run list/detail, paginated records, inspection summary, retry, authorization, conflict, and not-found responses.
  2. Assert the implementation conforms to `specs/001-call-recording-ingestion/contracts/recording-ingestion.openapi.yaml` and masks sensitive data.

- [X] T042 [US3] Implement ingestion operations endpoints in `app/routers/recording_ingestion.py`
  1. Implement authenticated manual-run, list, detail, and retry endpoints with bounded pagination and the `calls.ingestion.manage` permission.
  2. Return lifecycle totals, source reference, safe failure category, safe inspection summary, timestamps, and `call_id` only.

- [X] T043 [US3] Register the ingestion router in `app/main.py`
  1. Include the router under `/api/recording-ingestion` using the existing exception/authentication middleware.
  2. Confirm API startup does not read the source sheet or create a schedule unless explicitly enabled.

- [X] T044 [US3] Add sanitized audit and operational events in `app/services/recording_ingestion.py` and the repository audit service`
  1. Emit events for manual start, retry, record rejection, accepted storage, handoff, and reconciliation with actor/run/record IDs and safe outcome fields.
  2. Exclude raw URLs, tokens, filenames when sensitive, absolute paths, audio bytes, raw scanner output, and transcripts.

- [X] T045 [US3] Add run-result and secrecy regression tests in `tests/test_recording_ingestion_api.py`
  1. Test mixed-run counts, record traceability, pagination, conflict handling, and update timestamps.
  2. Serialize all response/error/audit payloads in tests and assert protected values cannot be found.

**Checkpoint**: Operations users can reconcile the ingestion system without gaining access to sensitive recording data.

---

## Phase 7: Production Readiness and Cross-Cutting Validation

**Purpose**: Complete deployment, security, quality, and performance gates across all user stories before enabling scheduled production ingestion.

- [X] T046 [P] Update production Compose topology in `docker-compose.prod.yml`
  1. Add separate API, ingestion worker, scheduler, inspection/scanner, and GPU worker service definitions with least-privilege volume and network access.
  2. Expose only the approved management port on the guest, add health checks, and prevent host bind mounts for all recording volumes.

- [X] T047 [P] Document the guest deployment and scheduler in `README.md`, `docs/vm-ingestion-runbook.md`, and `specs/001-call-recording-ingestion/quickstart.md`
  1. Document first deployment, migrations, secret placement, scanner updates, enabling/disabling the schedule, backup/restore, retention, and credential rotation.
  2. Include the exact validation sequence and rollback action without putting real sheet IDs, links, or credentials into docs.

- [X] T048 Add deployment configuration validation in `app/config.py` and tests in `tests/test_recording_ingestion_security.py`
  1. Fail production startup if safe guest paths, scanner health, required secrets, source host allowlist, or VM-only storage configuration are missing.
  2. Verify development mode remains usable with mocked storage/scanner and production mode never silently falls back to host/default uploads.

- [X] T049 Run database and contract verification using `alembic`, `tests/test_recording_ingestion_api.py`, and `specs/001-call-recording-ingestion/contracts/recording-ingestion.openapi.yaml`
  1. Test a clean migration upgrade/downgrade and API contract parsing in an isolated database.
  2. Confirm no migration or test reads the real Google Sheet, uses dialer credentials, or contacts an external recording host.

- [X] T050 Execute the 100-record performance test in `tests/test_recording_ingestion_worker.py`
  1. Use mocked reachable recordings and four bounded downloads to verify the 15-minute target without occupying the GPU worker.
  2. Record queue depth, rejection counts, processing handoff count, memory bound, and cleanup behavior as test assertions or documented metrics.

- [X] T051 Execute the VM isolation acceptance checklist in `docs/vm-ingestion-runbook.md`
  1. Verify no shared folders/host mounts/clipboard/drag-and-drop/USB, NAT/default-deny inbound, restricted egress, non-root services, and scanner/update health.
  2. Verify a rejected fixture cannot appear on the Windows host, in accepted storage, in a `Call`, or on a processing queue.

- [X] T052 Run the complete regression suite and record the release evidence in `docs/vm-ingestion-runbook.md`
  1. Run the targeted ingestion tests, existing audio pipeline tests, and relevant frontend/API tests from the guest environment.
  2. Record versions, migration revision, VM baseline snapshot, scanner version, test date, and approval; keep all credentials and raw recordings out of the evidence.

**Final checkpoint**: Enable `CALL_INGEST_ENABLED=true` only after all release gates in [plan.md](./plan.md) and [quickstart.md](./quickstart.md) pass inside the dedicated VM.

---

## Dependencies and Execution Order

```text
Phase 1: Decisions and VM baseline
    ↓
Phase 2: Shared configuration, schema, permissions, queue, fixtures
    ↓
Phase 3: US4 security containment (required gate)
    ↓
Phase 4: US1 safe source ingestion (MVP)
    ↓
Phase 5: US2 recovery and retries
    ↓
Phase 6: US3 operations and audit
    ↓
Phase 7: Production validation and enablement
```

### User story dependencies

- **US4 (containment)** must finish before **US1**, because no raw audio may enter normal storage or processing before the security gate exists.
- **US1 (new ingestion)** is the MVP and requires Phase 2 plus US4.
- **US2 (recovery)** depends on the US1 lifecycle and database record.
- **US3 (audit)** can begin after Phase 2 but is completed after US1/US2 so all final lifecycle states are represented.

### Parallel work opportunities

- T003, T004, and T005 can proceed in parallel after T001/T002 decisions.
- T007 and T014 can proceed in parallel with T008–T013 where they do not edit the same file.
- T015 security tests can be prepared while T016–T019 are implemented in separate modules/helpers.
- T024 source-reader tests can be prepared while security containment is being finalized; execution still waits for US4.
- T035 and T041 test design can begin when the Phase 2 schemas/contracts are stable.
- T046 and T047 are parallel cross-cutting documentation/deployment tasks after the service boundaries are implemented.

## Implementation Strategy

### Safe MVP

1. Complete Phase 1 and Phase 2.
2. Complete US4; stop if the VM, scanner, or inspection tests do not pass.
3. Complete US1 and run its independent test with synthetic fixtures.
4. Demonstrate one manual ingestion in the guest VM before adding automatic retries or enabling the hourly schedule.

### Incremental delivery

1. Ship the contained manual ingestion MVP (US4 + US1).
2. Add recoverable retries and reconciliation (US2).
3. Add operator controls and audit visibility (US3).
4. Complete production validation, then enable the schedule in the VM.

## Coverage Map

| Requirement area | Primary tasks |
| --- | --- |
| FR-001 to FR-006: source, dedupe, storage, handoff | T024–T034 |
| FR-007 to FR-014: lifecycle, retry, audit, safe status | T008–T013, T035–T045 |
| FR-015 to FR-020: VM isolation, inspection, least privilege, untrusted content | T001–T005, T015–T023, T046–T052 |
| SC-001 to SC-006: throughput, no duplicates, visible outcomes | T029–T034, T035–T045, T050 |
| SC-007 to SC-008: accepted-only processing and host isolation | T015–T023, T048, T051 |
