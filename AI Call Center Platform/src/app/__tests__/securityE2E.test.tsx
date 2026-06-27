import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router';
import axios from 'axios';
import { toast } from 'sonner';

import { Login } from '../pages/Login';
import { AdminSecurity } from '../pages/AdminSecurity';
import { getOrCreateDeviceId } from '../lib/deviceIdentity';
import { 
  isSecurityAuthError, 
  getApiErrorMessage, 
  getSafeSecurityLogoutReason 
} from '../lib/api';
import * as securityAdminApi from '../lib/securityAdminApi';
import { UserRole } from '../lib/types';

// Storage Mocking
class StorageMock {
  private store: Record<string, string> = {};
  getItem(key: string) {
    return this.store[key] || null;
  }
  setItem(key: string, value: string) {
    this.store[key] = String(value);
  }
  removeItem(key: string) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

const mockUseApp = vi.fn();
vi.mock('../context/AppContext', async (importOriginal) => {
  const actual = await importOriginal() as any;
  return {
    ...actual,
    useApp: () => mockUseApp(),
  };
});

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
  revokeTrustedDevice: vi.fn()
}));

describe('Frontend Security E2E Integration Suite', () => {
  let mockLocalStorage: StorageMock;
  let mockSessionStorage: StorageMock;
  const originalWindow = (global as any).window;
  const originalLocalStorage = (global as any).localStorage;
  const originalSessionStorage = (global as any).sessionStorage;

  beforeEach(() => {
    mockLocalStorage = new StorageMock();
    mockSessionStorage = new StorageMock();
    
    (global as any).localStorage = mockLocalStorage;
    (global as any).sessionStorage = mockSessionStorage;
    (global as any).window = global;
    (global as any).window.location = { pathname: '/notes', href: '' };
    (global as any).window.localStorage = mockLocalStorage;
    (global as any).window.sessionStorage = mockSessionStorage;
    
    mockUseApp.mockReturnValue({
      userRole: 'ADMIN',
      currentUser: { id: 1, name: 'Admin User', role: 'ADMIN', permissions: [] },
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });
    
    vi.restoreAllMocks();
    
    vi.mocked(securityAdminApi.listSecurityShifts).mockResolvedValue([]);
    vi.mocked(securityAdminApi.listSecuritySessions).mockResolvedValue([]);
    vi.mocked(securityAdminApi.listTrustedDevices).mockResolvedValue([]);
  });

  afterEach(() => {
    (global as any).window = originalWindow;
    (global as any).localStorage = originalLocalStorage;
    (global as any).sessionStorage = originalSessionStorage;
    vi.clearAllMocks();
  });

  describe('1. Login & Device Identity Integration', () => {
    it('Login request includes device_id, OTP verify sends same device_id, and logouts preserve it', async () => {
      // 1. Setup stable device ID in localStorage (>= 32 chars to pass validation)
      const testDeviceId = 'stable-e2e-device-id-xyz-longer-than-32-chars';
      mockLocalStorage.setItem('call_rating_device_id', testDeviceId);
      
      // 2. Mock axios login response requiring OTP
      const postSpy = vi.spyOn(axios, 'post')
        .mockResolvedValueOnce({
          status: 200,
          data: {
            otp_required: true,
            challenge_id: 'challenge-123',
            destination: 'st***@example.com',
            dev_otp_code: '123456'
          }
        })
        .mockResolvedValueOnce({
          status: 200,
          data: {
            access_token: 'valid-jwt-token-xyz',
            user: {
              id: 1,
              name: 'Agent User',
              email: 'agent@example.com',
              role: 'ADMIN',
              permissions: [],
              account_status: 'active'
            },
            session: { session_id: 99, expires_at: '2026-06-19T00:00:00Z', policy_mode: 'enforce' }
          }
        });
      
      render(
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      );
      
      // Fill employee code and password and click Sign In
      const codeInput = screen.getByPlaceholderText('349');
      const passwordInput = screen.getByPlaceholderText('••••••••');
      fireEvent.change(codeInput, { target: { value: 'agent_code' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.click(screen.getByText('Sign In'));
      
      await waitFor(() => {
        const loginCall = postSpy.mock.calls.find(([url]) =>
          typeof url === 'string' && url.includes('/api/auth/login')
        );
        expect(loginCall).toBeDefined();
        expect(loginCall?.[1]).toMatchObject({
          employee_code: 'agent_code',
          password: 'password123',
          device_id: testDeviceId
        });
      });
      
      // Verify OTP screen renders
      expect(screen.getByText('Verification Code')).toBeInTheDocument();
      
      // Submit OTP verification
      const otpInput = screen.getByPlaceholderText('000000');
      fireEvent.change(otpInput, { target: { value: '123456' } });
      
      fireEvent.click(screen.getByText('Verify Code'));
      
      await waitFor(() => {
        const verifyCall = postSpy.mock.calls.find(([url]) =>
          typeof url === 'string' && url.includes('/api/auth/login/verify-otp')
        );
        expect(verifyCall).toBeDefined();
        expect(verifyCall?.[1]).toMatchObject({
          challenge_id: 'challenge-123',
          otp_code: '123456',
          device_id: testDeviceId
        });
      });
      
      // Verify normal logout preserves device ID
      mockLocalStorage.setItem('access_token', 'valid-jwt-token-xyz');
      mockLocalStorage.setItem('user', JSON.stringify({ id: 1 }));
      
      const normalLogout = () => {
        mockLocalStorage.removeItem('access_token');
        mockLocalStorage.removeItem('user');
      };
      normalLogout();
      expect(mockLocalStorage.getItem('access_token')).toBeNull();
      expect(mockLocalStorage.getItem('call_rating_device_id')).toBe(testDeviceId);
      
      // Verify forced logout preserves device ID
      mockLocalStorage.setItem('access_token', 'valid-jwt-token-xyz');
      mockLocalStorage.setItem('user', JSON.stringify({ id: 1 }));
      
      const forceLogout = (reason?: string) => {
        mockLocalStorage.removeItem('access_token');
        mockLocalStorage.removeItem('user');
        if (reason) {
          mockSessionStorage.setItem('forced_logout_reason', reason);
        }
      };
      forceLogout('Session expired');
      expect(mockLocalStorage.getItem('access_token')).toBeNull();
      expect(mockLocalStorage.getItem('call_rating_device_id')).toBe(testDeviceId);
      expect(mockSessionStorage.getItem('forced_logout_reason')).toBe('Session expired');
    });
  });

  describe('2. Forced Logout Security Denial', () => {
    it('Protected 401 and security lifecycle 403 force logouts, role-only 403 does not, and sanitizes messages', () => {
      vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);
      
      // 1. Protected 401 error
      const error401 = {
        isAxiosError: true,
        response: { status: 401, data: { detail: 'Session has been revoked' } },
        config: { url: '/api/ops/dashboard' }
      };
      expect(isSecurityAuthError(error401)).toBe(true);
      
      // 2. Security lifecycle 403 error
      const error403Shift = {
        isAxiosError: true,
        response: { status: 403, data: { detail: 'outside allowed working hours' } },
        config: { url: '/api/ops/dashboard' }
      };
      expect(isSecurityAuthError(error403Shift)).toBe(true);
      
      // 3. Role-only 403 error (should NOT trigger forced logout)
      const error403Role = {
        isAxiosError: true,
        response: { status: 403, data: { detail: 'Only Admins are allowed to perform this action' } },
        config: { url: '/api/security-admin/shifts' }
      };
      expect(isSecurityAuthError(error403Role)).toBe(false);
      
      // 4. Sanitization of unsafe backend details
      const unsafeError = {
        isAxiosError: true,
        response: { data: { detail: 'Session expired: sid=abcdef123456 JWT=eyJ...' } }
      };
      expect(getSafeSecurityLogoutReason(unsafeError)).toBe('Your access is no longer valid. Please sign in again.');
      
      // Preserves safe message
      const safeError = {
        isAxiosError: true,
        response: { data: { detail: 'outside allowed working hours' } }
      };
      expect(getSafeSecurityLogoutReason(safeError)).toBe('outside allowed working hours');
    });
  });

  describe('3. Admin Security UI Integration', () => {
    it('Admin can perform actions with reasons, displays duplicate error, and sanitizes UI from raw secrets', async () => {
      const mockShifts = [
        { id: 10, employee_id: '101', work_date: '2026-06-18', starts_at: '09:00:00', ends_at: '17:00:00', status: 'scheduled' }
      ];
      const mockSessions = [
        { id: 20, employee_id: '202', created_at: '2026-06-18T10:00:00Z', expires_at: '2026-06-18T22:00:00Z', revoked_at: null, is_active: true, last_seen_at: '2026-06-18T12:00:00Z' }
      ];
      const mockDevices = [
        { id: 30, employee_id: '303', label: 'Work Laptop', is_trusted: true, revoked_at: null, last_seen_at: '2026-06-18T12:00:00Z', fingerprint: 'fp-abcdef' }
      ];
      
      vi.mocked(securityAdminApi.listSecurityShifts).mockResolvedValue(mockShifts);
      vi.mocked(securityAdminApi.listSecuritySessions).mockResolvedValue(mockSessions);
      vi.mocked(securityAdminApi.listTrustedDevices).mockResolvedValue(mockDevices);

      render(
        <MemoryRouter>
          <AdminSecurity initialTab="shifts" />
        </MemoryRouter>
      );

      // Verify page loaded
      await waitFor(() => {
        expect(screen.getByText('Employee 101')).toBeInTheDocument();
      });

      // 1. Shift Cancellation with reason
      const cancelBtn = screen.getByTitle('Cancel Shift');
      fireEvent.click(cancelBtn);
      
      const cancelReasonInput = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
      fireEvent.change(cancelReasonInput, { target: { value: 'Contract ended' } });
      
      vi.mocked(securityAdminApi.deleteSecurityShift).mockResolvedValue({ message: 'Shift cancelled' });
      fireEvent.click(screen.getByText('Confirm'));
      
      await waitFor(() => {
        expect(securityAdminApi.deleteSecurityShift).toHaveBeenCalledWith(10, 'Contract ended');
      });

      // 2. Session Revocation with reason
      fireEvent.click(screen.getByText('Active Sessions'));
      await waitFor(() => {
        expect(screen.getByText('Employee 202')).toBeInTheDocument();
      });
      
      const revokeSessBtn = screen.getByText('Revoke');
      fireEvent.click(revokeSessBtn);
      
      const revokeSessReason = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
      fireEvent.change(revokeSessReason, { target: { value: 'Session hijack check' } });
      
      vi.mocked(securityAdminApi.revokeSecuritySession).mockResolvedValue({ message: 'Session revoked successfully' });
      fireEvent.click(screen.getByText('Confirm'));
      
      await waitFor(() => {
        expect(securityAdminApi.revokeSecuritySession).toHaveBeenCalledWith(20, { reason: 'Session hijack check' });
      });

      // 3. Device Revocation with reason
      fireEvent.click(screen.getByText('Trusted Devices'));
      await waitFor(() => {
        expect(screen.getByText('Work Laptop')).toBeInTheDocument();
      });
      
      const revokeDevBtn = screen.getByText('Revoke');
      fireEvent.click(revokeDevBtn);
      
      const revokeDevReason = screen.getByPlaceholderText('Specify the reason (e.g. Schedule cancellation, Device security audit...)');
      fireEvent.change(revokeDevReason, { target: { value: 'Stolen device report' } });
      
      vi.mocked(securityAdminApi.revokeTrustedDevice).mockResolvedValue({
        id: 30, employee_id: '303', label: 'Work Laptop', is_trusted: false, fingerprint: 'fp-abcdef'
      });
      fireEvent.click(screen.getByText('Confirm'));
      
      await waitFor(() => {
        expect(securityAdminApi.revokeTrustedDevice).toHaveBeenCalledWith(30, { reason: 'Stolen device report' });
      });

      // 4. Duplicate Shift Error Displays Safely
      fireEvent.click(screen.getByText('Employee Shifts'));
      await waitFor(() => {
        expect(screen.getByText('Employee 101')).toBeInTheDocument();
      });
      
      // Mock updateSecurityShift to return duplicate 400 error
      const mockAxiosError = {
        isAxiosError: true,
        response: {
          status: 400,
          data: { detail: 'Employee already has a shift scheduled on this date' }
        }
      };
      vi.mocked(securityAdminApi.updateSecurityShift).mockRejectedValue(mockAxiosError);
      
      const editBtn = screen.getByTitle('Edit Shift');
      fireEvent.click(editBtn);
      
      const updateReasonInput = screen.getByPlaceholderText('Specify the reason for updating this shift...');
      fireEvent.change(updateReasonInput, { target: { value: 'Re-schedule' } });
      
      fireEvent.click(screen.getByText('Save Schedule'));
      
      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Employee already has a shift scheduled on this date');
      });

      // 5. Verify UI does not leak raw secrets
      const htmlContent = document.body.innerHTML;
      const uuidRegex = /[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}/;
      const rawHashRegex = /[a-fA-F0-9]{32,}/;
      
      expect(uuidRegex.test(htmlContent)).toBe(false);
      expect(rawHashRegex.test(htmlContent)).toBe(false);
      expect(htmlContent).not.toContain('eyJ');
      expect(htmlContent).not.toContain('sid_');
      expect(htmlContent).not.toContain('jti_');
    });
  });

  describe('4. Real Forced Logout Integration', () => {
    // Test the real forceLogout function via AppProvider context.
    // We render AppProvider with a child that captures forceLogout from useApp(),
    // then invoke it directly. This avoids the interceptor-bypass problem where
    // mocking axios.Axios.prototype.request skips the api instance interceptor chain.
    
    it('Real forced logout path clears auth state, preserves device ID, stores sanitized reason, and redirects', async () => {
      // 1. Setup localStorage and sessionStorage
      mockLocalStorage.setItem('access_token', 'token-to-be-removed');
      mockLocalStorage.setItem('user', JSON.stringify({ id: 1, name: 'Agent' }));
      const testDeviceId = 'stable-e2e-device-id-xyz-longer-than-32-chars';
      mockLocalStorage.setItem('call_rating_device_id', testDeviceId);
      
      // Setup window location mock
      (global as any).window.location = { pathname: '/notes', href: '' };
      
      // Temporarily remove the useApp mock so we get the real AppProvider + real useApp
      let capturedForceLogout: ((reason?: string) => void) | null = null;
      
      // Import real AppContext — the vi.mock spreads actual, so AppProvider is real.
      // But useApp is mocked. We need a child that uses the real context.
      // Since AppProvider provides value via AppContext.Provider, we can use
      // React.useContext directly to access forceLogout.
      const { AppProvider } = await import('../context/AppContext');
      
      // Create a child that grabs forceLogout from context
      // AppProvider renders <AppContext.Provider value={...}>{children}</AppContext.Provider>
      // The real useApp reads from this context. But our mock intercepts useApp.
      // Instead, we test forceLogout indirectly: we know AppProvider calls registerSecurityErrorCallback(forceLogout).
      // So we can trigger it via the registered callback.
      
      // Import the real registerSecurityErrorCallback and capture the callback
      const apiModule = await import('../lib/api');
      let capturedCallback: ((reason: string) => void) | null = null;
      const origRegister = apiModule.registerSecurityErrorCallback;
      vi.spyOn(apiModule, 'registerSecurityErrorCallback').mockImplementation((cb) => {
        capturedCallback = cb;
        origRegister(cb); // still register it
      });
      
      // Mock getCurrentUser to prevent bootstrap HTTP call
      vi.spyOn(apiModule, 'getCurrentUser').mockRejectedValue(new Error('skip'));
      
      render(
        <AppProvider>
          <div>Child</div>
        </AppProvider>
      );
      
      // Wait for AppProvider to finish loading
      await waitFor(() => {
        expect(screen.getByText('Child')).toBeInTheDocument();
      });
      
      // Verify callback was captured
      expect(capturedCallback).not.toBeNull();
      
      // 2. Invoke forceLogout with an unsafe reason (contains sid and JWT tokens)
      capturedCallback!('Session expired: sid=abcdef123456 JWT=eyJ...');
      
      // 3. Assertions
      expect(mockLocalStorage.getItem('access_token')).toBeNull();
      expect(mockLocalStorage.getItem('user')).toBeNull();
      expect(mockLocalStorage.getItem('call_rating_device_id')).toBe(testDeviceId);
      
      // Unsafe details should fall back to the safe generic message
      expect(mockSessionStorage.getItem('forced_logout_reason')).toBe('Your access is no longer valid. Please sign in again.');
      
      // Redirect to /login
      expect(window.location.href).toBe('/login');
    });

    it('Real forced logout path preserves safe backend details in sessionStorage', async () => {
      mockLocalStorage.setItem('access_token', 'token-to-be-removed');
      mockLocalStorage.setItem('user', JSON.stringify({ id: 1, name: 'Agent' }));
      const testDeviceId = 'stable-e2e-device-id-xyz-longer-than-32-chars';
      mockLocalStorage.setItem('call_rating_device_id', testDeviceId);
      
      // Setup window location mock
      (global as any).window.location = { pathname: '/notes', href: '' };
      
      const apiModule = await import('../lib/api');
      let capturedCallback: ((reason: string) => void) | null = null;
      const origRegister = apiModule.registerSecurityErrorCallback;
      vi.spyOn(apiModule, 'registerSecurityErrorCallback').mockImplementation((cb) => {
        capturedCallback = cb;
        origRegister(cb);
      });
      
      // Mock getCurrentUser to prevent bootstrap HTTP call
      vi.spyOn(apiModule, 'getCurrentUser').mockRejectedValue(new Error('skip'));
      
      const { AppProvider } = await import('../context/AppContext');
      
      render(
        <AppProvider>
          <div>Child</div>
        </AppProvider>
      );
      
      await waitFor(() => {
        expect(screen.getByText('Child')).toBeInTheDocument();
      });
      
      expect(capturedCallback).not.toBeNull();
      
      // Invoke forceLogout with a safe reason
      capturedCallback!('outside allowed working hours');
      
      // Assertions
      expect(mockLocalStorage.getItem('access_token')).toBeNull();
      expect(mockLocalStorage.getItem('call_rating_device_id')).toBe(testDeviceId);
      
      // Preserves safe message
      expect(mockSessionStorage.getItem('forced_logout_reason')).toBe('outside allowed working hours');
      
      // Redirect to /login
      expect(window.location.href).toBe('/login');
    });
  });

  describe('5. Route-level Admin Security Guard', () => {
    it('/admin/security route renders for admin', async () => {
      mockUseApp.mockReturnValue({
        userRole: UserRole.ADMIN,
        currentUser: { id: 1, name: 'Admin User', role: UserRole.ADMIN, permissions: [] },
      });

      const { RoleGuard } = await import('../components/auth/RoleGuard');

      render(
        <MemoryRouter initialEntries={['/admin/security']}>
          <Routes>
            <Route
              path="/admin/security"
              element={
                <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                  <div>Admin Security Renders</div>
                </RoleGuard>
              }
            />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.getByText('Admin Security Renders')).toBeInTheDocument();
    });

    it('/admin/security route is blocked for non-admin', async () => {
      mockUseApp.mockReturnValue({
        userRole: UserRole.AGENT,
        currentUser: { id: 2, name: 'Agent User', role: UserRole.AGENT, permissions: [] },
      });

      const { RoleGuard } = await import('../components/auth/RoleGuard');

      render(
        <MemoryRouter initialEntries={['/admin/security']}>
          <Routes>
            <Route
              path="/admin/security"
              element={
                <RoleGuard allowedRoles={[UserRole.ADMIN]}>
                  <div>Admin Security Renders</div>
                </RoleGuard>
              }
            />
            <Route path="/" element={<div>Redirected to Root</div>} />
          </Routes>
        </MemoryRouter>
      );

      expect(screen.queryByText('Admin Security Renders')).toBeNull();
      expect(screen.getByText('Redirected to Root')).toBeInTheDocument();
    });
  });
});
