# VM Isolation Verification Record

Feature: Automated Call Recording Ingestion
Runbook: [vm-ingestion-runbook.md](./vm-ingestion-runbook.md)
Bootstrap script: [deploy/ingestion-vm/bootstrap.sh](../deploy/ingestion-vm/bootstrap.sh)

## Baseline record

- Validation date: 2026-06-24
- Baseline snapshot ID: `call-rating-ingestion-baseline-2026-06-23`
- Recorded by: repository-side verification note (not VM deployment evidence)

## Verified controls

- NAT networking only.
- Default-deny inbound firewall.
- Egress allowlist configured for sheet source, recording hosts, DNS, NTP, update mirrors, and approved internal endpoints.
- No host drive mounts.
- No shared folders.
- No clipboard integration.
- No drag-and-drop integration.
- No USB passthrough.
- Service account is non-root.
- Password SSH remains disabled.
- Rejected fixtures remain inside the guest and do not appear in Windows host storage, accepted storage, `Call` records, or downstream processing queues.

## Evidence notes

- The guest bootstrap creates the runtime directories inside the VM and owns them with the non-root service account.
- The bootstrap configures UFW to deny inbound and outbound traffic by default, then opens only the approved SSH and egress destinations.
- Hypervisor-side integration features remain an operator responsibility and must stay disabled in the VM platform settings.

## Repository safety note

No production secrets, credentials, raw recordings, or scanner output are stored in this verification record.
