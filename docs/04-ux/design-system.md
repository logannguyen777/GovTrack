# Design System — Component & Style Reference

Standard reference cho mọi UI implementation. Mở rộng [`../02-solution/design-theme.md`](../02-solution/design-theme.md) với detail components.

**Token values live in [`design-tokens.md`](./design-tokens.md).** This file describes *components* and *patterns*; it references tokens by name (`--color-action-solid`, `--duration-medium-2`) but never defines their values. Separating tokens from components allows the frontend team to copy `design-tokens.md` directly into `frontend/styles/tokens.css` without scrolling past component specs.

## Tech stack

- **Next.js 15** (App Router, Server Components)
- **TypeScript**
- **Tailwind CSS** v4 (CSS-first `@theme`)
- **shadcn/ui** (Radix primitives + Tailwind)
- **Framer Motion** v12 (animations)
- **React Flow** (XyFlow) + **Cytoscape.js** (graph viz)
- **Tremor** + **Recharts** (dashboards, KPI blocks)
- **TanStack Query** (server state)
- **Zustand** (client state minimal)
- **react-pdf** (Document Viewer)
- **Tiptap** (rich text editor — Consult Inbox opinion composer)
- **Inter** + **Source Serif 4** + **JetBrains Mono** (fonts)

## Token system (shortref)

Tokens defined in [`design-tokens.md`](./design-tokens.md) using a 3-tier model:

1. **Tier 1 — Primitives:** OKLCH color ramps (`--gov-accent-1..12`, `--gov-neutral-1..12`, etc using [Radix 12-step semantic scale](https://www.radix-ui.com/themes/docs/theme/color)), type scale, motion duration/easing, spacing, radius. **Components never reference these directly.**
2. **Tier 2 — Semantic:** role-based tokens consumed by components (`--color-surface-card`, `--color-text-primary`, `--color-action-solid`, `--duration-medium-2`, `--ease-emphasized`). Dark/light mode swap happens at this tier only.
3. **Tier 3 — Component:** optional per-component overrides when a component needs divergence from semantic defaults.

**Rules enforced by build lint:**
- No raw hex in `app/` or `components/` outside `styles/tokens/`
- Every `--color-*` semantic has a paired `-fg`/`-text` token with AA contrast (≥ 4.5:1)
- No inline `transition: { duration: 0.XXX }` — must reference `motionTokens` from `lib/motion.ts`

See [design-tokens.md](./design-tokens.md) for full definitions, OKLCH rationale, Vietnamese typography hardening, and Material 3 motion scale.

> **Old hex-based token block removed.** Previous versions of this file duplicated token values from `design-tokens.md`. All tokens now live exclusively in [design-tokens.md](./design-tokens.md) to prevent drift. Old palette values like `brand.500 = #2563EB` are replaced by `--color-action-solid` backed by OKLCH primitives. Do not add hex values back to this file.

## Core components (shadcn/ui customized)

### Button

```tsx
<Button variant="default">Primary</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="destructive">Delete</Button>
<Button variant="destructive-confirm">Delete (requires confirm)</Button>  // custom
<Button variant="ghost">Ghost</Button>
<Button variant="outline">Outline</Button>
```

Custom `destructive-confirm` variant: 2-click confirmation for high-stakes actions (publish VB, delete case).

### Badge

```tsx
<Badge variant="default">Default</Badge>
<Badge variant="classification" level="unclassified">Unclassified</Badge>
<Badge variant="classification" level="confidential">Confidential</Badge>
<Badge variant="classification" level="secret">Secret</Badge>
<Badge variant="classification" level="topsecret">Top Secret</Badge>
<Badge variant="sla" status="on_track">SLA 7d</Badge>
<Badge variant="sla" status="at_risk">SLA 2d</Badge>
<Badge variant="sla" status="overdue">Overdue</Badge>
```

### Card — Case variant

```tsx
<CaseCard
  caseId="C-20260412-0001"
  title="Cấp phép xây dựng nhà xưởng"
  applicant="Nguyễn Văn M***"
  tthc="Cấp giấy phép xây dựng"
  complianceScore={94}
  slaStatus="on_track"
  slaRemaining="7 ngày"
  classification="confidential"
  summary="Hồ sơ đủ 6/6 thành phần. Pháp chế + Quy hoạch đã duyệt. Đề xuất approve."
  onClick={() => router.push(`/cases/${caseId}`)}
/>
```

Layout:
```
┌────────────────────────────────────────┐
│ [Confidential badge]      [SLA: 7d]   │
│                                         │
│ Cấp phép xây dựng nhà xưởng           │
│ Nguyễn Văn M*** • C-20260412-0001      │
│                                         │
│ Hồ sơ đủ 6/6 thành phần. Pháp chế +   │
│ Quy hoạch đã duyệt. Đề xuất approve.  │
│                                         │
│ Compliance ████████████▒▒ 94%          │
└────────────────────────────────────────┘
```

### AgentStep component (for Agent Trace Viewer)

```tsx
<AgentStep
  agent="Compliance"
  tool="case.find_missing_components"
  status="success"
  latency={342}
  tokensIn={1240}
  tokensOut={86}
  inputSummary="case_id: C-001"
  outputSummary="1 missing: Văn bản thẩm duyệt PCCC"
  timestamp={new Date()}
  expandable
  onExpand={() => showAuditDetail()}
/>
```

Layout:
```
[agent icon] Compliance · case.find_missing_components
             ✓ 342ms · 1,240 → 86 tokens
             ▸ Expand reasoning
```

### Graph visualization wrapper

```tsx
<CaseGraph
  caseId={caseId}
  layout="force"  // or "hierarchical"
  highlightAgentSteps
  onNodeClick={(node) => {...}}
/>
```

Uses React Flow. Nodes colored by label (Case=blue, Document=gray, Gap=amber, Citation=purple).

### ConnectionLostBanner

```tsx
<ConnectionLostBanner
  severity="warning"  // or "critical" for Security Console
  reconnectIn={8}     // seconds until next auto-retry
  onRetry={() => ws.reconnect()}
/>
```

**Props:**
- `severity: "warning" | "critical"` — yellow (default) or red (Security Console, where audit gaps are unacceptable)
- `reconnectIn: number` — countdown to next auto-retry attempt
- `onRetry?: () => void` — manual retry button handler

**Layout:** full-width sticky banner at top of page (below app header, above content), height 40px. Shows spinner + "Kết nối mất. Thử lại sau {reconnectIn}s" + manual [Thử lại] button. Respects sticky ClassificationBanner z-index (banner appears BELOW classification, never obscuring).

**States:**
- `connecting` — spinner + countdown
- `reconnected` — brief success flash green 800ms then unmount
- `failed-permanently` — red with [Liên hệ IT] button after 5 failed retries

**Usage:** wrap any screen that subscribes to WS topics. Automatically shown when `useWebSocket()` state is `disconnected`.

### ConsultSlidePanel

```tsx
<ConsultSlidePanel
  caseId="C-20260412-0001"
  open={isOpen}
  onClose={() => setIsOpen(false)}
  preAnalyzedContext={ctx}  // from Consult Agent
  legalRefs={refs}           // from LegalLookup
  attachedDocs={docs}
  onSubmit={async (payload) => {...}}
/>
```

**Props:**
- `caseId: string` — the case being consulted on
- `open: boolean` — controlled open state
- `onClose: () => void`
- `preAnalyzedContext: ConsultContext` — `{ summary, question, suggestedRecipient }` pre-filled by Consult Agent
- `legalRefs: Citation[]` — pre-checked from LegalLookup
- `attachedDocs: Document[]` — relevance-classified by DocAnalyzer
- `onSubmit: (payload: ConsultRequestPayload) => Promise<void>`

**States:**
- `idle` — editable form
- `submitting` — form disabled, submit button loading 600ms min
- `submitted` — slide out + toast
- `error` — form re-enabled, error banner

**Width:** 480px, slide-in from right 300ms `--ease-emphasized`. Backdrop dims `oklch(0 0 0 / 0.4)`. Dismissible by Esc, outside click, or X button.

Full layout in [screen-catalog.md §4 Consult dialog slide-panel spec](./screen-catalog.md#consult-dialog-slide-panel-spec).

### ConsultRequestCard

```tsx
<ConsultRequestCard
  request={consultRequest}
  active={activeId === consultRequest.id}
  onClick={() => setActive(consultRequest.id)}
/>
```

**Props:**
- `request: ConsultRequest` — full vertex data `{ id, caseId, tthcName, applicantName, priority, slaRemaining, classification, questionExcerpt, status, createdAt }`
- `active: boolean` — whether this card is the currently-selected one in the list (shows left-border accent stripe)
- `onClick: () => void`

**Variants (via `request.status`):**
- `pending` — unread dot + full opacity
- `reading` — hovered or current (shown in inbox left sidebar)
- `replied` — muted opacity 0.6, ✓ indicator

**States:** focus, hover, active-selected, replied, urgent (red priority badge)

**Height:** 88px fixed. Width: 320px (matching Consult Inbox left sidebar).

### OpinionComposer

```tsx
<OpinionComposer
  initialValue={draft}   // localStorage-backed
  citationRefs={refs}     // for [Cite] button insert
  onChange={setDraft}
  onSubmit={async (html, decision) => {...}}
  submitting={isSubmitting}
/>
```

**Props:**
- `initialValue: string` — HTML string (Tiptap output), from localStorage draft or empty
- `citationRefs: Citation[]` — available citations to insert via toolbar button
- `onChange: (html: string) => void` — fires on every keystroke (debounced 500ms), use for autosave
- `onSubmit: (html: string, decision: "approve" | "deny") => Promise<void>`
- `submitting: boolean`

**Features:**
- Tiptap editor with StarterKit + Citation extension (custom)
- Toolbar: bold, italic, bulleted list, blockquote, [Cite NĐ...] insert button (dropdown of refs)
- Minimum height 200px, expands as user types (max 600px then scrolls)
- Character count bottom-right (soft limit 2000, hard limit 5000)
- Autosave indicator ("Đã lưu nháp 2s trước")
- Submit button with decision radio inline (Approve / Deny)
- Keyboard: `⌘+B` bold, `⌘+I` italic, `⌘+Enter` submit

**Font:** Inter, `--text-body-14` with `--lh-vn-body: 1.65`

### KGGraph

```tsx
<KGGraph
  initialNodes={seedNodes}   // 50 most-cited articles
  initialEdges={seedEdges}
  rootId={articleId}          // optional zoom target
  layout="cola"               // or "dagre-tb"
  classificationFilter={userClearance}
  onNodeClick={(node) => showDetailPanel(node)}
  onNodeExpand={async (id) => fetchNeighbors(id)}
/>
```

**Props:**
- `initialNodes: GraphNode[]` — seed graph from SSR
- `initialEdges: GraphEdge[]`
- `rootId?: string` — if provided, zoom to this node on mount
- `layout: "cola" | "dagre-tb" | "dagre-lr"` — see [graph-visualization.md §Cytoscape KG Explorer](./graph-visualization.md#cytoscapejs--kg-explorer)
- `classificationFilter: ClassificationLevel` — nodes at higher levels render as ghost placeholders
- `onNodeClick: (node) => void`
- `onNodeExpand: (id: string) => Promise<{ nodes, edges }>` — lazy load 1-hop neighbors

**Internal state:** maintains Cytoscape instance, handles layout re-runs on new nodes, debounces layout to 200ms.

**Performance:** initial load ≤200ms render target for 50 nodes; >500 nodes triggers clustering by decree.

**Accessibility:** ARIA labels on nodes — template in [graph-visualization.md §Accessibility](./graph-visualization.md#accessibility).

### ElevationModal

```tsx
<ElevationModal
  currentClearance="unclassified"
  targetClearance="confidential"
  resourceName="C-20260412-0001"
  onSubmit={async (reason, authToken) => {...}}
  onCancel={() => {...}}
/>
```

**Props:**
- `currentClearance: ClearanceLevel`
- `targetClearance: ClearanceLevel`
- `resourceName: string` — what the user is trying to access
- `onSubmit: (reason: string, authToken: string) => Promise<void>`
- `onCancel: () => void`

**Required fields:**
- Reason textarea (bắt buộc, min 10 chars, audit-logged before grant takes effect)
- OTP or passkey (step-up auth, backend-dependent)

**Flow:**
1. User types reason
2. User enters OTP
3. Click "Xác nhận"
4. **Audit entry written FIRST** (compliance requirement — audit before grant)
5. If audit succeeds, grant issued, modal closes, `ClearanceCountdown` chip appears in header
6. If audit fails, grant rejected, error banner

**NOT allowed:**
- ❌ Slider to pick clearance level — implies "dial" (wrong mental model)
- ❌ Persistent elevation (grants are time-bounded, max 1 hour)
- ❌ Skipping the reason field (mandatory for audit)

### ClearanceCountdown

```tsx
<ClearanceCountdown
  level="confidential"
  expiresAt={timestamp}
  onExpire={() => ...}
/>
```

**Props:**
- `level: ClearanceLevel` — current elevated level
- `expiresAt: Date | number` — Unix ms or Date
- `onExpire: () => void` — callback when countdown hits 0

**Layout:** small pill in app header (top-right, next to user avatar). Non-dismissible. Shows: `⏳ CONFIDENTIAL (55 min)`. Updates every 1s.

**Visual states:**
- `> 10 min remaining` — blue/neutral
- `5-10 min remaining` — amber (warning)
- `< 5 min remaining` — red + subtle pulse (urgent)
- `expired` — auto-unmount after firing `onExpire`

**On expire:** fires callback so parent can re-mask all Confidential content + show toast "Clearance đã hết hạn".

### Permission denied UI

```tsx
<PermissionDenied
  tier="SDK_Guard"
  attemptedAction="read Applicant.national_id"
  agent="Summarizer"
  reason="Property 'national_id' is in mask list for agent 'Summarizer'"
  auditId="audit:12345"
  onViewAudit={() => {...}}
/>
```

Red border (`--color-status-danger-border`), shake animation on mount (200ms), collapsible details. Classifies into Tier 1 (SDK Guard), Tier 2 (GDB RBAC), or Tier 3 (Property Mask) — see [Security Console permission demo harness](./screen-catalog.md#permission-demo-harness) for end-to-end demo spec.

### Classification banner component

`<ClassificationBanner>` is **sticky top + bottom**, full-width, solid fill, uppercase text, centered. It reads the current document's highest classification from React context and renders `position: sticky; z-index: 9999` at both the top and bottom of the viewport so scrolled content is always bounded by the classification.

```tsx
<ClassificationBanner level="confidential" />
// renders:
// [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ CONFIDENTIAL ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓]
// ... page content ...
// [▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ CONFIDENTIAL ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓]
```

**Why top AND bottom:** DoD/NATO marking convention. The banner must appear both above and below so printed or screen-capped sections carry the classification with them. [DoDM 5200.01 Vol. 2](https://www.esd.whs.mil/portals/54/Documents/DD/issuances/dodm/520001m_vol2.pdf) requires this.

**Color:** driven by semantic tokens `--color-class-{level}-banner` and `--color-class-{level}-text` — see [design-tokens.md §2.3](./design-tokens.md#semantic-tokens-tier-2). Defaults:
- `unclassified` → emerald (`--gov-class-unclass-9`)
- `confidential` → blue (`--gov-class-confid-9`)
- `secret` → orange (`--gov-class-secret-9`)
- `topsecret` → red (`--gov-class-topsec-9`)

**Rule: never render classification via a colored page border.** Users habituate to borders and stop seeing them. The sticky banner with full-width fill is annoying on purpose — annoyance is the feature.

### Portion marks

For paragraph-level classification within a mixed-level document:

```tsx
<p>
  <PortionMark level="confidential">(M)</PortionMark> Công trình có vị trí trong khu vực hạn chế...
</p>
```

Small pill prefix on each portion. Vietnamese equivalents: `(M)` = MẬT, `(TM)` = TỐI MẬT, `(TTM)` = TUYỆT MẬT, no mark = Unclassified.

### Redaction — solid bar (NOT blur)

```tsx
<Redacted reason="PII" level="sensitive">079****1234</Redacted>
// renders: [▓▓▓▓▓▓▓▓▓▓▓▓] — solid rounded-rect bar, line-height sized
```

**Four redaction options ranked by security:**

1. **Solid bar** (`--color-redact-bar` = `--gov-neutral-1`, rounded 4px, sized to parent line-height) — **DEFAULT CHOICE**. Unrecoverable, readable in context.
2. **Server-side `[REDACTED]` text substitution** — when clearance is fully absent (the data never reaches the client at all).
3. **Pixelation** — *insecure* (recoverable via deconvolution). Do NOT use.
4. **Blur** — *least secure*, recoverable, reads as consumer soft-focus. Do NOT use. Previous versions of this spec called for `filter: blur(8px→0)` mask dissolve — **that is deprecated** because blur is cryptographically recoverable and inappropriate for gov-serious tone.

**Elevation reveal animation** (Scene C of demo storyboard):

```tsx
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.25, ease: [0.3, 0, 0, 1] }}  // --duration-medium-1 + --ease-emphasized
>
  {revealedContent}  // becomes visible underneath the (now-removed) solid bar
</motion.div>
```

When clearance is granted:
1. Audit log is written BEFORE UI reveal (compliance requirement)
2. Solid bar unmounts (no blur unblur)
3. Revealed content crossfades in (opacity 0 → 1, 250ms)
4. Classification banner above transitions to the higher level (fade 200ms)

**Elevation granting UX:** modal with step-up auth, NOT a slider or stepper. Slider implies "dial your clearance" (wrong mental model). Modal implies "request higher role for a bounded task":

```
┌──────────────────────────────────────┐
│ Nâng clearance                      × │
├──────────────────────────────────────┤
│                                       │
│ Bạn đang xem: C-20260412-0001         │
│ Classification: CONFIDENTIAL          │
│                                       │
│ Clearance hiện tại: UNCLASSIFIED      │
│ Cần nâng lên: CONFIDENTIAL            │
│                                       │
│ Lý do (bắt buộc, ghi audit):          │
│ [_____________________________]       │
│                                       │
│ Xác thực bổ sung:                     │
│ [Mã OTP gửi điện thoại: ______]       │
│                                       │
│ Clearance sẽ hết hạn sau: 1 giờ       │
│                                       │
│              [Hủy]  [Xác nhận]       │
└──────────────────────────────────────┘
```

After grant:
- Audit entry written (before UI changes)
- Countdown badge appears in app header: `⏳ CONFIDENTIAL (55 min)` — non-dismissible, non-obscurable
- At expiry, all Confidential content re-masks with the same solid-bar pattern, user sees toast "Clearance đã hết hạn"

References: [DCSA CUI Marking Handbook](https://www.dcsa.mil/Portals/91/Documents/CTP/CUI/DOD-CUI_Marking_Handbook-DOD_(2020).pdf), [Delinea — Privilege Elevation Workflow](https://docs.delinea.com/online-help/cloud-suite/cloud-clients/managing/privilege-elevation/privilege-elevation-workflow.htm).

## Layout templates

### Citizen Portal
```
┌──────────────────────────────────────────┐
│  [logo] GovFlow    [login via VNeID]    │  <- large header, light theme
├──────────────────────────────────────────┤
│                                           │
│         Hồ sơ của bạn                    │
│         [Big search bar by mã hồ sơ]     │
│                                           │
│         Hoặc:                             │
│         [Nộp hồ sơ mới] [Tra cứu TTHC]  │
│                                           │
├──────────────────────────────────────────┤
│  Các TTHC phổ biến:                      │
│  [CPXD] [GCN] [ĐKKD] [LLTP] [GPMT]      │
│                                           │
└──────────────────────────────────────────┘
```

Very simple, high density of whitespace, big touch targets. Mobile-responsive.

### Internal Workspace (Intake, Compliance, Dashboard, Security)

```
┌─────┬────────────────────────────────────┐
│ nav │ ⌘K search    [user avatar] [bell] │
│     ├────────────────────────────────────┤
│  •  │                                     │
│  •  │  [page content area]               │
│  •  │                                     │
│  •  │                                     │
│  •  │                                     │
│  •  │                                     │
└─────┴────────────────────────────────────┘
```

Dark theme default. Sidebar collapsible. Keyboard-first.

## Animation principles

### Micro-interactions

- **Hover states:** 150ms, subtle brightness/elevation change
- **Focus states:** ring with brand color, 2px offset
- **Click feedback:** 100ms scale(0.98) then back

### Entry animations

- **Fade-in:** 250ms, no slide (too distracting)
- **Slide-up:** 300ms for modals, 400ms for side panels
- **Stagger:** 50ms delay per item when lists appear

### Agent trace animation

- New AgentStep node appears: `fade-in` + `scale(0.9 → 1.0)` + subtle glow
- Edge draws: stroke-dashoffset animation, 400ms
- When all steps done, subtle pulse on whole graph

### Permission denied

- **Shake:** `x:[-4, 4, -4, 4, 0]` in 200ms
- **Red flash:** border + bg color pulse from red-500 → red-50 in 400ms
- **Audit log slide:** side panel slides in from right in 300ms

### Mask dissolve (Scene C demo) — DEPRECATED in favor of solid-bar crossfade

> **This blur-based approach is no longer used.** Blur is cryptographically recoverable and reads as consumer soft-focus. See [Redaction — solid bar](#redaction--solid-bar-not-blur) for the current pattern: solid bar unmount + revealed content opacity crossfade.

The new pattern:

```tsx
{clearanceLevel >= 'confidential' ? (
  <motion.span
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.25, ease: [0.3, 0, 0, 1] }}
  >
    {actualValue}
  </motion.span>
) : (
  <Redacted reason="clearance_insufficient">{placeholder}</Redacted>
)}
```

### Motion intent mapping

> Animations should have narrative intent, not just aesthetic polish. This table maps each animation pattern to what it *communicates* — use this when deciding which pattern to apply, and when NOT to.

| Animation | Token ref | Narrative intent | When to use | When NOT to use |
|---|---|---|---|---|
| **Glow pulse** (scale 1 → 1.08 → 1) | `--duration-long-4` + `--ease-emphasized` | "System just did something successfully" | Agent step complete, graph edge established, draft generated | Background state changes, loading |
| **Red shake** (x: [-4, 4, -4, 4, 0]) | `--duration-short-4` | "Refusal, with conviction" | Permission denied, invalid publish attempt, WS submit rejected | Form validation errors (use inline error instead) |
| **Amber shake** (x: [-3, 3, -3, 3, 0]) | `--duration-short-4` | "Attention needed, but recoverable" | Gap detected on Intake UI row | Any destructive/irreversible scenario |
| **Solid-bar dissolve** (opacity 0 → 1 on revealed content) | `--duration-medium-1` + `--ease-emphasized` | "Clearance elevated, data revealed" | Classification mask removal after step-up auth | Any consumer/playful reveal — gov tone |
| **Edge draw** (stroke-dashoffset) | `--duration-long-2` + `--ease-standard` | "Causal link being established" | New WS `graph_update` event in Agent Trace Viewer | Re-layout of existing edges (use instant update) |
| **Skeleton shimmer** (linear gradient, 1.5s loop) | `--duration-xl-1` × linear | "Waiting but not stuck" | SSR pending, WS initial fetch, OCR per-file progress | Error state (use static error UI), empty state |
| **Counter animate** (lerp) | `--duration-medium-4` + `--ease-emphasized` | "Accumulating value" | Compliance score 80% → 100%, SLA countdown ticking, Leadership Dashboard KPIs | Static numbers that don't change |
| **Stagger list** (50ms delay per item) | `--duration-medium-1` + `--ease-emphasized` | "Batch arrival of ordered items" | Audit log streaming, agent step timeline, entity chips within a row | Single item, random order, already-present list |
| **Kanban card slide** (translate 300ms) | `--duration-medium-2` + `--ease-emphasized` | "Case moved through workflow" | Router decision moving a card between Kanban columns | Minor position adjustments within a column |
| **Fade-in** (opacity 0 → 1) | `--duration-medium-1` + `--ease-emphasized` | Default new content entry | Card, modal, panel mount, tab content switch | Graph nodes (use glow pulse + scale instead) |
| **Button click feedback** (scale 1 → 0.98 → 1) | `--duration-short-3` | Tactile confirmation | Any interactive button/toggle | Non-interactive elements |

**Principle:** when in doubt, ask "what am I trying to tell the user?" If the answer is "nothing, I just want it to look cool" — don't animate it. Gov-serious brands communicate with motion, they don't decorate with it.

## Icon guidelines

- **Library:** Lucide React
- **Sizes:** 16px (inline text), 20px (buttons), 24px (headers), 32px (feature)
- **Stroke:** 1.5 default
- **Color:** inherit from text color

Custom icons for classification (4 levels) — simple geometric shapes with clear color differentiation.

## Responsive breakpoints

- `sm: 640px`  — mobile (Citizen Portal)
- `md: 768px`  — tablet
- `lg: 1024px` — small laptop
- `xl: 1280px` — standard workspace
- `2xl: 1536px` — large monitor / projector

**Demo target:** `xl:1440` (laptop demo) and `2xl:1920` (projector). Ensure everything looks great at both.

## Dark / light mode

Both built from day 1. Implementation:
- Use `next-themes` for theme switching
- All components use Tailwind's `dark:` prefix
- Citizen Portal defaults to **light** (familiar to public)
- Internal Workspace defaults to **dark** (polished, reduces eye strain)
- User can toggle via command palette or settings

## Accessibility

- **WCAG 2.2 AA** minimum (legal requirement per EU EAA, US DOJ, UK PSBAR, VN TCVN)
- Text contrast ratio ≥ 4.5:1 for body, ≥ 3:1 for large text (enforced by build-time token lint per [design-tokens.md §9](./design-tokens.md#9-verification))
- Focus rings visible on all interactive elements via `:focus-visible` (3px width, non-negotiable)
- Full keyboard navigation (all actions reachable — see [Global keyboard shortcut reference](#global-keyboard-shortcut-reference) below)
- Screen reader: semantic HTML + ARIA labels for dynamic regions — template examples in [graph-visualization.md §Accessibility](./graph-visualization.md#accessibility)
- `prefers-reduced-motion` respected — implementation in [design-tokens.md §4 Reduced motion](./design-tokens.md#reduced-motion--legal-requirement)
- Touch targets ≥ 48×48px on mobile (WCAG AA)
- Focus management: after modal close, focus returns to triggering element; after slide panel close, focus returns to triggering button; after submit, focus goes to next actionable item (e.g. Consult Inbox next card); after error, focus moves to error message element

## Global keyboard shortcut reference

> Single source of truth for every keyboard shortcut in GovFlow. Power users should be able to operate the entire internal workspace without touching the mouse. The ⌘K command palette indexes all shortcuts for discoverability.

### Global (any internal screen)

| Key | Action |
|---|---|
| `⌘K` (Mac) / `Ctrl+K` (Win) | Open command palette (search cases, screens, shortcuts) |
| `⌘/` | Toggle keyboard shortcut overlay |
| `⌘B` | Toggle sidebar collapse |
| `⌘\` | Toggle right detail panel (where applicable) |
| `Esc` | Close modal / slide panel / cancel edit |
| `?` | Open help overlay for current screen |
| `g` then `d` | Go to Dashboard |
| `g` then `i` | Go to Inbox |
| `g` then `c` | Go to Consult Inbox |
| `g` then `k` | Go to KG Explorer |
| `g` then `s` | Go to Security Console |
| `g` then `p` | Go to Profile / Settings |

### List navigation (Inbox, Consult Inbox, Audit Log, Approve Queue)

| Key | Action |
|---|---|
| `j` / `↓` | Next item |
| `k` / `↑` | Previous item |
| `Enter` | Open selected item |
| `x` | Select/toggle (for batch operations) |
| `a` | Approve (where action is allowed) |
| `d` | Deny (where action is allowed) |
| `Space` | Peek preview without opening |

### Forms & editors (Intake UI, Compliance Workspace, Opinion Composer)

| Key | Action |
|---|---|
| `⌘+Enter` | Submit / primary action |
| `⌘S` | Save draft |
| `⌘Z` / `⌘⇧Z` | Undo / redo |
| `⌘B` / `⌘I` | Bold / italic (rich text) |
| `Tab` / `⇧Tab` | Next / previous field |

### Graph (Agent Trace Viewer, KG Explorer)

| Key | Action |
|---|---|
| `F` | Fit to screen |
| `+` / `-` | Zoom in / out |
| `0` | Reset zoom (100%) |
| `/` | Focus search input |
| `1`-`4` | Classification filter presets (KG Explorer) |
| `[` / `]` | Collapse/expand left/right panel |
| `Ctrl+Z` | Undo last expand (graph navigation) |
| `Arrow keys` | Pan viewport |

### Security Console demo harness

| Key | Action |
|---|---|
| `D` then `A` | Run demo Scene A (SDK Guard reject) |
| `D` then `B` | Run demo Scene B (GDB RBAC reject) |
| `D` then `C` | Run demo Scene C (Property mask elevation) |

### Document Viewer

| Key | Action |
|---|---|
| `j` / `k` | Next / previous page |
| `⌘F` | Find in document |
| `e` | Export / download |
| `⌘P` | Print (generates print CSS view) |

### Consult Slide Panel (within Compliance Workspace)

| Key | Action |
|---|---|
| `⌘+Enter` | Send consult |
| `Esc` | Close panel (draft preserved) |

**Discoverability:** every shortcut is indexed in the ⌘K command palette. Typing a screen name or action finds its shortcut; typing `shortcut` shows the full list. On hover of any button with a keyboard shortcut, tooltip shows the shortcut in mono font: `[⌘+Enter]`.

**Conflicts:** `j`/`k` conflicts with common vim navigation expectations — intentional, matches GitHub/Linear conventions. `D+A/B/C` uses held chord to avoid collision with single-key actions.

**Discovery overlay:** pressing `⌘/` shows a floating panel listing all shortcuts for the current screen, dismissible with Esc.

## Form patterns

### Upload

```tsx
<FileUpload
  accept=".pdf,.jpg,.jpeg,.png"
  maxSize={50_000_000}
  multiple
  onUpload={async (files) => {
    // Get presigned URLs, upload in parallel
  }}
/>
```

Features: drag-and-drop, multiple files, progress bar per file, retry on failure, preview thumbnails.

### Confirm dialog

```tsx
<ConfirmDialog
  title="Xác nhận ký và phát hành"
  description="Văn bản sau khi phát hành không thể thu hồi. Hành động này sẽ:"
  consequences={[
    "Gửi thông báo tới công dân",
    "Lưu vào kho lưu trữ nhà nước",
    "Tạo PDF có chữ ký số"
  ]}
  confirmText="Ký và phát hành"
  confirmVariant="destructive-confirm"
  onConfirm={async () => {...}}
/>
```

## Toast notifications

```tsx
toast.success("Hồ sơ đã được tiếp nhận", { description: "Mã: C-20260412-0001" })
toast.warning("SLA sắp hết", { description: "Còn 2 ngày" })
toast.destructive("Access denied", { description: "Clearance insufficient" })
toast.info("Agent đang xử lý...", { description: "Ước tính 30 giây" })
```

## Mandatory states

Every component MUST have:
- [ ] Empty state — when no data
- [ ] Loading state — **skeleton (not spinner)** — see [Error state catalog](#error-state-catalog) + per-screen skeletons in [screen-catalog.md](./screen-catalog.md)
- [ ] Error state — with retry action — see [Error state catalog](#error-state-catalog)
- [ ] Focus state — keyboard navigation (`:focus-visible`, 3px ring via `--focus-ring`)
- [ ] Hover state — for interactive
- [ ] Disabled state — for gated actions (use `--color-action-disabled`, reduce opacity to 0.5, keep focus ring active)

No exceptions. UI debt is not acceptable per Principle #10.

## Error state catalog

> Every error scenario GovFlow UI can hit. Each row names the exact component/toast/banner to render plus the recovery path. Per-screen variations live in the screen-catalog's per-screen "Error states" subsections.

| # | Error | Trigger | UI pattern | Recovery | Screens affected |
|---|---|---|---|---|---|
| 1 | **PDF load failure** | `react-pdf` fetch fails (404, network, CORS) | Placeholder in viewer area: "Không tải được tài liệu gốc. [Thử lại] hoặc [Tải xuống trực tiếp]" — data around PDF (info panel, summaries, audit) still renders | Retry button or direct download link | Document Viewer, Compliance WS |
| 2 | **WS disconnect mid-trace** | WebSocket close mid-session | `<ConnectionLostBanner>` top of page (yellow, except Security Console which is red) + reconnect countdown + **cached graph freezes** (no fake updates) + timeline rows show "paused" chip per-agent. Principle: "animations must not lag reality" ([realtime-interactions.md:147](./realtime-interactions.md#L147)) | Auto-reconnect with exponential backoff; replay missed events from server buffer on reconnect | Agent Trace Viewer, Department Inbox, Leadership Dashboard, Security Console, Consult Inbox |
| 3 | **OCR failure on one file** | DocAnalyzer returns error for a single file | Row turns amber with `⚠ Retry OCR` button + `Manual label ▼` dropdown. Compliance bar recalculates from remaining files. Does NOT block other rows from progressing. | Retry per-file or manually classify | Intake UI |
| 4 | **OCR failure on all files** | Systemic DocAnalyzer fail | Full-page banner "Hệ thống OCR tạm không khả dụng. Tiếp tục thủ công?" + fallback button to manual labeling | Fallback to manual labeling | Intake UI |
| 5 | **API 5xx / timeout** | Backend 500 or no response within 10s | Generic `<ErrorBanner>` with error ID + `[Thử lại]` + "Liên hệ hỗ trợ nếu tiếp tục lỗi" | Retry button, log error with trace ID | All screens |
| 6 | **Permission denied mid-view (auth expired)** | Auth token expired while user was viewing a case | Modal: "Phiên làm việc hết hạn. [Đăng nhập lại]" — case ID preserved for return after re-auth | Re-authenticate and return to same case | Document Viewer, Compliance WS, Consult Inbox |
| 7 | **Graph layout fails (>1000 nodes)** | React Flow dagre runs out of time on large case | Fallback to grid layout + warning banner "Graph too large, using simple layout". Cluster audit events into single badge. | Cluster by agent type or agent-level rollup | Agent Trace Viewer, KG Explorer |
| 8 | **Classification fetch fail** | Clearance check API down | All nodes at classification > Unclassified ghost out (not visible content). Top banner explains + retry button. | Retry fetch | KG Explorer, Document Viewer |
| 9 | **Submit timeout** (consult, decision, publish) | WS send fails or backend doesn't ack within 5s | Button reverts from loading state + toast + draft preserved in localStorage for retry | Retry button; draft never lost | Compliance WS consult panel, Leadership Dashboard decisions, Document Viewer publish |
| 10 | **Duplicate consult pending** | User tries to send consult when one already exists for this case | Panel shows "Đã có 1 consult đang chờ trên case này. Xem trạng thái hiện tại?" | Link to existing request, prevent duplicate | Compliance WS consult panel |
| 11 | **Rate-limited** | API rate limit (429) | Toast "Bạn đã thao tác quá nhanh. Thử lại sau X giây." | Auto-retry after backoff | All screens |
| 12 | **Concurrent edit collision** | Another user modified the same case simultaneously | Toast + auto-refresh case + highlight changed fields | Manual merge or accept remote | Department Inbox (drag-drop), Compliance WS |
| 13 | **Anomaly service fails** | SecurityOfficer anomaly detection offline | Anomaly panel shows "Detection temporarily unavailable" — non-blocking | Non-blocking; log only | Security Console, Leadership Dashboard |
| 14 | **Citizen push delivery fails** | Firebase FCM / Zalo OA rejection | Server-side retry queue + fallback to SMS + in-app notification still persists | Retry queue handles it silently | Citizen Portal (backend concern) |

**Render rules:**
- Banner vs toast vs modal decision: **banner** for persistent errors that block further work (WS disconnect, auth expired), **toast** for transient errors with retry (submit fail, rate limit), **modal** for errors that require immediate user decision (re-auth, concurrent edit collision)
- Error color: use `--color-status-danger-*` for errors that blocked user intent, `--color-status-warning-*` for gaps/degraded state that user can still proceed past
- Error copy: always Vietnamese-first, always name the action (not the technology). "Không gửi được ý kiến" not "WebSocket error 1006"
- Always include a recovery path. Never dead-end the user.

## Demo polish checklist

Per screen, before ship:
- [ ] All 6 states implemented
- [ ] Responsive at 1440 and 1920
- [ ] Dark + light mode tested
- [ ] Animations at 60fps
- [ ] Vietnamese text renders correctly
- [ ] No lorem ipsum — real content
- [ ] Contrast ratio passes AA
- [ ] Keyboard nav works end-to-end
- [ ] Screen reader labels
- [ ] ⌘K command palette opens
- [ ] Toast feedback on actions

## File organization

```
frontend/
├── app/
│   ├── (public)/           # Citizen Portal
│   │   ├── page.tsx
│   │   ├── cases/[code]/
│   │   └── tthc/
│   ├── (internal)/          # Workspace (auth required)
│   │   ├── intake/
│   │   ├── compliance/[id]/
│   │   ├── inbox/
│   │   ├── consult/         # NEW — Consult Inbox (screen 9)
│   │   ├── consult/[id]/
│   │   ├── cases/[id]/
│   │   ├── cases/[id]/trace/
│   │   ├── dashboard/
│   │   ├── kg/              # NEW — KG Explorer (screen 10)
│   │   ├── kg/article/[id]/
│   │   ├── kg/tthc/[code]/
│   │   ├── security/
│   │   └── admin/
│   └── api/
├── components/
│   ├── ui/                  # shadcn base
│   ├── govflow/             # custom
│   │   ├── CaseCard.tsx
│   │   ├── AgentStep.tsx
│   │   ├── CaseGraph.tsx
│   │   ├── KGGraph.tsx          # NEW — Cytoscape wrapper
│   │   ├── PermissionDenied.tsx
│   │   ├── ClassificationBadge.tsx
│   │   ├── ClassificationBanner.tsx  # NEW — sticky top+bottom
│   │   ├── PortionMark.tsx           # NEW — inline classification pill
│   │   ├── Redacted.tsx              # NEW — solid bar redaction
│   │   ├── ConsultSlidePanel.tsx     # NEW — Compliance WS slide panel
│   │   ├── ConsultRequestCard.tsx    # NEW — Consult Inbox list item
│   │   ├── OpinionComposer.tsx       # NEW — Tiptap rich text
│   │   ├── ConnectionLostBanner.tsx  # NEW — WS disconnect UI
│   │   ├── ElevationModal.tsx        # NEW — step-up auth for clearance
│   │   ├── ClearanceCountdown.tsx    # NEW — header chip for granted elevation
│   │   └── ...
│   └── layout/
├── lib/
│   ├── api.ts               # typed API client
│   ├── ws.ts                # WebSocket hooks
│   ├── graph.ts             # React Flow helpers
│   ├── cytoscape.ts         # Cytoscape helpers for KG Explorer
│   ├── motion.ts            # motionTokens export for Framer Motion
│   ├── permissions.ts
│   └── classification.ts    # classification context + helpers
└── styles/
    └── tokens/              # design-tokens.md materialized
        ├── color.css        # primitive + semantic OKLCH
        ├── type.css         # typography scales + VN hardening
        ├── motion.css       # duration + easing
        ├── spacing.css
        └── index.css        # imports all
```

## Implementation references (reuse first)

> Building 10 polished screens in 4-5 days requires aggressive reuse. This section lists **what to copy-paste instead of build**. Every component mentioned here has a working shadcn/Tremor/React Flow example — do NOT rebuild from scratch.

### shadcn/ui blocks to copy

- **[ui.shadcn.com/blocks Dashboard-01](https://ui.shadcn.com/blocks)** → Leadership Dashboard baseline (KPI cards + charts + table). Copy, retint with our tokens, done.
- **[ui.shadcn.com/blocks Sidebar-07](https://ui.shadcn.com/blocks)** → Internal Workspace shell (nav + header + command palette). Every internal screen wraps this.
- **[ui.shadcn.com/blocks Login-04](https://ui.shadcn.com/blocks)** → VNeID login page wrapper.
- **Components (pure shadcn, already installed)**: `Sheet` (for Consult slide panel), `Command` (⌘K palette), `Skeleton` (loading states), `Tabs`, `Tooltip`, `Popover`, `DropdownMenu`, `Sonner` (toasts), `DataTable` (TanStack Table + Radix), `Dialog`, `AlertDialog` (destructive confirms), `Progress` (compliance bar), `Checkbox`, `Label`, `RadioGroup`, `Switch`.

### React Flow (XyFlow) starters

- **["Custom Node" example](https://reactflow.dev/examples/nodes/custom-node)** → AgentStepNode, GapNode, CitationNode base pattern.
- **["Collaborative Edge Sharing"](https://reactflow.dev/examples/edges/collaboration)** → multi-user Agent Trace Viewer (deferred for PoC, useful pattern).
- **["Dagre Tree" example](https://reactflow.dev/examples/layout/dagre-tree)** → hierarchical layout for Agent Trace Viewer (already scaffolded in [graph-visualization.md:45-63](./graph-visualization.md#L45-L63)).
- **[Layouting docs](https://reactflow.dev/learn/layouting/layouting)** — pick dagre or elkjs; never force-directed for workflows (see [Polish rules in graph-visualization.md](./graph-visualization.md) for rationale).

### Tremor blocks for Leadership Dashboard

- **[tremor.so/blocks](https://blocks.tremor.so/)** KPI cards + chart templates. Saves ~4h vs custom Recharts.
- Specifically: `KpiCardDelta` for 4-metric row, `AreaChart` for processing time trend, `BarList` for SLA-by-TTHC. All dark-mode compatible, easy to retint.

### Cytoscape.js for KG Explorer

- **[Cytoscape demos](https://js.cytoscape.org/#demos)** — the "Tokyo Railways" and "Graph Processing" demos show cola-layout performance on 500+ node graphs.
- **cytoscape-cola** extension for force-directed layout (for KG Explorer topology mode).
- **cytoscape-dagre** extension for hierarchical layout (for single-law structure view).

### DO NOT REBUILD list

- **PDF viewer** → `react-pdf` (@latest, Next.js 15 compatible). Supports annotations + search.
- **File upload with drag-drop** → shadcn `FileUploader` community extension (not in core shadcn but well-maintained).
- **Rich text editor** (Consult opinion composer) → `@tiptap/react` + StarterKit. Built-in Markdown export for storage.
- **Date formatting / relative time** → `date-fns` + `date-fns/locale/vi`.
- **Virtual scroll for long lists** (audit log, Kanban columns) → TanStack Virtual.
- **Form validation** → React Hook Form + Zod.
- **Toast notifications** → Sonner (shadcn-compatible).
- **Graph node tooltip positioning** → `floating-ui` (React Flow defaults are ugly; restyle).

### Budget reminder

**2.5 days for 10 screens = ~6h average per screen.** Any component taking >6h must be downgraded (strip features) or swapped for one of the reuse options above. The signature screens (Agent Trace Viewer, Intake UI, Consult Inbox, KG Explorer) get extra time budget; MVP screens (Department Inbox, Document Viewer) must use heavy reuse.

**Hard rule:** before writing any new component, grep existing shadcn / Tremor / React Flow examples for something close. If there's a 70% match, copy and modify — don't start blank. The difference between a polished demo and a prototype-looking demo is usually "did they reuse enough."
