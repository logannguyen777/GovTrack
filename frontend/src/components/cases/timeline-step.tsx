import { cn } from "@/lib/utils"

export type StepStatus = "completed" | "active" | "pending"

export interface TimelineStepData {
  label: string
  timestamp: string // ISO date string
  status: StepStatus
}

interface TimelineStepProps {
  step: TimelineStepData
  isLast: boolean
  className?: string
}

const DOT_STYLES: Record<StepStatus, string> = {
  completed: "border-2 border-[var(--accent-success)] bg-[var(--accent-success)]",
  active: "border-2 border-[var(--accent-primary)] bg-[var(--accent-primary)] animate-pulse",
  pending: "border-2 border-[var(--border-default)] bg-transparent",
}

const LABEL_STYLES: Record<StepStatus, string> = {
  completed: "text-[var(--text-primary)]",
  active: "text-[var(--accent-primary)] font-semibold",
  pending: "text-[var(--text-muted)]",
}

const STATUS_LABELS: Record<StepStatus, string> = {
  completed: "Hoàn thành",
  active: "Đang xử lý",
  pending: "Chờ xử lý",
}

function formatTimestamp(iso: string): string {
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export function TimelineStep({ step, isLast, className }: TimelineStepProps) {
  const { label, timestamp, status } = step

  return (
    <li
      aria-label={`${label} — ${STATUS_LABELS[status]}`}
      className={cn("flex gap-3", className)}
    >
      {/* Left column: dot + connector line */}
      <div className="flex flex-col items-center">
        {/* Status dot */}
        <div
          aria-hidden="true"
          className={cn("mt-0.5 h-3 w-3 shrink-0 rounded-full", DOT_STYLES[status])}
        />
        {/* Vertical connector — hidden for last item */}
        {!isLast && (
          <div
            aria-hidden="true"
            className="mt-1 w-px flex-1"
            style={{ backgroundColor: "var(--border-subtle)" }}
          />
        )}
      </div>

      {/* Right column: content */}
      <div className={cn("pb-5", isLast && "pb-0")}>
        <p className={cn("text-[13px] leading-snug", LABEL_STYLES[status])}>
          {label}
        </p>
        {timestamp && (
          <time
            dateTime={timestamp}
            className="mt-0.5 block font-mono text-[10px] text-[var(--text-muted)] tabular-nums"
          >
            {formatTimestamp(timestamp)}
          </time>
        )}
      </div>
    </li>
  )
}
