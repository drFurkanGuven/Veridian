import type {
  AiBuildContext,
  AiConversation,
  AiConversationListResponse,
  AiMessage,
  AiMessageListResponse,
  CreateAiConversationRequest,
  EditorSelection,
  WsAiClientMessage,
  WsAiServerMessage,
} from '@veridian/shared-types';

import { apiFetch, authHeaders, getAccessToken, parseError } from '@/lib/api-http';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

function wsBaseUrl(): string {
  const base = API_URL.replace(/\/$/, '');
  if (base.startsWith('https://')) return `wss://${base.slice('https://'.length)}`;
  if (base.startsWith('http://')) return `ws://${base.slice('http://'.length)}`;
  return base;
}

export async function listProjectConversations(projectId: string): Promise<AiConversation[]> {
  const response = await apiFetch(`${API_URL}/api/v1/projects/${projectId}/ai/conversations`, {
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
  const response = await apiFetch(`${API_URL}/api/v1/projects/${projectId}/ai/conversations`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(input),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json();
}

export async function getConversationMessages(conversationId: string): Promise<AiMessage[]> {
  const response = await apiFetch(
    `${API_URL}/api/v1/ai/conversations/${conversationId}/messages?pageSize=200`,
    { headers: authHeaders() },
  );
  if (!response.ok) throw new Error(await parseError(response));
  const data = (await response.json()) as AiMessageListResponse;
  return data.items;
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const response = await apiFetch(`${API_URL}/api/v1/ai/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export function connectAiWebSocket(
  conversationId: string,
  handlers: {
    onChunk?: (content: string) => void;
    onDone?: (messageId: string, metadata: Record<string, unknown>) => void;
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
        handlers.onDone?.(msg.messageId, msg.metadata);
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
  options?: {
    activeFileId?: string;
    editorContent?: string;
    editorSelection?: EditorSelection;
    buildContext?: AiBuildContext;
  },
): void {
  const payload: WsAiClientMessage = {
    type: 'message',
    content,
    ...(options?.activeFileId ? { activeFileId: options.activeFileId } : {}),
    ...(options?.editorContent !== undefined ? { editorContent: options.editorContent } : {}),
    ...(options?.editorSelection ? { editorSelection: options.editorSelection } : {}),
    ...(options?.buildContext ? { buildContext: options.buildContext } : {}),
  };
  ws.send(JSON.stringify(payload));
}
