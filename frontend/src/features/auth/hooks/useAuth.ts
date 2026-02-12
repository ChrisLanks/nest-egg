/**
 * Auth hooks using React Query
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/authApi';
import { useAuthStore } from '../stores/authStore';
import { LoginRequest, RegisterRequest } from '../../../types/auth';
import { queryKeys } from '../../../services/queryClient';

export const useLogin = () => {
  const navigate = useNavigate();
  const { setTokens } = useAuthStore();

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token, data.user);
      navigate('/dashboard');
    },
  });
};

export const useRegister = () => {
  const navigate = useNavigate();
  const { setTokens } = useAuthStore();

  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token, data.user);
      navigate('/dashboard');
    },
  });
};

export const useLogout = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { logout, refreshToken } = useAuthStore();

  return useMutation({
    mutationFn: () => authApi.logout(refreshToken || ''),
    onSuccess: () => {
      logout();
      queryClient.clear();
      navigate('/login');
    },
    onError: () => {
      // Logout locally even if API call fails
      logout();
      queryClient.clear();
      navigate('/login');
    },
  });
};

export const useCurrentUser = () => {
  const { isAuthenticated } = useAuthStore();

  return useQuery({
    queryKey: queryKeys.currentUser,
    queryFn: authApi.getCurrentUser,
    enabled: isAuthenticated,
    retry: false,
  });
};
