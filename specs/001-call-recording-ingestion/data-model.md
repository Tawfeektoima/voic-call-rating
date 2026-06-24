# Data Model: Automated Call Recording Ingestion

## Existing entities used

### Employee

`Employee.employee_code` is the primary mapping target for source `CODE`. A normalized source `NAME` may only be used if it resolves to exactly one employee. An unknown or ambiguous agent is a per-row validation failure.

### Campaign

Every imported `Call` requires an existing active campaign. Version 1 uses `CALL_INGEST_DEFAULT_CAMPAIGN_ID`; a missing, inactive, or invalid configured campaign fails the run preflight before downloads begin.

### Call

The existing `Call` record remains the pipeline contract. An imported call uses `source="sheet_ingestion"`, its atomically stored file path, mapped employee and campaign, and the existing `PENDING` status before `process_call_audio_task` is queued. Imported source score and notes remain in the ingestion record rather than overwriting AI-generated `evaluation_score` or `weaknesses`.

## New entities

### RecordingIngestionRun

Represents one scheduled, manual, retry, or reconciliation execution.

| Field | Rules |
| --- | --- |
| `id` | Primary key. |
| `source_name` | Stable configured source identifier, initially `vicdi_tests`. |
| `trigger` | `scheduled`, `manual`, `retry`, or `reconciliation`. |
| `status` | `requested`, `reading_source`, `processing`, `completed`, `completed_with_errors`, or `failed`. |
| `requested_by_employee_id` | Nullable FK for a manual/retry actor; null for scheduler. |
| `started_at`, `completed_at` | UTC timestamps. |
| `rows_seen`, `new_count`, `duplicate_count`, `success_count`, `failed_count`, `retryable_count` | Non-negative reconciliation totals. |
| `failure_summary` | Sanitized run-level error only; no raw URLs or credentials. |

Only one non-terminal run is permitted for a source. This is enforced before the worker begins, using a database constraint/transactional claim rather than an in-memory lock.

### RecordingIngestionRecord

Represents the current durable state for one source call record.

| Field | Rules |
| --- | --- |
| `id` | Primary key. |
| `source_name`, `source_key` | Unique pair. `source_key` is derived from `CRDTS` or the documented fallback identity. |
| `source_row_number` | Original one-based row position for reconciliation. |
| `source_payload` | JSON containing the preserved source fields (`DATE`, `CODE`, `CRDTS`, `NAME`, `CALL LINK`, `SCORE`, `WEAKNESS`, and remaining feedback fields). It is never returned verbatim to routine status clients. |
| `recording_url` | Protected retrieval input; omitted from logs and API responses. |
| `recording_url_fingerprint` | Non-reversible digest used for duplicate decisions and safe diagnostics. |
| `source_call_date` | Parsed source calendar date when valid; raw original value remains in `source_payload`. |
| `source_score`, `source_quality_notes` | Optional preserved upstream score and feedback. |
| `employee_id`, `campaign_id` | Resolved target FKs once validation succeeds. |
| `status` | Current ingestion lifecycle state. |
| `attempt_count`, `next_retry_at` | Retry control. |
| `quarantine_file_path` | Guest-local transient path set after a complete download; never exposed to host-facing APIs. |
| `stored_file_path`, `content_type`, `byte_size`, `file_sha256` | Set only after all inspection stages pass and the file is atomically moved to accepted storage. |
| `signature_status`, `malware_scan_status`, `media_verification_status` | `pending`, `passed`, `rejected`, or `unavailable`; accepted storage requires all three to be `passed`. |
| `scanner_name`, `scanner_version`, `inspection_completed_at` | Required evidence for an accepted or rejected file; scanner output itself is not retained in routine records. |
| `call_id` | Nullable unique FK to `Call`; set before pipeline handoff. |
| `pipeline_queued_at` | Set after the existing call task has been requested. |
| `last_error_category`, `last_error_detail` | Sanitized diagnostic fields. |
| `created_at`, `updated_at`, `completed_at` | UTC lifecycle timestamps. |

Indexes support `(source_name, status, next_retry_at)`, `employee_id`, `call_id`, and run reconciliation. The record must not store plaintext credentials or full external URLs in error fields.

### RecordingIngestionAttempt

Captures every row evaluation and retrieval attempt without mutating history.

| Field | Rules |
| --- | --- |
| `id` | Primary key. |
| `ingestion_record_id`, `ingestion_run_id` | Required FKs. |
| `attempt_number` | Monotonic for one ingestion record. |
| `phase` | `validation`, `download`, `signature_check`, `malware_scan`, `media_verification`, `storage`, or `handoff`. |
| `status` | `started`, `succeeded`, `failed`, `skipped_duplicate`, or `retry_scheduled`. |
| `error_category`, `error_detail` | Sanitized when failed. |
| `started_at`, `completed_at` | UTC timestamps. |
| `http_status`, `bytes_downloaded` | Nullable operational data; no raw URL. |

The unique pair `(ingestion_record_id, attempt_number, phase)` prevents duplicate historical events from a retrying worker.

## State transitions

```text
run: requested -> reading_source -> processing -> completed | completed_with_errors | failed

record: pending -> downloading -> quarantined -> inspecting -> accepted -> handoff_pending -> submitted
                 -> rejected
                 -> failed -> retry_scheduled -> pending
        pending -> duplicate
        submitted + same URL fingerprint -> duplicate
        submitted + changed URL fingerprint -> requires_review
```

- Validation failures are `failed` and are not retried automatically until source data is corrected.
- `quarantined` files are never visible to transcription or host-facing storage; `accepted` is reached only after signature, antimalware, and media-verification attempts have all succeeded.
- A scanner failure, inspection timeout, unsupported byte signature, parser failure, or malware finding reaches `rejected`; it must not be retried automatically or queued for processing. An authorized operator may create a new review-controlled attempt after remediation.
- Network timeout, rate limit, and server failures become `retry_scheduled` with bounded exponential backoff (three automatic attempts: 1, 5, and 15 minutes).
- A changed link for a successfully submitted source record becomes `requires_review`; an authorized user explicitly retries it to prevent silently processing a replacement recording twice.
- A committed `Call` without `pipeline_queued_at` is reclaimed by reconciliation and re-enqueued with the same `call_id`, never by creating a second call.

## Relationships

```text
RecordingIngestionRun 1 --- * RecordingIngestionAttempt * --- 1 RecordingIngestionRecord
RecordingIngestionRecord 0..1 --- 1 Call
Employee 1 --- * RecordingIngestionRecord
Campaign 1 --- * RecordingIngestionRecord
```

## Trust boundaries

- Raw links, source values, downloaded bytes, filenames, and transcripts are untrusted input.
- Quarantine and accepted audio directories exist only in the VM. No model, API response, log, or host shared folder receives a raw quarantine file.
- The only trusted state transition is `accepted`, established by the inspection service. The transcription pipeline consumes accepted files as untrusted media, with no tools or command-execution capability.
