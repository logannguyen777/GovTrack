# 17 - Frontend Screens: All 8 Application Views

## Muc tieu (Objective)

Implement all 8 GovFlow screens, the shared component library, graph visualization
rules, and accessibility requirements. After completing this guide, every screen
renders with live data, graph visualization works with WebSocket updates, and the
UI meets WCAG 2.1 AA compliance.

---

## 1. Shared Component Library

Build these components first, as every screen depends on them.

### 1.1 CaseCard: `frontend/src/components/cases/case-card.tsx`

```tsx
"use client";

import { motion } from "framer-motion";
import { slideUp } from "@/lib/motion";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { SLABadge } from "@/components/cases/sla-badge";

interface CaseCardProps {
  caseId: string;
  title: string;
  tthcCode: string;
  tthcName: string;
  status: string;
  classification: "unclassified" | "confidential" | "secret" | "top-secret";
  slaDeadline: string;      // ISO timestamp
  assignee?: string;
  gapCount?: number;
  onClick?: () => void;
}

export function CaseCard(props: CaseCardProps) {
  return (
    <motion.div
      variants={slideUp}
      initial="hidden"
      animate="visible"
      className="group cursor-pointer rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 shadow-sm transition-shadow hover:shadow-md"
      onClick={props.onClick}
      role="article"
      aria-label={`Case ${props.caseId}: ${props.title}`}
    >
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-mono text-[var(--text-muted)]">{props.caseId}</p>
          <h3 className="font-semibold text-sm text-[var(--text-primary)] line-clamp-2">
            {props.title}
          </h3>
          <p className="text-xs text-[var(--text-secondary)]">
            {props.tthcCode} - {props.tthcName}
          </p>
        </div>
        <ClassificationBadge level={props.classification} />
      </div>
      <div className="mt-3 flex items-center gap-2">
        <SLABadge deadline={props.slaDeadline} />
        <span className="rounded-full bg-[var(--bg-surface-raised)] px-2 py-0.5 text-[10px] font-medium">
          {props.status}
        </span>
        {props.gapCount != null && props.gapCount > 0 && (
          <span className="rounded-full bg-[var(--accent-warning)]/20 px-2 py-0.5 text-[10px] font-medium text-[var(--accent-warning)]">
            {props.gapCount} gap{props.gapCount > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </motion.div>
  );
}
```

### 1.2 SLABadge: `frontend/src/components/cases/sla-badge.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";

export function SLABadge({ deadline }: { deadline: string }) {
  const [remaining, setRemaining] = useState("");
  const [urgency, setUrgency] = useState<"normal" | "warning" | "critical">("normal");

  useEffect(() => {
    function update() {
      const diff = new Date(deadline).getTime() - Date.now();
      const hours = Math.floor(diff / 3_600_000);
      const days = Math.floor(hours / 24);
      if (diff <= 0) { setRemaining("Overdue"); setUrgency("critical"); }
      else if (hours < 24) { setRemaining(`${hours}h left`); setUrgency("critical"); }
      else if (days < 3) { setRemaining(`${days}d left`); setUrgency("warning"); }
      else { setRemaining(`${days}d left`); setUrgency("normal"); }
    }
    update();
    const iv = setInterval(update, 60_000);
    return () => clearInterval(iv);
  }, [deadline]);

  const colors = {
    normal: "text-[var(--accent-success)]",
    warning: "text-[var(--accent-warning)]",
    critical: "text-[var(--accent-error)] animate-pulse",
  };

  return (
    <span className={`text-[10px] font-mono font-bold ${colors[urgency]}`}
          role="timer" aria-label={`SLA: ${remaining}`}>
      {remaining}
    </span>
  );
}
```

### 1.3 GapCard, CitationBadge, TimelineStep, AnimatedCounter, RedactedField

```tsx
// frontend/src/components/cases/gap-card.tsx
export function GapCard({ gap }: { gap: { id: string; description: string; severity: "low" | "medium" | "high" | "critical"; fix_suggestion: string; requirement_ref: string } }) {
  const severityColors = {
    low: "border-l-blue-400", medium: "border-l-amber-400",
    high: "border-l-orange-500", critical: "border-l-red-500",
  };
  return (
    <div className={`rounded-md border border-[var(--border-subtle)] border-l-4 ${severityColors[gap.severity]} bg-[var(--bg-surface)] p-3 space-y-2`}
         role="alert" aria-label={`Gap: ${gap.description}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold uppercase">{gap.severity}</span>
        <span className="text-[10px] font-mono text-[var(--text-muted)]">{gap.id}</span>
      </div>
      <p className="text-sm">{gap.description}</p>
      <p className="text-xs text-[var(--text-secondary)]">Suggestion: {gap.fix_suggestion}</p>
      <p className="text-[10px] font-mono text-[var(--text-muted)]">Ref: {gap.requirement_ref}</p>
    </div>
  );
}

// frontend/src/components/cases/citation-badge.tsx
export function CitationBadge({ citation }: { citation: { law_name: string; article: string; relevance: number } }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md bg-purple-500/10 px-2 py-1 text-[11px] font-medium text-purple-400 border border-purple-500/20"
          title={`${citation.law_name} - ${citation.article} (${(citation.relevance * 100).toFixed(0)}%)`}>
      {citation.article}
      <span className="text-[9px] opacity-60">{(citation.relevance * 100).toFixed(0)}%</span>
    </span>
  );
}

// frontend/src/components/cases/timeline-step.tsx
export function TimelineStep({ step, isLast }: { step: { label: string; timestamp: string; status: "completed" | "active" | "pending" }; isLast: boolean }) {
  const dot = { completed: "bg-[var(--accent-success)]", active: "bg-[var(--accent-primary)] animate-pulse", pending: "bg-[var(--border-default)]" };
  return (
    <div className="flex gap-3" role="listitem">
      <div className="flex flex-col items-center">
        <div className={`h-3 w-3 rounded-full ${dot[step.status]}`} />
        {!isLast && <div className="w-px flex-1 bg-[var(--border-subtle)]" />}
      </div>
      <div className="pb-4">
        <p className="text-sm font-medium">{step.label}</p>
        <p className="text-[10px] text-[var(--text-muted)]">{step.timestamp}</p>
      </div>
    </div>
  );
}

// frontend/src/components/ui/animated-counter.tsx
// Uses Framer Motion useMotionValue + useSpring for smooth number transitions
export function AnimatedCounter({ value, suffix = "" }: { value: number; suffix?: string }) {
  // Implementation: spring-animated number that counts up from 0 to value
  // Duration: var(--duration-emphasis) = 400ms
  return <span className="font-mono tabular-nums">{value}{suffix}</span>;
}

// frontend/src/components/ui/redacted-field.tsx
// Blur-to-clear animation for property mask demo
export function RedactedField({ value, isRevealed }: { value: string; isRevealed: boolean }) {
  return (
    <motion.span
      animate={isRevealed ? "revealed" : "masked"}
      variants={{ masked: { filter: "blur(8px)", opacity: 0.6 }, revealed: { filter: "blur(0px)", opacity: 1 } }}
      transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
      className="inline-block"
    >
      {value}
    </motion.span>
  );
}
```

---

## 2. Screen 1 — Citizen Portal

### Route: `frontend/src/app/(public)/page.tsx`

```tsx
"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { staggerContainer, slideUp } from "@/lib/motion";

const TTHC_CARDS = [
  { code: "1.004415", name: "Cap phep xay dung",       icon: "Building", color: "blue" },
  { code: "1.000046", name: "GCN quyen su dung dat",    icon: "Map",      color: "green" },
  { code: "1.001757", name: "Dang ky kinh doanh",       icon: "Briefcase",color: "purple" },
  { code: "1.000122", name: "Ly lich tu phap",          icon: "FileText", color: "amber" },
  { code: "2.002154", name: "Giay phep moi truong",     icon: "Leaf",     color: "emerald" },
];

export default function CitizenPortal() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="min-h-screen bg-[var(--bg-app)]">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center px-4 py-20 text-center">
        <h1 className="text-4xl font-bold text-[var(--text-primary)]">
          Cong dich vu cong truc tuyen
        </h1>
        <p className="mt-3 text-lg text-[var(--text-secondary)] max-w-xl">
          Nop ho so thu tuc hanh chinh nhanh chong, minh bach voi AI
        </p>
        {/* Search bar */}
        <div className="mt-8 flex w-full max-w-lg">
          <input
            type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tim kiem thu tuc hanh chinh..."
            className="flex-1 rounded-l-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-3 text-sm"
            aria-label="Search procedures"
          />
          <button className="rounded-r-lg bg-[var(--accent-primary)] px-6 py-3 text-white font-medium">
            Tim kiem
          </button>
        </div>
      </section>

      {/* 5 TTHC Cards */}
      <motion.section variants={staggerContainer} initial="hidden" animate="visible"
        className="mx-auto max-w-5xl grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 px-4 pb-16">
        {TTHC_CARDS.map((tthc) => (
          <motion.a key={tthc.code} variants={slideUp} href={`/submit/${tthc.code}`}
            className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-6 hover:shadow-md transition-shadow">
            <p className="text-xs font-mono text-[var(--text-muted)]">{tthc.code}</p>
            <h3 className="mt-2 font-semibold">{tthc.name}</h3>
          </motion.a>
        ))}
      </motion.section>

      {/* Case tracking: enter case ID -> timeline */}
      {/* Submit wizard: 4-step form with presigned URL upload */}
    </div>
  );
}
```

**Submit Wizard** (4 steps):
1. Select TTHC type -> loads required document checklist
2. Applicant info form (name, CCCD, address, phone)
3. Document upload -> presigned URL from `/api/documents/presign` -> drag-drop zone
4. Review and submit -> POST `/api/cases` -> redirect to tracking page

**Case Tracking** (`(public)/track/[case_id]/page.tsx`):
- Timeline component showing processing stages
- Each stage: Tiep nhan -> Phan loai -> Kiem tra -> Xu ly -> Ket qua
- Real-time updates via polling (no WS for public route)

---

## 3. Screen 2 — Intake UI

### Route: `frontend/src/app/(internal)/intake/page.tsx`

```tsx
"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";

export default function IntakeUI() {
  const [files, setFiles] = useState<File[]>([]);
  const [ocrPreviews, setOcrPreviews] = useState<Record<string, string>>({});
  const [caseForm, setCaseForm] = useState({ tthc_code: "", applicant_name: "", notes: "" });

  const onDrop = useCallback(async (accepted: File[]) => {
    setFiles((prev) => [...prev, ...accepted]);
    // Upload each file, get OCR preview
    for (const file of accepted) {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/documents/upload-ocr", { method: "POST", body: fd });
      const { text_preview, document_id } = await res.json();
      setOcrPreviews((prev) => ({ ...prev, [document_id]: text_preview }));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { "application/pdf": [".pdf"], "image/*": [".jpg", ".png"] },
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tiep nhan ho so</h1>

      {/* Drag-drop upload zone */}
      <div {...getRootProps()} className={`rounded-lg border-2 border-dashed p-8 text-center
        ${isDragActive ? "border-[var(--accent-primary)] bg-[var(--accent-primary)]/5" : "border-[var(--border-default)]"}`}>
        <input {...getInputProps()} />
        <p className="text-sm text-[var(--text-secondary)]">
          {isDragActive ? "Tha tai lieu vao day..." : "Keo tha tai lieu hoac bam de chon"}
        </p>
      </div>

      {/* OCR preview panels */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(ocrPreviews).map(([docId, text]) => (
          <div key={docId} className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <p className="text-xs font-mono text-[var(--text-muted)] mb-2">{docId}</p>
            <pre className="text-xs whitespace-pre-wrap font-mono max-h-40 overflow-auto">{text}</pre>
          </div>
        ))}
      </div>

      {/* Case creation form */}
      {/* TTHC selector, applicant name, notes textarea */}
      {/* "Trigger Pipeline" button -> POST /api/cases -> navigates to /trace/{case_id} */}
    </div>
  );
}
```

---

## 4. Screen 3 — Agent Trace Viewer

### Route: `frontend/src/app/(internal)/trace/[case_id]/page.tsx`

```tsx
"use client";

import { useCallback, useEffect, useMemo } from "react";
import { ReactFlow, Background, Controls, useNodesState, useEdgesState } from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import { useTraceStore } from "@/lib/store";
import { wsManager } from "@/lib/ws";

// --- Custom node types ---
const NODE_STYLES: Record<string, { bg: string; border: string }> = {
  Case:     { bg: "bg-blue-900/30",    border: "border-blue-500" },
  Task:     { bg: "bg-gray-800/30",    border: "border-gray-500" },
  Document: { bg: "bg-indigo-900/30",  border: "border-indigo-500" },
  Gap:      { bg: "bg-amber-900/30",   border: "border-amber-500" },
  Citation: { bg: "bg-purple-900/30",  border: "border-purple-500" },
  Decision: { bg: "bg-green-900/30",   border: "border-green-500" },
  DecisionReject: { bg: "bg-red-900/30", border: "border-red-500" },
};

const NODE_WIDTH = 220;
const NODE_PADDING = 12;

function GraphNode({ data }: { data: { label: string; type: string; status?: string } }) {
  const style = NODE_STYLES[data.type] || NODE_STYLES.Task;
  const statusStrip = data.status === "running" ? "border-l-4 border-l-[var(--accent-primary)] animate-pulse"
    : data.status === "completed" ? "border-l-4 border-l-[var(--accent-success)]"
    : data.status === "failed" ? "border-l-4 border-l-[var(--accent-error)]" : "";

  return (
    <div className={`rounded-md border ${style.border} ${style.bg} ${statusStrip} p-[${NODE_PADDING}px]`}
         style={{ width: NODE_WIDTH }}>
      <p className="text-[10px] font-mono text-[var(--text-muted)]">{data.type}</p>
      <p className="text-sm font-medium truncate">{data.label}</p>
    </div>
  );
}

const nodeTypes = { graphNode: GraphNode };

export default function TraceViewer({ params }: { params: { case_id: string } }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const { steps, addStep, updateStep, setActiveStep } = useTraceStore();

  // Subscribe to WS trace events
  useEffect(() => {
    const unsub = wsManager.subscribe("trace", (msg) => {
      if (msg.type === "agent_step_started") addStep(msg.payload as any);
      if (msg.type === "agent_step_completed") updateStep((msg.payload as any).step_id, msg.payload as any);
      if (msg.type === "node_added") {
        // Add new node to graph with dagre re-layout
        const p = msg.payload as any;
        setNodes((prev) => [...prev, { id: p.id, type: "graphNode", data: p, position: { x: 0, y: 0 } }]);
      }
      if (msg.type === "edge_added") {
        const p = msg.payload as any;
        setEdges((prev) => [...prev, { id: p.id, source: p.source, target: p.target, type: "smoothstep" }]);
      }
    });
    return unsub;
  }, []);

  // Dagre layout: TB (top-bottom), re-run on node/edge changes
  useEffect(() => {
    if (nodes.length === 0) return;
    const g = new dagre.graphlib.Graph();
    g.setDefaultEdgeLabel(() => ({}));
    g.setGraph({ rankdir: "TB", ranksep: 60, nodesep: 40 });
    nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: 60 }));
    edges.forEach((e) => g.setEdge(e.source, e.target));
    dagre.layout(g);
    setNodes((nds) => nds.map((n) => {
      const pos = g.node(n.id);
      return { ...n, position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - 30 } };
    }));
  }, [nodes.length, edges.length]);

  return (
    <div className="flex h-full gap-4">
      {/* Graph panel: 70% width */}
      <div className="flex-[7] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)]">
        <ReactFlow
          nodes={nodes} edges={edges} nodeTypes={nodeTypes}
          onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          fitView defaultEdgeOptions={{ type: "smoothstep", animated: true }}
        >
          <Background gap={16} size={1} />
          <Controls />
        </ReactFlow>
      </div>

      {/* AgentStep sidebar: 30% width */}
      <div className="flex-[3] space-y-3 overflow-auto">
        <h2 className="font-semibold text-lg">Agent Steps</h2>
        {steps.map((step) => (
          <div key={step.step_id}
            onClick={() => setActiveStep(step.step_id)}
            className="cursor-pointer rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 hover:bg-[var(--bg-surface-raised)]">
            <p className="text-xs font-bold">{step.agent_name}</p>
            <p className="text-[10px] text-[var(--text-muted)]">{step.status}</p>
            <p className="text-xs mt-1 line-clamp-2">{step.output_summary || step.input_summary}</p>
          </div>
        ))}
        {/* Timeline scrubber: slider to replay steps chronologically */}
      </div>
    </div>
  );
}
```

---

## 5. Screen 4 — Compliance Workspace

### Route: `frontend/src/app/(internal)/compliance/[case_id]/page.tsx`

```tsx
"use client";

// Split view: documents (left 50%) | gaps + citations (right 50%)

export default function ComplianceWorkspace({ params }: { params: { case_id: string } }) {
  // Fetch case data: GET /api/cases/{case_id}/compliance
  // Returns: { documents, gaps, citations, decision_status }

  return (
    <div className="flex h-full gap-4">
      {/* Left: Document list with expandable previews */}
      <div className="flex-1 space-y-3 overflow-auto">
        <h2 className="font-semibold">Tai lieu ({/* count */})</h2>
        {/* Each document: thumbnail, name, classification badge, extracted entities */}
        {/* Click to open in Document Viewer (Screen 6) */}
      </div>

      {/* Right: Gaps and Citations */}
      <div className="flex-1 space-y-4 overflow-auto">
        <h2 className="font-semibold">Thieu sot ({/* gap count */})</h2>
        {/* GapCard list, sorted by severity */}
        {/* Each GapCard shows: description, severity, fix suggestion, requirement ref */}

        <h2 className="font-semibold mt-6">Can cu phap ly</h2>
        {/* CitationBadge list */}
        {/* Each badge links to law article in Document Viewer */}

        {/* Action bar at bottom */}
        <div className="sticky bottom-0 flex gap-3 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <button className="flex-1 rounded-md bg-[var(--accent-success)] py-2 text-white font-medium">
            Phe duyet
          </button>
          <button className="flex-1 rounded-md bg-[var(--accent-error)] py-2 text-white font-medium">
            Tu choi
          </button>
          <button className="rounded-md border border-[var(--border-default)] px-4 py-2">
            Yeu cau bo sung
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## 6. Screen 5 — Department Inbox

### Route: `frontend/src/app/(internal)/inbox/page.tsx`

```tsx
"use client";

import { DndContext, closestCenter } from "@dnd-kit/core";

const COLUMNS = [
  { id: "tiep_nhan",    label: "Tiep nhan",    color: "var(--accent-info)" },
  { id: "dang_xu_ly",   label: "Dang xu ly",   color: "var(--accent-primary)" },
  { id: "cho_y_kien",   label: "Cho y kien",   color: "var(--accent-warning)" },
  { id: "da_quyet_dinh",label: "Da quyet dinh", color: "var(--accent-success)" },
  { id: "tra_ket_qua",  label: "Tra ket qua",  color: "var(--text-muted)" },
];

export default function DepartmentInbox() {
  // Fetch cases grouped by status: GET /api/cases?view=kanban
  // DnD: move cards between columns -> PATCH /api/cases/{id}/status

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Ho so den</h1>
        {/* Filter: TTHC type, department, SLA urgency */}
      </div>

      <DndContext collisionDetection={closestCenter}>
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map((col) => (
            <div key={col.id} className="min-w-[280px] flex-shrink-0">
              {/* Column header with count badge */}
              <div className="mb-3 flex items-center gap-2">
                <div className="h-2 w-2 rounded-full" style={{ background: col.color }} />
                <h3 className="text-sm font-semibold">{col.label}</h3>
                <span className="rounded-full bg-[var(--bg-surface-raised)] px-2 text-[10px]">
                  {/* count */}
                </span>
              </div>
              {/* CaseCards in this column, sorted by SLA urgency */}
              <div className="space-y-2">
                {/* <CaseCard ... /> for each case in this column */}
              </div>
            </div>
          ))}
        </div>
      </DndContext>

      {/* Consult panel: slide-out sheet for inter-department consultation */}
      {/* Triggered by "Cho y kien" column action, shows department selector + message */}
    </div>
  );
}
```

---

## 7. Screen 6 — Document Viewer

### Route: `frontend/src/app/(internal)/documents/[id]/page.tsx`

```tsx
"use client";

import { Document, Page } from "react-pdf";
import { ClassificationBadge } from "@/components/ui/classification-badge";
import { RedactedField } from "@/components/ui/redacted-field";
import { motion } from "framer-motion";

export default function DocumentViewer({ params }: { params: { id: string } }) {
  // Fetch: GET /api/documents/{id}
  // Returns: { url, classification, entities, summary, ocr_text }

  return (
    <div className="flex h-full gap-4">
      {/* Left: PDF viewer with entity overlay */}
      <div className="flex-[6] rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] overflow-auto relative">
        <Document file={`/api/documents/${params.id}/file`}>
          <Page pageNumber={1} width={700} />
        </Document>
        {/* Entity overlay: highlight bounding boxes for detected entities */}
        {/* Colored by entity type: name=blue, date=green, amount=amber, id=red */}
      </div>

      {/* Right: Info tabs */}
      <div className="flex-[4] space-y-4">
        {/* Classification badge */}
        <div className="flex items-center gap-2">
          <ClassificationBadge level="confidential" />
          <span className="text-sm font-medium">Document classification</span>
        </div>

        {/* Tabs: Summary | Entities | OCR Text | Metadata */}
        {/* Summary tab: AI-generated summary, key findings */}
        {/* Entities tab: list of extracted entities with types */}
        {/* OCR tab: raw OCR text, font-mono */}

        {/* Property mask demo: RedactedField with blur animation */}
        <div className="rounded-md border border-[var(--border-subtle)] p-3">
          <p className="text-xs font-bold mb-2">Sensitive Fields</p>
          <div className="space-y-1 text-sm">
            <p>CCCD: <RedactedField value="079201001234" isRevealed={false} /></p>
            <p>Phone: <RedactedField value="090 123 4567" isRevealed={false} /></p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 8. Screen 7 — Leadership Dashboard

### Route: `frontend/src/app/(internal)/dashboard/page.tsx`

```tsx
"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { AnimatedCounter } from "@/components/ui/animated-counter";

export default function LeadershipDashboard() {
  // Fetch: GET /api/leadership/metrics
  // Returns: { kpis, sla_heatmap, cases_by_tthc, weekly_brief, approve_queue }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Bang dieu hanh</h1>

      {/* KPI Cards row */}
      <div className="grid grid-cols-4 gap-4">
        <KPICard label="Tong ho so" value={142} trend={+12} />
        <KPICard label="Dang xu ly" value={38} trend={-3} />
        <KPICard label="SLA dat" value={94} suffix="%" trend={+2} />
        <KPICard label="Trung binh xu ly" value={3.2} suffix=" ngay" trend={-0.5} />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* SLA Heatmap: department x week grid, color = % on-time */}
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <h3 className="text-sm font-semibold mb-3">SLA Heatmap theo phong ban</h3>
          {/* Grid: rows=departments, cols=weeks, cell color=green(>90%) amber(70-90%) red(<70%) */}
        </div>

        {/* Cases by TTHC bar chart */}
        <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <h3 className="text-sm font-semibold mb-3">Ho so theo TTHC</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={[
              { name: "CPXD", count: 45 }, { name: "QSDD", count: 32 },
              { name: "DKKD", count: 28 }, { name: "LLTP", count: 22 },
              { name: "GPMT", count: 15 },
            ]}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#06b6d4"].map((c, i) => (
                  <Cell key={i} fill={c} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Hologres AI Functions weekly brief card */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 className="text-sm font-semibold mb-2">Bao cao tuan (AI)</h3>
        <p className="text-sm text-[var(--text-secondary)] font-legal leading-relaxed">
          {/* Weekly brief generated by Hologres AI Functions */}
        </p>
      </div>

      {/* Approve queue: pending cases requiring leader signature */}
    </div>
  );
}

function KPICard({ label, value, suffix, trend }: { label: string; value: number; suffix?: string; trend: number }) {
  return (
    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
      <p className="text-xs text-[var(--text-muted)]">{label}</p>
      <p className="text-2xl font-bold mt-1">
        <AnimatedCounter value={value} suffix={suffix} />
      </p>
      <p className={`text-xs mt-1 ${trend >= 0 ? "text-[var(--accent-success)]" : "text-[var(--accent-error)]"}`}>
        {trend >= 0 ? "+" : ""}{trend}
      </p>
    </div>
  );
}
```

---

## 9. Screen 8 — Security Console

### Route: `frontend/src/app/(internal)/security/page.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import { wsManager } from "@/lib/ws";
import { RedactedField } from "@/components/ui/redacted-field";

export default function SecurityConsole() {
  const [auditLog, setAuditLog] = useState<any[]>([]);
  const [elevationActive, setElevationActive] = useState(false);

  // Live audit log via WebSocket
  useEffect(() => {
    const unsub = wsManager.subscribe("audit", (msg) => {
      setAuditLog((prev) => [msg.payload, ...prev].slice(0, 200));
    });
    return unsub;
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trung tam bao mat</h1>

      <div className="grid grid-cols-3 gap-4">
        {/* Col 1: Live audit log */}
        <div className="col-span-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
          <h3 className="text-sm font-semibold mb-3">Nhat ky kiem tra (Live)</h3>
          <div className="space-y-1 max-h-[500px] overflow-auto font-mono text-xs">
            {auditLog.map((event, i) => (
              <div key={i} className={`flex gap-2 px-2 py-1 rounded
                ${event.action === "DENY" ? "bg-red-500/10 text-red-400" : "text-[var(--text-secondary)]"}`}>
                <span className="w-20 shrink-0">{event.tier}</span>
                <span className="w-16 shrink-0 font-bold">{event.action}</span>
                <span className="w-28 shrink-0">{event.agent_id}</span>
                <span className="truncate">{event.detail}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Col 2: 3-scene demo controls */}
        <div className="space-y-4">
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="text-sm font-semibold mb-3">Demo Permissions</h3>
            <div className="space-y-2">
              <button onClick={() => fetch("/api/demo/permissions/scene-a/sdk-guard-rejection", { method: "POST" })}
                className="w-full rounded-md border border-[var(--border-default)] px-3 py-2 text-xs text-left hover:bg-[var(--bg-surface-raised)]">
                Scene A: SDK Guard Rejection
              </button>
              <button onClick={() => fetch("/api/demo/permissions/scene-b/rbac-rejection", { method: "POST" })}
                className="w-full rounded-md border border-[var(--border-default)] px-3 py-2 text-xs text-left hover:bg-[var(--bg-surface-raised)]">
                Scene B: RBAC Rejection
              </button>
              <button onClick={() => setElevationActive(!elevationActive)}
                className="w-full rounded-md border border-[var(--border-default)] px-3 py-2 text-xs text-left hover:bg-[var(--bg-surface-raised)]">
                Scene C: Clearance Elevation
              </button>
            </div>
          </div>

          {/* Classification distribution pie */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="text-sm font-semibold mb-3">Phan bo phan loai</h3>
            {/* Donut chart: Unclassified(70%) Confidential(20%) Secret(8%) TopSecret(2%) */}
          </div>

          {/* Denial heatmap: agent x hour, color = denial count */}
          <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
            <h3 className="text-sm font-semibold mb-3">Tu choi theo gio</h3>
            {/* Heatmap grid */}
          </div>
        </div>
      </div>

      {/* RedactedField demo with blur-to-clear animation */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4">
        <h3 className="text-sm font-semibold mb-3">Clearance Elevation Demo</h3>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs text-[var(--text-muted)]">CCCD</p>
            <RedactedField value="079201001234" isRevealed={elevationActive} />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Dia chi</p>
            <RedactedField value="12 Le Loi, Quan 1, TP.HCM" isRevealed={elevationActive} />
          </div>
          <div>
            <p className="text-xs text-[var(--text-muted)]">Tai khoan</p>
            <RedactedField value="VCB 1234567890" isRevealed={elevationActive} />
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 10. Graph Visualization Rules

All React Flow graph instances follow these rules:

| Rule                 | Value                                          |
|----------------------|------------------------------------------------|
| Layout algorithm     | dagre, direction=TB (top-to-bottom)            |
| Edge type            | smoothstep (orthogonal with rounded corners)   |
| Node width           | 220px fixed                                    |
| Node padding         | 12px                                           |
| Node border          | 1px solid, color from NODE_STYLES              |
| Status indicator     | Left-border strip: 4px, color by status        |
| Node spacing         | ranksep=60, nodesep=40                         |
| Animation on add     | Framer Motion fadeIn + scaleIn, 250ms          |
| Edge animation       | animated=true (moving dots for active)         |
| Background           | Dot grid, gap=16, size=1                       |
| Interactivity        | Pan, zoom, fit-view on load, click to select   |

### Node type color map:

```
Case      -> blue-500    (primary entity)
Task      -> gray-500    (processing step)
Document  -> indigo-500  (uploaded / generated)
Gap       -> amber-500   (deficiency found)
Citation  -> purple-500  (legal reference)
Decision  -> green-500   (approved) / red-500 (rejected)
Entity    -> cyan-500    (extracted data point)
```

---

## 11. Accessibility Requirements

- Keyboard navigation: all interactive elements reachable via Tab, Escape closes modals
- ARIA labels: every card, badge, button, and chart has descriptive `aria-label`
- Focus indicators: 2px ring with `ring-[var(--accent-primary)]` on focus-visible
- Screen reader: graph nodes announce type + label + status on focus
- High contrast mode: CSS media query `@media (prefers-contrast: high)` increases border widths, removes transparency
- Color blind: severity uses shape indicators in addition to color (icon + text label)
- Reduced motion: `@media (prefers-reduced-motion: reduce)` disables all Framer Motion animations

---

## 12. Verification Checklist

```bash
# 1. All 8 screens render without errors
npm run dev
# Visit each route, verify no console errors:
#   / (Citizen Portal)
#   /intake (Intake UI)
#   /trace/test-case-001 (Agent Trace)
#   /compliance/test-case-001 (Compliance)
#   /inbox (Kanban)
#   /documents/test-doc-001 (Document Viewer)
#   /dashboard (Leadership)
#   /security (Security Console)

# 2. Graph visualization
# Visit /trace/test-case-001
# Verify: dagre TB layout, smoothstep edges, correct node colors
# Send WS event: verify new node appears with animation

# 3. WS events update UI
# Open /security, verify live audit log populates
# Open /trace, submit case, verify steps appear in sidebar

# 4. Responsive
# Resize to 768px: sidebar collapses, kanban scrolls horizontally
# Resize to 1440px: all layouts fit without horizontal scroll

# 5. TypeScript compiles
npm run build
# Expected: 0 type errors

# 6. Accessibility
# Tab through /dashboard: all cards focusable
# Screen reader: VoiceOver reads classification badges
```

---

## Tong ket (Summary)

| Screen               | Route                              | Key Components                    |
|----------------------|------------------------------------|-----------------------------------|
| Citizen Portal       | (public)/                          | Hero search, TTHC cards, wizard   |
| Intake UI            | (internal)/intake/                 | Drag-drop, OCR preview, pipeline  |
| Agent Trace Viewer   | (internal)/trace/[case_id]/        | React Flow, dagre, WS live nodes  |
| Compliance Workspace | (internal)/compliance/[case_id]/   | Split view, GapCard, CitationBadge|
| Department Inbox     | (internal)/inbox/                  | Kanban 5-col, DnD, SLA countdown |
| Document Viewer      | (internal)/documents/[id]/         | react-pdf, entity overlay, tabs   |
| Leadership Dashboard | (internal)/dashboard/              | KPI cards, charts, AI weekly brief|
| Security Console     | (internal)/security/               | Live audit, demo controls, blur   |

Next step: proceed to `18-integration-testing.md` for E2E and permission tests.
