/**
 * Axios API client with JWT token management
 *
 * Security model:
 * - Access token: held in Zustand memory only (not localStorage)
 * - Refresh token: httpOnly cookie managed by the browser (not accessible to JS)
 * - withCredentials: true so the browser sends the refresh cookie on /auth/refresh
 */

import axios from 'axios';
import { useAuthStore } from '../features/auth/stores/authStore';

// In dev the Vite proxy rewrites /api → http://localhost:8000/api so cookies
// are same-origin.  In production the backend and frontend share a domain.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Development mode logger - only logs in development
const isDev = import.meta.env.DEV;
const devLog = (...args: any[]) => {
  if (isDev) {
    console.log(...args);
  }
};
const devError = (...args: any[]) => {
  if (isDev) {
    console.error(...args);
  }
};

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send httpOnly refresh cookie on every request
});

// Token refresh timer and in-flight promise
let refreshTimer: NodeJS.Timeout | null = null;

/** Cancel any pending proactive token refresh. Call this on logout. */
export const clearTokenRefresh = () => {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
};
let isRefreshing = false;
let refreshPromise: Promise<string | null> | null = null;

// Decode JWT token to get expiration time
const decodeToken = (token: string): { exp: number } | null => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (error) {
    devError('[Auth] Failed to decode token:', error);
    return null;
  }
};

// Check if token is expired or will expire soon
const isTokenExpired = (token: string, bufferMinutes: number = 0): boolean => {
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) return true;

  const expirationTime = decoded.exp * 1000; // Convert to milliseconds
  const now = Date.now();
  const bufferMs = bufferMinutes * 60 * 1000;

  return expirationTime - now <= bufferMs;
};

// Proactively refresh token before it expires
export const scheduleTokenRefresh = (accessToken?: string) => {
  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  const token = accessToken ?? useAuthStore.getState().accessToken;
  if (!token) return;

  // Decode token to get expiration time
  const decoded = decodeToken(token);
  if (!decoded || !decoded.exp) {
    devError('[Auth] Could not decode token expiration');
    return;
  }

  const expirationTime = decoded.exp * 1000; // Convert to milliseconds
  const now = Date.now();
  const timeUntilExpiration = expirationTime - now;

  // Refresh 5 minutes before expiration
  const refreshBuffer = 5 * 60 * 1000; // 5 minutes in ms
  const timeUntilRefresh = timeUntilExpiration - refreshBuffer;

  if (timeUntilRefresh <= 0) {
    devLog('[Auth] Token expired or expiring soon, refreshing immediately...');
    refreshTokenNow();
    return;
  }

  const refreshInMinutes = Math.round(timeUntilRefresh / 60000);
  devLog(`[Auth] Scheduling token refresh in ${refreshInMinutes} minutes`);

  refreshTimer = setTimeout(async () => {
    refreshTokenNow();
  }, timeUntilRefresh);
};

// Refresh token immediately — all concurrent callers share the same in-flight promise
const refreshTokenNow = (): Promise<string | null> => {
  if (isRefreshing && refreshPromise) {
    devLog('[Auth] Token refresh already in progress, waiting for in-flight request...');
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async (): Promise<string | null> => {
    try {
      devLog('[Auth] Refreshing token via httpOnly cookie...');
      // No body needed — browser sends the httpOnly refresh cookie automatically
      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {}, {
        withCredentials: true,
      });

      const { access_token, user } = response.data;

      // Update Zustand store (in-memory only — no localStorage)
      const store = useAuthStore.getState();
      if (user) {
        store.setTokens(access_token, user);
      } else {
        store.setAccessToken(access_token);
      }
      devLog('[Auth] Token refreshed successfully');

      return access_token;
    } catch (error: any) {
      const errorDetail = error?.response?.data?.detail || error.message || 'Unknown error';
      devError('[Auth] Token refresh failed:', errorDetail);
      return null;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};

// Read a cookie value by name
const getCookie = (name: string): string | undefined => {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : undefined;
};

// Request interceptor to add JWT token, CSRF token, and check expiration
api.interceptors.request.use(
  async (config) => {
    const token = useAuthStore.getState().accessToken;

    // Attach CSRF token from cookie for state-changing requests
    const method = config.method?.toUpperCase();
    if (method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
      const csrfToken = getCookie('csrf_token');
      if (csrfToken && config.headers) {
        config.headers['X-CSRF-Token'] = csrfToken;
      }
    }

    // Log all API requests (mask sensitive data)
    const logData = config.url?.includes('/auth/')
      ? { ...config.data, password: '***' }
      : config.data;

    devLog(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: logData,
    });

    // Skip token refresh for auth endpoints
    const isAuthEndpoint = config.url?.includes('/auth/login') ||
                          config.url?.includes('/auth/register') ||
                          config.url?.includes('/auth/refresh');

    if (token && !isAuthEndpoint) {
      // Check if token will expire soon (within 2 minutes)
      if (isTokenExpired(token, 2)) {
        devLog('[API] Token expiring soon, refreshing before request...');
        try {
          const newToken = await refreshTokenNow();
          if (newToken && config.headers) {
            config.headers.Authorization = `Bearer ${newToken}`;
          } else if (config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        } catch (error) {
          devError('[API] Pre-request token refresh failed:', error);
          if (config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
      } else if (config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    return config;
  },
  (error) => {
    devError('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => {
    devLog(`[API] ✅ ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  async (error) => {
    devError(`[API] ❌ ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    });
    const originalRequest = error.config;

    // On 401, attempt silent refresh via httpOnly cookie.
    // Also handle 403 when we have no access token in memory — FastAPI's
    // HTTPBearer raises 403 (not 401) when the Authorization header is absent.
    // Skip for auth endpoints — errors there are credential failures, not expiry.
    const isAuthEndpoint = originalRequest?.url?.includes('/auth/login') ||
                           originalRequest?.url?.includes('/auth/register') ||
                           originalRequest?.url?.includes('/auth/forgot-password') ||
                           originalRequest?.url?.includes('/auth/reset-password');

    const isMissingToken =
      error.response?.status === 403 && !useAuthStore.getState().accessToken;

    if (
      (error.response?.status === 401 || isMissingToken) &&
      !originalRequest?._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;

      try {
        devLog('[Auth] Access token expired, attempting silent refresh...');
        const newToken = await refreshTokenNow();

        if (!newToken) {
          devLog('[Auth] Silent refresh returned no token — logging out');
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        devLog('[Auth] Silent refresh succeeded, retrying original request');
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        return api(originalRequest);
      } catch (refreshError: any) {
        devError('[Auth] Silent refresh failed:', refreshError.response?.data?.detail || refreshError.message);
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
