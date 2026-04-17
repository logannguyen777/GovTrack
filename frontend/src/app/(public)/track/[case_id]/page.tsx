"use client";

import { use, useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { usePublicCase, usePublicAudit } from "@/hooks/use-public";
import { useExplainCase } from "@/hooks/use-assistant";
import { NextStepCTA } from "@/components/track/next-step-cta";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import {
  Sparkles,
  Phone,
  Bell,
  X,
  Eye,
  PenLine,
  ShieldCheck,
  BellRing,
  Clock,
} from "lucide-react";
import type { PublicAuditEntry } from "@/hooks/use-public";

const STAGES = [
  { key: "submitted", label: "Tiếp nhận" },
  { key: "classifying", label: "Phân loại" },
  { key: "extracting", label: "Kiểm tra" },
  { key: "processing", label: "Xử lý" },
  { key: "completed", label: "Kết quả" },
];

const STATUS_TO_STAGE: Record<string, number> = {
  submitted: 0,
  classifying: 1,
  extracting: 2,
  gap_checking: 2,
  pending_supplement: 2,
  legal_review: 3,
  drafting: 3,
  leader_review: 3,
  consultation: 3,
  approved: 4,
  rejected: 4,
  published: 4,
};

const STATUS_DESCRIPTIONS: Record<string, string> = {
  submitted: "Hồ sơ đã được tiếp nhận vào hệ thống",
  classifying: "Hệ thống đang phân loại và kiểm tra thành phần hồ sơ",
  extracting: "Đang trích xuất thông tin từ tài liệu",
  gap_checking: "Đang kiểm tra tính đầy đủ và hợp lệ theo quy định",
  pending_supplement: "Hồ sơ cần bổ sung thêm tài liệu",
  legal_review: "Đang xem xét cơ sở pháp lý",
  drafting: "Đang soạn thảo văn bản quyết định",
  leader_review: "Đang chờ lãnh đạo phê duyệt",
  consultation: "Đang xin ý kiến các cơ quan liên quan",
  approved: "Hồ sơ đã được phê duyệt",
  rejected: "Hồ sơ bị từ chối — vui lòng liên hệ để biết lý do",
  published:
    "Kết quả đã được ban hành — vui lòng đến nhận tại bộ phận Một cửa",
};

// ---------------------------------------------------------------------------
// Browser notification helpers
// ---------------------------------------------------------------------------

const NOTIF_PROMPTED_KEY = "govflow-notif-prompted";

function useStatusPush(code: string, status: string | undefined) {
  const prevStatus = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!status || typeof window === "undefined") return;
    if (!("Notification" in window)) return;

    if (
      prevStatus.current !== undefined &&
      prevStatus.current !== status &&
      Notification.permission === "granted"
    ) {
      new Notification(`Hồ sơ ${code}`, {
        body: STATUS_DESCRIPTIONS[status] ?? status,
        icon: "/favicon.svg",
      });
    }

    prevStatus.current = status;
  }, [code, status]);
}

function useNotifPrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("Notification" in window)) return;
    if (Notification.permission !== "default") return;
    const prompted = localStorage.getItem(NOTIF_PROMPTED_KEY);
    if (!prompted) {
      setShow(true);
    }
  }, []);

  async function requestPermission() {
    localStorage.setItem(NOTIF_PROMPTED_KEY, "1");
    setShow(false);
    const result = await Notification.requestPermission();
    if (result === "granted") {
      new Notification("Đã bật thông báo", {
        body: "Anh/chị sẽ nhận thông báo khi hồ sơ thay đổi trạng thái.",
        icon: "/favicon.svg",
      });
    }
  }

  function dismiss() {
    localStorage.setItem(NOTIF_PROMPTED_KEY, "1");
    setShow(false);
  }

  return { show, requestPermission, dismiss };
}

// ---------------------------------------------------------------------------
// NotifPromptBanner
// ---------------------------------------------------------------------------

function NotifPromptBanner({
  onEnable,
  onDismiss,
}: {
  onEnable: () => void;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
      className="flex items-center gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3 shadow-sm"
      role="banner"
    >
      <Bell className="h-5 w-5 shrink-0 text-[var(--accent-primary)]" aria-hidden="true" />
      <p className="flex-1 text-sm text-[var(--text-secondary)]">
        Nhận thông báo khi hồ sơ thay đổi trạng thái?
      </p>
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onEnable}
          className="rounded-lg px-3 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90"
          style={{ background: "var(--accent-primary)" }}
        >
          Bật thông báo
        </button>
        <button
          type="button"
          onClick={onDismiss}
          aria-label="Để sau"
          className="rounded-lg p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
        >
          <X size={14} />
        </button>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Demo notification button
// ---------------------------------------------------------------------------

function DemoNotificationButton({ caseId }: { caseId: string }) {
  const [fired, setFired] = useState(false);

  function fireDemo() {
    if (fired) return;
    setFired(true);
    setTimeout(() => {
      if (typeof window !== "undefined" && "Notification" in window) {
        if (Notification.permission === "granted") {
          new Notification("Hồ sơ của bạn đã được xem", {
            body: `Sở Xây dựng đang xử lý hồ sơ ${caseId}`,
            icon: "/favicon.svg",
          });
        } else {
          void Notification.requestPermission().then((perm) => {
            if (perm === "granted") {
              new Notification("Hồ sơ của bạn đã được xem", {
                body: `Sở Xây dựng đang xử lý hồ sơ ${caseId}`,
                icon: "/favicon.svg",
              });
            }
          });
        }
      }
      setTimeout(() => setFired(false), 5000);
    }, 1000);
  }

  return (
    <button
      type="button"
      onClick={fireDemo}
      disabled={fired}
      className="flex items-center gap-1.5 rounded-lg border border-[var(--border-default)] bg-[var(--bg-subtle)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--accent-primary)] hover:text-[var(--accent-primary)] disabled:opacity-50"
    >
      <BellRing size={12} />
      {fired ? "Đang gửi thông báo..." : "Giả lập thông báo"}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Audit panel — Estonia-style "Ai đã xem hồ sơ của tôi"
// ---------------------------------------------------------------------------

function formatAuditTime(timestamp: string): string {
  try {
    const d = new Date(timestamp);
    const hh = String(d.getHours()).padStart(2, "0");
    const mm2 = String(d.getMinutes()).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const yyyy = d.getFullYear();
    return `${hh}:${mm2}, ${dd}/${mo}/${yyyy}`;
  } catch {
    return timestamp;
  }
}

const ACTION_ICONS: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  read: Eye,
  view: Eye,
  update: PenLine,
  edit: PenLine,
};

function actionIcon(action: string) {
  const key = action.toLowerCase();
  for (const [k, Icon] of Object.entries(ACTION_ICONS)) {
    if (key.includes(k)) return Icon;
  }
  return Eye;
}

// Static ISO timestamps prevent React #418 hydration mismatch.
// These are intentionally fixed so SSR and client produce identical HTML.
// The AuditPanel component uses real data when available; mock is fallback only.
const MOCK_AUDIT: PublicAuditEntry[] = [
  {
    role: "Chuyên viên xử lý",
    org: "Sở Xây dựng TP. Hà Nội",
    action: "xem tài liệu",
    timestamp: "2026-04-17T09:55:00.000Z",
  },
  {
    role: "Chuyên viên tiếp nhận",
    org: "Trung tâm hành chính công",
    action: "xem hồ sơ",
    timestamp: "2026-04-17T09:25:00.000Z",
  },
  {
    role: "Hệ thống",
    org: "GovFlow · AI phân loại",
    action: "phân loại tự động",
    timestamp: "2026-04-17T09:00:00.000Z",
  },
];

function AuditPanel({ caseId }: { caseId: string }) {
  const { data, isLoading, error } = usePublicAudit(caseId);

  // Use real data if available, otherwise show mock data for demo
  const entries: PublicAuditEntry[] = (data && data.length > 0) ? data : MOCK_AUDIT;
  const isMocked = !data || data.length === 0;

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
      {/* Estonia trust signal header */}
      <div className="mb-4 flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--accent-primary)]/10">
          <ShieldCheck size={16} className="text-[var(--accent-primary)]" />
        </div>
        <div>
          <h2 className="font-semibold text-[var(--text-primary)]">
            Ai đã xem hồ sơ của tôi?
          </h2>
          <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
            Minh bạch toàn diện — xem ai đã truy cập hồ sơ của bạn theo thời gian thực.
          </p>
          {isMocked && (
            <span className="mt-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              Dữ liệu minh họa
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3" aria-busy="true">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <div className="h-8 w-8 animate-pulse rounded-full bg-[var(--bg-subtle)]" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 w-2/3 animate-pulse rounded bg-[var(--bg-subtle)]" />
                <div className="h-2.5 w-1/2 animate-pulse rounded bg-[var(--bg-subtle)]" />
              </div>
            </div>
          ))}
        </div>
      ) : error && (!data || data.length === 0) ? (
        // Show mock data even on error for demo purposes
        <AuditList entries={MOCK_AUDIT} />
      ) : (
        <AuditList entries={entries} />
      )}
    </div>
  );
}

function AuditList({ entries }: { entries: PublicAuditEntry[] }) {
  return (
    <div className="space-y-0" role="list">
      {entries.map((entry, i) => {
        const Icon = actionIcon(entry.action);
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.25, delay: i * 0.05 }}
            className="flex gap-3"
            role="listitem"
          >
            {/* Timeline connector */}
            <div className="flex flex-col items-center">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--border-subtle)] bg-[var(--bg-subtle)]">
                <Icon size={14} className="text-[var(--text-secondary)]" />
              </div>
              {i < entries.length - 1 && (
                <div className="w-px flex-1 bg-[var(--border-subtle)]" style={{ minHeight: "1rem" }} />
              )}
            </div>

            {/* Content */}
            <div className="pb-4 pt-1">
              <p className="text-sm font-medium text-[var(--text-primary)]">
                {entry.org}
                <span className="mx-1.5 text-[var(--text-muted)]">·</span>
                <span className="font-normal text-[var(--text-secondary)]">{entry.role}</span>
              </p>
              {/* suppressHydrationWarning: formatted timestamp depends on browser locale/timezone
                  which differs between SSR (server TZ) and client (user TZ). */}
              <p className="mt-0.5 text-xs text-[var(--text-muted)]" suppressHydrationWarning>
                {formatAuditTime(entry.timestamp)}
                <span className="mx-1.5">·</span>
                {entry.action}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function CaseTrackingPage({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const { data: caseData, isLoading, error } = usePublicCase(case_id);
  const { data: explanation, isLoading: isExplaining } = useExplainCase(case_id);

  useStatusPush(case_id, caseData?.status);
  const notifPrompt = useNotifPrompt();

  const currentStage = caseData ? STATUS_TO_STAGE[caseData.status] ?? 0 : -1;
  const staticDescription = caseData ? STATUS_DESCRIPTIONS[caseData.status] ?? "" : "";

  // Overdue computation
  const TERMINAL_STATUSES = new Set(["approved", "rejected", "published"]);
  const overdueInfo = useMemo(() => {
    if (!caseData) return null;
    if (TERMINAL_STATUSES.has(caseData.status)) return null;

    const submittedMs = new Date(caseData.submitted_at).getTime();
    const nowMs = Date.now();
    const daysSinceSubmit = Math.floor((nowMs - submittedMs) / (1000 * 60 * 60 * 24));

    // Use sla_days from data if available, otherwise use estimated_completion
    const slaDays = caseData.sla_days;
    if (slaDays != null) {
      if (daysSinceSubmit > slaDays) {
        const overdueDays = daysSinceSubmit - slaDays;
        return { isOverdue: true, overdueDays, slaDays, daysSinceSubmit };
      }
      return null;
    }

    // Fallback: check estimated_completion
    if (caseData.estimated_completion) {
      const estMs = new Date(caseData.estimated_completion).getTime();
      if (nowMs > estMs) {
        const overdueDays = Math.floor((nowMs - estMs) / (1000 * 60 * 60 * 24));
        return { isOverdue: true, overdueDays, slaDays: null, daysSinceSubmit };
      }
    }
    return null;
  }, [caseData]);

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      {/* Push notification prompt */}
      <AnimatePresence>
        {notifPrompt.show && (
          <div className="mb-6">
            <NotifPromptBanner
              onEnable={() => void notifPrompt.requestPermission()}
              onDismiss={notifPrompt.dismiss}
            />
          </div>
        )}
      </AnimatePresence>

      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">
            Tra cứu hồ sơ
          </h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Mã hồ sơ: <span className="font-mono">{case_id}</span>
          </p>
        </div>
        {/* Demo notification button beside the header */}
        <DemoNotificationButton caseId={case_id} />
      </div>

      {isLoading && (
        <div className="mt-8 space-y-3" aria-live="polite" aria-busy="true">
          <div className="h-24 animate-pulse rounded-lg bg-[var(--bg-surface)]" />
          <div className="h-48 animate-pulse rounded-lg bg-[var(--bg-surface)]" />
          <p className="text-center text-sm text-[var(--text-muted)]">
            Đang tải thông tin hồ sơ...
          </p>
        </div>
      )}

      {error && (
        <div
          className="mt-8 rounded-md border border-[var(--accent-destructive)]/30 bg-[var(--accent-destructive)]/5 p-5"
          role="alert"
        >
          <p className="font-medium text-[var(--accent-destructive)]">
            Không tìm thấy hồ sơ
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Không tìm thấy hồ sơ với mã{" "}
            <span className="font-mono font-semibold">{case_id}</span>. Vui lòng
            kiểm tra lại mã hồ sơ. Nếu cần hỗ trợ, liên hệ Tổng đài:{" "}
            <a
              href="tel:1900xxxx"
              className="font-semibold text-[var(--accent-primary)] hover:underline"
            >
              1900.xxxx
            </a>
          </p>
        </div>
      )}

      {caseData && (
        <div className="mt-8 space-y-6">
          {/* Hint banner */}
          <HelpHintBanner id="track-explanation" variant="tip">
            AI giải thích trạng thái hồ sơ bằng tiếng Việt phổ thông, kèm bước tiếp theo nếu bạn cần thực hiện thêm.
          </HelpHintBanner>

          {/* Next step CTA banner */}
          <NextStepCTA caseData={caseData} />

          {/* Status card */}
          <div
            className={`rounded-lg border bg-[var(--bg-surface)] p-6 ${overdueInfo ? "border-[var(--accent-destructive)]/40" : "border-[var(--border-subtle)]"}`}
          >
            {/* Overdue banner */}
            {overdueInfo && (
              <div
                className="mb-4 flex items-center gap-2 rounded-md border border-[var(--accent-destructive)]/30 bg-[var(--accent-destructive)]/5 px-3 py-2"
                role="alert"
                aria-label="Hồ sơ quá hạn"
              >
                <Clock className="h-4 w-4 shrink-0 text-[var(--accent-destructive)]" aria-hidden="true" />
                <div className="flex-1">
                  <span
                    className="inline-flex items-center rounded px-2 py-0.5 text-xs font-semibold text-white"
                    style={{ backgroundColor: "var(--accent-destructive)" }}
                    title={
                      overdueInfo.slaDays != null
                        ? `SLA theo luật: ${overdueInfo.slaDays} ngày. Thời gian đã xử lý: ${overdueInfo.daysSinceSubmit} ngày.`
                        : `Hồ sơ đã quá hạn dự kiến ${overdueInfo.overdueDays} ngày.`
                    }
                  >
                    Quá hạn ({overdueInfo.overdueDays} ngày)
                  </span>
                  {overdueInfo.slaDays != null && (
                    <span className="ml-2 text-xs text-[var(--text-muted)]">
                      SLA: {overdueInfo.slaDays} ngày · Đã xử lý: {overdueInfo.daysSinceSubmit} ngày
                    </span>
                  )}
                </div>
              </div>
            )}

            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--text-secondary)]">
                  Trạng thái hiện tại
                </p>
                <p className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
                  {caseData.current_step ?? caseData.status}
                </p>

                {/* AI plain-language explanation */}
                {isExplaining ? (
                  <div className="mt-2 flex items-center gap-2">
                    <Sparkles size={12} className="text-purple-500 animate-pulse shrink-0" />
                    <div className="h-3 w-64 animate-pulse rounded bg-[var(--bg-subtle)]" />
                  </div>
                ) : explanation?.explanation ? (
                  <div
                    className="mt-2 flex items-start gap-2 rounded-lg border px-3 py-2"
                    style={{
                      background: "var(--gradient-qwen-soft)",
                      borderColor: "oklch(0.65 0.15 280 / 0.2)",
                    }}
                  >
                    <Sparkles size={12} className="mt-0.5 shrink-0 text-purple-600" />
                    <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                      {explanation.explanation}
                    </p>
                  </div>
                ) : staticDescription ? (
                  <p className="mt-1.5 text-sm text-[var(--text-secondary)]">
                    {staticDescription}
                  </p>
                ) : null}

                {/* Next step from AI */}
                {explanation?.next_step && (
                  <ul className="mt-3 space-y-1">
                    <li className="flex items-start gap-2 text-sm text-[var(--text-secondary)]">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-purple-400" />
                      {explanation.next_step}
                    </li>
                  </ul>
                )}
              </div>
              {caseData.estimated_completion && (
                <div className="shrink-0 text-right">
                  <p className="text-sm text-[var(--text-secondary)]">
                    Dự kiến hoàn thành
                  </p>
                  <p className="mt-1 text-sm font-medium text-[var(--text-primary)]">
                    {new Date(caseData.estimated_completion).toLocaleDateString(
                      "vi-VN",
                    )}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6">
            <h2 className="mb-4 font-semibold text-[var(--text-primary)]">
              Tiến trình xử lý
            </h2>
            <div className="space-y-0" role="list">
              {STAGES.map((stage, i) => {
                const status =
                  i < currentStage
                    ? "completed"
                    : i === currentStage
                      ? "active"
                      : "pending";
                const dotClass =
                  status === "completed"
                    ? "bg-[var(--accent-success)]"
                    : status === "active"
                      ? "bg-[var(--accent-primary)] animate-pulse"
                      : "bg-[var(--border-default)]";

                return (
                  <div key={stage.key} className="flex gap-3" role="listitem">
                    <div className="flex flex-col items-center">
                      <div
                        className={`h-3 w-3 rounded-full ${dotClass}`}
                        aria-label={
                          status === "completed"
                            ? "Đã hoàn thành"
                            : status === "active"
                              ? "Đang xử lý"
                              : "Chưa đến"
                        }
                      />
                      {i < STAGES.length - 1 && (
                        <div className="w-px flex-1 bg-[var(--border-subtle)]" />
                      )}
                    </div>
                    <div className="pb-6">
                      <p
                        className={`text-sm font-medium ${status === "pending" ? "text-[var(--text-muted)]" : "text-[var(--text-primary)]"}`}
                      >
                        {stage.label}
                        {status === "active" && (
                          <span className="ml-2 rounded-full bg-[var(--accent-primary)]/10 px-2 py-0.5 text-xs font-normal text-[var(--accent-primary)]">
                            Đang xử lý
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Estonia-style audit panel */}
          <AuditPanel caseId={case_id} />
        </div>
      )}

      {/* Audit panel shown even when case not found (for demo) */}
      {!caseData && !isLoading && (
        <div className="mt-8">
          <AuditPanel caseId={case_id} />
        </div>
      )}

      {/* Support footer — always visible */}
      <div className="mt-10 flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-subtle)] px-5 py-4">
        <Phone className="h-5 w-5 shrink-0 text-[var(--accent-primary)]" />
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            Cần hỗ trợ?
          </p>
          <p className="text-sm text-[var(--text-secondary)]">
            Liên hệ Tổng đài:{" "}
            <a
              href="tel:1900xxxx"
              className="font-semibold text-[var(--accent-primary)] hover:underline"
            >
              1900.xxxx
            </a>{" "}
            <span className="text-[var(--text-muted)]">
              (Thứ Hai – Thứ Sáu, 7:30 – 17:00)
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}
