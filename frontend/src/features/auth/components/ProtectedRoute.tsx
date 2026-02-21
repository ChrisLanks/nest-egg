/**
 * Protected Route component
 *
 * On page reload the access token is gone from memory (it's never persisted to
 * localStorage). If the Zustand store says the user was previously authenticated,
 * we silently call /auth/refresh — the browser sends the httpOnly refresh cookie
 * automatically — to get a new access token before deciding to show or redirect.
 */

import { useEffect, useState } from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { Spinner, Center } from '@chakra-ui/react';

export const ProtectedRoute = () => {
  const { isAuthenticated, isLoading, accessToken, tryRestoreSession } = useAuthStore();
  const [restoring, setRestoring] = useState(false);
  const [restored, setRestored] = useState(false);

  useEffect(() => {
    // If state says authenticated but we have no access token in memory,
    // try to restore via the httpOnly cookie.
    if (isAuthenticated && !accessToken && !restoring && !restored) {
      setRestoring(true);
      tryRestoreSession().finally(() => {
        setRestoring(false);
        setRestored(true);
      });
    } else if (!isAuthenticated || accessToken) {
      setRestored(true);
    }
  }, [isAuthenticated, accessToken]);

  if (isLoading || restoring || !restored) {
    return (
      <Center h="100vh">
        <Spinner size="xl" color="brand.500" />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};
