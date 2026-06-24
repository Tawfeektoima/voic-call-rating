import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import { AdminSecurity } from '../pages/AdminSecurity';
import { RoleGuard } from '../components/auth/RoleGuard';
import { UserRole } from '../lib/types';
import { toast } from 'sonner';
import * as securityAdminApi from '../lib/securityAdminApi';

const mockUseApp = vi.fn();
vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  }
}));

vi.mock('../lib/securityAdminApi', () => ({
  listSecurityShifts: vi.fn(),
  createSecurityShift: vi.fn(),
  updateSecurityShift: vi.fn(),
  deleteSecurityShift: vi.fn(),
  listSecuritySessions: vi.fn(),
  revokeSecuritySession: vi.fn(),
  listTrustedDevices: vi.fn(),
  approveTrustedDevice: vi.fn(),
  revokeTrustedDevice: vi.fn(),
  getSecuritySummary: vi.fn(),
  listSecurityAuditEvents: vi.fn()
}));

describe('Admin Security Management UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    mockUseApp.mockReturnValue({
      userRole: UserRole.ADMIN,
      currentUser: { id: 1, name: 'Admin', role: UserRole.ADMIN, permissions: [] }
    });

    vi.mocked(securityAdminApi.listSecurityShifts).mockResolvedValue([]);
    vi.mocked(securityAdminApi.listSecuritySessions).mockResolvedValue([]);
    vi.mocked(securityAdminApi.listTrustedDevices).mockResolvedValue([]);
    vi.mocked(securityAdminApi.listSecurityAuditEvents).mockResolvedValue({
      hours: 24,
      limit: 10,
      offset: 0,
      total: 0,
      items: []
    });
    vi.mocked(securityAdminApi.getSecuritySummary).mockResolvedValue({
      audit_policy_violations: 0,
      enforced_policy_denials: 0,
      denied_logins: 0,
      denied_protected_requests: 0,
      revoked_sessions: 0,
      revoked_devices: 0,
      cancelled_shifts: 0,
      websocket_security_closes: 0
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('Admin Security route renders for admin users', async () => {
    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    expect(screen.getByText('Security Administration')).toBeInTheDocument();
    expect(screen.getByText('Employee Shifts')).toBeInTheDocument();
  });

  it('Non-admin users cannot access the page', () => {
    mockUseApp.mockReturnValue({
      userRole: UserRole.AGENT,
      currentUser: { id: 2, name: 'Agent', role: UserRole.AGENT, permissions: [] }
    });

    render(
      <MemoryRouter initialEntries={['/admin/security']}>
        <Routes>
          <Route path="/" element={<div>Dashboard Home</div>} />
          <Route path="/admin/security" element={
            <RoleGuard allowedRoles={[UserRole.ADMIN]}>
              <AdminSecurity />
            </RoleGuard>
          } />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText('Security Administration')).not.toBeInTheDocument();
  });

  it('Shift form status dropdown only offers backend-supported values', () => {
    render(
      <MemoryRouter>
        <AdminSecurity initialTab="shifts" />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Schedule Shift'));

    const statusSelect = document.body.querySelector('select') as HTMLSelectElement;
    expect(statusSelect).toBeInTheDocument();

    const options = Array.from(statusSelect.options).map(opt => opt.value);
    expect(options).toEqual(['scheduled', 'disabled']);
  });

  it('Creating a shift sends only supported statuses', async () => {
    vi.mocked(securityAdminApi.createSecurityShift).mockResolvedValue({
      id: 11, employee_id: '456', work_date: '2026-06-19', starts_at: '09:00:00', ends_at: '17:00:00', status: 'disabled'
    });

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="shifts" />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByText('Schedule Shift'));

    const modalForm = document.body.querySelector('form') as HTMLFormElement;
    const empInput = modalForm.querySelector('input[placeholder="e.g. 123"]') as HTMLInputElement;
    const dateInput = modalForm.querySelector('input[type="date"]') as HTMLInputElement;
    const startInput = modalForm.querySelector('input[placeholder="09:00:00"]') as HTMLInputElement;
    const endInput = modalForm.querySelector('input[placeholder="17:00:00"]') as HTMLInputElement;
    const statusSelect = modalForm.querySelector('select') as HTMLSelectElement;

    fireEvent.change(empInput, { target: { value: '456' } });
    fireEvent.change(dateInput, { target: { value: '2026-06-19' } });
    fireEvent.change(startInput, { target: { value: '09:00:00' } });
    fireEvent.change(endInput, { target: { value: '17:00:00' } });
    fireEvent.change(statusSelect, { target: { value: 'disabled' } });

    fireEvent.click(screen.getByText('Save Schedule'));

    await waitFor(() => {
      expect(securityAdminApi.createSecurityShift).toHaveBeenCalledWith({
        employee_id: '456',
        work_date: '2026-06-19',
        starts_at: '09:00:00',
        ends_at: '17:00:00',
        status: 'disabled'
      });
    });
  });

  it('Updating a shift requires reason and sends it', async () => {
    const mockShifts = [
      { id: 10, employee_id: '101', work_date: '2026-06-18', starts_at: '09:00:00', ends_at: '17:00:00', status: 'scheduled' }
    ];
    vi.mocked(securityAdminApi.listSecurityShifts).mockResolvedValue(mockShifts);

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="shifts" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Employee 101')).toBeInTheDocument();
    });

    const editBtn = screen.getByTitle('Edit Shift');
    fireEvent.click(editBtn);

    // Try submitting without reason
    fireEvent.click(screen.getByText('Save Schedule'));
    expect(toast.error).toHaveBeenCalledWith('Reason for update is required');

    // Fill in the reason
    const reasonInput = screen.getByPlaceholderText('Specify the reason for updating this shift...');
    fireEvent.change(reasonInput, { target: { value: 'Shift adjustments' } });

    vi.mocked(securityAdminApi.updateSecurityShift).mockResolvedValue({
      id: 10, employee_id: '101', work_date: '2026-06-18', starts_at: '09:00:00', ends_at: '17:00:00', status: 'scheduled'
    });

    fireEvent.click(screen.getByText('Save Schedule'));

    await waitFor(() => {
      expect(securityAdminApi.updateSecurityShift).toHaveBeenCalledWith(10, {
        work_date: '2026-06-18',
        starts_at: '09:00:00',
        ends_at: '17:00:00',
        status: 'scheduled',
        reason: 'Shift adjustments'
      });
    });
  });

  it('Cancelling a shift requires a reason', async () => {
    const mockShifts = [
      { id: 10, employee_id: '101', work_date: '2026-06-18', starts_at: '09:00:00', ends_at: '17:00:00', status: 'scheduled' }
    ];
    vi.mocked(securityAdminApi.listSecurityShifts).mockResolvedValue(mockShifts);

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="shifts" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Employee 101')).toBeInTheDocument();
    });

    const cancelBtn = screen.getByTitle('Cancel Shift');
    fireEvent.click(cancelBtn);

    // Verify confirmation dialog is visible
    expect(screen.getByText('Cancel Shift')).toBeInTheDocument();

    const reasonInput = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
    
    // Attempt confirm without reason
    fireEvent.click(screen.getByText('Confirm'));
    expect(toast.error).toHaveBeenCalledWith('A reason is required to perform this action');

    // Enter reason and confirm
    fireEvent.change(reasonInput, { target: { value: 'Holiday cancellation' } });
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(securityAdminApi.deleteSecurityShift).toHaveBeenCalledWith(10, 'Holiday cancellation');
    });
  });

  it('Revoking a session requires a reason and handles response', async () => {
    const mockSessions = [
      { id: 20, employee_id: '202', created_at: '2026-06-18T10:00:00Z', expires_at: '2026-06-18T22:00:00Z', revoked_at: null, is_active: true, last_seen_at: '2026-06-18T12:00:00Z' }
    ];
    vi.mocked(securityAdminApi.listSecuritySessions).mockResolvedValue(mockSessions);

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="sessions" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Employee 202')).toBeInTheDocument();
    });

    const revokeBtn = screen.getByText('Revoke');
    fireEvent.click(revokeBtn);

    const reasonInput = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
    fireEvent.change(reasonInput, { target: { value: 'Suspicious activities' } });

    vi.mocked(securityAdminApi.revokeSecuritySession).mockResolvedValue({ message: 'Revoked by security admin' });
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(securityAdminApi.revokeSecuritySession).toHaveBeenCalledWith(20, { reason: 'Suspicious activities' });
      expect(toast.success).toHaveBeenCalledWith('Revoked by security admin');
    });
  });

  it('Approving and revoking a device requires a reason', async () => {
    const mockDevices = [
      { id: 30, employee_id: '303', label: 'Company Phone', is_trusted: false, revoked_at: null, last_seen_at: '2026-06-18T12:00:00Z', fingerprint: 'fp-abcdef' }
    ];
    vi.mocked(securityAdminApi.listTrustedDevices).mockResolvedValue(mockDevices);

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="devices" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Company Phone')).toBeInTheDocument();
    });

    // Device is currently not trusted (is_trusted: false), so it renders Approve
    const approveBtn = screen.getByText('Approve');
    fireEvent.click(approveBtn);

    const reasonInput = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
    fireEvent.change(reasonInput, { target: { value: 'Verified ownership' } });

    vi.mocked(securityAdminApi.approveTrustedDevice).mockResolvedValue({
      id: 30, employee_id: '303', label: 'Company Phone', is_trusted: true, revoked_at: null, last_seen_at: '2026-06-18T12:00:00Z', fingerprint: 'fp-abcdef'
    });
    fireEvent.click(screen.getByText('Confirm'));

    await waitFor(() => {
      expect(securityAdminApi.approveTrustedDevice).toHaveBeenCalledWith(30, { reason: 'Verified ownership' });
    });
  });

  it('Admin UI renders safe fingerprint and avoids sensitive hashes', async () => {
    const mockDevices = [
      { id: 30, employee_id: '303', label: 'Company Phone', is_trusted: true, revoked_at: null, last_seen_at: '2026-06-18T12:00:00Z', fingerprint: 'fp-123456' }
    ];
    vi.mocked(securityAdminApi.listTrustedDevices).mockResolvedValue(mockDevices);

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="devices" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Company Phone')).toBeInTheDocument();
    });

    expect(screen.getByText('fp-123456')).toBeInTheDocument();

    const uuidRegex = /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/;
    const rawHashRegex = /[a-fA-F0-9]{32,}/;
    const htmlContent = document.body.innerHTML;

    expect(uuidRegex.test(htmlContent)).toBe(false);
    expect(rawHashRegex.test(htmlContent)).toBe(false);
    expect(htmlContent).not.toContain('eyJ');
    expect(htmlContent).not.toContain('sid_');
    expect(htmlContent).not.toContain('jti_');
  });

  it('Dashboard renders counts when security events exist', async () => {
    vi.mocked(securityAdminApi.getSecuritySummary).mockResolvedValue({
      audit_policy_violations: 7,
      enforced_policy_denials: 6,
      denied_logins: 2,
      denied_protected_requests: 4,
      revoked_sessions: 1,
      revoked_devices: 3,
      cancelled_shifts: 5,
      websocket_security_closes: 6
    });

    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('count-audit_policy_violations')).toHaveTextContent('7');
      expect(screen.getByTestId('count-enforced_policy_denials')).toHaveTextContent('6');
      expect(screen.getByTestId('count-denied_logins')).toHaveTextContent('2');
      expect(screen.getByTestId('count-denied_protected_requests')).toHaveTextContent('4');
      expect(screen.getByTestId('count-revoked_sessions')).toHaveTextContent('1');
      expect(screen.getByTestId('count-revoked_devices')).toHaveTextContent('3');
      expect(screen.getByTestId('count-cancelled_shifts')).toHaveTextContent('5');
      expect(screen.getByTestId('count-websocket_security_closes')).toHaveTextContent('6');
    });

    expect(screen.getByText('Audit-only violations')).toBeInTheDocument();
    expect(screen.getByText('Enforced denials')).toBeInTheDocument();
    expect(screen.getByText('Login denials')).toBeInTheDocument();
    expect(screen.getByText('Request denials')).toBeInTheDocument();
    expect(screen.getByText('Revoked sessions')).toBeInTheDocument();
    expect(screen.getByText('Revoked devices')).toBeInTheDocument();
    expect(screen.getByText('Cancelled shifts')).toBeInTheDocument();
    expect(screen.getByText('WebSocket closes')).toBeInTheDocument();
  });

  it('Dashboard renders loading state during fetch', async () => {
    let resolvePromise: any;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    vi.mocked(securityAdminApi.getSecuritySummary).mockReturnValue(promise as any);

    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    expect(screen.getByTestId('summary-loading')).toBeInTheDocument();
    
    // Cleanup/resolve to avoid memory leak or test hanging
    resolvePromise({
      audit_policy_violations: 0,
      enforced_policy_denials: 0,
      denied_logins: 0,
      denied_protected_requests: 0,
      revoked_sessions: 0,
      revoked_devices: 0,
      cancelled_shifts: 0,
      websocket_security_closes: 0
    });
  });

  it('Dashboard renders neutral empty state when no security events occurred', async () => {
    vi.mocked(securityAdminApi.getSecuritySummary).mockResolvedValue({
      audit_policy_violations: 0,
      enforced_policy_denials: 0,
      denied_logins: 0,
      denied_protected_requests: 0,
      revoked_sessions: 0,
      revoked_devices: 0,
      cancelled_shifts: 0,
      websocket_security_closes: 0
    });

    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('summary-empty')).toBeInTheDocument();
    });
    expect(screen.getByText('No security events occurred today.')).toBeInTheDocument();
  });

  it('Dashboard renders safe error state and retry button on fetch failure', async () => {
    vi.mocked(securityAdminApi.getSecuritySummary).mockRejectedValue(new Error('Network error'));

    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('summary-error')).toBeInTheDocument();
    });
    expect(screen.getByText('Failed to fetch security summary')).toBeInTheDocument();

    // Test retry
    vi.mocked(securityAdminApi.getSecuritySummary).mockResolvedValue({
      audit_policy_violations: 0,
      enforced_policy_denials: 0,
      denied_logins: 1,
      denied_protected_requests: 0,
      revoked_sessions: 0,
      revoked_devices: 0,
      cancelled_shifts: 0,
      websocket_security_closes: 0
    });

    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByTestId('count-denied_logins')).toHaveTextContent('1');
    });
  });

  it('Dashboard fetches the summary once on initial render', async () => {
    render(
      <MemoryRouter>
        <AdminSecurity />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(securityAdminApi.getSecuritySummary).toHaveBeenCalledTimes(1);
    });
  });

  it('Investigation tab renders safe security events and supports filters', async () => {
    vi.mocked(securityAdminApi.listSecurityAuditEvents).mockResolvedValue({
      hours: 24,
      limit: 10,
      offset: 0,
      total: 1,
      items: [
        {
          id: 91,
          actor_id: 1,
          actor_email: 'admin@example.com',
          action: 'SESSION_REVOKED',
          target: 'UserSession id=10; employee_id=42',
          subject_employee_id: 42,
          summary: 'Session revoked',
          details: '{"session_id":10,"already_revoked":true}',
          reason: 'Admin investigation',
          success: true,
          created_at: '2026-06-19T00:00:00Z'
        }
      ]
    });

    render(
      <MemoryRouter>
        <AdminSecurity initialTab="events" />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('SESSION_REVOKED')).toBeInTheDocument();
      expect(screen.getByText('Employee 42')).toBeInTheDocument();
      expect(screen.getByText('Session revoked')).toBeInTheDocument();
    });

    expect(screen.getByText('Showing 1 of 1 events')).toBeInTheDocument();
    expect(screen.getByText('Success')).toBeInTheDocument();
  });
});
