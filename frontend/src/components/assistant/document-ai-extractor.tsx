"use client";

import * as React from "react";
import { Sparkles, Pencil, Check, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExtractResponse } from "@/hooks/use-document-extract";
import type { Entity } from "@/lib/types";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DocumentAIExtractorProps {
  file: File;
  tthcHint?: string;
  onExtracted: (result: ExtractResponse) => void;
  onReject: () => void;
  /** Pass the mutation result externally so the bubble can manage state */
  extractResult?: ExtractResponse | null;
  isExtracting: boolean;
  extractError?: string | null;
}

// ---------------------------------------------------------------------------
// Confidence bar
// ---------------------------------------------------------------------------

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const colorClass =
    value >= 0.9
      ? "bg-[var(--accent-success)]"
      : value >= 0.7
        ? "bg-[var(--accent-warning)]"
        : "bg-[var(--accent-destructive)]";
  const textColor =
    value >= 0.9
      ? "text-[var(--accent-success)]"
      : value >= 0.7
        ? "text-[var(--accent-warning)]"
        : "text-[var(--accent-destructive)]";

  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-12 overflow-hidden rounded-full bg-[var(--bg-subtle)]">
        <div
          className={cn("h-full rounded-full transition-all duration-500", colorClass)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={cn("text-[10px] font-medium tabular-nums", textColor)}>
        {pct}%
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable entity row
// ---------------------------------------------------------------------------

function EntityRow({
  entity,
  onChange,
}: {
  entity: Entity;
  onChange: (key: string, value: unknown) => void;
}) {
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(String(entity.value ?? ""));
  const inputRef = React.useRef<HTMLInputElement>(null);

  const LABELS: Record<string, string> = {
    applicant_name: "Họ tên",
    applicant_id_number: "CCCD",
    date_of_birth: "Ngày sinh",
    applicant_address: "Địa chỉ",
    gender: "Giới tính",
    nationality: "Quốc tịch",
    place_of_origin: "Quê quán",
    expiry_date: "Ngày hết hạn",
    applicant_phone: "Điện thoại",
  };

  function confirm() {
    onChange(entity.key, draft);
    setEditing(false);
  }

  React.useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  return (
    <div className="flex items-center gap-2 py-1.5 border-b border-[var(--border-subtle)] last:border-0">
      <span className="w-24 shrink-0 text-xs text-[var(--text-muted)]">
        {LABELS[entity.key] ?? entity.key}
      </span>
      <div className="flex-1 min-w-0">
        {editing ? (
          <div className="flex items-center gap-1">
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") confirm();
                if (e.key === "Escape") setEditing(false);
              }}
              className="flex-1 min-w-0 rounded border border-[var(--accent-primary)] bg-[var(--bg-app)] px-2 py-0.5 text-xs outline-none focus:ring-1 focus:ring-[var(--accent-primary)]"
            />
            <button
              type="button"
              onClick={confirm}
              aria-label="Lưu"
              className="rounded p-0.5 hover:bg-[var(--accent-success)]/10"
            >
              <Check size={12} className="text-[var(--accent-success)]" />
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              aria-label="Hủy"
              className="rounded p-0.5 hover:bg-[var(--accent-destructive)]/10"
            >
              <X size={12} className="text-[var(--accent-destructive)]" />
            </button>
          </div>
        ) : (
          <span className="text-xs font-medium text-[var(--text-primary)] truncate block">
            {String(entity.value ?? "—")}
          </span>
        )}
      </div>
      <ConfidenceBar value={entity.confidence} />
      {!editing && (
        <button
          type="button"
          onClick={() => { setDraft(String(entity.value ?? "")); setEditing(true); }}
          aria-label={`Sửa ${LABELS[entity.key] ?? entity.key}`}
          className="shrink-0 rounded p-0.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
        >
          <Pencil size={12} />
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function DocumentAIExtractor({
  file,
  onExtracted,
  onReject,
  extractResult,
  isExtracting,
  extractError,
}: DocumentAIExtractorProps) {
  const [entities, setEntities] = React.useState<Entity[]>([]);
  const [objectUrl, setObjectUrl] = React.useState<string | null>(null);

  // Create object URL for preview
  React.useEffect(() => {
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setObjectUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [file]);

  // Sync entities when result arrives
  React.useEffect(() => {
    if (extractResult?.entities) {
      setEntities(extractResult.entities);
    }
  }, [extractResult]);

  function handleEntityChange(key: string, value: unknown) {
    setEntities((prev) =>
      prev.map((e) => (e.key === key ? { ...e, value } : e)),
    );
  }

  function handleUse() {
    if (!extractResult) return;
    onExtracted({ ...extractResult, entities });
  }

  return (
    <div
      className="rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] overflow-hidden"
      role="region"
      aria-label="Trích xuất tài liệu AI"
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2"
        style={{ background: "var(--gradient-qwen-soft)" }}
      >
        <Sparkles size={14} className="text-purple-600 shrink-0" />
        <span className="text-xs font-semibold text-[var(--text-primary)]">
          Qwen3-VL đang đọc tài liệu
        </span>
        <span className="text-xs text-[var(--text-muted)] truncate max-w-[120px]">
          · {file.name}
        </span>
      </div>

      {/* Content */}
      <div className="p-3">
        {/* Loading */}
        {isExtracting && (
          <div className="space-y-2">
            {/* Progress shimmer */}
            <div className="flex items-center gap-2">
              <Loader2 size={14} className="animate-spin text-purple-600 shrink-0" />
              <span className="text-xs text-[var(--text-secondary)]">
                AI đang đọc tài liệu... Sử dụng Qwen3-VL
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[var(--bg-subtle)] overflow-hidden">
              <div
                className="h-full rounded-full animate-pulse"
                style={{ background: "var(--gradient-qwen)", width: "60%" }}
              />
            </div>
            {/* Skeleton rows */}
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex gap-2 items-center">
                <div className="w-20 h-3 rounded bg-[var(--bg-subtle)] animate-pulse" />
                <div className="flex-1 h-3 rounded bg-[var(--bg-subtle)] animate-pulse" />
                <div className="w-12 h-2 rounded bg-[var(--bg-subtle)] animate-pulse" />
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {extractError && !isExtracting && (
          <div className="flex items-center gap-2 py-2">
            <X size={14} className="text-[var(--accent-destructive)] shrink-0" />
            <p className="text-xs text-[var(--accent-destructive)]">{extractError}</p>
            <button
              type="button"
              onClick={onReject}
              className="ml-auto text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] underline"
            >
              Bỏ qua
            </button>
          </div>
        )}

        {/* Result */}
        {extractResult && !isExtracting && entities.length > 0 && (
          <div className="space-y-0">
            {/* Thumbnail */}
            {objectUrl && (
              <div className="mb-2 flex justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={objectUrl}
                  alt="Xem trước tài liệu"
                  className="max-h-24 rounded-lg object-cover border border-[var(--border-subtle)]"
                />
              </div>
            )}

            {/* Entity list */}
            <div className="divide-y divide-transparent">
              {entities.map((entity) => (
                <EntityRow
                  key={entity.key}
                  entity={entity}
                  onChange={handleEntityChange}
                />
              ))}
            </div>

            {/* Actions */}
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                onClick={handleUse}
                className="flex-1 rounded-lg py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
                style={{ background: "var(--gradient-qwen)" }}
              >
                Dùng thông tin này
              </button>
              <button
                type="button"
                onClick={onReject}
                className="rounded-lg border border-[var(--border-default)] px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] transition-colors"
              >
                Bỏ qua
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
