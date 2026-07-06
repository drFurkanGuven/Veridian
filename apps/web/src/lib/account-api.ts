import type {
  ChangePasswordRequest,
  UpdateProfileRequest,
  User,
  UserSession,
} from '@veridian/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('veridian_access_token');
}

function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('veridian_refresh_token');
}

function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail ?? data.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function getCurrentUser(): Promise<User> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateProfile(input: UpdateProfileRequest): Promise<User> {
  const response = await fetch(`${API_URL}/api/v1/auth/me`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function changePassword(input: ChangePasswordRequest): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/change-password`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function listSessions(): Promise<UserSession[]> {
  const response = await fetch(`${API_URL}/api/v1/auth/sessions`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return data.items;
}

export async function revokeSession(sessionId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/sessions/${sessionId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function revokeOtherSessions(): Promise<number> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error('No refresh token');
  const response = await fetch(`${API_URL}/api/v1/auth/sessions/revoke-others`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ refreshToken }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return data.revokedCount as number;
}

export function isLoggedIn(): boolean {
  return Boolean(getAccessToken());
}
