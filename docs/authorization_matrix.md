# Authorization Matrix

This document defines the supported backend roles and the default access rules used across the platform.

## Supported Roles

- `AGENT`
- `QA`
- `HR_MANAGER`
- `ADMIN`

## Access Rules

| Actor | Authenticated | Own data | Export data | Manage employees | Change employee role | Change employee status | View audits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Anonymous | No | No | No | No | No | No | No |
| AGENT | Yes | Yes | No | No | No | No | No |
| QA | Yes | Yes | Yes, redacted | No | No | No | No |
| HR_MANAGER | Yes | Yes | Yes, redacted | Read only | No | Yes | No |
| ADMIN | Yes | Yes | Yes, full | Yes | Yes | Yes | Yes |
| Disabled / suspended | No | No | No | No | No | No | No |

## Rules To Keep In Mind

- Backend authorization is the source of truth.
- Disabled and suspended accounts are rejected during token validation, even if they still hold a valid token.
- Export access is limited to `ADMIN`, `QA`, and `HR_MANAGER`.
- Non-admin exports are redacted before download.
- Role changes are admin-only.
- Account status changes are allowed for `ADMIN` and `HR_MANAGER`.
- Audit records are append-only and include the actor, target, action, before and after state, reason, success flag, and timestamp.
- Workflow notes are permission-checked backend records and do not grant access to linked resources.
- Soft-deleted notes remain admin-visible for audit purposes and are hidden from non-admin users.
