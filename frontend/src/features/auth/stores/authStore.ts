/**
 * Auth store using Zustand
 *
 * Security model:
 * - Access token lives in memory only (this store, NOT localStorage)
 * - Refresh token lives in an httpOnly cookie set by the backend (not readable by JS)
 * - On page reload: no access token in memory → tryRestoreSession() calls /auth/refresh
 *   which sends the httpOnly cookie automatically → backend returns a new access token
 * - This prevents XSS from stealing the long-lived refresh token
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../../../types/user';
import { scheduleTokenRefresh, clearTokenRefresh } from '../../../services/api';

interface AuthState {
  user: User | null;
  accessToken: string | null;  // Memory only — NOT persisted to localStorage
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setTokens: (accessToken: string, user: User) => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
  tryRestoreSession: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,

      setTokens: (accessToken, user) => {
        // Schedule proactive token refresh
        scheduleTokenRefresh(accessToken);

        set({
          accessToken,
          user,
          isAuthenticated: true,
        });
      },

      setAccessToken: (accessToken) => {
        // Update just the access token (used during silent refresh)
        scheduleTokenRefresh(accessToken);

        set({
          accessToken,
          isAuthenticated: true,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      logout: () => {
        clearTokenRefresh(); // cancel any pending proactive refresh timer
        localStorage.removeItem('nest-egg-view'); // clear persisted view selection
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
        });
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },

      /**
       * Try to restore the session using the httpOnly refresh cookie.
       * Called on app startup when accessToken is null but isAuthenticated is true.
       * Returns true if session was restored successfully.
       */
      tryRestoreSession: async () => {
        try {
          // Lazy import to avoid circular dependency
          const { authApi } = await import('../services/authApi');
          const data = await authApi.refresh();
          const user = data.user ?? get().user;
          if (data.access_token && user) {
            get().setTokens(data.access_token, user);
            return true;
          }
          return false;
        } catch {
          get().logout();
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      // Only persist user + isAuthenticated flag — never tokens
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        return (state) => {
          // Access token is not persisted, so it will always be null after reload.
          // tryRestoreSession() (called in App.tsx) will restore it via the httpOnly cookie.
          if (state) {
            console.log('[Auth] Storage rehydrated — session will be restored via cookie on startup');
          }
        };
      },
    }
  )
);
