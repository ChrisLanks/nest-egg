/**
 * Auth store using Zustand
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '../../../types/user';
import { scheduleTokenRefresh } from '../../../services/api';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  setTokens: (accessToken: string, refreshToken: string, user: User) => void;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      setTokens: (accessToken, refreshToken, user) => {
        // Also store in localStorage for API interceptor
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        // Schedule proactive token refresh
        scheduleTokenRefresh();

        set({
          accessToken,
          refreshToken,
          user,
          isAuthenticated: true,
        });
      },

      setAccessToken: (accessToken) => {
        // Update just the access token (used during refresh)
        localStorage.setItem('access_token', accessToken);

        // Schedule next token refresh
        scheduleTokenRefresh();

        set({
          accessToken,
          isAuthenticated: true,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      logout: () => {
        // Clear localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      setLoading: (loading) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => {
        return (state) => {
          // After Zustand restores persisted state, validate tokens
          if (state && state.isAuthenticated) {
            const accessToken = localStorage.getItem('access_token');
            const refreshToken = localStorage.getItem('refresh_token');

            // If tokens exist in localStorage, user should stay logged in
            // The api.ts will handle token refresh if needed
            if (accessToken && refreshToken) {
              console.log('[Auth] Session restored from storage');
              scheduleTokenRefresh();
            } else {
              // Tokens missing, log out
              console.log('[Auth] Tokens missing, clearing auth state');
              state.logout();
            }
          }
        };
      },
    }
  )
);
