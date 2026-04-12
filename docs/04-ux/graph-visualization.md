# Graph Visualization — React Flow / Cytoscape usage

Graph viz is GovFlow's "signature" visual. Judges see a case subgraph grow in realtime → wow moment.

## Two visualization contexts

| Context | Use case | Library |
|---|---|---|
| **Agent Trace Viewer** (live) | Realtime agent steps + context graph growth | React Flow |
| **KG Explorer** (static) | Navigate Vietnamese law corpus + TTHC catalog | Cytoscape.js |

## React Flow — Agent Trace Viewer

### Why React Flow
- First-class React support, good TypeScript types
- Smooth animations out of the box
- Custom node components (we style each agent type differently)
- WebSocket-friendly (easy state updates)
- Decent performance for ~200 nodes (our hackathon target)

### Node types

```tsx
// nodes.ts
export const nodeTypes = {
  case: CaseNode,           // Blue, rounded, root
  agent_step: AgentStepNode, // Colored per agent, small circle
  document: DocumentNode,    // Gray, rectangular
  extracted_entity: EntityNode,  // Gray, small pill
  gap: GapNode,              // Amber, warning icon
  citation: CitationNode,    // Purple, book icon
  article: ArticleNode,      // Purple outlined, law reference
  classification: ClassNode, // Red (Top Secret) to green (Unclassified)
  decision: DecisionNode,    // Green (approve) or red (deny)
  draft: DraftNode,          // Yellow, edit icon
  published: PublishedNode,  // Green check, sealed icon
  audit: AuditNode,          // Tiny dots, red for denies
}
```

### Layout

Use hierarchical layout (dagre) by default — makes temporal flow visible top-to-bottom.

```tsx
import { dagre } from 'dagre';
import ReactFlow, { useNodesState, useEdgesState } from 'reactflow';

function layoutGraph(nodes, edges) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 120 });

  nodes.forEach((n) => dagreGraph.setNode(n.id, { width: 180, height: 60 }));
  edges.forEach((e) => dagreGraph.setEdge(e.source, e.target));

  dagre.layout(dagreGraph);

  return nodes.map((n) => {
    const { x, y } = dagreGraph.node(n.id);
    return { ...n, position: { x: x - 90, y: y - 30 } };
  });
}
```

### Real-time updates via WebSocket

```tsx
function AgentTraceViewer({ caseId }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    const ws = new WebSocket(`/api/trace/ws?case_id=${caseId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === 'graph_update') {
        // Add new vertices
        setNodes((prev) => [
          ...prev,
          ...msg.added_vertices.map(toReactFlowNode)
        ]);
        // Add new edges with animation
        setEdges((prev) => [
          ...prev,
          ...msg.added_edges.map((e) => ({
            ...toReactFlowEdge(e),
            animated: true,  // animate on entry
          }))
        ]);
        // Re-layout
        const laidOut = layoutGraph(...);
        setNodes(laidOut);
      }

      if (msg.type === 'agent_step') {
        // Pulse the corresponding node
        pulseNode(msg.agent_step_id);
      }
    };

    return () => ws.close();
  }, [caseId]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      fitView
      minZoom={0.3}
      maxZoom={1.5}
    >
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
}
```

### Animations

- **New node entry:** fade-in + scale(0.8 → 1.0), 400ms
- **New edge entry:** `stroke-dashoffset` animation, 500ms
- **Step pulse:** brief scale(1.0 → 1.1 → 1.0) + glow, 600ms
- **Denied access:** red shake + flash, 300ms

Use Framer Motion for node-level animations, CSS keyframes for edge dashoffset.

### Click interactions

- **Click node** → opens detail panel with properties + related steps
- **Hover edge** → tooltip with edge type
- **Click background** → close detail
- **Double-click** → zoom to that part of graph

### Layout toggle

Two modes:
1. **Temporal (hierarchical top-down)** — default, shows time flow
2. **Structural (force-directed)** — better for seeing topology

Toggle in toolbar.

---

## Cytoscape.js — KG Explorer

### Why Cytoscape for KG
- Better performance for larger static graphs (~1000+ nodes)
- More sophisticated layouts (cola, cose-bilkent)
- Feature-rich (filtering, querying)
- Good for exploration UX

### Use case
Navigate the Vietnamese legal corpus + TTHC catalog to understand cross-references.

```tsx
import cytoscape from 'cytoscape';
import cola from 'cytoscape-cola';

cytoscape.use(cola);

function KGExplorer({ rootNodeId }) {
  const cyRef = useRef(null);
  const [elements, setElements] = useState([]);

  useEffect(() => {
    // Load initial subgraph around root
    fetchKGSubgraph(rootNodeId, depth=2).then(setElements);
  }, [rootNodeId]);

  useEffect(() => {
    if (!cyRef.current || !elements.length) return;

    cyRef.current = cytoscape({
      container: document.getElementById('kg-cy'),
      elements,
      style: [
        {
          selector: 'node[type="Law"]',
          style: { 'background-color': '#9333EA', 'label': 'data(name)', 'shape': 'rectangle' }
        },
        {
          selector: 'node[type="Article"]',
          style: { 'background-color': '#A78BFA', 'label': 'data(num)' }
        },
        {
          selector: 'node[type="TTHCSpec"]',
          style: { 'background-color': '#14B8A6', 'label': 'data(name)' }
        },
        {
          selector: 'edge[label="SUPERSEDED_BY"]',
          style: { 'line-color': '#DC2626', 'target-arrow-color': '#DC2626' }
        },
        // ... more styles
      ],
      layout: { name: 'cola', animate: true }
    });

    // Click to expand
    cyRef.current.on('tap', 'node', async (evt) => {
      const node = evt.target;
      const neighbors = await fetchNeighbors(node.id());
      cyRef.current.add(neighbors);
      cyRef.current.layout({ name: 'cola', animate: true }).run();
    });
  }, [elements]);

  return <div id="kg-cy" style={{ width: '100%', height: '600px' }} />;
}
```

### Features
- **Search law by keyword** — jump to node
- **Expand neighbors** on click (lazy loading)
- **Highlight amendment chain** — trace `SUPERSEDED_BY` path
- **Filter by classification** — dim Secret/Top Secret if user clearance insufficient

---

## Node styling — unified look

### Color palette per label

| Label | Fill | Stroke | Icon |
|---|---|---|---|
| Case | #2563EB (blue) | #1D4ED8 | 📋 |
| Applicant | #6B7280 (gray) | — | 👤 |
| Document | #6B7280 | — | 📄 |
| ExtractedEntity | #9CA3AF | — | 🏷️ |
| Gap | #F59E0B (amber) | — | ⚠️ |
| Citation | #A78BFA (purple) | — | 📖 |
| Article | #8B5CF6 | #7C3AED | 📜 |
| Law / Decree | #6D28D9 | — | 📚 |
| TTHCSpec | #14B8A6 (teal) | — | ⚙️ |
| Organization | #06B6D4 (cyan) | — | 🏛️ |
| Classification | per level | — | 🔒 |
| Decision | #10B981 / #DC2626 | — | ✓/✗ |
| Draft | #EAB308 (yellow) | — | ✏️ |
| PublishedDoc | #10B981 (green) | — | 📑 |
| AgentStep | per agent color | — | ⚡ |
| AuditEvent | #DC2626 (small dot) | — | 🔴 |

### Agent-specific colors (for AgentStep nodes)

```
Planner:         #3B82F6 (blue)
DocAnalyzer:     #6366F1 (indigo)
Classifier:      #8B5CF6 (violet)
Compliance:      #EC4899 (pink)
LegalLookup:     #A78BFA (purple)
Router:          #06B6D4 (cyan)
Consult:         #10B981 (emerald)
Summarizer:      #F59E0B (amber)
Drafter:         #EAB308 (yellow)
SecurityOfficer: #DC2626 (red)
```

---

## Performance tips

- **Virtualization:** React Flow supports it for large graphs
- **Lazy edge rendering:** only render visible edges when zoomed out
- **Debounce layout:** re-layout at most every 200ms when nodes stream in
- **Limit node count visible:** collapse "AuditEvent" nodes into aggregated "audit trail" badge
- **CSS transform:** prefer GPU-accelerated properties for smooth 60fps

## Demo polish

- **Initial entry:** fade in entire graph over 500ms (no jarring pop-in)
- **Processing:** simulated 30s timeline shows nodes appearing one by one — **see the second-by-second choreography table in [screen-catalog.md §Agent Trace Viewer Live build choreography](./screen-catalog.md#live-build-choreography-t0--t30s)**
- **Zoom on specific agents:** animate camera pan to highlight agent doing work
- **Color coding:** agent colors distinct enough to be read at a glance
- **Minimap:** always visible, shows your position in larger graph

## Polish rules — "feels professional" vs "feels like student project"

> Research finding: the difference between a graph visualization that looks like LangGraph Studio / Dagster and one that looks like a student project comes down to ~8 specific rules. Apply ALL of them.

### Edge routing: orthogonal, never default bezier

```tsx
// RIGHT — orthogonal routing, reads as hierarchy
<ReactFlow
  defaultEdgeOptions={{
    type: 'smoothstep',
    pathOptions: { borderRadius: 8 },
  }}
/>

// WRONG — default bezier, reads as "flowy" / organic
<ReactFlow /> // default is bezier
```

Bezier edges look organic but fight hierarchy. Workflow graphs are directional; use `smoothstep` with `borderRadius: 8` for the GovFlow default. Reserve bezier for entity-relationship graphs only (not applicable to GovFlow).

### Node padding ≥ 12px inner

```tsx
// node CSS
.agent-step-node {
  padding: 12px 16px;  /* --space-3 vertical, --space-4 horizontal */
  min-width: 240px;
  max-width: 280px;
}
```

Cramped nodes read as prototype. 12px is minimum; 16px better when node has a title + metadata row.

### Node borders: single 1px, no heavy shadows

```css
.agent-step-node {
  border: 1px solid var(--color-border-default);
  box-shadow: var(--shadow-subtle);  /* 0 1px 2px oklch(0 0 0 / 0.04) — barely there */
  /* NEVER: shadow-raised or above on graph nodes */
}
```

Heavy drop shadows (`shadow-md`, `shadow-lg`, `shadow-xl`) are the #1 "student project" tell in graph UIs. Linear, Dagster, LangGraph Studio all use 1px borders with minimal shadows. Borders carry the hierarchy.

### Consistent node width — let dagre lay out, don't content-size

```tsx
nodes.forEach((n) => dagreGraph.setNode(n.id, {
  width: 240,   // fixed — don't compute from content
  height: 64,
}));
```

Content-sizing nodes creates visual chaos where some nodes are 100px wide and others are 400px. Dagre (or any hierarchical layout) expects consistent widths to compute spacing. Fix at 240-280px for case nodes, 160-200px for small nodes (entities, citations), clip text with ellipsis.

### Status via 4px colored left-border strip, not background tint

```css
.agent-step-node[data-status="success"] {
  border-left: 4px solid var(--color-status-success-solid);
}
.agent-step-node[data-status="error"] {
  border-left: 4px solid var(--color-status-danger-solid);
}
.agent-step-node[data-status="running"] {
  border-left: 4px solid var(--color-status-info-solid);
  animation: pulse 2s linear infinite;
}
```

Tinting the whole background ruins text contrast. Dagster and Linear both use the left-strip pattern — status is visible at a glance without fighting the body text. Keep the node body at `--color-surface-card`.

### Neutral edge color (not accent)

```css
.react-flow__edge-path {
  stroke: var(--color-border-strong);  /* OKLCH L≈0.7 */
  stroke-width: 1.5;
}
```

Accent-colored edges everywhere = **Christmas-tree syndrome**. The eye stops being able to read the topology. Use a single neutral color for 95% of edges; reserve accent colors for semantically special edges (e.g. `HAS_GAP` amber, `SUPERSEDED_BY` red dashed, `CITES` purple). When in doubt, neutral.

### Never force-directed for workflow/case graphs

Use `dagre` (TB or LR) or `elkjs` (better for large graphs with many crossings). Force-directed layouts (cola, d3-force) are for **relationship graphs** (social networks, entity graphs) — they show topology. Workflow graphs have direction (input → processing → output); force-directed destroys that direction.

**Exception:** the KG Explorer screen (knowledge graph) uses Cola force-directed by default because it IS a relationship graph (laws, articles, TTHCs). Workflow graphs (Agent Trace Viewer) must use hierarchical layout.

### Labels on nodes, not edges

```tsx
// RIGHT — label is the node itself
<CaseNode>Case C-20260412-0001</CaseNode>

// Edge has no label (or at most a small pill at midpoint for critical info)
<edge type="smoothstep" />

// WRONG — floating string on edge
<edge type="smoothstep" label="HAS_GAP" /> // looks like a floating string
```

Floating edge labels clutter fast. If you absolutely need an edge label, render as a small pill at the edge midpoint with background fill matching the canvas — not as a free-floating string. Exceptions for hover-only tooltips (always OK).

### Restyle React Flow's default Controls + MiniMap

React Flow's default `<Controls>` and `<MiniMap>` components look like 2018 — they'll tank the professional feel. Restyle to match our tokens:

```tsx
<Controls
  style={{
    background: 'var(--color-surface-elevated)',
    border: '1px solid var(--color-border-default)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--shadow-popover)',
    backdropFilter: 'blur(12px)',
  }}
  showInteractive={false}
/>

<MiniMap
  style={{
    background: 'var(--color-surface-card)',
    border: '1px solid var(--color-border-default)',
    borderRadius: 'var(--radius-lg)',
  }}
  maskColor="oklch(0 0 0 / 0.6)"
  nodeColor={(node) => nodeColorMap[node.type]}
/>
```

Frosted-glass background (`backdropFilter: 'blur(12px)'`) on Controls + consistent radius/border match makes them feel native to the GovFlow brand instead of bolted-on.

### Summary — the "pro" checklist

Before shipping the Agent Trace Viewer, verify:
- [ ] All edges use `smoothstep` (orthogonal) — no bezier
- [ ] Node padding ≥ 12px inner
- [ ] Single 1px border, `--shadow-subtle` max
- [ ] Fixed node width (240-280px for case nodes)
- [ ] Status via left-border strip, not bg tint
- [ ] Edges neutral by default, accent only for semantic reasons
- [ ] Dagre TB layout (never force-directed for workflows)
- [ ] Labels on nodes, edges are silent
- [ ] Controls + MiniMap restyled with tokens
- [ ] Classification banner sticky top/bottom if case > Unclassified
- [ ] No more than 3 distinct colors visible at once (neutral + 1 accent + 1 status)

If all 11 boxes check, the graph will read as professional. Miss 2+, it will read as prototype.

## Testing

Test with:
- 10 nodes (small case)
- 100 nodes (typical case with audit trail)
- 500 nodes (complex case with multiple consults)
- 1,000 nodes (stress test — ensure framerate > 30fps)

All animations should feel smooth on demo laptop (16GB RAM, M-class Mac or high-end Intel).

## Accessibility

### Keyboard navigation
- **Tab / Shift+Tab** — move focus between nodes in DOM order (top-to-bottom, left-to-right)
- **Enter** on focused node — open detail panel (same as click)
- **Space** on focused node — toggle neighbors expand (KG Explorer)
- **Arrow keys** — pan viewport
- **+** / **-** — zoom in/out
- **F** — fit to screen
- **Esc** — deselect / close detail panel

### Screen reader: ARIA label templates

Every graph node MUST have a descriptive `aria-label` so a screen reader narrates meaningful information instead of "node 42". Templates:

```tsx
// Case node
<CaseNode
  data={{ caseId: "C-20260412-0001", tthc: "Cấp phép XD" }}
  aria-label="Case C-20260412-0001, Cấp phép xây dựng, classification Confidential, compliance 80%"
  role="treeitem"
  aria-expanded={hasChildren}
/>

// Agent step node
<AgentStepNode
  data={{ agent: "Compliance", tool: "case.find_missing_components", status: "success", latency: 342 }}
  aria-label="Compliance agent step, tool case.find_missing_components, status success, 342 milliseconds"
  role="treeitem"
/>

// Gap node (important — this is a state judges care about)
<GapNode
  data={{ description: "Thiếu Văn bản thẩm duyệt PCCC", severity: "blocker", citation: "NĐ 136/2020 Điều 13.2.b" }}
  aria-label="Gap blocker, missing Văn bản thẩm duyệt PCCC, citation NĐ 136 slash 2020 article 13 clause 2 point b"
  role="treeitem"
  aria-describedby="gap-detail-${id}"
/>

// Citation node
<CitationNode
  data={{ articleNumber: "Điều 13", lawCode: "NĐ 136/2020" }}
  aria-label="Citation to NĐ 136 slash 2020, Điều 13"
  role="treeitem"
/>

// Document node
<DocumentNode
  data={{ filename: "gcn_qsdd.jpg", label: "Giấy chứng nhận quyền sử dụng đất" }}
  aria-label="Document: Giấy chứng nhận quyền sử dụng đất, file gcn_qsdd.jpg"
  role="treeitem"
/>

// ExtractedEntity node
<EntityNode
  data={{ type: "diện tích", value: "500m²" }}
  aria-label="Entity: diện tích, value 500 mét vuông"
  role="treeitem"
/>

// Classification node
<ClassificationNode
  data={{ level: "confidential", reason: "near military zone" }}
  aria-label="Classification: Confidential, reason near military zone"
  role="treeitem"
/>
```

**Rule:** always read special characters as words (`500m²` → "500 mét vuông", `NĐ 136/2020` → "NĐ 136 slash 2020"). Vietnamese screen readers (NVDA + eSpeak VN voice) handle Unicode fine but punctuation is better spoken.

### Live region for new nodes

Wrap the graph canvas in an `aria-live="polite"` container so screen readers announce new events:

```tsx
<div role="region" aria-label="Agent trace graph" aria-live="polite">
  <span className="sr-only" id="graph-announcer">{lastAnnouncement}</span>
  <ReactFlow ... />
</div>
```

When a new node arrives via WS, set `lastAnnouncement` to the appropriate string:

```tsx
// gap_found event
setLastAnnouncement("Gap phát hiện: Thiếu Văn bản thẩm duyệt PCCC. Citation: Nghị định 136/2020 Điều 13.");

// agent_step_end
setLastAnnouncement(`${agent} agent hoàn thành, ${latency} milliseconds`);
```

Don't spam the live region — throttle to 1 announcement per 500ms, prefer the highest-priority event in a batch (gap > step_end > graph_update).

### Focus management

- When detail panel opens (click node), focus moves to the panel's first focusable element
- When detail panel closes (Esc or outside click), focus returns to the node
- When a new node arrives during trace, focus does NOT auto-move (breaks user flow) — announcement is sufficient
- Tab order follows DOM order, not graph topology — users can explore systematically

### High contrast mode

Alternative color palette at `.high-contrast` scope — all status colors use step 12 (max saturation) and all borders use 2px width instead of 1px. Triggered by `@media (prefers-contrast: more)` and by user settings toggle.

### Reduced motion

Per [design-tokens.md §4 Reduced motion](./design-tokens.md#reduced-motion--legal-requirement):
- Disable edge `stroke-dashoffset` animation — edges appear instantly
- Disable node entry scale — nodes fade in only (opacity 0→1, 150ms)
- Disable camera auto-pan — viewport stays fixed, user scrolls manually
- Counter animations jump to final value
- Pulse animations disabled entirely
