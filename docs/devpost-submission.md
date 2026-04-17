# GovFlow — Devpost Submission Writeup

> Paste the sections below into the Devpost project form.
> Replace [PLACEHOLDER] values before submitting.
> GitHub: [PLACEHOLDER — repo URL]
> Demo video: [PLACEHOLDER — YouTube/Loom URL]
> Production URL: [PLACEHOLDER — if deployed]

---

## Project Name

**GovFlow — Agentic GraphRAG for Vietnam Public Administrative Services**

---

## Inspiration

**Vấn đề (Vietnamese):**
Việt Nam xử lý hơn 100 triệu TTHC mỗi năm tại 63 tỉnh thành. Nhưng thời gian xử lý cấp phép xây dựng vẫn mất 5–7 ngày làm việc — và đó là chưa kể vấn đề phổ biến nhất: người dân nộp hồ sơ thiếu thành phần, bị trả về sửa rồi lại xếp hàng từ đầu.

Chúng tôi phỏng vấn chuyên viên tại bộ phận một cửa cấp huyện và tìm ra 3 nguyên nhân gốc rễ: (1) kiểm tra thành phần hồ sơ thủ công — mỗi ca phải đối chiếu 5–15 văn bản pháp luật; (2) tra cứu pháp luật chậm — Việt Nam có 870.000+ văn bản trên vbpl.vn; (3) phối hợp liên phòng ban nặng về giấy tờ, "xin ý kiến" một vòng mất 3–7 ngày.

**The problem (English):**
Vietnam processes over 100 million TTHC (public administrative procedure) requests per year. Average processing time for a construction permit is 5–7 business days — and the most common failure is applicants submitting incomplete files: they are sent home to correct them, losing their queue position and waiting again.

Three root causes: manual compliance checking against 5–15 legal documents per case; slow legal lookup (870,000+ documents on vbpl.vn with frequent amendments); and paper-heavy cross-department coordination ("xin ý kiến" rounds take 3–7 days alone).

The national e-government framework (NĐ 61/2018, NĐ 107/2021, Đề án 06) mandates digitization — but most existing systems simply digitize the paper process without automating the reasoning. **GovFlow automates the reasoning.**

---

## What It Does

GovFlow is a production-grade agentic system for Vietnam's public sector with two distinct workflows:

### Flow 1: Citizen TTHC (6-step, NĐ 61/2018)

A citizen submits a construction permit application (code 1.004415) via the Citizen Portal. Ten Qwen3 agents take over:

1. **DocAnalyzer** (Qwen3-VL-Plus) — OCR + layout understanding of uploaded scans. Identifies document types, extracts entities (land parcel ID, project area, citizen ID), detects red stamps and signatures.

2. **Classifier** (Qwen3-Max) — maps the file bundle to a specific TTHC code in the knowledge graph (10,725 vertices / 104,560 edges). Always matches an existing TTHCSpec vertex — never invents codes.

3. **SecurityOfficer** (Qwen3-Max) — assigns initial classification level (Unclassified → Top Secret) per Luật BVBMNN 2018 Điều 8. All downstream agents are clearance-capped from this point.

4. **Compliance** (Qwen3-Max) — compares submitted documents against TTHCSpec RequiredComponents. Detects gaps. Example: "Missing PCCC fire safety certificate — required by NĐ 136/2020/NĐ-CP Điều 9 khoản 2."

5. **LegalLookup** (Qwen3-Max + Qwen3-Embedding v3) — agentic GraphRAG: vector recall on 869 law chunks in Hologres Proxima, then graph traversal on the legal KG following SUPERSEDED_BY / AMENDED_BY edges to ensure only effective provisions are cited.

6. **Router** (Qwen3-Max) — assigns the case to the correct department and staff officer, checking workload.

7. **Consult** (Qwen3-Max) — drafts cross-department consultation requests; aggregates replies into Opinion vertices.

8. **Summarizer** (Qwen3-Max) — generates three versions: executive (3-line leadership brief), staff (full detail + deadlines + citations), citizen (plain Vietnamese explanation).

9. **Drafter** (Qwen3-Max) — produces the output document in NĐ 30/2020 format: Quốc hiệu, số/ký hiệu, trích yếu, 9 required components, digital signature placeholder.

10. **SecurityOfficer** (final pass) — confirms classification before publishing. Writes forensic AuditEvent.

Every agent writes to the Context Graph in real time. The **Agent Trace Viewer** (React Flow + WebSocket) shows the full reasoning chain live.

### Flow 2: Internal Dispatch (PIPELINE_DISPATCH)

An officer uploads an internal memo (công văn) requesting cross-department coordination. **DispatchRouterAgent** classifies it as CONFIDENTIAL, identifies the target department and priority, generates a formatted briefing document (phiếu trình) in NĐ 30/2020 format, and pushes it to the department head's inbox via WebSocket — within seconds.

---

## How We Built It

**AI backbone:**
Qwen3-Max for all reasoning agents (function calling, structured JSON output, Vietnamese instruction following). Qwen3-VL-Plus for DocAnalyzer (multimodal OCR, stamp + signature detection). Qwen3-Embedding v3 for semantic search over the legal corpus. All via Alibaba Cloud Model Studio (DashScope) OpenAI-compatible API.

**Knowledge Graph (Alibaba Cloud GDB):**
Two graphs — a static Knowledge Graph (10,725 vertices encoding laws, decrees, TTHC specs, organizations, positions) and a dynamic Context Graph (per-case state: documents, extracted entities, gaps, citations, tasks, audit events). Gremlin Template Library with 30 prebuilt queries. All 47 GDB calls routed through `PermittedGremlinClient`.

**3-Tier Permission Engine:**
- Tier 1: Agent SDK Guard — parses Gremlin bytecode AST before any DB call, rejects out-of-scope label access
- Tier 2: GDB Native RBAC — per-agent database users with specific GRANT statements, enforced at the DB engine level
- Tier 3: Property Mask Middleware — post-query PII redaction based on clearance (national_id → `***` for clearance < SECRET)

**Backend:** Python FastAPI, pydantic v2, asyncio throughout. Argon2id password hashing, JWT with clearance claims, Alembic migrations (5 versions), OpenTelemetry + Prometheus + Sentry, slowapi rate limiting, DSR endpoints (NĐ 13/2023).

**Frontend:** Next.js 15 App Router (TypeScript strict), shadcn/ui + Tailwind CSS v4, Framer Motion, React Flow for live graph viz, TanStack Query, Zustand, WebSocket real-time agent trace, WCAG-compliant semantic HTML.

**Storage:** Alibaba Cloud Hologres for users + analytics + law embeddings (pgvector-compatible Proxima). Alibaba Cloud OSS with SSE-KMS + STS short-lived credentials.

**Testing:** 280 automated tests (pytest-asyncio, Playwright). Mock DashScope for unit tests, real calls for integration. 23 permission negative scenarios. Agent accuracy benchmarks.

---

## Challenges We Ran Into

**Vietnamese OCR and diacritics:** Vietnamese government documents use strict NĐ 30/2020 formatting, mixed diacritics, red stamps (con dấu đỏ), and handwritten signatures. Careful prompt engineering for each document type schema was required. Diacritic preservation in Gremlin property values needed explicit UTF-8 handling throughout the stack.

**3-tier Gremlin permission engine:** Tier 1 required understanding Gremlin bytecode AST structure; Tier 2 required per-agent DB user provisioning; Tier 3 required a middleware that traverses arbitrary result graphs to mask properties. Making all three work together against 23 negative scenarios took two full days.

**NĐ 30/2020 compliance in Drafter:** Vietnamese administrative documents have strict formatting rules (9 required components, specific font/size/number format, signature block). The Drafter agent validates its own output and retries if components are missing — a structured output + self-correction loop.

**REPEALED article filter:** LegalLookup must never cite a superseded provision. We implemented SUPERSEDED_BY edge traversal in the GraphRAG hop, plus a filter in LegalLookup that checks the `status` property of each LawArticle vertex before citing it.

**Demo reliability with 10 agents + external services:** Any single failure breaks the live demo. We built a full LLM response cache (demo mode) so the pitch runs deterministically in under 10 seconds regardless of DashScope latency or quota state.

---

## Accomplishments We're Proud Of

- **280 automated tests passing** — unit, integration, E2E Playwright, 23 permission negative scenarios, agent accuracy benchmarks. Production-grade, not a hackathon prototype.
- **Full security stack** — Argon2id, JWT revocation, SSRF guard, CSP/HSTS, 3-tier ABAC, STS+SSE-KMS, Gremlin injection prevention, audit middleware. Wave 0 security hardened before any feature work.
- **Complete observability** — OpenTelemetry traces (Jaeger), Prometheus metrics + Grafana dashboard, Sentry (BE + FE), structured JSON logging with PII redaction, p50/p95 benchmarks per agent.
- **Real Vietnamese legal data** — 15 core laws + 4,966 related documents from vbpl.vn, 10,725 KG vertices, 104,560 edges. Not synthetic.
- **Dual-flow architecture** — Citizen TTHC + Internal Dispatch as two separate pipelines sharing the same agent infrastructure, permission engine, and audit trail.
- **9 compliance frameworks mapped** — NĐ 61, NĐ 107, NĐ 45, NĐ 42, NĐ 30, NĐ 13, Luật BVBMNN 2018, Luật ANM, Luật BVDLCN — each with specific điều/khoản citation.

---

## What We Learned

**Agentic GraphRAG is meaningfully different from simple RAG.** Vector search alone returns text that may be from repealed decrees. Following SUPERSEDED_BY, AMENDED_BY, REFERENCES edges after vector recall ensures legal currency — this was the key quality improvement over naive RAG for the Compliance and LegalLookup agents.

**Vietnamese legal ontology design matters.** Laws, decrees, circulars, and decisions have specific relationships that must be modeled distinctly (AMENDED_BY vs SUPERSEDED_BY vs REFERENCES vs BASED_ON). Getting the ontology right enabled LegalLookup to retrieve the exact điều/khoản/điểm rather than just the parent law.

**The Alibaba Cloud ecosystem depth for Vietnam government use cases.** GDB + Hologres + OSS + KMS + Model Studio share IAM, VPC, and SLS logging. For government deployments requiring data residency (NĐ 53/2022 Điều 26), the on-prem Qwen3 path via PAI-EAS is genuinely feasible — no other cloud provider currently offers this combination for Vietnam.

**Reliability engineering for demo credibility.** Judges evaluate live demos. A deterministic LLM cache that exactly mirrors production prompt shapes — warmed before the demo — was as important as the feature code itself.

---

## What's Next

- **Mobile app** — React Native for citizens to submit TTHC on smartphones
- **SMS + Zalo OA notifications** — 90%+ smartphone penetration in Vietnam
- **VNeID deep integration** — Đề án 06 digital identity API for one-click citizen verification
- **Federated Knowledge Graph** — Share anonymized legal precedents across provinces/ministries
- **Qwen3 on-prem (PAI-EAS)** — Deploy Qwen3-32B within Vietnam data centers (NĐ 53/2022)
- **Predictive SLA** — ML to predict which cases will miss legal deadlines 3 days ahead
- **Multi-tenant SaaS** — Each Sở/UBND as an isolated tenant with its own KG extensions
- **Auto-update KG** — Crawl vbpl.vn + thuvienphapluat.vn automatically on new legal documents

---

## Built With

`qwen3-max` `qwen3-vl-plus` `qwen3-embedding-v3` `alibaba-cloud-model-studio` `dashscope` `alibaba-cloud-gdb` `gremlin` `tinkerpop` `alibaba-cloud-hologres` `alibaba-cloud-oss` `alibaba-cloud-kms` `alibaba-cloud-ack` `fastapi` `python` `pydantic` `asyncio` `next.js` `react` `typescript` `shadcn-ui` `tailwindcss` `framer-motion` `react-flow` `tanstack-query` `zustand` `websockets` `opentelemetry` `prometheus` `grafana` `sentry` `argon2` `jwt` `alembic` `postgresql` `pgvector` `mcp` `playwright` `pytest`

---

## Try It Out

- **GitHub Repository:** [PLACEHOLDER — https://github.com/your-org/GovTrack]
- **Demo Video:** [PLACEHOLDER — YouTube/Loom URL]
- **Production URL:** [PLACEHOLDER — if deployed on ACK]
- **Devpost:** [PLACEHOLDER — this page URL after submission]

---

## Team

[PLACEHOLDER — Add team member names, GitHub handles, and roles]

---

*Built at Qwen AI Build Day 2026 — Public Sector (Government) Track*
*Submission deadline: 2026-04-17*
