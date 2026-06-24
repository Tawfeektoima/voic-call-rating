# VM Ingestion Runbook

This runbook covers the dedicated ingestion VM used for raw call recordings. The intent is simple: keep untrusted audio inside the guest, keep the Windows host out of the recording path, and make recovery predictable.

## Scope

- Dedicated Ubuntu Server LTS VM only.
- Hyper-V Generation 2 with NAT when available.
- VirtualBox with NAT only when Hyper-V is unavailable.
- No host mount, shared folder, clipboard sharing, drag-and-drop, or USB passthrough.
- No raw recordings copied to the Windows host for inspection.

## Baseline VM Creation

1. Create the VM with the approved helper script: `scripts/provision-ingestion-vm.ps1`.
2. Use the approved sizing:
   - 4 vCPU
   - 8 GB RAM
   - 80 GB VHDX on a BitLocker-protected Windows volume
3. Keep the VM powered off after creation until Ubuntu Server LTS is installed.
4. During Ubuntu installation, enable full-disk encryption for the guest storage (guided LVM with LUKS).
5. Take a clean baseline snapshot before adding credentials or sheet access.

## Network Setup

- Use NAT only.
- Do not use bridged networking.
- Keep inbound access blocked by default.
- Allow only the approved outbound destinations needed for the sheet source, recording hosts, DNS, NTP, OS updates, and explicit internal result endpoints.
- Do not expose recording directories to the Windows host.

## Guest Hardening

1. Run `deploy/ingestion-vm/bootstrap.sh` as root inside the guest.
   Example:
   ```bash
   sudo SSH_ALLOWED_CIDR="<host-management-cidr>" \
     EGRESS_ALLOWED_CIDRS="<dns-cidr> <ntp-cidr> <update-mirror-cidr> <sheet-source-cidr> <recording-host-cidr> <internal-endpoint-cidr>" \
     ./deploy/ingestion-vm/bootstrap.sh
   ```
2. Confirm the script creates:
   - a non-root service account
   - guest-local `quarantine`, `accepted`, `rejected`, and `state` directories
   - unattended security updates
   - a default-deny inbound and allowlisted outbound firewall
3. Confirm password SSH login stays disabled.
4. Approved management route:
   - create one named administrator account during Ubuntu setup
   - sign in on the VM console and add the approved public key to that account before using SSH
   - keep `SSH_ALLOWED_CIDR` scoped to the host-only management network or a single approved admin subnet
5. Use key-based SSH only if remote administration is required.
6. Keep the guest patch cadence separate from day-to-day ingestion runs.

Install the SSH key from the guest console before relying on remote access:

```bash
sudo install -d -m 700 -o <admin-user> -g <admin-user> /home/<admin-user>/.ssh
sudo tee /home/<admin-user>/.ssh/authorized_keys >/dev/null
sudo chown <admin-user>:<admin-user> /home/<admin-user>/.ssh/authorized_keys
sudo chmod 600 /home/<admin-user>/.ssh/authorized_keys
```

Paste exactly one approved public key into the `tee` prompt, then press `Ctrl+D`.

## Service Layout

- Ingestion downloads land in `quarantine`.
- Files that pass inspection move to `accepted`.
- Rejected files stay in `rejected` under the guest retention policy.
- Operational state stays in `state`.
- The host never mounts these directories.

## Guest Deployment

1. Place the Google Sheets service-account JSON on the guest only, for example at `/var/lib/call-rating/secrets/vicdi-sheets-reader.json`, with permissions restricted to the deployment account.
2. Export deployment secrets from the guest environment and keep `CALL_INGEST_ENABLED=false` during the first deployment.
3. Run:
   ```bash
   docker compose -f docker-compose.prod.yml up -d postgres redis scanner-updater scanner media-verifier api worker ingestion-downloader ingestion-inspector
   docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
   ```
4. Confirm the API is reachable only through the approved guest-local management route.
5. Leave `ingestion-scheduler` stopped until the validation sequence below passes.

Production runtime roles are split intentionally:

- `api`: management API only
- `gpu_worker`: existing audio-processing queue only
- `downloader`: sheet reads and HTTPS downloads only
- `inspector`: malware scan, media verification, and accepted/rejected promotion only
- `scheduler`: Beat schedule only

## Patching

- Apply guest OS updates on a scheduled maintenance window.
- Update scanner definitions inside the guest.
- Rebuild or refresh containers inside the guest after base image updates.
- Reboot the VM after kernel or security updates when required.

## Snapshots and Backup

- Keep a known-good snapshot before enabling ingestion for the first time.
- Take a new snapshot after any major guest change that affects networking, storage, or inspection.
- Back up only guest-local configuration, database state, and sanitized logs.
- Do not back up raw recordings to a Windows-host location as part of normal operations.
- If backup tooling needs network access, keep it allowlisted and guest-initiated.
- Keep a documented rejected-file retention window and purge only from inside the guest according to policy.

## Restore Procedure

1. Disable the ingestion schedule inside the guest.
2. Preserve the current guest-local logs, rejected evidence, and database state if incident review is required.
3. Restore the VM from the last known-good snapshot or backup.
4. Reapply the approved guest bootstrap and configuration.
5. Validate firewall, NAT, and service health before re-enabling ingestion.
6. Run one manual ingestion with synthetic or approved test content before turning the schedule back on.

## Incident Action

If a suspicious audio file, scanner alert, malformed media file, or unexpected guest behavior occurs:

1. Disable the guest schedule first.
2. Preserve guest-local evidence and sanitized logs.
3. Rotate guest-only credentials.
4. Rebuild or restore the guest from a trusted baseline.
5. Verify the scanner and media-verification path before resuming.
6. Never copy a suspicious audio file to the Windows host for investigation.

## Validation Checklist

- NAT is enabled.
- Shared folders are disabled.
- Clipboard and drag-and-drop integration are disabled.
- USB passthrough is disabled.
- Password SSH is disabled.
- Outbound egress is limited to the approved CIDR allowlist.
- Guest-local storage roots exist and are owned by the service account.
- Scanner service health is green.
- The schedule is disabled until a successful manual test run completes.

## Validation Sequence

1. Run `docker compose -f docker-compose.prod.yml ps` and confirm `api`, `worker`, `ingestion-downloader`, `ingestion-inspector`, `scanner`, and `media-verifier` are healthy.
2. Confirm `ingestion-scheduler` is still stopped.
3. Run one manual ingestion against synthetic or approved non-production content.
4. Confirm the rejected fixture stays out of Windows host storage, `accepted`, `Call`, and downstream processing queues.
5. Confirm only accepted files create `Call` rows and queue downstream processing exactly once.
6. Review the sanitized run detail, retry flow, and audit events.
7. Only then start `ingestion-scheduler` and set `CALL_INGEST_ENABLED=true`.

Rollback:

1. Stop `ingestion-scheduler` first.
2. If suspicious behavior continues, stop `ingestion-downloader` and `ingestion-inspector`.
3. Restore the baseline snapshot recorded in the verification record.
4. Re-run the validation sequence before re-enabling the schedule.

## Verification Record

Capture the operator-checked baseline in [vm-isolation-verification.md](./vm-isolation-verification.md) before enabling real recordings.

- Record the exact baseline snapshot ID from the hypervisor.
- Record the validation date.
- Keep the repository copy free of secrets, dialer credentials, and raw audio evidence.

## Release Evidence

- Validation date: 2026-06-24
- Release scope: Phase 7 production-readiness gates for automated call recording ingestion
- Compose topology: split `api`, `gpu_worker`, `downloader`, `inspector`, `scheduler`, `scanner`, and `media-verifier`
- Migration revision validated: `b2c9a1d8e4f7`
- Baseline snapshot ID: `call-rating-ingestion-baseline-2026-06-23`
- Scanner path/version evidence: `clamd` service with guest-local `clamav-db`; confirm exact signature version in-guest before enabling production traffic
- Contract and schema evidence: sanitized operations contract parsed and Alembic revision-chain/head verification recorded in repository tests
- Performance evidence: mocked 100-record ingestion run validated with four-download concurrency ceiling and 100 downstream handoffs in repository tests
- Repository regression evidence: `86` targeted ingestion/deployment tests passed and `7` adjacent worker/transcript safety tests passed on 2026-06-24
- Approval state: repository implementation complete; guest-side operator approval still required before enabling scheduled production ingestion

## Operational Notes

- Treat every recording as untrusted input until inspection completes.
- Treat transcripts and evaluation output as untrusted content as well.
- Keep raw recordings, scanner output, and guest paths out of host-facing documentation.
- If in doubt, prefer stopping the schedule over trying to salvage a questionable file.
