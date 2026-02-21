/**
 * Authentication types
 */

import type { User } from './user';

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
  birth_day?: number;
  birth_month?: number;
  birth_year?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string | null;  // Not in body when using httpOnly cookie
  token_type: string;
  user: User;
}

export interface RefreshTokenRequest {
  refresh_token?: string | null;  // Optional: cookie takes precedence
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  user?: User | null;  // Included on refresh so frontend can restore session
}
