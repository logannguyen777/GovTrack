"use client";

import { useState } from "react";
import { useCases } from "@/hooks/use-cases";
import { EmptyState } from "@/components/ui/empty-state";
import { SlaBadge } from "@/components/cases/sla-badge";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  BotMessageSquare,
  Filter,
  RefreshCw,
  ChevronRight,
  Activity,
} from "lucide-react";
import type { CaseResponse } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = {
  submitted: "Đã nộp",
  classifying: "Phân loại",
  extracting: "Trích xuất",
  gap_checking: "Kiểm tra khoảng trống",
  pending_supplement: "Chờ bổ sung",
  legal_review: "Xem xét pháp lý",
  drafting: "Soạn thảo",
  leader_review: "Chờ lãnh đạo duyệt",
  consultation: "Đang tham vấn",
  approved: "Đã phê duyệt",
  rejected: "Đã từ chối",
  published: "Đã ban hành",
};

const STATUS_COLOR: Record<string, string> = {
  submitted: "var(--accent-primary)",
  classifying: "var(--accent-info)",
  extracting: "var(--accent-info)",
  gap_checking: "var(--accent-warning)",
  pending_supplement: "var(--accent-warning)",
  legal_review: "var(--accent-primary)",
  drafting: "var(--accent-primary)",
  leader_review: "var(--accent-warning)",
  consultation: "var(--accent-warning)",
  approved: "var(--accent-success)",
  rejected: "var(--accent-error)",
  published: "var(--accent-success)",
};

// Statuses that indicate active or completed AI pipeline processing
const PIPELINE_ACTIVE_STATUSES = new Set([
  "classifying",
  "extracting",
  "gap_checking",
  "legal_review",
  "drafting",
  "consultation",
]);

const PIPELINE_DONE_STATUSES = new Set([
  "leader_review",
  "approved",
  "rejected",
  "published",
]);

function pipelineInfo(status: string): {
  label: string;
  color: string;
  pulse: boolean;
} {
  if (PIPELINE_ACTIVE_STATUSES.has(status)) {
    return {
      label: "Đang chạy",
      color: "var(--accent-info)",
      pulse: true,
    };
  }
  if (PIPELINE_DONE_STATUSES.has(status)) {
    return {
      label: "Hoàn thành",
      color: "var(--accent-success)",
      pulse: false,
    };
  }
  if (status === "pending_supplement") {
    return {
      label: "Tạm dừng",
      color: "var(--accent-warning)",
      pulse: false,
    };
  }
  // submitted or unknown — waiting
  return {
    label: "Chờ khởi chạy",
    color: "var(--text-muted)",
    pulse: false,
  };
}

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function computeDeadline(c: CaseResponse): string {
  if (c.sla_days) {
    return new Date(
      new Date(c.submitted_at).getTime() + c.sla_days * 86_400_000,
    ).toISOString();
  }
  return new Date(Date.now() + 7 * 86_400_000).toISOString();
}

type PipelineFilter = "all" | "running" | "done" | "waiting";

export default function TracePage() {
  const { data, isLoading, error, refetch } = useCases();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [pipelineFilter, setPipelineFilter] =
    useState<PipelineFilter>("all");

  const allCases: CaseResponse[] = data?.items ?? [];

  const filtered = allCases.filter((c) => {
    const matchSearch =
      !search ||
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.applicant_name.toLowerCase().includes(search.toLowerCase()) ||
      c.tthc_code.toLowerCase().includes(search.toLowerCase());

    const info = pipelineInfo(c.status);
    const matchPipeline =
      pipelineFilter === "all"
        ? true
        : pipelineFilter === "running"
          ? info.label === "Đang chạy"
          : pipelineFilter === "done"
            ? info.label === "Hoàn thành"
            : info.label === "Chờ khởi chạy" || info.label === "Tạm dừng";

    return matchSearch && matchPipeline;
  });

  const runningCount = allCases.filter(
    (c) => PIPELINE_ACTIVE_STATUSES.has(c.status),
  ).length;

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Theo dõi xử lý AI
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Quá trình xử lý tự động của các agent AI cho từng hồ sơ
          </p>
        </div>

        {/* Live pipeline indicator */}
        <div className="flex items-center gap-2">
          {runningCount > 0 && (
            <div className="flex shrink-0 items-center gap-2 rounded-full border border-[var(--accent-info)]/40 bg-[var(--accent-info)]/10 px-3 py-1.5">
              <span
                aria-hidden="true"
                className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--accent-info)]"
              />
              <span className="text-xs font-medium text-[var(--accent-info)]">
                {runningCount} pipeline đang chạy
              </span>
            </div>
          )}

          {/* Demo hero case shortcut for judges */}
          <button
            type="button"
            onClick={() => router.push("/trace/CASE-2026-0001")}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-purple-300 bg-gradient-to-r from-purple-50 to-violet-50 px-3 py-1.5 text-xs font-medium text-purple-700 hover:opacity-90 dark:border-purple-700 dark:from-purple-950 dark:to-violet-950 dark:text-purple-200"
            title="Mở hồ sơ CPXD mẫu đã có đầy đủ trace + gap + citation"
          >
            <BotMessageSquare size={12} />
            Xem case mẫu CPXD
          </button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter
          className="h-4 w-4 shrink-0 text-[var(--text-muted)]"
          aria-hidden="true"
        />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm theo mã hồ sơ, tên, TTHC..."
          aria-label="Tìm kiếm hồ sơ"
          className="w-56 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-[var(--accent-primary)]"
        />
        <div
          className="flex gap-1"
          role="group"
          aria-label="Lọc theo trạng thái pipeline"
        >
          {(
            [
              { key: "all", label: "Tất cả" },
              { key: "running", label: "Đang chạy" },
              { key: "done", label: "Hoàn thành" },
              { key: "waiting", label: "Chờ / Tạm dừng" },
            ] as const
          ).map((f) => (
            <button
              key={f.key}
              onClick={() => setPipelineFilter(f.key)}
              aria-pressed={pipelineFilter === f.key}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                pipelineFilter === f.key
                  ? "bg-[var(--accent-primary)] text-white"
                  : "bg-[var(--bg-surface-raised)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        {!isLoading && (
          <span className="ml-auto text-xs text-[var(--text-muted)]">
            {filtered.length} / {allCases.length} hồ sơ
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
          <AlertTriangle
            className="h-5 w-5 shrink-0 text-[var(--accent-error)]"
            aria-hidden="true"
          />
          <div className="flex-1">
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Không thể tải danh sách hồ sơ
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              {(error as Error).message ?? "Lỗi không xác định"}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            <RefreshCw className="h-3 w-3" aria-hidden="true" />
            Thử lại
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <div className="border-b border-[var(--border-subtle)] px-4 py-3">
            <div className="grid grid-cols-5 gap-4">
              {[
                "Mã hồ sơ",
                "Người nộp",
                "TTHC",
                "Trạng thái xử lý",
                "Thời gian nộp",
              ].map((h) => (
                <div
                  key={h}
                  className="h-3 animate-pulse rounded bg-[var(--bg-surface-raised)]"
                />
              ))}
            </div>
          </div>
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="border-b border-[var(--border-subtle)] px-4 py-4 last:border-b-0"
            >
              <div className="grid grid-cols-5 gap-4">
                {[...Array(5)].map((__, j) => (
                  <div
                    key={j}
                    className="h-4 animate-pulse rounded bg-[var(--bg-surface-raised)]"
                    style={{ animationDelay: `${(i * 5 + j) * 30}ms` }}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Data table */}
      {!isLoading && !error && (
        <>
          {filtered.length === 0 ? (
            <EmptyState
              icon={BotMessageSquare}
              title="Chưa có pipeline nào được khởi chạy"
              description={
                search || pipelineFilter !== "all"
                  ? "Không tìm thấy hồ sơ phù hợp với bộ lọc đang chọn."
                  : "Pipeline AI sẽ xuất hiện tại đây khi hồ sơ được xử lý."
              }
            />
          ) : (
            <div
              className="overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
              role="region"
              aria-label="Danh sách pipeline xử lý AI"
            >
              {/* Table header */}
              <div className="grid grid-cols-[1fr_1.4fr_0.9fr_1.1fr_1.2fr_1fr_auto] items-center gap-4 border-b border-[var(--border-subtle)] px-4 py-2.5">
                {[
                  "Mã hồ sơ",
                  "Người nộp",
                  "TTHC",
                  "Pipeline",
                  "Trạng thái",
                  "SLA",
                  "",
                ].map((h, i) => (
                  <span
                    key={i}
                    className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]"
                  >
                    {h}
                  </span>
                ))}
              </div>

              {/* Table rows */}
              <ul role="list">
                {filtered.map((c, idx) => {
                  const statusLabel = STATUS_LABEL[c.status] ?? c.status;
                  const statusColor =
                    STATUS_COLOR[c.status] ?? "var(--text-secondary)";
                  const pipeline = pipelineInfo(c.status);
                  const deadline = computeDeadline(c);

                  return (
                    <li key={c.case_id}>
                      <button
                        onClick={() => router.push(`/trace/${c.case_id}`)}
                        aria-label={`Xem trace AI hồ sơ ${c.code} — ${c.applicant_name}`}
                        className={`grid w-full grid-cols-[1fr_1.4fr_0.9fr_1.1fr_1.2fr_1fr_auto] items-center gap-4 px-4 py-3.5 text-left transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)] ${
                          idx !== filtered.length - 1
                            ? "border-b border-[var(--border-subtle)]"
                            : ""
                        }`}
                      >
                        {/* Case code */}
                        <span className="font-mono text-[12px] font-medium text-[var(--text-primary)]">
                          {c.code}
                        </span>

                        {/* Applicant name */}
                        <span className="truncate text-sm text-[var(--text-primary)]">
                          {c.applicant_name}
                        </span>

                        {/* TTHC code */}
                        <span className="inline-flex w-fit items-center rounded border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">
                          {c.tthc_code}
                        </span>

                        {/* Pipeline status */}
                        <span
                          className="flex items-center gap-1.5 text-xs font-medium"
                          style={{ color: pipeline.color }}
                          aria-label={`Pipeline: ${pipeline.label}`}
                        >
                          {pipeline.pulse ? (
                            <Activity
                              className="h-3 w-3 animate-pulse"
                              aria-hidden="true"
                            />
                          ) : (
                            <span
                              aria-hidden="true"
                              className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                              style={{ backgroundColor: pipeline.color }}
                            />
                          )}
                          {pipeline.label}
                        </span>

                        {/* Case status */}
                        <span
                          className="flex items-center gap-1.5 text-xs"
                          style={{ color: statusColor }}
                        >
                          <span
                            aria-hidden="true"
                            className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                            style={{ backgroundColor: statusColor }}
                          />
                          {statusLabel}
                        </span>

                        {/* SLA badge */}
                        <SlaBadge deadline={deadline} />

                        {/* Chevron */}
                        <ChevronRight
                          className="h-4 w-4 text-[var(--text-muted)]"
                          aria-hidden="true"
                        />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
