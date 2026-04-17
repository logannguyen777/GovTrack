"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/providers/auth-provider";
import { useWSTopic } from "@/hooks/use-ws";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";
import type { WSMessage } from "@/lib/types";

// ---------------------------------------------------------------------------
// LiveAgentIndicator
//
// Subscribes to user:{userId}:notifications WS topic.
// Tracks running agents per case in a local Map<caseId, Set<agentName>>.
// Click opens the artifact panel for the most-recent active case.
// ---------------------------------------------------------------------------

export function LiveAgentIndicator() {
  const { user } = useAuth();
  const setActivePipeline = useArtifactPanelStore((s) => s.setActivePipeline);
  const setCase = useArtifactPanelStore((s) => s.setCase);
  const open = useArtifactPanelStore((s) => s.open);

  // Map<caseId, Set<agentId>> of running agents
  const [activePipelines, setActivePipelines] = React.useState<
    Map<string, Set<string>>
  >(new Map());

  // Track most recently active caseId for click-to-open
  const lastCaseRef = React.useRef<string | null>(null);

  const topic = user ? `user:${user.user_id}:notifications` : "";

  useWSTopic(topic, (event: WSMessage) => {
    const d = event.data as Record<string, unknown>;
    const caseId = (d.case_id as string) ?? "";
    const agentId = (d.agent_id as string) ?? (d.agent_name as string) ?? "";

    if (!caseId || !agentId) return;

    if (event.event === "agent_started") {
      lastCaseRef.current = caseId;
      setActivePipelines((prev) => {
        const next = new Map(prev);
        if (!next.has(caseId)) next.set(caseId, new Set());
        next.get(caseId)!.add(agentId);
        return next;
      });
    } else if (
      event.event === "agent_completed" ||
      event.event === "agent_failed"
    ) {
      setActivePipelines((prev) => {
        const next = new Map(prev);
        const agents = next.get(caseId);
        if (agents) {
          agents.delete(agentId);
          if (agents.size === 0) next.delete(caseId);
        }
        return next;
      });
    }
  });

  // Sync hasActivePipeline into the store whenever the map changes
  React.useEffect(() => {
    setActivePipeline(activePipelines.size > 0);
  }, [activePipelines, setActivePipeline]);

  const totalRunning = React.useMemo(
    () =>
      Array.from(activePipelines.values()).reduce(
        (sum, agents) => sum + agents.size,
        0,
      ),
    [activePipelines],
  );

  const isActive = totalRunning > 0;

  const handleClick = () => {
    const targetCaseId =
      lastCaseRef.current ??
      (activePipelines.size > 0
        ? activePipelines.keys().next().value ?? null
        : null);
    if (targetCaseId) {
      setCase(targetCaseId);
    }
    open();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={cn(
        "flex items-center gap-1.5 rounded-[var(--radius-md)] px-2 py-1 text-xs",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]",
        isActive ? "hover:bg-[var(--bg-surface-raised)]" : "cursor-default",
      )}
      style={{ color: isActive ? "var(--accent-success)" : "var(--text-muted)" }}
      aria-live="polite"
      aria-label={
        isActive
          ? `${totalRunning} agent đang chạy, nhấn để mở panel`
          : "Không có agent nào đang chạy"
      }
      title={isActive ? "Nhấn để xem chi tiết pipeline" : undefined}
    >
      {/* Status dot */}
      <span
        aria-hidden="true"
        className={cn(
          "h-2 w-2 rounded-full shrink-0",
          isActive ? "animate-pulse" : "",
        )}
        style={{
          backgroundColor: isActive
            ? "var(--accent-success)"
            : "var(--text-muted)",
          opacity: isActive ? 1 : 0.5,
        }}
      />
      <span className="hidden sm:inline tabular-nums">
        {isActive
          ? `${totalRunning} agent đang chạy`
          : "Không có agent"}
      </span>
    </button>
  );
}
