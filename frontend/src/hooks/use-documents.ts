import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import type { DocumentResponse } from "@/lib/types";

// ---- Query key factory ----
export const documentKeys = {
  detail: (docId: string) => ["document", docId] as const,
  signedUrl: (docId: string) => ["document", docId, "signed-url"] as const,
  byCase: (caseId: string) => ["documents", "case", caseId] as const,
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

/**
 * Fetch all documents attached to a case.
 * Used in the documents list page to navigate to the first doc.
 */
export function useCaseDocuments(caseId: string) {
  return useQuery<DocumentResponse[]>({
    queryKey: documentKeys.byCase(caseId),
    queryFn: () =>
      apiClient.get<DocumentResponse[]>(`/api/cases/${caseId}/documents`),
    enabled: Boolean(caseId),
    staleTime: 30_000,
  });
}

/**
 * Fetch the full document vertex including extracted_text / ocr_text.
 * The base useDocument hook returns DocumentResponse which may be a summary.
 * This hook re-uses the same endpoint but is semantically named for the
 * extraction use-case so callers are self-documenting.
 */
export function useDocumentExtraction(docId: string) {
  return useQuery<DocumentResponse & { extracted_text?: string; ocr_text?: string }>({
    queryKey: [...documentKeys.detail(docId), "extraction"] as const,
    queryFn: () =>
      apiClient.get<DocumentResponse & { extracted_text?: string; ocr_text?: string }>(
        `/api/documents/${docId}`,
      ),
    enabled: Boolean(docId),
    staleTime: 60_000,
  });
}
