import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { DashboardResponse, InboxItem } from "@/lib/types";

// ---- Query key factory ----
export const leadershipKeys = {
  dashboard: ["dashboard"] as const,
  inbox: ["leader-inbox"] as const,
};

// ---- Hooks ----

/**
 * Leadership KPI dashboard: case counts, by-status breakdown,
 * by-department breakdown, and agent performance metrics.
 */
export function useDashboard() {
  return useQuery<DashboardResponse>({
    queryKey: leadershipKeys.dashboard,
    queryFn: () => apiClient.get<DashboardResponse>("/api/leadership/dashboard"),
  });
}

/**
 * Leader inbox: cases awaiting a leader decision or signature.
 */
export function useLeaderInbox() {
  return useQuery<InboxItem[]>({
    queryKey: leadershipKeys.inbox,
    queryFn: () => apiClient.get<InboxItem[]>("/api/leadership/inbox"),
  });
}
