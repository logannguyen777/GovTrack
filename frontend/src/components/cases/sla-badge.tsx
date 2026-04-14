"use client"

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"

interface SlaBadgeProps {
  deadline: string // ISO date string
  className?: string
}

function computeStatus(deadlineMs: number, nowMs: number) {
  const diffMs = deadlineMs - nowMs
  const diffHours = diffMs / (1000 * 60 * 60)
  const diffDays = diffMs / (1000 * 60 * 60 * 24)

  if (diffMs <= 0) {
    return { label: "Quá hạn", variant: "critical" as const }
  }
  if (diffHours < 24) {
    const h = Math.ceil(diffHours)
    return { label: `${h}h còn lại`, variant: "critical" as const }
  }
  if (diffDays < 3) {
    const d = Math.ceil(diffDays)
    return { label: `${d}d còn lại`, variant: "warning" as const }
  }
  const d = Math.ceil(diffDays)
  return { label: `${d}d còn lại`, variant: "normal" as const }
}

export function SlaBadge({ deadline, className }: SlaBadgeProps) {
  const deadlineMs = new Date(deadline).getTime()
  const [status, setStatus] = useState(() => computeStatus(deadlineMs, Date.now()))

  useEffect(() => {
    // Recompute immediately on mount and every 60 seconds
    setStatus(computeStatus(deadlineMs, Date.now()))
    const id = setInterval(() => {
      setStatus(computeStatus(deadlineMs, Date.now()))
    }, 60_000)
    return () => clearInterval(id)
  }, [deadlineMs])

  const variantStyles: Record<typeof status.variant, string> = {
    normal: "border-[var(--accent-success)] text-[var(--accent-success)]",
    warning: "border-[var(--accent-warning)] text-[var(--accent-warning)]",
    critical: "border-[var(--accent-error)] text-[var(--accent-error)] animate-pulse",
  }

  return (
    <span
      role="status"
      aria-label={`Thời hạn SLA: ${status.label}`}
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5",
        "font-mono text-[10px] font-medium tabular-nums whitespace-nowrap",
        variantStyles[status.variant],
        className
      )}
    >
      {status.label}
    </span>
  )
}
