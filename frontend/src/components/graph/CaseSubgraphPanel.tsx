"use client";

/**
 * CaseSubgraphPanel — renders the case knowledge-graph subgraph using
 * React Flow + dagre. Loaded dynamically (ssr: false) from the trace page
 * to split the heavy @xyflow/react + @dagrejs/dagre bundle into a separate
 * async chunk.
 */

import { useCallback, useEffect } from "react";
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
import { AlertTriangle } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SubgraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface SubgraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

export interface SubgraphData {
  nodes: SubgraphNode[];
  edges: SubgraphEdge[];
}

export interface WSNodeUpdate {
  event: "node_added" | "edge_added" | "status_changed";
  payload: Record<string, unknown>;
}

interface CaseSubgraphPanelProps {
  subgraph: SubgraphData | undefined;
  subgraphError: Error | null;
  onRefetch: () => void;
  /** Live WS updates — parent passes these in so no WS subscription needed here */
  pendingUpdate?: WSNodeUpdate | null;
}

// ---------------------------------------------------------------------------
// Node style map
// ---------------------------------------------------------------------------

const NODE_STYLES: Record<
  string,
  { bg: string; border: string; emoji: string; vi: string }
> = {
  Case: { bg: "rgba(59,130,246,0.12)", border: "#3b82f6", emoji: "📋", vi: "Hồ sơ" },
  Applicant: { bg: "rgba(14,165,233,0.12)", border: "#0ea5e9", emoji: "👤", vi: "Công dân" },
  Task: { bg: "rgba(107,114,128,0.12)", border: "#6b7280", emoji: "✅", vi: "Nhiệm vụ" },
  Document: { bg: "rgba(99,102,241,0.12)", border: "#6366f1", emoji: "📄", vi: "Tài liệu" },
  Bundle: { bg: "rgba(139,92,246,0.12)", border: "#8b5cf6", emoji: "📦", vi: "Bundle" },
  Gap: { bg: "rgba(245,158,11,0.12)", border: "#f59e0b", emoji: "⚠️", vi: "Thiếu sót" },
  Citation: { bg: "rgba(168,85,247,0.12)", border: "#a855f7", emoji: "📚", vi: "Căn cứ" },
  Decision: { bg: "rgba(34,197,94,0.12)", border: "#22c55e", emoji: "✔️", vi: "Quyết định" },
  Entity: { bg: "rgba(6,182,212,0.12)", border: "#06b6d4", emoji: "🔖", vi: "Thực thể" },
  AgentStep: { bg: "rgba(236,72,153,0.12)", border: "#ec4899", emoji: "🤖", vi: "Bước AI" },
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 60;

// ---------------------------------------------------------------------------
// Custom graph node
// ---------------------------------------------------------------------------

function GraphNode({
  data,
}: {
  data: { label: string; type: string; status?: string };
}) {
  const style = NODE_STYLES[data.type] ?? NODE_STYLES.Task;
  const statusClass =
    data.status === "running"
      ? "border-l-4 border-l-[var(--accent-primary)] animate-pulse-glow"
      : data.status === "completed"
        ? "border-l-4 border-l-[var(--accent-success)] animate-pulse-success"
        : data.status === "failed"
          ? "border-l-4 border-l-[var(--accent-destructive)]"
          : "";

  return (
    <div
      className={`relative rounded-md border p-3 ${statusClass}`}
      style={{ width: NODE_WIDTH, background: style.bg, borderColor: style.border }}
      title={`${style.vi}: ${data.label}`}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="flex items-center gap-1.5">
        <span className="text-sm leading-none" aria-hidden="true">{style.emoji}</span>
        <span
          className="font-mono text-[10px] uppercase tracking-wider"
          style={{ color: style.border }}
        >
          {style.vi}
        </span>
      </div>
      <p className="mt-1 truncate text-sm font-medium text-[var(--text-primary)]">
        {data.label}
      </p>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { graphNode: GraphNode };

// ---------------------------------------------------------------------------
// Dagre layout
// ---------------------------------------------------------------------------

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
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}

// ---------------------------------------------------------------------------
// Label extractor
// ---------------------------------------------------------------------------

function nodeLabel(n: SubgraphNode): string {
  const p = n.properties;
  const first = (...keys: string[]): string => {
    for (const k of keys) {
      const v = p[k];
      if (typeof v === "string" && v.trim()) return v;
      if (typeof v === "number") return String(v);
    }
    return "";
  };
  switch (n.label) {
    case "Case":
      return first("code", "tthc_code", "case_id") + (p.status ? ` · ${p.status}` : "");
    case "Applicant":
      return first("full_name", "applicant_id", "id_number") || "Công dân";
    case "Document":
      return first("filename", "doc_type", "document_id", "doc_id") || "Tài liệu";
    case "Gap":
      return first("description", "gap_id", "severity") || "Gap";
    case "Citation":
      return (
        first("law_name", "article", "citation_id") +
        (p.relevance ? ` (${Math.round(Number(p.relevance) * 100)}%)` : "")
      );
    case "Bundle":
      return first("bundle_id", "status") || "Bundle";
    case "AgentStep":
      return first("agent_name", "action", "step_id") || "Agent step";
    case "Task":
      return first("name", "task_id", "status") || "Task";
    default:
      return first("name", "label", "title") || n.label;
  }
}

// ---------------------------------------------------------------------------
// Panel component
// ---------------------------------------------------------------------------

export function CaseSubgraphPanel({
  subgraph,
  subgraphError,
  onRefetch,
  pendingUpdate,
}: CaseSubgraphPanelProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Build initial graph from subgraph data
  useEffect(() => {
    if (!subgraph) return;
    const initialNodes: Node[] = subgraph.nodes.map((n) => ({
      id: n.id,
      type: "graphNode",
      data: {
        label: nodeLabel(n),
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

  // Apply incremental WS updates from parent
  const applyUpdate = useCallback(
    (update: WSNodeUpdate) => {
      const { event, payload } = update;
      if (event === "node_added" && payload.id) {
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
          return layoutGraph([...prev, newNode], []);
        });
      }
      if (event === "edge_added" && payload.id) {
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
      if (event === "status_changed" && payload.node_id) {
        setNodes((prev) =>
          prev.map((n) =>
            n.id === payload.node_id
              ? { ...n, data: { ...n.data, status: payload.status as string } }
              : n,
          ),
        );
      }
    },
    [setNodes, setEdges],
  );

  useEffect(() => {
    if (pendingUpdate) applyUpdate(pendingUpdate);
  }, [pendingUpdate, applyUpdate]);

  if (subgraphError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
        <AlertTriangle
          className="h-8 w-8"
          style={{ color: "var(--accent-destructive)" }}
          aria-hidden="true"
        />
        <p className="text-sm font-semibold text-[var(--text-primary)]">
          Không thể tải đồ thị
        </p>
        <p className="text-xs text-[var(--text-muted)]">
          {subgraphError.message ?? "Lỗi không xác định"}
        </p>
        <button
          onClick={onRefetch}
          className="rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          style={{ borderColor: "var(--border-default)" }}
        >
          Thử lại
        </button>
      </div>
    );
  }

  return (
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
  );
}
