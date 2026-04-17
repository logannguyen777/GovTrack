import * as React from "react";
import { cn } from "@/lib/utils";
import { LawChunkPopover } from "./law-chunk-popover";

export interface Citation {
  law_name: string;
  article: string;
  relevance: number; // 0-1 float
  /** Optional: chunk ID for popover detail */
  chunkId?: string;
}

interface CitationBadgeProps {
  citation: Citation;
  className?: string;
  onClick?: () => void;
}

function CitationBadgeInner({
  citation,
  className,
  onClick,
  asButton,
}: CitationBadgeProps & { asButton?: boolean }) {
  const relevancePct = Math.round(citation.relevance * 100);
  const Tag = (asButton || onClick) ? "button" : "span";

  return (
    <Tag
      role={(asButton || onClick) ? "button" : "note"}
      type={(asButton || onClick) ? "button" : undefined}
      aria-label={`Trích dẫn: ${citation.law_name}, ${citation.article}, độ liên quan ${relevancePct}%`}
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5",
        "text-[11px] font-medium whitespace-nowrap",
        "transition-colors duration-150",
        (asButton || onClick) &&
          "cursor-pointer hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-400",
        className,
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
    </Tag>
  );
}

export function CitationBadge({ citation, className, onClick }: CitationBadgeProps) {
  // When chunkId is available, wrap in LawChunkPopover for rich detail
  if (citation.chunkId) {
    return (
      <LawChunkPopover
        chunkId={citation.chunkId}
        fallback={{ lawName: citation.law_name, article: citation.article }}
        trigger={
          <CitationBadgeInner
            citation={citation}
            className={className}
            asButton
          />
        }
      />
    );
  }

  return (
    <CitationBadgeInner
      citation={citation}
      className={className}
      onClick={onClick}
    />
  );
}
