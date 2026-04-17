"use client";

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
import { useCaseSubgraph } from "@/hooks/use-graph";
import { AlertTriangle, RefreshCw } from "lucide-react";
import type { GraphNode } from "@/lib/types";

// ---------------------------------------------------------------------------
// Node styles by vertex label
// ---------------------------------------------------------------------------

const LABEL_STYLE: Record<string, { leftBorder: string; bg: string; emoji: string }> = {
  Case:     { leftBorder: "#3b82f6", bg: "rgba(59,130,246,0.08)",  emoji: "📋" },
  Document: { leftBorder: "#6366f1", bg: "rgba(99,102,241,0.08)",  emoji: "📄" },
  Gap:      { leftBorder: "#f59e0b", bg: "rgba(245,158,11,0.08)",  emoji: "⚠️" },
  Citation: { leftBorder: "#a855f7", bg: "rgba(168,85,247,0.08)",  emoji: "📚" },
  Decision: { leftBorder: "#22c55e", bg: "rgba(34,197,94,0.08)",   emoji: "✔️" },
  Bundle:   { leftBorder: "#8b5cf6", bg: "rgba(139,92,246,0.08)",  emoji: "📦" },
  Task:     { leftBorder: "#6b7280", bg: "rgba(107,114,128,0.08)", emoji: "✅" },
};

const NODE_WIDTH = 220;
const NODE_HEIGHT = 58;

function labelStyle(label: string) {
  return LABEL_STYLE[label] ?? LABEL_STYLE.Task;
}

function nodeTitle(gn: GraphNode): string {
  const p = gn.properties as Record<string, unknown>;
  const first = (...keys: string[]) => {
    for (const k of keys) {
      const v = p[k];
      if (typeof v === "string" && v.trim()) return v;
    }
    return "";
  };
  switch (gn.label) {
    case "Case":     return first("code", "tthc_code") || "Hồ sơ";
    case "Document": return first("filename", "doc_type", "doc_id") || "Tài liệu";
    case "Gap":      return first("description", "gap_id") || "Gap";
    case "Citation": return first("law_name", "article") || "Căn cứ";
    case "Bundle":   return first("bundle_id", "status") || "Bundle";
    default:         return first("name", "label", "title") || gn.label;
  }
}

function CaseGraphNode({ data }: { data: { label: string; nodeLabel: string; title: string } }) {
  const ls = labelStyle(data.nodeLabel);

  return (
    <div
      className="rounded-md border border-[var(--border-subtle)]"
      style={{
        width: NODE_WIDTH,
        background: ls.bg,
        borderLeftWidth: 4,
        borderLeftColor: ls.leftBorder,
        borderLeftStyle: "solid",
      }}
      title={data.title}
    >
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <span className="text-sm leading-none">{ls.emoji}</span>
          <span
            className="font-mono text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: ls.leftBorder }}
          >
            {data.nodeLabel}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs font-medium text-[var(--text-primary)]">
          {data.title}
        </p>
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { caseNode: CaseGraphNode };

function layoutGraph(nodes: Node[], edges: Edge[]): Node[] {
  if (nodes.length === 0) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 60, nodesep: 36 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}

// ---------------------------------------------------------------------------
// CaseGraph
// ---------------------------------------------------------------------------

interface CaseGraphProps {
  caseId: string;
  /** Height of the graph container, defaults to 400px */
  height?: number;
}

export default function CaseGraph({ caseId, height = 400 }: CaseGraphProps) {
  const { data: subgraph, isLoading, error, refetch } = useCaseSubgraph(caseId);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const buildGraph = useCallback(
    (sg: typeof subgraph) => {
      if (!sg) return;
      const rfNodes: Node[] = sg.nodes.map((n) => ({
        id: n.id,
        type: "caseNode",
        data: { label: n.label, nodeLabel: n.label, title: nodeTitle(n) },
        position: { x: 0, y: 0 },
      }));
      const rfEdges: Edge[] = sg.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: "smoothstep",
        style: { stroke: "#64748b", strokeWidth: 1.5 },
      }));
      setNodes(layoutGraph(rfNodes, rfEdges));
      setEdges(rfEdges);
    },
    [setNodes, setEdges],
  );

  useEffect(() => {
    buildGraph(subgraph);
  }, [subgraph, buildGraph]);

  return (
    <div
      className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
      style={{ height }}
    >
      {isLoading ? (
        <div className="flex h-full items-center justify-center">
          <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--accent-primary)]" />
        </div>
      ) : error ? (
        <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
          <AlertTriangle className="h-6 w-6 text-[var(--accent-warning)]" />
          <p className="text-sm text-[var(--text-muted)]">Không thể tải đồ thị hồ sơ</p>
          <button
            onClick={() => void refetch()}
            className="flex items-center gap-1.5 rounded border border-[var(--border-default)] px-3 py-1.5 text-xs hover:bg-[var(--bg-surface-raised)]"
          >
            <RefreshCw className="h-3 w-3" />
            Thử lại
          </button>
        </div>
      ) : nodes.length === 0 ? (
        <div className="flex h-full items-center justify-center">
          <p className="text-sm text-[var(--text-muted)]">Chưa có dữ liệu đồ thị</p>
        </div>
      ) : (
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          defaultEdgeOptions={{ type: "smoothstep" }}
          minZoom={0.3}
        >
          <Background gap={16} size={1} color="var(--border-subtle)" />
          <Controls />
        </ReactFlow>
      )}
    </div>
  );
}
