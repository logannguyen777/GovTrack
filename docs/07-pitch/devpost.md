# GovFlow — Devpost Submission Writeup

> Template for pasting to devpost.com.
> Replace [PLACEHOLDER] values before submitting.
> Target length: 1000–1500 words.

---

## Project Name

**GovFlow — Agentic GraphRAG for Vietnam Public Administrative Services**

---

## Inspiration

Vietnam's public administrative system processes over **100 million TTHC (thủ tục hành chính) requests** per year across 63 provinces. Yet the average processing time for a construction permit (Cấp phép xây dựng) is still **5–7 business days** — and that's before accounting for the most common problem: applicants submit incomplete files and are sent home to fix them, only to return and wait again.

We talked to civil servants at district-level one-stop service centers (bộ phận một cửa) and found three root causes:

1. **Manual compliance checking** — officers must mentally cross-reference 5–15 legal documents per case type to verify all required components are present and valid.
2. **Legal lookup bottleneck** — regulations change frequently (Vietnam passed 870,000+ legal documents on vbpl.vn), and officers cannot always find the latest effective version of a decree in real time.
3. **Paper-heavy coordination** — when a case needs sign-off from multiple departments (e.g., fire safety + environmental assessment + land use), the "xin ý kiến" (consultation) process alone takes 3–7 days.

The national e-government framework (NĐ 61/2018, NĐ 107/2021, Đề án 06) provides the legal mandate for digitization, but most existing systems simply digitize the paper process — they don't automate the reasoning.

**GovFlow is our answer:** 10 AI agents running on Qwen3, coordinated over a legal knowledge graph, with a 3-tier security engine enforcing Vietnam's 4-level classification law at every step.

---

## What It Does

GovFlow is a **production-grade agentic system** that handles two flows:

### Flow 1: Citizen TTHC (6-step workflow per NĐ 61/2018)

A citizen submits a construction permit application (Cấp phép xây dựng, code 1.004415) via the Citizen Portal. GovFlow's 10 agents take over:

1. **DocAnalyzer** (Qwen3-VL-Plus) — OCR and layout understanding of uploaded scans. Identifies document types, extracts entities (land parcel number, project area, citizen ID), detects red stamps and signatures. Handles blurry or skewed scans that defeat traditional OCR.

2. **Classifier** (Qwen3-Max) — maps the file bundle to a specific TTHC code in the knowledge graph (10,725 vertices, 104,560 edges). Must match an existing TTHCSpec vertex — never invents codes.

3. **SecurityOfficer** (Qwen3-Max) — assigns the initial classification level (Unclassified → Top Secret per Luật BVBMNN 2018 Điều 8). All downstream agents are clearance-capped.

4. **Compliance** (Qwen3-Max) — compares submitted documents against the TTHCSpec's RequiredComponents. Detects gaps. In our demo: "Missing PCCC fire safety certificate — required by NĐ 136/2020/NĐ-CP Điều 9 khoản 2."

5. **LegalLookup** (Qwen3-Max + Qwen3-Embedding v3) — agentic GraphRAG: vector recall on 869 law chunks in Hologres Proxima, then graph traversal on the legal KG to resolve SUPERSEDED_BY / AMENDED_BY edges, ensuring only currently effective provisions are cited.

6. **Router** (Qwen3-Max) — assigns the case to the correct department and staff officer, checking current workload.

7. **Consult** (Qwen3-Max) — drafts cross-department consultation requests, aggregates responses into Opinion vertices.

8. **Summarizer** (Qwen3-Max) — generates three versions: executive summary for leadership (3 lines + action item), staff summary (full technical detail + deadlines + citations), and citizen-facing explanation in plain Vietnamese.

9. **Drafter** (Qwen3-Max) — produces the output document (approval, denial, or supplement request) in strict NĐ 30/2020 format: Quốc hiệu, số/ký hiệu, trích yếu, 9 required components, digital signature placeholder.

Every agent writes to the Context Graph in real time. The **Agent Trace Viewer** (React Flow + WebSocket) shows judges the full reasoning chain live.

### Flow 2: Internal Dispatch (PIPELINE_DISPATCH)

An officer uploads an internal memo (công văn) requesting cross-department coordination on a fire safety issue. The **DispatchRouterAgent** classifies it as CONFIDENTIAL, identifies the target department, and the system generates a formatted briefing document (phiếu trình) for the department head — appearing in their inbox within seconds.

---

## How We Built It

**AI backbone:**
Qwen3-Max for all reasoning agents (function calling, structured JSON output, Vietnamese instruction following). Qwen3-VL-Plus for DocAnalyzer (multimodal OCR). Qwen3-Embedding v3 for semantic search over the legal corpus. All accessed via Alibaba Cloud Model Studio (DashScope) with OpenAI-compatible API.

**Knowledge Graph (Alibaba Cloud GDB):**
Two graphs — a static Knowledge Graph (10,725 vertices: laws, decrees, TTHC specs, organizations, positions) and a dynamic Context Graph (per-case state: documents, extracted entities, gaps, citations, tasks, audit events). Gremlin Template Library with 30 prebuilt queries. All 47 GDB calls routed through `PermittedGremlinClient`.

**3-Tier Permission Engine:**
- Tier 1: Agent SDK Guard — parses Gremlin bytecode AST before any DB call, rejects out-of-scope label/edge access
- Tier 2: GDB Native RBAC — per-agent database users with specific GRANT statements, enforced at the DB engine level
- Tier 3: Property Mask Middleware — post-query PII redaction based on clearance level (national_id → `***` for clearance < SECRET)

**Backend:** Python FastAPI, pydantic v2, asyncio throughout. Argon2id password hashing, JWT with clearance claims, Alembic migrations, OpenTelemetry + Prometheus + Sentry observability, Slowapi rate limiting.

**Frontend:** Next.js 15 App Router, shadcn/ui + Tailwind CSS v4, Framer Motion, React Flow for graph visualization, TanStack Query, Zustand, WebSocket for real-time agent trace.

**Storage:** Alibaba Cloud Hologres for users + analytics + law chunk embeddings (pgvector-compatible). Alibaba Cloud OSS with SSE-KMS + STS short-lived credentials for document storage.

**Testing:** 280 automated tests (pytest-asyncio, Playwright). Mock DashScope for unit tests, real calls for integration tests. 23 permission negative scenarios. Agent accuracy benchmarks.

---

## Challenges

**Vietnamese OCR and document understanding:** Vietnamese government documents use specific formatting (NĐ 30/2020 thể thức), mixed diacritics, red stamps (con dấu đỏ), and handwritten signatures. Qwen3-VL-Plus handles this well, but we needed careful prompt engineering for entity extraction schemas per document type.

**Building a Gremlin permission engine:** The 3-tier engine required understanding Gremlin bytecode AST at Tier 1, configuring per-agent DB users in TinkerGraph at Tier 2, and writing a middleware that traverses arbitrary result graphs to mask properties at Tier 3. This took two full days to make robust enough for the 23 negative test scenarios.

**NĐ 30/2020 compliance in Drafter:** Vietnamese administrative documents have strict formatting rules (9 required components, specific font/size, number format, signature block structure). The Drafter agent had to validate its own output and loop until all 9 components were present — a structured output + self-correction pattern.

**Internal Dispatch scope expansion:** Midway through the build we realized the PDF brief explicitly mentioned "nội bộ" (internal) workflow as a separate requirement. We extended CaseType to include `internal_dispatch` and built DispatchRouterAgent as a dedicated agent — two days before deadline.

**Keeping the demo reliable:** With 10 agents and multiple external services, any one failure breaks the demo. We built a full LLM response cache (demo mode) so the pitch demo runs deterministically in <10 seconds regardless of DashScope API latency or quota.

---

## Accomplishments We're Proud Of

- **280 automated tests passing** — unit, integration, E2E Playwright, permission negative, agent accuracy benchmarks. This is production-grade, not a hackathon prototype.
- **Full security hardening** — Argon2id, JWT revocation, SSRF guard, CSP/HSTS, 3-tier ABAC, STS+SSE-KMS, Gremlin injection prevention, audit middleware.
- **Complete observability stack** — OpenTelemetry traces, Prometheus metrics, Sentry error tracking, structured JSON logging, p50/p95 benchmarks per agent.
- **Real legal data** — 15 core Vietnamese laws + 4,966 related documents ingested from vbpl.vn (10,725 vertices, 104,560 edges). Not synthetic.
- **Dual-flow architecture** — Citizen TTHC + Internal Dispatch, two different pipelines with shared agent infrastructure.
- **Compliance by design** — 9 Vietnamese legal frameworks mapped to specific GovFlow features, each with the specific điều/khoản citation.

---

## What We Learned

**Agentic GraphRAG is different from simple RAG.** The key insight was that traversing the knowledge graph after vector recall — following SUPERSEDED_BY, AMENDED_BY, REFERENCES edges — dramatically improves citation accuracy. Pure vector search returns text that might be from a repealed decree. Graph traversal ensures legal currency.

**Vietnamese legal modeling requires careful ontology design.** Laws, decrees, circulars, and decisions have specific relationships (AMENDED_BY, BASED_ON, REFERENCES, SUPERSEDED_BY) that are distinct from generic "related document" edges. Getting this right enabled LegalLookup to find the exact điều/khoản/điểm rather than the parent law.

**The Alibaba Cloud ecosystem is deeply integrated.** GDB + Hologres + OSS + KMS + Model Studio share IAM, VPC, and logging infrastructure. For government deployments requiring data residency (NĐ 53/2022), the on-prem option with Qwen3 open-weight on PAI-EAS is genuinely feasible — something no other cloud provider can currently offer for Vietnam.

---

## What's Next

- **Mobile application** — React Native app for citizens to submit and track TTHC on smartphones
- **SMS + Zalo notifications** — Push updates to citizens via Zalo OA (90%+ smartphone penetration in Vietnam)
- **VNeID deep integration** — Connect to Đề án 06 digital identity API for one-click citizen verification
- **Federated Knowledge Graph** — Share anonymized legal precedents across multiple provinces/ministries
- **On-prem deployment** — Package for Qwen3-32B on PAI-EAS within Vietnam data centers (NĐ 53/2022 compliant)
- **Predictive SLA** — ML model to predict which cases will miss their legal deadline 3 days in advance
- **Multi-tenant** — Allow each Sở/UBND to have an isolated tenant with their own KG extensions

---

## Built With

`qwen3-max` `qwen3-vl-plus` `qwen3-embedding-v3` `alibaba-cloud-model-studio` `dashscope` `alibaba-cloud-gdb` `gremlin` `tinkerpop` `alibaba-cloud-hologres` `alibaba-cloud-oss` `alibaba-cloud-kms` `alibaba-cloud-ack` `fastapi` `python` `pydantic` `asyncio` `next.js` `react` `typescript` `shadcn-ui` `tailwindcss` `framer-motion` `react-flow` `tanstack-query` `zustand` `websockets` `opentelemetry` `prometheus` `grafana` `sentry` `argon2` `jwt` `alembic` `postgresql` `pgvector` `mcp` `playwright` `pytest`

---

## Try It Out

- **GitHub Repository:** [https://github.com/[PLACEHOLDER]/GovTrack]
- **Demo Video:** [PLACEHOLDER — YouTube/Loom link]
- **Production URL:** [PLACEHOLDER — if deployed]
- **Devpost submission:** [PLACEHOLDER]

---

## Team

[PLACEHOLDER — Add team member names and roles]

---

*Built at Qwen AI Build Day 2026 — Public Sector Track*
*Submission deadline: 2026-04-17*
