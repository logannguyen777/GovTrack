"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useCreateCase } from "@/hooks/use-cases";
import { useAgentTrace } from "@/hooks/use-agents";
import { useSearchTTHC } from "@/hooks/use-search";
import { apiClient } from "@/lib/api";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import type {
  BundleCreate,
  BundleResponse,
  AgentRunRequest,
} from "@/lib/types";
import {
  Upload,
  FileText,
  X,
  CheckCircle,
  Loader2,
  ArrowRight,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

interface UploadedFile {
  file: File;
  id: string;
  status: "pending" | "uploading" | "done" | "error";
}

interface OcrPanel {
  docId: string;
  filename: string;
  ossKey: string;
  ready: boolean;
  text: string;
}

type Phase = "idle" | "uploading" | "processing" | "done" | "error";

export default function IntakeUI() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [tthcQuery, setTthcQuery] = useState("");
  const [selectedTTHC, setSelectedTTHC] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [activeCaseCode, setActiveCaseCode] = useState<string | null>(null);
  const [ocrPanels, setOcrPanels] = useState<OcrPanel[]>([]);
  const [form, setForm] = useState({
    applicant_name: "",
    applicant_id_number: "",
    applicant_phone: "",
    applicant_address: "",
    department_id: "DEPT-QLDT",
    notes: "",
  });

  const { data: tthcResults } = useSearchTTHC(tthcQuery);
  const createCase = useCreateCase();

  // Poll agent trace when we have an active case
  const { data: trace } = useAgentTrace(activeCaseId ?? "");

  // Compute compliance score from trace
  const complianceScore = (() => {
    if (!trace) return 0;
    const completed = trace.steps.filter(
      (s) => s.status === "completed",
    ).length;
    const total = Math.max(trace.steps.length, 1);
    if (trace.status === "completed") return 100;
    return Math.round((completed / total) * 100);
  })();

  // Check if pipeline is done
  if (
    trace?.status === "completed" &&
    phase === "processing"
  ) {
    setPhase("done");
    toast.success("Pipeline hoàn thành!");
  }

  const onDrop = useCallback((accepted: File[]) => {
    const newFiles = accepted.map((f) => ({
      file: f,
      id: crypto.randomUUID(),
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".jpg", ".jpeg", ".png"],
    },
    disabled: phase !== "idle",
  });

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  async function handleSubmit() {
    if (!selectedTTHC || !form.applicant_name || !form.applicant_id_number) {
      toast.error("Vui lòng điền đầy đủ thông tin bắt buộc");
      return;
    }

    setPhase("uploading");

    try {
      // Step 1: Create case
      const caseRes = await createCase.mutateAsync({
        tthc_code: selectedTTHC,
        department_id: form.department_id,
        applicant_name: form.applicant_name,
        applicant_id_number: form.applicant_id_number,
        applicant_phone: form.applicant_phone,
        applicant_address: form.applicant_address,
        notes: form.notes,
      });

      setActiveCaseId(caseRes.case_id);
      setActiveCaseCode(caseRes.code);

      // Step 2: Create bundle + upload files
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

        // Set up OCR panels
        setOcrPanels(
          bundleRes.upload_urls.map((u) => ({
            docId: u.oss_key.split("/").pop() || u.filename,
            filename: u.filename,
            ossKey: u.oss_key,
            ready: false,
            text: "Đang trích xuất...",
          })),
        );

        // Upload files to presigned URLs
        for (const uploadUrl of bundleRes.upload_urls) {
          const fileToUpload = files.find(
            (f) => f.file.name === uploadUrl.filename,
          );
          if (fileToUpload) {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === fileToUpload.id
                  ? { ...f, status: "uploading" }
                  : f,
              ),
            );
            try {
              await fetch(uploadUrl.signed_url, {
                method: "PUT",
                body: fileToUpload.file,
                headers: { "Content-Type": fileToUpload.file.type },
              });
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === fileToUpload.id ? { ...f, status: "done" } : f,
                ),
              );
            } catch {
              setFiles((prev) =>
                prev.map((f) =>
                  f.id === fileToUpload.id
                    ? { ...f, status: "error" }
                    : f,
                ),
              );
            }
          }
        }
      }

      // Step 3: Finalize case
      await apiClient.post(`/api/cases/${caseRes.case_id}/finalize`);

      // Step 4: Trigger agent pipeline
      setPhase("processing");
      await apiClient.post<unknown>(
        `/api/agents/run/${caseRes.case_id}`,
        { pipeline: "full" } satisfies AgentRunRequest,
      );

      toast.success("Hồ sơ đã tạo. Đang xử lý bởi AI...");
    } catch (err) {
      setPhase("error");
      toast.error("Có lỗi xảy ra khi tạo hồ sơ");
      console.error(err);
    }
  }

  const isProcessing = phase === "uploading" || phase === "processing";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tiếp nhận hồ sơ</h1>

      {/* Status banners */}
      <AnimatePresence mode="wait">
        {phase === "processing" && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/5 p-4"
            role="status"
            aria-live="polite"
          >
            <Loader2 className="h-5 w-5 animate-spin text-[var(--accent-primary)]" />
            <div>
              <p className="text-sm font-medium">
                Đang xử lý hồ sơ {activeCaseCode}...
              </p>
              <p className="text-xs text-[var(--text-muted)]">
                Pipeline AI đang phân tích tài liệu
              </p>
            </div>
          </motion.div>
        )}
        {phase === "done" && (
          <motion.div
            key="done"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center justify-between rounded-lg border border-[var(--accent-success)]/30 bg-[var(--accent-success)]/5 p-4"
          >
            <div className="flex items-center gap-3">
              <CheckCircle className="h-5 w-5 text-[var(--accent-success)]" />
              <div>
                <p className="text-sm font-medium">
                  Hoàn thành xử lý {activeCaseCode}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  Pipeline AI đã hoàn tất
                </p>
              </div>
            </div>
            <button
              onClick={() => router.push(`/trace/${activeCaseId}`)}
              className="flex items-center gap-1 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-sm font-medium text-white"
            >
              Xem Trace <ArrowRight className="h-3 w-3" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Compliance score bar - show during/after processing */}
      {(phase === "processing" || phase === "done") && trace && (
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Tiến trình xử lý</h3>
            <span className="text-lg font-bold">
              <AnimatedCounter value={complianceScore} suffix="%" />
            </span>
          </div>
          <div
            className="mt-2 h-2.5 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]"
            role="progressbar"
            aria-valuenow={complianceScore}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <motion.div
              className="h-full rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${complianceScore}%` }}
              transition={{ duration: 0.6, ease: [0.25, 1, 0.5, 1] }}
              style={{
                backgroundColor:
                  complianceScore >= 80
                    ? "var(--accent-success)"
                    : complianceScore >= 50
                      ? "var(--accent-warning)"
                      : "var(--accent-error)",
              }}
            />
          </div>
          {/* Agent steps */}
          <div className="mt-3 space-y-1">
            {trace.steps.map((step) => (
              <div
                key={step.step_id}
                className="flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${
                      step.status === "completed"
                        ? "bg-[var(--accent-success)]"
                        : step.status === "running"
                          ? "animate-pulse bg-[var(--accent-primary)]"
                          : "bg-[var(--text-muted)]"
                    }`}
                  />
                  <span className="font-medium">{step.agent_name}</span>
                  <span className="text-[var(--text-muted)]">
                    {step.action}
                  </span>
                </div>
                {step.duration_ms != null && (
                  <span className="font-mono text-[var(--text-muted)]">
                    {(step.duration_ms / 1000).toFixed(1)}s
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drag-drop upload zone */}
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          phase !== "idle"
            ? "pointer-events-none opacity-50"
            : isDragActive
              ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5"
              : "border-[var(--border-default)] hover:border-[var(--accent-primary)]/50"
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-8 w-8 text-[var(--text-muted)]" />
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          {isDragActive
            ? "Thả tài liệu vào đây..."
            : "Kéo thả tài liệu hoặc bấm để chọn"}
        </p>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          PDF, JPG, PNG (tối đa 20MB/file)
        </p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2" role="list">
          {files.map((f) => (
            <div
              key={f.id}
              role="listitem"
              className="flex items-center justify-between rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-2"
            >
              <div className="flex items-center gap-3">
                <FileText className="h-4 w-4 text-[var(--text-muted)]" />
                <div>
                  <p className="text-sm">{f.file.name}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {(f.file.size / 1024).toFixed(0)} KB
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {f.status === "uploading" && (
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--accent-primary)]" />
                )}
                {f.status === "done" && (
                  <CheckCircle className="h-4 w-4 text-[var(--accent-success)]" />
                )}
                {f.status === "error" && (
                  <span className="text-xs text-[var(--accent-error)]">
                    Lỗi
                  </span>
                )}
                {phase === "idle" && (
                  <button
                    onClick={() => removeFile(f.id)}
                    className="rounded p-1 hover:bg-[var(--bg-surface-raised)]"
                  >
                    <X className="h-3 w-3 text-[var(--text-muted)]" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* OCR Preview Grid */}
      {ocrPanels.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {ocrPanels.map((panel) => (
            <div
              key={panel.ossKey}
              className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium">{panel.filename}</p>
                {panel.ready ? (
                  <CheckCircle className="h-3 w-3 text-[var(--accent-success)]" />
                ) : (
                  <Loader2 className="h-3 w-3 animate-spin text-[var(--accent-primary)]" />
                )}
              </div>
              <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">
                {panel.docId}
              </p>
              <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-xs text-[var(--text-secondary)]">
                {panel.text}
              </pre>
            </div>
          ))}
        </div>
      )}

      {/* TTHC selector */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <label htmlFor="tthc-search" className="text-sm font-medium">
          Thủ tục hành chính *
        </label>
        <input
          id="tthc-search"
          type="text"
          value={tthcQuery}
          onChange={(e) => setTthcQuery(e.target.value)}
          placeholder="Tìm kiếm thủ tục..."
          disabled={isProcessing}
          className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
        />
        {tthcResults && tthcResults.length > 0 && tthcQuery.length >= 2 && (
          <div className="mt-2 max-h-40 space-y-1 overflow-auto">
            {tthcResults.map((t) => (
              <button
                key={t.tthc_code}
                onClick={() => {
                  setSelectedTTHC(t.tthc_code);
                  setTthcQuery(t.name);
                }}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-surface-raised)] ${selectedTTHC === t.tthc_code ? "bg-[var(--accent-primary)]/10" : ""}`}
              >
                <span className="font-mono text-xs text-[var(--text-muted)]">
                  {t.tthc_code}
                </span>{" "}
                {t.name}
                <span className="ml-2 text-xs text-[var(--text-muted)]">
                  ({t.sla_days} ngày)
                </span>
              </button>
            ))}
          </div>
        )}
        {selectedTTHC && (
          <p className="mt-2 text-xs text-[var(--accent-success)]">
            Đã chọn: {selectedTTHC}
          </p>
        )}
      </div>

      {/* Applicant form */}
      <div className="grid grid-cols-1 gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 md:grid-cols-2">
        <div>
          <label htmlFor="name" className="text-sm font-medium">
            Họ và tên *
          </label>
          <input
            id="name"
            value={form.applicant_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, applicant_name: e.target.value }))
            }
            disabled={isProcessing}
            className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
          />
        </div>
        <div>
          <label htmlFor="cccd" className="text-sm font-medium">
            Số CCCD *
          </label>
          <input
            id="cccd"
            value={form.applicant_id_number}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                applicant_id_number: e.target.value,
              }))
            }
            disabled={isProcessing}
            className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
          />
        </div>
        <div>
          <label htmlFor="phone" className="text-sm font-medium">
            Số điện thoại
          </label>
          <input
            id="phone"
            value={form.applicant_phone}
            onChange={(e) =>
              setForm((f) => ({ ...f, applicant_phone: e.target.value }))
            }
            disabled={isProcessing}
            className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
          />
        </div>
        <div>
          <label htmlFor="address" className="text-sm font-medium">
            Địa chỉ
          </label>
          <input
            id="address"
            value={form.applicant_address}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                applicant_address: e.target.value,
              }))
            }
            disabled={isProcessing}
            className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
          />
        </div>
        <div className="md:col-span-2">
          <label htmlFor="notes" className="text-sm font-medium">
            Ghi chú
          </label>
          <textarea
            id="notes"
            value={form.notes}
            onChange={(e) =>
              setForm((f) => ({ ...f, notes: e.target.value }))
            }
            rows={3}
            disabled={isProcessing}
            className="mt-1 w-full rounded-md border border-[var(--border-default)] bg-[var(--bg-app)] px-3 py-2 text-sm outline-none focus:border-[var(--accent-primary)] disabled:opacity-50"
          />
        </div>
      </div>

      {/* Submit / Navigate button */}
      {phase === "done" ? (
        <button
          onClick={() => router.push(`/trace/${activeCaseId}`)}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-[var(--accent-primary)] py-3 font-medium text-white transition-opacity hover:opacity-90"
        >
          Xem tiến trình xử lý <ArrowRight className="h-4 w-4" />
        </button>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={isProcessing || createCase.isPending}
          className="w-full rounded-md bg-[var(--accent-primary)] py-3 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isProcessing
            ? "Đang xử lý..."
            : "Tạo hồ sơ & khởi chạy pipeline"}
        </button>
      )}
    </div>
  );
}
