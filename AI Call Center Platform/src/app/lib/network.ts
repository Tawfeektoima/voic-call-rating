const LOCAL_API_BASE_URL = 'http://localhost:8000';

export const getApiBaseUrl = (): string => {
  const explicitBaseUrl = String(import.meta.env.VITE_API_BASE_URL || '').trim();
  if (explicitBaseUrl) {
    return explicitBaseUrl.replace(/\/$/, '');
  }

  if (typeof window === 'undefined') {
    return LOCAL_API_BASE_URL;
  }

  const hostname = window.location.hostname.toLowerCase();
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '[::1]') {
    return LOCAL_API_BASE_URL;
  }

  return window.location.origin.replace(/\/$/, '');
};

export const getWebSocketBaseUrl = (): string => getApiBaseUrl().replace(/^http/i, 'ws');
