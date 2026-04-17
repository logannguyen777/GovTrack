"use client";

import * as React from "react";
import type { ChatMessage, Citation, ToolCall, Attachment } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AttachmentInput {
  name: string;
  data: string; // base64
  type: "image" | "pdf" | "other";
}

export interface ChatSuggestion {
  tthc_code: string;
  name: string;
  reason: string;
  confidence?: number;
}

export interface ChatMessageExtended extends ChatMessage {
  thinkingText?: string;
  suggestions?: ChatSuggestion[];
  isStreaming?: boolean;
}

export interface UseAIChatReturn {
  sessionId: string;
  messages: ChatMessageExtended[];
  isStreaming: boolean;
  send: (text: string, attachments?: AttachmentInput[]) => Promise<void>;
  abort: () => void;
  clear: () => void;
  error: string | null;
}

interface ChatContext {
  type: "case" | "submit" | "portal";
  ref?: string;
}

interface UseAIChatOptions {
  context?: ChatContext;
  initialSessionId?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SESSION_KEY = "govflow-assistant-session";
const MAX_MESSAGES = 50;
const MOCK_ENABLED =
  typeof process !== "undefined" &&
  process.env.NEXT_PUBLIC_MOCK_ASSISTANT === "true";

// ---------------------------------------------------------------------------
// Session ID
// ---------------------------------------------------------------------------

function getOrCreateSessionId(initial?: string): string {
  if (initial) return initial;
  if (typeof window === "undefined") return crypto.randomUUID();
  const stored = localStorage.getItem(SESSION_KEY);
  if (stored) return stored;
  const id = crypto.randomUUID();
  localStorage.setItem(SESSION_KEY, id);
  return id;
}

// ---------------------------------------------------------------------------
// SessionStorage helpers
// ---------------------------------------------------------------------------

function loadMessages(sessionId: string): ChatMessageExtended[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(`govflow-chat-${sessionId}`);
    return raw ? (JSON.parse(raw) as ChatMessageExtended[]) : [];
  } catch {
    return [];
  }
}

let _saveTimer: ReturnType<typeof setTimeout> | null = null;
function saveMessages(sessionId: string, messages: ChatMessageExtended[]) {
  if (typeof window === "undefined") return;
  if (_saveTimer) clearTimeout(_saveTimer);
  _saveTimer = setTimeout(() => {
    try {
      const capped = messages.slice(-MAX_MESSAGES);
      sessionStorage.setItem(`govflow-chat-${sessionId}`, JSON.stringify(capped));
    } catch {
      // storage quota — ignore
    }
  }, 200);
}

// ---------------------------------------------------------------------------
// SSE line parser
// ---------------------------------------------------------------------------

interface SSEEvent {
  type: string;
  data: Record<string, unknown>;
}

function parseSSEChunk(raw: string): SSEEvent[] {
  const events: SSEEvent[] = [];
  const blocks = raw.split("\n\n");
  for (const block of blocks) {
    const lines = block.split("\n");
    let dataLine = "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        dataLine += line.slice(6);
      }
    }
    if (!dataLine.trim()) continue;
    try {
      const parsed = JSON.parse(dataLine) as { type?: string } & Record<string, unknown>;
      if (parsed.type) {
        events.push({ type: parsed.type, data: parsed });
      }
    } catch {
      // partial chunk — will be re-buffered by caller
    }
  }
  return events;
}

// ---------------------------------------------------------------------------
// Mock SSE stream (NEXT_PUBLIC_MOCK_ASSISTANT=true)
// ---------------------------------------------------------------------------

async function* mockStream(text: string): AsyncGenerator<SSEEvent> {
  yield { type: "session", data: { session_id: "mock-session" } };
  yield { type: "thinking", data: { text: "Đang phân tích yêu cầu của bạn..." } };
  await delay(300);

  if (text.toLowerCase().includes("xây") || text.toLowerCase().includes("xây dựng")) {
    yield {
      type: "tool_call",
      data: {
        id: "tc-1",
        name: "search_tthc",
        args: { query: "cấp phép xây dựng" },
        status: "pending",
      },
    };
    await delay(400);
    yield {
      type: "tool_result",
      data: {
        id: "tc-1",
        status: "success",
        result: { tthc_code: "1.004415", name: "Cấp phép xây dựng" },
      },
    };
    await delay(200);
  }

  const reply =
    "Dựa trên yêu cầu của bạn, tôi có thể hỗ trợ tra cứu thủ tục hành chính. Để cấp giấy phép xây dựng, bạn cần chuẩn bị: Đơn đề nghị cấp phép, bản vẽ thiết kế, giấy chứng nhận quyền sử dụng đất và một số giấy tờ liên quan.";
  for (let i = 0; i < reply.length; i += 5) {
    yield { type: "text_delta", data: { text: reply.slice(i, i + 5) } };
    await delay(30);
  }

  if (text.toLowerCase().includes("xây") || text.toLowerCase().includes("xây dựng")) {
    yield {
      type: "citation",
      data: {
        id: "cit-1",
        lawName: "Luật Xây dựng 50/2014/QH13",
        article: "Điều 89",
        url: "#",
      },
    };
    yield {
      type: "suggestion",
      data: {
        tthc_code: "1.004415",
        name: "Cấp phép xây dựng",
        reason: "Phù hợp với yêu cầu của bạn",
        confidence: 0.95,
      },
    };
  }

  yield { type: "done", data: {} };
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAIChat(opts?: UseAIChatOptions): UseAIChatReturn {
  const sessionId = React.useRef(getOrCreateSessionId(opts?.initialSessionId));

  const [messages, setMessages] = React.useState<ChatMessageExtended[]>(() =>
    loadMessages(sessionId.current),
  );
  const [isStreaming, setIsStreaming] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const abortRef = React.useRef<AbortController | null>(null);
  const doneTimeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Persist on message change
  React.useEffect(() => {
    saveMessages(sessionId.current, messages);
  }, [messages]);

  // Helper: update last assistant message
  const updateLastAssistant = React.useCallback(
    (updater: (prev: ChatMessageExtended) => ChatMessageExtended) => {
      setMessages((prev) => {
        const idx = [...prev].reverse().findIndex((m) => m.role === "assistant");
        if (idx === -1) return prev;
        const realIdx = prev.length - 1 - idx;
        const updated = [...prev];
        updated[realIdx] = updater(updated[realIdx]);
        return updated;
      });
    },
    [],
  );

  const processEvent = React.useCallback(
    (event: SSEEvent) => {
      const { type, data } = event;
      const d = data as Record<string, unknown>;

      if (type === "session") {
        const sid = d.session_id as string | undefined;
        if (sid) {
          sessionId.current = sid;
          localStorage.setItem(SESSION_KEY, sid);
        }
        return;
      }

      if (type === "thinking") {
        const text = (d.text ?? d.delta ?? "") as string;
        updateLastAssistant((msg) => ({
          ...msg,
          thinkingText: (msg.thinkingText ?? "") + text,
        }));
        return;
      }

      if (type === "text_delta") {
        const text = (d.text ?? d.delta ?? d.content ?? "") as string;
        updateLastAssistant((msg) => ({
          ...msg,
          content: msg.content + text,
        }));
        return;
      }

      if (type === "tool_call") {
        const tc: ToolCall = {
          id: (d.id as string) ?? crypto.randomUUID(),
          name: (d.name ?? d.tool_name ?? "") as string,
          args: d.args as Record<string, unknown> | undefined,
          status: "pending",
        };
        updateLastAssistant((msg) => ({
          ...msg,
          toolCalls: [...(msg.toolCalls ?? []), tc],
        }));
        return;
      }

      if (type === "tool_result") {
        const id = d.id as string;
        const isError = d.status === "error" || !!d.error;
        updateLastAssistant((msg) => ({
          ...msg,
          toolCalls: (msg.toolCalls ?? []).map((tc) =>
            tc.id === id
              ? {
                  ...tc,
                  status: isError ? "error" : "success",
                  result: d.result,
                }
              : tc,
          ),
        }));
        return;
      }

      if (type === "citation") {
        const citation: Citation = {
          id: (d.id as string) ?? crypto.randomUUID(),
          // Backend may emit law_id (not law_name/lawName) — handle all variants
          lawName: (d.lawName ?? d.law_name ?? d.law_id ?? "") as string,
          article: (d.article ?? "") as string,
          url: d.url as string | undefined,
          chunkId: d.chunk_id as string | undefined,
        };
        updateLastAssistant((msg) => ({
          ...msg,
          citations: [...(msg.citations ?? []), citation],
        }));
        return;
      }

      if (type === "suggestion") {
        const suggestion: ChatSuggestion = {
          tthc_code: (d.tthc_code ?? "") as string,
          name: (d.name ?? "") as string,
          reason: (d.reason ?? "") as string,
          confidence: d.confidence as number | undefined,
        };
        updateLastAssistant((msg) => ({
          ...msg,
          suggestions: [...(msg.suggestions ?? []), suggestion],
        }));
        return;
      }

      if (type === "done") {
        if (doneTimeoutRef.current) clearTimeout(doneTimeoutRef.current);
        updateLastAssistant((msg) => ({ ...msg, isStreaming: false }));
        setIsStreaming(false);
        return;
      }

      if (type === "error") {
        const msg = (d.message ?? d.error ?? "Có lỗi xảy ra") as string;
        setError(msg);
        updateLastAssistant((m) => ({ ...m, isStreaming: false }));
        setIsStreaming(false);
        return;
      }
    },
    [updateLastAssistant],
  );

  const send = React.useCallback(
    async (text: string, attachments?: AttachmentInput[]) => {
      if (isStreaming) return;
      setError(null);

      const userMsg: ChatMessageExtended = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        createdAt: new Date().toISOString(),
        attachments: attachments?.map((a) => ({
          id: crypto.randomUUID(),
          name: a.name,
          type: a.type,
        })),
      };
      const assistantMsg: ChatMessageExtended = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
        isStreaming: true,
        toolCalls: [],
        citations: [],
        suggestions: [],
      };

      setMessages((prev) => [...prev.slice(-(MAX_MESSAGES - 2)), userMsg, assistantMsg]);
      setIsStreaming(true);

      // 30-second done timeout
      doneTimeoutRef.current = setTimeout(() => {
        setError("Phiên AI đã hết thời gian. Vui lòng thử lại.");
        updateLastAssistant((m) => ({ ...m, isStreaming: false }));
        setIsStreaming(false);
      }, 30_000);

      if (MOCK_ENABLED) {
        // Consume mock stream
        for await (const event of mockStream(text)) {
          processEvent(event);
        }
        return;
      }

      abortRef.current = new AbortController();
      const { signal } = abortRef.current;

      try {
        const res = await fetch("/api/assistant/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId.current,
            message: text,
            context: opts?.context,
            attachments: attachments ?? [],
          }),
          signal,
        });

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        if (!res.body) {
          throw new Error("No response body");
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Split on double-newline (SSE event boundary)
          const parts = buffer.split("\n\n");
          buffer = parts.pop() ?? "";

          for (const part of parts) {
            if (!part.trim()) continue;
            const events = parseSSEChunk(part + "\n\n");
            for (const event of events) {
              processEvent(event);
            }
          }
        }

        // flush remaining
        if (buffer.trim()) {
          const events = parseSSEChunk(buffer + "\n\n");
          for (const event of events) {
            processEvent(event);
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          updateLastAssistant((m) => ({ ...m, isStreaming: false }));
          setIsStreaming(false);
          return;
        }

        setError("Lỗi kết nối, đang thử lại...");
        updateLastAssistant((m) => ({ ...m, isStreaming: false }));
        setIsStreaming(false);

        // auto-retry once after 3s
        setTimeout(() => {
          void send(text, attachments);
        }, 3000);
      } finally {
        if (doneTimeoutRef.current) clearTimeout(doneTimeoutRef.current);
        abortRef.current = null;
      }
    },
    [isStreaming, opts?.context, processEvent, updateLastAssistant],
  );

  const abort = React.useCallback(() => {
    abortRef.current?.abort();
    if (doneTimeoutRef.current) clearTimeout(doneTimeoutRef.current);
    updateLastAssistant((m) => ({ ...m, isStreaming: false }));
    setIsStreaming(false);
  }, [updateLastAssistant]);

  const clear = React.useCallback(() => {
    setMessages([]);
    setError(null);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(`govflow-chat-${sessionId.current}`);
    }
  }, []);

  return {
    sessionId: sessionId.current,
    messages,
    isStreaming,
    send,
    abort,
    clear,
    error,
  };
}
