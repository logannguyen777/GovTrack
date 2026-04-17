"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ToolCallCard } from "@/components/agents/tool-call-card";
import type { ToolCall } from "@/lib/stores/agent-artifact-store";

// ---------------------------------------------------------------------------
// Filter chips
// ---------------------------------------------------------------------------

type FilterValue = "all" | "pending" | "success" | "error";

const FILTER_LABELS: Record<FilterValue, string> = {
  all: "Tất cả",
  pending: "Đang chạy",
  success: "Thành công",
  error: "Lỗi",
};

// ---------------------------------------------------------------------------
// ToolsTab
// ---------------------------------------------------------------------------

interface ToolsTabProps {
  toolCalls: ToolCall[];
}

export function ToolsTab({ toolCalls }: ToolsTabProps) {
  const [filter, setFilter] = React.useState<FilterValue>("all");

  const filtered = React.useMemo(() => {
    if (filter === "all") return toolCalls;
    return toolCalls.filter((tc) => tc.status === filter);
  }, [toolCalls, filter]);

  // Group by agent name
  const byAgent = React.useMemo(() => {
    const groups: Record<string, ToolCall[]> = {};
    for (const tc of filtered) {
      const key = tc.agentName || "Unknown";
      if (!groups[key]) groups[key] = [];
      groups[key].push(tc);
    }
    return groups;
  }, [filtered]);

  if (toolCalls.length === 0) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center p-6 text-center"
        style={{ color: "var(--text-muted)" }}
      >
        <p className="text-sm">Chưa có tool call nào</p>
        <p className="text-xs mt-1 opacity-70">
          Các lần gọi công cụ sẽ hiển thị tại đây
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Filter chips */}
      <div
        className="flex gap-1.5 px-3 py-2 border-b shrink-0 flex-wrap"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        {(Object.keys(FILTER_LABELS) as FilterValue[]).map((f) => (
          <button
            key={f}
            type="button"
            onClick={() => setFilter(f)}
            className={cn(
              "rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
              filter === f
                ? "text-white"
                : "hover:opacity-80",
            )}
            style={
              filter === f
                ? { backgroundColor: "var(--accent-primary)" }
                : {
                    backgroundColor: "var(--bg-subtle)",
                    color: "var(--text-secondary)",
                  }
            }
            aria-pressed={filter === f}
          >
            {FILTER_LABELS[f]}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-auto px-3 py-2 space-y-3">
        {filtered.length === 0 ? (
          <p className="text-xs py-4 text-center" style={{ color: "var(--text-muted)" }}>
            Không có kết quả cho bộ lọc này
          </p>
        ) : (
          Object.entries(byAgent).map(([agentName, calls]) => (
            <div key={agentName}>
              <p
                className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: "var(--text-muted)" }}
              >
                {agentName} ({calls.length})
              </p>
              <div className="space-y-1.5">
                {calls.map((call) => (
                  <ToolCallCard
                    key={call.id}
                    call={call}
                    defaultExpanded={false}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
