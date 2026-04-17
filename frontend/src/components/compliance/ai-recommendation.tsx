"use client";

import * as React from "react";
import { Sparkles, ChevronRight, ChevronDown } from "lucide-react";
import { useComplianceRecommendation } from "@/hooks/use-assistant";
import { CitationBadge } from "@/components/cases/citation-badge";
import { AgentThinkingSection } from "./agent-thinking-section";
import { SkeletonCard } from "@/components/ui/skeleton-card";

// ---------------------------------------------------------------------------
// Decision label mapper
// ---------------------------------------------------------------------------

const DECISION_LABELS: Record<string, { label: string; color: string }> = {
  approve: { label: "Phê duyệt hồ sơ", color: "var(--accent-success)" },
  request_supplement: { label: "Yêu cầu bổ sung hồ sơ", color: "var(--accent-warning)" },
  reject: { label: "Từ chối hồ sơ", color: "var(--accent-destructive)" },
};

// ---------------------------------------------------------------------------
// AIRecommendation
// ---------------------------------------------------------------------------

interface AIRecommendationProps {
  caseId: string;
}

export function AIRecommendation({ caseId }: AIRecommendationProps) {
  const { data, isLoading, isError } = useComplianceRecommendation(caseId);
  const [thinkingOpen, setThinkingOpen] = React.useState(false);

  if (isLoading) {
    return (
      <div className="rounded-xl border-2 p-4" style={{ borderColor: "oklch(0.75 0.1 300 / 0.4)" }}>
        <SkeletonCard />
      </div>
    );
  }

  if (isError || !data) return null;

  const decisionKey = (data.decision || "").toLowerCase();
  const decisionConfig =
    DECISION_LABELS[decisionKey] ?? DECISION_LABELS["request_supplement"];
  const confidencePct = Math.round((data.confidence ?? 0) * 100);
  const reasoningLines = (data.reasoning || "")
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const citations = Array.isArray(data.citations) ? data.citations : [];

  return (
    <section
      className="rounded-xl border-2 p-5 space-y-4"
      aria-label="Đề xuất AI"
      style={{
        borderColor: "oklch(0.75 0.1 300 / 0.4)",
        background:
          "linear-gradient(135deg, oklch(0.96 0.03 300 / 0.5), oklch(0.97 0.02 240 / 0.3))",
      }}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <Sparkles
          className="h-5 w-5 shrink-0 mt-0.5"
          style={{ color: "oklch(0.55 0.18 300)" }}
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          {/* Badge */}
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium"
            style={{
              backgroundColor: "oklch(0.55 0.18 300 / 0.12)",
              color: "oklch(0.55 0.18 300)",
              border: "1px solid oklch(0.55 0.18 300 / 0.3)",
            }}
          >
            AI đề xuất · Độ tin cậy {confidencePct}%
          </span>

          {/* Decision label */}
          <h3
            className="mt-2 text-base font-semibold leading-snug"
            style={{ color: decisionConfig.color }}
          >
            {decisionConfig.label}
          </h3>

          {/* Reasoning (multi-line) */}
          {reasoningLines.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {reasoningLines.map((r, i) => (
                <li
                  key={i}
                  className="flex items-start gap-1.5 text-xs leading-relaxed"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <span
                    className="shrink-0 mt-0.5 h-1.5 w-1.5 rounded-full"
                    style={{ backgroundColor: decisionConfig.color }}
                    aria-hidden="true"
                  />
                  {r}
                </li>
              ))}
            </ul>
          )}

          {/* Citations */}
          {citations.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {citations.map((c, i) => (
                <CitationBadge
                  key={i}
                  citation={{
                    law_name: String(c.law_name ?? c.law ?? c.law_id ?? "Trích dẫn"),
                    article: String(c.article ?? ""),
                    relevance: typeof c.relevance === "number" ? c.relevance : 0.9,
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* "AI suy nghĩ gì?" collapsible */}
      <div
        className="border-t pt-3"
        style={{ borderColor: "oklch(0.55 0.18 300 / 0.2)" }}
      >
        <button
          type="button"
          className="flex items-center gap-1.5 text-xs font-medium transition-opacity hover:opacity-80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)] rounded-sm"
          style={{ color: "oklch(0.55 0.18 300)" }}
          onClick={() => setThinkingOpen((p) => !p)}
          aria-expanded={thinkingOpen}
          aria-controls="ai-thinking-content"
        >
          {thinkingOpen ? (
            <ChevronDown size={12} aria-hidden="true" />
          ) : (
            <ChevronRight size={12} aria-hidden="true" />
          )}
          AI suy nghĩ gì?
        </button>

        {thinkingOpen && (
          <div id="ai-thinking-content" className="mt-2">
            <AgentThinkingSection
              caseId={caseId}
              agentFilter="ComplianceAgent"
            />
          </div>
        )}
      </div>
    </section>
  );
}
