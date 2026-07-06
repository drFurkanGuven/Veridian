import type {
  CreateProjectRequest,
  PaginatedResponse,
  Project,
  UpdateProjectRequest,
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
    return data.detail ?? response.statusText;
  } catch {
    return response.statusText;
  }
}

export async function listProjects(page = 1, pageSize = 20): Promise<PaginatedResponse<Project>> {
  const response = await fetch(`${API_URL}/api/v1/projects?page=${page}&pageSize=${pageSize}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createProject(input: CreateProjectRequest): Promise<Project> {
  const response = await fetch(`${API_URL}/api/v1/projects`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function updateProject(
  projectId: string,
  input: UpdateProjectRequest,
): Promise<Project> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export function isLoggedIn(): boolean {
  return Boolean(getAccessToken());
}
