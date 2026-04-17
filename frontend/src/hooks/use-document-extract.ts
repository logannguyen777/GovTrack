"use client";

import { useMutation } from "@tanstack/react-query";
import type { Entity } from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExtractResponse {
  extraction_id: string;
  /** Backend field name is document_type; doc_type kept as alias for backward compat */
  document_type?: string | null;
  doc_type?: string | null;
  entities: Entity[];
  confidence: number;
  thumbnail_url?: string;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useDocumentExtract() {
  return useMutation({
    mutationFn: async ({
      file,
      tthcCode,
    }: {
      file: File;
      tthcCode?: string;
    }): Promise<ExtractResponse> => {
      // Mock mode
      if (process.env.NEXT_PUBLIC_MOCK_ASSISTANT === "true") {
        await new Promise((r) => setTimeout(r, 1500));
        return {
          extraction_id: `mock-${crypto.randomUUID()}`,
          doc_type: "CCCD",
          confidence: 0.96,
          entities: [
            { key: "applicant_name", value: "NGUYỄN VĂN A", confidence: 0.98 },
            { key: "applicant_id_number", value: "012345678901", confidence: 0.95 },
            { key: "date_of_birth", value: "01/01/1990", confidence: 0.93 },
            { key: "applicant_address", value: "Số 1, Đường ABC, Quận Cầu Giấy, Hà Nội", confidence: 0.82 },
            { key: "gender", value: "Nam", confidence: 0.99 },
          ],
        };
      }

      const fd = new FormData();
      fd.append("file", file);
      if (tthcCode) fd.append("tthc_code", tthcCode);

      const res = await fetch("/api/documents/extract", {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<ExtractResponse>;
    },
  });
}
