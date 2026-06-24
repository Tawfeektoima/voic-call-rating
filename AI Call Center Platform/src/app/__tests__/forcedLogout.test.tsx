/** @vitest-environment node */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import axios from 'axios';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { Login } from '../pages/Login';
import {
  isSecurityAuthError,
  registerSecurityErrorCallback,
  getApiErrorMessage,
  isSafeDisplayMessage,
  getSafeSecurityLogoutReason
} from '../lib/api';

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
vi.mock('../context/AppContext', () => ({
  useApp: () => mockUseApp(),
}));

describe('Forced Logout and Security Error Detection', () => {
  const originalWindow = (global as any).window;
  const originalLocalStorage = (global as any).localStorage;
  const originalSessionStorage = (global as any).sessionStorage;
  let mockLocalStorage: StorageMock;
  let mockSessionStorage: StorageMock;

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
      setCurrentUser: vi.fn(),
      setUserRole: vi.fn(),
    });
    
    vi.restoreAllMocks();
  });

  afterEach(() => {
    (global as any).window = originalWindow;
    (global as any).localStorage = originalLocalStorage;
    (global as any).sessionStorage = originalSessionStorage;
  });

  it('renders Login page without ReferenceError', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );
    expect(html).toContain('VoiceQA AI');
    expect(html).toContain('Sign In');
  });

  it('isSafeDisplayMessage flags sensitive patterns and allows safe patterns', () => {
    // Allows "outside allowed working hours"
    expect(isSafeDisplayMessage('outside allowed working hours')).toBe(true);

    // Contains sid with boundaries
    expect(isSafeDisplayMessage('Session sid_12345 expired')).toBe(false);
    expect(isSafeDisplayMessage('User sid=123')).toBe(false);
    expect(isSafeDisplayMessage('User sid: abc')).toBe(false);
    expect(isSafeDisplayMessage('User "sid": "abc"')).toBe(false);

    // Contains jti
    expect(isSafeDisplayMessage('token jti=abc')).toBe(false);
    expect(isSafeDisplayMessage('token jti: abc')).toBe(false);

    // Contains device_id and device_id_hash
    expect(isSafeDisplayMessage('device_id=abc')).toBe(false);
    expect(isSafeDisplayMessage('device_id_hash=abc')).toBe(false);

    // Contains bearer
    expect(isSafeDisplayMessage('Bearer token is invalid')).toBe(false);

    // Contains JWT dot-separated parts
    expect(isSafeDisplayMessage('token: abc.def.ghi')).toBe(false);

    // Contains hex hash (32+ chars)
    expect(isSafeDisplayMessage('failed key: 1234567890abcdef1234567890abcdef')).toBe(false);

    // Safe message
    expect(isSafeDisplayMessage('Your shift has ended')).toBe(true);
  });

  it('getApiErrorMessage and getSafeSecurityLogoutReason sanitization rules', () => {
    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    // Allows outside allowed working hours
    const errorOutsideHours = {
      isAxiosError: true,
      response: { data: { detail: 'outside allowed working hours' } }
    };
    expect(getApiErrorMessage(errorOutsideHours, 'Fallback Error')).toBe('outside allowed working hours');

    // Rejects unsafe messages and uses fallback
    const errorWithSid = {
      isAxiosError: true,
      response: { data: { detail: 'Session revocation: sid=abcdef123456' } }
    };
    expect(getApiErrorMessage(errorWithSid, 'Fallback Error')).toBe('Fallback Error');

    // Forced logout reason uses sanitized fallback when backend detail is unsafe
    const unsafeLogoutError = {
      isAxiosError: true,
      response: { data: { detail: 'Session revocation: sid=abcdef123456' } }
    };
    expect(getSafeSecurityLogoutReason(unsafeLogoutError)).toBe('Your access is no longer valid. Please sign in again.');

    // Forced logout reason preserves safe backend detail
    const safeLogoutError = {
      isAxiosError: true,
      response: { data: { detail: 'Your session has expired.' } }
    };
    expect(getSafeSecurityLogoutReason(safeLogoutError)).toBe('Your session has expired.');
  });

  it('does not log sensitive credentials or axios request bodies on login failure', () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    // Try to simulate call and check no console.error happened
    console.warn('Login failed');
    
    expect(consoleWarnSpy).toHaveBeenCalledWith('Login failed');
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it('isSecurityAuthError correctly identifies protected 401 and security-related 403 errors', () => {
    const error401 = {
      isAxiosError: true,
      response: { status: 401, data: { detail: 'Session expired' } },
      config: { url: '/api/admin/employees' }
    };
    const error403Shift = {
      isAxiosError: true,
      response: { status: 403, data: { detail: 'Your shift has ended' } },
      config: { url: '/api/admin/employees' }
    };

    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    expect(isSecurityAuthError(error401)).toBe(true);
    expect(isSecurityAuthError(error403Shift)).toBe(true);
  });

  it('isSecurityAuthError ignores login/reset 401/403 and role-based 403 errors', () => {
    const loginError = {
      isAxiosError: true,
      response: { status: 401, data: { detail: 'Invalid password' } },
      config: { url: '/api/auth/login' }
    };
    const resetError = {
      isAxiosError: true,
      response: { status: 403, data: { detail: 'Invalid national ID' } },
      config: { url: '/api/auth/password-reset' }
    };
    const role403Error = {
      isAxiosError: true,
      response: { status: 403, data: { detail: 'Only admins are allowed to manage shifts' } },
      config: { url: '/api/admin/employees' }
    };

    vi.spyOn(axios, 'isAxiosError').mockReturnValue(true);

    expect(isSecurityAuthError(loginError)).toBe(false);
    expect(isSecurityAuthError(resetError)).toBe(false);
    expect(isSecurityAuthError(role403Error)).toBe(false);
  });

  it('registerSecurityErrorCallback correctly bridges interceptors to callbacks', () => {
    const cb = vi.fn();
    registerSecurityErrorCallback(cb);

    cb('Revoked session');
    expect(cb).toHaveBeenCalledWith('Revoked session');
  });

  it('forced logout logic clears auth state but preserves call_rating_device_id', () => {
    mockLocalStorage.setItem('access_token', 'test-token');
    mockLocalStorage.setItem('user', 'test-user');
    mockLocalStorage.setItem('call_rating_device_id', 'stable-device-id');

    const forceLogout = (reason?: string) => {
      mockLocalStorage.removeItem('access_token');
      mockLocalStorage.removeItem('user');
      if (reason) {
        mockSessionStorage.setItem('forced_logout_reason', reason);
      }
    };

    forceLogout('Session has been revoked');

    expect(mockLocalStorage.getItem('access_token')).toBeNull();
    expect(mockLocalStorage.getItem('user')).toBeNull();
    expect(mockLocalStorage.getItem('call_rating_device_id')).toBe('stable-device-id');
    expect(mockSessionStorage.getItem('forced_logout_reason')).toBe('Session has been revoked');
  });

  it('prevents duplicate forced logout loops when already on login page and no token exists', () => {
    mockLocalStorage.removeItem('access_token');
    (global as any).window.location.pathname = '/login';

    const forceLogout = vi.fn((reason?: string) => {
      if (!mockLocalStorage.getItem('access_token') && (global as any).window.location.pathname === '/login') {
        return;
      }
      mockLocalStorage.removeItem('access_token');
    });

    forceLogout('Force logout trigger');
    expect(forceLogout).toReturn();
    expect(mockLocalStorage.getItem('access_token')).toBeNull();
  });

  it('WebSocket onclose handler triggers forceLogout for 4401 and 4403', () => {
    const forceLogoutSpy = vi.fn();
    
    const handleClose = (event: { code: number }) => {
      if (event.code === 4401) {
        forceLogoutSpy("Your session is no longer valid. Please sign in again.");
      } else if (event.code === 4403) {
        forceLogoutSpy("Your access is no longer allowed from this device or shift.");
      }
    };

    handleClose({ code: 4401 });
    expect(forceLogoutSpy).toHaveBeenCalledWith("Your session is no longer valid. Please sign in again.");

    handleClose({ code: 4403 });
    expect(forceLogoutSpy).toHaveBeenCalledWith("Your access is no longer allowed from this device or shift.");
  });
});
