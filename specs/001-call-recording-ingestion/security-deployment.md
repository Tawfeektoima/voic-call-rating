# Security Deployment: Isolated Recording Ingestion VM

## Decision

Run all raw-audio handling within a dedicated Ubuntu Server LTS VM. Prefer Hyper-V Generation 2 with NAT on compatible Windows editions; use VirtualBox with NAT only when Hyper-V cannot be used. The VM is the primary security boundary. Docker containers inside it are a second containment layer, not the only isolation mechanism.

For version 1, do not depend on GPU passthrough inside the ingestion VM. Use CPU-only transcription inside the guest for this feature path until a supported passthrough setup has been proven and benchmarked in isolation.

## Capacity impact

- CPU-only transcription keeps the first release simple and avoids coupling the security boundary to GPU passthrough support.
- The tradeoff is lower transcription throughput than a GPU-backed worker, so queue depth should be watched during the first manual and hourly runs.
- The current fallback is to keep GPU-accelerated workflows out of the ingestion VM feature path until a later phase proves a safe passthrough configuration.

## Guest antimalware decision

Use `clamd` inside the Linux guest as the default antimalware engine for version 1.

- Result states are `clean`, `finding`, `unavailable`, and `timeout`.
- If the scanner is unavailable, times out, or returns any non-clean result, the ingestion pipeline must fail closed and move the file to rejected storage.
- The scanner definition updates are owned inside the guest maintenance process so the host never needs direct access to raw recordings.

## Trust boundary

```text
Allowed Google Sheet / VICIdial recording host
  -> guest download worker (outbound HTTPS only; quarantine write only)
  -> guest quarantine volume
  -> internal-only scanner and no-network, non-root media-verifier service
  -> guest inspection/promotion worker (no external recording-host route)
  -> guest accepted volume
  -> guest transcription/evaluation worker
  -> authenticated, structured result to the host UI/API

The Windows host never mounts or shares quarantine or accepted audio directories.
```

## VM baseline

- Guest: Ubuntu Server LTS, patched before secrets or production data are added.
- Capacity: 4 vCPU, 8 GB RAM, 80 GB encrypted persistent virtual disk; increase storage only after retention sizing.
- Networking: NAT, default-deny inbound firewall. Do not use bridged networking for the ingestion VM.
- Integration: disable shared folders, host-drive mounts, shared clipboard, drag-and-drop, USB passthrough, and public RDP/SSH exposure. Administrative SSH, if needed, is reachable only from the host/management network using a key, not a password.
- Accounts: one non-root service account owns runtime files. Docker images and packages are patched on a defined maintenance schedule. Separate service credentials are least-privilege and guest-local.
- Egress: allow only the configured Google source, approved recording hosts, approved DNS/NTP/update services, and explicitly approved internal result endpoints. No general internet access from inspection or transcription containers.

## Guest storage layout

```text
/var/lib/call-rating/
  quarantine/  # downloader and inspector only
  accepted/    # processing worker only after inspection success
  rejected/    # retention-controlled incident evidence; never processed
  state/       # database/manifest references and safe run artifacts
```

No container has every mount. The downloader has a bind mount only for `quarantine` and cannot write `accepted` or `rejected`. The inspector has the three guest-local paths needed to atomically move a completed file; it is kept off the downloader's external route and can reach only the internal scanner and media-verifier services. The API and general worker have no ingestion storage mount. The media verifier sees a read-only `quarantine` mount and has no database credentials or outbound network.

The ClamAV definition updater is a distinct service with approved update egress. The scanner daemon receives that database read-only and remains on the internal-only scanner network; it never runs `freshclam` itself.

## Inspection policy

1. Validate the URL and every redirect against the configured allowlist before download.
2. Stream to a temporary file in quarantine with request, size, and disk-space limits; atomically finalize only a complete download.
3. Validate the actual file signature against an approved audio-type allowlist.
4. Scan the quarantined file with the approved guest antimalware engine.
5. Send only the quarantined basename to the dedicated internal media-verifier service. It has a read-only quarantine mount, no external network, non-root execution, read-only runtime, CPU/memory/process limits, a wall-clock timeout, and a hard bounded parser-output buffer. Fail closed if it is unavailable.
6. Compute SHA-256 and record inspection evidence.
7. Atomically move only a passing file to `accepted`; otherwise move it to `rejected` and prevent all processing handoff.

Any unavailable, timed-out, or failed required stage rejects the file. A clean antivirus result is evidence, not a guarantee; the VM boundary and parser restrictions remain mandatory.

## AI/content policy

- Audio, metadata, and transcripts are untrusted call content.
- Transcription/evaluation receives no browser, shell, filesystem write, database-admin, or external-action tools.
- Evaluation returns schema-validated fixed JSON fields. Text cannot select a tool, URL, command, prompt, or privileged workflow.
- Raw recordings and transcripts are not sent to public malware scanning services.

## Rollout gates

1. Build a patched VM snapshot with no production secrets.
2. Verify that host shares and enhanced-session integration are disabled.
3. Verify NAT/default-deny inbound and egress allowlist before adding dialer credentials.
4. Run valid, malformed, oversize, redirect-escape, scanner-failure, and media-verification-failure fixtures.
5. Confirm rejected files never appear in accepted storage, calls, Celery processing, or host shares.
6. Run one manual ingestion successfully, review sanitized audit records, then enable the schedule.

## Incident and recovery

If an inspection alert or suspected compromise occurs, disable scheduled ingestion, preserve the relevant rejected file and sanitized logs according to policy, rotate guest-only source credentials, restore the VM from a known-good image, patch the affected component, and require a clean manual validation before re-enabling the schedule. Do not copy the suspicious recording to the Windows host for investigation.
