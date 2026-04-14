"use client";

import { use, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useCase } from "@/hooks/use-cases";
import { useAgentTrace } from "@/hooks/use-agents";
import { useCaseSubgraph } from "@/hooks/use-graph";
import { GapCard } from "@/components/cases/gap-card";
import { CitationBadge } from "@/components/cases/citation-badge";
import { AnimatedCounter } from "@/components/ui/animated-counter";
import {
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import type { GraphNode } from "@/lib/types";

interface Gap {
  id: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  fix_suggestion: string;
  requirement_ref: string;
}

interface Citation {
  law_name: string;
  article: string;
  relevance: number;
}

function extractGapsFromSubgraph(nodes: GraphNode[]): Gap[] {
  return nodes
    .filter((n) => n.label === "Gap")
    .map((n, i) => ({
      id: (n.properties.gap_id as string) || `GAP-${i + 1}`,
      description:
        (n.properties.description as string) || "Thiếu thành phần hồ sơ",
      severity: (n.properties.severity as Gap["severity"]) || "medium",
      fix_suggestion:
        (n.properties.fix_suggestion as string) ||
        "Bổ sung tài liệu theo yêu cầu",
      requirement_ref:
        (n.properties.requirement_ref as string) || n.id,
    }));
}

function extractCitationsFromSubgraph(nodes: GraphNode[]): Citation[] {
  return nodes
    .filter(
      (n) =>
        n.label === "Citation" ||
        n.label === "Article" ||
        n.label === "Clause",
    )
    .map((n) => ({
      law_name:
        (n.properties.law_name as string) ||
        (n.properties.document_name as string) ||
        "Văn bản pháp luật",
      article:
        (n.properties.article_number as string) ||
        (n.properties.clause_path as string) ||
        n.id,
      relevance: (n.properties.relevance as number) || 0.85,
    }));
}

function extractDocumentsFromSubgraph(nodes: GraphNode[]) {
  return nodes
    .filter((n) => n.label === "Document" || n.label === "Bundle")
    .map((n) => ({
      id: n.id,
      name:
        (n.properties.filename as string) ||
        (n.properties.name as string) ||
        n.id,
      type: n.label,
      status: (n.properties.status as string) || "pending",
    }));
}

export default function ComplianceWorkspace({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const router = useRouter();
  const { data: caseData, isLoading } = useCase(case_id);
  const { data: trace } = useAgentTrace(case_id);
  const { data: subgraph } = useCaseSubgraph(case_id);

  const gaps = useMemo(
    () => (subgraph ? extractGapsFromSubgraph(subgraph.nodes) : []),
    [subgraph],
  );

  const citations = useMemo(
    () => (subgraph ? extractCitationsFromSubgraph(subgraph.nodes) : []),
    [subgraph],
  );

  const documents = useMemo(
    () => (subgraph ? extractDocumentsFromSubgraph(subgraph.nodes) : []),
    [subgraph],
  );

  const complianceScore = useMemo(() => {
    if (!trace) return 0;
    const completed = trace.steps.filter(
      (s) => s.status === "completed",
    ).length;
    const total = Math.max(trace.steps.length, 1);
    return trace.status === "completed"
      ? 100
      : Math.round((completed / total) * 100);
  }, [trace]);

  async function handleDecision(
    decision: "approve" | "reject" | "supplement",
  ) {
    const confirmMessages: Record<typeof decision, string> = {
      approve: "Bạn có chắc chắn muốn phê duyệt hồ sơ này?",
      reject: "Bạn có chắc chắn muốn từ chối hồ sơ này? Vui lòng ghi rõ lý do.",
      supplement: "Yêu cầu công dân bổ sung hồ sơ?",
    };
    if (!window.confirm(confirmMessages[decision])) return;

    try {
      await apiClient.post(`/api/cases/${case_id}/finalize`, {
        decision,
      });
      toast.success(
        decision === "approve"
          ? "Hồ sơ đã được phê duyệt"
          : decision === "reject"
            ? "Hồ sơ đã bị từ chối"
            : "Đã yêu cầu bổ sung",
      );
    } catch {
      toast.error("Không thể thực hiện thao tác");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-[var(--text-muted)]">
          Đang tải...
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full gap-4">
      {/* Left: Documents + Agent trace */}
      <div className="flex-1 space-y-3 overflow-auto">
        {/* Page subtitle */}
        <div>
          <h1 className="text-lg font-bold">Không gian tuân thủ</h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Xem xét mức độ tuân thủ pháp luật và đầy đủ của hồ sơ
          </p>
        </div>

        {/* Case info */}
        {caseData && (
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-[var(--text-muted)]" />
                <div>
                  <p className="text-sm font-medium">
                    {caseData.code} · {caseData.tthc_code}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {caseData.applicant_name} · {caseData.status}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Compliance score */}
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">Điểm tuân thủ</h3>
            <span className="text-lg font-bold">
              <AnimatedCounter value={complianceScore} suffix="%" />
            </span>
          </div>
          <div
            className="mt-2 h-2 overflow-hidden rounded-full bg-[var(--bg-surface-raised)]"
            role="progressbar"
            aria-valuenow={complianceScore}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${complianceScore}%`,
                backgroundColor:
                  complianceScore >= 80
                    ? "var(--accent-success)"
                    : complianceScore >= 50
                      ? "var(--accent-warning)"
                      : "var(--accent-error)",
              }}
            />
          </div>
          <p className="mt-2 text-xs text-[var(--text-muted)]">
            {complianceScore >= 80
              ? "Hồ sơ đạt yêu cầu, có thể phê duyệt"
              : complianceScore >= 50
                ? "Hồ sơ cần bổ sung một số thành phần"
                : "Hồ sơ thiếu nhiều thành phần bắt buộc"}
          </p>
        </div>

        {/* Document list */}
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <h3 className="mb-2 text-sm font-semibold">
            Tài liệu ({documents.length})
          </h3>
          {documents.length === 0 ? (
            <p className="text-sm text-[var(--text-muted)]">
              Chưa có tài liệu
            </p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => router.push(`/documents/${doc.id}`)}
                  className="flex cursor-pointer items-center justify-between rounded-md border border-[var(--border-subtle)] p-2 text-sm transition-colors hover:bg-[var(--bg-surface-raised)]"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-[var(--text-muted)]" />
                    <span>{doc.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-[var(--bg-surface-raised)] px-1.5 py-0.5 text-[10px]">
                      {doc.status}
                    </span>
                    <ExternalLink className="h-3 w-3 text-[var(--text-muted)]" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Agent trace */}
        {trace && (
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="mb-2 text-sm font-semibold">
              Agent Trace ({trace.status})
            </h3>
            <div className="space-y-1">
              {trace.steps.map((step) => (
                <div
                  key={step.step_id}
                  className="flex items-center justify-between text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-block h-2 w-2 rounded-full ${
                        step.status === "completed"
                          ? "bg-[var(--accent-success)]"
                          : step.status === "running"
                            ? "animate-pulse bg-[var(--accent-primary)]"
                            : "bg-[var(--accent-error)]"
                      }`}
                    />
                    <span className="font-medium">{step.agent_name}</span>
                  </div>
                  {step.duration_ms != null && (
                    <span className="font-mono text-[var(--text-muted)]">
                      {(step.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right: Gaps + Citations + Actions */}
      <div className="flex flex-1 flex-col overflow-auto">
        <div className="flex-1 space-y-4">
          {/* Gaps */}
          <div>
            <h2 className="font-semibold">Thiếu sót ({gaps.length})</h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Các thiếu sót phát hiện bởi hệ thống AI. Mỗi thiếu sót cần được khắc phục trước khi phê duyệt
            </p>
          </div>
          {gaps.length === 0 ? (
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 text-center text-sm text-[var(--text-muted)]">
              {trace?.status === "completed"
                ? "Không phát hiện thiếu sót"
                : "Đang kiểm tra..."}
            </div>
          ) : (
            <div className="space-y-2">
              {gaps.map((gap) => (
                <GapCard key={gap.id} gap={gap} />
              ))}
            </div>
          )}

          {/* Citations */}
          <div className="mt-4">
            <h2 className="font-semibold">
              Căn cứ pháp lý ({citations.length})
            </h2>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              Căn cứ pháp lý liên quan đến hồ sơ này
            </p>
          </div>
          {citations.length === 0 ? (
            <div className="text-sm text-[var(--text-muted)]">
              {trace?.status === "completed"
                ? "Không có trích dẫn pháp lý"
                : "Đang tra cứu..."}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {citations.map((c, i) => (
                <CitationBadge key={i} citation={c} />
              ))}
            </div>
          )}

          {/* Summary tabs - if trace has summarizer output */}
          {trace?.steps.some(
            (s) =>
              s.agent_name === "Summarizer" && s.status === "completed",
          ) && (
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
              <h3 className="mb-2 text-sm font-semibold">Tóm tắt</h3>
              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                Hồ sơ đã được tóm tắt bởi AI. Xem chi tiết trong Trace
                Viewer.
              </p>
            </div>
          )}
        </div>

        {/* Action bar */}
        <div className="sticky bottom-0 flex gap-3 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <button
            onClick={() => handleDecision("approve")}
            className="flex flex-1 items-center justify-center gap-2 rounded-md bg-[var(--accent-success)] py-2.5 font-medium text-white transition-opacity hover:opacity-90"
          >
            <CheckCircle className="h-4 w-4" />
            Phê duyệt
          </button>
          <button
            onClick={() => handleDecision("reject")}
            className="flex flex-1 items-center justify-center gap-2 rounded-md bg-[var(--accent-error)] py-2.5 font-medium text-white transition-opacity hover:opacity-90"
          >
            <XCircle className="h-4 w-4" />
            Từ chối
          </button>
          <button
            onClick={() => handleDecision("supplement")}
            className="flex items-center gap-2 rounded-md border border-[var(--border-default)] px-4 py-2.5 transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            <AlertTriangle className="h-4 w-4" />
            Yêu cầu bổ sung
          </button>
        </div>
      </div>
    </div>
  );
}
