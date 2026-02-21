/**
 * Authentication API service
 */

import api from '../../../services/api';
import type {
  RegisterRequest,
  LoginRequest,
  TokenResponse,
  AccessTokenResponse,
} from '../../../types/auth';
import type { User } from '../../../types/user';

export const authApi = {
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/register', data);
    return response.data;
  },

  login: async (data: LoginRequest): Promise<TokenResponse> => {
    console.log('📡 authApi.login called', { email: data.email });
    try {
      const response = await api.post<TokenResponse>('/auth/login', data);
      console.log('📡 authApi.login response received', response.data);
      return response.data;
    } catch (error) {
      console.error('📡 authApi.login error', error);
      throw error;
    }
  },

  refresh: async (): Promise<AccessTokenResponse> => {
    // No body needed — browser sends httpOnly refresh cookie automatically
    const response = await api.post<AccessTokenResponse>('/auth/refresh', {});
    return response.data;
  },

  logout: async (): Promise<void> => {
    // No body needed — backend clears the httpOnly cookie server-side
    await api.post('/auth/logout', {});
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me');
    return response.data;
  },

  verifyEmail: async (token: string): Promise<{ message: string }> => {
    const response = await api.get<{ message: string }>('/auth/verify-email', {
      params: { token },
    });
    return response.data;
  },

  resendVerification: async (): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/auth/resend-verification');
    return response.data;
  },

  forgotPassword: async (email: string): Promise<{ message: string; token?: string }> => {
    const response = await api.post<{ message: string; token?: string }>('/auth/forgot-password', { email });
    return response.data;
  },

  resetPassword: async (token: string, new_password: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>('/auth/reset-password', { token, new_password });
    return response.data;
  },
};
