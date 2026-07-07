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
  className?: string;
}

interface ChatEntry {
  id: string;
  role: AiMessage['role'];
  content: string;
  streaming?: boolean;
}

export function AiChatPanel({
  projectId,
  activeFileId,
  activeFilePath,
  className = '',
}: AiChatPanelProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [conversation, setConversation] = useState<AiConversation | null>(null);
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const loadConversation = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const conversations = await listProjectConversations(projectId);
      const current =
        conversations[0] ?? (await createProjectConversation(projectId, { title: 'New chat' }));
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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  async function handleSend() {
    const text = input.trim();
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
      sendAiMessage(ws, text, activeFileId ?? undefined);
    };
  }

  if (loading) {
    return (
      <div className={`flex h-[70vh] items-center justify-center text-sm text-ide-muted ${className}`}>
        Loading AI assistant…
      </div>
    );
  }

  return (
    <div className={`flex h-[70vh] min-h-0 flex-col rounded border border-ide-border bg-ide-bg ${className}`}>
      <div className="border-b border-ide-border px-4 py-2">
        <h2 className="text-sm font-semibold text-white">Veridian AI</h2>
        <p className="text-xs text-ide-muted">
          {conversation?.title ?? 'Chat'}
          {activeFilePath ? ` · context: ${activeFilePath}` : ''}
        </p>
      </div>

      {error && <p className="px-4 py-2 text-xs text-red-400">{error}</p>}

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {messages.length === 0 && (
          <p className="text-sm text-ide-muted">
            Ask about your HDL design, testbench, synthesis, or simulation errors.
          </p>
        )}
        {messages.map((message) => (
          <div
            key={message.id}
            className={`rounded px-3 py-2 text-sm ${
              message.role === 'user'
                ? 'ml-8 bg-ide-sidebar text-white'
                : 'mr-8 border border-ide-border text-ide-text'
            }`}
          >
            <p className="mb-1 text-[10px] uppercase tracking-wide text-ide-muted">{message.role}</p>
            <pre className="whitespace-pre-wrap font-sans">{message.content}</pre>
            {message.streaming && <span className="text-xs text-ide-muted">…</span>}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-ide-border p-3">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                handleSend().catch(() => undefined);
              }
            }}
            placeholder="Ask Veridian AI…"
            rows={2}
            disabled={sending}
            className="flex-1 resize-none rounded border border-ide-border bg-ide-sidebar px-3 py-2 text-sm text-white"
          />
          <button
            type="button"
            onClick={() => {
              handleSend().catch(() => undefined);
            }}
            disabled={sending || !input.trim()}
            className="self-end rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {sending ? '…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}
