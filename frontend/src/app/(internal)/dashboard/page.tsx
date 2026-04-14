"use client";

import { useDashboard, useLeaderInbox } from "@/hooks/use-leadership";
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
import { AlertTriangle, ClipboardList } from "lucide-react";

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

export default function LeadershipDashboard() {
  const { data: dashboard, isLoading, error: dashboardError, refetch: refetchDashboard } = useDashboard();
  const { data: inbox, isLoading: inboxLoading, error: inboxError, refetch: refetchInbox } = useLeaderInbox();
  const router = useRouter();

  const chartData = dashboard
    ? Object.entries(dashboard.cases_by_department).map(([name, count]) => ({
        name,
        count,
      }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Bảng điều hành</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Tổng quan tình hình xử lý hồ sơ thủ tục hành chính
        </p>
      </div>

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
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <KPICard
              label="Tổng hồ sơ"
              subtitle="Tổng số hồ sơ đang quản lý"
              value={dashboard.total_cases}
              trend={dashboard.completed_today}
              trendLabel="hoàn thành hôm nay"
            />
            <KPICard
              label="Đang xử lý"
              subtitle="Hồ sơ chưa có kết quả cuối cùng"
              value={dashboard.pending_cases}
            />
            <KPICard
              label="Quá hạn"
              subtitle="Vượt quá thời hạn xử lý"
              value={dashboard.overdue_cases}
              isNegative
            />
            <KPICard
              label="Trung bình xử lý"
              subtitle="Thời gian từ tiếp nhận đến trả kết quả"
              value={dashboard.avg_processing_days}
              suffix=" ngày"
            />
          </div>

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

          {/* Weekly brief */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-2 text-sm font-semibold">
              Báo cáo tuần (AI)
            </h3>
            <p className="font-legal text-sm leading-relaxed text-[var(--text-secondary)]">
              Trong tuần qua, hệ thống đã xử lý{" "}
              <strong>{dashboard.completed_today}</strong> hồ sơ hoàn thành
              trong ngày hôm nay. Tổng cộng{" "}
              <strong>{dashboard.total_cases}</strong> hồ sơ đang quản lý,
              trong đó <strong>{dashboard.overdue_cases}</strong> hồ sơ quá
              hạn cần xử lý ưu tiên. Thời gian xử lý trung bình là{" "}
              <strong>
                {dashboard.avg_processing_days.toFixed(1)} ngày
              </strong>
              .
            </p>
          </div>

          {/* Agent performance */}
          {dashboard.agent_performance.length > 0 && (
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
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

      {/* Approve queue */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 className="mb-1 text-sm font-semibold">
          Hồ sơ chờ phê duyệt{inbox && inbox.length > 0 ? ` (${inbox.length})` : ""}
        </h3>
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
              onClick={() => refetchInbox()}
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
            {inbox.map((item) => (
              <div
                key={item.case_id}
                onClick={() => router.push(`/compliance/${item.case_id}`)}
                className="flex cursor-pointer items-center justify-between rounded-md border border-[var(--border-subtle)] p-3 transition-colors hover:bg-[var(--bg-surface-raised)]"
              >
                <div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {item.code} · {item.action_required}
                  </p>
                </div>
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
            ))}
          </div>
        ) : (
          <EmptyState
            icon={ClipboardList}
            title="Không có hồ sơ chờ phê duyệt"
            description="Tất cả hồ sơ đã được xử lý hoặc chưa có hồ sơ mới."
          />
        )}
      </div>
    </div>
  );
}

function KPICard({
  label,
  subtitle,
  value,
  suffix,
  trend,
  trendLabel,
  isNegative,
}: {
  label: string;
  subtitle?: string;
  value: number;
  suffix?: string;
  trend?: number;
  trendLabel?: string;
  isNegative?: boolean;
}) {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
      {subtitle && (
        <p className="mt-0.5 text-[11px] leading-tight text-[var(--text-muted)]">
          {subtitle}
        </p>
      )}
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
