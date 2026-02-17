/**
 * Axios API client with JWT token management
 */

import axios from 'axios';
import { useAuthStore } from '../features/auth/stores/authStore';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

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
});

// Token refresh timer and flag
let refreshTimer: NodeJS.Timeout | null = null;
let isRefreshing = false;

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
export const scheduleTokenRefresh = () => {
  // Clear existing timer
  if (refreshTimer) {
    clearTimeout(refreshTimer);
  }

  const accessToken = localStorage.getItem('access_token');
  if (!accessToken) return;

  // Decode token to get expiration time
  const decoded = decodeToken(accessToken);
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
    // Token already expired or will expire very soon, refresh immediately
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

// Refresh token immediately
const refreshTokenNow = async (): Promise<string | null> => {
  // Prevent concurrent refresh attempts
  if (isRefreshing) {
    devLog('[Auth] Token refresh already in progress, waiting...');
    // Wait a bit and return the token from storage (it should be updated by the in-flight request)
    await new Promise(resolve => setTimeout(resolve, 1000));
    return localStorage.getItem('access_token');
  }

  try {
    isRefreshing = true;
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      devError('[Auth] No refresh token available');
      return null;
    }

    devLog('[Auth] Refreshing token...');
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const { access_token } = response.data;

    // Update both localStorage and Zustand store
    useAuthStore.getState().setAccessToken(access_token);
    devLog('[Auth] Token refreshed successfully and auth store updated');

    // Schedule next refresh (handled by setAccessToken)
    return access_token;
  } catch (error: any) {
    const errorDetail = error?.response?.data?.detail || error.message || 'Unknown error';
    devError('[Auth] Token refresh failed. Backend error:', errorDetail);
    devError('[Auth] Full error:', error);
    // Don't clear localStorage here - let the response interceptor handle it
    return null;
  } finally {
    isRefreshing = false;
  }
};

// Start token refresh on initial load if user is logged in
const initToken = localStorage.getItem('access_token');
if (initToken) {
  // Check if token is still valid
  if (isTokenExpired(initToken, 5)) {
    devLog('[Auth] Token expired on page load, attempting refresh...');
    refreshTokenNow();
  } else {
    devLog('[Auth] Valid token found, scheduling refresh');
    scheduleTokenRefresh();
  }
}

// Request interceptor to add JWT token and check expiration
api.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem('access_token');

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

    devLog('[API] Auth endpoint check:', { url: config.url, isAuthEndpoint, hasToken: !!token });

    if (token && !isAuthEndpoint) {
      // Check if token will expire soon (within 2 minutes)
      if (isTokenExpired(token, 2)) {
        devLog('[API] Token expiring soon, refreshing before request...');
        try {
          const newToken = await refreshTokenNow();
          if (newToken && config.headers) {
            config.headers.Authorization = `Bearer ${newToken}`;
            devLog('[API] Using refreshed token for request');
          } else {
            // Refresh failed, use old token and let response interceptor handle it
            if (config.headers) {
              config.headers.Authorization = `Bearer ${token}`;
            }
          }
        } catch (error) {
          devError('[API] Pre-request token refresh failed:', error);
          // Let the request continue - the response interceptor will handle it
          if (config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }
      } else if (config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }

    devLog('[API] Request interceptor complete, sending request...');
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
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
    });
    const originalRequest = error.config;

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');

        if (!refreshToken) {
          // No refresh token, redirect to login
          devLog('[Auth] No refresh token found, redirecting to login');
          useAuthStore.getState().logout();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        devLog('[Auth] Access token expired, attempting to refresh...');

        // Try to refresh access token
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;

        // Update both localStorage and Zustand store
        useAuthStore.getState().setAccessToken(access_token);

        devLog('[Auth] Token refreshed successfully and auth store updated, retrying original request');

        // Retry original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return api(originalRequest);
      } catch (refreshError: any) {
        // Refresh failed, clear tokens and redirect to login
        const errorMessage = refreshError.response?.data?.detail || refreshError.message;
        devError('[Auth] Token refresh failed:', errorMessage);
        devLog('[Auth] Clearing tokens and redirecting to login');
        useAuthStore.getState().logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
