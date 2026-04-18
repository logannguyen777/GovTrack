"use client";

import { useState, useCallback } from "react";
import { useCases } from "@/hooks/use-cases";
import { EmptyState } from "@/components/ui/empty-state";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import {
  AlertTriangle,
  FolderOpen,
  Filter,
  RefreshCw,
  Info,
  ChevronRight,
  Loader2,
  Sparkles,
} from "lucide-react";
import type { CaseResponse, DocumentResponse } from "@/lib/types";

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

const DEPT_LABEL: Record<string, string> = {
  "DEPT-QLDT": "Quản lý đất đai",
  "DEPT-TNMT": "Tài nguyên môi trường",
  "DEPT-PHAPCHE": "Pháp chế",
  "DEPT-HAICHUAN": "Hải quan",
  "DEPT-THUEVIEN": "Thuế vụ",
};

function formatDate(iso: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(iso));
}

function deptName(id: string): string {
  return DEPT_LABEL[id] ?? id;
}

export default function DocumentsPage() {
  const { data, isLoading, error, refetch } = useCases();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("all");
  const [navigatingId, setNavigatingId] = useState<string | null>(null);

  /** Navigate to the first document of a case. Falls back to /trace if no documents. */
  const handleRowClick = useCallback(
    async (c: CaseResponse) => {
      setNavigatingId(c.case_id);
      try {
        const docs = await apiClient.get<DocumentResponse[]>(
          `/api/cases/${c.case_id}/documents`,
        );
        if (docs && docs.length > 0) {
          router.push(`/documents/${docs[0].doc_id}`);
        } else {
          // No documents yet — fall through to trace
          router.push(`/trace/${c.case_id}`);
        }
      } catch {
        // API error — best effort fallback
        router.push(`/trace/${c.case_id}`);
      } finally {
        setNavigatingId(null);
      }
    },
    [router],
  );

  const allCases: CaseResponse[] = data?.items ?? [];

  // Collect unique department IDs for the filter
  const departments = Array.from(new Set(allCases.map((c) => c.department_id)));

  const filtered = allCases.filter((c) => {
    const matchSearch =
      !search ||
      c.code.toLowerCase().includes(search.toLowerCase()) ||
      c.applicant_name.toLowerCase().includes(search.toLowerCase());
    const matchDept =
      deptFilter === "all" || c.department_id === deptFilter;
    return matchSearch && matchDept;
  });

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Quản lý tài liệu
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Tổng hợp tài liệu đính kèm của các hồ sơ thủ tục hành chính
          </p>
        </div>
        <button
          type="button"
          onClick={() => router.push("/trace/CASE-2026-0001")}
          className="flex shrink-0 items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-600 to-violet-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
          title="Mở hồ sơ CPXD mẫu có đầy đủ tài liệu và gap PCCC"
        >
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Xem case mẫu
        </button>
      </div>

      {/* Guidance banner */}
      <div className="flex items-start gap-3 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/5 px-4 py-3">
        <Info
          className="mt-0.5 h-4 w-4 shrink-0 text-[var(--accent-primary)]"
          aria-hidden="true"
        />
        <p className="text-sm text-[var(--text-secondary)]">
          Chọn hồ sơ để xem tài liệu đính kèm. Tài liệu được quản lý theo
          từng hồ sơ.
        </p>
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
          placeholder="Tìm theo mã hồ sơ hoặc tên người nộp..."
          aria-label="Tìm kiếm hồ sơ"
          className="w-64 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-[var(--accent-primary)]"
        />
        {departments.length > 0 && (
          <select
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
            aria-label="Lọc theo phòng ban"
            className="rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-2.5 py-1.5 text-xs outline-none transition-colors focus:border-[var(--accent-primary)]"
          >
            <option value="all">Tất cả phòng ban</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {deptName(d)}
              </option>
            ))}
          </select>
        )}
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
            <div className="grid grid-cols-4 gap-4">
              {["Mã hồ sơ", "Người nộp", "Trạng thái", "Phòng ban"].map(
                (h) => (
                  <div
                    key={h}
                    className="h-3 animate-pulse rounded bg-[var(--bg-surface-raised)]"
                  />
                ),
              )}
            </div>
          </div>
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="border-b border-[var(--border-subtle)] px-4 py-4 last:border-b-0"
            >
              <div className="grid grid-cols-4 gap-4">
                {[...Array(4)].map((__, j) => (
                  <div
                    key={j}
                    className="h-4 animate-pulse rounded bg-[var(--bg-surface-raised)]"
                    style={{ animationDelay: `${(i * 4 + j) * 30}ms` }}
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
              icon={FolderOpen}
              title="Chưa có tài liệu nào trong hệ thống"
              description={
                search || deptFilter !== "all"
                  ? "Không tìm thấy hồ sơ phù hợp với bộ lọc đang chọn."
                  : "Tài liệu đính kèm sẽ xuất hiện tại đây khi hồ sơ được nộp vào hệ thống."
              }
            />
          ) : (
            <div
              className="overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
              role="region"
              aria-label="Danh sách hồ sơ có tài liệu"
            >
              {/* Table header */}
              <div className="grid grid-cols-[1fr_1.4fr_1.1fr_1.2fr_auto_auto] items-center gap-4 border-b border-[var(--border-subtle)] px-4 py-2.5">
                {[
                  "Mã hồ sơ",
                  "Người nộp",
                  "Trạng thái",
                  "Phòng ban",
                  "Mật",
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

                  return (
                    <li key={c.case_id}>
                      <button
                        onClick={() => handleRowClick(c)}
                        disabled={navigatingId === c.case_id}
                        aria-label={`Xem tài liệu hồ sơ ${c.code} — ${c.applicant_name}`}
                        className={`grid w-full grid-cols-[1fr_1.4fr_1.1fr_1.2fr_auto_auto] items-center gap-4 px-4 py-4 text-left transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)] disabled:opacity-60 ${
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

                        {/* Department */}
                        <span className="truncate text-xs text-[var(--text-secondary)]">
                          {deptName(c.department_id)}
                        </span>

                        {/* Classification badge */}
                        <ClassificationBadge level="unclassified" />

                        {/* Chevron / spinner */}
                        {navigatingId === c.case_id ? (
                          <Loader2
                            className="h-4 w-4 animate-spin text-[var(--accent-primary)]"
                            aria-hidden="true"
                          />
                        ) : (
                          <ChevronRight
                            className="h-4 w-4 text-[var(--text-muted)]"
                            aria-hidden="true"
                          />
                        )}
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
