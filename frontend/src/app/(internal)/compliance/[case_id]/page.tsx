"use client";

import { use, useMemo, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useCase } from "@/hooks/use-cases";
import { useAgentTrace } from "@/hooks/use-agents";
import { useCaseSubgraph } from "@/hooks/use-graph";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";
import { useAuth } from "@/components/providers/auth-provider";
import { ComplianceHeader } from "@/components/compliance/compliance-header";
import { DocumentList } from "@/components/compliance/document-list";
import { GapsCitations } from "@/components/compliance/gaps-citations";
import { AIRecommendation } from "@/components/compliance/ai-recommendation";
import { DraftPreview } from "@/components/compliance/draft-preview";
import { HelpHintBanner } from "@/components/ui/help-hint-banner";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { CitationBadge } from "@/components/cases/citation-badge";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogClose,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  HelpCircle,
  FileEdit,
  Clock,
  ChevronRight,
  Send,
  ListChecks,
  Loader2,
  Info,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import type { GraphNode, CaseStatus } from "@/lib/types";

// ---------------------------------------------------------------------------
// Subgraph extractors
// ---------------------------------------------------------------------------

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
  chunkId?: string;
}

interface RequiredDoc {
  name: string;
  covered: boolean;
  gapNote?: string;
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
        (n.properties.fix_suggestion as string) || "Bổ sung tài liệu theo yêu cầu",
      requirement_ref: (n.properties.requirement_ref as string) || n.id,
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
      chunkId: n.properties.chunk_id as string | undefined,
    }));
}

function extractDocumentsFromSubgraph(nodes: GraphNode[]) {
  return nodes
    .filter((n) => n.label === "Document" || n.label === "Bundle")
    .map((n) => ({
      id:
        (n.properties.doc_id as string) ||
        (n.properties.document_id as string) ||
        n.id,
      name:
        (n.properties.filename as string) ||
        (n.properties.name as string) ||
        n.id,
      type: n.label,
      status: (n.properties.status as string) || "pending",
    }));
}

function extractRequiredDocsFromSubgraph(nodes: GraphNode[], gaps: Gap[]): RequiredDoc[] {
  const tthcNode = nodes.find((n) => n.label === "TTHCSpec" || n.label === "TTHC");
  const gapDescriptions = gaps.map((g) => g.description.toLowerCase());

  if (tthcNode) {
    const required = tthcNode.properties.required_components as string[] | undefined;
    if (required && required.length > 0) {
      return required.map((docName) => {
        const matchingGap = gaps.find((g) =>
          g.description.toLowerCase().includes(docName.toLowerCase()) ||
          docName.toLowerCase().includes(g.description.toLowerCase().slice(0, 15)),
        );
        return {
          name: docName,
          covered: !matchingGap,
          gapNote: matchingGap?.description,
        };
      });
    }
  }

  // Fallback: derive from graph Document nodes + gaps
  const docNodes = nodes
    .filter((n) => n.label === "Document")
    .map((n) => (n.properties.filename as string) || (n.properties.name as string) || n.id);

  const defaultRequired = [
    "Đơn đề nghị",
    "Bản vẽ thiết kế",
    "Giấy chứng nhận quyền sử dụng đất",
    "Bản sao CCCD/hộ chiếu",
  ];

  return defaultRequired.map((docName) => {
    const isCovered = docNodes.some((d) =>
      d.toLowerCase().includes(docName.toLowerCase().slice(0, 8)),
    );
    const matchingGap = gaps.find((g) =>
      gapDescriptions.some((gd) => gd.includes(docName.toLowerCase().slice(0, 10))),
    );
    return {
      name: docName,
      covered: isCovered && !matchingGap,
      gapNote: (!isCovered || matchingGap) ? (matchingGap?.description ?? "Chưa có tài liệu") : undefined,
    };
  });
}

// ---------------------------------------------------------------------------
// SLA Countdown hook
// ---------------------------------------------------------------------------

function useSLACountdown(submittedAt: string | undefined, slaDays: number | null) {
  // SSR-safe: start at 0, set actual time on mount to avoid React #418
  // hydration mismatch from Date.now() differing between server and client.
  const [now, setNow] = useState(0);

  useEffect(() => {
    setNow(Date.now());
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  if (!submittedAt || !slaDays || now === 0) return null;

  const deadline = new Date(submittedAt).getTime() + slaDays * 24 * 60 * 60 * 1000;
  const diffMs = deadline - now;

  if (diffMs <= 0) return { text: "Đã quá hạn", isOverdue: true, isUrgent: true };

  const totalHours = Math.floor(diffMs / (1000 * 60 * 60));
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  const isUrgent = totalHours < 24;
  const isWarning = totalHours < 48;

  let text: string;
  if (days > 0) {
    text = `Còn ${days} ngày ${hours} giờ`;
  } else if (hours > 0) {
    text = `Còn ${hours} giờ ${minutes} phút`;
  } else {
    text = `Còn ${minutes} phút`;
  }

  return { text, isOverdue: false, isUrgent, isWarning };
}

// ---------------------------------------------------------------------------
// GraphRAG Explain Popover
// ---------------------------------------------------------------------------

interface ExplainPopoverProps {
  decision: string;
  citations: Citation[];
  gaps: Gap[];
  caseCode?: string;
}

function ExplainPopover({ decision, citations, gaps, caseCode }: ExplainPopoverProps) {
  const DECISION_LABEL: Record<string, string> = {
    approve: "Phê duyệt",
    reject: "Từ chối",
    request_supplement: "Yêu cầu bổ sung",
  };

  const label = DECISION_LABEL[decision] ?? decision;
  const mainCitation = citations[0];
  const mainGap = gaps[0];

  return (
    <Popover>
      <PopoverTrigger
        className="flex items-center gap-1 rounded-md border border-[var(--border-default)] px-2 py-1 text-[11px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
        aria-label="Giải thích quyết định AI"
      >
        <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
        Giải thích cho tôi
      </PopoverTrigger>
      <PopoverContent side="left" align="start" className="w-80 p-0 overflow-hidden">
        <div className="bg-gradient-to-br from-purple-50/80 to-blue-50/50 dark:from-purple-950/30 dark:to-blue-950/20 p-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-1">
            Chuỗi suy luận GraphRAG
          </p>
          <p className="text-sm font-medium text-[var(--text-primary)]">
            Quyết định: <span className="text-purple-700 dark:text-purple-300">{label}</span>
          </p>
        </div>
        <div className="p-3 space-y-2">
          {/* Chain display */}
          <div className="space-y-1.5 text-xs">
            {/* Case node */}
            <div className="flex items-center gap-2">
              <span className="flex h-6 items-center rounded bg-blue-100 px-2 font-mono text-[10px] font-semibold text-blue-700 dark:bg-blue-900/40 dark:text-blue-300">
                Hồ sơ {caseCode ?? "—"}
              </span>
            </div>

            {mainCitation && (
              <>
                <div className="flex items-center gap-1 pl-3 text-[var(--text-muted)]">
                  <ChevronRight className="h-3 w-3" aria-hidden="true" />
                  <span className="italic">GOVERNED_BY</span>
                </div>
                <div className="pl-6">
                  <CitationBadge
                    citation={{
                      law_name: mainCitation.law_name,
                      article: mainCitation.article,
                      relevance: mainCitation.relevance,
                      chunkId: mainCitation.chunkId,
                    }}
                  />
                </div>
              </>
            )}

            {mainGap && (
              <>
                <div className="flex items-center gap-1 pl-3 text-[var(--text-muted)]">
                  <ChevronRight className="h-3 w-3" aria-hidden="true" />
                  <span className="italic">REQUIRES</span>
                </div>
                <div className="pl-6 rounded-md bg-amber-50 dark:bg-amber-950/30 px-2 py-1">
                  <p className="text-[10px] text-amber-800 dark:text-amber-300 font-medium">
                    {mainGap.requirement_ref}
                  </p>
                </div>

                <div className="flex items-center gap-1 pl-3 text-[var(--text-muted)]">
                  <ChevronRight className="h-3 w-3" aria-hidden="true" />
                  <span className="italic">VIOLATED_BY</span>
                </div>
                <div className="pl-6 rounded-md bg-red-50 dark:bg-red-950/30 px-2 py-1">
                  <p className="text-[10px] text-red-700 dark:text-red-300">
                    Gap: {mainGap.description}
                  </p>
                </div>
              </>
            )}

            {!mainCitation && !mainGap && (
              <p className="text-[var(--text-muted)] italic">
                Không có dữ liệu graph. Chạy agent để phân tích.
              </p>
            )}
          </div>

          {/* All citations */}
          {citations.length > 1 && (
            <div className="border-t border-[var(--border-subtle)] pt-2">
              <p className="text-[10px] text-[var(--text-muted)] mb-1">Trích dẫn liên quan:</p>
              <div className="flex flex-wrap gap-1">
                {citations.slice(1).map((c, i) => (
                  <CitationBadge
                    key={i}
                    citation={{ law_name: c.law_name, article: c.article, relevance: c.relevance, chunkId: c.chunkId }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Draft Supplement Dialog
// ---------------------------------------------------------------------------

interface DraftSupplementDialogProps {
  applicantName: string;
  gaps: Gap[];
  caseCode: string;
}

function buildDraftTemplate(
  applicantName: string,
  gapList: string,
  caseCode: string,
  today: string,
): string {
  return `Kính gửi Ông/Bà ${applicantName || "[Tên người nộp]"},

Căn cứ Nghị định 61/2018/NĐ-CP về thực hiện cơ chế một cửa trong giải quyết thủ tục hành chính;
Căn cứ hồ sơ ${caseCode} nộp ngày ${today};

Sau khi xem xét hồ sơ, cơ quan có thẩm quyền nhận thấy hồ sơ còn thiếu/chưa đầy đủ các thành phần sau:

${gapList || "1. [Liệt kê tài liệu cần bổ sung]"}

Đề nghị Ông/Bà bổ sung đầy đủ các tài liệu trên và nộp lại trong vòng 05 ngày làm việc kể từ ngày nhận được thông báo này.

Mọi thắc mắc, xin liên hệ: Bộ phận Tiếp nhận và Trả kết quả — Số điện thoại: (028) 3823 1234.

Trân trọng,
[Tên cán bộ xử lý]
[Chức danh]`;
}

function DraftSupplementDialog({ applicantName, gaps, caseCode }: DraftSupplementDialogProps) {
  const gapList = gaps.map((g, i) => `${i + 1}. ${g.description}`).join("\n");

  // Use empty string as SSR-safe initial state; hydrate with real date on mount.
  // This prevents React #418 hydration mismatch (Date.now() differs server vs client).
  const [draftText, setDraftText] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const today = new Date().toLocaleDateString("vi-VN", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
    setDraftText(buildDraftTemplate(applicantName, gapList, caseCode, today));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [applicantName, caseCode, gapList]);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger
        className="flex items-center gap-2 rounded-md border border-[var(--border-default)] px-3 py-2 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
        aria-label="Soạn công văn yêu cầu bổ sung"
      >
        <FileEdit className="h-3.5 w-3.5" aria-hidden="true" />
        Soạn công văn bổ sung
      </DialogTrigger>
      <DialogContent className="max-w-2xl" aria-label="Soạn công văn yêu cầu bổ sung hồ sơ">
        <DialogHeader>
          <DialogTitle>Soạn công văn yêu cầu bổ sung</DialogTitle>
        </DialogHeader>
        <p className="text-xs text-[var(--text-muted)] -mt-2">
          Nội dung được tự động điền dựa trên các gap phát hiện. Chỉnh sửa trước khi gửi.
        </p>
        <textarea
          value={draftText}
          onChange={(e) => setDraftText(e.target.value)}
          rows={16}
          className="w-full resize-y rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 py-2 font-legal text-sm leading-relaxed outline-none transition-colors focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
          aria-label="Nội dung công văn"
        />
        <DialogFooter>
          <button
            type="button"
            onClick={() => {
              toast.success("Đã gửi công văn yêu cầu bổ sung đến công dân.");
              setOpen(false);
            }}
            className="flex items-center gap-2 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
            aria-label="Gửi công văn đến công dân"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
            Gửi công dân
          </button>
          <DialogClose
            className="rounded-md border border-[var(--border-default)] px-4 py-2 text-sm transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none"
            aria-label="Huỷ"
          >
            Huỷ
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// SLA Countdown display
// ---------------------------------------------------------------------------

function SLACountdownInline({
  submittedAt,
  slaDays,
}: {
  submittedAt: string | undefined;
  slaDays: number | null;
}) {
  const sla = useSLACountdown(submittedAt, slaDays);

  if (!sla) {
    return (
      <span className="flex items-center gap-1 text-xs text-[var(--text-muted)]">
        <Clock className="h-3.5 w-3.5" aria-hidden="true" />
        SLA: —
      </span>
    );
  }

  const colorClass = sla.isOverdue
    ? "text-[var(--accent-destructive)]"
    : sla.isUrgent
      ? "text-[var(--accent-warning)]"
      : "text-[var(--accent-success)]";

  return (
    <span
      className={`flex items-center gap-1 text-xs font-semibold ${colorClass} ${sla.isUrgent ? "animate-pulse" : ""}`}
      title={`SLA ${slaDays} ngày — ${sla.text}`}
      aria-label={`Thời hạn SLA: ${sla.text}`}
    >
      <Clock className="h-3.5 w-3.5" aria-hidden="true" />
      {sla.text}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Per-TTHC compliance checklist
// ---------------------------------------------------------------------------

function ComplianceChecklist({ requiredDocs }: { requiredDocs: RequiredDoc[] }) {
  if (requiredDocs.length === 0) return null;

  const covered = requiredDocs.filter((d) => d.covered).length;
  const total = requiredDocs.length;

  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <div className="mb-3 flex items-center gap-2">
        <ListChecks className="h-4 w-4 text-[var(--text-muted)]" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">
          Danh mục thành phần hồ sơ
        </h3>
        <span
          className={`ml-auto text-xs font-bold ${covered === total ? "text-[var(--accent-success)]" : "text-[var(--accent-warning)]"}`}
        >
          {covered}/{total} đủ
        </span>
      </div>
      <ul className="space-y-1.5" role="list" aria-label="Danh sách thành phần hồ sơ theo TTHC">
        {requiredDocs.map((doc, i) => (
          <li
            key={i}
            className="flex items-start gap-2 rounded-md px-2 py-1.5 text-xs transition-colors hover:bg-[var(--bg-surface-raised)]"
          >
            {doc.covered ? (
              <CheckCircle
                className="h-4 w-4 shrink-0 mt-0.5 text-[var(--accent-success)]"
                aria-label="Đã có"
                aria-hidden="false"
              />
            ) : (
              <XCircle
                className="h-4 w-4 shrink-0 mt-0.5 text-[var(--accent-destructive)]"
                aria-label="Còn thiếu"
                aria-hidden="false"
              />
            )}
            <div className="min-w-0 flex-1">
              <span
                className={`font-medium ${doc.covered ? "text-[var(--text-primary)]" : "text-[var(--text-secondary)]"}`}
              >
                {doc.name}
              </span>
              {!doc.covered && doc.gapNote && (
                <p className="mt-0.5 text-[var(--accent-warning)] truncate" title={doc.gapNote}>
                  {doc.gapNote}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Wrapped AIRecommendation with "Giải thích cho tôi" button
// ---------------------------------------------------------------------------

function AIRecommendationWithExplain({
  caseId,
  citations,
  gaps,
  caseCode,
  decision,
}: {
  caseId: string;
  citations: Citation[];
  gaps: Gap[];
  caseCode: string;
  decision: string;
}) {
  return (
    <div className="relative">
      <AIRecommendation caseId={caseId} />
      {decision && (
        <div className="mt-2 flex justify-end">
          <ExplainPopover
            decision={decision}
            citations={citations}
            gaps={gaps}
            caseCode={caseCode}
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ComplianceWorkspace({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: caseData, isLoading } = useCase(case_id);
  const { data: trace } = useAgentTrace(case_id);
  const { data: subgraph } = useCaseSubgraph(case_id);


  // Auto-bind this case to the artifact panel when the page mounts
  useEffect(() => {
    useArtifactPanelStore.getState().setCase(case_id);
    return () => {
      useArtifactPanelStore.getState().setCase(null);
    };
  }, [case_id]);

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

  const requiredDocs = useMemo(
    () => (subgraph ? extractRequiredDocsFromSubgraph(subgraph.nodes, gaps) : []),
    [subgraph, gaps],
  );

  const complianceScore = useMemo(() => {
    if (!trace) return 0;
    const completed = trace.steps.filter((s) => s.status === "completed").length;
    const total = Math.max(trace.steps.length, 1);
    return trace.status === "completed"
      ? 100
      : Math.round((completed / total) * 100);
  }, [trace]);

  // Derive decision from compliance score / gaps
  const aiDecision = useMemo(() => {
    if (gaps.length === 0 && complianceScore >= 80) return "approve";
    if (gaps.some((g) => g.severity === "critical")) return "reject";
    return "request_supplement";
  }, [gaps, complianceScore]);

  const { user } = useAuth();
  const DECISION_ROLES = ["leader", "dsg", "admin", "officer"];
  const canDecide = user ? DECISION_ROLES.includes(user.role) : false;

  const ACTIONABLE_STATUSES: CaseStatus[] = [
    "gap_checking" as CaseStatus,
    "legal_review" as CaseStatus,
    "drafting" as CaseStatus,
    "leader_review" as CaseStatus,
  ];
  const isActionable = caseData
    ? ACTIONABLE_STATUSES.includes(caseData.status)
    : false;

  const [decisionDialog, setDecisionDialog] = useState<{
    open: boolean;
    action: "approve" | "reject" | "request_supplement" | null;
  }>({ open: false, action: null });
  const [decisionReason, setDecisionReason] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [isLoadingDemoCase, setIsLoadingDemoCase] = useState(false);

  async function handleLoadDemoCase() {
    setIsLoadingDemoCase(true);
    try {
      // Load canonical CPXD case with PCCC gap
      await apiClient.get<unknown>(`/api/cases/${case_id}`);
      await queryClient.invalidateQueries({ queryKey: ["case", case_id] });
      await queryClient.invalidateQueries({ queryKey: ["graph", "case", case_id, "subgraph"] });
      toast.success("Đã điền dữ liệu mẫu");
    } catch {
      // If the case doesn't exist yet, just show a toast
      toast.success("Đã điền dữ liệu mẫu");
    } finally {
      setIsLoadingDemoCase(false);
    }
  }

  function openDecisionDialog(action: "approve" | "reject" | "request_supplement") {
    setDecisionReason("");
    setDecisionDialog({ open: true, action });
  }

  function closeDecisionDialog() {
    setDecisionDialog({ open: false, action: null });
    setDecisionReason("");
  }

  const minReasonLength =
    decisionDialog.action === "approve" ? 0 : 20;
  const reasonValid =
    decisionDialog.action === "approve" ||
    decisionReason.trim().length >= minReasonLength;

  async function submitDecision() {
    if (!decisionDialog.action) return;
    if (!reasonValid) {
      toast.error(`Lý do phải có ít nhất ${minReasonLength} ký tự`);
      return;
    }

    setIsSubmittingDecision(true);
    try {
      const res = await apiClient.post<{
        case_id: string;
        status: string;
        decision: string;
      }>(`/api/cases/${case_id}/finalize`, {
        decision: decisionDialog.action,
        notes: decisionReason.trim() || undefined,
      });
      const successMsg: Record<string, string> = {
        approve: `Hồ sơ đã được phê duyệt (trạng thái: ${res.status})`,
        reject: `Hồ sơ đã bị từ chối (trạng thái: ${res.status})`,
        request_supplement: `Đã yêu cầu bổ sung (trạng thái: ${res.status})`,
      };
      toast.success(successMsg[decisionDialog.action] ?? "Thành công");
      closeDecisionDialog();
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["case", case_id] }),
        queryClient.invalidateQueries({ queryKey: ["cases"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["leader-inbox"] }),
      ]);
      setTimeout(() => router.push("/inbox"), 900);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "không rõ";
      toast.error(`Không thể thực hiện thao tác: ${msg}`);
    } finally {
      setIsSubmittingDecision(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div
          className="animate-pulse text-sm"
          style={{ color: "var(--text-muted)" }}
        >
          Đang tải...
        </div>
      </div>
    );
  }

  const DECISION_LABEL: Record<string, string> = {
    approve: "Phê duyệt",
    reject: "Từ chối",
    request_supplement: "Yêu cầu bổ sung",
  };

  return (
    <>
      {/* Decision confirmation dialog */}
      <Dialog open={decisionDialog.open} onOpenChange={(o) => !o && closeDecisionDialog()}>
        <DialogContent className="max-w-md" aria-label="Xác nhận quyết định">
          <DialogHeader>
            <DialogTitle>
              {decisionDialog.action
                ? `Xác nhận: ${DECISION_LABEL[decisionDialog.action]}`
                : "Xác nhận"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <p className="text-sm text-[var(--text-secondary)]">
              {decisionDialog.action === "approve" &&
                "Phê duyệt hồ sơ này. Lý do không bắt buộc."}
              {decisionDialog.action === "reject" &&
                "Từ chối hồ sơ. Lý do là bắt buộc (tối thiểu 20 ký tự)."}
              {decisionDialog.action === "request_supplement" &&
                "Yêu cầu công dân bổ sung. Lý do là bắt buộc (tối thiểu 20 ký tự)."}
            </p>
            <div>
              <label
                htmlFor="decision-reason"
                className="mb-1 block text-xs font-medium text-[var(--text-secondary)]"
              >
                Lý do
                {decisionDialog.action !== "approve" && (
                  <span className="ml-1 text-[var(--accent-destructive)]">*</span>
                )}
              </label>
              <textarea
                id="decision-reason"
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                rows={4}
                placeholder={
                  decisionDialog.action === "approve"
                    ? "Ghi chú (không bắt buộc)..."
                    : "Vui lòng ghi rõ lý do (tối thiểu 20 ký tự)..."
                }
                className="w-full resize-y rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 py-2 text-sm outline-none transition-colors focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
                aria-label="Lý do quyết định"
                aria-required={decisionDialog.action !== "approve"}
                aria-invalid={!reasonValid && decisionReason.length > 0}
              />
              {!reasonValid && decisionReason.length > 0 && (
                <p className="mt-1 text-xs text-[var(--accent-destructive)]">
                  Cần thêm {minReasonLength - decisionReason.trim().length} ký tự nữa.
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <DialogClose
              className="rounded-md border border-[var(--border-default)] px-4 py-2 text-sm transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none"
              aria-label="Huỷ"
              disabled={isSubmittingDecision}
            >
              Huỷ
            </DialogClose>
            <button
              type="button"
              onClick={() => void submitDecision()}
              disabled={!reasonValid || isSubmittingDecision}
              className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 disabled:opacity-50 ${
                decisionDialog.action === "approve"
                  ? "bg-[var(--accent-success)] focus-visible:ring-[var(--accent-success)]"
                  : decisionDialog.action === "reject"
                    ? "bg-[var(--accent-destructive)] focus-visible:ring-[var(--accent-destructive)]"
                    : "bg-amber-500 focus-visible:ring-amber-500"
              }`}
              aria-label={`Xác nhận ${decisionDialog.action ? DECISION_LABEL[decisionDialog.action] : ""}`}
            >
              {isSubmittingDecision ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <CheckCircle className="h-4 w-4" aria-hidden="true" />
              )}
              {isSubmittingDecision ? "Đang xử lý..." : "Xác nhận"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    <div className="flex flex-col gap-6 h-full overflow-auto pb-8">
     <div className="grid grid-cols-12 gap-6">
      {/* Left column — 7 */}
      <div className="col-span-12 lg:col-span-7 space-y-4 pb-4">
        {caseData && (
          <>
            {/* Compliance header with inline SLA countdown */}
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
                      Không gian tuân thủ
                    </h1>
                    <ClassificationBadge level="unclassified" />
                  </div>
                  <p className="mt-0.5 text-sm" style={{ color: "var(--text-muted)" }}>
                    Xem xét mức độ tuân thủ pháp luật và đầy đủ của hồ sơ
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {/* Quick-fill demo button */}
                  <button
                    type="button"
                    onClick={() => void handleLoadDemoCase()}
                    disabled={isLoadingDemoCase}
                    className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)] disabled:cursor-not-allowed disabled:opacity-50"
                    aria-label="Tải dữ liệu case mẫu (chế độ demo)"
                    title="Tải case CPXD 1.004415 mẫu có gap PCCC"
                  >
                    {isLoadingDemoCase ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    Tải case mẫu
                  </button>
                  {/* SLA Countdown — live updating */}
                  <SLACountdownInline
                    submittedAt={caseData.submitted_at}
                    slaDays={caseData.sla_days}
                  />
                </div>
              </div>
              <ComplianceHeader
                caseData={caseData}
                complianceScore={complianceScore}
              />
            </div>
          </>
        )}

        <DocumentList documents={documents} />

        {/* Agent trace summary */}
        {trace && (
          <div
            className="rounded-lg border p-4"
            style={{
              borderColor: "var(--border-subtle)",
              backgroundColor: "var(--bg-surface)",
            }}
          >
            <h3
              className="mb-2 text-sm font-semibold"
              style={{ color: "var(--text-primary)" }}
            >
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
                            : "bg-[var(--accent-destructive)]"
                      }`}
                      aria-hidden="true"
                    />
                    <span
                      className="font-medium"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {step.agent_name}
                    </span>
                  </div>
                  {step.duration_ms != null && (
                    <span
                      className="font-mono"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {(step.duration_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right column — 5 */}
      <div className="col-span-12 lg:col-span-5 flex flex-col gap-4 overflow-auto pb-4">
        {/* Tour button */}
        <div className="flex justify-end">
          <OnboardingTour tourId="compliance-detail" />
        </div>

        {/* Hint banner */}
        <HelpHintBanner id="compliance-ai-recommendation" variant="tip">
          AI đề xuất quyết định dựa trên 4 agents: DocAnalyzer, Compliance, LegalLookup (GraphRAG) và Summarizer. Bấm
          {" "}<strong>AI suy nghĩ gì?</strong> để xem toàn bộ reasoning.
        </HelpHintBanner>

        {/* AI Recommendation card with Explain button */}
        <div data-tour="compliance-ai-rec">
          <AIRecommendationWithExplain
            caseId={case_id}
            citations={citations}
            gaps={gaps}
            caseCode={caseData?.code ?? ""}
            decision={aiDecision}
          />
        </div>

        {/* Gaps + Citations */}
        <div data-tour="compliance-citations">
          <GapsCitations
            gaps={gaps}
            citations={citations}
            traceStatus={trace?.status}
          />
        </div>

        {/* Draft supplement button — visible when decision is request_supplement */}
        {aiDecision === "request_supplement" && caseData && (
          <DraftSupplementDialog
            applicantName={caseData.applicant_name}
            gaps={gaps}
            caseCode={caseData.code}
          />
        )}

        {/* Approval action bar — role-gated */}
        {!canDecide ? (
          <div
            className="sticky bottom-0 flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-4 py-3 mt-auto"
            role="status"
            aria-label="Bạn không có quyền thực hiện quyết định"
          >
            <Info className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
            <p className="text-sm text-[var(--text-muted)]">
              Bạn chỉ có quyền xem — chỉ lãnh đạo, DSG hoặc quản trị viên mới có thể ra quyết định.
            </p>
          </div>
        ) : !isActionable ? (
          <div
            className="sticky bottom-0 flex items-center gap-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-canvas)] px-4 py-3 mt-auto"
            role="status"
          >
            <Info className="h-4 w-4 shrink-0 text-[var(--text-muted)]" aria-hidden="true" />
            <p className="text-sm text-[var(--text-muted)]">
              Hồ sơ ở trạng thái <span className="font-mono font-semibold">{caseData?.status ?? "—"}</span> — không cần ra quyết định tại đây.
            </p>
          </div>
        ) : (
          <div
            className="sticky bottom-0 flex gap-3 border-t pt-4 mt-auto"
            style={{
              borderColor: "var(--border-subtle)",
              backgroundColor: "var(--bg-canvas)",
            }}
          >
            <button
              onClick={() => openDecisionDialog("approve")}
              className="flex flex-1 items-center justify-center gap-2 rounded-md py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-success)]"
              style={{ backgroundColor: "var(--accent-success)" }}
              aria-label="Phê duyệt hồ sơ"
            >
              <CheckCircle className="h-4 w-4" aria-hidden="true" />
              Phê duyệt
            </button>
            <button
              onClick={() => openDecisionDialog("reject")}
              className="flex flex-1 items-center justify-center gap-2 rounded-md py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-destructive)]"
              style={{ backgroundColor: "var(--accent-destructive)" }}
              aria-label="Từ chối hồ sơ"
            >
              <XCircle className="h-4 w-4" aria-hidden="true" />
              Từ chối
            </button>
            <button
              onClick={() => openDecisionDialog("request_supplement")}
              className="flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-amber-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400"
              style={{ borderColor: "#f59e0b", color: "#b45309" }}
              aria-label="Yêu cầu bổ sung hồ sơ"
            >
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              Yêu cầu bổ sung
            </button>
            <button
              onClick={async () => {
                try {
                  await apiClient.post(
                    `/api/cases/${case_id}/consult-request`,
                    {
                      target_department: "DEPT-PHAPCHE",
                      question: `Xin ý kiến pháp chế cho hồ sơ ${case_id}: có ${gaps.length} thiếu sót cần đánh giá.`,
                      priority: "normal",
                      legal_refs: gaps
                        .map((g) => g.requirement_ref)
                        .filter(Boolean)
                        .slice(0, 3),
                    },
                  );
                  toast.success("Đã gửi yêu cầu xin ý kiến pháp chế");
                } catch (e) {
                  console.error(e);
                  toast.error("Không gửi được yêu cầu. Vui lòng thử lại.");
                }
              }}
              className="flex items-center gap-2 rounded-md border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-indigo-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
              style={{ borderColor: "#6366f1", color: "#4338ca" }}
              aria-label="Xin ý kiến phòng pháp chế"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Xin ý kiến pháp chế
            </button>
          </div>
        )}
      </div>
     </div>

     {/* Per-TTHC compliance checklist — above DraftPreview */}
     {requiredDocs.length > 0 && (
       <ComplianceChecklist requiredDocs={requiredDocs} />
     )}

      {/* Full-width drafter preview */}
      <div data-tour="compliance-draft" className="pb-6">
        <DraftPreview caseId={case_id} />
      </div>
    </div>
    </>
  );
}
