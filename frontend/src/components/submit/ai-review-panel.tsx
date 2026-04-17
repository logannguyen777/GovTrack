"use client";

import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import {
  AlertTriangle,
  Sparkles,
  Loader2,
  CheckCircle2,
  CheckCheck,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GapItem {
  field: string;
  description: string;
  law_ref?: string;
  severity: "error" | "warning" | "info";
}

export interface PrecheckResult {
  gaps: GapItem[];
  is_complete: boolean;
  summary: string;
}

export interface FormSuggestion {
  field: string;
  value: string;
  confidence: number;
  source: string; // e.g. "Trích từ ảnh CCCD upload"
}

export interface FormSuggestResult {
  suggestions: FormSuggestion[];
}

interface AIReviewPanelProps {
  tthcCode: string;
  formData: Record<string, unknown>;
  /** URLs of uploaded files for AI to read */
  uploadedFileUrls?: string[];
  /** Called when user accepts a suggestion */
  onAcceptSuggestion?: (field: string, value: string) => void;
  onPrecheckComplete?: (result: PrecheckResult) => void;
}

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_PRECHECK: PrecheckResult = {
  is_complete: false,
  summary: "Hồ sơ thiếu 1 tài liệu bắt buộc",
  gaps: [
    {
      field: "PCCC",
      description: "Thiếu giấy chứng nhận thẩm duyệt PCCC theo quy định",
      law_ref: "NĐ 136/2020 Điều 13.2.b",
      severity: "error",
    },
    {
      field: "Bản vẽ thiết kế",
      description: "Bản vẽ chưa có chữ ký/đóng dấu của chủ đầu tư",
      severity: "warning",
    },
  ],
};

const MOCK_SUGGEST: FormSuggestResult = {
  suggestions: [
    {
      field: "applicant_name",
      value: "NGUYỄN VĂN A",
      confidence: 0.96,
      source: "Trích từ ảnh CCCD upload",
    },
    {
      field: "applicant_id_number",
      value: "012345678901",
      confidence: 0.98,
      source: "Trích từ ảnh CCCD upload",
    },
    {
      field: "applicant_address",
      value: "Số 12 Nguyễn Chí Thanh, Đống Đa, Hà Nội",
      confidence: 0.91,
      source: "Trích từ ảnh CCCD upload",
    },
  ],
};

// ---------------------------------------------------------------------------
// FormSuggestPanel
// ---------------------------------------------------------------------------

const FIELD_LABEL: Record<string, string> = {
  applicant_name: "Họ tên",
  applicant_id_number: "Số CCCD/CMND",
  applicant_phone: "Số điện thoại",
  applicant_address: "Địa chỉ",
  applicant_dob: "Ngày sinh",
};

interface FormSuggestPanelProps {
  tthcCode: string;
  formData: Record<string, unknown>;
  uploadedFileUrls?: string[];
  onAccept: (field: string, value: string) => void;
}

function FormSuggestPanel({
  tthcCode,
  formData,
  uploadedFileUrls,
  onAccept,
}: FormSuggestPanelProps) {
  const MOCK = process.env.NEXT_PUBLIC_MOCK_ASSISTANT === "true";

  // Track accepted/dismissed suggestions per field
  const [dismissed, setDismissed] = React.useState<Set<string>>(new Set());
  const [accepted, setAccepted] = React.useState<Set<string>>(new Set());

  const mutation = useMutation<FormSuggestResult, Error>({
    mutationFn: async () => {
      if (MOCK) {
        await new Promise((r) => setTimeout(r, 1000));
        return MOCK_SUGGEST;
      }
      const res = await fetch("/api/assistant/form-suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tthc_code: tthcCode,
          partial_form: formData,
          uploaded_doc_urls: uploadedFileUrls ?? [],
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      return res.json() as Promise<FormSuggestResult>;
    },
  });

  function handleAccept(s: FormSuggestion) {
    onAccept(s.field, s.value);
    setAccepted((prev) => new Set([...prev, s.field]));
  }

  function handleDismiss(field: string) {
    setDismissed((prev) => new Set([...prev, field]));
  }

  // Idle state — show trigger button
  if (mutation.status === "idle") {
    return (
      <button
        type="button"
        onClick={() => mutation.mutate()}
        className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed py-2.5 text-sm font-medium transition-colors hover:bg-[var(--bg-subtle)]"
        style={{
          borderColor: "oklch(0.65 0.15 280 / 0.4)",
          color: "var(--text-secondary)",
        }}
      >
        <Sparkles size={14} className="text-purple-500" />
        AI gợi ý điền các trường còn lại
      </button>
    );
  }

  // Loading
  if (mutation.status === "pending") {
    return (
      <div
        className="flex items-center gap-3 rounded-xl border px-4 py-3"
        style={{
          background: "var(--gradient-qwen-soft)",
          borderColor: "oklch(0.65 0.15 280 / 0.25)",
        }}
      >
        <Loader2 size={14} className="animate-spin text-purple-600 shrink-0" />
        <p className="text-sm text-[var(--text-secondary)]">
          AI đang phân tích tài liệu...
        </p>
      </div>
    );
  }

  // Error
  if (mutation.status === "error") {
    return (
      <div
        className="rounded-xl border border-[var(--accent-destructive)]/30 bg-[var(--accent-destructive)]/5 px-4 py-3"
        role="alert"
      >
        <p className="text-sm text-[var(--accent-destructive)]">
          Lỗi gợi ý: {mutation.error.message}
        </p>
        <button
          type="button"
          onClick={() => mutation.mutate()}
          className="mt-1 text-xs text-[var(--accent-primary)] hover:underline"
        >
          Thử lại
        </button>
      </div>
    );
  }

  // Success — show suggestions
  const suggestions = (mutation.data?.suggestions ?? []).filter(
    (s) => !dismissed.has(s.field),
  );

  if (suggestions.length === 0) {
    return (
      <div
        className="flex items-center gap-2 rounded-xl border px-4 py-3"
        style={{
          background: "var(--gradient-qwen-soft)",
          borderColor: "oklch(0.65 0.15 280 / 0.2)",
        }}
      >
        <CheckCircle2 size={14} className="text-[var(--accent-success)] shrink-0" />
        <p className="text-sm text-[var(--text-secondary)]">
          Tất cả gợi ý đã được xử lý.
        </p>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border overflow-hidden"
      style={{ borderColor: "oklch(0.65 0.15 280 / 0.25)" }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4 py-2.5"
        style={{ background: "var(--gradient-qwen-soft)" }}
      >
        <Sparkles size={13} className="text-purple-600 shrink-0" />
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          AI gợi ý điền trường
        </span>
        <span
          className="ml-auto text-xs"
          style={{ color: "var(--text-muted)" }}
        >
          {suggestions.length} gợi ý
        </span>
      </div>

      {/* Suggestion rows */}
      <div className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {suggestions.map((s) => {
          const isAccepted = accepted.has(s.field);
          const label = FIELD_LABEL[s.field] ?? s.field;

          return (
            <div key={s.field} className="px-4 py-3">
              <div className="flex items-start gap-2">
                <Sparkles
                  size={12}
                  className={cn(
                    "mt-0.5 shrink-0",
                    isAccepted ? "text-[var(--accent-success)]" : "text-purple-500",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-[var(--text-primary)]">
                    {label}:{" "}
                    <span className="font-normal text-[var(--text-secondary)]">
                      {s.value}
                    </span>
                  </p>
                  <p
                    className="mt-0.5 text-[10px] leading-tight"
                    style={{ color: "var(--text-muted)" }}
                  >
                    {s.source} · độ tin cậy{" "}
                    {Math.round(s.confidence * 100)}%
                  </p>
                </div>
              </div>

              {!isAccepted && (
                <div className="mt-2 flex gap-2">
                  <button
                    type="button"
                    onClick={() => handleAccept(s)}
                    className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
                    style={{ background: "var(--gradient-qwen)" }}
                    aria-label={`Chấp nhận gợi ý cho trường ${label}`}
                  >
                    <CheckCheck size={11} />
                    Chấp nhận
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDismiss(s.field)}
                    className="flex items-center gap-1 rounded-lg border border-[var(--border-default)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] transition-colors"
                    aria-label={`Bỏ qua gợi ý cho trường ${label}`}
                  >
                    <X size={11} />
                    Bỏ qua
                  </button>
                </div>
              )}

              {isAccepted && (
                <div className="mt-1.5 flex items-center gap-1 text-[10px] text-[var(--accent-success)]">
                  <CheckCircle2 size={10} />
                  Đã chấp nhận
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AIReviewPanel (main export — precheck + optional form-suggest)
// ---------------------------------------------------------------------------

export function AIReviewPanel({
  tthcCode,
  formData,
  uploadedFileUrls,
  onAcceptSuggestion,
  onPrecheckComplete,
}: AIReviewPanelProps) {
  const [status, setStatus] = React.useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [result, setResult] = React.useState<PrecheckResult | null>(null);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  const MOCK = process.env.NEXT_PUBLIC_MOCK_ASSISTANT === "true";

  async function runPrecheck() {
    setStatus("loading");
    try {
      let data: PrecheckResult;
      if (MOCK) {
        await new Promise((r) => setTimeout(r, 1200));
        data = MOCK_PRECHECK;
      } else {
        const res = await fetch("/api/assistant/precheck", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            tthc_code: tthcCode,
            form_data: formData,
            uploaded_doc_urls: uploadedFileUrls ?? [],
          }),
        });
        if (!res.ok) throw new Error(await res.text());
        const raw = (await res.json()) as {
          score: number;
          gaps: string[];
          missing_docs: string[];
          suggestions: string[];
        };
        const gapItems: GapItem[] = [
          ...(raw.missing_docs ?? []).map((d) => ({
            field: "Giấy tờ",
            description: d,
            severity: "error" as const,
          })),
          ...(raw.gaps ?? []).map((g) => ({
            field: "Nội dung",
            description: g,
            severity: "warning" as const,
          })),
        ];
        const score = raw.score ?? 0;
        data = {
          is_complete: gapItems.length === 0 && score >= 0.9,
          summary:
            gapItems.length === 0
              ? "Hồ sơ đầy đủ, sẵn sàng nộp."
              : `Điểm tuân thủ ${Math.round(score * 100)}%. Còn ${gapItems.length} vấn đề cần xử lý.`,
          gaps: gapItems,
        };
      }
      setResult(data);
      setStatus("done");
      onPrecheckComplete?.(data);
    } catch (err) {
      setErrorMsg((err as Error).message);
      setStatus("error");
    }
  }

  if (status === "idle") {
    return (
      <div className="space-y-3">
        {/* Form-suggest (available before precheck if we have files) */}
        {onAcceptSuggestion && (
          <FormSuggestPanel
            tthcCode={tthcCode}
            formData={formData}
            uploadedFileUrls={uploadedFileUrls}
            onAccept={onAcceptSuggestion}
          />
        )}

        <button
          type="button"
          onClick={runPrecheck}
          className="w-full rounded-xl py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          style={{ background: "var(--gradient-qwen)" }}
        >
          <span className="flex items-center justify-center gap-2">
            <Sparkles size={16} />
            AI kiểm tra hồ sơ
          </span>
        </button>
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div
        className="flex items-center gap-3 rounded-xl border px-4 py-3"
        style={{
          background: "var(--gradient-qwen-soft)",
          borderColor: "oklch(0.65 0.15 280 / 0.25)",
        }}
      >
        <Loader2 size={16} className="animate-spin text-purple-600 shrink-0" />
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            AI đang kiểm tra hồ sơ...
          </p>
          <p className="text-xs text-[var(--text-muted)]">Sử dụng Qwen3-Max</p>
        </div>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div
        className="rounded-xl border border-[var(--accent-destructive)]/30 bg-[var(--accent-destructive)]/5 px-4 py-3"
        role="alert"
      >
        <p className="text-sm text-[var(--accent-destructive)]">
          Lỗi kiểm tra hồ sơ: {errorMsg}
        </p>
        <button
          type="button"
          onClick={runPrecheck}
          className="mt-1 text-xs text-[var(--accent-primary)] hover:underline"
        >
          Thử lại
        </button>
      </div>
    );
  }

  if (!result) return null;

  return (
    <div className="space-y-3">
      {/* Form-suggest (show above results if available) */}
      {onAcceptSuggestion && (
        <FormSuggestPanel
          tthcCode={tthcCode}
          formData={formData}
          uploadedFileUrls={uploadedFileUrls}
          onAccept={onAcceptSuggestion}
        />
      )}

      {/* Precheck results */}
      <div
        className="rounded-xl border overflow-hidden"
        style={{ borderColor: "oklch(0.65 0.15 280 / 0.25)" }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-2 px-4 py-2.5"
          style={{ background: "var(--gradient-qwen-soft)" }}
        >
          <Sparkles size={14} className="text-purple-600 shrink-0" />
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            Kết quả kiểm tra AI
          </span>
          {result.is_complete ? (
            <span className="ml-auto flex items-center gap-1 text-xs text-[var(--accent-success)]">
              <CheckCircle2 size={12} />
              Đủ điều kiện
            </span>
          ) : (
            <span className="ml-auto text-xs text-[var(--accent-warning)]">
              {result.gaps.length} vấn đề
            </span>
          )}
        </div>

        {/* Summary */}
        <div className="px-4 py-2 bg-[var(--bg-surface)]">
          <p className="text-sm text-[var(--text-secondary)]">{result.summary}</p>
        </div>

        {/* Gaps */}
        {result.gaps.length > 0 && (
          <div className="divide-y divide-[var(--border-subtle)] bg-[var(--bg-surface)]">
            {result.gaps.map((gap, i) => (
              <div key={i} className="px-4 py-3 flex items-start gap-3">
                <AlertTriangle
                  size={14}
                  className={cn(
                    "mt-0.5 shrink-0",
                    gap.severity === "error"
                      ? "text-[var(--accent-destructive)]"
                      : gap.severity === "warning"
                        ? "text-[var(--accent-warning)]"
                        : "text-[var(--text-muted)]",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-[var(--text-primary)]">
                    {gap.field}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                    {gap.description}
                  </p>
                  {gap.law_ref && (
                    <p className="mt-0.5 text-[10px] text-purple-600 font-mono">
                      {gap.law_ref}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
