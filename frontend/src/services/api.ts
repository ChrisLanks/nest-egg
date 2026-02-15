/**
 * Axios API client with JWT token management
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// Create axios instance
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token refresh timer
let refreshTimer: NodeJS.Timeout | null = null;

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
    console.error('[Auth] Failed to decode token:', error);
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
    console.error('[Auth] Could not decode token expiration');
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
    console.log('[Auth] Token expired or expiring soon, refreshing immediately...');
    refreshTokenNow();
    return;
  }

  const refreshInMinutes = Math.round(timeUntilRefresh / 60000);
  console.log(`[Auth] Scheduling token refresh in ${refreshInMinutes} minutes`);

  refreshTimer = setTimeout(async () => {
    refreshTokenNow();
  }, timeUntilRefresh);
};

// Refresh token immediately
const refreshTokenNow = async () => {
  try {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      console.error('[Auth] No refresh token available');
      return;
    }

    console.log('[Auth] Refreshing token...');
    const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    console.log('[Auth] Token refreshed successfully');

    // Schedule next refresh
    scheduleTokenRefresh();
  } catch (error) {
    console.error('[Auth] Token refresh failed:', error);
    // Don't clear localStorage here - let the response interceptor handle it
  }
};

// Start token refresh on initial load if user is logged in
const initToken = localStorage.getItem('access_token');
if (initToken) {
  // Check if token is still valid
  if (isTokenExpired(initToken, 5)) {
    console.log('[Auth] Token expired on page load, attempting refresh...');
    refreshTokenNow();
  } else {
    console.log('[Auth] Valid token found, scheduling refresh');
    scheduleTokenRefresh();
  }
}

// Request interceptor to add JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');

    // Log all API requests
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data,
    });

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => {
    console.log(`[API] ✅ ${response.config.method?.toUpperCase()} ${response.config.url}`, {
      status: response.status,
      data: response.data,
    });
    return response;
  },
  async (error) => {
    console.error(`[API] ❌ ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
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
          console.log('[Auth] No refresh token found, redirecting to login');
          localStorage.clear();
          window.location.href = '/login';
          return Promise.reject(error);
        }

        console.log('[Auth] Access token expired, attempting to refresh...');

        // Try to refresh access token
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;

        // Save new access token
        localStorage.setItem('access_token', access_token);

        console.log('[Auth] Token refreshed successfully, retrying original request');

        // Retry original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }

        return api(originalRequest);
      } catch (refreshError: any) {
        // Refresh failed, clear tokens and redirect to login
        const errorMessage = refreshError.response?.data?.detail || refreshError.message;
        console.error('[Auth] Token refresh failed:', errorMessage);
        console.log('[Auth] Clearing tokens and redirecting to login');
        localStorage.clear();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
