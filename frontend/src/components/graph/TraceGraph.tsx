"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import { useTraceGraph } from "@/hooks/use-graph";
import { useQueryClient } from "@tanstack/react-query";
import { useWSTopic } from "@/hooks/use-ws";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { AlertTriangle, Bot, Clock, Coins, RefreshCw } from "lucide-react";
import type { WSMessage, GraphNode } from "@/lib/types";
import { graphKeys } from "@/hooks/use-graph";

// ---------------------------------------------------------------------------
// Layout constants
// ---------------------------------------------------------------------------

const NODE_WIDTH = 240;
const NODE_HEIGHT = 64;

// ---------------------------------------------------------------------------
// Status styles — left-border color strip
// ---------------------------------------------------------------------------

const STATUS_STYLE: Record<
  string,
  { leftBorder: string; bg: string; label: string }
> = {
  pending:   { leftBorder: "#94a3b8", bg: "rgba(148,163,184,0.08)", label: "Chờ" },
  running:   { leftBorder: "#3b82f6", bg: "rgba(59,130,246,0.10)", label: "Đang chạy" },
  completed: { leftBorder: "#22c55e", bg: "rgba(34,197,94,0.10)",  label: "Hoàn thành" },
  failed:    { leftBorder: "#ef4444", bg: "rgba(239,68,68,0.10)",  label: "Lỗi" },
};

function statusStyle(status: string | undefined) {
  return STATUS_STYLE[status ?? "pending"] ?? STATUS_STYLE.pending;
}

// ---------------------------------------------------------------------------
// Custom node
// ---------------------------------------------------------------------------

interface AgentNodeData extends Record<string, unknown> {
  label: string;
  agentName: string;
  status?: string;
  duration_ms?: number | null;
  input_tokens?: number;
  output_tokens?: number;
  action?: string;
  rawNode: GraphNode;
}

function AgentStepNode({ data }: { data: AgentNodeData }) {
  const ss = statusStyle(data.status);
  const isRunning = data.status === "running";

  return (
    <div
      className={`relative rounded-md border border-[var(--border-subtle)] ${isRunning ? "animate-pulse" : ""}`}
      style={{
        width: NODE_WIDTH,
        background: ss.bg,
        borderLeftWidth: 4,
        borderLeftColor: ss.leftBorder,
        borderLeftStyle: "solid",
      }}
      title={data.label}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="px-3 py-2.5">
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <Bot className="h-3 w-3 shrink-0" style={{ color: ss.leftBorder }} />
            <span
              className="truncate font-mono text-[10px] font-semibold uppercase tracking-wide"
              style={{ color: ss.leftBorder }}
            >
              {data.agentName}
            </span>
          </div>
          <span
            className="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-medium text-white"
            style={{ backgroundColor: ss.leftBorder }}
          >
            {ss.label}
          </span>
        </div>
        {data.action && (
          <p className="mt-1 truncate text-[11px] text-[var(--text-secondary)]">
            {data.action}
          </p>
        )}
        {data.duration_ms != null && (
          <p className="mt-0.5 font-mono text-[9px] text-[var(--text-muted)]">
            {(data.duration_ms / 1000).toFixed(2)}s
            {data.input_tokens !== undefined && (
              <> · {(data.input_tokens ?? 0) + (data.output_tokens ?? 0)} tok</>
            )}
          </p>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { agentStep: AgentStepNode };

// ---------------------------------------------------------------------------
// Dagre layout
// ---------------------------------------------------------------------------

function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 70, nodesep: 40 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}

// ---------------------------------------------------------------------------
// Node data extractor from graph vertex
// ---------------------------------------------------------------------------

function extractNodeData(gn: GraphNode): AgentNodeData {
  const p = gn.properties as Record<string, unknown>;
  const str = (...keys: string[]) => {
    for (const k of keys) {
      const v = p[k];
      if (typeof v === "string" && v.trim()) return v;
    }
    return undefined;
  };
  const num = (k: string) => {
    const v = p[k];
    return typeof v === "number" ? v : undefined;
  };

  return {
    label: str("agent_name", "name", "step_id") ?? gn.id,
    agentName: str("agent_name", "name") ?? gn.label,
    status: str("status"),
    duration_ms: num("duration_ms") ?? null,
    input_tokens: num("input_tokens"),
    output_tokens: num("output_tokens"),
    action: str("action"),
    rawNode: gn,
  };
}

// ---------------------------------------------------------------------------
// Step detail side panel
// ---------------------------------------------------------------------------

function StepDetailSheet({
  node,
  onClose,
}: {
  node: AgentNodeData | null;
  onClose: () => void;
}) {
  if (!node) return null;
  const ss = statusStyle(node.status);

  return (
    <Sheet open={Boolean(node)} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-96 overflow-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-sm">
            <Bot className="h-4 w-4" style={{ color: ss.leftBorder }} />
            {node.agentName}
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {/* Status */}
          <div className="flex items-center gap-2">
            <span
              className="rounded-full px-2 py-0.5 text-xs font-medium text-white"
              style={{ backgroundColor: ss.leftBorder }}
            >
              {ss.label}
            </span>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3">
            {node.duration_ms != null && (
              <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-3 py-2">
                <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                  <Clock className="h-3 w-3" />
                  Thời gian
                </div>
                <p className="mt-0.5 font-mono text-sm font-medium text-[var(--text-primary)]">
                  {(node.duration_ms / 1000).toFixed(2)}s
                </p>
              </div>
            )}
            {node.input_tokens !== undefined && (
              <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)] px-3 py-2">
                <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
                  <Coins className="h-3 w-3" />
                  Tokens
                </div>
                <p className="mt-0.5 font-mono text-sm font-medium text-[var(--text-primary)]">
                  {(node.input_tokens ?? 0) + (node.output_tokens ?? 0)}
                </p>
              </div>
            )}
          </div>

          {/* Token breakdown */}
          {node.input_tokens !== undefined && (
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                Chi tiết token
              </p>
              <div className="flex gap-4 text-xs text-[var(--text-secondary)]">
                <span>Input: <span className="font-mono font-semibold text-[var(--text-primary)]">{node.input_tokens ?? 0}</span></span>
                <span>Output: <span className="font-mono font-semibold text-[var(--text-primary)]">{node.output_tokens ?? 0}</span></span>
              </div>
            </div>
          )}

          {/* Action */}
          {node.action && (
            <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                Hành động
              </p>
              <p className="text-sm leading-relaxed text-[var(--text-primary)]">
                {node.action}
              </p>
            </div>
          )}

          {/* Raw properties */}
          <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Thuộc tính gốc
            </p>
            <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-[var(--text-secondary)]">
              {JSON.stringify(node.rawNode.properties, null, 2)}
            </pre>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyGraph() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <div
        className="flex h-16 w-16 items-center justify-center rounded-full"
        style={{ backgroundColor: "var(--bg-subtle)" }}
        aria-hidden="true"
      >
        <Bot className="h-8 w-8" style={{ color: "var(--text-muted)" }} />
      </div>
      <p className="text-sm font-medium" style={{ color: "var(--text-secondary)" }}>
        Chưa có bước tác nhân nào
      </p>
      <p className="max-w-xs text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
        Pipeline AI chưa được khởi chạy cho hồ sơ này. Sau khi xử lý, đồ thị các bước agent sẽ xuất hiện tại đây.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// TraceGraph — public component
// ---------------------------------------------------------------------------

interface TraceGraphProps {
  caseId: string;
}

export default function TraceGraph({ caseId }: TraceGraphProps) {
  const queryClient = useQueryClient();
  const {
    data: traceSubgraph,
    isLoading,
    error,
    refetch,
  } = useTraceGraph(caseId);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<AgentNodeData | null>(null);
  const [wsConnected, setWsConnected] = useState(true);

  // Build RF nodes+edges from subgraph
  const buildGraph = useCallback(
    (subgraph: typeof traceSubgraph) => {
      if (!subgraph) return;

      const agentNodes = subgraph.nodes.filter(
        (n) => n.label === "AgentStep" || n.label === "Task",
      );

      const rfNodes: Node[] = agentNodes.map((n) => ({
        id: n.id,
        type: "agentStep",
        data: extractNodeData(n),
        position: { x: 0, y: 0 },
      }));

      const rfEdges: Edge[] = subgraph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: "smoothstep",
        animated: subgraph.nodes.some(
          (n) =>
            (n.id === e.source || n.id === e.target) &&
            (n.properties as Record<string, unknown>).status === "running",
        ),
        style: { stroke: "#64748b", strokeWidth: 1.5 },
      }));

      const laid = layoutGraph(rfNodes, rfEdges);
      setNodes(laid);
      setEdges(rfEdges);
    },
    [setNodes, setEdges],
  );

  useEffect(() => {
    buildGraph(traceSubgraph);
  }, [traceSubgraph, buildGraph]);

  // WS subscribe — invalidate query on trace events
  const handleWS = useCallback(
    (msg: WSMessage) => {
      setWsConnected(true);
      const payload = msg.data as Record<string, unknown>;

      if (
        msg.event === "node_added" ||
        msg.event === "status_changed" ||
        msg.event === "edge_added"
      ) {
        // Invalidate to re-fetch the full trace subgraph
        void queryClient.invalidateQueries({
          queryKey: graphKeys.traceGraph(caseId),
        });
      }

      // Optimistic local status update
      if (msg.event === "status_changed" && payload.node_id) {
        setNodes((prev) =>
          prev.map((n) => {
            if (n.id !== payload.node_id) return n;
            const updated = {
              ...(n.data as unknown as AgentNodeData),
              status: payload.status as string,
            };
            return { ...n, data: updated };
          }),
        );
      }
    },
    [queryClient, caseId, setNodes],
  );

  useWSTopic(`trace:${caseId}`, handleWS);

  // 5s polling fallback when WS not connected
  useEffect(() => {
    if (wsConnected) return;
    const id = setInterval(() => {
      void refetch();
    }, 5000);
    return () => clearInterval(id);
  }, [wsConnected, refetch]);

  // Detect WS disconnect — simple heuristic: if no WS event in 15s, assume disconnected
  useEffect(() => {
    const id = setTimeout(() => setWsConnected(false), 15_000);
    return () => clearTimeout(id);
  }, []);

  // Node click handler
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node.data as unknown as AgentNodeData);
    },
    [],
  );

  const hasNodes = nodes.length > 0;

  return (
    <div className="relative flex h-full flex-col overflow-hidden rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
      {/* Error banner */}
      {error && (
        <div className="flex items-center gap-3 border-b border-[var(--border-subtle)] bg-[var(--accent-destructive)]/5 px-4 py-2">
          <AlertTriangle className="h-4 w-4 shrink-0 text-[var(--accent-destructive)]" />
          <p className="flex-1 text-xs text-[var(--accent-destructive)]">
            Không thể tải đồ thị trace: {(error as Error).message ?? "lỗi không xác định"}
          </p>
          <button
            onClick={() => void refetch()}
            className="flex items-center gap-1 rounded border border-[var(--border-default)] px-2 py-1 text-[10px] font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
            aria-label="Thử lại tải đồ thị"
          >
            <RefreshCw className="h-3 w-3" />
            Thử lại
          </button>
        </div>
      )}

      {/* WS fallback notice */}
      {!wsConnected && !error && (
        <div className="flex items-center gap-2 border-b border-[var(--border-subtle)] bg-amber-50/60 px-4 py-1.5 dark:bg-amber-950/20">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden="true" />
          <p className="text-[10px] text-amber-700 dark:text-amber-400">
            WebSocket ngắt kết nối — đang dùng polling 5 giây
          </p>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" />
          <div className="w-full max-w-md space-y-3">
            <div className="flex justify-center gap-6">
              <div className="h-16 w-56 animate-pulse rounded-md bg-[var(--bg-subtle)]" />
            </div>
            <div className="flex justify-center gap-6">
              <div className="h-16 w-56 animate-pulse rounded-md bg-[var(--bg-subtle)]" />
              <div className="h-16 w-56 animate-pulse rounded-md bg-[var(--bg-subtle)]" />
            </div>
            <div className="flex justify-center gap-6">
              <div className="h-16 w-56 animate-pulse rounded-md bg-[var(--bg-subtle)]" />
            </div>
          </div>
          <p className="text-xs text-[var(--text-muted)]">Đang tải đồ thị agent...</p>
        </div>
      )}

      {/* Graph */}
      {!isLoading && (
        <div className="flex-1">
          {!hasNodes ? (
            <EmptyGraph />
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              defaultEdgeOptions={{ type: "smoothstep" }}
              minZoom={0.3}
              maxZoom={2}
            >
              <Background gap={16} size={1} color="var(--border-subtle)" />
              <Controls />
            </ReactFlow>
          )}
        </div>
      )}

      {/* Step detail sheet */}
      <StepDetailSheet node={selectedNode} onClose={() => setSelectedNode(null)} />
    </div>
  );
}
