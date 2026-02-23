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

export interface MFAChallengeResponse {
  mfa_required: true;
  mfa_token: string;
}

export interface MFAVerifyRequest {
  mfa_token: string;
  code: string;
}

// Login can return either a full token response or an MFA challenge
export type LoginResponse = TokenResponse | MFAChallengeResponse;

export function isMFAChallenge(r: LoginResponse): r is MFAChallengeResponse {
  return (r as MFAChallengeResponse).mfa_required === true;
}
