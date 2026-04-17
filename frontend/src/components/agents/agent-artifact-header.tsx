"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { X, ExternalLink } from "lucide-react";
import type { AgentBlock } from "@/lib/stores/agent-artifact-store";

interface AgentArtifactHeaderProps {
  caseId: string;
  activeAgent: AgentBlock | undefined;
  onClose: () => void;
}

export function AgentArtifactHeader({
  caseId,
  activeAgent,
  onClose,
}: AgentArtifactHeaderProps) {
  const router = useRouter();
  const shortId = caseId.slice(0, 8);

  return (
    <div
      className="flex items-start justify-between gap-3 px-4 py-3 border-b shrink-0"
      style={{
        borderColor: "var(--border-subtle)",
        backgroundColor: "var(--bg-surface)",
      }}
    >
      <div className="flex-1 min-w-0">
        {/* Case code + TTHC */}
        <div className="flex items-center gap-2">
          <span
            className="font-mono text-xs font-semibold truncate"
            style={{ color: "var(--text-primary)" }}
            title={caseId}
          >
            {shortId}
          </span>
          <span style={{ color: "var(--border-default)" }}>·</span>
          <span className="text-xs truncate" style={{ color: "var(--text-secondary)" }}>
            Trợ lý AI
          </span>
        </div>

        {/* Active agent pulse */}
        {activeAgent ? (
          <div className="flex items-center gap-1.5 mt-1">
            <span
              className="h-2 w-2 rounded-full shrink-0 animate-pulse"
              style={{ backgroundColor: "var(--accent-success)" }}
              aria-hidden="true"
            />
            <span className="text-[11px] truncate" style={{ color: "var(--accent-success)" }}>
              Đang chạy: {activeAgent.name}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 mt-1">
            <span
              className="h-2 w-2 rounded-full shrink-0"
              style={{ backgroundColor: "var(--text-muted)" }}
              aria-hidden="true"
            />
            <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>
              Không có agent chạy
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {/* Open trace page */}
        <button
          type="button"
          onClick={() => router.push(`/trace/${caseId}`)}
          className="flex h-7 w-7 items-center justify-center rounded transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
          style={{ color: "var(--text-muted)" }}
          aria-label="Mở trang chi tiết trace"
          title="Mở trang chi tiết"
        >
          <ExternalLink size={14} aria-hidden="true" />
        </button>

        {/* Close */}
        <button
          type="button"
          onClick={onClose}
          className="flex h-7 w-7 items-center justify-center rounded transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] hover:opacity-70"
          style={{ color: "var(--text-muted)" }}
          aria-label="Đóng panel"
        >
          <X size={14} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
