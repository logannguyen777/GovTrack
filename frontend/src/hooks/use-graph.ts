import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SubgraphResponse } from "@/lib/types";

// ---- Query key factory ----
export const graphKeys = {
  caseSubgraph: (caseId: string) => ["graph", "case", caseId, "subgraph"] as const,
  traceGraph: (caseId: string) => ["graph", "trace", caseId] as const,
};

// ---- Hooks ----

/**
 * Fetch the knowledge-graph subgraph for a specific case.
 * Returns nodes and edges ready for React Flow consumption.
 */
export function useCaseSubgraph(caseId: string) {
  return useQuery<SubgraphResponse>({
    queryKey: graphKeys.caseSubgraph(caseId),
    queryFn: () =>
      apiClient.get<SubgraphResponse>(`/api/graph/case/${caseId}/subgraph`),
    enabled: Boolean(caseId),
  });
}

/**
 * Fetch the agent-trace graph (AgentStep vertices + edges) for a case.
 * Used by the TraceGraph component to render pipeline execution as a DAG.
 */
export function useTraceGraph(caseId: string) {
  return useQuery<SubgraphResponse>({
    queryKey: graphKeys.traceGraph(caseId),
    queryFn: () =>
      apiClient.get<SubgraphResponse>(`/api/graph/trace/${caseId}`),
    enabled: Boolean(caseId),
    staleTime: 5_000,
  });
}
