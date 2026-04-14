import { cn } from "@/lib/utils"

export interface Citation {
  law_name: string
  article: string
  relevance: number // 0-1 float
}

interface CitationBadgeProps {
  citation: Citation
  className?: string
}

export function CitationBadge({ citation, className }: CitationBadgeProps) {
  const relevancePct = Math.round(citation.relevance * 100)

  return (
    <span
      role="note"
      aria-label={`Trích dẫn: ${citation.law_name}, ${citation.article}, độ liên quan ${relevancePct}%`}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        "text-[11px] font-medium whitespace-nowrap",
        "transition-colors duration-150",
        className
      )}
      style={{
        borderColor: "oklch(0.55 0.18 300 / 0.4)",
        backgroundColor: "oklch(0.55 0.18 300 / 0.08)",
        color: "oklch(0.78 0.14 300)",
      }}
    >
      {/* Article ref */}
      <span className="font-semibold">{citation.article}</span>

      {/* Law name — truncated */}
      <span
        className="max-w-[160px] truncate opacity-80"
        title={citation.law_name}
      >
        {citation.law_name}
      </span>

      {/* Relevance pill */}
      <span
        className="inline-flex items-center rounded-full px-1 py-px text-[9px] font-bold tabular-nums"
        style={{
          backgroundColor: "oklch(0.55 0.18 300 / 0.2)",
        }}
        aria-label={`Độ liên quan: ${relevancePct}%`}
      >
        {relevancePct}%
      </span>
    </span>
  )
}
