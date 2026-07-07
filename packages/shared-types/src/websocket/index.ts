import type { ArtifactMeta, JobLogEntry, JobStatus, LogLevel } from '../jobs';

export type AiMessageRole = 'user' | 'assistant' | 'system';

export interface AiConversation {
  id: string;
  userId: string;
  projectId: string | null;
  title: string;
  createdAt: string;
  updatedAt: string;
}

export interface AiMessage {
  id: string;
  conversationId: string;
  role: AiMessageRole;
  content: string;
  metadata: Record<string, unknown> | null;
  createdAt: string;
}

export interface CreateConversationRequest {
  projectId?: string;
  title?: string;
}

export interface EditorSelection {
  startLine: number;
  endLine: number;
  startColumn: number;
  endColumn: number;
  text: string;
}

export interface AiBuildContext {
  jobStatus?: JobStatus;
  simulationLogs?: Array<Pick<JobLogEntry, 'level' | 'message'>>;
  projectFiles?: Array<{ path: string; language?: string }>;
  aiToolFeedback?: {
    applied?: string[];
    failed?: Array<{ path: string; error: string }>;
  };
}

export interface AiWriteActiveFileAction {
  action: 'write_active_file';
  content: string;
}

export interface AiWriteFileAction {
  action: 'write_file';
  path: string;
  content: string;
}

export type AiAssistantAction = AiWriteActiveFileAction | AiWriteFileAction;

export interface SendAiMessageRequest {
  content: string;
  activeFileId?: string;
}


export interface WsJobLogMessage {
  type: 'log';
  sequence: number;
  level: LogLevel;
  message: string;
}

export interface WsJobProgressMessage {
  type: 'progress';
  percent: number;
}

export interface WsJobStatusMessage {
  type: 'status';
  status: JobStatus;
}

export interface WsJobArtifactMessage {
  type: 'artifact';
  artifact: ArtifactMeta;
}

export type WsJobMessage =
  | WsJobLogMessage
  | WsJobProgressMessage
  | WsJobStatusMessage
  | WsJobArtifactMessage;

// --- Terminal WebSocket messages ---

export interface WsTerminalOutputMessage {
  type: 'output';
  data: string;
}

export interface WsTerminalInputMessage {
  type: 'input';
  data: string;
}

export interface WsTerminalResizeMessage {
  type: 'resize';
  cols: number;
  rows: number;
}

export type WsTerminalClientMessage = WsTerminalInputMessage | WsTerminalResizeMessage;
export type WsTerminalServerMessage = WsTerminalOutputMessage;

// --- AI WebSocket messages ---

export interface WsAiChunkMessage {
  type: 'chunk';
  content: string;
}

export interface WsAiDoneMessage {
  type: 'done';
  messageId: string;
  metadata: Record<string, unknown>;
}

export interface WsAiErrorMessage {
  type: 'error';
  message: string;
}

export interface WsAiUserMessage {
  type: 'message';
  content: string;
  activeFileId?: string;
  editorContent?: string;
  editorSelection?: EditorSelection;
  buildContext?: AiBuildContext;
}

export type WsAiServerMessage = WsAiChunkMessage | WsAiDoneMessage | WsAiErrorMessage;
export type WsAiClientMessage = WsAiUserMessage;
