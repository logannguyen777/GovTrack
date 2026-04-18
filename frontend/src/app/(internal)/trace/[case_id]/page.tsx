"use client";

import { use, useCallback, useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import { useCaseSubgraph } from "@/hooks/use-graph";
import { useAgentTrace } from "@/hooks/use-agents";
import { useWSTopic } from "@/hooks/use-ws";
import { useQueryClient } from "@tanstack/react-query";
import { useAgentArtifact } from "@/hooks/use-agent-artifact";
import { useArtifactPanelStore } from "@/lib/stores/artifact-panel-store";
import { ThinkingTab } from "@/components/agents/tabs/thinking-tab";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  AlertTriangle,
  CheckCircle,
  X,
  ChevronDown,
  ChevronRight as ChevronRightIcon,
  Zap,
  Sparkles,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton-card";
import { TraceReplayButton } from "@/components/trace/trace-replay-button";
import { ReplayScrubber } from "@/components/trace/replay-scrubber";
import { OnboardingTour } from "@/components/onboarding/onboarding-tour";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { motion, AnimatePresence } from "framer-motion";
import type { WSMessage, AgentStepResponse } from "@/lib/types";
import type { WSNodeUpdate } from "@/components/graph/CaseSubgraphPanel";

// ---------------------------------------------------------------------------
// Dynamic import — splits @xyflow/react + @dagrejs/dagre into a separate
// async chunk so the initial trace page JS is smaller.
// ---------------------------------------------------------------------------

const CaseSubgraphPanel = dynamic(
  () =>
    import("@/components/graph/CaseSubgraphPanel").then(
      (m) => ({ default: m.CaseSubgraphPanel }),
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" aria-hidden="true" />
        <div className="w-full max-w-md space-y-3">
          <div className="flex justify-center gap-6">
            <Skeleton className="h-14 w-48" />
            <Skeleton className="h-14 w-48" />
          </div>
          <div className="flex justify-center gap-6">
            <Skeleton className="h-14 w-48" />
            <Skeleton className="h-14 w-48" />
            <Skeleton className="h-14 w-48" />
          </div>
          <div className="flex justify-center gap-6">
            <Skeleton className="h-14 w-48" />
          </div>
        </div>
        <p className="text-xs text-[var(--text-muted)]">Đang tải đồ thị...</p>
      </div>
    ),
  },
);

// ---------------------------------------------------------------------------
// Cost formatter
// ---------------------------------------------------------------------------

const COST_PER_1K_INPUT = 0.0008;
const COST_PER_1K_OUTPUT = 0.002;

function formatCost(inputTokens: number, outputTokens: number): string {
  const vnd =
    (inputTokens * COST_PER_1K_INPUT + outputTokens * COST_PER_1K_OUTPUT) /
    1000;
  return vnd < 0.01 ? "< ₫0.01" : `₫${vnd.toFixed(2)}`;
}

// AI pipeline stage descriptions for the thinking strip
const AGENT_VI: Record<string, string> = {
  planner: "Planner lập kế hoạch",
  doc_analyze_agent: "DocAnalyzer đang OCR",
  classifier: "Classifier phân loại TTHC",
  compliance: "Compliance kiểm tra khoảng trống",
  legal_lookup: "LegalLookup traverse Knowledge Graph",
  router: "Router gán phòng ban",
  consult: "Consult xin ý kiến",
  summarizer: "Summarizer tóm tắt hồ sơ",
  drafter: "Drafter đang soạn văn bản",
  security_officer: "SecurityOfficer kiểm tra bảo mật",
};

// ---------------------------------------------------------------------------
// AI Thinking Strip
// ---------------------------------------------------------------------------

function AiThinkingStrip({
  steps,
  traceStatus,
}: {
  steps: AgentStepResponse[];
  traceStatus: string;
}) {
  const running = steps.find((s) => s.status === "running");
  const lastCompleted = [...steps]
    .reverse()
    .find((s) => s.status === "completed");
  const current = running ?? lastCompleted;
  const isDone = traceStatus === "completed" && !running;

  const label = isDone
    ? "Tất cả agent đã hoàn thành"
    : current
      ? `${AGENT_VI[current.agent_name] ?? current.agent_name}...`
      : "Đang khởi động pipeline...";

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={label}
        initial={{ opacity: 0, x: -6 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 6 }}
        transition={{ duration: 0.25 }}
        className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${
          isDone
            ? "border-[var(--accent-success)]/40 bg-[var(--accent-success)]/5 text-[var(--accent-success)]"
            : "border-[var(--accent-primary)]/40 bg-[var(--accent-primary)]/5 text-[var(--accent-primary)]"
        }`}
        aria-live="polite"
        aria-label="Trạng thái xử lý AI"
      >
        {isDone ? (
          <CheckCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        ) : (
          <span className="h-2 w-2 shrink-0 animate-pulse rounded-full bg-current" aria-hidden="true" />
        )}
        <span>{label}</span>
      </motion.div>
    </AnimatePresence>
  );
}

// ---------------------------------------------------------------------------
// Step detail dialog
// ---------------------------------------------------------------------------

interface StepDetailDialogProps {
  step: AgentStepResponse;
  onClose: () => void;
}

function StepDetailDialog({ step, onClose }: StepDetailDialogProps) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`Chi tiết bước ${step.agent_name}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 8 }}
        transition={{ duration: 0.2 }}
        className="flex max-h-[80vh] w-[560px] flex-col overflow-hidden rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] px-5 py-3">
          <div>
            <p className="text-sm font-bold text-[var(--text-primary)]">
              {AGENT_VI[step.agent_name] ?? step.agent_name}
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              {step.agent_name.includes("Doc") || step.agent_name.includes("Analyzer")
                ? "Qwen3-VL-Plus"
                : "Qwen3-Max"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            aria-label="Đóng"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 space-y-4 overflow-auto p-5">
          <div className="flex flex-wrap gap-3">
            <Pill
              label="Trạng thái"
              value={
                (
                  {
                    completed: "Hoàn thành",
                    running: "Đang chạy",
                    failed: "Lỗi",
                    pending: "Chờ",
                  } as Record<string, string>
                )[step.status] ?? step.status
              }
              color={
                step.status === "completed"
                  ? "var(--accent-success)"
                  : step.status === "running"
                    ? "var(--accent-primary)"
                    : "var(--accent-destructive)"
              }
            />
            {step.duration_ms != null && (
              <Pill
                label="Thời gian"
                value={`${(step.duration_ms / 1000).toFixed(2)}s`}
              />
            )}
            <Pill
              label="Tokens"
              value={`${step.input_tokens + step.output_tokens}`}
            />
            <Pill
              label="Chi phí ước tính"
              value={formatCost(step.input_tokens, step.output_tokens)}
            />
            {step.tool_calls > 0 && (
              <Pill label="Tool calls" value={String(step.tool_calls)} />
            )}
          </div>

          <Section title="Hành động">
            <p className="text-sm leading-relaxed text-[var(--text-primary)]">
              {step.action || "—"}
            </p>
          </Section>

          <Section title="Chi tiết token">
            <div className="grid grid-cols-2 gap-2">
              <TokenRow label="Input tokens" value={step.input_tokens} />
              <TokenRow label="Output tokens" value={step.output_tokens} />
            </div>
          </Section>

          <div>
            <button
              onClick={() => setThinkingExpanded((v) => !v)}
              className="flex w-full items-center justify-between rounded-md border border-[var(--border-subtle)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              aria-expanded={thinkingExpanded}
            >
              <span>Thinking (suy luận nội bộ)</span>
              {thinkingExpanded ? (
                <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <ChevronRightIcon className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </button>
            <AnimatePresence>
              {thinkingExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <pre className="mt-1 max-h-48 overflow-auto rounded-md bg-[var(--bg-surface-raised)] p-3 font-mono text-[10px] leading-relaxed text-[var(--text-secondary)] whitespace-pre-wrap">
                    {`Agent: ${step.agent_name}\nAction: ${step.action}\nStatus: ${step.status}\nStarted: ${step.started_at ?? "—"}\nFinished: ${step.finished_at ?? "—"}`}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

function Pill({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-2.5 py-1.5">
      <p className="text-[9px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
        {label}
      </p>
      <p
        className="mt-0.5 text-xs font-medium"
        style={{ color: color ?? "var(--text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
        {title}
      </p>
      {children}
    </div>
  );
}

function TokenRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-2.5 py-1.5">
      <p className="text-[9px] text-[var(--text-muted)]">{label}</p>
      <p className="mt-0.5 font-mono text-xs font-medium text-[var(--text-primary)]">
        {value.toLocaleString("vi-VN")}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function TraceViewer({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [replayCutoff, setReplayCutoff] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<AgentStepResponse | null>(
    null,
  );
  const [wsActive, setWsActive] = useState(false);
  const [pendingUpdate, setPendingUpdate] = useState<WSNodeUpdate | null>(null);

  // Replay 60s state
  const [replaying60, setReplaying60] = useState(false);
  const replay60Ref = useRef<ReturnType<typeof setInterval> | null>(null);

  const {
    data: subgraph,
    isLoading: subgraphLoading,
    error: subgraphError,
    refetch: refetchSubgraph,
  } = useCaseSubgraph(case_id);
  const {
    data: trace,
    isLoading: traceLoading,
    error: traceError,
    refetch: refetchTrace,
  } = useAgentTrace(case_id);

  const artifactData = useAgentArtifact(case_id);
  const runningAgentIds = new Set(
    artifactData.activeAgents
      .filter((a) => a.status === "running")
      .map((a) => a.id.split(":")[0]),
  );

  useEffect(() => {
    useArtifactPanelStore.getState().setCase(case_id);
    return () => {
      useArtifactPanelStore.getState().setCase(null);
    };
  }, [case_id]);

  // WebSocket live updates
  const handleWS = useCallback(
    (msg: WSMessage) => {
      setWsActive(true);
      const payload = msg.data as Record<string, unknown>;

      if (
        msg.event === "node_added" ||
        msg.event === "edge_added" ||
        msg.event === "status_changed"
      ) {
        setPendingUpdate({ event: msg.event as WSNodeUpdate["event"], payload });
      }

      // Invalidate trace query for any WS event on this case/trace topic
      void queryClient.invalidateQueries({ queryKey: ["trace", case_id] });
    },
    [queryClient, case_id],
  );

  useWSTopic(`case:${case_id}`, handleWS);
  useWSTopic(`trace:${case_id}`, handleWS);

  // 5s polling fallback when WS not active
  useEffect(() => {
    if (wsActive) return;
    const id = setInterval(() => {
      void refetchTrace();
      void refetchSubgraph();
    }, 5000);
    return () => clearInterval(id);
  }, [wsActive, refetchTrace, refetchSubgraph]);

  // ---------------------------------------------------------------------------
  // Replay 60s handler
  // ---------------------------------------------------------------------------

  function startReplay60() {
    if (!trace?.steps || trace.steps.length === 0) return;
    setReplaying60(true);

    const sorted = [...trace.steps]
      .filter((s) => s.started_at)
      .sort(
        (a, b) =>
          new Date(a.started_at!).getTime() -
          new Date(b.started_at!).getTime(),
      );

    if (sorted.length === 0) {
      setReplaying60(false);
      return;
    }

    const intervalMs = 60000 / Math.max(sorted.length, 1);
    let idx = 0;

    setReplayCutoff(sorted[0].started_at ?? null);

    replay60Ref.current = setInterval(() => {
      idx++;
      if (idx >= sorted.length) {
        setReplayCutoff(null);
        setReplaying60(false);
        if (replay60Ref.current) clearInterval(replay60Ref.current);
        return;
      }
      setReplayCutoff(sorted[idx].started_at ?? null);
    }, intervalMs);
  }

  useEffect(() => {
    return () => {
      if (replay60Ref.current) clearInterval(replay60Ref.current);
    };
  }, []);

  const bothLoading = subgraphLoading && traceLoading;

  // ---------------------------------------------------------------------------
  // Loading skeleton
  // ---------------------------------------------------------------------------

  if (bothLoading) {
    return (
      <div className="flex h-full gap-4">
        <div className="flex-[7] flex flex-col items-center justify-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8">
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" aria-hidden="true" />
            Đang tải trace...
          </div>
          <div className="w-full space-y-3">
            <div className="flex justify-center gap-6">
              <Skeleton className="h-14 w-48" />
              <Skeleton className="h-14 w-48" />
            </div>
            <div className="flex justify-center gap-6">
              <Skeleton className="h-14 w-48" />
              <Skeleton className="h-14 w-48" />
              <Skeleton className="h-14 w-48" />
            </div>
            <div className="flex justify-center gap-6">
              <Skeleton className="h-14 w-48" />
            </div>
          </div>
        </div>
        <div className="flex-[3] space-y-3 overflow-auto">
          <Skeleton className="h-5 w-28" />
          {[...Array(5)].map((_, i) => (
            <div
              key={i}
              className="space-y-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3"
            >
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-2 w-20" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <>
      {/* Step detail dialog */}
      <AnimatePresence>
        {selectedStep && (
          <StepDetailDialog
            step={selectedStep}
            onClose={() => setSelectedStep(null)}
          />
        )}
      </AnimatePresence>

      <div className="flex h-full flex-col gap-4">
        {/* Page header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h1
                className="text-2xl font-bold"
                style={{ color: "var(--text-primary)" }}
              >
                Theo dõi xử lý AI
              </h1>
              <ClassificationBadge level="unclassified" />
            </div>
            <p
              className="mt-1 text-sm"
              style={{ color: "var(--text-muted)" }}
            >
              Đồ thị Knowledge Graph và các bước xử lý tự động của agent AI
              cho hồ sơ{" "}
              <span className="font-mono">{case_id.slice(0, 8)}</span>
            </p>
          </div>

          <div className="flex shrink-0 items-center gap-2 pt-1">
            {case_id !== "CASE-2026-0001" && (
              <button
                type="button"
                onClick={() => router.push("/trace/CASE-2026-0001")}
                className="flex items-center gap-1.5 rounded-md border border-purple-300 bg-gradient-to-r from-purple-600 to-violet-600 px-4 py-1.5 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90"
                title="Mở hồ sơ CPXD mẫu có gap PCCC"
              >
                <Sparkles className="h-4 w-4" aria-hidden="true" />
                Xem case mẫu
              </button>
            )}
            {trace?.steps && trace.steps.length > 0 && (
              <AiThinkingStrip
                steps={trace.steps}
                traceStatus={trace.status}
              />
            )}

            <OnboardingTour tourId="trace-viewer" />
            <div data-tour="trace-replay">
              <TraceReplayButton caseId={case_id} />
            </div>
          </div>
        </div>

        {/* Replay scrubber + Replay 60s button */}
        {trace?.steps && trace.steps.length > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <ReplayScrubber
                steps={trace.steps.map((s) => ({
                  started_at: s.started_at ?? "",
                  agent_name: s.agent_name,
                  status: s.status,
                }))}
                onCutoffChange={setReplayCutoff}
              />
            </div>

            {/* Replay 60s button */}
            <button
              onClick={startReplay60}
              disabled={replaying60}
              className="flex shrink-0 items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)] disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              aria-label="Phát lại toàn bộ pipeline trong 60 giây"
              title="Tua nhanh toàn bộ pipeline trong 60 giây"
            >
              <Zap
                className={`h-3.5 w-3.5 ${replaying60 ? "animate-pulse text-[var(--accent-primary)]" : ""}`}
                aria-hidden="true"
              />
              {replaying60 ? "Đang tua..." : "Replay 60s"}
            </button>
          </div>
        )}

        <div className="flex flex-1 gap-4 overflow-hidden min-h-0">
          {/* Graph panel — 60% — dynamically loaded */}
          <div
            data-tour="trace-graph"
            className="flex-[6] rounded-lg border overflow-hidden"
            style={{
              borderColor: "var(--border-subtle)",
              backgroundColor: "var(--bg-surface)",
            }}
          >
            <CaseSubgraphPanel
              subgraph={subgraph}
              subgraphError={subgraphError as Error | null}
              onRefetch={() => void refetchSubgraph()}
              pendingUpdate={pendingUpdate}
            />
          </div>

          {/* Right panel — 40% */}
          <div className="flex-[4] flex flex-col overflow-hidden min-h-0">
            <Tabs
              defaultValue="steps"
              className="flex-1 flex flex-col overflow-hidden"
            >
              <TabsList
                variant="line"
                className="w-full justify-start border-b rounded-none px-3 shrink-0 h-auto py-0 bg-transparent gap-0"
                style={{ borderColor: "var(--border-subtle)" }}
              >
                <TabsTrigger
                  value="steps"
                  className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
                >
                  Các bước AI
                </TabsTrigger>
                <TabsTrigger
                  value="thinking"
                  className="text-xs px-3 py-2 rounded-none border-b-2 border-transparent data-active:border-[var(--accent-primary)]"
                >
                  Suy nghĩ trực tiếp
                </TabsTrigger>
              </TabsList>

              {/* Steps tab */}
              <TabsContent
                value="steps"
                className="flex-1 overflow-auto p-0 m-0"
              >
                <div
                  className="p-3 space-y-2 h-full overflow-auto"
                  data-tour="trace-steps"
                >
                  {traceError ? (
                    <div
                      className="flex items-center gap-3 rounded-md border p-3"
                      style={{
                        borderColor: "var(--border-subtle)",
                        backgroundColor: "var(--bg-surface)",
                      }}
                    >
                      <AlertTriangle
                        className="h-4 w-4 shrink-0"
                        style={{ color: "var(--accent-destructive)" }}
                        aria-hidden="true"
                      />
                      <div className="flex-1">
                        <p
                          className="text-xs font-semibold"
                          style={{ color: "var(--text-primary)" }}
                        >
                          Không thể tải các bước xử lý AI
                        </p>
                      </div>
                      <button
                        onClick={() => void refetchTrace()}
                        className="rounded border px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                        style={{ borderColor: "var(--border-default)" }}
                      >
                        Thử lại
                      </button>
                    </div>
                  ) : trace ? (
                    <>
                      <div
                        className="flex items-center gap-2 text-xs"
                        style={{ color: "var(--text-muted)" }}
                      >
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${
                            trace.status === "running"
                              ? "animate-pulse bg-[var(--accent-primary)]"
                              : trace.status === "completed"
                                ? "bg-[var(--accent-success)]"
                                : "bg-[var(--accent-destructive)]"
                          }`}
                          aria-hidden="true"
                        />
                        {(
                          {
                            running: "Đang chạy",
                            completed: "Hoàn thành",
                            failed: "Lỗi",
                          } as Record<string, string>
                        )[trace.status] ?? trace.status}{" "}
                        · {trace.total_tokens} token ·{" "}
                        {(trace.total_duration_ms / 1000).toFixed(1)}s
                      </div>

                      {trace.steps
                        .filter((step) => {
                          if (!replayCutoff) return true;
                          if (!step.started_at) return true;
                          return (
                            new Date(step.started_at).getTime() <=
                            new Date(replayCutoff).getTime()
                          );
                        })
                        .map((step) => {
                          const STEP_STATUS_VI: Record<string, string> = {
                            completed: "Hoàn thành",
                            running: "Đang chạy",
                            failed: "Lỗi",
                            pending: "Chờ",
                          };
                          return (
                            <button
                              key={step.step_id}
                              onClick={() => setSelectedStep(step)}
                              className="w-full rounded-md border p-3 text-left transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-primary)]"
                              style={{
                                borderColor: "var(--border-subtle)",
                                backgroundColor: "var(--bg-surface)",
                              }}
                              aria-label={`Xem chi tiết bước ${step.agent_name}`}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1">
                                  <p
                                    className="text-xs font-bold"
                                    style={{ color: "var(--text-primary)" }}
                                  >
                                    {step.agent_name}
                                  </p>
                                  <span
                                    className="ml-1 rounded px-1 py-0.5 text-[9px]"
                                    style={{
                                      backgroundColor: "var(--accent-primary)",
                                      color: "#fff",
                                      opacity: 0.8,
                                    }}
                                  >
                                    {step.agent_name.includes("Doc") ||
                                    step.agent_name.includes("Analyzer")
                                      ? "Qwen3-VL"
                                      : "Qwen3-Max"}
                                  </span>
                                </div>
                                <span
                                  className="text-[10px]"
                                  style={{
                                    color:
                                      step.status === "completed"
                                        ? "var(--accent-success)"
                                        : step.status === "running"
                                          ? "var(--accent-primary)"
                                          : "var(--accent-destructive)",
                                  }}
                                >
                                  {STEP_STATUS_VI[step.status] ?? step.status}
                                </span>
                              </div>

                              <p
                                className="mt-1 text-xs"
                                style={{ color: "var(--text-muted)" }}
                              >
                                {step.action}
                              </p>

                              {step.duration_ms != null && (
                                <div
                                  className="mt-1 flex items-center gap-2 font-mono text-[10px]"
                                  style={{ color: "var(--text-muted)" }}
                                >
                                  <span>
                                    {(step.duration_ms / 1000).toFixed(1)}s
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span>
                                    {step.input_tokens + step.output_tokens}{" "}
                                    tokens
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span>
                                    {formatCost(
                                      step.input_tokens,
                                      step.output_tokens,
                                    )}
                                  </span>
                                </div>
                              )}

                              <p
                                className="mt-1.5 text-[10px] italic"
                                style={{ color: "var(--text-muted)" }}
                              >
                                Bấm để xem chi tiết →
                              </p>
                            </button>
                          );
                        })}
                    </>
                  ) : (
                    <div
                      className="rounded-md border border-dashed p-5 text-center"
                      style={{
                        borderColor: "var(--border-subtle)",
                        backgroundColor: "var(--bg-surface)",
                      }}
                    >
                      <p
                        className="text-sm font-medium"
                        style={{ color: "var(--text-secondary)" }}
                      >
                        Chưa có bước xử lý AI
                      </p>
                      <p
                        className="mt-2 text-xs leading-relaxed"
                        style={{ color: "var(--text-muted)" }}
                      >
                        Pipeline AI chưa được khởi chạy cho hồ sơ này.
                      </p>
                    </div>
                  )}
                </div>
              </TabsContent>

              {/* Live reasoning tab */}
              <TabsContent
                value="thinking"
                className="flex-1 overflow-hidden p-0 m-0"
              >
                <ThinkingTab
                  thinking={artifactData.thinking}
                  runningAgentIds={runningAgentIds}
                />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </>
  );
}
