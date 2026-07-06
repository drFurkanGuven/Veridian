import type { AuthTokens, User } from '@veridian/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
}

export interface OAuthUrlResponse {
  url: string;
  state: string;
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail ?? data.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function registerUser(input: {
  email: string;
  password: string;
  displayName: string;
}): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function loginUser(input: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getOAuthUrl(provider: 'google' | 'github'): Promise<OAuthUrlResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/${provider}/url`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function saveAuthTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('veridian_access_token', tokens.accessToken);
  localStorage.setItem('veridian_refresh_token', tokens.refreshToken);
}
