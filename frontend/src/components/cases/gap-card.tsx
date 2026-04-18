import { cn } from "@/lib/utils"

export type GapSeverity = "low" | "medium" | "high" | "critical"

export interface Gap {
  id: string
  description: string
  severity: GapSeverity
  fix_suggestion: string
  requirement_ref: string
}

interface GapCardProps {
  gap: Gap
  className?: string
}

const SEVERITY_CONFIG: Record<
  GapSeverity,
  { label: string; borderColor: string; badgeBg: string; badgeText: string }
> = {
  low: {
    label: "Thấp",
    borderColor: "var(--accent-primary)",
    badgeBg: "var(--accent-primary)",
    badgeText: "#ffffff",
  },
  medium: {
    label: "Trung bình",
    borderColor: "var(--accent-warning)",
    badgeBg: "var(--accent-warning)",
    badgeText: "#000000",
  },
  high: {
    label: "Cao",
    borderColor: "var(--classification-secret)",
    badgeBg: "var(--classification-secret)",
    badgeText: "#ffffff",
  },
  critical: {
    label: "Nghiêm trọng",
    borderColor: "var(--accent-error)",
    badgeBg: "var(--accent-error)",
    badgeText: "#ffffff",
  },
}

export function GapCard({ gap, className }: GapCardProps) {
  const config =
    SEVERITY_CONFIG[gap.severity as GapSeverity] ?? SEVERITY_CONFIG.medium

  return (
    <article
      aria-label={`Thiếu sót: ${gap.id}`}
      className={cn(
        "flex gap-0 overflow-hidden rounded-lg",
        "border border-[var(--border-subtle)]",
        "bg-[var(--bg-surface)]",
        "transition-shadow duration-150 hover:shadow-[var(--shadow-md)]",
        className
      )}
    >
      {/* Left severity border strip — 4px, status via color not background */}
      <div
        aria-hidden="true"
        className="w-1 shrink-0"
        style={{ backgroundColor: config.borderColor }}
      />

      {/* Content */}
      <div className="flex flex-1 flex-col gap-3 p-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            {/* Severity badge */}
            <span
              className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
              style={{
                backgroundColor: config.badgeBg,
                color: config.badgeText,
              }}
            >
              {config.label}
            </span>
            {/* Gap ID */}
            <span
              className="font-mono text-[11px] text-[var(--text-muted)]"
              aria-label={`Mã thiếu sót: ${gap.id}`}
            >
              {gap.id}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="text-[13px] leading-snug text-[var(--text-primary)]">
          {gap.description}
        </p>

        {/* Fix suggestion */}
        {gap.fix_suggestion && (
          <div className="rounded-md bg-[var(--bg-surface-raised,var(--border-subtle))/20] px-3 py-2">
            <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Đề xuất khắc phục
            </p>
            <p className="text-[12px] leading-snug text-[var(--text-secondary)]">
              {gap.fix_suggestion}
            </p>
          </div>
        )}

        {/* Requirement reference */}
        {gap.requirement_ref && (
          <p className="text-[11px] text-[var(--text-muted)]">
            <span className="font-semibold">Cơ sở pháp lý: </span>
            <span className="font-mono">{gap.requirement_ref}</span>
          </p>
        )}
      </div>
    </article>
  )
}
