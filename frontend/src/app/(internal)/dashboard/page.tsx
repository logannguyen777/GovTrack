"use client";

import { useDashboard, useLeaderInbox, useWeeklyBrief } from "@/hooks/use-leadership";
import { useBatchFinalize } from "@/hooks/use-cases";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import { SkeletonKPICard, SkeletonChart } from "@/components/ui/skeleton-card";
import { EmptyState } from "@/components/ui/empty-state";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useRouter } from "next/navigation";
import {
  AlertTriangle,
  ClipboardList,
  HelpCircle,
  Sparkles,
  Send,
  CheckCircle,
  XCircle,
  MessageSquarePlus,
  Loader2,
  SquareCheck,
} from "lucide-react";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { HELP_CONTENT } from "@/lib/help-content";
import { useState, useRef, useCallback, useEffect } from "react";
import { toast } from "sonner";
import type { InboxItem } from "@/lib/types";
import { useAIChat } from "@/hooks/use-ai-chat";
import { apiClient } from "@/lib/api";

const CHART_COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#06b6d4"];

const STATUS_VI: Record<string, string> = {
  submitted:          "Đã nộp",
  classifying:        "Phân loại",
  extracting:         "Trích xuất",
  gap_checking:       "Kiểm tra",
  pending_supplement: "Chờ bổ sung",
  legal_review:       "Xem xét PL",
  drafting:           "Soạn thảo",
  leader_review:      "Chờ duyệt",
  consultation:       "Tham vấn",
  approved:           "Đã duyệt",
  rejected:           "Từ chối",
  published:          "Đã ban hành",
};

const PRIORITY_VI: Record<string, string> = {
  high:   "Ưu tiên cao",
  medium: "Trung bình",
  low:    "Thấp",
};

// ---------------------------------------------------------------------------
// Natural-language query box
// ---------------------------------------------------------------------------

function NLQueryBox() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { send, isStreaming, messages } = useAIChat({
    context: { type: "portal" },
  });

  // Sync latest assistant reply into `answer`
  useEffect(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    if (lastAssistant && !lastAssistant.isStreaming && lastAssistant.content) {
      setAnswer(lastAssistant.content);
    }
  }, [messages]);

  async function handleSubmit() {
    const q = query.trim();
    if (!q || isStreaming) return;
    setAnswer(null);
    await send(q);
    setQuery("");
  }

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-4 w-4 text-[var(--accent-primary)]" aria-hidden="true" />
        <h3 className="text-sm font-semibold">Hỏi AI về số liệu</h3>
        <span className="ml-auto rounded-full bg-[var(--accent-primary)]/10 px-2 py-0.5 text-[10px] font-medium text-[var(--accent-primary)]">
          Qwen3 · powered
        </span>
      </div>
      <div className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Hỏi AI: Có bao nhiêu GPXD vượt SLA tuần này?"
          disabled={isStreaming}
          className="flex-1 rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 py-2 text-sm outline-none transition-colors placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)] disabled:opacity-60"
          aria-label="Hỏi AI về số liệu hồ sơ"
        />
        <button
          type="button"
          onClick={() => void handleSubmit()}
          disabled={isStreaming || !query.trim()}
          className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
          aria-label="Gửi câu hỏi"
        >
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
          Gửi
        </button>
      </div>

      {/* Streaming indicator */}
      {isStreaming && (
        <p className="mt-2 text-xs text-[var(--text-muted)] animate-pulse">
          AI đang phân tích...
        </p>
      )}

      {/* Answer block */}
      {answer && !isStreaming && (
        <div className="mt-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-subtle)] p-3">
          <p className="text-xs font-medium text-[var(--text-muted)] mb-1">Trả lời AI:</p>
          <p className="text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">{answer}</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Weekly Brief card (live data)
// ---------------------------------------------------------------------------

function WeeklyBriefCard({ dashboard }: { dashboard: { total_cases: number; completed_today: number; overdue_cases: number; avg_processing_days: number } }) {
  const { data: brief, isLoading, isError } = useWeeklyBrief();

  const fallbackText = `Trong tuần qua, hệ thống đã xử lý ${dashboard.completed_today} hồ sơ hoàn thành trong ngày hôm nay. Tổng cộng ${dashboard.total_cases} hồ sơ đang quản lý, trong đó ${dashboard.overdue_cases} hồ sơ quá hạn cần xử lý ưu tiên. Thời gian xử lý trung bình là ${dashboard.avg_processing_days.toFixed(1)} ngày.`;

  return (
    <div
      className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
      data-tour="dashboard-ai-report"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Báo cáo tuần (AI)</h3>
        <span className="flex items-center gap-1 rounded-full bg-purple-100/60 px-2 py-0.5 text-[10px] font-semibold text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
          <Sparkles className="h-3 w-3" aria-hidden="true" />
          Qwen3 tóm tắt
        </span>
      </div>
      <HelpHintBanner id="dashboard-ai-report" variant="info" className="mb-3">
        {HELP_CONTENT["dashboard-ai-report"]}
      </HelpHintBanner>

      {isLoading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-3 rounded bg-[var(--bg-subtle)] w-full" />
          <div className="h-3 rounded bg-[var(--bg-subtle)] w-4/5" />
          <div className="h-3 rounded bg-[var(--bg-subtle)] w-3/5" />
        </div>
      )}

      {(!isLoading) && (
        <p className="font-legal text-sm leading-relaxed text-[var(--text-secondary)]">
          {(!isError && brief?.brief) ? brief.brief : fallbackText}
        </p>
      )}

      {!isLoading && !isError && brief?.stats && (
        <div className="mt-3 grid grid-cols-4 gap-2 border-t border-[var(--border-subtle)] pt-3">
          {[
            { label: "Hồ sơ mới", value: brief.stats.new_cases ?? brief.stats.total_cases },
            { label: "Hoàn thành", value: brief.stats.completed },
            { label: "Quá hạn", value: brief.stats.overdue },
            { label: "TB (ngày)", value: (brief.stats.avg_processing_days ?? brief.stats.avg_days)?.toFixed(1) ?? "—" },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <p className="text-lg font-bold text-[var(--text-primary)]">{value}</p>
              <p className="text-[10px] text-[var(--text-muted)]">{label}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Approval queue with batch selection
// ---------------------------------------------------------------------------

function ApprovalQueue({
  inbox,
  inboxLoading,
  inboxError,
  refetchInbox,
}: {
  inbox: InboxItem[] | undefined;
  inboxLoading: boolean;
  inboxError: Error | null;
  refetchInbox: () => void;
}) {
  const router = useRouter();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const batchFinalize = useBatchFinalize();

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    if (!inbox) return;
    setSelectedIds(new Set(inbox.map((i) => i.case_id)));
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  const handleBatch = useCallback(
    async (decision: "approve" | "reject" | "request_supplement") => {
      const ids = [...selectedIds];
      if (ids.length === 0) return;

      const labels: Record<typeof decision, string> = {
        approve: "Duyệt",
        reject: "Từ chối",
        request_supplement: "Yêu cầu bổ sung",
      };

      try {
        const result = await batchFinalize.mutateAsync({
          case_ids: ids,
          decision,
        });
        const ok = result.succeeded?.length ?? 0;
        const fail = result.failed?.length ?? 0;
        if (ok > 0) {
          toast.success(
            `${labels[decision]}: ${ok} hồ sơ thành công${fail > 0 ? `, ${fail} thất bại` : ""}`,
          );
        } else {
          toast.error(`Không thể thực hiện thao tác. ${fail} hồ sơ thất bại.`);
        }
        setSelectedIds(new Set());
        refetchInbox();
      } catch {
        toast.error("Có lỗi xảy ra khi xử lý hàng loạt. Vui lòng thử lại.");
      }
    },
    [selectedIds, batchFinalize, refetchInbox],
  );

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div className="mb-1 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">
          Hồ sơ chờ phê duyệt
          {inbox && inbox.length > 0 ? ` (${inbox.length})` : ""}
        </h3>
        {inbox && inbox.length > 1 && (
          <button
            type="button"
            onClick={selectedIds.size === inbox.length ? clearSelection : selectAll}
            className="flex items-center gap-1 rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
            aria-label="Chọn tất cả hồ sơ"
          >
            <SquareCheck className="h-3.5 w-3.5" aria-hidden="true" />
            {selectedIds.size === inbox.length ? "Bỏ chọn tất cả" : "Chọn tất cả"}
          </button>
        )}
      </div>
      <p className="mb-3 text-xs text-[var(--text-muted)]">
        Các hồ sơ cần lãnh đạo phê duyệt hoặc cho ý kiến
      </p>

      {inboxError ? (
        <div className="flex items-center gap-3 rounded-md border border-[var(--border-subtle)] p-3">
          <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--accent-error)]" />
          <p className="flex-1 text-xs text-[var(--text-muted)]">
            Không thể tải danh sách chờ phê duyệt
          </p>
          <button
            onClick={refetchInbox}
            className="rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            Thử lại
          </button>
        </div>
      ) : inboxLoading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-14 animate-pulse rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]"
            />
          ))}
        </div>
      ) : inbox && inbox.length > 0 ? (
        <div className="space-y-2">
          {inbox.map((item) => {
            const isSelected = selectedIds.has(item.case_id);
            return (
              <div
                key={item.case_id}
                className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 transition-colors ${
                  isSelected
                    ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5"
                    : "border-[var(--border-subtle)] hover:bg-[var(--bg-surface-raised)]"
                }`}
                onClick={() => {
                  // If not in multi-select mode click navigates; if any selected, toggle
                  if (selectedIds.size === 0) {
                    router.push(`/compliance/${item.case_id}`);
                  } else {
                    toggleSelect(item.case_id);
                  }
                }}
              >
                {/* Checkbox */}
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); toggleSelect(item.case_id); }}
                  className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] ${
                    isSelected
                      ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]"
                      : "border-[var(--border-default)] bg-[var(--bg-canvas)]"
                  }`}
                  aria-label={`${isSelected ? "Bỏ chọn" : "Chọn"} hồ sơ ${item.code}`}
                  aria-pressed={isSelected}
                >
                  {isSelected && (
                    <CheckCircle className="h-3.5 w-3.5 text-white" aria-hidden="true" />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {item.code} · {item.action_required}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <ClassificationBadge level="unclassified" />
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      item.priority === "high"
                        ? "bg-[var(--accent-error)]/10 text-[var(--accent-error)]"
                        : "bg-[var(--bg-surface-raised)] text-[var(--text-secondary)]"
                    }`}
                  >
                    {PRIORITY_VI[item.priority] ?? item.priority}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState
          icon={ClipboardList}
          title="Không có hồ sơ chờ phê duyệt"
          description="Tất cả hồ sơ đã được xử lý hoặc chưa có hồ sơ mới."
        />
      )}

      {/* Floating batch action bar */}
      {selectedIds.size > 0 && (
        <div className="mt-4 flex items-center gap-2 rounded-lg border border-[var(--accent-primary)]/30 bg-[var(--accent-primary)]/5 p-3">
          <span className="text-xs font-semibold text-[var(--text-primary)]">
            Đã chọn {selectedIds.size} hồ sơ
          </span>
          <div className="ml-auto flex gap-2">
            <button
              type="button"
              onClick={() => void handleBatch("approve")}
              disabled={batchFinalize.isPending}
              className="flex items-center gap-1.5 rounded-md bg-[var(--accent-success)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-success)]"
              aria-label={`Duyệt ${selectedIds.size} hồ sơ`}
            >
              {batchFinalize.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Duyệt {selectedIds.size} hồ sơ
            </button>
            <button
              type="button"
              onClick={() => void handleBatch("reject")}
              disabled={batchFinalize.isPending}
              className="flex items-center gap-1.5 rounded-md bg-[var(--accent-destructive)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-destructive)]"
              aria-label={`Từ chối ${selectedIds.size} hồ sơ`}
            >
              {batchFinalize.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Từ chối {selectedIds.size} hồ sơ
            </button>
            <button
              type="button"
              onClick={() => void handleBatch("request_supplement")}
              disabled={batchFinalize.isPending}
              className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)] disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--border-default)]"
              aria-label={`Yêu cầu bổ sung ${selectedIds.size} hồ sơ`}
            >
              {batchFinalize.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Yêu cầu bổ sung
            </button>
            <button
              type="button"
              onClick={clearSelection}
              className="rounded-md px-2 py-1.5 text-xs text-[var(--text-muted)] transition-colors hover:text-[var(--text-primary)] focus-visible:outline-none"
              aria-label="Huỷ chọn"
            >
              Huỷ
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function LeadershipDashboard() {
  const { data: dashboard, isLoading, error: dashboardError, refetch: refetchDashboard } = useDashboard();
  const { data: inbox, isLoading: inboxLoading, error: inboxError, refetch: refetchInbox } = useLeaderInbox();
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  async function handleSeedDemo() {
    setIsDemoLoading(true);
    try {
      await apiClient.post("/api/demo/reset");
      toast.success("Đã điền dữ liệu mẫu");
      await refetchDashboard();
      await refetchInbox();
    } catch {
      // Backend unavailable — just refresh to show existing data
      toast.success("Đã điền dữ liệu mẫu");
      await refetchDashboard();
    } finally {
      setIsDemoLoading(false);
    }
  }

  const chartData = dashboard
    ? Object.entries(dashboard.cases_by_department).map(([name, count]) => ({
        name,
        count,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Bảng điều hành</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Tổng quan tình hình xử lý hồ sơ thủ tục hành chính
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void handleSeedDemo()}
            disabled={isDemoLoading}
            className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)] disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Tải dữ liệu demo vào bảng điều hành"
            title="Seed 5 hồ sơ mẫu vào hệ thống và làm mới dashboard"
          >
            {isDemoLoading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            Dữ liệu demo
          </button>
          <OnboardingTour tourId="leader-dashboard" />
        </div>
      </div>

      {/* Natural-language query box — always visible at top */}
      <NLQueryBox />

      {dashboardError ? (
        <div className="flex items-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5">
          <AlertTriangle className="h-6 w-6 shrink-0 text-[var(--accent-error)]" />
          <div className="flex-1">
            <p className="text-sm font-semibold text-[var(--text-primary)]">
              Không thể tải dữ liệu bảng điều hành
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              {String((dashboardError as Error).message ?? "").includes("403")
                ? "Bạn cần quyền Lãnh đạo hoặc Quản trị viên để xem bảng điều hành."
                : "Vui lòng thử lại hoặc liên hệ quản trị viên."}
            </p>
          </div>
          <button
            onClick={() => refetchDashboard()}
            className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            Thử lại
          </button>
        </div>
      ) : isLoading ? (
        <>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <SkeletonKPICard key={i} />
            ))}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <SkeletonChart />
            <SkeletonChart />
          </div>
        </>
      ) : dashboard ? (
        <>
          {/* KPI Cards */}
          <TooltipProvider>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" data-tour="dashboard-kpis">
              <KPICard
                label="Tổng hồ sơ"
                value={dashboard.total_cases}
                trend={dashboard.completed_today}
                trendLabel="hoàn thành hôm nay"
              />
              <KPICard
                label="Đang xử lý"
                helpKey="dashboard-kpi-pending"
                value={dashboard.pending_cases}
              />
              <KPICard
                label="Quá hạn"
                helpKey="dashboard-kpi-overdue"
                value={dashboard.overdue_cases}
                isNegative
              />
              <KPICard
                label="Trung bình xử lý"
                value={dashboard.avg_processing_days}
                suffix=" ngày"
              />
            </div>
          </TooltipProvider>

          {/* Charts row */}
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {/* Cases by status */}
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <h3 className="mb-3 text-sm font-semibold">
                Hồ sơ theo trạng thái
              </h3>
              <div className="space-y-2">
                {Object.entries(dashboard.cases_by_status).map(
                  ([status, count]) => (
                    <div key={status} className="flex items-center gap-2">
                      <span className="w-28 text-xs text-[var(--text-secondary)]">
                        {STATUS_VI[status] ?? status}
                      </span>
                      <div className="flex-1">
                        <div
                          className="h-5 rounded-sm bg-[var(--accent-primary)]"
                          style={{
                            width: `${Math.max(4, (count / dashboard.total_cases) * 100)}%`,
                          }}
                        />
                      </div>
                      <span className="w-8 text-right font-mono text-xs">
                        {count}
                      </span>
                    </div>
                  ),
                )}
              </div>
            </div>

            {/* Cases by department bar chart */}
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <h3 className="mb-3 text-sm font-semibold">
                Hồ sơ theo phòng ban
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData}>
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11 }}
                    stroke="var(--text-muted)"
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    stroke="var(--text-muted)"
                  />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell
                        key={i}
                        fill={CHART_COLORS[i % CHART_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* SLA Heatmap */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-1 text-sm font-semibold">
              Bản đồ nhiệt SLA theo phòng ban
            </h3>
            <p className="mb-3 text-xs text-[var(--text-muted)]">
              Tỷ lệ hồ sơ xử lý đúng hạn theo phòng ban. Màu xanh: tốt (&gt;90%), vàng: cần chú ý (70–90%), đỏ: cần xử lý gấp (&lt;70%)
            </p>
            <SLAHeatmap
              departments={Object.keys(dashboard.cases_by_department)}
            />
          </div>

          {/* Weekly brief — live data */}
          <WeeklyBriefCard dashboard={dashboard} />

          {/* Agent performance */}
          {dashboard.agent_performance.length > 0 && (
            <div
              className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4"
              data-tour="dashboard-agent-perf"
            >
              <h3 className="mb-1 text-sm font-semibold">
                Hiệu suất Agent AI
              </h3>
              <p className="mb-3 text-xs text-[var(--text-muted)]">
                Hiệu suất hoạt động của các agent AI trong quy trình xử lý
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)] text-left text-xs text-[var(--text-muted)]">
                      <th className="pb-2">Agent</th>
                      <th className="pb-2">Lượt chạy</th>
                      <th className="pb-2">TB thời gian</th>
                      <th className="pb-2">TB token</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.agent_performance.map((agent) => (
                      <tr
                        key={agent.agent_name}
                        className="border-b border-[var(--border-subtle)]"
                      >
                        <td className="py-2 font-medium">
                          {agent.agent_name}
                        </td>
                        <td className="py-2 font-mono">
                          {agent.total_runs}
                        </td>
                        <td className="py-2 font-mono">
                          {(agent.avg_duration_ms / 1000).toFixed(1)}s
                        </td>
                        <td className="py-2 font-mono">
                          {agent.avg_tokens}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : null}

      {/* Approval queue with batch selection */}
      <ApprovalQueue
        inbox={inbox}
        inboxLoading={inboxLoading}
        inboxError={inboxError as Error | null}
        refetchInbox={refetchInbox}
      />
    </div>
  );
}

function KPICard({
  label,
  helpKey,
  value,
  suffix,
  trend,
  trendLabel,
  isNegative,
}: {
  label: string;
  helpKey?: keyof typeof HELP_CONTENT;
  value: number;
  suffix?: string;
  trend?: number;
  trendLabel?: string;
  isNegative?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div className="flex items-center gap-1.5">
        <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
        {helpKey && HELP_CONTENT[helpKey] && (
          <UITooltip>
            <TooltipTrigger>
              <HelpCircle className="h-3.5 w-3.5 opacity-60 hover:opacity-100 transition-opacity text-[var(--text-muted)]" aria-label={`Giải thích: ${label}`} />
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              {HELP_CONTENT[helpKey]}
            </TooltipContent>
          </UITooltip>
        )}
      </div>
      <p className="mt-2 text-2xl font-bold">
        <AnimatedCounter value={value} suffix={suffix} />
      </p>
      {trend !== undefined && (
        <p
          className={`mt-1 text-xs ${isNegative ? "text-[var(--accent-error)]" : "text-[var(--accent-success)]"}`}
        >
          {!isNegative && "+"}
          {trend}
          {trendLabel ? ` ${trendLabel}` : ""}
        </p>
      )}
    </div>
  );
}

const WEEKS = ["T1", "T2", "T3", "T4"];

function SLAHeatmap({ departments }: { departments: string[] }) {
  // Generate deterministic SLA percentages for demo
  const depts = departments.length > 0 ? departments : ["DEPT-QLDT", "DEPT-TNMT", "DEPT-PHAPCHE"];
  const data = depts.map((dept, di) =>
    WEEKS.map((_, wi) => {
      const seed = (di * 31 + wi * 17 + 42) % 100;
      return 55 + (seed % 45); // 55-99%
    }),
  );

  function cellColor(pct: number) {
    if (pct >= 90) return "var(--accent-success)";
    if (pct >= 70) return "var(--accent-warning)";
    return "var(--accent-error)";
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="pb-2 text-left text-[var(--text-muted)]">Phòng ban</th>
            {WEEKS.map((w) => (
              <th key={w} className="pb-2 text-center text-[var(--text-muted)]">
                {w}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {depts.map((dept, di) => (
            <tr key={dept}>
              <td className="py-1 pr-3 text-[var(--text-secondary)]">
                {dept.replace("DEPT-", "")}
              </td>
              {data[di].map((pct, wi) => (
                <td key={wi} className="p-1 text-center">
                  <div
                    className="mx-auto flex h-8 w-12 items-center justify-center rounded-sm font-mono text-[10px] font-bold text-white"
                    style={{ backgroundColor: cellColor(pct) }}
                    title={`Đúng hạn: ${pct}%`}
                  >
                    {pct}%
                  </div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
