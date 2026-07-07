import type {
  AiConversation,
  AiConversationListResponse,
  AiMessage,
  AiMessageListResponse,
  CreateAiConversationRequest,
  WsAiClientMessage,
  WsAiServerMessage,
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

function wsBaseUrl(): string {
  const base = API_URL.replace(/\/$/, '');
  if (base.startsWith('https://')) return `wss://${base.slice('https://'.length)}`;
  if (base.startsWith('http://')) return `ws://${base.slice('http://'.length)}`;
  return base;
}

export async function listProjectConversations(projectId: string): Promise<AiConversation[]> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}/ai/conversations`, {
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AiConversationListResponse;
  return data.items;
}

export async function createProjectConversation(
  projectId: string,
  input: CreateAiConversationRequest = {},
): Promise<AiConversation> {
  const response = await fetch(`${API_URL}/api/v1/projects/${projectId}/ai/conversations`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getConversationMessages(conversationId: string): Promise<AiMessage[]> {
  const response = await fetch(
    `${API_URL}/api/v1/ai/conversations/${conversationId}/messages?pageSize=200`,
    { headers: authHeaders() },
  );
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AiMessageListResponse;
  return data.items;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/ai/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export function connectAiWebSocket(
  conversationId: string,
  handlers: {
    onChunk?: (content: string) => void;
    onDone?: (messageId: string) => void;
    onError?: (message: string) => void;
  },
): WebSocket | null {
  const token = getAccessToken();
  if (!token) return null;

  const ws = new WebSocket(
    `${wsBaseUrl()}/api/v1/ws/ai/${conversationId}?token=${encodeURIComponent(token)}`,
  );

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data as string) as WsAiServerMessage;
      if (msg.type === 'chunk') {
        handlers.onChunk?.(msg.content);
      } else if (msg.type === 'done') {
        handlers.onDone?.(msg.messageId);
      } else if (msg.type === 'error') {
        handlers.onError?.(msg.message);
      }
    } catch {
      handlers.onError?.('Invalid AI response');
    }
  };

  ws.onerror = () => handlers.onError?.('WebSocket connection failed');
  return ws;
}

export function sendAiMessage(
  ws: WebSocket,
  content: string,
  options?: { activeFileId?: string; editorContent?: string },
): void {
  const payload: WsAiClientMessage = {
    type: 'message',
    content,
    ...(options?.activeFileId ? { activeFileId: options.activeFileId } : {}),
    ...(options?.editorContent !== undefined ? { editorContent: options.editorContent } : {}),
  };
  ws.send(JSON.stringify(payload));
}
