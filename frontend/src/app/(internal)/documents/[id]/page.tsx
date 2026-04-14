"use client";

import { use, useState } from "react";
import { useDocument, useDocumentUrl } from "@/hooks/use-documents";
import { RedactedField } from "@/components/ui/redacted-field";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Download, ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

export default function DocumentViewer({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: doc, isLoading } = useDocument(id);
  const { data: urlData } = useDocumentUrl(id);
  const [showSensitive, setShowSensitive] = useState(false);
  const router = useRouter();

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
    <div className="flex h-full flex-col gap-4">
      {/* Back button */}
      <div>
        <button
          onClick={() => router.back()}
          className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] transition-colors hover:text-[var(--text-primary)]"
          aria-label="Quay lại trang trước"
        >
          <ArrowLeft className="h-4 w-4" />
          Quay lại
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
        </div>

        {/* PDF/Image preview area */}
        <div className="flex min-h-[600px] items-center justify-center p-8">
          {urlData?.signed_url ? (
            doc.content_type?.startsWith("image/") ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={urlData.signed_url}
                alt={doc.filename}
                className="max-h-[80vh] max-w-full rounded-md"
              />
            ) : (
              <div className="text-center">
                <FileText className="mx-auto h-16 w-16 text-[var(--text-muted)]" />
                <p className="mt-4 text-sm text-[var(--text-secondary)]">
                  Xem trước PDF
                </p>
                <a
                  href={urlData.signed_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-2 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
                >
                  <Download className="h-4 w-4" />
                  Tải xuống
                </a>
              </div>
            )
          ) : (
            <div className="text-center text-sm text-[var(--text-muted)]">
              <FileText className="mx-auto h-16 w-16" />
              <p className="mt-4">Đang tải URL tài liệu...</p>
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

          <TabsContent value="summary" className="mt-3">
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <p className="text-sm leading-relaxed text-[var(--text-muted)]">
                Chưa có tóm tắt. Hồ sơ chưa được xử lý bởi agent AI. Tóm tắt tự động sẽ xuất hiện tại đây sau khi hệ thống phân tích xong tài liệu.
              </p>
            </div>
          </TabsContent>

          <TabsContent value="entities" className="mt-3">
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <p className="text-sm leading-relaxed text-[var(--text-muted)]">
                Chưa có thực thể được trích xuất. Sau khi agent AI xử lý tài liệu, các thông tin quan trọng (tên, địa chỉ, số CCCD, ngày tháng...) sẽ được hiển thị tại đây.
              </p>
            </div>
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
                    value={doc.page_count != null ? String(doc.page_count) : "Chưa xác định"}
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
  );
}

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
      <span className="text-right text-xs text-[var(--text-primary)]">{value}</span>
    </div>
  );
}

const OCR_STATUS_VI: Record<string, { label: string; color: string }> = {
  pending:    { label: "Chờ xử lý",    color: "var(--text-muted)" },
  processing: { label: "Đang xử lý",   color: "var(--accent-warning)" },
  completed:  { label: "Hoàn thành",   color: "var(--accent-success)" },
  failed:     { label: "Lỗi",          color: "var(--accent-destructive)" },
};

function OcrStatusBadge({ status }: { status: string }) {
  const info = OCR_STATUS_VI[status] ?? { label: status, color: "var(--text-muted)" };
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
