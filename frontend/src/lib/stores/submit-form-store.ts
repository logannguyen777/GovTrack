import { create } from "zustand";
import { persist } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface UploadedFile {
  id: string;
  name: string;
  url?: string;
  entities?: unknown[];
}

interface ExtractedEntity {
  key: string;
  value: unknown;
  confidence: number;
}

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------

// Only these keys are allowed in formData. Prevents stale / injected keys
// (e.g. "file_count") from leaking from localStorage into the LLM precheck.
const ALLOWED_FORM_KEYS = new Set<string>([
  "applicant_name",
  "applicant_id_number",
  "applicant_phone",
  "applicant_address",
  "applicant_dob",
  "applicant_email",
  "applicant_gender",
  "notes",
  "purpose",
  "project_name",
  "project_address",
  "construction_area",
  "land_parcel",
  "land_area",
  "company_name",
  "company_capital",
  "business_address",
  "certificate_type",
  "project_capacity",
]);

// Keys that count toward the "AI đã điền X/Y trường" progress counter.
const REQUIRED_APPLICANT_KEYS = [
  "applicant_name",
  "applicant_id_number",
  "applicant_phone",
  "applicant_address",
];

interface SubmitFormState {
  tthcCode: string | null;
  formData: Record<string, unknown>;
  uploadedFiles: UploadedFile[];
  aiFilledFields: string[]; // serialized as array (Set not serializable)
  totalRequiredFields: number;

  setField: (name: string, value: unknown, fromAI?: boolean) => void;
  setFromExtraction: (entities: ExtractedEntity[]) => void;
  hydrateFromPrefill: (id: string) => Promise<void>;
  reset: () => void;
  resetForTTHC: (tthcCode: string) => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSubmitFormStore = create<SubmitFormState>()(
  persist(
    (set) => ({
      tthcCode: null,
      formData: {},
      uploadedFiles: [],
      aiFilledFields: [],
      totalRequiredFields: 0,

      setField: (name, value, fromAI = false) => {
        // Hard allowlist: reject unknown keys so stale "file_count" from a
        // prior session can never contaminate the precheck payload.
        if (!ALLOWED_FORM_KEYS.has(name)) {
          return;
        }
        set((s) => {
          const nextFilled = fromAI
            ? s.aiFilledFields.includes(name)
              ? s.aiFilledFields
              : [...s.aiFilledFields, name]
            : s.aiFilledFields;
          const totalReq = Math.max(
            s.totalRequiredFields,
            REQUIRED_APPLICANT_KEYS.length,
          );
          return {
            formData: { ...s.formData, [name]: value },
            aiFilledFields: nextFilled,
            totalRequiredFields: totalReq,
          };
        });
      },

      setFromExtraction: (entities) =>
        set((s) => {
          const newFields: Record<string, unknown> = {};
          const newAIFields: string[] = [...s.aiFilledFields];
          for (const { key, value, confidence } of entities) {
            if (confidence >= 0.5 && ALLOWED_FORM_KEYS.has(key)) {
              newFields[key] = value;
              if (!newAIFields.includes(key)) newAIFields.push(key);
            }
          }
          return {
            formData: { ...s.formData, ...newFields },
            aiFilledFields: newAIFields,
          };
        }),

      hydrateFromPrefill: async (id: string) => {
        try {
          const res = await fetch(`/api/assistant/prefill/${id}`);
          if (!res.ok) return;
          // Backend returns ExtractResponse: {extraction_id, document_type, entities:[{key,value,confidence}], raw_text, confidence}
          const data = (await res.json()) as {
            entities?: Array<{ key: string; value: unknown; confidence: number }>;
          };
          const entities = data.entities ?? [];
          if (entities.length === 0) return;
          const formPatch: Record<string, unknown> = {};
          const aiFields = new Set<string>();
          for (const e of entities) {
            if (e.confidence >= 0.8 && ALLOWED_FORM_KEYS.has(e.key)) {
              formPatch[e.key] = e.value;
              aiFields.add(e.key);
            }
          }
          set((s) => ({
            formData: { ...s.formData, ...formPatch },
            aiFilledFields: Array.from(
              new Set<string>([...s.aiFilledFields, ...aiFields]),
            ),
          }));
        } catch {
          // silently fail — prefill is best-effort
        }
      },

      reset: () =>
        set({
          tthcCode: null,
          formData: {},
          uploadedFiles: [],
          aiFilledFields: [],
          totalRequiredFields: 0,
        }),

      // Call on wizard mount — ensures a fresh session for each TTHC without
      // leaking formData / aiFilledFields from the previous flow's localStorage.
      resetForTTHC: (tthcCode) =>
        set({
          tthcCode,
          formData: {},
          uploadedFiles: [],
          aiFilledFields: [],
          totalRequiredFields: REQUIRED_APPLICANT_KEYS.length,
        }),
    }),
    {
      name: "govflow-submit-form",
      // aiFilledFields stored as array in localStorage; uploadedFiles excluded (large)
      partialize: (state) => ({
        tthcCode: state.tthcCode,
        formData: state.formData,
        aiFilledFields: state.aiFilledFields,
      }),
    },
  ),
);

// ---------------------------------------------------------------------------
// Derived selector helpers
// ---------------------------------------------------------------------------

/** Returns the aiFilledFields as a Set for O(1) lookups at component level */
export function selectAIFilledSet(state: SubmitFormState): Set<string> {
  return new Set(state.aiFilledFields);
}
