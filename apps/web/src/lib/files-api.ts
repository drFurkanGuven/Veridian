import type {
  CreateFileRequest,
  CreateFolderRequest,
  FileContent,
  FileNode,
  ProjectTree,
  UpdateFileContentRequest,
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

function projectBase(projectId: string): string {
  return `${API_URL}/api/v1/projects/${projectId}`;
}

export async function getProjectTree(projectId: string): Promise<ProjectTree> {
  const response = await fetch(`${projectBase(projectId)}/tree`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createFolder(
  projectId: string,
  input: CreateFolderRequest,
): Promise<unknown> {
  const response = await fetch(`${projectBase(projectId)}/folders`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function createFile(projectId: string, input: CreateFileRequest): Promise<FileNode> {
  const response = await fetch(`${projectBase(projectId)}/files`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getFileContent(projectId: string, fileId: string): Promise<FileContent> {
  const response = await fetch(`${projectBase(projectId)}/files/${fileId}`, {
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
  const response = await fetch(`${projectBase(projectId)}/files/${fileId}/content`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function deleteFile(projectId: string, fileId: string): Promise<void> {
  const response = await fetch(`${projectBase(projectId)}/files/${fileId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}
