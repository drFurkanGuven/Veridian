import type { AiConversation, AiMessage } from '../websocket';

export interface AiConversationListResponse {
  items: AiConversation[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface AiMessageListResponse {
  items: AiMessage[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface CreateAiConversationRequest {
  title?: string;
}
