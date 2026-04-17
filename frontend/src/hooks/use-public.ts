import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type {
  PublicCaseStatus,
  PublicTTHCItem,
  PublicStatsResponse,
} from "@/lib/types";

// ---- Query key factory ----
export const publicKeys = {
  case: (code: string) => ["public", "case", code] as const,
  tthc: ["public", "tthc"] as const,
  stats: ["public", "stats"] as const,
  audit: (code: string) => ["public", "audit", code] as const,
};

// ---- Types ----

export interface PublicAuditEntry {
  role: string;
  org: string;
  action: string;
  timestamp: string;
}

// ---- Hooks ----

/**
 * Citizen-facing case status lookup by tracking code.
 * Polls every 10 seconds so the citizen sees live progress updates.
 *
 * @param code - Public tracking code shown on the submission receipt
 */
export function usePublicCase(code: string) {
  return useQuery<PublicCaseStatus>({
    queryKey: publicKeys.case(code),
    queryFn: () =>
      apiClient.get<PublicCaseStatus>(`/api/public/cases/${code}`),
    enabled: Boolean(code),
    refetchInterval: 10_000,
  });
}

/**
 * Full catalogue of available TTHC procedures, used on the citizen portal.
 * Data is stable so a long stale time is fine.
 */
export function usePublicTTHC() {
  return useQuery<PublicTTHCItem[]>({
    queryKey: publicKeys.tthc,
    queryFn: () => apiClient.get<PublicTTHCItem[]>("/api/public/tthc"),
    staleTime: 5 * 60 * 1000, // 5 minutes — catalogue changes rarely
  });
}

/**
 * Aggregate statistics shown in the citizen portal hero section.
 */
export function usePublicStats() {
  return useQuery<PublicStatsResponse>({
    queryKey: publicKeys.stats,
    queryFn: () => apiClient.get<PublicStatsResponse>("/api/public/stats"),
    staleTime: 60_000, // 1 minute
  });
}

/**
 * Estonia-style public audit log — who accessed this citizen's case.
 * Endpoint: GET /api/public/track/{case_code}/audit-public
 * Returns entries sorted newest-first by default from the server.
 */
export function usePublicAudit(caseCode: string) {
  return useQuery<PublicAuditEntry[]>({
    queryKey: publicKeys.audit(caseCode),
    queryFn: () =>
      apiClient.get<PublicAuditEntry[]>(
        `/api/public/track/${encodeURIComponent(caseCode)}/audit-public`,
      ),
    enabled: Boolean(caseCode),
    staleTime: 30_000,
    refetchInterval: 30_000,
  });
}
