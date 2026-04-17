"use client";

import * as React from "react";
import { useAgentArtifactStore } from "@/lib/stores/agent-artifact-store";
import { StreamingText } from "@/components/assistant/streaming-text";

interface AgentThinkingSectionProps {
  caseId: string;
  /** Filter to specific agent name, e.g. "ComplianceAgent" */
  agentFilter?: string;
}

// Stable empty sentinels so zustand selectors return a consistent reference
// when the per-case entry is missing. `?? {}` and `?? []` allocate fresh
// objects on every render → useSyncExternalStore fires → infinite loop.
const EMPTY_THINKING = Object.freeze({}) as Readonly<Record<string, { agentName: string; text: string }>>;
const EMPTY_ACTIVE: ReadonlyArray<{ id: string; status: string }> = Object.freeze([]);

export function AgentThinkingSection({
  caseId,
  agentFilter,
}: AgentThinkingSectionProps) {
  const thinking = useAgentArtifactStore(
    (s) => s.byCaseId[caseId]?.thinking ?? EMPTY_THINKING,
  );
  const activeAgents = useAgentArtifactStore(
    (s) => s.byCaseId[caseId]?.activeAgents ?? EMPTY_ACTIVE,
  );

  const runningIds = React.useMemo(
    () =>
      new Set(
        activeAgents
          .filter((a) => a.status === "running")
          .map((a) => a.id.split(":")[0]),
      ),
    [activeAgents],
  );

  const entries = React.useMemo(() => {
    // Normalize both sides so "ComplianceAgent" matches "compliance_agent",
    // "Compliance", "complianceAgent" etc.
    const norm = (s: string) =>
      s.toLowerCase().replace(/[_\s-]/g, "").replace(/agent$/, "");
    const needle = agentFilter ? norm(agentFilter) : "";
    return Object.entries(thinking).filter(([, t]) => {
      if (!needle) return true;
      return norm(t.agentName).includes(needle);
    });
  }, [thinking, agentFilter]);

  if (entries.length === 0) {
    return (
      <p
        className="text-xs py-2"
        style={{ color: "var(--text-muted)" }}
      >
        Không có dữ liệu suy nghĩ
        {agentFilter ? ` từ ${agentFilter}` : ""}
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map(([agentId, t]) => (
        <div
          key={agentId}
          className="rounded p-2"
          style={{ backgroundColor: "var(--bg-subtle)" }}
        >
          <p
            className="mb-1 text-[10px] font-semibold"
            style={{ color: "var(--text-muted)" }}
          >
            {t.agentName}
          </p>
          <StreamingText
            text={t.text.slice(0, 2000)}
            isStreaming={runningIds.has(agentId)}
            className="text-xs leading-relaxed"
            ariaLive="polite"
          />
          {t.text.length > 2000 && (
            <p
              className="mt-1 text-[10px] italic"
              style={{ color: "var(--text-muted)" }}
            >
              ...đã rút gọn
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
