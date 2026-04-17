"use client";

import * as React from "react";
import type { GraphOp } from "@/lib/stores/agent-artifact-store";

// ---------------------------------------------------------------------------
// Mini syntax highlight for Gremlin queries
// Bold g.V() traversal keywords
// ---------------------------------------------------------------------------

function GremlinHighlight({ query }: { query: string }) {
  // Very lightweight: bold known Gremlin entry points
  const parts = query.split(/(g\.[VE]\(\)|\.has\(|\.out\(|\.in\(|\.where\(|\.values\(|\.toList\(\))/g);
  return (
    <code className="text-[11px] leading-relaxed" style={{ fontFamily: "var(--font-mono)" }}>
      {parts.map((part, i) => {
        if (part.startsWith("g.") || part === ".toList()") {
          return (
            <strong key={i} style={{ color: "var(--accent-primary)" }}>
              {part}
            </strong>
          );
        }
        if (part.startsWith(".has(") || part.startsWith(".out(") || part.startsWith(".in(") || part.startsWith(".where(") || part.startsWith(".values(")) {
          return (
            <span key={i} style={{ color: "var(--accent-warning)" }}>
              {part}
            </span>
          );
        }
        return <span key={i} style={{ color: "var(--text-secondary)" }}>{part}</span>;
      })}
    </code>
  );
}

// ---------------------------------------------------------------------------
// Mini graph (static SVG — avoids heavy ReactFlow import overhead per card)
// ---------------------------------------------------------------------------

interface MiniGraphProps {
  nodes: GraphOp["nodes"];
  edges: GraphOp["edges"];
}

const MAX_MINI_NODES = 20;
const MINI_NODE_W = 80;
const MINI_NODE_H = 28;
const COLS = 4;
const COL_GAP = 100;
const ROW_GAP = 50;
const PAD = 12;

function MiniGraph({ nodes, edges }: MiniGraphProps) {
  const visible = nodes.slice(0, MAX_MINI_NODES);
  const truncated = nodes.length > MAX_MINI_NODES;

  const positions: Record<string, { x: number; y: number }> = {};
  visible.forEach((n, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    positions[n.id] = {
      x: PAD + col * COL_GAP,
      y: PAD + row * ROW_GAP,
    };
  });

  const rows = Math.ceil(visible.length / COLS);
  const svgW = PAD * 2 + COLS * COL_GAP;
  const svgH = PAD * 2 + rows * ROW_GAP;

  return (
    <div>
      <svg
        width="100%"
        viewBox={`0 0 ${svgW} ${svgH}`}
        className="overflow-visible"
        aria-label="Mini graph visualization"
        role="img"
      >
        {/* Edges */}
        {edges.map((e, i) => {
          const src = positions[e.source];
          const tgt = positions[e.target];
          if (!src || !tgt) return null;
          const x1 = src.x + MINI_NODE_W / 2;
          const y1 = src.y + MINI_NODE_H / 2;
          const x2 = tgt.x + MINI_NODE_W / 2;
          const y2 = tgt.y + MINI_NODE_H / 2;
          return (
            <line
              key={`e-${i}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#64748b"
              strokeWidth={1}
              strokeOpacity={0.5}
            />
          );
        })}

        {/* Nodes */}
        {visible.map((n) => {
          const pos = positions[n.id];
          if (!pos) return null;
          return (
            <g key={n.id} transform={`translate(${pos.x}, ${pos.y})`}>
              <rect
                width={MINI_NODE_W}
                height={MINI_NODE_H}
                rx={4}
                fill="var(--bg-surface)"
                stroke="var(--border-subtle)"
                strokeWidth={1}
              />
              <text
                x={MINI_NODE_W / 2}
                y={MINI_NODE_H / 2 + 4}
                textAnchor="middle"
                fontSize={9}
                fill="var(--text-secondary)"
                fontFamily="var(--font-mono)"
              >
                {n.label.slice(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>
      {truncated && (
        <p
          className="mt-1 text-[10px] text-center"
          style={{ color: "var(--text-muted)" }}
        >
          Hiển thị {MAX_MINI_NODES}/{nodes.length} node
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GraphOpCard
// ---------------------------------------------------------------------------

interface GraphOpCardProps {
  op: GraphOp;
}

function GraphOpCard({ op }: GraphOpCardProps) {
  const [showGraph, setShowGraph] = React.useState(false);

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        borderColor: "var(--border-subtle)",
        backgroundColor: "var(--bg-surface)",
      }}
    >
      {/* Query */}
      <div className="px-3 py-2">
        <p
          className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: "var(--text-muted)" }}
        >
          Gremlin Query
        </p>
        <pre
          className="overflow-x-auto rounded p-2 text-[11px] leading-relaxed whitespace-pre-wrap break-words"
          style={{ backgroundColor: "var(--bg-subtle)" }}
        >
          <GremlinHighlight query={op.query} />
        </pre>
      </div>

      {/* Graph toggle */}
      {op.nodes.length > 0 && (
        <div
          className="border-t"
          style={{ borderColor: "var(--border-subtle)" }}
        >
          <button
            type="button"
            className="flex w-full items-center justify-between px-3 py-2 text-xs hover:bg-[var(--bg-surface-raised)] transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent-primary)]"
            onClick={() => setShowGraph((p) => !p)}
            aria-expanded={showGraph}
          >
            <span style={{ color: "var(--text-secondary)" }}>
              {op.nodes.length} node · {op.edges.length} edge
            </span>
            <span style={{ color: "var(--text-muted)" }} aria-hidden="true">
              {showGraph ? "▼ Ẩn đồ thị" : "▶ Xem đồ thị"}
            </span>
          </button>
          {showGraph && (
            <div
              className="border-t px-3 pb-3"
              style={{ borderColor: "var(--border-subtle)" }}
            >
              <MiniGraph nodes={op.nodes} edges={op.edges} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// GraphTab
// ---------------------------------------------------------------------------

interface GraphTabProps {
  ops: GraphOp[];
}

export function GraphTab({ ops }: GraphTabProps) {
  if (ops.length === 0) {
    return (
      <div
        className="flex h-full flex-col items-center justify-center p-6 text-center"
        style={{ color: "var(--text-muted)" }}
      >
        <p className="text-sm">Chưa có thao tác đồ thị</p>
        <p className="text-xs mt-1 opacity-70">
          Gremlin query và kết quả Knowledge Graph sẽ hiển thị ở đây
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto px-3 py-2 space-y-2">
      {ops.map((op) => (
        <GraphOpCard key={op.id} op={op} />
      ))}
    </div>
  );
}
