let inMemoryDeviceId: string | null = null;

function generateRandomString(length: number): string {
  const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

export function getOrCreateDeviceId(): string {
  const KEY = 'call_rating_device_id';

  // Helper to check localStorage availability
  const isLocalStorageAvailable = (): boolean => {
    try {
      if (typeof window === 'undefined' || !window.localStorage) {
        return false;
      }
      const testKey = '__storage_test__';
      window.localStorage.setItem(testKey, testKey);
      window.localStorage.removeItem(testKey);
      return true;
    } catch (e) {
      return false;
    }
  };

  const hasLocalStorage = isLocalStorageAvailable();

  if (hasLocalStorage) {
    try {
      const stored = window.localStorage.getItem(KEY);
      if (stored && stored.length >= 32) {
        return stored;
      }
    } catch (e) {
      console.warn('Failed to read device_id from localStorage:', e);
    }
  } else {
    if (inMemoryDeviceId) {
      return inMemoryDeviceId;
    }
  }

  // Generate new ID
  let newId = '';
  try {
    const webCrypto = typeof window !== 'undefined' ? (window.crypto || (window as any).msCrypto) : (typeof crypto !== 'undefined' ? crypto : null);
    if (webCrypto) {
      if (typeof webCrypto.randomUUID === 'function') {
        newId = webCrypto.randomUUID(); // 36 characters (UUIDv4)
      } else if (typeof webCrypto.getRandomValues === 'function') {
        const bytes = new Uint8Array(16);
        webCrypto.getRandomValues(bytes);
        newId = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join(''); // 32 characters hex
      }
    }
  } catch (e) {
    console.warn('Web Crypto API failed, falling back to basic random generation:', e);
  }

  // Fallback to timestamp + random string if Web Crypto is unavailable or fails
  if (!newId || newId.length < 32) {
    const timestamp = Date.now().toString(36);
    const randomPart = generateRandomString(32);
    newId = `${timestamp}-${randomPart}`.substring(0, 64);
  }

  // Persist
  if (hasLocalStorage) {
    try {
      window.localStorage.setItem(KEY, newId);
    } catch (e) {
      console.warn('Failed to write device_id to localStorage:', e);
    }
  } else {
    inMemoryDeviceId = newId;
  }

  return newId;
}
