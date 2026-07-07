import type {
  CreateFileRequest,
  CreateFolderRequest,
  FileContent,
  FileNode,
  ProjectTree,
  UpdateFileContentRequest,
} from '@veridian/shared-types';

import { apiFetch, authHeaders, parseError } from '@/lib/api-http';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function projectBase(projectId: string): string {
  return `${API_URL}/api/v1/projects/${projectId}`;
}

export async function getProjectTree(projectId: string): Promise<ProjectTree> {
  const response = await apiFetch(`${projectBase(projectId)}/tree`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createFolder(
  projectId: string,
  input: CreateFolderRequest,
): Promise<unknown> {
  const response = await apiFetch(`${projectBase(projectId)}/folders`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createFile(projectId: string, input: CreateFileRequest): Promise<FileNode> {
  const response = await apiFetch(`${projectBase(projectId)}/files`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function upsertFileByPath(
  projectId: string,
  path: string,
  content: string,
): Promise<FileContent> {
  const response = await apiFetch(`${projectBase(projectId)}/files/by-path`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ path: path.replace(/^\//, ''), content }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getFileContent(projectId: string, fileId: string): Promise<FileContent> {
  const response = await apiFetch(`${projectBase(projectId)}/files/${fileId}`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function updateFileContent(
  projectId: string,
  fileId: string,
  input: UpdateFileContentRequest,
): Promise<FileContent> {
  const response = await apiFetch(`${projectBase(projectId)}/files/${fileId}/content`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function renameFile(
  projectId: string,
  fileId: string,
  name: string,
): Promise<FileNode> {
  const response = await apiFetch(`${projectBase(projectId)}/files/${fileId}`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function deleteFile(projectId: string, fileId: string): Promise<void> {
  const response = await apiFetch(`${projectBase(projectId)}/files/${fileId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}
