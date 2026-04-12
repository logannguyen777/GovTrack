# GovFlow — Project Context

> Agentic GraphRAG for Vietnam Public Administrative Services (TTHC)
> Qwen AI Build Day 2026 — Public Sector Track

## Monorepo Layout

```
GovTrack/
  backend/                  # Python FastAPI + Agent Runtime
    src/
      main.py               # FastAPI app factory + lifespan
      config.py              # Pydantic Settings (env vars)
      database.py            # GDB + Hologres + OSS connection factories
      auth.py                # JWT validation + claims extraction
      api/                   # FastAPI routers
        cases.py             # POST/GET /cases
        documents.py         # GET /documents/{id}
        agents.py            # Agent trace + trigger
        graph.py             # Admin Gremlin queries
        search.py            # Law + TTHC search
        leadership.py        # Dashboard + inbox
        audit.py             # Audit log queries
        public.py            # Citizen-facing (no auth)
        ws.py                # WebSocket manager
        schemas.py           # Pydantic v2 models
      agents/                # 10 agents + orchestrator
        base.py              # BaseAgent ABC
        orchestrator.py      # AgentRuntime DAG executor
        qwen_client.py       # DashScope SDK wrapper
        mcp_server.py        # MCP tool registry
        planner.py
        doc_analyzer.py
        classifier.py
        compliance.py
        legal_lookup.py
        router.py
        consult.py
        summarizer.py
        drafter.py
        security_officer.py
        profiles/            # YAML permission profiles per agent
      graph/                 # Graph layer
        client.py            # GremlinClient wrapper
        templates.py         # 30 Gremlin template queries
        sdk_guard.py         # Tier 1 permission
        permitted_client.py  # Wraps client with 3-tier checks
        property_mask.py     # Tier 3 property redaction
        audit.py             # AuditEvent writer
      services/              # Business logic
        case_service.py
        notify_service.py
        oss_service.py
    tests/
    pyproject.toml
  frontend/                  # Next.js 15 + shadcn/ui
    src/
      app/
        (public)/            # Citizen Portal (no auth)
        (internal)/          # Staff workspace (JWT auth)
        auth/                # Login
        layout.tsx
      components/
        ui/                  # shadcn/ui components
        graph/               # React Flow visualizations
        layout/              # Sidebar, topbar
        providers/           # Auth, WS, Query providers
      hooks/                 # TanStack Query hooks
      stores/                # Zustand stores
      lib/                   # API client, WS client, utils
      types/                 # TypeScript interfaces
    package.json
  infra/                     # Infrastructure configs
    docker-compose.yml       # Local dev: gremlin-server + postgres + minio
    hologres-schema.sql
    gdb-rbac.groovy
  data/                      # Reference data (exists)
    legal/                   # Vietnamese legal documents
    samples/                 # Sample TTHC documents
    tthc_specs/              # 5 TTHC spec JSONs
  scripts/                   # Data pipeline scripts (exists)
    ingest_legal.py
    ingest_tthc.py
  docs/                      # Specification docs (60+ files, exists)
    implementation/          # Implementation guides (this project)
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15 (App Router, TypeScript) | Web UI |
| UI | shadcn/ui + Tailwind CSS v4 + Framer Motion + React Flow | Design system, graph viz |
| Backend | Python FastAPI + pydantic v2 | REST + WebSocket API |
| Graph DB | Alibaba Cloud GDB (Gremlin/TinkerPop 3.x) | Knowledge Graph + Context Graph |
| Relational+Vector | Alibaba Cloud Hologres (PG-compat + Proxima) | Users, analytics, law embeddings |
| Blob Storage | Alibaba Cloud OSS (S3-compatible) | Documents, templates, archives |
| AI Models | Qwen3-Max, Qwen3-VL-Plus, Qwen3-Embedding v3 | Reasoning, OCR, embeddings |
| AI Gateway | Alibaba Cloud Model Studio (DashScope) | OpenAI-compatible API |
| Agent Protocol | MCP (Model Context Protocol) | Tool exposure to agents |

## Key Environment Variables

```
DASHSCOPE_API_KEY=          # Alibaba Cloud Model Studio
GDB_ENDPOINT=               # ws://gdb-instance:8182/gremlin
GDB_USERNAME=               # GDB admin user
GDB_PASSWORD=               # GDB admin password
HOLOGRES_DSN=               # postgresql://user:pass@host:5432/govflow
OSS_ENDPOINT=               # https://oss-ap-southeast-1.aliyuncs.com
OSS_ACCESS_KEY=
OSS_SECRET_KEY=
OSS_BUCKET=govflow-prod
JWT_SECRET=                 # HS256 secret for hackathon
```

## 10 Agents

| # | Name | Model | Role |
|---|------|-------|------|
| 1 | Planner | Qwen3-Max | Task DAG generation |
| 2 | DocAnalyzer | Qwen3-VL-Plus | OCR + entity extraction |
| 3 | Classifier | Qwen3-Max | TTHC matching |
| 4 | Compliance | Qwen3-Max | Gap detection + citations |
| 5 | LegalLookup | Qwen3-Max + Embedding v3 | Agentic GraphRAG |
| 6 | Router | Qwen3-Max | Department assignment |
| 7 | Consult | Qwen3-Max | Cross-dept opinion |
| 8 | Summarizer | Qwen3-Max | Role-aware summaries |
| 9 | Drafter | Qwen3-Max | ND 30/2020 document generation |
| 10 | SecurityOfficer | Qwen3-Max | Classification + access control |

## DashScope API (OpenAI-compatible)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)
# Models: qwen-max-latest, qwen-vl-max-latest, text-embedding-v3
```

## Code Conventions

- **Python**: async everywhere, pydantic v2 for validation, ruff for linting
- **TypeScript**: strict mode, no `any`, TanStack Query for server state
- **Graph queries**: use Gremlin Template Library (30 prebuilt), avoid raw Gremlin unless necessary
- **Permissions**: every GDB query goes through PermittedGremlinClient (SDK Guard + RBAC + Property Mask)
- **Audit**: every graph write creates AuditEvent vertex
- **Vietnamese**: all user-facing text in Vietnamese, preserve diacritics, UTF-8 everywhere
- **Security**: never commit secrets, never skip permission checks, never auto-publish without human review

## Documentation

- `docs/03-architecture/` — Technical specs (overview, agents, permissions, data model, GraphRAG, MCP)
- `docs/04-ux/` — Design system, screen catalog, graph visualization, realtime interactions
- `docs/implementation/` — Step-by-step implementation guides (this is what you follow)
- `docs/08-execution/` — Daily plan, milestones, verification rubric

## Build Timeline

- Day 12/04: Infra + KG + API skeleton + Frontend skeleton + Agent skeletons
- Day 13/04: Permission engine + 5 core agents (Planner, DocAnalyzer, Classifier, Compliance, LegalLookup)
- Day 14/04: Remaining 5 agents + Frontend core 3 screens + E2E test
- Day 15/04: Remaining 5 screens + 3 permission demo scenes + polish
- Day 16/04: Benchmark + demo video + pitch deck
- Day 17/04: Final submission to Devpost
