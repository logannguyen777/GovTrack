import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { AuditEventResponse } from "@/lib/types";

// ---- Query key factory ----
export const auditKeys = {
  events: (params?: {
    event_type?: string;
    case_id?: string;
    limit?: number;
  }) => ["audit-events", params] as const,
};

// ---- Hooks ----

/**
 * Fetch audit events with optional filters.
 *
 * @param params.event_type - Filter by event type (e.g. "GRAPH_WRITE")
 * @param params.case_id    - Filter events scoped to a specific case
 * @param params.limit      - Maximum number of events to return
 */
export function useAuditEvents(params?: {
  event_type?: string;
  case_id?: string;
  limit?: number;
}) {
  const queryParams: Record<string, string> = {};
  if (params?.event_type) queryParams.event_type = params.event_type;
  if (params?.case_id) queryParams.case_id = params.case_id;
  if (params?.limit !== undefined) queryParams.limit = String(params.limit);

  return useQuery<AuditEventResponse[]>({
    queryKey: auditKeys.events(params),
    queryFn: () =>
      apiClient.get<AuditEventResponse[]>("/api/audit/events", queryParams),
  });
}
