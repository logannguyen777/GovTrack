"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StreamingText } from "@/components/assistant/streaming-text";
import type { ThinkingDelta } from "@/lib/stores/agent-artifact-store";

// ---------------------------------------------------------------------------
// Time ago helper
// ---------------------------------------------------------------------------

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s trước`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m trước`;
  return `${Math.floor(min / 60)}h trước`;
}

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

interface CollapsibleSectionProps {
  agentName: string;
  updatedAt: string;
  text: string;
  isStreaming: boolean;
  defaultOpen?: boolean;
}

function CollapsibleSection({
  agentName,
  updatedAt,
  text,
  isStreaming,
  defaultOpen,
}: CollapsibleSectionProps) {
  const [open, setOpen] = React.useState(defaultOpen ?? true);
  const contentRef = React.useRef<HTMLDivElement>(null);
  const [userScrolledUp, setUserScrolledUp] = React.useState(false);
  const [hasNew, setHasNew] = React.useState(false);

  // Auto-scroll to bottom when new text arrives, unless user scrolled up
  React.useEffect(() => {
    if (!isStreaming) return;
    const el = contentRef.current;
    if (!el) return;
    if (userScrolledUp) {
      setHasNew(true);
      return;
    }
    el.scrollTop = el.scrollHeight;
  }, [text, isStreaming, userScrolledUp]);

  const handleScroll = React.useCallback(() => {
    const el = contentRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setUserScrolledUp(!atBottom);
    if (atBottom) setHasNew(false);
  }, []);

  const scrollToBottom = () => {
    const el = contentRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    setUserScrolledUp(false);
    setHasNew(false);
  };

  const isTruncated = text.length >= 50_000;

  return (
    <div
      className="border-b last:border-b-0"
      style={{ borderColor: "var(--border-subtle)" }}
    >
      {/* Trigger */}
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-left",
          "hover:bg-[var(--bg-surface-raised)] transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)]",
        )}
        onClick={() => setOpen((p) => !p)}
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown size={12} aria-hidden="true" style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        ) : (
          <ChevronRight size={12} aria-hidden="true" style={{ color: "var(--text-muted)", flexShrink: 0 }} />
        )}
        <span
          className="flex-1 text-xs font-semibold truncate"
          style={{ color: "var(--text-primary)" }}
        >
          {agentName}
        </span>
        {isStreaming && (
          <span
            className="shrink-0 text-[10px] animate-pulse"
            style={{ color: "var(--accent-primary)" }}
          >
            đang suy nghĩ...
          </span>
        )}
        <span
          className="shrink-0 text-[10px]"
          style={{ color: "var(--text-muted)" }}
        >
          {timeAgo(updatedAt)}
        </span>
      </button>

      {/* Content */}
      {open && (
        <div className="relative">
          <div
            ref={contentRef}
            className="max-h-[320px] overflow-auto px-3 pb-3"
            onScroll={handleScroll}
          >
            {isTruncated && (
              <p
                className="mb-2 text-[10px] italic rounded px-2 py-1"
                style={{
                  color: "var(--text-muted)",
                  backgroundColor: "var(--bg-subtle)",
                }}
              >
                Đã rút gọn... (hiển thị 50KB cuối)
              </p>
            )}
            <StreamingText
              text={text}
              isStreaming={isStreaming}
              className="text-xs leading-relaxed"
              ariaLive="polite"
            />
          </div>

          {/* "↓ Mới" chip */}
          {hasNew && userScrolledUp && (
            <button
              type="button"
              onClick={scrollToBottom}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium shadow-sm border transition-opacity hover:opacity-90"
              style={{
                backgroundColor: "var(--accent-primary)",
                color: "#fff",
                borderColor: "var(--accent-primary)",
              }}
              aria-label="Cuộn xuống nội dung mới"
            >
              ↓ Mới
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ThinkingTab
// ---------------------------------------------------------------------------

interface ThinkingTabProps {
  thinking: Record<string, ThinkingDelta>;
  runningAgentIds?: Set<string>;
}

export function ThinkingTab({ thinking, runningAgentIds }: ThinkingTabProps) {
  const entries = Object.entries(thinking);

  if (entries.length === 0) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center p-6 text-center"
        style={{ color: "var(--text-muted)" }}
      >
        <p className="text-sm">Agent chưa bắt đầu suy nghĩ</p>
        <p className="text-xs mt-1 opacity-70">
          Khi agent chạy, suy nghĩ sẽ stream tại đây
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto" style={{ backgroundColor: "var(--bg-canvas)" }}>
      {entries.map(([agentId, t]) => (
        <CollapsibleSection
          key={agentId}
          agentName={t.agentName}
          updatedAt={t.updatedAt}
          text={t.text}
          isStreaming={runningAgentIds?.has(agentId) ?? false}
          defaultOpen={t.text.length < 5000}
        />
      ))}
    </div>
  );
}
