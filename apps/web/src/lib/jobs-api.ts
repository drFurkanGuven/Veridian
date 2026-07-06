import type {
  ArtifactMeta,
  CompilationJob,
  CompileRequest,
  CompileResponse,
  JobLogEntry,
  JobStatus,
  SimulateRequest,
  SimulateResponse,
  SimulationJob,
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

function wsBaseUrl(): string {
  const base = API_URL.replace(/\/$/, '');
  if (base.startsWith('https://')) return `wss://${base.slice('https://'.length)}`;
  if (base.startsWith('http://')) return `ws://${base.slice('http://'.length)}`;
  return base;
}

export async function startCompilation(
  projectId: string,
  input: CompileRequest,
): Promise<CompileResponse> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}/compile`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function startSimulation(
  projectId: string,
  input: SimulateRequest,
): Promise<SimulateResponse> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}/simulate`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getJob(jobId: string): Promise<CompilationJob | SimulationJob> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getJobLogs(jobId: string): Promise<JobLogEntry[]> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/logs`, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return data.items;
}

export async function getJobArtifacts(jobId: string): Promise<ArtifactMeta[]> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}/artifacts`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = await response.json();
  return data.items;
}

export async function downloadArtifact(downloadUrl: string, filename: string): Promise<void> {
  const response = await fetch(downloadUrl, { headers: authHeaders() });
  if (!response.ok) throw new Error(await parseError(response));
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = href;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(href);
}

export function connectJobWebSocket(
  jobId: string,
  handlers: {
    onLog?: (entry: JobLogEntry) => void;
    onProgress?: (percent: number) => void;
    onStatus?: (status: JobStatus) => void;
    onArtifact?: (artifact: ArtifactMeta) => void;
    onError?: () => void;
  },
): WebSocket | null {
  const token = getAccessToken();
  if (!token) return null;

  const ws = new WebSocket(`${wsBaseUrl()}/api/v1/ws/jobs/${jobId}?token=${encodeURIComponent(token)}`);

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data as string) as
        | { type: 'log'; sequence: number; level: JobLogEntry['level']; message: string }
        | { type: 'progress'; percent: number }
        | { type: 'status'; status: JobStatus }
        | { type: 'artifact'; artifact: ArtifactMeta };

      if (msg.type === 'log') {
        handlers.onLog?.({
          sequence: msg.sequence,
          level: msg.level,
          message: msg.message,
          createdAt: new Date().toISOString(),
        });
      } else if (msg.type === 'progress') {
        handlers.onProgress?.(msg.percent);
      } else if (msg.type === 'status') {
        handlers.onStatus?.(msg.status);
      } else if (msg.type === 'artifact') {
        handlers.onArtifact?.(msg.artifact);
      }
    } catch {
      handlers.onError?.();
    }
  };

  ws.onerror = () => handlers.onError?.();
  return ws;
}
