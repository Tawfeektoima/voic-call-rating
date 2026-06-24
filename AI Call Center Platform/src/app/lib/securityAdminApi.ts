import api from './api';
import { SecurityShift, SecuritySession, TrustedDevice, SecuritySummary, SecurityAuditFeed } from './types';


const mapShift = (s: any): SecurityShift => ({
  id: s.id,
  employee_id: String(s.employee_id),
  work_date: s.work_date,
  starts_at: s.shift_start || '',
  ends_at: s.shift_end || '',
  status: s.status,
});

const mapSession = (s: any): SecuritySession => ({
  id: s.id,
  employee_id: String(s.employee_id),
  created_at: s.issued_at || '',
  expires_at: s.expires_at || '',
  revoked_at: s.revoked_at || null,
  is_active: s.is_active,
  last_seen_at: s.last_seen_at || null,
});

const mapDevice = (d: any): TrustedDevice => ({
  id: d.id,
  employee_id: String(d.employee_id),
  label: d.device_label || null,
  is_trusted: d.is_trusted,
  revoked_at: d.revoked_at || null,
  last_seen_at: d.last_seen_at || null,
  fingerprint: d.device_fingerprint || null,
});

export async function listSecurityShifts(params?: {
  employee_id?: string;
  work_date?: string;
}): Promise<SecurityShift[]> {
  const requestParams: any = {};
  if (params?.employee_id) {
    requestParams.employee_id = parseInt(params.employee_id, 10);
  }
  if (params?.work_date) {
    requestParams.from_date = params.work_date;
    requestParams.to_date = params.work_date;
  }
  const response = await api.get<any[]>('/api/security-admin/shifts', { params: requestParams });
  return response.data.map(mapShift);
}

export async function createSecurityShift(payload: {
  employee_id: string;
  work_date: string;
  starts_at: string;
  ends_at: string;
  status?: string;
}): Promise<SecurityShift> {
  const response = await api.post('/api/security-admin/shifts', {
    employee_id: parseInt(payload.employee_id, 10),
    work_date: payload.work_date,
    shift_start: payload.starts_at,
    shift_end: payload.ends_at,
    status: payload.status,
  });
  return mapShift(response.data);
}

export async function updateSecurityShift(shiftId: number, payload: {
  work_date?: string;
  starts_at?: string;
  ends_at?: string;
  status?: string;
  reason?: string;
}): Promise<SecurityShift> {
  const response = await api.patch(`/api/security-admin/shifts/${shiftId}`, {
    work_date: payload.work_date,
    shift_start: payload.starts_at,
    shift_end: payload.ends_at,
    status: payload.status,
    reason: payload.reason,
  });
  return mapShift(response.data);
}

export async function deleteSecurityShift(shiftId: number, reason?: string): Promise<void> {
  await api.post(`/api/security-admin/shifts/${shiftId}/cancel`, {
    reason: reason || 'Shift cancelled by admin',
  });
}

export async function listSecuritySessions(params?: {
  employee_id?: string;
  active_only?: boolean;
}): Promise<SecuritySession[]> {
  const requestParams: any = {};
  if (params?.employee_id) {
    requestParams.employee_id = parseInt(params.employee_id, 10);
  }
  if (params?.active_only !== undefined) {
    requestParams.active_only = params.active_only;
  }
  const response = await api.get<any[]>('/api/security-admin/sessions', { params: requestParams });
  return response.data.map(mapSession);
}

export async function revokeSecuritySession(sessionId: number, payload: {
  reason: string;
}): Promise<{ message: string }> {
  const response = await api.post(`/api/security-admin/sessions/${sessionId}/revoke`, {
    reason: payload.reason,
  });
  return {
    message: response.data.message || 'Session revoked successfully'
  };
}

export async function listTrustedDevices(params?: {
  employee_id?: string;
  trusted_only?: boolean;
}): Promise<TrustedDevice[]> {
  const requestParams: any = {};
  if (params?.employee_id) {
    requestParams.employee_id = parseInt(params.employee_id, 10);
  }
  if (params?.trusted_only !== undefined) {
    requestParams.trusted_only = params.trusted_only;
  }
  const response = await api.get<any[]>('/api/security-admin/devices', { params: requestParams });
  return response.data.map(mapDevice);
}

export async function approveTrustedDevice(deviceId: number, payload: {
  reason: string;
}): Promise<TrustedDevice> {
  const response = await api.post(`/api/security-admin/devices/${deviceId}/approve`, {
    reason: payload.reason,
  });
  return mapDevice(response.data);
}

export async function revokeTrustedDevice(deviceId: number, payload: {
  reason: string;
}): Promise<TrustedDevice> {
  const response = await api.post(`/api/security-admin/devices/${deviceId}/revoke`, {
    reason: payload.reason,
  });
  return mapDevice(response.data);
}

export async function getSecuritySummary(hours?: number): Promise<SecuritySummary> {
  const params: any = {};
  if (hours !== undefined) {
    params.hours = hours;
  }
  const response = await api.get<SecuritySummary>('/api/security-admin/summary', { params });
  return response.data;
}

export async function listSecurityAuditEvents(params?: {
  hours?: number;
  limit?: number;
  offset?: number;
  action?: string;
  employee_id?: string;
  target?: string;
  success?: boolean;
  q?: string;
}): Promise<SecurityAuditFeed> {
  const requestParams: any = {};
  if (params?.hours !== undefined) requestParams.hours = params.hours;
  if (params?.limit !== undefined) requestParams.limit = params.limit;
  if (params?.offset !== undefined) requestParams.offset = params.offset;
  if (params?.action) requestParams.action = params.action;
  if (params?.employee_id) requestParams.employee_id = parseInt(params.employee_id, 10);
  if (params?.target) requestParams.target = params.target;
  if (params?.success !== undefined) requestParams.success = params.success;
  if (params?.q) requestParams.q = params.q;
  const response = await api.get<SecurityAuditFeed>('/api/security-admin/events', { params: requestParams });
  return response.data;
}
