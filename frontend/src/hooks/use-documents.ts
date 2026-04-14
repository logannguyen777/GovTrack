import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { DocumentResponse } from "@/lib/types";

// ---- Query key factory ----
export const documentKeys = {
  detail: (docId: string) => ["document", docId] as const,
  signedUrl: (docId: string) => ["document", docId, "signed-url"] as const,
};

// ---- Hooks ----

/**
 * Fetch document metadata by ID.
 */
export function useDocument(docId: string) {
  return useQuery<DocumentResponse>({
    queryKey: documentKeys.detail(docId),
    queryFn: () => apiClient.get<DocumentResponse>(`/api/documents/${docId}`),
    enabled: Boolean(docId),
  });
}

/**
 * Fetch a short-lived signed URL for direct OSS access.
 * Stale after 4 minutes to stay safely within a typical 5-minute URL TTL.
 */
interface SignedUrlResponse {
  doc_id: string;
  signed_url: string;
  expires_in: number;
}

export function useDocumentUrl(docId: string) {
  return useQuery<SignedUrlResponse>({
    queryKey: documentKeys.signedUrl(docId),
    queryFn: () =>
      apiClient.get<SignedUrlResponse>(`/api/documents/${docId}/signed-url`),
    enabled: Boolean(docId),
    staleTime: 4 * 60 * 1000, // 4 minutes
    gcTime: 5 * 60 * 1000,    // 5 minutes
  });
}
