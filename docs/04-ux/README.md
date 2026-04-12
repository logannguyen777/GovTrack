# 04-UX — Design spec index

> UX documentation for GovFlow. Read this first to know where to look for each question.

## Source of truth map

| Question | Canonical doc |
|---|---|
| **What do judges see in the 2:30 demo?** | [`../07-pitch/demo-video-storyboard.md`](../07-pitch/demo-video-storyboard.md) |
| **When does each system artifact first appear on screen?** | [`artifact-inventory.md`](./artifact-inventory.md) (Table 3) |
| **Which screen surfaces which artifact?** | [`artifact-inventory.md`](./artifact-inventory.md) (Tables 1-2) |
| **How is each of the 10 screens built?** | [`screen-catalog.md`](./screen-catalog.md) |
| **What token/color/typography/motion values to use?** | [`design-tokens.md`](./design-tokens.md) |
| **What components exist, error/loading states, keyboard shortcuts?** | [`design-system.md`](./design-system.md) |
| **How does the Agent Trace Viewer graph render (+ ARIA labels)?** | [`graph-visualization.md`](./graph-visualization.md) |
| **How does realtime plumbing (WebSocket) drive animations?** | [`realtime-interactions.md`](./realtime-interactions.md) |
| **Which persona touches which screen?** | [`user-journeys.md`](./user-journeys.md) |
| **Hero case seed data, demo reset, fallback video, projector test?** | [`demo-day-mechanics.md`](./demo-day-mechanics.md) |

## Files in this directory

- **[artifact-inventory.md](./artifact-inventory.md)** — cross-cut table: system artifact × screen × animation × demo timestamp. The sync contract between UX spec and pitch narrative.
- **[demo-day-mechanics.md](./demo-day-mechanics.md)** — hero case seed data, reset endpoint, fallback video plan, projector test, rehearsal protocol.
- **[design-system.md](./design-system.md)** — component library, error state catalog, classification banner + redaction component, motion intent mapping, global keyboard shortcut reference, implementation references (reuse-first cheat sheet).
- **[design-tokens.md](./design-tokens.md)** — 3-tier token architecture (primitive → semantic → component), OKLCH color ramps, Vietnamese-hardened typography with canonical test paragraph, Material 3 motion scale.
- **[graph-visualization.md](./graph-visualization.md)** — React Flow + Cytoscape setup for Agent Trace Viewer and KG Explorer, node types, animations, "pro vs student project" polish rules, ARIA label templates.
- **[realtime-interactions.md](./realtime-interactions.md)** — WebSocket architecture, 15 event types, animation coordination, demo moment mapping.
- **[screen-catalog.md](./screen-catalog.md)** — 10 screens with ASCII wireframes, per-screen skeleton + error states + artifact coverage, live choreography tables for all 4 hero demo scenes (2, 3, 5, 6), mobile view for Scene 4, Agent Status tab.
- **[user-journeys.md](./user-journeys.md)** — 6 personas end-to-end flows with time savings.

## Screen roster

| # | Screen | Hero tier | Persona | Route |
|---|---|---|---|---|
| 1 | Citizen Portal | MVP | Minh (citizen) | `/`, `/cases/[code]` |
| 2 | Intake UI | **Hero #2** | Chị Lan | `/intake` |
| 3 | Agent Trace Viewer | **Hero #1** (signature) | debug/demo | `/cases/[id]/trace` |
| 4 | Compliance Workspace | Important | Anh Tuấn | `/compliance/[case_id]` |
| 5 | Department Inbox (Kanban) | MVP | Anh Tuấn, department staff | `/inbox` |
| 6 | Leadership Dashboard | Important | Chị Hương | `/dashboard` |
| 7 | Security Console | Important (3-scene demo) | Anh Quốc | `/security` |
| 8 | Document Viewer | MVP | any authorized | `/cases/[id]` |
| 9 | **Consult Inbox** (NEW) | Critical for Persona 5 | Anh Dũng (pháp chế) | `/consult`, `/consult/[id]` |
| 10 | **KG Explorer** (NEW) | Critical for GraphRAG proof | Anh Tuấn, Anh Dũng, demo Q&A | `/kg`, `/kg/article/[id]` |

## Read order for new frontend contributors

1. This README (source of truth map)
2. [`user-journeys.md`](./user-journeys.md) — understand WHO and WHY
3. [`screen-catalog.md`](./screen-catalog.md) — browse all 10 screens
4. [`design-tokens.md`](./design-tokens.md) — internalize the token vocabulary
5. [`design-system.md`](./design-system.md) — component patterns + mandatory states + reuse refs
6. [`artifact-inventory.md`](./artifact-inventory.md) — the sync contract (skim tables)
7. [`graph-visualization.md`](./graph-visualization.md) — only if building Agent Trace Viewer or KG Explorer
8. [`realtime-interactions.md`](./realtime-interactions.md) — only if wiring WebSocket event handlers

After reading, you should be able to answer:
- "At Scene 3 @ 1:03 what appears on screen, driven by which WS event, styled with which component, animating with which tokens?"
- "If the PDF fails to load in Document Viewer, what does the user see and how do they recover?"
- "Why does GovFlow use solid-bar redaction instead of blur?"

If any answer is unclear, the spec has a gap — fix it or ask.

## Update discipline

- **Adding a new artifact** → update [`artifact-inventory.md`](./artifact-inventory.md) Table 1 FIRST, then the consuming screen in [`screen-catalog.md`](./screen-catalog.md), then the event type in [`realtime-interactions.md`](./realtime-interactions.md).
- **Adding a new screen** → add wireframe to [`screen-catalog.md`](./screen-catalog.md), add row to [`artifact-inventory.md`](./artifact-inventory.md) Table 2, add persona touch to [`user-journeys.md`](./user-journeys.md) if applicable, add to roster table above.
- **Changing a token value** → edit [`design-tokens.md`](./design-tokens.md) ONLY. Never hand-tune in component files.
- **Changing an animation duration** → edit [`design-tokens.md`](./design-tokens.md) motion section. Verify [`design-system.md`](./design-system.md) Motion intent mapping still makes sense with the new value.
- **Updating the demo narrative** → edit [`../07-pitch/demo-video-storyboard.md`](../07-pitch/demo-video-storyboard.md) AND [`artifact-inventory.md`](./artifact-inventory.md) Table 3 in the same commit. They must stay in sync.

## Principle: UX spec ↔ narrative ↔ artifact

The three-way contract:

```
        screen-catalog.md (UX spec)
               │
               │
artifact-inventory.md (cross-cut) ───── demo-video-storyboard.md (narrative)
```

Any edit to one edge should be reflected in both endpoints. Drift = spec lies.
