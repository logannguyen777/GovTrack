"use client";

import { useEffect } from "react";
import { useAgentArtifactStore } from "@/lib/stores/agent-artifact-store";
import { useWSTopic } from "@/hooks/use-ws";
import type { WSMessage } from "@/lib/types";

/**
 * useAgentArtifact — hydrate + live subscribe for a case artifact bucket.
 *
 * 1. On caseId change: REST hydrate from GET /api/agents/trace/{caseId}/artifact
 * 2. Subscribe WS topic case:{caseId} and ingest each event into the store
 *
 * Returns the current artifact bucket for the caseId, or a zero-state bucket.
 */
export function useAgentArtifact(caseId: string | null) {
  const data = useAgentArtifactStore((s) =>
    caseId ? s.byCaseId[caseId] : null,
  );
  const ingest = useAgentArtifactStore((s) => s.ingestEvent);
  const hydrate = useAgentArtifactStore((s) => s.hydrate);

  // Hydrate from REST when caseId changes.
  // Backend returns {events:[{type, ...}]} (reconstructed timeline). We must
  // iterate each event through ingestEvent() so the store builds the same
  // activeAgents / thinking / toolCalls buckets as live WS events would.
  useEffect(() => {
    if (!caseId) return;
    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("govflow-token")
        : null;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    fetch(`/api/agents/trace/${caseId}/artifact`, { headers })
      .then((r) => (r.ok ? r.json() : null))
      .then((snap) => {
        if (!snap || !caseId) return;
        // Clear the bucket so re-navigation doesn't double-count.
        hydrate(caseId, {});
        const events = (snap.events ?? []) as Array<{
          type: string;
          [k: string]: unknown;
        }>;
        for (const e of events) {
          const { type, ...rest } = e;
          ingest(caseId, { type, data: rest });
        }
      })
      .catch(() => {
        // Gracefully degrade — live WS events will populate the store
      });
  }, [caseId, hydrate, ingest]);

  // Subscribe WS topic case:{caseId}
  useWSTopic(caseId ? `case:${caseId}` : "", (event: WSMessage) => {
    if (caseId) {
      ingest(caseId, { type: event.event, data: event.data });
    }
  });

  return (
    data ?? {
      activeAgents: [],
      thinking: {},
      toolCalls: [],
      searches: [],
      graphOps: [],
    }
  );
}
