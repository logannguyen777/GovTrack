"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, ChevronLeft, ChevronRight, Loader2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import { useSubmitFormStore } from "@/lib/stores/submit-form-store";
import { AIFillProgress } from "./ai-fill-progress";

// Demo sample shape returned by GET /api/public/demo-samples/{code}
interface DemoSampleFile {
  filename: string;
  url: string;
  mime_type: string;
  size_bytes?: number;
}
interface DemoSampleResponse {
  tthc_code: string;
  applicant: {
    applicant_name: string;
    applicant_id_number: string;
    applicant_phone: string;
    applicant_address: string;
  };
  sample_files: DemoSampleFile[];
  notes: string;
}
import { StepTTHC } from "./step-tthc";
import { StepCitizenInfo } from "./step-citizen-info";
import { StepUpload, type UploadFile } from "./step-upload";
import { StepReview } from "./step-review";
import type { CitizenInfoData } from "./step-citizen-info";
import type { CaseCreate, CaseResponse, BundleCreate, BundleResponse } from "@/lib/types";

// ---------------------------------------------------------------------------
// Step metadata
// ---------------------------------------------------------------------------

const STEPS = [
  {
    label: "Chọn thủ tục",
    key: "tthc",
    description: "Xác nhận thủ tục hành chính bạn muốn thực hiện",
  },
  {
    label: "Thông tin công dân",
    key: "info",
    description: "Nhập thông tin người nộp hồ sơ",
  },
  {
    label: "Tải tài liệu",
    key: "upload",
    description: "Tải lên các tài liệu theo yêu cầu",
  },
  {
    label: "Xem lại & nộp",
    key: "review",
    description: "Kiểm tra lại thông tin trước khi nộp",
  },
];

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface SubmitWizardProps {
  tthcCode: string;
  prefillId?: string | null;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SubmitWizard({ tthcCode, prefillId }: SubmitWizardProps) {
  const router = useRouter();
  const decoded = decodeURIComponent(tthcCode);

  // Prefill hydration — hydrateFromPrefill fetches the extraction itself,
  // so we don't need usePrefill() on top (avoids a redundant GET).
  const hydrateFromPrefill = useSubmitFormStore((s) => s.hydrateFromPrefill);
  const storeData = useSubmitFormStore((s) => s.formData);
  const aiFilledFields = useSubmitFormStore((s) => s.aiFilledFields);
  const setField = useSubmitFormStore((s) => s.setField);
  const totalRequiredFields = useSubmitFormStore((s) => s.totalRequiredFields);
  const resetForTTHC = useSubmitFormStore((s) => s.resetForTTHC);

  // Reset session state whenever the wizard mounts for a new TTHC — prevents
  // stale formData / aiFilledFields from a previous localStorage session from
  // leaking into the current precheck payload (e.g. "file_count", "9/1 trường").
  React.useEffect(() => {
    resetForTTHC(decoded);
  }, [decoded, resetForTTHC]);

  React.useEffect(() => {
    if (prefillId) {
      void hydrateFromPrefill(prefillId);
    }
  }, [prefillId, hydrateFromPrefill]);

  // Local state
  const [step, setStep] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);
  const [files, setFiles] = React.useState<UploadFile[]>([]);
  const [confirmed, setConfirmed] = React.useState(false);
  const [errors, setErrors] = React.useState<Partial<Record<keyof CitizenInfoData, string>>>({});
  const [filling, setFilling] = React.useState(false);

  // One-click demo fill: GET /api/public/demo-samples/{tthc} → populate form + attach sample files
  async function handleFillSample() {
    setFilling(true);
    try {
      const sample = await apiClient.get<DemoSampleResponse>(
        `/api/public/demo-samples/${encodeURIComponent(decoded)}`,
      );
      // 1. Populate form fields (mark as AI-filled so purple badge shows)
      setField("applicant_name", sample.applicant.applicant_name, true);
      setField("applicant_id_number", sample.applicant.applicant_id_number, true);
      setField("applicant_phone", sample.applicant.applicant_phone, true);
      setField("applicant_address", sample.applicant.applicant_address, true);

      // 2. Fetch sample files as Blobs → convert to File → attach
      const attached: UploadFile[] = [];
      for (const f of sample.sample_files) {
        try {
          const res = await fetch(f.url);
          if (!res.ok) continue;
          const blob = await res.blob();
          attached.push({
            id: crypto.randomUUID(),
            file: new File([blob], f.filename, { type: f.mime_type }),
          });
        } catch {
          // Best-effort — skip missing sample files silently
        }
      }
      setFiles((prev) => [...prev, ...attached]);

      toast.success(
        `Đã điền mẫu: ${sample.applicant.applicant_name} + ${attached.length} tệp.`,
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không rõ lỗi";
      toast.error(`Không lấy được dữ liệu mẫu: ${msg}`);
    } finally {
      setFilling(false);
    }
  }

  // Sync form from store
  const citizenData: CitizenInfoData = {
    applicant_name: String(storeData.applicant_name ?? ""),
    applicant_id_number: String(storeData.applicant_id_number ?? ""),
    applicant_phone: String(storeData.applicant_phone ?? ""),
    applicant_address: String(storeData.applicant_address ?? ""),
  };

  function handleFieldChange(field: keyof CitizenInfoData, value: string) {
    setField(field, value, false);
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  }

  function validateStep1(): Partial<Record<keyof CitizenInfoData, string>> {
    const newErrors: Partial<Record<keyof CitizenInfoData, string>> = {};
    if (!citizenData.applicant_name.trim()) {
      newErrors.applicant_name = "Vui lòng nhập họ và tên";
    }
    if (!citizenData.applicant_id_number.trim()) {
      newErrors.applicant_id_number = "Vui lòng nhập số CCCD";
    } else if (!/^\d{12}$/.test(citizenData.applicant_id_number.trim())) {
      newErrors.applicant_id_number = "Số CCCD phải gồm 12 chữ số";
    }
    return newErrors;
  }

  function handleNext() {
    if (step === 1) {
      const newErrors = validateStep1();
      if (Object.keys(newErrors).length > 0) {
        setErrors(newErrors);
        return;
      }
    }
    setStep(step + 1);
  }

  function canNext(): boolean {
    if (step === 0) return Boolean(decoded);
    return true;
  }

  async function handleSubmit() {
    if (!confirmed) return;
    setSubmitting(true);
    try {
      const caseBody: CaseCreate = {
        tthc_code: decoded,
        department_id: "DEPT-QLDT",
        applicant_name: citizenData.applicant_name,
        applicant_id_number: citizenData.applicant_id_number,
        applicant_phone: citizenData.applicant_phone,
        applicant_address: citizenData.applicant_address,
      };
      const caseRes = await apiClient.post<CaseResponse>("/api/public/cases", caseBody);

      if (files.length > 0) {
        // Prefix each filename with its index so duplicate client-side names
        // still map to distinct OSS keys (and distinct upload URLs).
        const bundleBody: BundleCreate = {
          files: files.map((f, i) => ({
            filename: `${i}_${f.file.name}`,
            content_type: f.file.type || "application/octet-stream",
            size_bytes: f.file.size,
          })),
        };
        const bundleRes = await apiClient.post<BundleResponse>(
          `/api/public/cases/${caseRes.case_id}/bundles`,
          bundleBody,
        );

        // Upload by positional index — backend preserves order.
        const failures: string[] = [];
        for (let i = 0; i < bundleRes.upload_urls.length; i++) {
          const url = bundleRes.upload_urls[i];
          const match = files[i];
          if (!match || !url.signed_url) continue;
          try {
            const res = await fetch(url.signed_url, {
              method: "PUT",
              body: match.file,
              headers: { "Content-Type": match.file.type },
            });
            if (!res.ok) failures.push(match.file.name);
          } catch {
            failures.push(match.file.name);
          }
        }
        if (failures.length > 0) {
          throw new Error(
            `Không tải được ${failures.length} tệp: ${failures.join(", ")}`,
          );
        }
      }

      await apiClient.post(`/api/public/cases/${caseRes.case_id}/finalize`);
      toast.success(`Hồ sơ đã nộp thành công! Mã: ${caseRes.code}`);
      router.push(`/submit/${encodeURIComponent(decoded)}/receipt?case=${encodeURIComponent(caseRes.code)}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Không rõ lỗi";
      toast.error(`Có lỗi khi nộp hồ sơ: ${msg}`);
    } finally {
      setSubmitting(false);
    }
  }

  const currentStepMeta = STEPS[step];
  // Don't divide by zero; store typically tracks 2 (required fields for the
  // wizard: applicant_name + applicant_id_number). Phone and address are
  // optional on the backend CaseCreate schema.
  // Applicant form has a fixed set of 5 fields (name, id, phone, address, dob).
  // Store's totalRequiredFields may be 0 if never set, so cap to 5 min to avoid
  // division-by-one bugs (filled=9/total=1 → 900%).
  const requiredTotal = Math.max(5, totalRequiredFields);
  const filledSafe = Math.min(aiFilledFields.length, requiredTotal);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="flex items-start justify-between gap-3">
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          Nộp hồ sơ trực tuyến
        </h1>

        {/* One-click demo fill — visible throughout wizard, targets the judge */}
        <button
          type="button"
          onClick={handleFillSample}
          disabled={filling}
          className="flex shrink-0 items-center gap-1.5 rounded-lg border border-purple-300 bg-gradient-to-br from-purple-50 to-violet-50 px-3 py-2 text-xs font-medium text-purple-700 shadow-sm transition-opacity hover:opacity-90 disabled:opacity-50 dark:border-purple-700 dark:from-purple-950 dark:to-violet-950 dark:text-purple-200"
          title="Điền dữ liệu mẫu + đính kèm tài liệu mẫu cho thủ tục này (demo)"
        >
          {filling ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Wand2 className="h-3.5 w-3.5" />
          )}
          {filling ? "Đang điền..." : "Điền mẫu (demo)"}
        </button>
      </div>

      {/* AI fill progress (shows when AI has filled something) */}
      {aiFilledFields.length > 0 && (
        <AIFillProgress
          filled={filledSafe}
          total={requiredTotal}
          className="mt-4"
        />
      )}

      {/* Step indicator */}
      <div className="mt-6 flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s.key} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                i <= step
                  ? "bg-[var(--accent-primary)] text-white"
                  : "bg-[var(--bg-surface-raised)] text-[var(--text-muted)]"
              }`}
            >
              {i < step ? <CheckCircle className="h-4 w-4" /> : i + 1}
            </div>
            <span
              className={`text-xs ${i <= step ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"}`}
            >
              {s.label}
            </span>
            {i < STEPS.length - 1 && (
              <div className="h-px w-6 bg-[var(--border-subtle)]" />
            )}
          </div>
        ))}
      </div>

      {/* Step content */}
      <div className="mt-8 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
        <p className="mb-4 text-sm text-[var(--text-secondary)] border-b border-[var(--border-subtle)] pb-4">
          {currentStepMeta.description}
        </p>

        {step === 0 && <StepTTHC tthcCode={decoded} />}

        {step === 1 && (
          <StepCitizenInfo
            tthcCode={decoded}
            data={citizenData}
            errors={errors}
            onChange={handleFieldChange}
          />
        )}

        {step === 2 && (
          <StepUpload
            tthcCode={decoded}
            files={files}
            onFilesChange={setFiles}
          />
        )}

        {step === 3 && (
          <StepReview
            tthcCode={decoded}
            data={citizenData}
            files={files}
            confirmed={confirmed}
            onConfirmChange={setConfirmed}
          />
        )}
      </div>

      {/* Navigation buttons */}
      <div className="mt-6 flex justify-between">
        <button
          onClick={() => (step === 0 ? router.back() : setStep(step - 1))}
          className="flex items-center gap-1 rounded-md border border-[var(--border-default)] px-4 py-2 text-sm transition-colors hover:bg-[var(--bg-surface-raised)]"
        >
          <ChevronLeft className="h-4 w-4" />
          {step === 0 ? "Quay lại" : "Bước trước"}
        </button>

        {step < STEPS.length - 1 ? (
          <button
            onClick={handleNext}
            disabled={!canNext()}
            className="flex items-center gap-1 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            Tiếp theo <ChevronRight className="h-4 w-4" />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={submitting || !confirmed}
            className="flex items-center gap-1 rounded-md bg-[var(--accent-primary)] px-6 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            title={!confirmed ? "Vui lòng xác nhận thông tin trước khi nộp" : undefined}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Đang nộp...
              </>
            ) : (
              "Nộp hồ sơ"
            )}
          </button>
        )}
      </div>
    </div>
  );
}
