"use client";

import { use, useCallback, useEffect } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import { useCaseSubgraph } from "@/hooks/use-graph";
import { useAgentTrace } from "@/hooks/use-agents";
import { useWSTopic } from "@/hooks/use-ws";
import type { WSMessage } from "@/lib/types";
import { AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton-card";

const NODE_STYLES: Record<string, { bg: string; border: string }> = {
  Case: { bg: "rgba(59,130,246,0.12)", border: "#3b82f6" },
  Task: { bg: "rgba(107,114,128,0.12)", border: "#6b7280" },
  Document: { bg: "rgba(99,102,241,0.12)", border: "#6366f1" },
  Gap: { bg: "rgba(245,158,11,0.12)", border: "#f59e0b" },
  Citation: { bg: "rgba(168,85,247,0.12)", border: "#a855f7" },
  Decision: { bg: "rgba(34,197,94,0.12)", border: "#22c55e" },
  Entity: { bg: "rgba(6,182,212,0.12)", border: "#06b6d4" },
  AgentStep: { bg: "rgba(99,102,241,0.12)", border: "#6366f1" },
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 60;

function GraphNode({
  data,
}: {
  data: { label: string; type: string; status?: string };
}) {
  const style = NODE_STYLES[data.type] || NODE_STYLES.Task;
  const statusClass =
    data.status === "running"
      ? "border-l-4 border-l-[var(--accent-primary)] animate-pulse-glow"
      : data.status === "completed"
        ? "border-l-4 border-l-[var(--accent-success)] animate-pulse-success"
        : data.status === "failed"
          ? "border-l-4 border-l-[var(--accent-error)]"
          : "";
  return (
    <div
      className={`rounded-md border p-3 ${statusClass}`}
      style={{
        width: NODE_WIDTH,
        background: style.bg,
        borderColor: style.border,
      }}
    >
      <p className="font-mono text-[10px] text-[var(--text-muted)]">
        {data.type}
      </p>
      <p className="truncate text-sm font-medium">{data.label}</p>
    </div>
  );
}

const nodeTypes = { graphNode: GraphNode };

function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 60, nodesep: 40 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      ...n,
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });
}

export default function TraceViewer({
  params,
}: {
  params: Promise<{ case_id: string }>;
}) {
  const { case_id } = use(params);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const { data: subgraph, isLoading: subgraphLoading, error: subgraphError, refetch: refetchSubgraph } = useCaseSubgraph(case_id);
  const { data: trace, isLoading: traceLoading, error: traceError, refetch: refetchTrace } = useAgentTrace(case_id);

  // Initial load from subgraph
  useEffect(() => {
    if (!subgraph) return;
    const initialNodes: Node[] = subgraph.nodes.map((n) => ({
      id: n.id,
      type: "graphNode",
      data: {
        label: (n.properties.name as string) || n.label,
        type: n.label,
        status: n.properties.status as string | undefined,
      },
      position: { x: 0, y: 0 },
    }));
    const initialEdges: Edge[] = subgraph.edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      type: "smoothstep",
      animated: true,
    }));
    const laid = layoutGraph(initialNodes, initialEdges);
    setNodes(laid);
    setEdges(initialEdges);
  }, [subgraph, setNodes, setEdges]);

  // WebSocket live updates
  const handleWS = useCallback(
    (msg: WSMessage) => {
      const payload = msg.data as Record<string, unknown>;
      if (msg.event === "node_added" && payload.id) {
        setNodes((prev) => {
          const newNode: Node = {
            id: payload.id as string,
            type: "graphNode",
            data: {
              label: (payload.name as string) || (payload.label as string) || "",
              type: (payload.type as string) || "Task",
              status: payload.status as string | undefined,
            },
            position: { x: 0, y: 0 },
          };
          const updated = [...prev, newNode];
          return layoutGraph(updated, []);
        });
      }
      if (msg.event === "edge_added" && payload.id) {
        setEdges((prev) => [
          ...prev,
          {
            id: payload.id as string,
            source: payload.source as string,
            target: payload.target as string,
            type: "smoothstep",
            animated: true,
          },
        ]);
      }
      if (msg.event === "status_changed" && payload.node_id) {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === payload.node_id
              ? {
                  ...n,
                  data: { ...n.data, status: payload.status as string },
                }
              : n,
          ),
        );
      }
    },
    [setNodes, setEdges],
  );

  useWSTopic(`case:${case_id}`, handleWS);

  const bothLoading = subgraphLoading && traceLoading;

  if (bothLoading) {
    return (
      <div className="flex h-full gap-4">
        {/* Graph skeleton */}
        <div className="flex-[7] flex flex-col items-center justify-center gap-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-8">
          <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
            <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" />
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
        {/* Sidebar skeleton */}
        <div className="flex-[3] space-y-3 overflow-auto">
          <Skeleton className="h-5 w-28" />
          {[...Array(5)].map((_, i) => (
            <div key={i} className="space-y-2 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-3 w-40" />
              <Skeleton className="h-2 w-20" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Theo dõi xử lý AI</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Đồ thị Knowledge Graph và các bước xử lý tự động của agent AI cho hồ sơ <span className="font-mono">{case_id.slice(0, 8)}</span>
        </p>
      </div>
      <div className="flex flex-1 gap-4">
      {/* Graph panel */}
      <div className="flex-[7] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        {subgraphError ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
            <AlertTriangle className="h-8 w-8 text-[var(--accent-error)]" />
            <p className="text-sm font-semibold">Không thể tải đồ thị</p>
            <p className="text-xs text-[var(--text-muted)]">
              {(subgraphError as Error).message ?? "Lỗi không xác định"}
            </p>
            <button
              onClick={() => refetchSubgraph()}
              className="rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
            >
              Thử lại
            </button>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            fitView
            defaultEdgeOptions={{ type: "smoothstep", animated: true }}
          >
            <Background gap={16} size={1} />
            <Controls />
          </ReactFlow>
        )}
      </div>

      {/* Các bước xử lý AI sidebar */}
      <div className="flex-[3] space-y-3 overflow-auto">
        <h2 className="text-lg font-semibold">Các bước xử lý AI</h2>
        {traceError ? (
          <div className="flex items-center gap-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
            <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--accent-error)]" />
            <div className="flex-1">
              <p className="text-xs font-semibold">Không thể tải các bước xử lý AI</p>
              <p className="text-[10px] text-[var(--text-muted)]">
                {(traceError as Error).message ?? "Lỗi không xác định"}
              </p>
            </div>
            <button
              onClick={() => refetchTrace()}
              className="rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
            >
              Thử lại
            </button>
          </div>
        ) : trace ? (
          <>
            <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
              <span
                className={`inline-block h-2 w-2 rounded-full ${trace.status === "running" ? "animate-pulse bg-[var(--accent-primary)]" : trace.status === "completed" ? "bg-[var(--accent-success)]" : "bg-[var(--accent-error)]"}`}
              />
              {({ running: "Đang chạy", completed: "Hoàn thành", failed: "Lỗi" } as Record<string,string>)[trace.status] ?? trace.status} · {trace.total_tokens} token ·{" "}
              {(trace.total_duration_ms / 1000).toFixed(1)}s
            </div>
            {trace.steps.map((step) => {
              const STEP_STATUS_VI: Record<string, string> = {
                completed: "Hoàn thành",
                running: "Đang chạy",
                failed: "Lỗi",
                pending: "Chờ",
              };
              return (
              <div
                key={step.step_id}
                className="cursor-pointer rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 transition-colors hover:bg-[var(--bg-surface-raised)]"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <p className="text-xs font-bold">{step.agent_name}</p>
                    <span className="ml-1 rounded bg-[var(--accent-primary)]/10 px-1 py-0.5 text-[9px] text-[var(--accent-primary)]">
                      {step.agent_name.includes("Doc") || step.agent_name.includes("Analyzer")
                        ? "Qwen3-VL"
                        : "Qwen3-Max"}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] ${step.status === "completed" ? "text-[var(--accent-success)]" : step.status === "running" ? "text-[var(--accent-primary)]" : "text-[var(--accent-error)]"}`}
                  >
                    {STEP_STATUS_VI[step.status] ?? step.status}
                  </span>
                </div>
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  {step.action}
                </p>
                {step.duration_ms != null && (
                  <p className="mt-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                    {(step.duration_ms / 1000).toFixed(1)}s ·{" "}
                    {step.input_tokens + step.output_tokens} tokens
                  </p>
                )}
              </div>
            );})}
          </>
        ) : (
          <div className="rounded-md border border-dashed border-[var(--border-subtle)] bg-[var(--bg-surface)] p-5 text-center">
            <p className="text-sm font-medium text-[var(--text-secondary)]">
              Chưa có bước xử lý AI
            </p>
            <p className="mt-2 text-xs leading-relaxed text-[var(--text-muted)]">
              Pipeline AI chưa được khởi chạy cho hồ sơ này.
              Để bắt đầu xử lý, vào trang <strong>Tiếp nhận</strong> và
              chọn &ldquo;Tạo hồ sơ &amp; khởi chạy pipeline&rdquo;.
            </p>
            <p className="mt-3 text-xs text-[var(--text-muted)]">
              Khi pipeline chạy, các bước xử lý sẽ hiển thị realtime tại đây:
              Phân loại → Trích xuất → Kiểm tra → Xem xét → Soạn thảo
            </p>
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
