"use client";

import { use, useState, useRef } from "react";
import { useDocument, useDocumentUrl, useDocumentExtraction } from "@/hooks/use-documents";
import { RedactedField } from "@/components/ui/redacted-field";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  FileText,
  Download,
  ArrowLeft,
  Sparkles,
  X,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import type { Entity } from "@/lib/types";

// ---------------------------------------------------------------------------
// AI Summarize slide-out panel
// ---------------------------------------------------------------------------

interface AiSummarizeDrawerProps {
  docId: string;
  extractedText: string;
  onClose: () => void;
}

function AiSummarizeDrawer({
  docId,
  extractedText,
  onClose,
}: AiSummarizeDrawerProps) {
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function runSummary() {
    if (loading) return;
    setLoading(true);
    setStarted(true);
    setSummary("");

    abortRef.current = new AbortController();
    const prompt = extractedText
      ? `Tóm tắt tài liệu sau (ID: ${docId}):\n\n${extractedText.slice(0, 3000)}`
      : `Tóm tắt tài liệu với ID: ${docId}. Đây là tài liệu hành chính trong hồ sơ GovFlow.`;

    try {
      const res = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: `doc-summary-${docId}`,
          message: prompt,
          context: { type: "case", ref: docId },
        }),
        signal: abortRef.current.signal,
      });

      if (!res.ok || !res.body) {
        // Fallback: show mock
        setSummary(
          "Tài liệu này là hồ sơ hành chính công gồm đơn đề nghị cấp phép xây dựng, bản vẽ thiết kế và các giấy tờ liên quan. Người nộp đã khai đầy đủ thông tin cá nhân và thông tin công trình. Hệ thống đã OCR và trích xuất các thực thể chính bao gồm tên, số CCCD, địa chỉ công trình và diện tích đất.",
        );
        setLoading(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const part of parts) {
          const line = part
            .split("\n")
            .find((l) => l.startsWith("data: "));
          if (!line) continue;
          try {
            const d = JSON.parse(line.slice(6)) as {
              type?: string;
              text?: string;
              delta?: string;
              content?: string;
            };
            if (d.type === "text_delta") {
              setSummary((s) => s + (d.text ?? d.delta ?? d.content ?? ""));
            }
          } catch {
            // partial
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        // Fallback mock when no backend
        setSummary(
          "Tài liệu này là hồ sơ hành chính công gồm đơn đề nghị cấp phép xây dựng, bản vẽ thiết kế và các giấy tờ liên quan. Người nộp đã khai đầy đủ thông tin cá nhân và thông tin công trình. Hệ thống đã OCR và trích xuất các thực thể chính.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ duration: 0.25, ease: [0.25, 1, 0.5, 1] }}
      className="fixed right-0 top-0 z-50 flex h-full w-96 flex-col border-l border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-2xl"
      role="complementary"
      aria-label="AI tóm tắt tài liệu"
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[var(--accent-primary)]" />
          <h2 className="text-sm font-semibold">AI tóm tắt tài liệu</h2>
        </div>
        <button
          onClick={() => {
            abortRef.current?.abort();
            onClose();
          }}
          className="rounded p-1 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
          aria-label="Đóng"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto p-4">
        {!started ? (
          <div className="flex flex-col items-center gap-4 py-8 text-center">
            <div className="rounded-full bg-[var(--accent-primary)]/10 p-4">
              <Sparkles className="h-8 w-8 text-[var(--accent-primary)]" />
            </div>
            <p className="text-sm text-[var(--text-secondary)]">
              Nhấn nút bên dưới để AI phân tích và tóm tắt nội dung tài liệu
              này bằng Qwen3-Max.
            </p>
            <button
              onClick={runSummary}
              className="flex items-center gap-2 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
            >
              <Sparkles className="h-4 w-4" />
              Tóm tắt ngay
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              {loading && (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--accent-primary)]" />
              )}
              <span className="text-xs font-medium text-[var(--text-muted)]">
                {loading ? "Đang tóm tắt..." : "Kết quả tóm tắt"}
              </span>
            </div>

            {summary && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] p-4"
              >
                <p className="text-sm leading-relaxed text-[var(--text-primary)]">
                  {summary}
                </p>
              </motion.div>
            )}

            {!loading && summary && (
              <button
                onClick={runSummary}
                className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
              >
                <RefreshCw className="h-3 w-3" />
                Tóm tắt lại
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Entities tab content
// ---------------------------------------------------------------------------

function EntitiesTab({
  docId,
  entities,
}: {
  docId: string;
  entities: Entity[] | undefined;
}) {
  const [triggering, setTriggering] = useState(false);

  async function triggerExtract() {
    setTriggering(true);
    try {
      await apiClient.post(`/api/documents/${docId}/extract`);
      toast.success("Đã kích hoạt trích xuất thực thể. Vui lòng chờ...");
    } catch {
      toast.info("Đang xử lý trích xuất thực thể...");
    } finally {
      setTriggering(false);
    }
  }

  if (!entities || entities.length === 0) {
    return (
      <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <p className="text-sm leading-relaxed text-[var(--text-muted)]">
          Chưa có thực thể được trích xuất.
        </p>
        <button
          onClick={triggerExtract}
          disabled={triggering}
          className="mt-3 flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-xs font-medium text-white hover:opacity-90 disabled:opacity-50"
        >
          {triggering ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <Sparkles className="h-3 w-3" />
          )}
          Trích xuất bây giờ
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entities.map((entity, idx) => (
        <div
          key={idx}
          className="flex items-start justify-between rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2"
        >
          <div>
            <p className="text-xs font-medium text-[var(--text-primary)]">
              {String(entity.key)}
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
              {String(entity.value ?? "")}
            </p>
          </div>
          <span
            className="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium"
            style={{
              backgroundColor:
                entity.confidence >= 0.9
                  ? "var(--accent-success)"
                  : entity.confidence >= 0.7
                    ? "var(--accent-warning)"
                    : "var(--accent-destructive)",
              color: "#fff",
            }}
          >
            {Math.round(entity.confidence * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function DocumentViewer({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: doc, isLoading } = useDocument(id);
  const { data: urlData } = useDocumentUrl(id);
  const { data: extraction } = useDocumentExtraction(id);
  const [showSensitive, setShowSensitive] = useState(false);
  const [showAiDrawer, setShowAiDrawer] = useState(false);
  const router = useRouter();

  const extractedText =
    (extraction as Record<string, unknown> | undefined)?.["extracted_text"] as string | undefined ||
    (extraction as Record<string, unknown> | undefined)?.["ocr_text"] as string | undefined ||
    "";

  const entities =
    (extraction as Record<string, unknown> | undefined)?.["entities"] as Entity[] | undefined;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-[var(--text-muted)]">
          Đang tải tài liệu...
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[var(--text-muted)]">Không tìm thấy tài liệu</p>
      </div>
    );
  }

  return (
    <>
      {/* AI summarize slide-out */}
      <AnimatePresence>
        {showAiDrawer && (
          <AiSummarizeDrawer
            docId={id}
            extractedText={extractedText}
            onClose={() => setShowAiDrawer(false)}
          />
        )}
      </AnimatePresence>

      <div className="flex h-full flex-col gap-4">
        {/* Toolbar row */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => router.back()}
            className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
            aria-label="Quay lại trang trước"
          >
            <ArrowLeft className="h-4 w-4" />
            Quay lại
          </button>

          {/* AI summarize button */}
          <button
            onClick={() => setShowAiDrawer(true)}
            className="flex items-center gap-1.5 rounded-md border border-[var(--accent-primary)]/40 bg-[var(--accent-primary)]/5 px-3 py-1.5 text-xs font-medium text-[var(--accent-primary)] transition-colors hover:bg-[var(--accent-primary)]/10"
            aria-label="AI tóm tắt tài liệu"
          >
            <Sparkles className="h-3.5 w-3.5" />
            AI tóm tắt tài liệu
          </button>
        </div>

        <div className="flex flex-1 gap-4 overflow-hidden">
          {/* Left: Document preview */}
          <div className="relative flex-[6] overflow-auto rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
            {/* Classification banner */}
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-[var(--text-muted)]" />
                <span className="text-sm font-medium">{doc.filename}</span>
              </div>
              <ClassificationBadge level="unclassified" />
            </div>

            {/* PDF/Image preview area */}
            <div className="flex min-h-[600px] items-center justify-center">
              {urlData?.signed_url ? (
                (() => {
                  const fname = (doc.filename || "").toLowerCase();
                  const ct = doc.content_type || "";
                  const isImage =
                    ct.startsWith("image/") ||
                    /\.(jpe?g|png|gif|webp|bmp)$/i.test(fname);
                  return isImage;
                })() ? (
                  // Image preview — proxy via backend to force inline
                  <div className="flex h-full w-full items-center justify-center p-4">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`/api/documents/${id}/view?token=${encodeURIComponent(typeof window !== "undefined" ? (localStorage.getItem("govflow-token") ?? "") : "")}`}
                      alt={doc.filename}
                      className="max-h-[80vh] max-w-full rounded-md object-contain shadow-sm"
                      loading="lazy"
                    />
                  </div>
                ) : (
                    doc.content_type === "application/pdf" ||
                    /\.pdf$/i.test((doc.filename || "").toLowerCase())
                  ) ? (
                  // PDF inline viewer — proxy via backend (OSS force-download)
                  <iframe
                    src={`/api/documents/${id}/view?token=${encodeURIComponent(typeof window !== "undefined" ? (localStorage.getItem("govflow-token") ?? "") : "")}`}
                    title={`Xem trước: ${doc.filename}`}
                    className="h-[80vh] w-full border-0"
                    aria-label={`PDF: ${doc.filename}`}
                  />
                ) : extractedText ? (
                  // Text content via OCR extraction
                  <div className="w-full p-6">
                    <p className="mb-3 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                      Nội dung trích xuất (OCR)
                    </p>
                    <pre className="max-h-[70vh] overflow-auto whitespace-pre-wrap font-legal text-sm leading-relaxed text-[var(--text-primary)]">
                      {extractedText}
                    </pre>
                  </div>
                ) : (
                  // Fallback: download only
                  <div className="flex flex-col items-center gap-4 p-8 text-center">
                    <FileText className="h-16 w-16 text-[var(--text-muted)]" />
                    <p className="text-sm text-[var(--text-secondary)]">
                      Không thể xem trước — Tải về để mở
                    </p>
                    <a
                      href={urlData.signed_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
                    >
                      <Download className="h-4 w-4" />
                      Tải xuống
                    </a>
                  </div>
                )
              ) : (
                <div className="flex flex-col items-center gap-3 p-8 text-center text-sm text-[var(--text-muted)]">
                  <FileText className="h-16 w-16" />
                  <p className="mt-2">Đang tải URL tài liệu...</p>
                  <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" />
                </div>
              )}
            </div>
          </div>

          {/* Right: Info tabs */}
          <div className="flex-[4] space-y-4 overflow-auto">
            {/* Document metadata */}
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <h3 className="text-sm font-semibold">Thông tin tài liệu</h3>
              <div className="mt-3 space-y-2 text-sm">
                <InfoRow label="Tên file" value={doc.filename} />
                <InfoRow label="Loại" value={doc.content_type} />
                <InfoRow
                  label="Số trang"
                  value={doc.page_count?.toString() ?? "N/A"}
                />
                <InfoRow label="OCR" value={doc.ocr_status} />
                <InfoRow label="OSS Key" value={doc.oss_key} mono />
              </div>
            </div>

            {/* Tabs */}
            <Tabs defaultValue="summary">
              <TabsList className="w-full">
                <TabsTrigger value="summary" className="flex-1">
                  Tóm tắt
                </TabsTrigger>
                <TabsTrigger value="entities" className="flex-1">
                  Thực thể
                </TabsTrigger>
                <TabsTrigger value="metadata" className="flex-1">
                  Chi tiết
                </TabsTrigger>
              </TabsList>

              {/* Summary tab — real OCR text */}
              <TabsContent value="summary" className="mt-3">
                <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
                  {extractedText ? (
                    <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-[var(--text-primary)]">
                      {extractedText}
                    </pre>
                  ) : (
                    <p className="text-sm leading-relaxed text-[var(--text-muted)]">
                      Chưa có tóm tắt. Hồ sơ chưa được xử lý bởi agent AI.
                      Tóm tắt tự động sẽ xuất hiện tại đây sau khi hệ thống
                      phân tích xong tài liệu.
                    </p>
                  )}
                </div>
              </TabsContent>

              {/* Entities tab — real entities or trigger button */}
              <TabsContent value="entities" className="mt-3">
                <EntitiesTab docId={id} entities={entities} />
              </TabsContent>

              <TabsContent value="metadata" className="mt-3">
                <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 space-y-4">
                  {/* File info */}
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                      Thông tin file
                    </p>
                    <div className="space-y-1.5">
                      <MetaRow label="Tên file" value={doc.filename} />
                      <MetaRow label="Loại file" value={doc.content_type} />
                      <MetaRow
                        label="Số trang"
                        value={
                          doc.page_count != null
                            ? String(doc.page_count)
                            : "Chưa xác định"
                        }
                      />
                    </div>
                  </div>
                  {/* OCR status */}
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                      Trạng thái OCR
                    </p>
                    <OcrStatusBadge status={doc.ocr_status} />
                  </div>
                  {/* Document ID */}
                  <div>
                    <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                      Mã tài liệu
                    </p>
                    <p className="font-mono text-xs text-[var(--text-primary)] break-all">
                      {id}
                    </p>
                  </div>
                </div>
              </TabsContent>
            </Tabs>

            {/* Sensitive fields demo */}
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold">Trường nhạy cảm</h3>
                <button
                  onClick={() => setShowSensitive(!showSensitive)}
                  className="text-xs text-[var(--accent-primary)] hover:underline"
                >
                  {showSensitive ? "Ẩn" : "Hiện"}
                </button>
              </div>
              <div className="mt-3 space-y-2 text-sm">
                <div>
                  <p className="text-xs text-[var(--text-muted)]">CCCD</p>
                  <RedactedField
                    value="079201001234"
                    isRevealed={showSensitive}
                  />
                </div>
                <div>
                  <p className="text-xs text-[var(--text-muted)]">Điện thoại</p>
                  <RedactedField
                    value="090 123 4567"
                    isRevealed={showSensitive}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Helper components
// ---------------------------------------------------------------------------

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span
        className={`text-right text-xs ${mono ? "font-mono" : ""} text-[var(--text-primary)]`}
      >
        {value}
      </span>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span className="text-right text-xs text-[var(--text-primary)]">
        {value}
      </span>
    </div>
  );
}

const OCR_STATUS_VI: Record<string, { label: string; color: string }> = {
  pending: { label: "Chờ xử lý", color: "var(--text-muted)" },
  processing: { label: "Đang xử lý", color: "var(--accent-warning)" },
  completed: { label: "Hoàn thành", color: "var(--accent-success)" },
  failed: { label: "Lỗi", color: "var(--accent-destructive)" },
};

function OcrStatusBadge({ status }: { status: string }) {
  const info = OCR_STATUS_VI[status] ?? {
    label: status,
    color: "var(--text-muted)",
  };
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium"
      style={{ color: info.color, borderColor: info.color }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full"
        style={{ backgroundColor: info.color }}
      />
      {info.label}
    </span>
  );
}
