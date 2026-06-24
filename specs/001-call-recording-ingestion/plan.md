# Implementation Plan: Automated Call Recording Ingestion

**Branch**: No active Git branch | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-call-recording-ingestion/spec.md`

## Summary

Add a reliable, auditable, and contained path from the `VICDI_TESTS` Google Sheet to the existing call-analysis pipeline. A read-only Google service account will read the configured worksheet; a dedicated Celery ingestion queue running inside a dedicated VM will validate and download recording links in bounded parallelism. Every completed file stays in quarantine until file-signature validation, malware scanning, and bounded media verification succeed. New database records will enforce idempotency, retain source metadata, and track every attempt. Only then will the platform create the existing `Call` record and enqueue the existing `process_call_audio_task` pipeline inside the same VM boundary.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: FastAPI 0.115, SQLAlchemy 2, Alembic, Celery 5.4, Redis 5, HTTPX 0.27; add the Google Sheets Python client and Google authentication library for read-only service-account access. Add ClamAV/`clamd` (or the Windows Defender equivalent only when the guest is Windows) and FFmpeg/`ffprobe` for isolated inspection.

**Storage**: PostgreSQL in production (SQLite only for isolated development/tests), Redis task broker, and VM-local persistent audio storage with separate `quarantine`, `accepted`, and `rejected` directories. The API, ingestion worker, and GPU worker run within the same VM and may mount the accepted volume; the host workstation must not mount any recording volume.

**Testing**: pytest with the existing in-memory SQLite fixture, mocked Google Sheet reader and HTTP download transport, plus targeted API and worker integration tests. No test reads the production sheet or Dial Fusion recordings.

**Target Platform**: Windows primary workstation hosting a dedicated Linux VM (Ubuntu Server LTS) on Hyper-V where available, or VirtualBox when Hyper-V is unavailable. The current containerized FastAPI deployment, PostgreSQL, Redis, ingestion worker, scheduler, and GPU worker run inside the guest. The host accesses operations UI only through a host-only/local port route, never a shared recording folder.

**Project Type**: Web application with FastAPI backend and React frontend. Version 1 adds an authenticated backend operations API; no new frontend screen is required to satisfy the feature.

**Performance Goals**: Process a normal batch of 100 reachable recordings within 15 minutes; use four bounded concurrent downloads by default; do not block the GPU worker while reading a sheet or downloading audio.

**Constraints**: The VM has NAT networking, no dialer-initiated inbound access, no shared clipboard, drag-and-drop, USB passthrough, or host-drive mounts. Guest outbound access is allowlisted to the sheet source, recording hosts, approved DNS/NTP/update services, and any explicitly approved processing endpoint. Only HTTPS recording links from configured allowlisted hosts are accepted; maximum file size uses the existing upload limit; all redirects must remain allowlisted. Raw links and credentials never appear in API responses, audit text, or logs. The initial source is accessed through a least-privilege service account, not a published-to-web export. Inspection is fail-closed and each parser runs non-root with no network and CPU, memory, and time limits.

**Scale/Scope**: One configured Google worksheet (`VICDI_TESTS`, first worksheet) initially, a scheduled run every 15 minutes when enabled, and one active run per source. The source adapter is isolated so CSV or additional tabular inputs can be added later without changing download, tracking, inspection, or pipeline behavior. Version 1 does not transfer raw recordings from the VM to the host; it exposes authenticated, sanitized status and analysis results only.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The repository constitution is an unfilled template and therefore contains no enforceable project-specific principles or gates. This plan passes provisionally and applies the repository's observable practices instead: Alembic-managed production schema changes, RBAC on operational endpoints, durable audit records, isolated tests, no secrets in source control, and a VM boundary for untrusted audio.

**Post-design re-check**: Pass. The design uses the established FastAPI, SQLAlchemy, Celery, Redis, audit, and permission patterns. It adds one bounded source adapter, inspection lifecycle evidence, and a dedicated VM deployment boundary; no unrelated frontend or dialer integration is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/001-call-recording-ingestion/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
app/
├── config.py                         # Ingestion settings and validation
├── models.py                         # Ingestion run/record/attempt models and Call relationship
├── schemas.py                        # API request and safe response models
├── worker.py                         # Celery routes, Beat schedule, ingestion tasks, call handoff
├── routers/
│   └── recording_ingestion.py        # Admin-only run, status, and retry endpoints
└── services/
    └── recording_ingestion.py        # Sheet reader, row mapping, safe downloader, state transitions

alembic/versions/
└── <revision>_add_recording_ingestion.py

tests/
├── test_recording_ingestion_service.py
├── test_recording_ingestion_api.py
├── test_recording_ingestion_worker.py
└── test_recording_ingestion_security.py

requirements.txt                      # Google Sheets/auth dependencies
.env.example                          # Non-secret ingestion configuration examples
docker-compose.prod.yml               # Shared audio volume, ingestion worker, and scheduler
run_platform.bat                      # Local ingestion worker and scheduler launch commands
```

**Structure Decision**: Keep the feature backend-first. The existing `Call` model and `process_call_audio_task` remain the processing boundary but both run inside the VM. A dedicated ingestion service owns external input, quarantine, inspection, persistent tracking, and safe downloads. Operational visibility is exposed through authenticated API responses and audit events before any optional React dashboard is considered. The VM is the main boundary; an unprivileged no-network media-inspection container is a second boundary rather than a replacement for the VM.

## Complexity Tracking

No constitution violations or extra architectural layers require justification. The separate ingestion Celery queue is necessary to keep network-bound downloads from delaying the existing single-process GPU worker.

## VM Addition Implementation Sequence

1. **Provision the boundary**: Create a dedicated Ubuntu Server LTS VM with Hyper-V NAT (VirtualBox NAT only when Hyper-V is unavailable), a non-root service account, encrypted guest storage, default-deny inbound firewall, and no host integration features. Snapshot this clean baseline before adding credentials.
2. **Deploy the platform inside the guest**: Move the existing Compose deployment, PostgreSQL, Redis, API, CPU ingestion worker, scheduler, and GPU worker into the VM. Expose the operations UI/API only through a host-only or local management route. Do not mount `D:\voic call rating`, `uploads`, or any host drive into the guest.
3. **Partition guest storage**: Add VM-local `quarantine`, `accepted`, `rejected`, and `state` paths. Give each service the minimum volume access: the API gets no quarantine mount; the downloader cannot write directly to accepted storage; the processing worker consumes accepted files only.
4. **Add fail-closed inspection**: Extend the downloader to write to quarantine, validate real audio signatures, scan with the selected guest antimalware engine, and run resource-bounded `ffprobe` verification in a non-root, no-network inspection process. Record hashes and sanitized evidence. Atomically promote only passing files to accepted storage.
5. **Contain processing and content**: Keep transcription and evaluation in the guest. Treat all text as untrusted content, require fixed schema output, and remove tool, shell, browser, URL-fetch, and state-changing capabilities from transcript-driven steps.
6. **Enforce and test networking**: Permit guest egress only for approved source, recording, resolver/NTP/update, and internal-result endpoints. Test blocked redirect hosts, oversized files, malformed audio, scanner unavailability, parser timeout, and an attempted host-share path.
7. **Operationalize**: Document guest patching, credential rotation, VM snapshot/restore, rejected-file retention, alert handling, and the safe emergency action: disable the guest scheduler first, never investigate a suspicious file by copying it to the Windows host.

## Release Gates for This Addition

- The VM has no shared recording directory, host drive mount, enhanced clipboard, drag-and-drop, or USB passthrough.
- The dialer cannot initiate a connection to the guest or host; all retrieval is guest-initiated and allowlisted.
- The VM rejects files when scanning or verification is unavailable; accepted storage and processing contain only fully inspected files.
- A valid recording completes one end-to-end ingestion and transcription run inside the guest, while malformed and rejected fixtures never create a `Call` or processing task.
- Operations can see sanitized inspection status and hashes without seeing raw links, raw scanner logs, or guest filesystem paths.
