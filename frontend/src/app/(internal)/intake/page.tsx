"use client";

import * as React from "react";
import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { useCreateCase } from "@/hooks/use-cases";
import { useAgentTrace } from "@/hooks/use-agents";
import { useSearchTTHC } from "@/hooks/use-search";
import { usePublicStats } from "@/hooks/use-public";
import { apiClient } from "@/lib/api";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import type {
  BundleCreate,
  BundleResponse,
  AgentRunRequest,
  AgentStepResponse,
} from "@/lib/types";
import {
  Upload,
  FileText,
  X,
  CheckCircle,
  Loader2,
  ArrowRight,
  Nfc,
  Printer,
  Users,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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

type NfcPhase = "idle" | "reading" | "decoding" | "done";

interface TthcConfidence {
  code: string;
  name: string;
  pct: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract a text blob from an AgentStepResponse for display in OCR panels.
 *  AgentStepResponse has no `output_summary`; we read from `action` field
 *  which the backend populates with a description of what was done. */
function stepText(step: AgentStepResponse): string {
  return step.action ?? "";
}

// NFC demo fixture — auto-fill form with sample citizen data
import nfcFixture from "@/fixtures/nfc-citizen.json";

// ---------------------------------------------------------------------------
// NFC Modal
// ---------------------------------------------------------------------------

function NfcModal({
  phase,
  onClose,
}: {
  phase: NfcPhase;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Quét CCCD qua NFC"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.92 }}
        transition={{ duration: 0.2 }}
        className="w-80 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 shadow-2xl"
      >
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="relative">
            {/* Outer pulse ring */}
            {phase === "reading" && (
              <motion.div
                className="absolute inset-0 rounded-full border-2 border-[var(--accent-primary)]"
                animate={{ scale: [1, 1.5, 1], opacity: [0.8, 0, 0.8] }}
                transition={{ duration: 1.4, repeat: Infinity }}
              />
            )}
            <div
              className={`flex h-16 w-16 items-center justify-center rounded-full ${
                phase === "done"
                  ? "bg-[var(--accent-success)]/10"
                  : "bg-[var(--accent-primary)]/10"
              }`}
            >
              {phase === "done" ? (
                <CheckCircle className="h-8 w-8 text-[var(--accent-success)]" />
              ) : (
                <Nfc
                  className={`h-8 w-8 ${
                    phase === "reading"
                      ? "animate-pulse text-[var(--accent-primary)]"
                      : "text-[var(--text-muted)]"
                  }`}
                />
              )}
            </div>
          </div>

          <div>
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              {phase === "reading" && "Vui lòng áp CCCD lên đầu đọc NFC..."}
              {phase === "decoding" && "Đọc thành công — đang giải mã..."}
              {phase === "done" && "Đã đọc thông tin CCCD!"}
            </p>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              {phase === "reading" &&
                "Giữ yên thẻ cho đến khi hoàn tất"}
              {phase === "decoding" && "Đang xác minh chữ ký số BAC/EAC..."}
              {phase === "done" && "Thông tin đã được điền vào biểu mẫu"}
            </p>
          </div>

          {(phase === "reading" || phase === "decoding") && (
            <Loader2 className="h-5 w-5 animate-spin text-[var(--accent-primary)]" />
          )}

          {phase === "done" && (
            <button
              onClick={onClose}
              className="rounded-md bg-[var(--accent-primary)] px-4 py-1.5 text-sm font-medium text-white hover:opacity-90"
            >
              Xác nhận
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Print Receipt Dialog
// ---------------------------------------------------------------------------

function PrintReceiptDialog({
  caseCode,
  slaDate,
  onClose,
}: {
  caseCode: string;
  slaDate: string;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Biên nhận hồ sơ"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 12 }}
        className="w-[480px] rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-2xl"
      >
        {/* Receipt preview */}
        <div className="border-b border-[var(--border-subtle)] p-5">
          <div className="text-center">
            <p className="text-xs font-semibold uppercase tracking-widest text-[var(--text-muted)]">
              CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
            </p>
            <p className="text-[10px] text-[var(--text-muted)]">
              Độc lập – Tự do – Hạnh phúc
            </p>
            <p className="mt-3 text-base font-bold text-[var(--text-primary)]">
              BIÊN NHẬN HỒ SƠ
            </p>
            <p className="text-xs text-[var(--text-muted)]">
              (Theo NĐ 61/2018/NĐ-CP)
            </p>
          </div>

          <div className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Mã hồ sơ</span>
              <span className="font-mono font-semibold text-[var(--text-primary)]">
                {caseCode}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Ngày nộp</span>
              <span className="text-[var(--text-primary)]">
                {new Intl.DateTimeFormat("vi-VN", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                }).format(new Date())}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Dự kiến trả kết quả</span>
              <span className="font-medium text-[var(--accent-success)]">
                {slaDate}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Cơ quan xử lý</span>
              <span className="text-[var(--text-primary)]">Sở Xây dựng Hà Nội</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--text-muted)]">Căn cứ pháp lý</span>
              <span className="text-right text-xs text-[var(--text-secondary)]">
                NĐ 15/2021/NĐ-CP Điều 95
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between p-4">
          <button
            onClick={onClose}
            className="rounded-md border border-[var(--border-default)] px-4 py-1.5 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
          >
            Đóng
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => {
                navigator.clipboard.writeText(caseCode);
                toast.success("Đã sao chép mã hồ sơ");
              }}
              className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
            >
              Sao chép mã
            </button>
            <button
              onClick={() => {
                toast.info("Đang xuất PDF biên nhận...");
                onClose();
              }}
              className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"
            >
              <Printer className="h-3.5 w-3.5" />
              In biên nhận
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TTHC Confidence Bars
// ---------------------------------------------------------------------------

function TthcConfidenceBars({
  suggestions,
  onSelect,
}: {
  suggestions: TthcConfidence[];
  onSelect: (code: string, name: string) => void;
}) {
  return (
    <div className="mt-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
        AI gợi ý thủ tục — bấm để chọn
      </p>
      <div className="space-y-2">
        {suggestions.map((s) => (
          <button
            key={s.code}
            onClick={() => onSelect(s.code, s.name)}
            className="group w-full rounded-md p-2 text-left transition-colors hover:bg-[var(--bg-surface-raised)]"
            title={`Chọn ${s.name}`}
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-[var(--text-primary)] group-hover:text-[var(--accent-primary)]">
                {s.name}
              </span>
              <span className="font-mono text-[var(--text-muted)]">
                {s.pct}%
              </span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]">
              <motion.div
                className="h-full rounded-full"
                style={{
                  backgroundColor:
                    s.pct >= 80
                      ? "var(--accent-success)"
                      : s.pct >= 40
                        ? "var(--accent-warning)"
                        : "var(--accent-primary)",
                }}
                initial={{ width: 0 }}
                animate={{ width: `${s.pct}%` }}
                transition={{ duration: 0.6, ease: [0.25, 1, 0.5, 1], delay: 0.1 }}
              />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function IntakeUI() {
  const router = useRouter();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [tthcQuery, setTthcQuery] = useState("");
  const [selectedTTHC, setSelectedTTHC] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [activeCaseCode, setActiveCaseCode] = useState<string | null>(null);
  const [ocrPanels, setOcrPanels] = useState<OcrPanel[]>([]);
  const [showTthcSuggestions, setShowTthcSuggestions] = useState(false);
  const [nfcPhase, setNfcPhase] = useState<NfcPhase>("idle");
  const [showNfcModal, setShowNfcModal] = useState(false);
  const [showReceiptDialog, setShowReceiptDialog] = useState(false);
  const nfcTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const [form, setForm] = useState({
    applicant_name: "",
    applicant_id_number: "",
    applicant_phone: "",
    applicant_address: "",
    department_id: "DEPT-QLDT",
    notes: "",
  });
  const [classifyConfidence, setClassifyConfidence] = useState<TthcConfidence[]>([]);
  const [isLoadingDemo, setIsLoadingDemo] = useState(false);

  const { data: tthcResults } = useSearchTTHC(tthcQuery);
  const { data: publicStats } = usePublicStats();
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
  if (trace?.status === "completed" && phase === "processing") {
    setPhase("done");
    toast.success("Pipeline hoàn thành!");
  }

  // When doc_analyzer / intake steps complete, extract text from their `action`
  // field (AgentStepResponse has no output_summary). Best-effort parse of the
  // action string for doc/entity info; fall back to raw action text.
  React.useEffect(() => {
    if (!trace?.steps || ocrPanels.length === 0) return;
    const relevant = trace.steps.filter(
      (s) =>
        (s.agent_name === "doc_analyze_agent" ||
          s.agent_name === "intake_agent") &&
        s.status === "completed",
    );
    if (relevant.length === 0) return;

    setOcrPanels((prev) => {
      let changed = false;
      const updated = prev.map((panel) => {
        if (panel.ready) return panel;
        for (const step of relevant) {
          const out = stepText(step);
          if (out.includes(panel.filename) || out.includes(panel.docId)) {
            changed = true;
            return { ...panel, ready: true, text: out.slice(0, 400) };
          }
        }
        // After any relevant step finished, mark pending panels ready
        if (relevant.length > 0 && !panel.ready) {
          changed = true;
          return {
            ...panel,
            ready: true,
            text: stepText(relevant[0]).slice(0, 400) || "Đã xử lý xong",
          };
        }
        return panel;
      });
      return changed ? updated : prev;
    });
  }, [trace, ocrPanels.length]);

  // ---------------------------------------------------------------------------
  // NFC CCCD scan
  // ---------------------------------------------------------------------------
  function startNfcScan() {
    setNfcPhase("reading");
    setShowNfcModal(true);

    const t1 = setTimeout(() => {
      setNfcPhase("decoding");
    }, 2000);

    const t2 = setTimeout(() => {
      setNfcPhase("done");
      // Auto-fill form from NFC fixture (demo mode)
      setForm((f) => ({
        ...f,
        applicant_name: (nfcFixture as Record<string, string>).applicant_name ?? "Nguyễn Văn A",
        applicant_id_number: (nfcFixture as Record<string, string>).applicant_id_number ?? "024097012345",
        applicant_phone: (nfcFixture as Record<string, string>).applicant_phone ?? "0901234567",
        applicant_address: (nfcFixture as Record<string, string>).applicant_address ?? "123 Đường Láng, Đống Đa, Hà Nội",
      }));
    }, 3100);

    nfcTimers.current = [t1, t2];
  }

  function closeNfcModal() {
    nfcTimers.current.forEach(clearTimeout);
    setShowNfcModal(false);
    if (nfcPhase === "done") {
      toast.success("Đã điền thông tin từ CCCD");
    }
    setNfcPhase("idle");
  }

  // ---------------------------------------------------------------------------
  // File drop
  // ---------------------------------------------------------------------------
  const onDrop = useCallback((accepted: File[]) => { void (async () => {
    const newFiles = accepted.map((f) => ({
      file: f,
      id: crypto.randomUUID(),
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
    setShowTthcSuggestions(true);

    // Try to call the classify endpoint to get real confidence scores
    try {
      const firstFile = accepted[0];
      if (!firstFile) return;
      const formData = new FormData();
      formData.append("file", firstFile);
      const res = await fetch("/api/agents/classify", {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${localStorage.getItem("govflow-token") ?? ""}`,
        },
      });
      if (res.ok) {
        const data = await res.json() as {
          confidence?: Array<{ code: string; name: string; pct?: number; score?: number }>;
          alternatives?: Array<{ code: string; name: string; pct?: number; score?: number }>;
          tthc_code?: string;
          tthc_name?: string;
        };
        const rawList = data.confidence ?? data.alternatives ?? [];
        if (rawList.length > 0) {
          setClassifyConfidence(
            rawList.map((r) => ({
              code: r.code,
              name: r.name,
              pct: Math.round((r.pct ?? r.score ?? 0) * (r.pct && r.pct <= 1 ? 100 : 1)),
            })),
          );
          return;
        }
        // Single top result
        if (data.tthc_code && data.tthc_name) {
          setClassifyConfidence([{ code: data.tthc_code, name: data.tthc_name, pct: 94 }]);
          return;
        }
      }
    } catch {
      // Classify endpoint not available — fall through to default suggestions
    }

    // Fallback: static suggestions when API is unavailable
    setClassifyConfidence([
      { code: "1.004415", name: "Cấp phép xây dựng (GPXD)", pct: 94 },
      { code: "1.000046", name: "GCN quyền sử dụng đất", pct: 3 },
      { code: "1.001757", name: "Đăng ký kinh doanh", pct: 2 },
    ]);
  })(); }, []);

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
    if (files.length <= 1) setShowTthcSuggestions(false);
  };

  // ---------------------------------------------------------------------------
  // Demo quick-fill
  // ---------------------------------------------------------------------------
  async function handleLoadDemoSample() {
    setIsLoadingDemo(true);
    try {
      // Try public demo-samples endpoint first (pattern from submit-wizard)
      const sample = await apiClient.get<{
        tthc_code?: string;
        tthc_name?: string;
        applicant_name?: string;
        applicant_id_number?: string;
        applicant_phone?: string;
        applicant_address?: string;
        notes?: string;
        sample_files?: Array<{ filename: string; url: string; doc_type?: string }>;
      }>("/api/public/demo-samples/1.004415");

      setSelectedTTHC(sample.tthc_code ?? "1.004415");
      setTthcQuery(sample.tthc_name ?? "Cấp phép xây dựng (GPXD)");
      setForm((f) => ({
        ...f,
        applicant_name: sample.applicant_name ?? "Nguyễn Văn Bình",
        applicant_id_number: sample.applicant_id_number ?? "001085012345",
        applicant_phone: sample.applicant_phone ?? "0912345678",
        applicant_address:
          sample.applicant_address ??
          "Số 18 Nguyễn Trãi, Phường Thượng Đình, Quận Thanh Xuân, Hà Nội",
        notes: sample.notes ?? "Hồ sơ xin cấp phép xây dựng nhà ở riêng lẻ",
        department_id: "DEPT-QLDT",
      }));

      // Auto-load sample files from the demo-samples API
      const sampleFileList = sample.sample_files ?? [
        { filename: "sample_cccd.jpg", url: "/public/samples/sample_cccd.jpg" },
        { filename: "sample_don_xin_cpxd.pdf", url: "/public/samples/sample_don_xin_cpxd.pdf" },
        { filename: "sample_ban_ve_thiet_ke.pdf", url: "/public/samples/sample_ban_ve_thiet_ke.pdf" },
        { filename: "sample_gcn_qsdd.pdf", url: "/public/samples/sample_gcn_qsdd.pdf" },
      ];
      const fetchedFiles: UploadedFile[] = await Promise.all(
        sampleFileList.map(async (sf) => {
          try {
            const resp = await fetch(sf.url);
            const blob = await resp.blob();
            const mimeType = sf.filename.endsWith(".pdf") ? "application/pdf" : "image/jpeg";
            const file = new File([blob], sf.filename, { type: mimeType });
            return { file, id: crypto.randomUUID(), status: "pending" as const };
          } catch {
            // If fetch fails, create a stub file so the list renders
            const mimeType = sf.filename.endsWith(".pdf") ? "application/pdf" : "image/jpeg";
            const file = new File(["demo"], sf.filename, { type: mimeType });
            return { file, id: crypto.randomUUID(), status: "pending" as const };
          }
        }),
      );
      setFiles(fetchedFiles);
      setShowTthcSuggestions(false);
      toast.success(`Đã điền dữ liệu mẫu · ${fetchedFiles.length} tài liệu`);
    } catch {
      // Fallback inline fixture when endpoint unavailable
      setSelectedTTHC("1.004415");
      setTthcQuery("Cấp phép xây dựng (GPXD)");
      setForm((f) => ({
        ...f,
        applicant_name: "Nguyễn Văn Bình",
        applicant_id_number: "001085012345",
        applicant_phone: "0912345678",
        applicant_address:
          "Số 18 Nguyễn Trãi, Phường Thượng Đình, Quận Thanh Xuân, Hà Nội",
        notes: "Hồ sơ xin cấp phép xây dựng nhà ở riêng lẻ",
        department_id: "DEPT-QLDT",
      }));
      // Stub files from known public path
      const stubNames = [
        { name: "sample_cccd.jpg", type: "image/jpeg" },
        { name: "sample_don_xin_cpxd.pdf", type: "application/pdf" },
        { name: "sample_ban_ve_thiet_ke.pdf", type: "application/pdf" },
        { name: "sample_gcn_qsdd.pdf", type: "application/pdf" },
      ];
      setFiles(
        stubNames.map((s) => ({
          file: new File(["demo"], s.name, { type: s.type }),
          id: crypto.randomUUID(),
          status: "pending" as const,
        })),
      );
      toast.success("Đã điền dữ liệu mẫu · 4 tài liệu");
    } finally {
      setIsLoadingDemo(false);
    }
  }

  // ---------------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------------
  async function handleSubmit() {
    if (!selectedTTHC || !form.applicant_name || !form.applicant_id_number) {
      toast.error("Vui lòng điền đầy đủ thông tin bắt buộc");
      return;
    }

    setPhase("uploading");

    try {
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

        setOcrPanels(
          bundleRes.upload_urls.map((u) => ({
            docId: u.oss_key.split("/").pop() || u.filename,
            filename: u.filename,
            ossKey: u.oss_key,
            ready: false,
            text: "Đang trích xuất...",
          })),
        );

        for (const uploadUrl of bundleRes.upload_urls) {
          const fileToUpload = files.find(
            (f) => f.file.name === uploadUrl.filename,
          );
          if (fileToUpload) {
            setFiles((prev) =>
              prev.map((f) =>
                f.id === fileToUpload.id ? { ...f, status: "uploading" } : f,
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
                  f.id === fileToUpload.id ? { ...f, status: "error" } : f,
                ),
              );
            }
          }
        }
      }

      await apiClient.post(`/api/cases/${caseRes.case_id}/finalize`);

      setPhase("processing");
      apiClient
        .post<unknown>(
          `/api/agents/run/${caseRes.case_id}`,
          { pipeline: "full" } satisfies AgentRunRequest,
        )
        .catch((e) => console.error("agent run trigger failed", e));

      toast.success("Hồ sơ đã tạo. Đang xử lý AI — xem live trace ngay...");
      router.push(`/trace/${caseRes.case_id}`);
    } catch (err) {
      setPhase("error");
      toast.error("Có lỗi xảy ra khi tạo hồ sơ");
      console.error(err);
    }
  }

  const isProcessing = phase === "uploading" || phase === "processing";

  // SLA date string: today + 10 working days (approx)
  const slaDate = (() => {
    const d = new Date();
    d.setDate(d.getDate() + 14);
    return `trước 17:00 ngày ${new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    }).format(d)}`;
  })();

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="space-y-6">
      {/* NFC modal */}
      <AnimatePresence>
        {showNfcModal && (
          <NfcModal phase={nfcPhase} onClose={closeNfcModal} />
        )}
      </AnimatePresence>

      {/* Print receipt dialog */}
      <AnimatePresence>
        {showReceiptDialog && activeCaseCode && (
          <PrintReceiptDialog
            caseCode={activeCaseCode}
            slaDate={slaDate}
            onClose={() => setShowReceiptDialog(false)}
          />
        )}
      </AnimatePresence>

      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tiếp nhận hồ sơ</h1>
        <div className="flex items-center gap-2">
          {/* Queue counter */}
          <div className="flex items-center gap-1.5 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5">
            <Users className="h-3.5 w-3.5 text-[var(--text-muted)]" />
            <span className="text-xs text-[var(--text-muted)]">
              {publicStats
                ? `${publicStats.cases_this_month} hồ sơ đang chờ`
                : "— hồ sơ đang chờ"}
            </span>
          </div>
          <button
            type="button"
            onClick={() => void handleLoadDemoSample()}
            disabled={isLoadingDemo || phase !== "idle"}
            className="flex items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-600 to-violet-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Nạp hồ sơ mẫu (chế độ demo)"
            title="Điền thông tin hồ sơ CPXD mẫu + 4 tài liệu để demo nhanh"
          >
            {isLoadingDemo ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            )}
            Điền mẫu (demo)
          </button>
          <button
            type="button"
            onClick={() => router.push("/trace/CASE-2026-0001")}
            className="flex items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-50 to-violet-50 px-3 py-1.5 text-xs font-medium text-purple-700 hover:opacity-90 dark:border-purple-700 dark:from-purple-950 dark:to-violet-950 dark:text-purple-200"
            title="Mở hồ sơ CPXD mẫu đã có trace + gap + citation"
          >
            Xem case mẫu →
          </button>
          <OnboardingTour tourId="officer-inbox" showButton={true} />
        </div>
      </div>

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
            <div className="flex gap-2">
              <button
                onClick={() => setShowReceiptDialog(true)}
                className="flex items-center gap-1 rounded-md border border-[var(--border-default)] px-3 py-1.5 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
              >
                <Printer className="h-3.5 w-3.5" />
                In biên nhận
              </button>
              <button
                onClick={() => router.push(`/trace/${activeCaseId}`)}
                className="flex items-center gap-1 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-sm font-medium text-white"
              >
                Xem Trace <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Compliance score bar */}
      {(phase === "processing" || phase === "done") && trace && (
        <div
          className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
          data-tour="intake-pipeline"
        >
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
      <HelpHintBanner id="intake-upload" variant="tip">
        Kéo thả file PDF/JPG vào đây.{" "}
        <strong>Qwen3-VL</strong> sẽ tự động OCR và trích xuất thông tin hồ
        sơ.
      </HelpHintBanner>
      <div
        data-tour="intake-upload"
        {...getRootProps()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          phase !== "idle"
            ? "pointer-events-none opacity-50"
            : isDragActive
              ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5"
              : "border-[var(--border-default)] hover:border-[var(--accent-primary)]/50"
        }`}
      >
        <input {...getInputProps()} aria-label="Tải lên tài liệu (PDF, JPG, PNG)" />
        <Upload className="mx-auto h-8 w-8 text-[var(--text-muted)]" aria-hidden="true" />
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
                    aria-label={`Xóa file ${f.file.name}`}
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
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition-colors hover:bg-[var(--bg-surface-raised)] ${
                  selectedTTHC === t.tthc_code
                    ? "bg-[var(--accent-primary)]/10"
                    : ""
                }`}
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

        {/* AI classifier confidence bars — shown after file upload */}
        <AnimatePresence>
          {showTthcSuggestions && !selectedTTHC && classifyConfidence.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
            >
              <TthcConfidenceBars
                suggestions={classifyConfidence}
                onSelect={(code, name) => {
                  setSelectedTTHC(code);
                  setTthcQuery(name);
                  setShowTthcSuggestions(false);
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Applicant form */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        {/* Section header with NFC button */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold">Thông tin người nộp hồ sơ</h2>
          <button
            type="button"
            onClick={startNfcScan}
            disabled={isProcessing}
            title="Chức năng demo: mô phỏng quét CCCD qua NFC để tự điền thông tin vào biểu mẫu. Trong môi trường thực tế, thiết bị đọc NFC phần cứng sẽ được dùng."
            className="flex items-center gap-1.5 rounded-md border border-amber-400/50 bg-amber-50/80 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-100 disabled:opacity-50 dark:bg-amber-900/20 dark:text-amber-300"
            aria-label="Mô phỏng quét CCCD qua NFC (chế độ demo)"
          >
            <Nfc className="h-3.5 w-3.5" />
            Mô phỏng quét NFC (demo)
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
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
      </div>

      {/* Submit / Navigate button */}
      {phase === "done" ? (
        <div className="flex gap-3">
          <button
            onClick={() => setShowReceiptDialog(true)}
            className="flex flex-1 items-center justify-center gap-2 rounded-md border border-[var(--border-default)] py-3 font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            <Printer className="h-4 w-4" /> In biên nhận
          </button>
          <button
            onClick={() => router.push(`/trace/${activeCaseId}`)}
            className="flex flex-[2] items-center justify-center gap-2 rounded-md bg-[var(--accent-primary)] py-3 font-medium text-white transition-opacity hover:opacity-90"
          >
            Xem tiến trình xử lý <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={isProcessing || createCase.isPending}
          className="w-full rounded-md bg-[var(--accent-primary)] py-3 font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {isProcessing ? "Đang xử lý..." : "Tạo hồ sơ & khởi chạy pipeline"}
        </button>
      )}
    </div>
  );
}
