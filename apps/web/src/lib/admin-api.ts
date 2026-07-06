import type {
  AdminUser,
  AuditEventType,
  AuditLogEntry,
  UpdateAdminUserRequest,
  UserRole,
} from '@veridian/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('veridian_access_token');
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

export async function listAdminUsers(
  page = 1,
  pageSize = 20,
  search = '',
): Promise<{ items: AdminUser[]; total: number; hasMore: boolean }> {
  const params = new URLSearchParams({ page: String(page), pageSize: String(pageSize) });
  if (search) params.set('search', search);
  const response = await fetch(`${API_URL}/api/v1/admin/users?${params}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return { items: data.items, total: data.total, hasMore: data.hasMore };
}

export async function getAdminUser(userId: string): Promise<AdminUser> {
  const response = await fetch(`${API_URL}/api/v1/admin/users/${userId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateAdminUser(
  userId: string,
  input: UpdateAdminUserRequest,
): Promise<AdminUser> {
  const response = await fetch(`${API_URL}/api/v1/admin/users/${userId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function listAuditLogs(options: {
  page?: number;
  pageSize?: number;
  userId?: string;
  eventType?: AuditEventType;
}): Promise<{ items: AuditLogEntry[]; total: number; hasMore: boolean }> {
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    pageSize: String(options.pageSize ?? 50),
  });
  if (options.userId) params.set('userId', options.userId);
  if (options.eventType) params.set('eventType', options.eventType);
  const response = await fetch(`${API_URL}/api/v1/admin/audit?${params}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return { items: data.items, total: data.total, hasMore: data.hasMore };
}

export const AUDIT_EVENT_TYPES: AuditEventType[] = [
  'register',
  'login_success',
  'login_failed',
  'oauth_login',
  'logout',
  'password_changed',
  'session_revoked',
  'account_locked',
  'account_disabled',
  'account_enabled',
  'role_changed',
  'profile_updated',
];

export const USER_ROLES: UserRole[] = ['user', 'admin'];
