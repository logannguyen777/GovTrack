"use client";

import { use, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { apiClient } from "@/lib/api";
import type {
  CaseCreate,
  CaseResponse,
  BundleCreate,
  BundleResponse,
} from "@/lib/types";
import {
  Upload,
  FileText,
  X,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

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

interface UploadFile {
  file: File;
  id: string;
}

interface FormErrors {
  applicant_name?: string;
  applicant_id_number?: string;
}

function FieldHelper({ text }: { text: string }) {
  return (
    <p className="mt-1 text-xs text-[var(--text-muted)]">{text}</p>
  );
}

function FieldError({ message }: { message: string }) {
  return (
    <p role="alert" className="mt-1 text-xs font-medium text-[var(--accent-destructive)]">
      {message}
    </p>
  );
}

export default function SubmitWizard({
  params,
}: {
  params: Promise<{ tthc_code: string }>;
}) {
  const { tthc_code } = use(params);
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [errors, setErrors] = useState<FormErrors>({});
  const [confirmed, setConfirmed] = useState(false);
  const [form, setForm] = useState({
    tthc_code: decodeURIComponent(tthc_code),
    department_id: "DEPT-QLDT",
    applicant_name: "",
    applicant_id_number: "",
    applicant_phone: "",
    applicant_address: "",
    notes: "",
  });

  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [
      ...prev,
      ...accepted.map((f) => ({ file: f, id: crypto.randomUUID() })),
    ]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".jpg", ".jpeg", ".png"],
    },
  });

  function validateStep1(): FormErrors {
    const newErrors: FormErrors = {};
    if (!form.applicant_name.trim()) {
      newErrors.applicant_name = "Vui lòng nhập họ và tên";
    }
    if (!form.applicant_id_number.trim()) {
      newErrors.applicant_id_number = "Vui lòng nhập số CCCD";
    } else if (!/^\d{12}$/.test(form.applicant_id_number.trim())) {
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
      setErrors({});
    }
    setStep(step + 1);
  }

  function canNext(): boolean {
    if (step === 0) return Boolean(form.tthc_code);
    return true;
  }

  async function handleSubmit() {
    if (!confirmed) return;
    setSubmitting(true);
    try {
      // Create case
      const caseBody: CaseCreate = {
        tthc_code: form.tthc_code,
        department_id: form.department_id,
        applicant_name: form.applicant_name,
        applicant_id_number: form.applicant_id_number,
        applicant_phone: form.applicant_phone,
        applicant_address: form.applicant_address,
        notes: form.notes,
      };
      const caseRes = await apiClient.post<CaseResponse>(
        "/api/cases",
        caseBody,
      );

      // Upload files if any
      if (files.length > 0) {
        const bundleBody: BundleCreate = {
          files: files.map((f) => ({
            filename: f.file.name,
            content_type: f.file.type || "application/octet-stream",
            size_bytes: f.file.size,
          })),
        };
        const bundleRes = await apiClient.post<BundleResponse>(
          `/api/cases/${caseRes.case_id}/bundles`,
          bundleBody,
        );

        for (const url of bundleRes.upload_urls) {
          const match = files.find((f) => f.file.name === url.filename);
          if (match) {
            await fetch(url.signed_url, {
              method: "PUT",
              body: match.file,
              headers: { "Content-Type": match.file.type },
            });
          }
        }
      }

      // Finalize
      await apiClient.post(`/api/cases/${caseRes.case_id}/finalize`);

      toast.success(`Hồ sơ đã nộp thành công! Mã: ${caseRes.code}`);
      router.push(`/track/${caseRes.code}`);
    } catch {
      toast.error("Có lỗi khi nộp hồ sơ. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  const currentStepMeta = STEPS[step];

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">
        Nộp hồ sơ trực tuyến
      </h1>

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
              {i < step ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                i + 1
              )}
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
        {/* Step description */}
        <p className="mb-4 text-sm text-[var(--text-secondary)] border-b border-[var(--border-subtle)] pb-4">
          {currentStepMeta.description}
        </p>

        {step === 0 && (
          <div>
            <h2 className="text-lg font-semibold">Thủ tục hành chính</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Mã thủ tục đã được chọn tự động
            </p>
            <div className="mt-4 rounded-md border border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/5 p-4">
              <p className="font-mono text-sm">{form.tthc_code}</p>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Thông tin công dân</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label
                  htmlFor="applicant_name"
                  className="text-sm font-medium"
                >
                  Họ và tên <span className="text-[var(--accent-destructive)]">*</span>
                </label>
                <input
                  id="applicant_name"
                  value={form.applicant_name}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, applicant_name: e.target.value }));
                    if (errors.applicant_name) {
                      setErrors((prev) => ({ ...prev, applicant_name: undefined }));
                    }
                  }}
                  aria-describedby="applicant_name_helper applicant_name_error"
                  aria-invalid={Boolean(errors.applicant_name)}
                  className={`mt-1 w-full rounded-md border bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[var(--accent-primary)] ${
                    errors.applicant_name
                      ? "border-[var(--accent-destructive)] focus:border-[var(--accent-destructive)]"
                      : "border-[var(--border-default)] focus:border-[var(--accent-primary)]"
                  }`}
                />
                <span id="applicant_name_helper">
                  <FieldHelper text="Nhập đầy đủ họ tên như trong CCCD (ví dụ: Nguyễn Văn An)" />
                </span>
                {errors.applicant_name && (
                  <span id="applicant_name_error">
                    <FieldError message={errors.applicant_name} />
                  </span>
                )}
              </div>

              <div>
                <label
                  htmlFor="applicant_id_number"
                  className="text-sm font-medium"
                >
                  Số CCCD <span className="text-[var(--accent-destructive)]">*</span>
                </label>
                <input
                  id="applicant_id_number"
                  value={form.applicant_id_number}
                  onChange={(e) => {
                    setForm((f) => ({
                      ...f,
                      applicant_id_number: e.target.value,
                    }));
                    if (errors.applicant_id_number) {
                      setErrors((prev) => ({
                        ...prev,
                        applicant_id_number: undefined,
                      }));
                    }
                  }}
                  inputMode="numeric"
                  maxLength={12}
                  aria-describedby="applicant_id_helper applicant_id_error"
                  aria-invalid={Boolean(errors.applicant_id_number)}
                  className={`mt-1 w-full rounded-md border bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[var(--accent-primary)] ${
                    errors.applicant_id_number
                      ? "border-[var(--accent-destructive)] focus:border-[var(--accent-destructive)]"
                      : "border-[var(--border-default)] focus:border-[var(--accent-primary)]"
                  }`}
                />
                <span id="applicant_id_helper">
                  <FieldHelper text="Số căn cước công dân 12 số ở mặt trước thẻ" />
                </span>
                {errors.applicant_id_number && (
                  <span id="applicant_id_error">
                    <FieldError message={errors.applicant_id_number} />
                  </span>
                )}
              </div>

              <div>
                <label
                  htmlFor="applicant_phone"
                  className="text-sm font-medium"
                >
                  Số điện thoại
                </label>
                <input
                  id="applicant_phone"
                  value={form.applicant_phone}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      applicant_phone: e.target.value,
                    }))
                  }
                  inputMode="tel"
                  aria-describedby="applicant_phone_helper"
                  className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
                />
                <span id="applicant_phone_helper">
                  <FieldHelper text="Để nhận thông báo về kết quả xử lý hồ sơ" />
                </span>
              </div>

              <div>
                <label
                  htmlFor="applicant_address"
                  className="text-sm font-medium"
                >
                  Địa chỉ
                </label>
                <input
                  id="applicant_address"
                  value={form.applicant_address}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      applicant_address: e.target.value,
                    }))
                  }
                  aria-describedby="applicant_address_helper"
                  className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
                />
                <span id="applicant_address_helper">
                  <FieldHelper text="Địa chỉ thường trú hoặc liên lạc" />
                </span>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="text-lg font-semibold">Tải tài liệu</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Tải lên các tài liệu cần thiết cho thủ tục. Chấp nhận định dạng
              PDF, JPG, PNG.
            </p>
            <div
              {...getRootProps()}
              className={`mt-4 cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                isDragActive
                  ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5"
                  : "border-[var(--border-default)] hover:border-[var(--accent-primary)]/50"
              }`}
              role="button"
              aria-label="Vùng tải lên tài liệu"
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto h-8 w-8 text-[var(--text-muted)]" />
              <p className="mt-2 text-sm font-medium text-[var(--text-secondary)]">
                Kéo thả hoặc bấm để chọn file
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Hỗ trợ: PDF, JPG, PNG — tối đa 20MB mỗi file
              </p>
            </div>
            {files.length > 0 && (
              <div className="mt-3 space-y-1">
                {files.map((f) => (
                  <div
                    key={f.id}
                    className="flex items-center justify-between rounded-md border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
                  >
                    <div className="flex items-center gap-2">
                      <FileText className="h-3 w-3 text-[var(--text-muted)]" />
                      <span className="truncate max-w-xs">{f.file.name}</span>
                    </div>
                    <button
                      onClick={() =>
                        setFiles((prev) => prev.filter((x) => x.id !== f.id))
                      }
                      aria-label={`Xóa file ${f.file.name}`}
                    >
                      <X className="h-3 w-3 text-[var(--text-muted)]" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 className="text-lg font-semibold">Xem lại & nộp hồ sơ</h2>
            <div className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
                <span className="text-[var(--text-muted)]">Thủ tục</span>
                <span className="font-mono">{form.tthc_code}</span>
              </div>
              <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
                <span className="text-[var(--text-muted)]">Họ tên</span>
                <span>{form.applicant_name}</span>
              </div>
              <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
                <span className="text-[var(--text-muted)]">CCCD</span>
                <span className="font-mono">{form.applicant_id_number}</span>
              </div>
              {form.applicant_phone && (
                <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
                  <span className="text-[var(--text-muted)]">SĐT</span>
                  <span>{form.applicant_phone}</span>
                </div>
              )}
              {form.applicant_address && (
                <div className="flex justify-between border-b border-[var(--border-subtle)] pb-2">
                  <span className="text-[var(--text-muted)]">Địa chỉ</span>
                  <span className="text-right max-w-xs">
                    {form.applicant_address}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[var(--text-muted)]">Tài liệu</span>
                <span>{files.length} file</span>
              </div>
            </div>

            {/* Confirmation checkbox */}
            <label className="mt-6 flex cursor-pointer items-start gap-3 rounded-md border border-[var(--border-default)] bg-[var(--bg-subtle)] p-4">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent-primary)] cursor-pointer"
                aria-required="true"
              />
              <span className="text-sm text-[var(--text-secondary)] leading-relaxed">
                Tôi xác nhận thông tin trên là chính xác và chịu trách nhiệm
                về tính trung thực của hồ sơ
              </span>
            </label>
          </div>
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
