/**
 * Protected Route component
 *
 * On page reload the access token is gone from memory (it's never persisted to
 * localStorage). If the Zustand store says the user was previously authenticated,
 * we silently call /auth/refresh — the browser sends the httpOnly refresh cookie
 * automatically — to get a new access token before deciding to show or redirect.
 *
 * IMPORTANT: starts in 'checking' state so <Outlet /> is never rendered before
 * the auth check completes, avoiding a race where child components fire API
 * requests before the access token is restored.
 */

import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Spinner, Center } from '@chakra-ui/react';

type AuthState = 'checking' | 'ready' | 'unauthenticated';

export const ProtectedRoute = () => {
  const [authState, setAuthState] = useState<AuthState>('checking');

  useEffect(() => {
    let cancelled = false;

    const doAuth = async () => {
      // Wait for Zustand to finish hydrating from localStorage
      if (!useAuthStore.persist.hasHydrated()) {
        await new Promise<void>((resolve) => {
          const unsub = useAuthStore.persist.onFinishHydration(() => {
            unsub();
            resolve();
          });
        });
      }

      if (cancelled) return;

      const { isAuthenticated, accessToken, tryRestoreSession } =
        useAuthStore.getState();

      if (!isAuthenticated) {
        setAuthState('unauthenticated');
        return;
      }

      if (!accessToken) {
        // Restore session via httpOnly refresh cookie
        const success = await tryRestoreSession();
        if (!cancelled) {
          setAuthState(success ? 'ready' : 'unauthenticated');
        }
      } else {
        setAuthState('ready');
      }
    };

    doAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  if (authState === 'checking') {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (authState === 'unauthenticated') {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
