You are building GovFlow's Next.js 15 frontend. Follow docs/implementation/16-frontend-setup.md and docs/implementation/17-frontend-screens.md as detailed guides.

Task: $ARGUMENTS (screen name: citizen-portal, intake, agent-trace, compliance, inbox, document-viewer, dashboard, security-console, or "all" for everything)

## Design System

Before building any screen, read:
- docs/04-ux/design-tokens.md — OKLCH colors, semantic tokens, motion scale
- docs/04-ux/design-system.md — Component conventions
- docs/04-ux/graph-visualization.md — React Flow rules

### Token Discipline
- NEVER use raw hex. Use semantic tokens: --bg-surface, --text-primary, --border-subtle, --accent-*
- Classification colors: emerald (Unclassified), amber (Confidential), orange (Secret), red (Top Secret)
- Fonts: Inter (UI), Source Serif 4 (legal text), JetBrains Mono (code/Gremlin)

### Component States
Every component MUST implement: empty, loading, error, hover, focus, disabled

### Graph Visualization Rules (React Flow)
- Orthogonal edges (smoothstep), NOT bezier
- Node padding >= 12px, single 1px border
- Fixed node width, status via left-border color strip
- Dagre TB layout (hierarchical), NEVER force-directed for workflows
- Node labels ON nodes, not floating edge labels

## State Management
- **TanStack Query** for server state (API data)
- **Zustand** for WebSocket real-time state (agent trace, notifications) and UI state (sidebar, modals, dark mode)

## WebSocket Integration
```typescript
// src/lib/ws.ts — Connection manager
// src/stores/agent-trace.ts — Live agent steps + graph nodes/edges
// src/stores/notifications.ts — Notification queue
// src/hooks/useWSTopic.ts — Subscribe to topics (case:{id}, user:{id}:notifications)
```

## 8 Screens

1. **Citizen Portal** `(public)/` — Hero search, 5 TTHC cards, case tracking timeline, submit wizard (4 steps: select TTHC -> upload docs -> review -> confirm)
2. **Intake UI** `(internal)/intake/` — Drag-drop upload zone, OCR preview, case creation form, trigger pipeline button
3. **Agent Trace Viewer** `(internal)/trace/[case_id]/` — React Flow graph growing in real-time via WS. Custom nodes: Case (blue), Task (gray), Document (indigo), Gap (amber), Citation (purple), Decision (green/red). AgentStep sidebar.
4. **Compliance Workspace** `(internal)/compliance/[case_id]/` — Split view: docs left, gaps+citations right. GapCard with severity badge + fix suggestion.
5. **Department Inbox** `(internal)/inbox/` — Kanban 5 columns: Tiep nhan, Dang xu ly, Cho y kien, Da quyet dinh, Tra ket qua. SLA countdown badges.
6. **Document Viewer** `(internal)/documents/[id]/` — PDF viewer (react-pdf) left, entity overlay, summary tabs right. Property mask blur animation (RedactedField component).
7. **Leadership Dashboard** `(internal)/dashboard/` — KPI cards, SLA heatmap, bar chart (cases by TTHC), Hologres AI Functions brief card.
8. **Security Console** `(internal)/security/` — Live audit log (WS-fed), 3-scene demo controls, classification distribution chart, denial heatmap.

## Key Components
- CaseCard, TimelineStep, GapCard, CitationBadge, ClassificationBadge, SLABadge
- AnimatedCounter (Framer Motion), RedactedField (blur-to-clear on elevation)
- Command palette (Cmd+K via shadcn Command component)

## Motion (Framer Motion)
- 150ms micro-interactions, 250ms default transitions, 400ms emphasis
- ease-out-quart easing
- Key animations: graph node appearance (scale+fade), edge draw, permission denied shake, mask dissolve, SLA countdown pulse

## Accessibility
- WCAG AA, keyboard navigation (Tab/Enter/Space/Arrows/Cmd+K)
- ARIA labels per component type
- High contrast mode support
- Reduced motion respect

## Verification
```bash
npm run build  # Zero errors
npm run dev    # All screens render at localhost:3000
# Dark + light mode both work
# Graph viz shows nodes in Agent Trace Viewer
# WebSocket connects and receives events
# Responsive at 1440 and 1920
# Citizen Portal works on mobile viewport
```