"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import { useCaseSubgraph } from "@/hooks/use-graph";
import { apiClient } from "@/lib/api";
import { toast } from "sonner";
import type { GraphNode, SubgraphResponse } from "@/lib/types";
import {
  Search,
  LayoutTemplate,
  ZoomIn,
  Download,
  Sparkles,
  RefreshCw,
  Loader2,
  AlertTriangle,
  Filter,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Node style registry — mirrors CaseGraph.tsx
// ---------------------------------------------------------------------------

const LABEL_STYLE: Record<string, { leftBorder: string; bg: string; label: string }> = {
  Case:       { leftBorder: "#3b82f6", bg: "rgba(59,130,246,0.08)",  label: "Hồ sơ" },
  Document:   { leftBorder: "#6366f1", bg: "rgba(99,102,241,0.08)",  label: "Tài liệu" },
  Gap:        { leftBorder: "#f59e0b", bg: "rgba(245,158,11,0.08)",  label: "Gap" },
  Citation:   { leftBorder: "#a855f7", bg: "rgba(168,85,247,0.08)",  label: "Trích dẫn" },
  Decision:   { leftBorder: "#22c55e", bg: "rgba(34,197,94,0.08)",   label: "Quyết định" },
  Bundle:     { leftBorder: "#8b5cf6", bg: "rgba(139,92,246,0.08)",  label: "Bundle" },
  Task:       { leftBorder: "#6b7280", bg: "rgba(107,114,128,0.08)", label: "Task" },
  AgentStep:  { leftBorder: "#14b8a6", bg: "rgba(20,184,166,0.08)",  label: "Agent" },
  TTHCSpec:   { leftBorder: "#f97316", bg: "rgba(249,115,22,0.08)",  label: "TTHC" },
  Article:    { leftBorder: "#ec4899", bg: "rgba(236,72,153,0.08)",  label: "Điều luật" },
  Law:        { leftBorder: "#06b6d4", bg: "rgba(6,182,212,0.08)",   label: "Văn bản PL" },
  Published:  { leftBorder: "#22c55e", bg: "rgba(34,197,94,0.08)",   label: "Đã ban hành" },
};

const ALL_NODE_TYPES = Object.keys(LABEL_STYLE);

const NODE_WIDTH = 280;
const NODE_HEIGHT = 60;

function getLabelStyle(label: string) {
  return LABEL_STYLE[label] ?? { leftBorder: "#6b7280", bg: "rgba(107,114,128,0.08)", label };
}

function getNodeTitle(gn: GraphNode): string {
  const p = gn.properties as Record<string, unknown>;
  const first = (...keys: string[]) => {
    for (const k of keys) {
      const v = p[k];
      if (typeof v === "string" && v.trim()) return v;
    }
    return "";
  };
  switch (gn.label) {
    case "Case":      return first("code", "tthc_code") || "Hồ sơ";
    case "Document":  return first("filename", "doc_type", "doc_id") || "Tài liệu";
    case "Gap":       return first("description", "gap_id") || "Gap";
    case "Citation":  return first("law_name", "article") || "Căn cứ";
    case "Article":   return first("article_number", "title", "clause_path") || "Điều khoản";
    case "Law":       return first("short_name", "name", "law_id") || "Văn bản PL";
    case "TTHCSpec":  return first("name", "tthc_code") || "TTHC";
    case "AgentStep": return first("agent_name", "action") || "Agent";
    default:          return first("name", "title", "label") || gn.label;
  }
}

// ---------------------------------------------------------------------------
// Custom node component
// ---------------------------------------------------------------------------

function KGNode({ data }: { data: { nodeLabel: string; title: string; subtitle?: string } }) {
  const ls = getLabelStyle(data.nodeLabel);
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
          <span
            className="font-mono text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: ls.leftBorder }}
          >
            {ls.label}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs font-medium text-[var(--text-primary)]">
          {data.title}
        </p>
        {data.subtitle && (
          <p className="truncate text-[10px] text-[var(--text-muted)]">{data.subtitle}</p>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { kgNode: KGNode };

// ---------------------------------------------------------------------------
// Dagre layout
// ---------------------------------------------------------------------------

function layoutGraph(nodes: Node[], edges: Edge[], direction: "TB" | "LR"): Node[] {
  if (nodes.length === 0) return nodes;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction, ranksep: 70, nodesep: 40 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return nodes.map((n) => {
    const pos = g.node(n.id);
    return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 } };
  });
}

// ---------------------------------------------------------------------------
// Inline demo subgraph when API is unavailable
// ---------------------------------------------------------------------------

const DEMO_SUBGRAPH: SubgraphResponse = {
  nodes: [
    { id: "case-demo-1",   label: "Case",     properties: { code: "DEMO-1004415-A1B2C3", tthc_code: "1.004415" } },
    { id: "doc-don",       label: "Document", properties: { filename: "don_de_nghi_cpxd.pdf", doc_type: "Đơn đề nghị" } },
    { id: "doc-ban-ve",    label: "Document", properties: { filename: "ban_ve_thiet_ke.pdf",  doc_type: "Bản vẽ thiết kế" } },
    { id: "gap-pccc",      label: "Gap",      properties: { description: "Thiếu giấy chứng nhận PCCC", severity: "critical", gap_id: "GAP-001" } },
    { id: "gap-dat",       label: "Gap",      properties: { description: "Thiếu GCN quyền sử dụng đất", severity: "high", gap_id: "GAP-002" } },
    { id: "law-xd",        label: "Law",      properties: { short_name: "NĐ 15/2021/NĐ-CP", law_id: "nd-15-2021" } },
    { id: "article-95",    label: "Article",  properties: { article_number: "Điều 95", law_name: "NĐ 15/2021" } },
    { id: "citation-1",    label: "Citation", properties: { law_name: "NĐ 15/2021/NĐ-CP", article: "Điều 95 Khoản 2" } },
    { id: "tthc-gpxd",     label: "TTHCSpec", properties: { name: "Cấp phép xây dựng", tthc_code: "1.004415" } },
  ],
  edges: [
    { id: "e1",  source: "case-demo-1", target: "doc-don",    label: "HAS_DOCUMENT" },
    { id: "e2",  source: "case-demo-1", target: "doc-ban-ve", label: "HAS_DOCUMENT" },
    { id: "e3",  source: "case-demo-1", target: "gap-pccc",   label: "HAS_GAP" },
    { id: "e4",  source: "case-demo-1", target: "gap-dat",    label: "HAS_GAP" },
    { id: "e5",  source: "case-demo-1", target: "tthc-gpxd",  label: "BELONGS_TO" },
    { id: "e6",  source: "gap-pccc",    target: "citation-1", label: "CITED_BY" },
    { id: "e7",  source: "citation-1",  target: "article-95", label: "REFERENCES" },
    { id: "e8",  source: "article-95",  target: "law-xd",     label: "PART_OF" },
    { id: "e9",  source: "tthc-gpxd",   target: "law-xd",     label: "GOVERNED_BY" },
  ],
};

// ---------------------------------------------------------------------------
// Toolbar
// ---------------------------------------------------------------------------

interface ToolbarProps {
  searchQuery: string;
  onSearchChange: (v: string) => void;
  activeTypes: Set<string>;
  onToggleType: (t: string) => void;
  direction: "TB" | "LR";
  onToggleDirection: () => void;
  onFitView: () => void;
  onExportJSON: () => void;
  onRefresh: () => void;
  onLoadDemo: () => void;
  isLoading: boolean;
  isDemoLoading: boolean;
  showFilter: boolean;
  onToggleFilter: () => void;
}

function KGToolbar({
  searchQuery,
  onSearchChange,
  activeTypes,
  onToggleType,
  direction,
  onToggleDirection,
  onFitView,
  onExportJSON,
  onRefresh,
  onLoadDemo,
  isLoading,
  isDemoLoading,
  showFilter,
  onToggleFilter,
}: ToolbarProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Main toolbar row */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--text-muted)]"
            aria-hidden="true"
          />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm node..."
            className="h-8 w-52 rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] pl-8 pr-3 text-xs outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
            aria-label="Tìm kiếm node trong đồ thị"
          />
        </div>

        {/* Filter toggle */}
        <button
          type="button"
          onClick={onToggleFilter}
          className={`flex h-8 items-center gap-1.5 rounded-md border px-3 text-xs font-medium transition-colors ${
            showFilter
              ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/10 text-[var(--accent-primary)]"
              : "border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface-raised)]"
          }`}
          aria-label="Lọc theo loại node"
          aria-pressed={showFilter}
        >
          <Filter className="h-3.5 w-3.5" aria-hidden="true" />
          Lọc
        </button>

        {/* Layout toggle TB ↔ LR */}
        <button
          type="button"
          onClick={onToggleDirection}
          className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
          aria-label={`Đổi layout: hiện tại ${direction === "TB" ? "trên-xuống" : "trái-phải"}`}
          title="Đổi hướng layout dagre"
        >
          <LayoutTemplate className="h-3.5 w-3.5" aria-hidden="true" />
          {direction === "TB" ? "TB → LR" : "LR → TB"}
        </button>

        {/* Zoom fit */}
        <button
          type="button"
          onClick={onFitView}
          className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
          aria-label="Khớp toàn bộ đồ thị vào màn hình"
        >
          <ZoomIn className="h-3.5 w-3.5" aria-hidden="true" />
          Fit
        </button>

        {/* Export JSON */}
        <button
          type="button"
          onClick={onExportJSON}
          className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)]"
          aria-label="Xuất đồ thị ra JSON"
        >
          <Download className="h-3.5 w-3.5" aria-hidden="true" />
          Xuất JSON
        </button>

        {/* Refresh */}
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)] disabled:opacity-50"
          aria-label="Làm mới đồ thị"
        >
          {isLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          Làm mới
        </button>

        {/* Demo load */}
        <button
          type="button"
          onClick={onLoadDemo}
          disabled={isDemoLoading}
          className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-surface-raised)] disabled:opacity-50"
          aria-label="Tải dữ liệu đồ thị mẫu"
        >
          {isDemoLoading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          )}
          Dữ liệu mẫu
        </button>
      </div>

      {/* Node type filter chips */}
      {showFilter && (
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Lọc theo loại node">
          {ALL_NODE_TYPES.map((type) => {
            const ls = getLabelStyle(type);
            const active = activeTypes.has(type);
            return (
              <button
                key={type}
                type="button"
                onClick={() => onToggleType(type)}
                className={`flex h-6 items-center gap-1 rounded-full border px-2.5 text-[10px] font-semibold transition-all ${
                  active
                    ? "text-white"
                    : "border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-muted)] hover:bg-[var(--bg-surface-raised)]"
                }`}
                style={
                  active
                    ? { backgroundColor: ls.leftBorder, borderColor: ls.leftBorder }
                    : undefined
                }
                aria-pressed={active}
                aria-label={`${active ? "Ẩn" : "Hiện"} ${ls.label}`}
              >
                {ls.label}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inner graph (needs ReactFlow context)
// ---------------------------------------------------------------------------

function KGInnerGraph({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
}: {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
}) {
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      defaultEdgeOptions={{ type: "smoothstep", style: { stroke: "#64748b", strokeWidth: 1.5 } }}
      minZoom={0.15}
      maxZoom={2}
    >
      <Background gap={16} size={1} color="var(--border-subtle)" />
      <Controls />
      <MiniMap
        nodeColor={(n) => {
          const ls = getLabelStyle((n.data as { nodeLabel: string }).nodeLabel);
          return ls.leftBorder;
        }}
        pannable
        zoomable
      />
    </ReactFlow>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function KGExplorerPage() {
  // We start with a demo case ID so the graph auto-populates on first render.
  const DEMO_CASE_ID = "CASE-2026-0001";
  const [caseIdInput, setCaseIdInput] = useState(DEMO_CASE_ID);
  const [activeCaseId, setActiveCaseId] = useState(DEMO_CASE_ID);
  const [direction, setDirection] = useState<"TB" | "LR">("TB");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set(ALL_NODE_TYPES));
  const [showFilter, setShowFilter] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [localSubgraph, setLocalSubgraph] = useState<SubgraphResponse | null>(null);

  const { data: apiSubgraph, isLoading, error, refetch } = useCaseSubgraph(activeCaseId);

  // Prefer API data; fall back to localSubgraph (demo)
  const subgraph = apiSubgraph ?? localSubgraph;

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const buildGraph = useCallback(
    (sg: SubgraphResponse | null | undefined, dir: "TB" | "LR") => {
      if (!sg) return;

      // Apply node-type filter
      const filteredNodes = sg.nodes.filter((n) => activeTypes.has(n.label));
      const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
      const filteredEdges = sg.edges.filter(
        (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target),
      );

      const rfNodes: Node[] = filteredNodes.map((n) => ({
        id: n.id,
        type: "kgNode",
        data: {
          nodeLabel: n.label,
          title: getNodeTitle(n),
          subtitle: (n.properties.tthc_code as string) || undefined,
        },
        position: { x: 0, y: 0 },
      }));

      const rfEdges: Edge[] = filteredEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        type: "smoothstep",
        style: { stroke: "#64748b", strokeWidth: 1.5 },
      }));

      setNodes(layoutGraph(rfNodes, rfEdges, dir));
      setEdges(rfEdges);
    },
    [activeTypes, setNodes, setEdges],
  );

  // Rebuild when data or direction or filter changes
  useEffect(() => {
    buildGraph(subgraph, direction);
  }, [subgraph, direction, buildGraph]);

  // Apply search: highlight matching nodes by dimming non-matches
  const highlightedNodes = useMemo(() => {
    if (!searchQuery.trim()) return nodes;
    const q = searchQuery.toLowerCase();
    return nodes.map((n) => {
      const d = n.data as { title: string; nodeLabel: string };
      const matches =
        d.title.toLowerCase().includes(q) || d.nodeLabel.toLowerCase().includes(q);
      return {
        ...n,
        style: matches
          ? undefined
          : { opacity: 0.25, filter: "grayscale(80%)" },
      };
    });
  }, [nodes, searchQuery]);

  function toggleType(type: string) {
    setActiveTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        if (next.size === 1) return prev; // keep at least one
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }

  function handleExportJSON() {
    const data = { nodes: nodes.map((n) => n.data), edges };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kg-export-${activeCaseId}-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Đã xuất JSON đồ thị");
  }

  async function handleLoadDemo() {
    setIsDemoLoading(true);
    try {
      const data = await apiClient.get<SubgraphResponse>(
        `/api/graph/case/${DEMO_CASE_ID}/subgraph`,
      );
      setLocalSubgraph(data);
      setActiveCaseId(DEMO_CASE_ID);
      setCaseIdInput(DEMO_CASE_ID);
      toast.success("Đã điền dữ liệu mẫu");
    } catch {
      // Use inline fixture
      setLocalSubgraph(DEMO_SUBGRAPH);
      setActiveCaseId(DEMO_CASE_ID);
      setCaseIdInput(DEMO_CASE_ID);
      toast.success("Đã điền dữ liệu mẫu");
    } finally {
      setIsDemoLoading(false);
    }
  }

  function handleApplyCaseId() {
    const trimmed = caseIdInput.trim();
    if (!trimmed) return;
    setActiveCaseId(trimmed);
    setLocalSubgraph(null);
  }

  const nodeCount = subgraph?.nodes.length ?? 0;
  const edgeCount = subgraph?.edges.length ?? 0;

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Page header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Knowledge Graph Explorer</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Khám phá đồ thị tri thức pháp luật và hồ sơ hành chính
          </p>
        </div>
        {nodeCount > 0 && (
          <div className="flex items-center gap-3 rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-1.5 text-xs text-[var(--text-muted)]">
            <span>
              <span className="font-semibold text-[var(--text-primary)]">{nodeCount}</span> nodes
            </span>
            <span>
              <span className="font-semibold text-[var(--text-primary)]">{edgeCount}</span> edges
            </span>
          </div>
        )}
      </div>

      {/* Case ID input */}
      <div className="flex items-center gap-2">
        <label htmlFor="kg-case-id" className="text-xs font-medium text-[var(--text-secondary)] shrink-0">
          Mã hồ sơ:
        </label>
        <input
          id="kg-case-id"
          type="text"
          value={caseIdInput}
          onChange={(e) => setCaseIdInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") handleApplyCaseId(); }}
          placeholder="Nhập case ID..."
          className="h-8 w-60 rounded-md border border-[var(--border-default)] bg-[var(--bg-canvas)] px-3 text-xs outline-none placeholder:text-[var(--text-muted)] focus:border-[var(--accent-primary)] focus:ring-1 focus:ring-[var(--accent-primary)]"
          aria-label="Nhập mã hồ sơ để xem đồ thị"
        />
        <button
          type="button"
          onClick={handleApplyCaseId}
          className="flex h-8 items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 text-xs font-medium text-white transition-opacity hover:opacity-90"
          aria-label="Tải đồ thị cho hồ sơ này"
        >
          Tải
        </button>
      </div>

      {/* Toolbar */}
      <KGToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeTypes={activeTypes}
        onToggleType={toggleType}
        direction={direction}
        onToggleDirection={() => setDirection((d) => (d === "TB" ? "LR" : "TB"))}
        onFitView={() => {
          // fitView is called via ReactFlow instance — trigger rebuild to re-fit
          buildGraph(subgraph, direction);
        }}
        onExportJSON={handleExportJSON}
        onRefresh={() => void refetch()}
        onLoadDemo={() => void handleLoadDemo()}
        isLoading={isLoading}
        isDemoLoading={isDemoLoading}
        showFilter={showFilter}
        onToggleFilter={() => setShowFilter((v) => !v)}
      />

      {/* Graph canvas */}
      <div
        className="flex-1 min-h-[500px] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]"
        style={{ height: "calc(100vh - 360px)" }}
      >
        {isLoading && !localSubgraph ? (
          <div className="flex h-full items-center justify-center gap-3">
            <Loader2 className="h-5 w-5 animate-spin text-[var(--accent-primary)]" />
            <p className="text-sm text-[var(--text-muted)]">Đang tải đồ thị...</p>
          </div>
        ) : error && !localSubgraph ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
            <AlertTriangle className="h-8 w-8 text-[var(--accent-warning)]" />
            <div>
              <p className="text-sm font-medium text-[var(--text-primary)]">
                Không thể tải đồ thị từ server
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Kiểm tra kết nối hoặc dùng dữ liệu mẫu để demo
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void refetch()}
                className="flex items-center gap-1.5 rounded-md border border-[var(--border-default)] px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--bg-surface-raised)]"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Thử lại
              </button>
              <button
                type="button"
                onClick={() => void handleLoadDemo()}
                disabled={isDemoLoading}
                className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-3 py-1.5 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {isDemoLoading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5" />
                )}
                Dữ liệu mẫu
              </button>
            </div>
          </div>
        ) : highlightedNodes.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-6 text-center">
            <p className="text-sm text-[var(--text-muted)]">
              Chưa có dữ liệu đồ thị. Nhập mã hồ sơ hoặc nhấn &quot;Dữ liệu mẫu&quot;.
            </p>
            <button
              type="button"
              onClick={() => void handleLoadDemo()}
              disabled={isDemoLoading}
              className="flex items-center gap-1.5 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {isDemoLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Tải dữ liệu mẫu
            </button>
          </div>
        ) : (
          <KGInnerGraph
            nodes={highlightedNodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
          />
        )}
      </div>
    </div>
  );
}
