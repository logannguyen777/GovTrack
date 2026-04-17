"use client";

import { useQuery, useMutation } from "@tanstack/react-query";

// ---------------------------------------------------------------------------
// Types — aligned with backend Pydantic models in chat_schemas.py
// ---------------------------------------------------------------------------

export interface FieldHelpResponse {
  explanation: string;
  example_correct: string | null;
  example_incorrect: string | null;
  related_law: string | null;
}

export interface IntentPrimary {
  tthc_code: string;
  name: string;
  department: string;
  sla_days: number;
  confidence: number;
}
export interface IntentAlternative {
  tthc_code: string;
  name: string;
  confidence: number;
}
export interface IntentResponse {
  primary: IntentPrimary | null;
  alternatives: IntentAlternative[];
  explanation: string | null;
}

export interface ExplainCaseResponse {
  explanation: string;
  next_step: string | null;
}

export interface PrefillResponse {
  extraction_id?: string;
  document_type?: string | null;
  entities?: Array<{ key: string; value: unknown; confidence: number }>;
  raw_text?: string;
  confidence?: number;
}

export interface ComplianceRecommendationResponse {
  decision: string;
  reasoning: string;
  citations: Array<Record<string, unknown>>;
  confidence: number;
}

interface PublicTTHCItem {
  tthc_code: string;
  name: string;
  department: string;
  sla_days: number;
  fee: string;
  required_components: string[];
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useFieldHelp(tthcCode: string, fieldName: string) {
  return useQuery<FieldHelpResponse>({
    queryKey: ["field-help", tthcCode, fieldName],
    queryFn: async () => {
      const r = await fetch(
        `/api/assistant/field-help?tthc_code=${encodeURIComponent(tthcCode)}&field=${encodeURIComponent(fieldName)}`,
      );
      if (!r.ok) throw new Error(`${r.status}`);
      return r.json();
    },
    staleTime: Infinity,
    enabled: Boolean(tthcCode) && Boolean(fieldName),
  });
}

export function useIntent() {
  return useMutation<IntentResponse, Error, string>({
    mutationFn: async (text: string) => {
      if (process.env.NEXT_PUBLIC_MOCK_ASSISTANT === "true") {
        await new Promise((r) => setTimeout(r, 400));
        return {
          primary: {
            tthc_code: "1.004415",
            name: "Cấp giấy phép xây dựng",
            confidence: 0.95,
            department: "Sở Xây dựng",
            sla_days: 15,
          },
          alternatives: [
            { tthc_code: "1.000046", name: "GCN quyền sử dụng đất", confidence: 0.3 },
          ],
          explanation: "Mock response",
        };
      }

      const res = await fetch("/api/assistant/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) throw new Error(`${res.status}`);
      const raw = (await res.json()) as {
        primary_tthc_code: string | null;
        primary_confidence: number;
        explanation: string | null;
        alternatives: IntentAlternative[];
      };

      // Enrich primary with public TTHC detail (name/department/sla_days)
      let primary: IntentPrimary | null = null;
      if (raw.primary_tthc_code) {
        try {
          const tthcList = (await fetch("/api/public/tthc").then((r) =>
            r.ok ? r.json() : [],
          )) as PublicTTHCItem[];
          const detail = tthcList.find((t) => t.tthc_code === raw.primary_tthc_code);
          if (detail) {
            primary = {
              tthc_code: detail.tthc_code,
              name: detail.name,
              department: detail.department,
              sla_days: detail.sla_days,
              confidence: raw.primary_confidence,
            };
          } else {
            primary = {
              tthc_code: raw.primary_tthc_code,
              name: raw.primary_tthc_code,
              department: "",
              sla_days: 0,
              confidence: raw.primary_confidence,
            };
          }
        } catch {
          primary = {
            tthc_code: raw.primary_tthc_code,
            name: raw.primary_tthc_code,
            department: "",
            sla_days: 0,
            confidence: raw.primary_confidence,
          };
        }
      }

      return {
        primary,
        alternatives: raw.alternatives ?? [],
        explanation: raw.explanation ?? null,
      };
    },
  });
}

export function useExplainCase(code: string) {
  return useQuery<ExplainCaseResponse>({
    queryKey: ["explain-case", code],
    queryFn: async () => {
      const r = await fetch(
        `/api/assistant/explain-case/${encodeURIComponent(code)}`,
      );
      if (!r.ok) throw new Error(`${r.status}`);
      return r.json();
    },
    staleTime: 60_000,
    enabled: Boolean(code),
    retry: false,
  });
}

export function usePrefill(extractionId: string | null) {
  return useQuery<PrefillResponse | null>({
    queryKey: ["prefill", extractionId],
    queryFn: async () => {
      if (!extractionId) return null;
      const r = await fetch(
        `/api/assistant/prefill/${encodeURIComponent(extractionId)}`,
      );
      if (!r.ok) return null;
      return r.json();
    },
    enabled: Boolean(extractionId),
    retry: false,
  });
}

export function useComplianceRecommendation(caseId: string) {
  return useQuery<ComplianceRecommendationResponse | null>({
    queryKey: ["compliance-rec", caseId],
    queryFn: async () => {
      const token =
        typeof window !== "undefined"
          ? localStorage.getItem("govflow-token")
          : null;
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const r = await fetch(
        `/api/assistant/recommendation/${encodeURIComponent(caseId)}`,
        { headers },
      );
      if (!r.ok) return null;
      return r.json();
    },
    enabled: Boolean(caseId),
    // Allow 1 retry in case auth token hydrates after first failed attempt
    retry: 1,
    retryDelay: 1500,
  });
}
