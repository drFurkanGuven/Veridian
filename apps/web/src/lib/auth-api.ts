import type { AuthResponse, AuthTokens, OAuthProvidersResponse, OAuthUrlResponse } from '@veridian/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail ?? data.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function getAuthProviders(): Promise<OAuthProvidersResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/providers`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
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

export async function completeOAuthCallback(
  provider: 'google' | 'github',
  code: string,
  state: string,
): Promise<AuthResponse> {
  const response = await fetch(`${API_URL}/api/v1/auth/${provider}/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, state }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function saveAuthTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('veridian_access_token', tokens.accessToken);
  localStorage.setItem('veridian_refresh_token', tokens.refreshToken);
}

export function oauthStateKey(provider: 'google' | 'github'): string {
  return `veridian_oauth_state_${provider}`;
}
