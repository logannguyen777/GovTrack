"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Loader2, CheckCircle2, XCircle, ChevronDown, ChevronRight, Wrench } from "lucide-react";
import type { ToolCall } from "@/lib/stores/agent-artifact-store";

// ---------------------------------------------------------------------------
// Inline JSON renderer — avoids heavy libraries
// ---------------------------------------------------------------------------

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre
      className="overflow-x-auto rounded p-2 text-[11px] leading-relaxed"
      style={{
        backgroundColor: "var(--bg-subtle)",
        color: "var(--text-secondary)",
        fontFamily: "var(--font-mono)",
      }}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

// ---------------------------------------------------------------------------
// Status indicator
// ---------------------------------------------------------------------------

function StatusDot({ status }: { status: ToolCall["status"] }) {
  if (status === "pending") {
    return (
      <Loader2
        size={12}
        className="animate-spin"
        style={{ color: "var(--accent-warning)" }}
        aria-label="Đang chạy"
      />
    );
  }
  if (status === "success") {
    return (
      <CheckCircle2
        size={12}
        style={{ color: "var(--accent-success)" }}
        aria-label="Thành công"
      />
    );
  }
  return (
    <XCircle
      size={12}
      style={{ color: "var(--accent-destructive)" }}
      aria-label="Lỗi"
    />
  );
}

// ---------------------------------------------------------------------------
// ToolCallCard
// ---------------------------------------------------------------------------

interface ToolCallCardProps {
  call: ToolCall;
  defaultExpanded?: boolean;
}

export function ToolCallCard({ call, defaultExpanded = false }: ToolCallCardProps) {
  const [expanded, setExpanded] = React.useState(defaultExpanded);

  const durationLabel =
    call.durationMs != null
      ? call.durationMs < 1000
        ? `${call.durationMs}ms`
        : `${(call.durationMs / 1000).toFixed(1)}s`
      : null;

  return (
    <div
      className={cn(
        "rounded-lg border overflow-hidden transition-colors duration-150",
        call.status === "error"
          ? "border-[var(--accent-destructive)]/30"
          : "border-[var(--border-subtle)]",
      )}
      style={{ backgroundColor: "var(--bg-surface)" }}
    >
      {/* Header — always visible */}
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 px-3 py-2 text-left",
          "hover:bg-[var(--bg-surface-raised)] transition-colors duration-[var(--duration-micro)]",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)]",
        )}
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
        aria-label={`${call.name} — ${call.status}`}
      >
        {/* Tool icon */}
        <Wrench
          size={13}
          aria-hidden="true"
          style={{ color: "var(--text-muted)", flexShrink: 0 }}
        />

        {/* Name */}
        <span
          className="flex-1 truncate text-xs font-semibold"
          style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}
        >
          {call.name}
        </span>

        {/* Agent name */}
        {call.agentName && (
          <span
            className="shrink-0 text-[10px]"
            style={{ color: "var(--text-muted)" }}
          >
            {call.agentName}
          </span>
        )}

        {/* Duration */}
        {durationLabel && (
          <span
            className="shrink-0 text-[10px] tabular-nums"
            style={{ color: "var(--text-muted)" }}
          >
            {durationLabel}
          </span>
        )}

        {/* Status */}
        <StatusDot status={call.status} />

        {/* Expand toggle */}
        {expanded ? (
          <ChevronDown size={12} aria-hidden="true" style={{ color: "var(--text-muted)" }} />
        ) : (
          <ChevronRight size={12} aria-hidden="true" style={{ color: "var(--text-muted)" }} />
        )}
      </button>

      {/* Expandable body */}
      {expanded && (
        <div
          className="flex flex-col gap-3 border-t px-3 py-3"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          {/* Args */}
          {call.args != null && (
            <section aria-label="Tham số">
              <p
                className="mb-1 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: "var(--text-muted)" }}
              >
                Tham số
              </p>
              <JsonBlock value={call.args} />
            </section>
          )}

          {/* Result */}
          {call.result != null && (
            <section aria-label="Kết quả">
              <p
                className="mb-1 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: "var(--text-muted)" }}
              >
                Kết quả
              </p>
              <JsonBlock value={call.result} />
            </section>
          )}

          {/* Error */}
          {call.error && (
            <section aria-label="Lỗi">
              <p
                className="mb-1 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: "var(--accent-destructive)" }}
              >
                Lỗi
              </p>
              <pre
                className="rounded p-2 text-[11px]"
                style={{
                  backgroundColor: "var(--accent-destructive)/8",
                  color: "var(--accent-destructive)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {call.error}
              </pre>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
