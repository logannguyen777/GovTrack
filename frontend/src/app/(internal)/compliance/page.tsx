"use client";

import { useState } from "react";
import { useCases } from "@/hooks/use-cases";
import { EmptyState } from "@/components/ui/empty-state";
import { SlaBadge } from "@/components/cases/sla-badge";
import { useRouter } from "next/navigation";
import { AlertTriangle, ShieldCheck, Filter, RefreshCw } from "lucide-react";
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

// Statuses that are relevant for compliance review
const COMPLIANCE_STATUSES = new Set([
  "gap_checking",
  "legal_review",
  "leader_review",
  "pending_supplement",
  "consultation",
  "drafting",
  "submitted",
  "classifying",
  "extracting",
]);

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
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

export default function CompliancePage() {
  const { data, isLoading, error, refetch } = useCases();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "overdue" | "active">("all");

  const allCases = data?.items ?? [];

  // Only show cases relevant to compliance workflow
  const complianceCases = allCases.filter((c) =>
    COMPLIANCE_STATUSES.has(c.status),
  );

  const filtered = complianceCases.filter((c) => {
    const matchSearch =
      !search ||
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.applicant_name.toLowerCase().includes(search.toLowerCase()) ||
      c.tthc_code.toLowerCase().includes(search.toLowerCase());

    const matchStatus =
      statusFilter === "all"
        ? true
        : statusFilter === "overdue"
          ? c.is_overdue
          : !c.is_overdue;

    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          Kiểm tra tuân thủ
        </h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Danh sách hồ sơ cần kiểm tra tính hợp lệ theo quy định pháp luật
        </p>
      </div>

      {/* Filters row */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm theo mã hồ sơ, tên, TTHC..."
          aria-label="Tìm kiếm hồ sơ"
          className="w-56 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-[var(--accent-primary)]"
        />
        <div className="flex gap-1" role="group" aria-label="Lọc theo trạng thái SLA">
          {(
            [
              { key: "all", label: "Tất cả" },
              { key: "active", label: "Trong hạn" },
              { key: "overdue", label: "Quá hạn" },
            ] as const
          ).map((f) => (
            <button
              key={f.key}
              onClick={() => setStatusFilter(f.key)}
              aria-pressed={statusFilter === f.key}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                statusFilter === f.key
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
            {filtered.length} / {complianceCases.length} hồ sơ
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
          <AlertTriangle className="h-5 w-5 shrink-0 text-[var(--accent-error)]" aria-hidden="true" />
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
              {["Mã hồ sơ", "Người nộp", "TTHC", "Trạng thái", "Ngày nộp"].map(
                (h) => (
                  <div
                    key={h}
                    className="h-3 animate-pulse rounded bg-[var(--bg-surface-raised)]"
                  />
                ),
              )}
            </div>
          </div>
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="border-b border-[var(--border-subtle)] px-4 py-3.5 last:border-b-0"
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
              icon={ShieldCheck}
              title="Chưa có hồ sơ nào cần kiểm tra tuân thủ"
              description={
                search || statusFilter !== "all"
                  ? "Không tìm thấy hồ sơ phù hợp với bộ lọc đang chọn."
                  : "Hồ sơ sẽ xuất hiện tại đây khi được chuyển đến bước kiểm tra."
              }
            />
          ) : (
            <div
              className="overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
              role="region"
              aria-label="Danh sách hồ sơ kiểm tra tuân thủ"
            >
              {/* Table header */}
              <div className="grid grid-cols-[1fr_1.4fr_1fr_1.2fr_1fr_auto] items-center gap-4 border-b border-[var(--border-subtle)] px-4 py-2.5">
                {[
                  "Mã hồ sơ",
                  "Người nộp",
                  "Mã TTHC",
                  "Trạng thái",
                  "Ngày nộp",
                  "SLA",
                ].map((h) => (
                  <span
                    key={h}
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
                  const deadline = computeDeadline(c);

                  return (
                    <li key={c.case_id}>
                      <button
                        onClick={() =>
                          router.push(`/compliance/${c.case_id}`)
                        }
                        aria-label={`Xem kiểm tra tuân thủ hồ sơ ${c.code} — ${c.applicant_name}`}
                        className={`grid w-full grid-cols-[1fr_1.4fr_1fr_1.2fr_1fr_auto] items-center gap-4 px-4 py-3.5 text-left transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)] ${
                          idx !== filtered.length - 1
                            ? "border-b border-[var(--border-subtle)]"
                            : ""
                        } ${c.is_overdue ? "bg-[var(--accent-error)]/5" : ""}`}
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

                        {/* Status */}
                        <span
                          className="flex items-center gap-1.5 text-xs font-medium"
                          style={{ color: statusColor }}
                        >
                          <span
                            aria-hidden="true"
                            className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                            style={{ backgroundColor: statusColor }}
                          />
                          {statusLabel}
                        </span>

                        {/* Submitted date */}
                        <span className="font-mono text-xs text-[var(--text-secondary)]">
                          {formatDate(c.submitted_at)}
                        </span>

                        {/* SLA badge */}
                        <SlaBadge deadline={deadline} />
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
