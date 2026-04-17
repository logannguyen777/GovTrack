import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { DashboardResponse, InboxItem } from "@/lib/types";

// ---- Query key factory ----
export const leadershipKeys = {
  dashboard: ["dashboard"] as const,
  inbox: ["leader-inbox"] as const,
  weeklyBrief: ["weekly-brief"] as const,
};

// ---- Types ----

export interface WeeklyBriefStats {
  // Fields as returned by GET /api/leadership/weekly-brief
  new_cases: number;
  prev_week_new_cases: number;
  wow_pct: string;
  completed: number;
  overdue: number;
  avg_processing_days: number;
  top_stuck_tthc: Array<{ tthc_code: string; count: number }>;
  // Legacy aliases (may be present if backend changes)
  total_cases?: number;
  avg_days?: number;
}

export interface WeeklyBriefResponse {
  brief: string;
  stats: WeeklyBriefStats;
}

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

/**
 * AI-generated weekly brief from Summarizer agent.
 * Falls back gracefully when the endpoint is unavailable.
 */
export function useWeeklyBrief() {
  return useQuery<WeeklyBriefResponse>({
    queryKey: leadershipKeys.weeklyBrief,
    queryFn: () => apiClient.get<WeeklyBriefResponse>("/api/leadership/weekly-brief"),
    retry: 1,
    staleTime: 5 * 60 * 1000, // 5 minutes — brief is expensive to generate
  });
}
