/** @vitest-environment node */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import api, { getApiErrorMessage } from '../lib/api';
import {
  listSecurityShifts,
  createSecurityShift,
  updateSecurityShift,
  deleteSecurityShift,
  listSecuritySessions,
  revokeSecuritySession,
  listTrustedDevices,
  approveTrustedDevice,
  revokeTrustedDevice,
  listSecurityAuditEvents
} from '../lib/securityAdminApi';

describe('Admin Security API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('listSecurityShifts calls the correct endpoint and maps query parameters', async () => {
    const mockShifts = [
      {
        id: 1,
        employee_id: 123,
        work_date: '2026-06-18',
        shift_start: '09:00:00',
        shift_end: '17:00:00',
        grace_before_minutes: 10,
        grace_after_minutes: 10,
        status: 'scheduled'
      }
    ];

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: mockShifts });

    const result = await listSecurityShifts({ employee_id: '123', work_date: '2026-06-18' });

    expect(getSpy).toHaveBeenCalledWith('/api/security-admin/shifts', {
      params: {
        employee_id: 123,
        from_date: '2026-06-18',
        to_date: '2026-06-18'
      }
    });

    expect(result).toHaveLength(1);
    expect(result[0]).toEqual({
      id: 1,
      employee_id: '123',
      work_date: '2026-06-18',
      starts_at: '09:00:00',
      ends_at: '17:00:00',
      status: 'scheduled'
    });
  });

  it('createSecurityShift sends employee_id as int and maps parameters', async () => {
    const mockCreated = {
      id: 2,
      employee_id: 456,
      work_date: '2026-06-19',
      shift_start: '10:00:00',
      shift_end: '18:00:00',
      grace_before_minutes: 5,
      grace_after_minutes: 5,
      status: 'scheduled'
    };

    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: mockCreated });

    const result = await createSecurityShift({
      employee_id: '456',
      work_date: '2026-06-19',
      starts_at: '10:00:00',
      ends_at: '18:00:00',
      status: 'scheduled'
    });

    expect(postSpy).toHaveBeenCalledWith('/api/security-admin/shifts', {
      employee_id: 456,
      work_date: '2026-06-19',
      shift_start: '10:00:00',
      shift_end: '18:00:00',
      status: 'scheduled'
    });

    expect(result.employee_id).toBe('456');
    expect(result.starts_at).toBe('10:00:00');
  });

  it('updateSecurityShift sends patch request with status and reason', async () => {
    const mockUpdated = {
      id: 3,
      employee_id: 789,
      work_date: '2026-06-20',
      shift_start: '08:00:00',
      shift_end: '16:00:00',
      grace_before_minutes: 10,
      grace_after_minutes: 10,
      status: 'disabled'
    };

    const patchSpy = vi.spyOn(api, 'patch').mockResolvedValue({ data: mockUpdated });

    const result = await updateSecurityShift(3, {
      status: 'disabled',
      reason: 'Shift adjustments'
    });

    expect(patchSpy).toHaveBeenCalledWith('/api/security-admin/shifts/3', {
      work_date: undefined,
      shift_start: undefined,
      shift_end: undefined,
      status: 'disabled',
      reason: 'Shift adjustments'
    });

    expect(result.status).toBe('disabled');
  });

  it('deleteSecurityShift sends cancel request with reason', async () => {
    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: {} });

    await deleteSecurityShift(5, 'Holiday cancellation');

    expect(postSpy).toHaveBeenCalledWith('/api/security-admin/shifts/5/cancel', {
      reason: 'Holiday cancellation'
    });
  });

  it('listSecuritySessions filters active_only and employee_id', async () => {
    const mockSessions = [
      {
        id: 10,
        employee_id: 111,
        issued_at: '2026-06-18T12:00:00Z',
        expires_at: '2026-06-19T00:00:00Z',
        revoked_at: null,
        is_active: true,
        last_seen_at: '2026-06-18T12:30:00Z'
      }
    ];

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: mockSessions });

    const result = await listSecuritySessions({ employee_id: '111', active_only: true });

    expect(getSpy).toHaveBeenCalledWith('/api/security-admin/sessions', {
      params: {
        employee_id: 111,
        active_only: true
      }
    });

    expect(result).toHaveLength(1);
    expect(result[0].employee_id).toBe('111');
    expect(result[0].created_at).toBe('2026-06-18T12:00:00Z');
  });

  it('revokeSecuritySession posts session ID and reason', async () => {
    const mockRevoked = {
      message: 'Session revoked successfully'
    };

    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: mockRevoked });

    const result = await revokeSecuritySession(15, { reason: 'Admin revoked active session' });

    expect(postSpy).toHaveBeenCalledWith('/api/security-admin/sessions/15/revoke', {
      reason: 'Admin revoked active session'
    });

    expect(result.message).toBe('Session revoked successfully');
  });

  it('approveTrustedDevice and revokeTrustedDevice post to correct endpoints with reason', async () => {
    const mockDevice = {
      id: 20,
      employee_id: 333,
      device_label: 'Work Laptop',
      is_trusted: true,
      revoked_at: null
    };

    const postSpy = vi.spyOn(api, 'post').mockResolvedValue({ data: mockDevice });

    const approveResult = await approveTrustedDevice(20, { reason: 'Verified by team manager' });
    expect(postSpy).toHaveBeenCalledWith('/api/security-admin/devices/20/approve', {
      reason: 'Verified by team manager'
    });
    expect(approveResult.is_trusted).toBe(true);

    const revokeResult = await revokeTrustedDevice(20, { reason: 'Lost device' });
    expect(postSpy).toHaveBeenCalledWith('/api/security-admin/devices/20/revoke', {
      reason: 'Lost device'
    });
  });

  it('listTrustedDevices maps device_fingerprint to fingerprint', async () => {
    const mockDevices = [
      {
        id: 20,
        employee_id: 333,
        device_label: 'Work Laptop',
        is_trusted: true,
        revoked_at: null,
        last_seen_at: '2026-06-18T12:30:00Z',
        device_fingerprint: 'fp-123456'
      }
    ];

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: mockDevices });

    const result = await listTrustedDevices({ employee_id: '333', trusted_only: true });

    expect(getSpy).toHaveBeenCalledWith('/api/security-admin/devices', {
      params: {
        employee_id: 333,
        trusted_only: true
      }
    });

    expect(result).toHaveLength(1);
    expect(result[0].fingerprint).toBe('fp-123456');
    expect(result[0].label).toBe('Work Laptop');
  });

  it('listSecurityAuditEvents maps query params and returns a feed', async () => {
    const mockFeed = {
      hours: 24,
      limit: 10,
      offset: 0,
      total: 1,
      items: [
        {
          id: 101,
          actor_id: 1,
          actor_email: 'admin@example.com',
          action: 'SESSION_REVOKED',
          target: 'UserSession id=10; employee_id=42',
          subject_employee_id: 42,
          summary: 'Session revoked',
          details: '{"session_id":10}',
          reason: 'Administrative action',
          success: true,
          created_at: '2026-06-19T00:00:00Z'
        }
      ]
    };

    const getSpy = vi.spyOn(api, 'get').mockResolvedValue({ data: mockFeed });

    const result = await listSecurityAuditEvents({
      hours: 24,
      limit: 10,
      offset: 0,
      action: 'SESSION_REVOKED',
      employee_id: '42',
      success: true,
      q: 'revoked'
    });

    expect(getSpy).toHaveBeenCalledWith('/api/security-admin/events', {
      params: {
        hours: 24,
        limit: 10,
        offset: 0,
        action: 'SESSION_REVOKED',
        employee_id: 42,
        success: true,
        q: 'revoked'
      }
    });

    expect(result.total).toBe(1);
    expect(result.items[0].subject_employee_id).toBe(42);
  });

  it('getApiErrorMessage preserves backend detail message safely', () => {
    const axiosError = {
      isAxiosError: true,
      response: {
        data: {
          detail: 'Duplicate shift: Employee already has a shift on this date.'
        }
      }
    };

    const message = getApiErrorMessage(axiosError, 'Default Error');
    expect(message).toBe('Duplicate shift: Employee already has a shift on this date.');
  });
});
