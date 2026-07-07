import type {
  CreateProjectRequest,
  PaginatedResponse,
  Project,
  UpdateProjectRequest,
} from '@veridian/shared-types';

import { apiFetch, authHeaders, getAccessToken, parseError } from '@/lib/api-http';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export async function listProjects(page = 1, pageSize = 20): Promise<PaginatedResponse<Project>> {
  const response = await apiFetch(`${API_URL}/api/v1/projects?page=${page}&pageSize=${pageSize}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createProject(input: CreateProjectRequest): Promise<Project> {
  const response = await apiFetch(`${API_URL}/api/v1/projects`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function deleteProject(projectId: string): Promise<void> {
  const response = await apiFetch(`${API_URL}/api/v1/projects/${projectId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function updateProject(
  projectId: string,
  input: UpdateProjectRequest,
): Promise<Project> {
  const response = await apiFetch(`${API_URL}/api/v1/projects/${projectId}`, {
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
