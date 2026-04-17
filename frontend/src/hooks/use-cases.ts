import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type {
  CaseResponse,
  CaseCreate,
  CaseListResponse,
  BundleCreate,
  BundleResponse,
} from "@/lib/types";

// ---- Batch finalize types ----
export interface BatchFinalizeRequest {
  case_ids: string[];
  decision: "approve" | "reject" | "request_supplement";
  notes?: string;
}

export interface BatchFinalizeResponse {
  succeeded: string[];
  failed: Array<{ case_id: string; error: string }>;
}

// ---- Query key factory ----
export const caseKeys = {
  all: ["cases"] as const,
  list: (params?: { page?: number; status?: string }) =>
    [...caseKeys.all, "list", params] as const,
  detail: (caseId: string) => ["case", caseId] as const,
};

// ---- Hooks ----

/**
 * Paginated case list with optional status filter.
 */
export function useCases(params?: { page?: number; status?: string }) {
  const queryParams: Record<string, string> = {};
  if (params?.page !== undefined) queryParams.page = String(params.page);
  if (params?.status) queryParams.status = params.status;

  return useQuery<CaseListResponse>({
    queryKey: caseKeys.list(params),
    queryFn: () =>
      apiClient.get<CaseListResponse>("/api/cases", queryParams),
  });
}

/**
 * Single case by ID. Only fetches when caseId is truthy.
 */
export function useCase(
  caseId: string,
  options?: Omit<UseQueryOptions<CaseResponse>, "queryKey" | "queryFn">,
) {
  return useQuery<CaseResponse>({
    queryKey: caseKeys.detail(caseId),
    queryFn: () => apiClient.get<CaseResponse>(`/api/cases/${caseId}`),
    enabled: Boolean(caseId),
    ...options,
  });
}

/**
 * Create a new case. Invalidates the cases list on success.
 */
export function useCreateCase() {
  const queryClient = useQueryClient();

  return useMutation<CaseResponse, Error, CaseCreate>({
    mutationFn: (body) => apiClient.post<CaseResponse>("/api/cases", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: caseKeys.all });
    },
  });
}

/**
 * Upload a document bundle for a specific case.
 */
export function useCreateBundle(caseId: string) {
  return useMutation<BundleResponse, Error, BundleCreate>({
    mutationFn: (body) =>
      apiClient.post<BundleResponse>(`/api/cases/${caseId}/bundles`, body),
  });
}

/**
 * Finalize a case, triggering downstream processing.
 * Invalidates both the specific case and the cases list.
 */
export function useFinalizeCase() {
  const queryClient = useQueryClient();

  return useMutation<CaseResponse, Error, string>({
    mutationFn: (caseId) =>
      apiClient.post<CaseResponse>(`/api/cases/${caseId}/finalize`),
    onSuccess: (_data, caseId) => {
      queryClient.invalidateQueries({ queryKey: caseKeys.all });
      queryClient.invalidateQueries({ queryKey: caseKeys.detail(caseId) });
    },
  });
}

/**
 * Batch-finalize multiple cases with a single decision.
 * Returns succeeded / failed case IDs.
 * Invalidates case list, dashboard, and leader inbox on completion.
 */
export function useBatchFinalize() {
  const queryClient = useQueryClient();

  return useMutation<BatchFinalizeResponse, Error, BatchFinalizeRequest>({
    mutationFn: (body) =>
      apiClient.post<BatchFinalizeResponse>("/api/cases/batch-finalize", body),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: caseKeys.all });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["leader-inbox"] });
    },
  });
}
