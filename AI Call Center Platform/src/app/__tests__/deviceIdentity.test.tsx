/** @vitest-environment node */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getOrCreateDeviceId } from '../lib/deviceIdentity';

class LocalStorageMock {
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

describe('Device ID Generation & Storage', () => {
  const originalCrypto = (global as any).crypto;
  const originalWindow = (global as any).window;
  const originalLocalStorage = (global as any).localStorage;
  let mockLocalStorage: LocalStorageMock;

  beforeEach(() => {
    mockLocalStorage = new LocalStorageMock();
    (global as any).localStorage = mockLocalStorage;
    (global as any).window = global;
    (global as any).window.localStorage = mockLocalStorage;
    vi.restoreAllMocks();
  });

  afterEach(() => {
    // Restore originals
    if (originalCrypto) {
      try {
        Object.defineProperty(global, 'crypto', {
          value: originalCrypto,
          writable: true,
          configurable: true,
        });
      } catch (e) {
        // Fallback if redefine fails
      }
    } else {
      try {
        delete (global as any).crypto;
      } catch (e) {}
    }
    (global as any).window = originalWindow;
    (global as any).localStorage = originalLocalStorage;
  });

  it('generates a stable device ID of at least 32 characters and persists it in localStorage', () => {
    const id1 = getOrCreateDeviceId();
    expect(id1).toBeDefined();
    expect(id1.length).toBeGreaterThanOrEqual(32);

    const id2 = getOrCreateDeviceId();
    expect(id2).toBe(id1);

    expect((global as any).localStorage.getItem('call_rating_device_id')).toBe(id1);
  });

  it('uses crypto.randomUUID when available', () => {
    const mockUUID = '12345678-1234-1234-1234-1234567890ab';
    const mockCrypto = {
      randomUUID: vi.fn().mockReturnValue(mockUUID),
    };
    Object.defineProperty(global, 'crypto', {
      value: mockCrypto,
      writable: true,
      configurable: true,
    });

    const id = getOrCreateDeviceId();
    expect(mockCrypto.randomUUID).toHaveBeenCalled();
    expect(id).toBe(mockUUID);
  });

  it('falls back to crypto.getRandomValues when randomUUID is not available', () => {
    const mockCrypto = {
      getRandomValues: vi.fn().mockImplementation((arr: Uint8Array) => {
        for (let i = 0; i < arr.length; i++) {
          arr[i] = i;
        }
        return arr;
      }),
    };
    Object.defineProperty(global, 'crypto', {
      value: mockCrypto,
      writable: true,
      configurable: true,
    });

    const id = getOrCreateDeviceId();
    expect(mockCrypto.getRandomValues).toHaveBeenCalled();
    // 16 bytes: 000102030405060708090a0b0c0d0e0f
    expect(id).toBe('000102030405060708090a0b0c0d0e0f');
  });

  it('falls back to basic generator (timestamp/random string) when web crypto is unavailable', () => {
    Object.defineProperty(global, 'crypto', {
      value: undefined,
      writable: true,
      configurable: true,
    });

    const id = getOrCreateDeviceId();
    expect(id).toBeDefined();
    expect(id.length).toBeGreaterThanOrEqual(32);
  });

  it('falls back to in-memory ID if localStorage access throws an error', () => {
    // Mock localStorage to throw on access
    vi.spyOn(mockLocalStorage, 'setItem').mockImplementation(() => {
      throw new Error('Local storage is disabled/full');
    });
    vi.spyOn(mockLocalStorage, 'getItem').mockImplementation(() => {
      throw new Error('Local storage is disabled/full');
    });

    const id1 = getOrCreateDeviceId();
    expect(id1).toBeDefined();
    expect(id1.length).toBeGreaterThanOrEqual(32);

    const id2 = getOrCreateDeviceId();
    expect(id2).toBe(id1);
  });
});
