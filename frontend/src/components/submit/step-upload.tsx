"use client";

import * as React from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, X, Sparkles } from "lucide-react";
import { useDocumentExtract } from "@/hooks/use-document-extract";
import { useSubmitFormStore } from "@/lib/stores/submit-form-store";
import { DocumentAIExtractor } from "@/components/assistant/document-ai-extractor";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import type { ExtractResponse } from "@/hooks/use-document-extract";

export interface UploadFile {
  file: File;
  id: string;
}

interface StepUploadProps {
  tthcCode: string;
  files: UploadFile[];
  onFilesChange: (files: UploadFile[]) => void;
}

interface ExtractorState {
  file: File;
  isExtracting: boolean;
  result?: ExtractResponse;
  error?: string;
  dismissed: boolean;
}

export function StepUpload({ tthcCode, files, onFilesChange }: StepUploadProps) {
  const setFromExtraction = useSubmitFormStore((s) => s.setFromExtraction);
  const extractMutation = useDocumentExtract();
  const [extractorState, setExtractorState] = React.useState<ExtractorState | null>(
    null,
  );

  const onDrop = React.useCallback(
    async (accepted: File[]) => {
      const newFiles: UploadFile[] = accepted.map((f) => ({
        file: f,
        id: crypto.randomUUID(),
      }));
      onFilesChange([...files, ...newFiles]);

      // Auto-trigger extraction for image files (CCCD etc.)
      const imageFile = accepted.find((f) => f.type.startsWith("image/"));
      if (imageFile) {
        setExtractorState({ file: imageFile, isExtracting: true, dismissed: false });
        try {
          const result = await extractMutation.mutateAsync({
            file: imageFile,
            tthcCode,
          });
          setExtractorState((prev) =>
            prev ? { ...prev, isExtracting: false, result } : null,
          );
        } catch (err) {
          setExtractorState((prev) =>
            prev
              ? { ...prev, isExtracting: false, error: (err as Error).message }
              : null,
          );
        }
      }
    },
    [files, onFilesChange, extractMutation, tthcCode],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".jpg", ".jpeg", ".png"],
    },
  });

  function handleExtracted(result: ExtractResponse) {
    setFromExtraction(result.entities);
    setExtractorState((prev) => (prev ? { ...prev, dismissed: true } : null));
  }

  function handleReject() {
    setExtractorState((prev) => (prev ? { ...prev, dismissed: true } : null));
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-[var(--text-primary)]">
        Tải tài liệu
      </h2>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">
        Tải lên các tài liệu cần thiết. Ảnh CCCD sẽ được AI tự động trích xuất
        thông tin.
      </p>

      {/* HelpHintBanner for AI fill */}
      <div className="mt-3">
        <HelpHintBanner id="submit-ai-fill" variant="tip">
          Tải lên ảnh CCCD — <strong>Qwen3-VL</strong> sẽ tự động điền họ tên, số CCCD, ngày sinh. Bạn chỉ cần kiểm tra lại.
        </HelpHintBanner>
      </div>

      {/* AI extract hint */}
      <div
        className="mt-3 flex items-center gap-2 rounded-lg border px-3 py-2"
        style={{
          background: "var(--gradient-qwen-soft)",
          borderColor: "oklch(0.65 0.15 280 / 0.25)",
        }}
      >
        <Sparkles size={12} className="shrink-0 text-purple-600" />
        <p className="text-xs text-[var(--text-secondary)]">
          Tải ảnh CCCD lên để AI (Qwen3-VL) tự điền thông tin công dân
        </p>
      </div>

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

      {/* Extractor card */}
      {extractorState && !extractorState.dismissed && (
        <div className="mt-3">
          <DocumentAIExtractor
            file={extractorState.file}
            tthcHint={tthcCode}
            extractResult={extractorState.result ?? null}
            isExtracting={extractorState.isExtracting}
            extractError={extractorState.error}
            onExtracted={handleExtracted}
            onReject={handleReject}
          />
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-3 space-y-1">
          {files.map((f) => (
            <div
              key={f.id}
              className="flex items-center justify-between rounded-md border border-[var(--border-subtle)] px-3 py-1.5 text-sm"
            >
              <div className="flex items-center gap-2">
                <FileText className="h-3 w-3 text-[var(--text-muted)]" />
                <span className="truncate max-w-xs text-[var(--text-primary)]">
                  {f.file.name}
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  onFilesChange(files.filter((x) => x.id !== f.id))
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
  );
}
