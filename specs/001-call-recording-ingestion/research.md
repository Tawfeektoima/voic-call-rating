# Research: Automated Call Recording Ingestion

## Google Sheet access

**Decision**: Read the configured `VICDI_TESTS` worksheet through the Google Sheets API using a dedicated service account with Viewer access to that specific spreadsheet.

**Rationale**: The sheet can remain private to authorized viewers, the source columns can be read deterministically, and production does not depend on a browser session or a publicly published CSV link. Credentials are supplied by a path to a mounted secret, never committed to the repository.

**Alternatives considered**:

- Anonymous Google CSV export: rejected because it requires the data to be broadly exposed and provides weaker operational control.
- Browser automation: rejected because it depends on interactive session state and cannot run reliably as a service.
- Manual CSV upload: rejected because it does not deliver automated ingestion.

## Source identity and agent mapping

**Decision**: Use `CRDTS` as the preferred external call identifier and derive a stable source key from the source name plus that value. When `CRDTS` is blank, derive a fallback key from normalized `DATE`, `CODE`, `NAME`, and `CALL LINK`. Match the source `CODE` to `Employee.employee_code`; use a unique normalized `NAME` only as a fallback. Use a configured active campaign for imported records.

**Rationale**: The sheet supplies `CRDTS`, `CODE`, and `NAME`, while the platform requires `employee_id` and `campaign_id` for every `Call`. The mapping is deterministic, avoids guessing between duplicate names, and makes unmapped rows visible failures rather than misattributed calls.

**Alternatives considered**:

- Matching only on agent name: rejected because names can be duplicated or edited.
- Creating employees or campaigns during ingestion: rejected because it expands the scope and bypasses existing HR/campaign governance.
- Using the recording URL as the only key: rejected because URLs can change and may contain sensitive tokens.

## Exactly-once delivery

**Decision**: Add a durable `RecordingIngestionRecord` with a unique source key, recording URL fingerprint, and linked `Call`; use atomic status claims and reconciliation for committed-but-not-queued calls.

**Rationale**: Database constraints protect against overlapping scheduled and manual runs. A source row is only considered a duplicate when the source key and URL fingerprint have already reached a successful handoff. If a worker crashes after committing a `Call`, reconciliation re-enqueues that same call ID; the existing call worker already guards against duplicate completed evaluation.

**Alternatives considered**:

- In-memory or spreadsheet-only duplicate tracking: rejected because it fails across restarts and concurrent workers.
- Relying solely on Celery task IDs: rejected because broker delivery does not establish source-level identity.
- Storing only an audio-file hash: rejected because it requires downloading a duplicate before it can be detected.

## Download execution and pipeline isolation

**Decision**: Route sheet ingestion to a dedicated `ingestion` Celery queue with one CPU/I/O worker and four bounded concurrent HTTP downloads per run. Route audio analysis to the existing default/GPU worker. Celery Beat creates scheduled run requests when ingestion is enabled.

**Rationale**: The current Windows launcher starts one solo GPU worker and the call pipeline frees GPU memory after each task. Network waiting must not occupy that worker. Four concurrent downloads meet the 100-record performance target without unbounded connections to Dial Fusion.

**Alternatives considered**:

- Perform downloads in the FastAPI request: rejected because requests would time out and have no durable recovery.
- Use the existing GPU worker for downloads: rejected because it delays transcription and evaluation.
- Start unlimited per-record tasks: rejected because it risks source throttling, resource exhaustion, and hard-to-reconcile partial runs.

## Recording retrieval safety

**Decision**: Accept HTTPS links only from configured hosts, validate every redirect, stream to a temporary file under the approved upload root, enforce the existing byte limit, verify non-empty allowed audio content, then atomically move into final storage.

**Rationale**: Spreadsheet URLs are external input. Host allowlisting and bounded streaming prevent server-side request forgery, oversized downloads, accidental HTML/error pages stored as audio, and partial files becoming available to the processing worker.

**Alternatives considered**:

- Trust URL suffixes: rejected because archive links may omit a useful filename and suffixes can be forged.
- Download directly to the final path: rejected because interrupted files could be processed.
- Follow arbitrary redirects: rejected because redirects can escape the approved recording host.

## VM containment and guest operating system

**Decision**: Run the complete audio-handling stack in a dedicated Ubuntu Server LTS VM. Use Hyper-V Generation 2 with NAT on supported Windows editions; use VirtualBox with NAT as the fallback. Run the existing Compose services within the guest. The host receives only authenticated UI/API responses and never mounts audio directories.

**Rationale**: A VM is a stronger isolation boundary than a Python process or container alone. NAT prevents the dialer from initiating a connection to the guest, while no shared folders, clipboard, drag-and-drop, USB passthrough, or host-drive mount prevent an audio-processing compromise from directly reaching host data. Ubuntu matches the production container base and allows predictable non-root Linux controls.

**Alternatives considered**:

- Run the downloader on the primary Windows workstation: rejected because a decoder or dependency compromise would run beside user data and credentials.
- Windows Sandbox: rejected for scheduled ingestion because it is disposable and loses scheduling, state, and retained recordings at shutdown.
- Container-only isolation on the host: rejected because a container escape would land on the primary workstation; containers remain a useful second boundary inside the VM.
- Windows guest with Defender: permitted only when an existing Windows guest license and Defender policy require it; it is not the baseline because the Linux production runtime and tools already fit the platform.

## Content inspection and safe acceptance

**Decision**: Use a fail-closed three-stage inspection pipeline: byte-signature allowlist, antimalware scan, and `ffprobe` media verification. Downloads land in `quarantine`; only a file that passes all three moves atomically to `accepted`. A rejected file is retained only according to the incident-retention policy and is never queued for transcription.

**Rationale**: HTTP headers and filenames are attacker-controlled. Signature inspection blocks obvious type confusion, antimalware adds known-threat detection, and media verification detects incomplete or malformed recordings before the transcription tool reads them. AV detection alone cannot prove safety, so parser containment and least privilege remain required.

**Alternatives considered**:

- Trust `Content-Type` and a `.mp3` extension: rejected because both can be forged.
- Scan after the analysis worker has opened the recording: rejected because the decoder would already process untrusted bytes.
- Upload recordings to a public malware scanner: rejected because call recordings may contain personal or confidential information.
- Treat a passing scanner result as a security guarantee: rejected because unknown threats and parser vulnerabilities remain possible.

## Transcript and AI trust boundary

**Decision**: Treat the raw transcript and all source metadata as untrusted data. The transcription/evaluation service receives no tool-execution capability, shell access, browser control, or credentials; downstream evaluation output is schema-validated JSON with fixed fields.

**Rationale**: A spoken or embedded instruction is content, not authority. Separating the control plane from call content prevents prompt injection from initiating external actions even if an AI evaluator follows the wording semantically.

**Alternatives considered**:

- Let an LLM decide whether to call tools based on the transcript: rejected because recorded speech is not trusted operator input.
- Add prompt filtering as the only defense: rejected because filtering is fallible and cannot replace missing permissions.

## Guest networking, secrets, and observability

**Decision**: Default-deny guest inbound traffic. Restrict guest egress to the configured Google endpoint, recording hosts, approved resolver/NTP/update endpoints, and explicit internal processing destinations. Store secrets in guest-only secret files with restrictive permissions; use a dedicated least-privilege dialer/report account. Log masked host identity, hashes, inspection outcomes, versions, and resource-limit failures, never raw URLs, credentials, raw transcripts, or scanner reports.

**Rationale**: Restricting where the guest can connect limits damage from a compromised process. Guest-local secrets and sanitized logs prevent host leakage and reduce accidental disclosure of access tokens or customer data.

**Alternatives considered**:

- Bridge the VM directly to the LAN: rejected because it makes the guest a peer reachable from other network devices.
- Allow unrestricted egress for convenience: rejected because it enables command-and-control or data exfiltration if a process is compromised.
- Store secrets in the repository or spreadsheet: rejected because both are copied, logged, and shared too easily.

## Operational access and auditability

**Decision**: Add an admin-only `calls.ingestion.manage` permission, safe status endpoints, and audit events for manual run starts and retry actions. Return status, error category, and masked host information; never return the complete recording URL or credentials.

**Rationale**: The platform already uses RBAC and append-only audit events. Ingestion control is an administrative operation, while operations users need reconciliation detail without exposing sensitive recording links.

**Alternatives considered**:

- Reuse general raw-call viewing permission: rejected because it grants a different capability and does not represent source ingestion authority.
- Write full links into audit events: rejected because links can contain private identifiers or temporary access tokens.

## Verification scope

The design was derived from the existing FastAPI/Celery/SQLAlchemy implementation, its runtime configuration, and the provided read-only sheet structure. Direct external documentation lookup was attempted but unavailable from the current environment; implementation must validate the selected Google client library against its current official documentation before dependency pinning.
