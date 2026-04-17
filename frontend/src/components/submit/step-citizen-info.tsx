"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ShieldCheck, X, CheckCircle2, Smartphone } from "lucide-react";
import { SmartFieldHelper } from "./smart-field-helper";
import { useSubmitFormStore } from "@/lib/stores/submit-form-store";
import { apiClient } from "@/lib/api";

export interface CitizenInfoData {
  applicant_name: string;
  applicant_id_number: string;
  applicant_phone: string;
  applicant_address: string;
}

// ---------------------------------------------------------------------------
// VNeID Modal — fake QR + animated Face ID flow
// ---------------------------------------------------------------------------

type VNeIDStep = "qr" | "scanning" | "faceid" | "success";

interface DemoSampleResponse {
  tthc_code: string;
  applicant: {
    applicant_name: string;
    applicant_id_number: string;
    applicant_phone: string;
    applicant_address: string;
  };
  sample_files: Array<{
    filename: string;
    url: string;
    mime_type: string;
    size_bytes?: number;
  }>;
  notes: string;
}

// Placeholder QR SVG — renders a realistic-looking QR frame
function QRPlaceholder() {
  return (
    <svg
      width="160"
      height="160"
      viewBox="0 0 160 160"
      className="mx-auto rounded-lg border border-[var(--border-default)] bg-white p-3"
      aria-label="Mã QR VNeID"
    >
      {/* Finder patterns */}
      <rect x="10" y="10" width="40" height="40" rx="3" fill="none" stroke="#111" strokeWidth="4" />
      <rect x="20" y="20" width="20" height="20" rx="1" fill="#111" />
      <rect x="110" y="10" width="40" height="40" rx="3" fill="none" stroke="#111" strokeWidth="4" />
      <rect x="120" y="20" width="20" height="20" rx="1" fill="#111" />
      <rect x="10" y="110" width="40" height="40" rx="3" fill="none" stroke="#111" strokeWidth="4" />
      <rect x="20" y="120" width="20" height="20" rx="1" fill="#111" />
      {/* Data modules (mock pattern) */}
      {[60,65,70,75,80,85,90,95,100,105].map((x) =>
        [10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100,105,110,115,120,125,130,135,140,145].map((y) =>
          Math.sin(x * 0.3 + y * 0.7) > 0.3 ? (
            <rect key={`${x}-${y}`} x={x} y={y} width="4" height="4" fill="#111" />
          ) : null
        )
      )}
      {/* VNeID logo text area */}
      <rect x="62" y="62" width="36" height="36" fill="white" />
      <text x="80" y="82" textAnchor="middle" dominantBaseline="middle" fontSize="8" fontWeight="bold" fill="#1d4ed8">VNeID</text>
    </svg>
  );
}

interface VNeIDModalProps {
  tthcCode: string;
  onSuccess: (data: DemoSampleResponse) => void;
  onClose: () => void;
}

function VNeIDModal({ tthcCode, onSuccess, onClose }: VNeIDModalProps) {
  const [vStep, setVStep] = React.useState<VNeIDStep>("qr");

  React.useEffect(() => {
    // Auto-advance: QR → scanning → faceid → success, each ~700ms
    let t1: ReturnType<typeof setTimeout>;
    let t2: ReturnType<typeof setTimeout>;
    let t3: ReturnType<typeof setTimeout>;
    let t4: ReturnType<typeof setTimeout>;

    t1 = setTimeout(() => setVStep("scanning"), 800);
    t2 = setTimeout(() => setVStep("faceid"), 1600);
    t3 = setTimeout(() => setVStep("success"), 2400);
    t4 = setTimeout(async () => {
      try {
        const sample = await apiClient.get<DemoSampleResponse>(
          `/api/public/demo-samples/${encodeURIComponent(tthcCode)}`,
        );
        onSuccess(sample);
      } catch {
        onSuccess({
          tthc_code: tthcCode,
          applicant: {
            applicant_name: "Nguyễn Văn An",
            applicant_id_number: "036092001234",
            applicant_phone: "0912345678",
            applicant_address: "Số 1 Lê Duẩn, Hà Nội",
          },
          sample_files: [],
          notes: "",
        });
      }
    }, 2800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
    };
  }, [tthcCode, onSuccess]);

  const stepLabels: Record<VNeIDStep, string> = {
    qr: "Quét mã QR bằng app VNeID",
    scanning: "Đang quét...",
    faceid: "Đang xác thực Face ID...",
    success: "Xác thực thành công!",
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Đăng nhập VNeID"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0, y: 16 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.92, opacity: 0, y: 16 }}
        transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
        className="relative w-full max-w-sm rounded-2xl bg-[var(--bg-surface)] p-6 shadow-2xl"
      >
        {/* Header */}
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Smartphone size={16} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-[var(--text-primary)]">VNeID</p>
              <p className="text-[10px] text-[var(--text-muted)]">Căn cước công dân điện tử</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="rounded-lg p-1.5 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* QR or success */}
        <AnimatePresence mode="wait">
          {vStep !== "success" ? (
            <motion.div
              key="qr"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center"
            >
              <div className="relative mx-auto w-fit">
                <QRPlaceholder />
                {vStep === "scanning" && (
                  <motion.div
                    className="absolute inset-0 rounded-lg border-2 border-blue-500"
                    animate={{ opacity: [1, 0.4, 1] }}
                    transition={{ duration: 0.6, repeat: Infinity }}
                  />
                )}
                {vStep === "faceid" && (
                  <div className="absolute inset-0 flex items-center justify-center rounded-lg bg-blue-900/80 backdrop-blur-sm">
                    <div className="text-center text-white">
                      <motion.div
                        animate={{ scale: [1, 1.15, 1] }}
                        transition={{ duration: 0.8, repeat: Infinity }}
                        className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-blue-500"
                      >
                        <ShieldCheck size={24} />
                      </motion.div>
                      <p className="text-xs font-medium">Face ID</p>
                    </div>
                  </div>
                )}
              </div>

              <p className="mt-4 text-sm font-medium text-[var(--text-primary)]">
                {stepLabels[vStep]}
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Mở app VNeID → Quét mã → Xác nhận
              </p>

              {/* Step dots */}
              <div className="mt-4 flex items-center justify-center gap-1.5">
                {(["qr", "scanning", "faceid"] as VNeIDStep[]).map((s) => (
                  <div
                    key={s}
                    className={`h-1.5 rounded-full transition-all duration-300 ${
                      vStep === s ? "w-4 bg-blue-500" : "w-1.5 bg-[var(--border-default)]"
                    }`}
                  />
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="success"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
              className="text-center"
            >
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent-success)]/15">
                <CheckCircle2 size={36} className="text-[var(--accent-success)]" />
              </div>
              <p className="mt-3 text-base font-bold text-[var(--text-primary)]">
                Xác thực thành công!
              </p>
              <p className="mt-1 text-xs text-[var(--text-secondary)]">
                Đang điền thông tin từ căn cước công dân...
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        <p className="mt-5 text-center text-[10px] text-[var(--text-muted)]">
          Được bảo vệ bởi Bộ Công an · Mã hóa đầu cuối
        </p>
      </motion.div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// LabelledField
// ---------------------------------------------------------------------------

interface LabelledFieldProps {
  id: string;
  label: string;
  required?: boolean;
  helperId?: string;
  errorId?: string;
  error?: string;
  helper?: string;
  isAIFilled?: boolean;
  tthcCode: string;
  fieldName: string;
  children: React.ReactElement<{
    id: string;
    "aria-describedby"?: string;
    "aria-invalid"?: boolean;
  }>;
}

function LabelledField({
  id,
  label,
  required,
  helperId,
  errorId,
  error,
  helper,
  isAIFilled,
  tthcCode,
  fieldName,
  children,
}: LabelledFieldProps) {
  const describedBy = [helperId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div>
      <div className="flex items-center gap-1">
        <label htmlFor={id} className="text-sm font-medium text-[var(--text-primary)]">
          {label}
          {required && (
            <span className="ml-0.5 text-[var(--accent-destructive)]"> *</span>
          )}
        </label>
        {isAIFilled && (
          <span
            title="Do AI điền — bấm để sửa"
            className="inline-flex items-center gap-0.5 rounded-full bg-purple-100 px-1.5 py-0.5 text-[9px] font-medium text-purple-700"
          >
            <Sparkles size={9} />
            AI
          </span>
        )}
        <SmartFieldHelper tthcCode={tthcCode} fieldName={fieldName} />
      </div>
      {React.cloneElement(children, {
        id,
        "aria-describedby": describedBy,
        "aria-invalid": Boolean(error),
      })}
      {helper && !error && (
        <p id={helperId} className="mt-1 text-xs text-[var(--text-muted)]">
          {helper}
        </p>
      )}
      {error && (
        <p id={errorId} role="alert" className="mt-1 text-xs font-medium text-[var(--accent-destructive)]">
          {error}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// StepCitizenInfo
// ---------------------------------------------------------------------------

interface StepCitizenInfoProps {
  tthcCode: string;
  data: CitizenInfoData;
  errors: Partial<Record<keyof CitizenInfoData, string>>;
  onChange: (field: keyof CitizenInfoData, value: string) => void;
}

export function StepCitizenInfo({
  tthcCode,
  data,
  errors,
  onChange,
}: StepCitizenInfoProps) {
  const aiFilledFields = useSubmitFormStore((s) => s.aiFilledFields);
  const setField = useSubmitFormStore((s) => s.setField);
  const aiFilledSet = React.useMemo(
    () => new Set(aiFilledFields),
    [aiFilledFields],
  );

  const [showVNeID, setShowVNeID] = React.useState(false);
  const [vneIDVerified, setVneIDVerified] = React.useState(false);

  function handleVNeIDSuccess(sample: DemoSampleResponse) {
    // Populate all form fields via the store (marks as AI-filled)
    setField("applicant_name", sample.applicant.applicant_name, true);
    setField("applicant_id_number", sample.applicant.applicant_id_number, true);
    setField("applicant_phone", sample.applicant.applicant_phone, true);
    setField("applicant_address", sample.applicant.applicant_address, true);
    setVneIDVerified(true);
    setShowVNeID(false);
  }

  const inputClass = (field: keyof CitizenInfoData) =>
    `mt-1 w-full rounded-md border bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-[var(--accent-primary)] ${
      errors[field]
        ? "border-[var(--accent-destructive)] focus:border-[var(--accent-destructive)]"
        : "border-[var(--border-default)] focus:border-[var(--accent-primary)]"
    }`;

  return (
    <>
      {/* VNeID modal overlay */}
      <AnimatePresence>
        {showVNeID && (
          <VNeIDModal
            tthcCode={tthcCode}
            onSuccess={handleVNeIDSuccess}
            onClose={() => setShowVNeID(false)}
          />
        )}
      </AnimatePresence>

      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">
            Thông tin công dân
          </h2>

          {/* VNeID autofill button / verified badge */}
          {vneIDVerified ? (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1.5 rounded-full border border-[var(--accent-success)]/40 bg-[var(--accent-success)]/10 px-3 py-1.5 text-xs font-medium text-[var(--accent-success)]"
            >
              <ShieldCheck size={13} />
              Đã xác thực VNeID
            </motion.div>
          ) : (
            <button
              type="button"
              onClick={() => setShowVNeID(true)}
              className="flex items-center gap-1.5 rounded-lg border border-blue-300 bg-gradient-to-br from-blue-50 to-indigo-50 px-3 py-1.5 text-xs font-semibold text-blue-700 shadow-sm transition-all hover:shadow-md hover:-translate-y-0.5 dark:border-blue-700 dark:from-blue-950/40 dark:to-indigo-950/40 dark:text-blue-300"
            >
              <Smartphone size={13} />
              Đăng nhập VNeID để tự điền
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <LabelledField
            id="applicant_name"
            label="Họ và tên"
            required
            helperId="applicant_name_helper"
            errorId="applicant_name_error"
            error={errors.applicant_name}
            helper="Nhập đầy đủ họ tên như trong CCCD"
            isAIFilled={aiFilledSet.has("applicant_name")}
            tthcCode={tthcCode}
            fieldName="applicant_name"
          >
            <input
              type="text"
              value={data.applicant_name}
              onChange={(e) => {
                onChange("applicant_name", e.target.value);
              }}
              className={inputClass("applicant_name")}
            />
          </LabelledField>

          <LabelledField
            id="applicant_id_number"
            label="Số CCCD"
            required
            helperId="applicant_id_helper"
            errorId="applicant_id_error"
            error={errors.applicant_id_number}
            helper="Số căn cước công dân 12 số mặt trước thẻ"
            isAIFilled={aiFilledSet.has("applicant_id_number")}
            tthcCode={tthcCode}
            fieldName="applicant_id_number"
          >
            <input
              type="text"
              inputMode="numeric"
              maxLength={12}
              value={data.applicant_id_number}
              onChange={(e) => onChange("applicant_id_number", e.target.value)}
              className={inputClass("applicant_id_number")}
            />
          </LabelledField>

          <LabelledField
            id="applicant_phone"
            label="Số điện thoại"
            helperId="applicant_phone_helper"
            error={errors.applicant_phone}
            helper="Để nhận thông báo về kết quả xử lý hồ sơ"
            isAIFilled={aiFilledSet.has("applicant_phone")}
            tthcCode={tthcCode}
            fieldName="applicant_phone"
          >
            <input
              type="tel"
              inputMode="tel"
              value={data.applicant_phone}
              onChange={(e) => onChange("applicant_phone", e.target.value)}
              className={inputClass("applicant_phone")}
            />
          </LabelledField>

          <LabelledField
            id="applicant_address"
            label="Địa chỉ"
            helperId="applicant_address_helper"
            error={errors.applicant_address}
            helper="Địa chỉ thường trú hoặc liên lạc"
            isAIFilled={aiFilledSet.has("applicant_address")}
            tthcCode={tthcCode}
            fieldName="applicant_address"
          >
            <input
              type="text"
              value={data.applicant_address}
              onChange={(e) => onChange("applicant_address", e.target.value)}
              className={inputClass("applicant_address")}
            />
          </LabelledField>
        </div>
      </div>
    </>
  );
}
