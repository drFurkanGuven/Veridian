'use client';

import type { AiConversation, AiMessage } from '@veridian/shared-types';
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  connectAiWebSocket,
  createProjectConversation,
  getConversationMessages,
  listProjectConversations,
  sendAiMessage,
} from '@/lib/ai-api';

interface AiChatPanelProps {
  projectId: string;
  activeFileId?: string | null;
  activeFilePath?: string | null;
  editorContent?: string;
  onApplyToEditor?: (content: string) => void;
  onApplyAndSave?: (content: string) => void;
  className?: string;
}

interface ChatEntry {
  id: string;
  role: AiMessage['role'];
  content: string;
  streaming?: boolean;
}

function conversationStorageKey(projectId: string): string {
  return `veridian:ai-conversation:${projectId}`;
}

function extractPrimaryCodeBlock(content: string): string | null {
  const match = content.match(/```(?:\w+)?\n([\s\S]*?)```/);
  return match?.[1]?.trim() ?? null;
}

const QUICK_PROMPTS = [
  'Explain this file',
  'Fix errors in this code',
  'Add $dumpfile to this testbench',
];

export function AiChatPanel({
  projectId,
  activeFileId,
  activeFilePath,
  editorContent,
  onApplyToEditor,
  onApplyAndSave,
  className = '',
}: AiChatPanelProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const editorContentRef = useRef(editorContent ?? '');
  const activeFileIdRef = useRef(activeFileId);
  const [conversation, setConversation] = useState<AiConversation | null>(null);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  editorContentRef.current = editorContent ?? '';
  activeFileIdRef.current = activeFileId;

  const scrollToBottom = useCallback(() => {
    const container = messagesRef.current;
    if (!container) return;
    container.scrollTop = container.scrollHeight;
  }, []);

  const loadConversation = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const storageKey = conversationStorageKey(projectId);
      const storedId = localStorage.getItem(storageKey);
      const conversations = await listProjectConversations(projectId);
      const current =
        conversations.find((item) => item.id === storedId) ??
        conversations[0] ??
        (await createProjectConversation(projectId, { title: 'Project chat' }));
      localStorage.setItem(storageKey, current.id);
      setConversation(current);
      const history = await getConversationMessages(current.id);
      setMessages(
        history.map((message) => ({
          id: message.id,
          role: message.role,
          content: message.content,
        })),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load AI chat');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadConversation().catch(() => undefined);
    return () => {
      wsRef.current?.close();
    };
  }, [loadConversation]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending, scrollToBottom]);

  async function startNewChat() {
    setError('');
    try {
      const created = await createProjectConversation(projectId, { title: 'New chat' });
      localStorage.setItem(conversationStorageKey(projectId), created.id);
      setConversation(created);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start new chat');
    }
  }

  async function handleSend(prompt?: string) {
    const text = (prompt ?? input).trim();
    if (!text || !conversation || sending) return;

    setInput('');
    setSending(true);
    setError('');

    const userEntry: ChatEntry = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
    };
    const assistantEntry: ChatEntry = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      streaming: true,
    };
    setMessages((prev) => [...prev, userEntry, assistantEntry]);

    wsRef.current?.close();
    const ws = connectAiWebSocket(conversation.id, {
      onChunk: (chunk) => {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantEntry.id
              ? { ...message, content: message.content + chunk }
              : message,
          ),
        );
      },
      onDone: (messageId) => {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantEntry.id
              ? { ...message, id: messageId || message.id, streaming: false }
              : message,
          ),
        );
        setSending(false);
      },
      onError: (message) => {
        setError(message);
        setMessages((prev) =>
          prev.map((entry) =>
            entry.id === assistantEntry.id
              ? {
                  ...entry,
                  content: entry.content || message,
                  streaming: false,
                }
              : entry,
          ),
        );
        setSending(false);
      },
    });

    if (!ws) {
      setError('Not authenticated');
      setSending(false);
      return;
    }

    wsRef.current = ws;
    ws.onopen = () => {
      sendAiMessage(ws, text, {
        activeFileId: activeFileIdRef.current ?? undefined,
        editorContent: editorContentRef.current,
      });
    };
  }

  if (loading) {
    return (
      <div className={`flex flex-1 items-center justify-center text-sm text-ide-muted ${className}`}>
        Loading AI…
      </div>
    );
  }

  return (
    <div className={`flex min-h-0 flex-1 flex-col overflow-hidden ${className}`}>
      <div className="mb-2 flex shrink-0 items-center gap-2">
        {activeFilePath ? (
          <p className="min-w-0 flex-1 truncate text-xs text-ide-muted">
            <span className="font-mono text-ide-text">{activeFilePath}</span>
            <span className="ml-1 text-ide-muted">(live editor)</span>
          </p>
        ) : (
          <p className="flex-1 text-xs text-yellow-400/90">Open a file for AI code edits.</p>
        )}
        <button
          type="button"
          onClick={() => {
            startNewChat().catch(() => undefined);
          }}
          className="shrink-0 rounded border border-ide-border px-2 py-0.5 text-[10px] text-ide-muted hover:bg-ide-sidebar"
        >
          New chat
        </button>
      </div>

      {error && <p className="mb-2 shrink-0 text-xs text-red-400">{error}</p>}

      <div className="mb-2 flex shrink-0 flex-wrap gap-1">
        {QUICK_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            disabled={sending || !activeFileId}
            onClick={() => {
              handleSend(prompt).catch(() => undefined);
            }}
            className="rounded border border-ide-border px-2 py-0.5 text-[10px] text-ide-muted hover:bg-ide-sidebar disabled:opacity-50"
          >
            {prompt}
          </button>
        ))}
      </div>

      <div
        ref={messagesRef}
        className="min-h-0 flex-1 space-y-2 overflow-y-auto rounded border border-ide-border bg-ide-bg p-2"
      >
        {messages.length === 0 && (
          <p className="text-xs text-ide-muted">Ask about HDL, testbenches, or simulation errors.</p>
        )}
        {messages.map((message) => {
          const codeBlock =
            message.role === 'assistant' ? extractPrimaryCodeBlock(message.content) : null;
          return (
            <div
              key={message.id}
              className={`rounded px-2 py-1.5 text-xs ${
                message.role === 'user'
                  ? 'bg-ide-sidebar text-white'
                  : 'border border-ide-border text-ide-text'
              }`}
            >
              <p className="mb-1 text-[10px] uppercase tracking-wide text-ide-muted">{message.role}</p>
              <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
              {message.streaming && <span className="text-ide-muted">…</span>}
              {codeBlock && !message.streaming && onApplyToEditor && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => onApplyToEditor(codeBlock)}
                    className="text-sky-400 underline"
                  >
                    Apply to editor
                  </button>
                  {onApplyAndSave && (
                    <button
                      type="button"
                      onClick={() => onApplyAndSave(codeBlock)}
                      className="text-emerald-400 underline"
                    >
                      Apply &amp; save
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-2 flex shrink-0 gap-2">
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              handleSend().catch(() => undefined);
            }
          }}
          placeholder="Ask AI about the open file…"
          rows={2}
          disabled={sending}
          className="flex-1 resize-none rounded border border-ide-border bg-ide-sidebar px-2 py-1.5 text-xs text-white"
        />
        <button
          type="button"
          onClick={() => {
            handleSend().catch(() => undefined);
          }}
          disabled={sending || !input.trim()}
          className="self-end rounded bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
        >
          {sending ? '…' : 'Send'}
        </button>
      </div>
    </div>
  );
}
