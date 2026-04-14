import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { LawSearchResult, TTHCSearchResult } from "@/lib/types";

// ---- Query key factory ----
export const searchKeys = {
  law: (query: string, topK?: number) =>
    ["search", "law", query, topK] as const,
  tthc: (query: string) => ["search", "tthc", query] as const,
};

// ---- Hooks ----

/**
 * Semantic law-chunk search backed by Hologres/Proxima embeddings.
 * Only fires when the query is at least 2 characters.
 *
 * @param query   - Vietnamese or mixed search text
 * @param topK    - Maximum results to return (default: 10)
 */
export function useSearchLaw(query: string, topK?: number) {
  const params: Record<string, string> = { query };
  if (topK !== undefined) params.top_k = String(topK);

  return useQuery<LawSearchResult[]>({
    queryKey: searchKeys.law(query, topK),
    queryFn: () => apiClient.get<LawSearchResult[]>("/api/search/law", params),
    enabled: query.length >= 2,
  });
}

/**
 * TTHC procedure name search.
 * Only fires when the query is at least 2 characters.
 *
 * @param query - Vietnamese or mixed search text
 */
export function useSearchTTHC(query: string) {
  return useQuery<TTHCSearchResult[]>({
    queryKey: searchKeys.tthc(query),
    queryFn: () =>
      apiClient.get<TTHCSearchResult[]>("/api/search/tthc", { query }),
    enabled: query.length >= 2,
  });
}
