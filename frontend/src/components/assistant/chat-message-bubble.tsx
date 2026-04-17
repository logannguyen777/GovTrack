"use client";

import * as React from "react";
import { Sparkles, Wrench, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { StreamingText } from "./streaming-text";
import type { Citation, Attachment } from "@/lib/types";

// ---------------------------------------------------------------------------
// ChatMessageBubble
// ---------------------------------------------------------------------------

interface ChatMessageBubbleProps {
  role: "user" | "assistant" | "system" | "tool";
  content: React.ReactNode;
  timestamp?: string;
  isStreaming?: boolean;
  citations?: Citation[];
  attachments?: Attachment[];
  toolName?: string; // for role=tool
}

function CitationRow({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {citations.map((c) => (
        <a
          key={c.id}
          href={c.url ?? "#"}
          target={c.url ? "_blank" : undefined}
          rel="noopener noreferrer"
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5",
            "text-[10px] font-medium whitespace-nowrap transition-opacity hover:opacity-80",
          )}
          style={{
            borderColor: "oklch(0.55 0.18 300 / 0.4)",
            backgroundColor: "oklch(0.55 0.18 300 / 0.08)",
            color: "oklch(0.78 0.14 300)",
          }}
          aria-label={`Trích dẫn: ${c.lawName} ${c.article}`}
        >
          <span className="font-semibold">{c.article}</span>
          <span className="max-w-[120px] truncate opacity-80" title={c.lawName}>
            {c.lawName}
          </span>
        </a>
      ))}
    </div>
  );
}

function AttachmentRow({ attachments }: { attachments: Attachment[] }) {
  if (attachments.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {attachments.map((a) => (
        <a
          key={a.id}
          href={a.url ?? "#"}
          target={a.url ? "_blank" : undefined}
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 rounded border px-2 py-0.5 text-[10px] transition-opacity hover:opacity-80"
          style={{
            borderColor: "var(--border-subtle)",
            color: "var(--text-secondary)",
          }}
          aria-label={`Tệp đính kèm: ${a.name}`}
        >
          {a.type === "image" ? "🖼" : a.type === "pdf" ? "📄" : "📎"}
          <span className="max-w-[120px] truncate">{a.name}</span>
        </a>
      ))}
    </div>
  );
}

function ToolMessageBubble({
  toolName,
  content,
}: {
  toolName: string;
  content: React.ReactNode;
}) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="flex justify-center">
      <button
        type="button"
        onClick={() => setExpanded((p) => !p)}
        className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
        style={{
          borderColor: "var(--border-subtle)",
          backgroundColor: "var(--bg-subtle)",
          color: "var(--text-muted)",
        }}
        aria-expanded={expanded}
      >
        <Wrench size={12} aria-hidden="true" />
        <span>{toolName}</span>
        {expanded ? (
          <ChevronDown size={12} aria-hidden="true" />
        ) : (
          <ChevronRight size={12} aria-hidden="true" />
        )}
      </button>
      {expanded && (
        <div
          className="mt-1 w-full rounded border p-2 text-xs"
          style={{
            borderColor: "var(--border-subtle)",
            backgroundColor: "var(--bg-subtle)",
            color: "var(--text-secondary)",
          }}
        >
          {content}
        </div>
      )}
    </div>
  );
}

export function ChatMessageBubble({
  role,
  content,
  timestamp,
  isStreaming = false,
  citations = [],
  attachments = [],
  toolName,
}: ChatMessageBubbleProps) {
  // ---- tool message ----
  if (role === "tool") {
    return (
      <div className="my-1 px-4">
        <ToolMessageBubble
          toolName={toolName ?? "tool"}
          content={content}
        />
      </div>
    );
  }

  // ---- system message ----
  if (role === "system") {
    return (
      <div className="my-2 flex justify-center px-4">
        <span
          className="text-center text-xs"
          style={{ color: "var(--text-muted)" }}
        >
          {content}
        </span>
      </div>
    );
  }

  const isUser = role === "user";

  return (
    <div
      className={cn(
        "my-2 flex",
        isUser ? "justify-end px-4" : "justify-start px-4",
      )}
    >
      {/* Assistant prefix icon */}
      {!isUser && (
        <div
          className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full"
          style={{ background: "var(--gradient-qwen)" }}
          aria-hidden="true"
        >
          <Sparkles size={12} className="text-white" />
        </div>
      )}

      <div
        className={cn(
          "flex max-w-[80%] flex-col rounded-2xl px-3.5 py-2.5",
          isUser
            ? "rounded-br-sm"
            : "rounded-bl-sm",
        )}
        style={
          isUser
            ? {
                backgroundColor: "var(--accent-primary)",
                color: "#ffffff",
              }
            : {
                background: "var(--gradient-qwen-soft)",
                border: "1px solid oklch(0.65 0.15 280 / 0.25)",
                color: "var(--text-primary)",
              }
        }
      >
        {/* Content */}
        <div className="text-sm leading-relaxed">
          {isStreaming && typeof content === "string" ? (
            <StreamingText text={content} isStreaming={isStreaming} />
          ) : (
            content
          )}
        </div>

        {/* Citations */}
        {citations.length > 0 && <CitationRow citations={citations} />}

        {/* Attachments */}
        {attachments.length > 0 && <AttachmentRow attachments={attachments} />}

        {/* Timestamp */}
        {timestamp && (
          <p
            className="mt-1.5 text-right text-[10px]"
            style={{ opacity: 0.6 }}
            aria-label={`Gửi lúc ${timestamp}`}
          >
            {new Date(timestamp).toLocaleTimeString("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        )}
      </div>
    </div>
  );
}
