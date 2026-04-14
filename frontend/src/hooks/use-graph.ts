import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { SubgraphResponse } from "@/lib/types";

// ---- Query key factory ----
export const graphKeys = {
  caseSubgraph: (caseId: string) => ["graph", "case", caseId, "subgraph"] as const,
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
