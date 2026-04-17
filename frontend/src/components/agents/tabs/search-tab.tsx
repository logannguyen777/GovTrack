"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import type { SearchLog } from "@/lib/stores/agent-artifact-store";

// ---------------------------------------------------------------------------
// Similarity bar
// ---------------------------------------------------------------------------

function SimilarityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="h-1.5 w-16 overflow-hidden rounded-full"
        style={{ backgroundColor: "var(--bg-subtle)" }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            backgroundColor:
              pct >= 90
                ? "var(--accent-success)"
                : pct >= 70
                  ? "var(--accent-warning)"
                  : "var(--accent-destructive)",
          }}
        />
      </div>
      <span
        className="text-[10px] tabular-nums font-mono"
        style={{ color: "var(--text-muted)" }}
      >
        {value.toFixed(2)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Result row
// ---------------------------------------------------------------------------

interface ResultRowProps {
  chunkId: string;
  article: string;
  similarity: number;
  preview: string;
}

function ResultRow({ chunkId, article, similarity, preview }: ResultRowProps) {
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div
      className="rounded border overflow-hidden"
      style={{ borderColor: "var(--border-subtle)" }}
    >
      <button
        type="button"
        className={cn(
          "flex w-full items-center gap-2 px-2 py-1.5 text-left",
          "hover:bg-[var(--bg-surface-raised)] transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)]",
        )}
        onClick={() => setExpanded((p) => !p)}
        aria-expanded={expanded}
      >
        <span
          className="font-mono text-[10px] truncate flex-1"
          style={{ color: "var(--text-secondary)" }}
          title={chunkId}
        >
          {article || chunkId.slice(0, 20)}
        </span>
        <SimilarityBar value={similarity} />
        <span
          className="text-[10px]"
          style={{ color: "var(--text-muted)" }}
          aria-hidden="true"
        >
          {expanded ? "▼" : "▲"}
        </span>
      </button>

      {expanded && (
        <div
          className="border-t px-2 py-2"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <p
            className="text-[11px] leading-relaxed whitespace-pre-wrap"
            style={{
              color: "var(--text-secondary)",
              fontFamily: "var(--font-serif, serif)",
            }}
          >
            {preview || "Không có nội dung xem trước"}
          </p>
          <p
            className="mt-1.5 font-mono text-[9px]"
            style={{ color: "var(--text-muted)" }}
          >
            {chunkId}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchEntry card
// ---------------------------------------------------------------------------

interface SearchEntryProps {
  log: SearchLog;
}

function SearchEntry({ log }: SearchEntryProps) {
  return (
    <div
      className="rounded-lg border p-3 space-y-2"
      style={{
        borderColor: "var(--border-subtle)",
        backgroundColor: "var(--bg-surface)",
      }}
    >
      {/* Header */}
      <div className="flex items-start gap-2">
        <span className="text-base" aria-hidden="true">📚</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span
              className="text-xs font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
              {log.agentId || "LegalLookup"}
            </span>
            <span style={{ color: "var(--border-default)" }}>·</span>
            <span
              className="text-[11px]"
              style={{ color: "var(--text-muted)" }}
            >
              vector_recall
            </span>
          </div>
          <p
            className="mt-0.5 text-xs break-words"
            style={{ color: "var(--text-secondary)" }}
          >
            Query:{" "}
            <span className="italic">&ldquo;{log.query}&rdquo;</span>
          </p>
        </div>
      </div>

      {/* Top-k results */}
      {log.topK.length > 0 && (
        <div>
          <p
            className="mb-1 text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: "var(--text-muted)" }}
          >
            Top {log.topK.length} kết quả
          </p>
          <div className="space-y-1">
            {log.topK.map((item) => (
              <ResultRow
                key={item.chunkId}
                chunkId={item.chunkId}
                article={item.article}
                similarity={item.similarity}
                preview={item.preview}
              />
            ))}
          </div>
        </div>
      )}

      {/* Citations kept */}
      {log.citationsKept.length > 0 && (
        <p
          className="text-[11px]"
          style={{ color: "var(--text-muted)" }}
        >
          Citations giữ lại:{" "}
          <span
            className="font-semibold tabular-nums"
            style={{ color: "var(--accent-primary)" }}
          >
            {log.citationsKept.length}
          </span>
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SearchTab
// ---------------------------------------------------------------------------

interface SearchTabProps {
  searches: SearchLog[];
}

export function SearchTab({ searches }: SearchTabProps) {
  if (searches.length === 0) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center p-6 text-center"
        style={{ color: "var(--text-muted)" }}
      >
        <p className="text-sm">Chưa có tra cứu pháp lý</p>
        <p className="text-xs mt-1 opacity-70">
          Vector search và kết quả GraphRAG sẽ hiện ở đây
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto px-3 py-2 space-y-2">
      {searches.map((log) => (
        <SearchEntry key={log.id} log={log} />
      ))}
    </div>
  );
}
