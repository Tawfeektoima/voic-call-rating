# Protect Architecture — Production Rollout Runbook

> **Version**: 1.0 — June 2026
> **Audience**: Platform operators, DevOps, and security administrators
> **Prerequisite**: All E2E regression tests pass (`tests/test_security_e2e_flow.py`, `securityE2E.test.tsx`)

---

## Table of Contents

1. [Rollout Stages](#1-rollout-stages)
2. [Pre-Enforcement Checklist](#2-pre-enforcement-checklist)
3. [Environment Variable Reference](#3-environment-variable-reference)
4. [Monitoring & Admin Checks](#4-monitoring--admin-checks)
5. [Rollback Procedure](#5-rollback-procedure)
6. [Post-Rollout Validation](#6-post-rollout-validation)

---

## 1. Rollout Stages

The Protect Architecture is designed for a phased rollout. **Never jump directly to enforce mode in production.** Follow these stages in order.

### Stage 0 — Deploy with `off`

```env
SECURITY_POLICY_MODE=off
```

- Deploy the latest codebase to production.
- The security policy engine is completely inert — no shift checks, device enrollment, session validation, or audit logging occurs.
- Verify that existing login, API, and WebSocket flows work identically to the pre-rollout baseline.
- **Exit criteria**: All smoke tests pass. No user-facing regressions.

### Stage 1 — Enable `audit`

```env
SECURITY_POLICY_MODE=audit
```

- Restart the backend service after updating the environment variable.
- The policy engine now evaluates every login, protected route, and WebSocket connection against the shift/device/session rules.
- **Violations are logged but never blocked.** Users experience zero disruption.
- Frontend device identity begins enrolling browser `device_id` values on login.
- **Exit criteria**: Audit events appear in the `audit_events` table. No crashes or unexpected behavior.

### Stage 2 — Review Audit Logs & Admin Data

While still in `audit` mode:

```sql
-- Count security audit events by action
SELECT action, COUNT(*) AS total
FROM audit_events
WHERE action LIKE 'SECURITY_%' OR action IN (
  'SESSION_CREATED', 'SESSION_REVOKED',
  'DEVICE_APPROVED', 'DEVICE_REVOKED',
  'SHIFT_CREATE', 'SHIFT_UPDATE', 'SHIFT_CANCEL',
  'WEBSOCKET_SECURITY_CLOSE'
)
GROUP BY action
ORDER BY total DESC;

-- Find audit-only and enforced policy events
SELECT id, action, actor_email, target, created_at,
       after_state
FROM audit_events
WHERE action IN ('SECURITY_POLICY_AUDIT', 'SECURITY_POLICY_DENIAL')
ORDER BY created_at DESC
LIMIT 50;
```

- Identify which employees are missing shifts, have unapproved devices, or trigger session conflicts.
- **Exit criteria**: All denial causes are understood and documented.

### Stage 3 — Fix Shifts, Devices & Sessions Data

Using the Admin Security console (`/admin/security`) or direct API calls:

1. **Shifts**: Ensure every active employee has a valid shift for their working days.
   ```
   GET /api/security-admin/shifts?employee_id=<id>
   POST /api/security-admin/shifts
   ```

2. **Devices**: Review enrolled devices. Approve legitimate devices, revoke suspicious ones.
   ```
   GET /api/security-admin/devices?employee_id=<id>
   POST /api/security-admin/devices/<id>/approve
   ```

3. **Sessions**: Clear stale or orphaned sessions that would block new logins.
   ```
   GET /api/security-admin/sessions?active_only=true
   POST /api/security-admin/sessions/<id>/revoke
   ```

- **Exit criteria**: Re-run the Stage 2 audit queries. The number of `DENY` decisions should be near zero for legitimate employees.

### Stage 4 — Enable `enforce`

```env
SECURITY_POLICY_MODE=enforce
```

- Restart the backend service.
- **The policy engine now actively blocks violations.** Employees without valid shifts, trusted devices, or active sessions will be denied access.
- Monitor closely for the first 1–2 hours (see [Monitoring](#4-monitoring--admin-checks)).
- **Exit criteria**: No unexpected forced logouts. All legitimate employees can log in and work.

### Stage 5 — Monitor Denials & WebSocket Closes

After enforcement is stable, set up ongoing monitoring:

- Track `SECURITY_POLICY_AUDIT`, `SECURITY_POLICY_DENIAL`, `SESSION_REVOKED`, and `DEVICE_REVOKED` events.
- Monitor WebSocket close code spikes (`4401`, `4403`, `1011`).
- Review forced logout frequency reports from the frontend team.
- See [Monitoring & Admin Checks](#4-monitoring--admin-checks) for queries.

### Stage 6 — Roll Back If Needed

If enforcement causes operational disruption, follow the [Rollback Procedure](#5-rollback-procedure).

---

## 2. Pre-Enforcement Checklist

**Do not enable `enforce` mode until every item below is confirmed.**

### Data Readiness

| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Every active employee has a valid shift for today | `SELECT e.id FROM employees e LEFT JOIN employee_shifts s ON e.id = s.employee_id AND s.work_date = CURRENT_DATE AND s.status = 'scheduled' WHERE e.status = 'active' AND s.id IS NULL;` — result must be empty |
| 2 | First devices are enrolled or approved for active employees | `SELECT e.id FROM employees e LEFT JOIN trusted_devices d ON e.id = d.employee_id AND d.is_trusted = true WHERE e.status = 'active' AND d.id IS NULL;` — result must be empty (or employees have not logged in yet) |
| 3 | No stale active sessions blocking new logins | `SELECT * FROM user_sessions WHERE is_active = true AND expires_at < NOW();` — revoke any returned rows |

### Feature Readiness

| # | Check | How to Verify |
|---|-------|---------------|
| 4 | Admin Security UI is accessible at `/admin/security` | Log in as admin, navigate to the page |
| 5 | Admin can list, create, and cancel shifts | Use the Shifts tab |
| 6 | Admin can list and revoke sessions | Use the Sessions tab |
| 7 | Admin can list, approve, and revoke devices | Use the Devices tab |
| 8 | Frontend login sends `device_id` in login and OTP payloads | Inspect network request body on login |
| 9 | WebSocket security validation passes for a valid session | Connect to `/api/live/ws/live/<call_id>` with a valid token |

### Security & Audit Readiness

| # | Check | How to Verify |
|---|-------|---------------|
| 10 | Audit logs do not expose raw `sid`, `jti`, JWT, raw `device_id`, or full `device_id_hash` | `SELECT * FROM audit_events WHERE metadata::text ~* '(eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+|"sid"\s*:\s*"[a-f0-9-]{20,}"|"jti"\s*:\s*"[a-f0-9-]{20,}"|"device_id"\s*:\s*"[^"]{20,}")' LIMIT 5;` — must return zero rows |
| 11 | All backend E2E tests pass | `python -m pytest tests/test_security_e2e_flow.py -v` |
| 12 | All frontend E2E tests pass | `npx vitest run src/app/__tests__/securityE2E.test.tsx` |
| 13 | Full backend security regression suite passes | `python -m pytest -k "security" -v` |
| 14 | Frontend production build compiles | `npx vite build` |

---

## 3. Environment Variable Reference

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `SECURITY_POLICY_MODE` | `off`, `audit`, `enforce` | `off` | Controls the security policy engine behavior. `off` disables all checks. `audit` logs violations without blocking. `enforce` blocks violations. |
| `SECURITY_TIMEZONE` | IANA timezone string | `Africa/Cairo` | Timezone used for shift window calculations. Must be a valid `zoneinfo` timezone. |
| `DEFAULT_SHIFT_GRACE_BEFORE_MINUTES` | `0`–`240` | `10` | Minutes of early access allowed before shift start time. |
| `DEFAULT_SHIFT_GRACE_AFTER_MINUTES` | `0`–`240` | `10` | Minutes of late access allowed after shift end time. |
| `SECURITY_WS_REVALIDATION_INTERVAL_SECONDS` | `≥ 0` | `15` | How often active WebSocket connections recheck session/device/shift validity. `0` disables mid-connection revalidation. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | integer | `60` | JWT access token lifetime. Also determines server-side session `expires_at`. Hardcoded in `app/security.py`. |

### Recommended Production Values

```env
# Recommended starting configuration
SECURITY_POLICY_MODE=audit              # Start with audit, move to enforce after review
SECURITY_TIMEZONE=Africa/Cairo          # Match your operational timezone
DEFAULT_SHIFT_GRACE_BEFORE_MINUTES=15   # 15 minutes early clock-in
DEFAULT_SHIFT_GRACE_AFTER_MINUTES=15    # 15 minutes late clock-out
SECURITY_WS_REVALIDATION_INTERVAL_SECONDS=30  # Revalidate every 30s (lower = tighter, higher = less DB load)
```

### Rollback Values

```env
# Immediate rollback to observation-only
SECURITY_POLICY_MODE=audit

# Emergency rollback — disable all security checks
SECURITY_POLICY_MODE=off
```

> **Important**: After changing `SECURITY_POLICY_MODE`, restart the backend service for the change to take effect.

---

## 4. Monitoring & Admin Checks

### SQL Monitoring Queries

Run these queries periodically (or set up dashboards) after enabling `audit` or `enforce` mode.

#### Recent Security Denials

```sql
SELECT id, action, actor_email, target, created_at,
       after_state
FROM audit_events
WHERE action IN ('SECURITY_POLICY_AUDIT', 'SECURITY_POLICY_DENIAL')
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;
```

#### Session Revocations (Admin or Logout)

```sql
SELECT id, action, actor_email, target, created_at, reason
FROM audit_events
WHERE action = 'SESSION_REVOKED'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

#### Device Revocations

```sql
SELECT id, action, actor_email, target, created_at, reason
FROM audit_events
WHERE action = 'DEVICE_REVOKED'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

#### Shift Cancellations

```sql
SELECT id, action, actor_email, target, created_at, reason
FROM audit_events
WHERE action = 'SHIFT_CANCEL'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

#### Repeated Forced Logouts (Possible Misconfiguration)

```sql
-- Employees with 3+ denials in the last hour — likely a missing shift or device issue
SELECT actor_email, COUNT(*) AS denial_count
FROM audit_events
WHERE action IN ('SECURITY_POLICY_AUDIT', 'SECURITY_POLICY_DENIAL')
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY actor_email
HAVING COUNT(*) >= 3
ORDER BY denial_count DESC;
```

### WebSocket Close Code Monitoring

If your infrastructure logs WebSocket close events, monitor for spikes in these codes:

| Close Code | Meaning | Action |
|------------|---------|--------|
| `4401` | Session invalid, expired, or revoked | Check if admin revoked a session or if tokens are expiring prematurely |
| `4403` | Device untrusted, shift expired, or access policy violation | Check device trust status and shift schedule for the affected employee |
| `1011` | Internal server error during revalidation | Check backend logs for database connectivity or query failures |

### Admin Security Console Checks

Accessible at `/admin/security` (admin role required):

1. **Shifts tab**: Verify all active employees have shifts for the current and upcoming dates.
2. **Sessions tab**: Check for stale active sessions. Revoke any that belong to employees who should not be logged in.
3. **Devices tab**: Review newly enrolled devices. Approve legitimate ones and revoke unfamiliar entries.

---

## 5. Rollback Procedure

### Standard Rollback (Enforce → Audit)

Use this when enforcement causes unexpected denials but the system is otherwise stable.

1. Set `SECURITY_POLICY_MODE=audit` in the environment.
2. Restart the backend service.
3. Confirm users can log in by checking the login endpoint returns `200 OK`.
4. Review audit logs for the root cause of denials:
   ```sql
   SELECT event_type, metadata->>'code' AS code, COUNT(*)
   FROM audit_events
   WHERE metadata->>'decision' = 'DENY'
     AND created_at > NOW() - INTERVAL '2 hours'
   GROUP BY event_type, metadata->>'code'
   ORDER BY COUNT(*) DESC;
   ```
5. Fix the underlying data (missing shifts, unapproved devices, stale sessions) using the Admin Security console.
6. Re-run the [Pre-Enforcement Checklist](#2-pre-enforcement-checklist).
7. Re-enable `enforce` mode and restart the backend.

### Emergency Rollback (Enforce → Off)

Use this when the security policy engine itself is causing system instability (crashes, timeouts, database errors).

```env
SECURITY_POLICY_MODE=off
```

1. Set the variable and restart the backend immediately.
2. All security checks are disabled. Users can log in and operate without shift, device, or session validation.
3. **This is a temporary measure.** Investigate the root cause before re-enabling even `audit` mode.
4. Common emergency causes:
   - Database connection pool exhaustion from revalidation queries.
   - Corrupted shift/device/session data causing query exceptions.
   - Misconfigured `SECURITY_TIMEZONE` causing all shift checks to fail.

> **Warning**: While in `off` mode, no security audit events are recorded. Return to `audit` mode as soon as the issue is resolved.

---

## 6. Post-Rollout Validation

After enabling `enforce` mode, verify each of these behaviors manually or via automated tests.

### Login & Access

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 1 | Agent logs in during valid shift with trusted device | Login succeeds, session created, `access_token` returned |
| 2 | Agent logs in outside shift hours | Login blocked with `SHIFT_NOT_ALLOWED` |
| 3 | Agent logs in with a second browser while already logged in | Login blocked with `ACTIVE_SESSION_EXISTS` (409) |
| 4 | Agent accesses `/api/auth/me` with valid token | Returns user profile |

### Session Lifecycle

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 5 | Admin revokes an active session | Session marked inactive. Subsequent `/api/auth/me` returns `401` |
| 6 | Revoked session token used on WebSocket | WebSocket closes with code `4401` |
| 7 | Agent logs out normally | Session revoked, token invalidated |

### Device Lifecycle

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 8 | Admin revokes a trusted device | Device marked untrusted. Protected routes return `403 DEVICE_NOT_TRUSTED` |
| 9 | Admin re-approves a revoked device | Access is restored immediately |

### Shift Lifecycle

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 10 | Admin cancels an active shift | Protected routes return `403 SHIFT_NOT_ALLOWED`. WebSockets close with `4403` |
| 11 | Admin schedules a new shift for the same employee | Access is restored |

### Security & Safety

| # | Scenario | Expected Result |
|---|----------|-----------------|
| 12 | Frontend forced logout displays a safe message | No raw `sid`, `jti`, JWT tokens, or device hashes in the message |
| 13 | Admin revokes an already-revoked session | Returns success (idempotent) and writes an audit event with `already_revoked: True` |
| 14 | Admin revokes an already-revoked device | Returns success (idempotent) and writes an audit event with `already_revoked: True` |

---

*Last updated: June 2026*
