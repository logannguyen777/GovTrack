import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { AgentTraceResponse, AgentRunRequest } from "@/lib/types";

// ---- Query key factory ----
export const agentKeys = {
  trace: (caseId: string) => ["agent-trace", caseId] as const,
};

// ---- Hooks ----

/**
 * Poll the agent trace for a case.
 * Refetches every 5 seconds while the pipeline is still running.
 */
export function useAgentTrace(caseId: string) {
  return useQuery<AgentTraceResponse>({
    queryKey: agentKeys.trace(caseId),
    queryFn: () =>
      apiClient.get<AgentTraceResponse>(`/api/agents/trace/${caseId}`),
    enabled: Boolean(caseId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling once the pipeline reaches a terminal state
      return status === "completed" || status === "failed" ? false : 5000;
    },
  });
}

/**
 * Trigger the agent pipeline for a case.
 */
interface RunAgentsResponse {
  case_id: string;
  pipeline: string;
  status: string;
}

export function useRunAgents(caseId: string) {
  return useMutation<RunAgentsResponse, Error, AgentRunRequest>({
    mutationFn: (body) =>
      apiClient.post<RunAgentsResponse>(`/api/agents/run/${caseId}`, body),
  });
}
