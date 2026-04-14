"use client"

import { motion } from "framer-motion"
import { slideUp } from "@/lib/motion"
import { cn } from "@/lib/utils"
import { ClassificationBadge, type ClassificationLevel } from "@/components/ui/classification-badge"
import { SlaBadge } from "@/components/cases/sla-badge"

export interface CaseCardProps {
  caseId: string
  title: string
  tthcCode: string
  tthcName: string
  status: string
  classification: ClassificationLevel
  slaDeadline: string // ISO date string
  assignee?: string
  gapCount?: number
  onClick?: () => void
  className?: string
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft:              { label: "Nháp",           color: "var(--text-muted)" },
  submitted:          { label: "Đã nộp",         color: "var(--accent-primary)" },
  classifying:        { label: "Phân loại",      color: "var(--accent-info)" },
  extracting:         { label: "Trích xuất",     color: "var(--accent-info)" },
  gap_checking:       { label: "Kiểm tra",       color: "var(--accent-warning)" },
  pending_supplement: { label: "Chờ bổ sung",    color: "var(--accent-warning)" },
  legal_review:       { label: "Xem xét PL",     color: "var(--accent-primary)" },
  drafting:           { label: "Soạn thảo",      color: "var(--accent-primary)" },
  leader_review:      { label: "Chờ duyệt",      color: "var(--accent-warning)" },
  consultation:       { label: "Tham vấn",       color: "var(--accent-warning)" },
  approved:           { label: "Đã duyệt",       color: "var(--accent-success)" },
  rejected:           { label: "Từ chối",        color: "var(--accent-error)" },
  published:          { label: "Đã ban hành",    color: "var(--accent-success)" },
}

export function CaseCard({
  caseId,
  title,
  tthcCode,
  tthcName,
  status,
  classification,
  slaDeadline,
  assignee,
  gapCount,
  onClick,
  className,
}: CaseCardProps) {
  const statusCfg = STATUS_CONFIG[status] ?? { label: status, color: "var(--text-muted)" }
  const isInteractive = typeof onClick === "function"

  return (
    <motion.article
      variants={slideUp}
      initial="hidden"
      animate="visible"
      aria-label={`Hồ sơ: ${title}`}
      tabIndex={isInteractive ? 0 : undefined}
      role={isInteractive ? "button" : "article"}
      onClick={isInteractive ? onClick : undefined}
      onKeyDown={
        isInteractive
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                onClick?.()
              }
            }
          : undefined
      }
      className={cn(
        // Base card shell
        "group/card relative flex flex-col gap-3 overflow-hidden rounded-xl",
        "border border-[var(--border-subtle)] bg-[var(--bg-surface)]",
        "p-4 text-sm",
        // Single 1px border, no heavy shadow on rest state
        "shadow-[var(--shadow-sm)]",
        // Hover
        "transition-shadow duration-150",
        "hover:shadow-[var(--shadow-md)]",
        // Focus ring (keyboard nav)
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] focus-visible:ring-offset-2",
        isInteractive && "cursor-pointer",
        className
      )}
    >
      {/* ── Row 1: Case ID + Classification badge ── */}
      <div className="flex items-start justify-between gap-2">
        <span
          aria-label={`Mã hồ sơ: ${caseId}`}
          className="font-mono text-[11px] text-[var(--text-muted)] tabular-nums"
        >
          {caseId}
        </span>
        <ClassificationBadge level={classification} />
      </div>

      {/* ── Row 2: Title ── */}
      <h3 className="line-clamp-2 text-[14px] font-semibold leading-snug text-[var(--text-primary)]">
        {title}
      </h3>

      {/* ── Row 3: TTHC code + name ── */}
      <div className="flex flex-wrap items-center gap-1.5">
        <span
          className="inline-flex items-center rounded border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]"
        >
          {tthcCode}
        </span>
        <span className="line-clamp-1 text-[12px] text-[var(--text-secondary)]">
          {tthcName}
        </span>
      </div>

      {/* ── Row 4: Status + SLA + Gap count ── */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Status indicator */}
        <span
          className="inline-flex items-center gap-1 text-[11px] font-medium"
          style={{ color: statusCfg.color }}
          aria-label={`Trạng thái: ${statusCfg.label}`}
        >
          {/* Small dot */}
          <span
            aria-hidden="true"
            className="inline-block h-1.5 w-1.5 rounded-full"
            style={{ backgroundColor: statusCfg.color }}
          />
          {statusCfg.label}
        </span>

        {/* SLA badge */}
        <SlaBadge deadline={slaDeadline} />

        {/* Gap count badge — only when > 0 */}
        {typeof gapCount === "number" && gapCount > 0 && (
          <span
            aria-label={`${gapCount} thiếu sót`}
            className="inline-flex items-center gap-0.5 rounded border border-[var(--accent-warning)] px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[var(--accent-warning)]"
          >
            {gapCount} thiếu sót
          </span>
        )}
      </div>

      {/* ── Row 5: Assignee (optional) ── */}
      {assignee && (
        <p className="text-[11px] text-[var(--text-muted)]">
          <span className="font-medium">Phụ trách: </span>
          {assignee}
        </p>
      )}
    </motion.article>
  )
}
