# Feature Specification: Automated Call Recording Ingestion

**Feature Branch**: `[001-call-recording-ingestion]`  
**Created**: 2026-06-22  
**Status**: Draft  
**Input**: User description: "Automatically ingest call records from a spreadsheet or CSV, download each recording once, track outcomes, and send successfully acquired recordings to the internal processing pipeline."

## Source Context

The initial source is the shared `VICDI_TESTS` Google Sheet, on its first worksheet. Its confirmed fields are:

| Source field | Ingestion use |
| --- | --- |
| `DATE` | Call date |
| `CODE` | Source metadata retained with the call record |
| `CRDTS` | Source record reference retained for tracing and duplicate recognition |
| `NAME` | Agent name |
| `CALL LINK` | Recording link to retrieve |
| `SCORE` | Existing call score |
| `WEAKNESS` and subsequent quality-feedback fields | Quality notes retained with the call record |

The provided recording links point to the Dial Fusion archive domain. The implementation must verify that the configured service has authorized retrieval access before processing production data.

## Security Isolation Addition

Recording links, audio bytes, filenames, and all transcribed speech are untrusted external input. The ingestion and audio-processing runtime MUST run inside a dedicated virtual machine (VM), not on the user's primary Windows workstation. The VM is the primary containment boundary; containers inside it provide a second boundary for individual download, inspection, and transcription processes.

The host workstation may receive authenticated, structured operational results and transcript/evaluation data, but it must not mount the VM's recording directories or receive raw recordings through a shared folder. The implementation must fail closed when malware scanning or audio verification cannot run.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest New Call Recordings (Priority: P1)

An operations user provides a call-record source containing call details and recording links. The system identifies new valid recordings, obtains them, retains their associated call details, and makes them available to the internal analysis workflow without manual downloads.

**Why this priority**: This is the primary business value: converting a manual spreadsheet process into a reliable stream of recordings ready for analysis.

**Independent Test**: Provide a small source containing previously unprocessed records with accessible recording links and confirm that each recording is available to the analysis workflow with the matching call details.

**Acceptance Scenarios**:

1. **Given** a source record with all required call details and an accessible recording link that has not been processed, **When** ingestion runs, **Then** the recording is saved, its source details are retained, and it is submitted once to the processing workflow.
2. **Given** a source containing several new valid recording links, **When** ingestion runs, **Then** every reachable recording is processed independently and a summary identifies the result for each source record.
3. **Given** a successfully processed source record appears again in a later ingestion run, **When** the record is evaluated, **Then** no second copy is saved and no second processing request is created.

---

### User Story 2 - Resolve Problem Records (Priority: P2)

An operations user can identify records whose recording could not be obtained, understand why, and have recoverable records retried after the underlying issue is resolved.

**Why this priority**: Recording links can be missing, invalid, expired, or temporarily unavailable. Clear recovery prevents silent data loss and keeps manual intervention focused.

**Independent Test**: Provide records with a missing link, an invalid link, and a temporarily inaccessible link; confirm that each is recorded with a distinct outcome while valid records in the same run continue to be processed.

**Acceptance Scenarios**:

1. **Given** a source record with a missing or malformed recording link, **When** ingestion runs, **Then** the record is not sent for processing and is marked with an actionable validation failure.
2. **Given** a recording link that is temporarily unavailable, **When** a retrieval attempt fails, **Then** the outcome is tracked as recoverable and the record can be retried without creating duplicate processing work.
3. **Given** one invalid record and other valid records in the same source, **When** ingestion runs, **Then** the invalid record does not stop the valid records from being processed.

---

### User Story 3 - Audit Ingestion Activity (Priority: P3)

An operations user can review each ingestion run and determine which source records were processed, skipped as duplicates, failed, or are awaiting further action.

**Why this priority**: An auditable history establishes trust in automation and makes it possible to reconcile spreadsheet records with the analysis workflow.

**Independent Test**: Run ingestion against a source containing new, duplicate, and invalid records, then confirm that the run history shows the disposition and relevant timestamps for every record.

**Acceptance Scenarios**:

1. **Given** a completed ingestion run, **When** an operations user reviews its results, **Then** they can see totals and per-record status for new, duplicate, successful, failed, and retryable records.
2. **Given** a recording has been sent to the processing workflow, **When** its source record is reviewed, **Then** the user can trace it from the source record through saved recording to processing handoff.

---

### User Story 4 - Contain and Inspect Untrusted Recordings (Priority: P1)

An administrator can operate ingestion and transcription in a dedicated VM so that an untrusted recording, malformed media file, or malicious instruction spoken in a call cannot gain access to the primary workstation or cause the platform to perform unintended actions.

**Why this priority**: Audio comes from an external dialer and must be treated as untrusted before any decoder or AI component reads it.

**Independent Test**: Configure an allowed test source with a valid recording and a malformed non-audio response. Confirm that the valid recording passes quarantine, scanning, and media verification before processing, while the malformed response is rejected without a file reaching the accepted audio directory or processing queue.

**Acceptance Scenarios**:

1. **Given** a newly downloaded recording, **When** ingestion finishes downloading it, **Then** the file is placed in a quarantine directory and cannot be read by the transcription worker until it passes all required inspection stages.
2. **Given** a scanner finding, scanner outage, unsupported media signature, or invalid media parse, **When** inspection runs, **Then** the file is rejected, its reason is safely recorded, and no processing handoff is created.
3. **Given** speech or transcription text that contains an instruction, **When** the analysis pipeline evaluates it, **Then** it is treated as call content only and cannot invoke tools, open links, execute commands, or change platform instructions.

### Edge Cases

- A row has no recording link, no call date, or no agent name.
- A recording link requires access the ingestion service does not have, has expired, redirects unexpectedly, or returns non-audio content.
- A download is interrupted, incomplete, empty, or cannot be stored.
- The same source row, recording link, or a re-export of the same source is presented more than once, including while a prior run is still in progress.
- A recording is saved successfully but its processing handoff is temporarily unavailable.
- The source contains mixed valid and invalid rows, duplicate rows, or a changed recording link for a previously seen call.
- The scanner is unavailable, returns an error, or finds malicious content; the record must remain rejected rather than bypassing inspection.
- The response claims to be audio but its byte signature or media parser does not match an approved audio type.
- A recording or transcript attempts to induce the platform to execute an instruction; it must remain untrusted content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read the initial `VICDI_TESTS` Google Sheet or an approved export of it, as well as future configured tabular call-record sources, without requiring direct access to the dialer platform.
- **FR-002**: The system MUST retain the source `DATE`, `CODE`, `CRDTS`, `NAME`, `CALL LINK`, `SCORE`, `WEAKNESS`, and available subsequent quality-feedback fields for every evaluated row.
- **FR-003**: The system MUST validate that each row contains the required source information and a usable recording link before attempting retrieval.
- **FR-004**: The system MUST determine whether a source recording has already been successfully saved or handed to processing before starting new work for it.
- **FR-005**: The system MUST save each newly obtained recording in an approved storage location and associate it with the retained source details.
- **FR-006**: The system MUST submit a recording to the internal processing workflow only after it has been saved successfully and MUST prevent duplicate submissions for the same source recording.
- **FR-007**: The system MUST preserve a per-record lifecycle status covering at least pending, in progress, saved, submitted, duplicate, failed, and retryable outcomes.
- **FR-008**: The system MUST record the time, reason category, and relevant error detail for every failed retrieval, storage, validation, or processing-handoff attempt.
- **FR-009**: The system MUST continue evaluating other source records when an individual record fails.
- **FR-010**: The system MUST retry recoverable failures according to the configured operational policy and allow a previously failed record to be re-evaluated without duplicating successful work.
- **FR-011**: The system MUST create an auditable ingestion-run history with source identity, start and completion times, totals by outcome, and per-record results.
- **FR-012**: The system MUST make the retained call details available to the internal processing workflow together with the recording reference.
- **FR-013**: The system MUST avoid exposing recording contents, access credentials, or sensitive links in routine operator-facing status and error details.
- **FR-014**: The system MUST report a clear completion summary that distinguishes successful, duplicate, failed, and retryable records.
- **FR-015**: The system MUST run the downloader, file inspection, and audio processing on a dedicated VM with no host-drive mounts, shared recording folders, clipboard/drag-and-drop integration, or inbound connectivity from the dialer.
- **FR-016**: The system MUST place each complete download in quarantine and require file-signature validation, malware scanning, and bounded audio verification before moving it to accepted storage or handing it to processing.
- **FR-017**: The system MUST reject rather than process a file when a required inspection stage is unavailable, times out, exceeds resource limits, or returns a failure.
- **FR-018**: The system MUST enforce least-privilege execution: the ingestion and media-inspection processes run without administrator privileges, with no access to host data, and with outbound network access limited to explicitly approved destinations.
- **FR-019**: The system MUST treat source metadata, audio, and transcripts as untrusted data. No transcript-derived value may invoke tools, shell commands, URLs, or state-changing actions.
- **FR-020**: The system MUST retain a sanitized inspection result, content hash, tool version, and timestamps for every accepted or rejected recording without exposing raw audio, full links, credentials, or scanner output in routine status responses.

### Key Entities

- **Source Call Record**: One row from the configured source, including the call details, recording link, and available source identifier.
- **Recording Asset**: The saved audio recording associated with a source call record and its storage reference.
- **Ingestion Record**: The durable lifecycle history for one source recording, including duplicate decision, attempts, status, and failure reason when relevant.
- **Ingestion Run**: One execution that evaluates a source and summarizes its individual ingestion records and outcomes.
- **Processing Handoff**: The tracked delivery of a saved recording and its call details to the internal analysis workflow.
- **Recording Inspection**: The immutable result of signature validation, malware scan, and media verification for a quarantined file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a normal run of 100 source rows with reachable valid recordings, at least 99 recordings are saved and submitted to processing without manual download work.
- **SC-002**: Re-running an unchanged source produces no additional stored recordings or processing submissions for records that were already successfully submitted.
- **SC-003**: Every evaluated source row has a visible final or in-progress status and can be traced to its latest attempt within five minutes of that attempt completing.
- **SC-004**: A source containing invalid or inaccessible links still processes all other reachable valid recordings in that run.
- **SC-005**: Every failed record provides enough categorized information for an operations user to distinguish input correction, access, retrieval, storage, and processing-handoff issues.
- **SC-006**: An operations user can reconcile a completed source of 100 rows against the ingestion results in under 10 minutes.
- **SC-007**: No recording reaches the accepted storage directory or processing queue unless all required inspection stages succeed.
- **SC-008**: The host workstation has no VM recording-directory mount and the dialer has no inbound route to the VM or host.

## Assumptions

- Authorized users provide a source that can be read by the platform and, where necessary, provide the access required to retrieve its recording links.
- The first worksheet of the shared `VICDI_TESTS` Google Sheet is the initial ingestion source; its `CRDTS` value is assumed to be a stable source-record reference unless validation shows otherwise.
- Initial scope is limited to audio recordings represented by links in a tabular source; direct dialer integration, transcription, scoring, and analytics are outside this feature.
- The internal processing workflow already accepts a recording reference and the associated call details.
- An approved storage destination and retention policy for recordings already exist or will be selected as part of implementation planning.
- A stable source-record identifier is used when supplied; otherwise, the system uses the source details and recording link to recognize the same recording across repeated runs.
- Operators may correct source data or restore access before retrying failed records; the ingestion process does not alter the original spreadsheet or CSV.
