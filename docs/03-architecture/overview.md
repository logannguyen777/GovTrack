# Architecture Overview

## System layers

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1 — PRESENTATION                                          │
│                                                                  │
│  Citizen Portal (public, VNeID auth)                            │
│  Internal Workspace (civil servant, SSO)                        │
│  • Intake UI         • Compliance Workspace                     │
│  • Agent Trace       • Department Inbox                         │
│  • Leadership Dash   • Security Console                         │
│  • Document Viewer                                              │
│                                                                  │
│  [Next.js 15 + shadcn/ui + Framer Motion + React Flow]         │
└────────────────────┬───────────────────────────────────────────┘
                     │ HTTPS + WebSocket
┌────────────────────▼───────────────────────────────────────────┐
│ LAYER 2 — API GATEWAY                                           │
│                                                                  │
│  FastAPI with JWT(sub, clearance_level, departments, role)     │
│  /cases /documents /agents /trace/ws /graph /audit             │
│  /notifications /search /admin /public                         │
│                                                                  │
│  [Python FastAPI + pydantic v2 + SQLAlchemy]                   │
└────────────────────┬───────────────────────────────────────────┘
                     │
     ┌───────────────┼────────────────┬────────────┐
     ▼               ▼                ▼            ▼
┌─────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────┐
│ Agent   │  │ Graph       │  │ Notify   │  │ Ingest  │
│ Runtime │  │ Permission  │  │ Service  │  │ Pipeline│
│ +MCP    │  │ Engine (3)  │  │          │  │         │
└────┬────┘  └──────┬──────┘  └─────┬────┘  └────┬────┘
     │              │                │             │
     └──────────────┴────────────────┴─────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────┐
│ LAYER 3 — DATA STORAGE (polyglot, all Alibaba Cloud)            │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────┐ │
│  │ Alibaba Cloud  │  │ Hologres             │  │ Alibaba      │ │
│  │ GDB            │  │ PG-compat OLAP +     │  │ Cloud OSS    │ │
│  │ (Gremlin/      │  │ Proxima vector +     │  │              │ │
│  │  TinkerPop)    │  │ AI Functions         │  │              │ │
│  │                │  │                      │  │              │ │
│  │ • KG (static)  │  │ • users + policies   │  │ • Raw blobs  │ │
│  │ • CG (per-case)│  │ • law_chunks (vec)   │  │ • Scans PDFs │ │
│  │ • AuditEvents  │  │ • analytics aggs     │  │ • Draft docs │ │
│  │ • AgentSteps   │  │ • audit projection   │  │ (SSE-KMS)    │ │
│  │                │  │ • notifications      │  │              │ │
│  └────────────────┘  └─────────────────────┘  └──────────────┘ │
└───────────────────────────┬────────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────────┐
│ LAYER 4 — AI / REASONING                                        │
│                                                                  │
│  Alibaba Cloud Model Studio                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │ Qwen3-Max   │  │ Qwen3-VL-Plus│  │ Qwen3-Embedding v3  │   │
│  │ (reasoning, │  │ (multimodal  │  │ (semantic chunks)   │   │
│  │  agents,    │  │  OCR, layout,│  │                     │   │
│  │  MCP,       │  │  stamp, sig) │  │                     │   │
│  │  function   │  │              │  │                     │   │
│  │  calling)   │  │              │  │                     │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
│                                                                  │
│  [Production path: Qwen3-32B open-weight via PAI-EAS on-prem]  │
└────────────────────────────────────────────────────────────────┘
```

## Component map

### Presentation layer
- **Next.js 15 App Router** — file-based routing, server components, streaming
- **Zustand** — client-side state (minimal, most state comes from graph via WebSocket)
- **TanStack Query** — server state caching + invalidation
- **React Flow / Cytoscape.js** — graph visualization
- **Framer Motion** — animations
- **shadcn/ui + Tailwind** — design system

### API Gateway
- **FastAPI** — async, pydantic validation, OpenAPI docs
- **python-jose** — JWT with clearance claims
- **websockets** — realtime agent trace + notifications
- **Slowapi** — rate limiting per user tier

### Agent Runtime
- **Python class per agent** — see [`agent-catalog.md`](agent-catalog.md)
- **DashScope SDK** — Qwen3 function calling via Alibaba Cloud Model Studio
- **MCP server** — expose graph tools with permission layer
- **Gremlin Template Library** — ~30 prebuilt query templates
- **Orchestrator** — task DAG execution, parallel where possible

### Graph Permission Engine
3 tiers — see [`permission-engine.md`](permission-engine.md):
1. **Agent SDK Guard** — parse Gremlin AST, check read/write scope
2. **GDB Native RBAC** — per-agent DB users with privilege grants
3. **Property Mask Middleware** — redact properties per agent/user

### Notify Service
- **Push notifications** for citizens (Firebase + Zalo OA)
- **Email** for officials (Alibaba Cloud DirectMail)
- **WebSocket** for in-app alerts

### Ingest Pipeline
- **Presigned URL upload** → OSS → DocAnalyzer agent triggers → Context Graph updates

## Key architectural decisions

### Decision 1 — Graph-native
See [`../02-solution/why-graph-native.md`](../02-solution/why-graph-native.md). Summary: bài toán bản chất là graph, chọn graph DB = right tool.

### Decision 2 — Alibaba Cloud-first
Full stack Alibaba Cloud từ ngày đầu. Không hybrid. Lý do:
- Max điểm "Use of Alibaba Cloud" cho judge Alibaba SA
- Production story thuyết phục VC
- GDB + Hologres + Model Studio có integration sẵn (AI Functions)

### Decision 3 — Qwen3 via Model Studio, roadmap Qwen3-32B on-prem
Demo dùng Model Studio (quick, reliable). Production path qua PAI-EAS deploy Qwen3-32B open-weight cho data residency requirement.

### Decision 4 — 10 agents, không phải 1 super-agent
Mỗi agent có role + scope + permission riêng. Lý do:
- Separation of concerns — dễ debug, audit
- Permission granularity — từng agent có scope riêng
- Parallel execution — agent độc lập có thể chạy song song
- Pitch ready — 10 agent khớp với "multi-agent showcase"

### Decision 5 — Polyglot persistence
Graph (GDB) + Relational+Vector (Hologres) + Blob (OSS). Mỗi store cho đúng job.

### Decision 6 — Human-in-the-loop explicit
Gate tại mọi điểm quyết định citizen-facing (publish VB, approve decision, reclassify). Agent đề xuất, human duyệt. Đây không phải hạn chế — đây là design feature vì cán bộ chịu trách nhiệm pháp lý.

### Decision 7 — WebSocket realtime, không polling
Agent Trace Viewer + Citizen Portal tracking + Security Console audit log — all push via WebSocket. Polling is UX debt.

### Decision 8 — Python backend, TypeScript frontend
Python vì DashScope SDK + agentic ecosystem. TypeScript vì Next.js + shadcn ecosystem. Không JS fullstack vì Qwen3 tooling Python mạnh hơn.

## Request flow — citizen submits bundle

```
1. Citizen → Citizen Portal (Next.js)
2. Next.js → FastAPI /cases (POST with JWT)
3. FastAPI → OSS presigned URL → frontend uploads blob directly
4. FastAPI → GDB: CREATE Case vertex
5. FastAPI → GDB: CREATE Bundle + CONTAINS edges
6. FastAPI → Orchestrator.run(case_id)
7. Orchestrator → Planner.run(case_id)
8. Planner → GDB: query KG for TTHCSpec candidates, write Task vertices
9. Orchestrator → spawn parallel: DocAnalyzer, SecurityOfficer initial scan
10. Each agent → GDB: write results as vertices + edges
11. Orchestrator → Compliance.run(case_id) [after DocAnalyzer]
12. Compliance → LegalLookup.run(case_id, missing) → write Gap/Citation
13. If gaps → Drafter writes CitizenNotice → Notify service → push to citizen
14. If complete → Router → Consult → Summarizer → human review → Drafter → Publish
15. WebSocket streams all agent steps to Agent Trace Viewer throughout
16. Citizen Portal updates status via WebSocket subscription
```

## Scalability considerations

### For hackathon (1 demo, 5 TTHC, ~20 cases tested)
- Single GDB instance (r-small)
- Single Hologres instance
- 1 ECS instance backend
- Qwen calls via Model Studio (rate limit chính)

### For PoC 1 Sở (3 months, ~10k cases/year)
- Same single instances, autoscale agent runtime
- Caching for KG queries (repeated legal lookups)
- Rate limit Qwen Model Studio or switch to PAI-EAS dedicated

### For production 5–10 Sở
- GDB read replica cho analytics
- Hologres compute + storage separation
- Multi-region cho disaster recovery
- Dedicated PAI-EAS for Qwen inference

### For national scale (63 tỉnh × N Sở)
- Multi-tenant architecture (separate graph per tenant)
- Central KG (shared) + per-tenant Context Graph
- Federated query để cross-tenant lookup

## Integration points

### Inbound
- **VNeID** (Đề án 06) — citizen authentication + ID verification
- **Cổng DVC Quốc gia** — OpenAPI để import TTHC metadata + sync status
- **Hệ thống Một cửa Tỉnh** — API adapter cho mỗi tỉnh (tạm không build cho hackathon)
- **Email gateway** (Alibaba Cloud DirectMail) — outbound notifications
- **Zalo OA** — citizen push notifications

### Outbound
- Signed PDFs to OSS → download link to citizen
- Audit log projection to Hologres → reports
- WebSocket events → frontend clients

## Files

- [`dual-graph-design.md`](dual-graph-design.md) — KG + Context Graph schema detail
- [`agent-catalog.md`](agent-catalog.md) — 10 agents, 1 page each
- [`permission-engine.md`](permission-engine.md) — 3-tier ABAC-on-graph
- [`pipeline-walkthrough.md`](pipeline-walkthrough.md) — sequence diagram
- [`graphrag-legal-reasoning.md`](graphrag-legal-reasoning.md) — LegalLookup deep dive
- [`data-model.md`](data-model.md) — GDB + Hologres schemas
- [`alibaba-cloud-stack.md`](alibaba-cloud-stack.md) — product mapping
- [`mcp-integration.md`](mcp-integration.md) — Model Context Protocol
- [`gremlin-template-library.md`](gremlin-template-library.md) — query templates
