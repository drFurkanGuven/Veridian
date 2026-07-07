export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('veridian_access_token');
}

export function authHeaders(): HeadersInit {
  const token = getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function parseError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail ?? data.message ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(url, init);
  if (response.status === 401 && typeof window !== 'undefined') {
    localStorage.removeItem('veridian_access_token');
    localStorage.removeItem('veridian_refresh_token');
    window.location.href = '/login';
    throw new Error('Session expired');
  }
  return response;
}
