"use client";

/**
 * WSCacheInvalidator — subscribes to wildcard WS events and invalidates
 * TanStack Query caches for well-known event types:
 *
 *   case_updated        → ["case", caseId]
 *   agent_step_completed→ ["trace", caseId]
 *   consult_complete    → ["case", caseId]
 *   audit_event         → ["audit"]
 *
 * Mount once inside (internal)/layout.tsx.
 */

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useWSTopic } from "@/hooks/use-ws";
import type { WSMessage } from "@/lib/types";

export function WSCacheInvalidator() {
  const queryClient = useQueryClient();

  const handleMessage = useCallback(
    (msg: WSMessage) => {
      const data = msg.data as Record<string, unknown> | null;
      const caseId =
        (data?.case_id as string | undefined) ??
        (data?.caseId as string | undefined) ??
        null;

      switch (msg.event) {
        case "case_updated":
          if (caseId) {
            void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
          }
          void queryClient.invalidateQueries({ queryKey: ["cases"] });
          break;

        case "agent_step_completed":
          if (caseId) {
            void queryClient.invalidateQueries({ queryKey: ["trace", caseId] });
            void queryClient.invalidateQueries({ queryKey: ["graph", caseId] });
          }
          break;

        case "consult_complete":
          if (caseId) {
            void queryClient.invalidateQueries({ queryKey: ["case", caseId] });
          }
          break;

        case "audit_event":
          void queryClient.invalidateQueries({ queryKey: ["audit"] });
          break;

        default:
          break;
      }
    },
    [queryClient],
  );

  // Subscribe to all topics via wildcard
  useWSTopic("*", handleMessage);

  // Renders nothing — pure side-effect component
  return null;
}
