# GovFlow

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com)
[![Qwen3](https://img.shields.io/badge/Qwen3-Max%20%7C%20VL%20%7C%20Embedding-orange.svg)](https://dashscope.aliyuncs.com)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-280%20passing-brightgreen.svg)](backend/tests)

**Hệ thống xử lý văn bản hành chính thông minh — Agentic GraphRAG cho khu vực công Việt Nam**

> Qwen AI Build Day 2026 — Public Sector (Government) Track

---

## TL;DR (1 phút)

- **Rút ngắn xử lý TTHC từ 5–7 ngày xuống dưới 2 giờ** bằng cách tự động hoá toàn bộ pipeline: tiếp nhận hồ sơ công dân, OCR tài liệu scan, kiểm tra thành phần, tra cứu pháp lý, phân công xử lý, và soạn văn bản trả lời theo NĐ 30/2020.
- **10 AI agent Qwen3 hoạt động song song** trên đồ thị tri thức 10.725 đỉnh / 104.560 cạnh (15 luật lõi + 5 TTHC flagship), phát hiện thiếu sót hồ sơ và trích dẫn điều luật chính xác đến khoản/điểm cụ thể.
- **Xử lý cả công văn nội bộ (Internal Dispatch)** — DispatchRouterAgent phân loại và chuyển tiếp công văn liên phòng, sinh phiếu trình cho lãnh đạo trong vài giây.
- **3-tier permission engine + 4-level classification** (Unclassified → Top Secret theo Luật BVBMNN 2018) đảm bảo mỗi agent và người dùng chỉ thấy đúng dữ liệu được phép — 280 automated tests kiểm chứng.
- **Real-time trace** — Agent Trace Viewer (React Flow + WebSocket) hiển thị toàn bộ chuỗi suy luận của các agent theo thời gian thực; mọi bước đều có audit trail đầy đủ.

---

## Quickstart — POC trong 10 phút

### Yêu cầu

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- DashScope API key (đăng ký miễn phí tại https://dashscope.console.aliyun.com)

### Các bước

```bash
git clone <repo>
cd GovTrack
cp backend/.env.example backend/.env
# Mở backend/.env, paste DASHSCOPE_API_KEY (đăng ký miễn phí tại https://dashscope.console.aliyun.com)
./scripts/start_demo.sh
# Chờ ~30s — sẽ tự khởi tạo Gremlin + Postgres + MinIO + warm cache
open http://localhost:3100  # Citizen Portal
open http://localhost:8100/docs  # API Swagger
```

> **Demo mode:** `start_demo.sh` bật `DEMO_MODE=true` tự động — cached LLM responses → mỗi scenario chạy dưới 10 giây mà không tiêu quota DashScope.
>
> **Muốn cache warm ngay từ đầu:** `./scripts/start_demo.sh --warm`

### Tài khoản demo

Tất cả tài khoản dùng mật khẩu `demo`.

| Username | Password | Role | Trang đầu sau login |
|---|---|---|---|
| `applicant_demo` | demo | applicant (công dân) | /portal |
| `dsg_demo` | demo | DSG officer | /dashboard |
| `leader_demo` | demo | leader | /dashboard |
| `legal_demo` | demo | legal advisor | /inbox |
| `security_demo` | demo | security officer | /security |
| `admin_demo` | demo | admin | /dashboard |

> Tài khoản hiện có trong seed data cũng bao gồm: `admin`, `ld_phong`, `cv_qldt`, `staff_intake`, `legal_expert`, `security_officer`, `citizen_demo` (mật khẩu `demo`).

### Chạy 6 demo scenarios

```bash
python scripts/demo/scenario_1_cpxd_gap.py          # CPXD: thiếu PCCC → gap → ND 136/2020
python scripts/demo/scenario_2_permission_demo.py   # 3-tier permission: từ chối truy cập
python scripts/demo/scenario_3_realtime_trace.py    # Agent trace theo thời gian thực
python scripts/demo/scenario_4_leadership.py        # Leadership dashboard + inbox
python scripts/demo/scenario_5_elevation.py         # Security elevation (CONFIDENTIAL → SECRET)
python scripts/demo/scenario_6_internal_dispatch.py # Nội bộ: công văn phối hợp PCCC
```

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 15)                                             │
│                                                                    │
│  /portal          Citizen Portal (no auth)                         │
│  /submit/[code]   Multi-step TTHC form                             │
│  /track/[id]      Public case status                               │
│  /dashboard       Analytics dashboard (staff)                      │
│  /intake          Document intake + review                         │
│  /compliance/[id] Compliance workspace + gap viewer                │
│  /trace/[id]      Agent Trace Viewer (React Flow + WS)             │
│  /inbox           Department inbox + leadership                    │
│  /documents       NĐ 30/2020 document viewer                       │
│  /security        Security Console + audit log                     │
└───────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS + WSS
┌───────────────────────────▼────────────────────────────────────────┐
│  API GATEWAY (FastAPI)                                             │
│                                                                    │
│  Middleware: JWT → ClearanceCheck → RateLimit → OTel → Sentry     │
│                                                                    │
│  /auth/login   /cases   /documents/{id}   /api/ws (WebSocket)     │
│  /api/agents/trace   /graph   /search   /leadership   /audit      │
│  /public   /metrics   /api/dsr   /healthz                         │
└─────────────┬──────────────────────┬───────────────────┬──────────┘
              │                      │                   │
┌─────────────▼──────┐  ┌────────────▼──────────┐  ┌────▼──────────┐
│  AGENT RUNTIME     │  │  PERMISSION ENGINE    │  │  NOTIFY SVC   │
│                    │  │                       │  │               │
│  Orchestrator      │  │  Tier 1: SDK Guard    │  │  WS push      │
│  (DAG executor)    │  │  Tier 2: GDB RBAC     │  │  Email hook   │
│  10 agents         │  │  Tier 3: PropMask     │  │               │
│  MCP tool registry │  │  AuditEvent writer    │  │               │
│  LLM cache         │  │  PermittedClient      │  │               │
└─────────────┬──────┘  └────────────┬──────────┘  └───────────────┘
              │                      │
┌─────────────▼──────────────────────▼───────────────────────────────┐
│  DATA LAYER (Alibaba Cloud)                                        │
│                                                                    │
│  GDB (Gremlin/TinkerPop 3.7)    Hologres (PG + Proxima)  OSS      │
│  ├── Knowledge Graph            ├── users + JWT store    ├── PDFs  │
│  │   ├── 15 core laws           ├── law_chunks (vec)     ├── Drafts│
│  │   ├── 5 TTHC specs           ├── analytics_cases      └── Tmpls │
│  │   └── 10.7k vertices         ├── audit projection               │
│  └── Context Graph              └── notifications                  │
│      ├── per-case state                                            │
│      └── AuditEvent log                                            │
└─────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────────────┐
│  AI LAYER (Qwen3 via DashScope — OpenAI-compatible API)             │
│                                                                     │
│  Qwen3-Max (qwen-max-latest)        Reasoning, agents, MCP tools   │
│  Qwen3-VL-Plus (qwen-vl-max-latest) OCR, layout, stamp detection   │
│  Qwen3-Embedding v3                 Semantic search, RAG recall     │
└─────────────────────────────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────────────┐
│  OBSERVABILITY                                                      │
│                                                                     │
│  OpenTelemetry → Jaeger/Grafana Tempo   (distributed traces)        │
│  Prometheus → Grafana                   (metrics + dashboards)      │
│  Sentry (BE + FE)                       (error tracking)            │
│  Audit → GDB + Hologres                 (forensic audit trail)      │
└─────────────────────────────────────────────────────────────────────┘
```

### Citizen TTHC flow (NĐ 61/2018 — 6 bước)

```
Citizen Portal  →  POST /cases  →  Orchestrator.run()
→ Planner (DAG)  →  DocAnalyzer (OCR / Qwen3-VL)
→ Classifier (TTHC code)  →  SecurityOfficer (4-level classification)
→ Compliance (gap detect)  →  LegalLookup (GraphRAG + citation)
→ Router (department)  →  Consult (xin ý kiến liên phòng)
→ Summarizer (role-aware)  →  Drafter (NĐ 30/2020 output)
→ Leader review gate  →  PublishedDoc  →  WebSocket notify  →  Citizen track
```

### Internal Dispatch flow (PIPELINE_DISPATCH)

```
Staff uploads công văn  →  POST /cases {case_type: internal_dispatch}
→  DispatchRouterAgent  →  classify department + priority
→  Summarizer (executive brief)  →  Drafter (phiếu trình NĐ 30/2020)
→  Leader inbox notification (WebSocket)
```

---

## 10 Agents

| # | Tên | Model | Vai trò | File |
|---|---|---|---|---|
| 1 | Planner | qwen-max | Sinh DAG nhiệm vụ | planner.py |
| 2 | DocAnalyzer | qwen-vl-max | OCR + trích entity | doc_analyzer.py |
| 3 | Classifier | qwen-max | Phân loại TTHC / chủ đề công văn | classifier.py |
| 4 | Compliance | qwen-max | Phát hiện gap + trích dẫn luật | compliance.py |
| 5 | LegalLookup | qwen-max + embedding-v3 | GraphRAG đa-hop | legal_lookup.py |
| 6 | Router | qwen-max | Phân công phòng ban | router.py |
| 7 | Consult | qwen-max | Xin ý kiến chuyên môn | consult.py |
| 8 | Summarizer | qwen-max | Tóm tắt theo vai trò | summarizer.py |
| 9 | Drafter | qwen-max | Soạn văn bản NĐ 30/2020 | drafter.py |
| 10 | SecurityOfficer | qwen-max | Phân loại 4 mức bảo mật | security_officer.py |
| + | DispatchRouter | qwen-max | Phân phối công văn nội bộ | dispatch_router.py |

**Agent phụ trợ:** `AssistantAgent` (citizen chatbot), `IntakeAgent` (hỗ trợ tiếp nhận một cửa).

---

## 3-Tier Permission Engine

Mỗi trong số 47 GDB calls đều đi qua `PermittedGremlinClient`.

```
Agent / User request
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  TIER 1 — Agent SDK Guard                             │
│  Parse Gremlin bytecode AST.                          │
│  Reject nếu agent đọc/ghi label ngoài AgentProfile.  │
│  Ví dụ: Compliance KHÔNG được đọc 'User' label.      │
│  Cost: thấp (regex + AST parse, không cần DB call).  │
└───────────────────────────┬───────────────────────────┘
                            │  Pass
                            ▼
┌───────────────────────────────────────────────────────┐
│  TIER 2 — GDB Native RBAC                             │
│  Mỗi agent có DB user riêng với GRANT cụ thể.        │
│  GDB engine từ chối ở tầng DB nếu thiếu quyền.      │
│  Bắt bypass SDK Guard và Gremlin injection attempt.  │
│  Cost: zero (DB engine native enforcement).          │
└───────────────────────────┬───────────────────────────┘
                            │  Pass
                            ▼
┌───────────────────────────────────────────────────────┐
│  TIER 3 — Property Mask Middleware                    │
│  Post-query redaction theo clearance level.          │
│  national_id → "***" cho clearance < SECRET.         │
│  phone, address → masked cho public_viewer.          │
│  Bắt authorized query trả về unauthorized property. │
│  Cost: thấp (dict traversal per result row).         │
└───────────────────────────────────────────────────────┘
                            │
                            ▼
                   AuditEvent written
          (mọi query đều có forensic audit trail)
```

**23 negative test scenarios** tại `backend/tests/test_permission_negative.py` — 100% pass rate required.

---

## 4-Level Classification (Luật BVBMNN 2018)

Per Luật Bảo vệ Bí mật Nhà nước 2018, Điều 8.

| Cấp độ | Enum | Màu | Điều luật | SecurityOfficer hành động |
|---|---|---|---|---|
| UNCLASSIFIED (Không mật) | 0 | green | Không thuộc bí mật nhà nước | Cho phép public viewer |
| CONFIDENTIAL (Mật) | 1 | yellow | Điều 8 Luật BVBMNN 2018 | Chặn public_viewer; officer+ |
| SECRET (Tối mật) | 2 | orange | Điều 8 Luật BVBMNN 2018 | Chỉ SECRET+ clearance |
| TOP_SECRET (Tuyệt mật) | 3 | red | Điều 8 Luật BVBMNN 2018 | Chỉ admin + security_officer |

---

## PDF Public Sector Track — 8 Future-State Capabilities

| Capability (theo đề bài) | GovFlow Feature | Agent / API |
|---|---|---|
| Tự động tiếp nhận hồ sơ điện tử | Citizen Portal multi-step form, DocAnalyzer OCR | POST /cases, DocAnalyzer |
| Phân loại + định tuyến tự động | TTHC Classifier + Router agent | Classifier, Router |
| Kiểm tra thành phần hồ sơ | Compliance gap detection + TTHCSpec | Compliance + LegalLookup |
| Tra cứu pháp luật thông minh | Agentic GraphRAG (10.7k vertices, 869 law chunks) | LegalLookup + GDB |
| Sinh văn bản trả lời tự động | Drafter (NĐ 30/2020 9-component format) | Drafter |
| Theo dõi tiến độ thời gian thực | Agent Trace Viewer + WebSocket push | /api/ws + /trace screen |
| Kiểm soát bảo mật đa cấp | 3-tier permission + 4-level classification + AuditEvent | SDK Guard + RBAC + PropMask |
| Phân tích, báo cáo lãnh đạo | Leadership Dashboard + Executive Summary | Summarizer + /leadership |

---

## Tech Stack

| Layer | Technology | Mục đích |
|---|---|---|
| Frontend | Next.js 15 (App Router, TypeScript) | 8 screens + Citizen Portal |
| UI | shadcn/ui + Tailwind CSS v4 + Framer Motion + React Flow | Design system + graph viz |
| Backend | Python FastAPI + pydantic v2 | REST + WebSocket API |
| Graph DB | Alibaba Cloud GDB (Gremlin / TinkerPop 3.7) | Knowledge Graph + Context Graph |
| Relational + Vector | Alibaba Cloud Hologres (PG-compat + Proxima) | Users, analytics, law embeddings |
| Blob Storage | Alibaba Cloud OSS (S3-compatible, SSE-KMS) | Documents, templates, archives |
| AI Models | Qwen3-Max, Qwen3-VL-Plus, Qwen3-Embedding v3 | Reasoning, OCR, embeddings |
| AI Gateway | Alibaba Cloud Model Studio (DashScope) | OpenAI-compatible API |
| Agent Protocol | MCP (Model Context Protocol) | Tool exposure to agents |
| Auth | Argon2id + JWT HS256 (clearance claims) | Authentication + authorization |
| Observability | OTel + Prometheus + Grafana + Sentry | Metrics, traces, error tracking |
| CI/CD | GitHub Actions + Docker + K8s (ACK) | Build, test, deploy |

---

## Testing

```bash
# Backend (280 passing)
cd backend
pip install -e ".[dev]"
pytest tests/ -q

# By category
pytest tests/ -m "unit" -v
pytest tests/ -m "e2e" -v
pytest tests/ -m "permission" -v
pytest tests/ -m "agent" -v

# Frontend E2E (Playwright)
cd frontend
npx playwright test

# Smoke test (post start_demo.sh)
./scripts/smoke_test.sh
```

### Accuracy targets

| Metric | Target | Measurement |
|---|---|---|
| TTHC classification | > 80% | 5 inputs per TTHC, correct code returned |
| Compliance gap detection | > 90% | Known gaps detected vs missed |
| Legal citation accuracy | > 85% | Correct article + clause referenced |
| Demo reliability | 100% | 5/5 consecutive runs pass |
| Permission denial accuracy | 100% | All 23 negative scenarios reject correctly |

---

## Production Deployment

See [docs/PRODUCTION.md](docs/PRODUCTION.md) for the full step-by-step Alibaba Cloud ACK deployment runbook.

Related:
- `docs/07-operations/disaster-recovery.md` — DR runbook
- `infra/k8s/` — 9 Kubernetes manifests (HPA, PDB, Ingress)
- `.github/workflows/` — CI + E2E + deploy workflows

**Quick summary:**
1. Provision ACK, GDB, Hologres, OSS, KMS, Model Studio
2. `kubectl create secret generic govflow-secrets --from-env-file=.env.prod`
3. GitHub Actions `deploy-prod.yml` builds + pushes images
4. `kubectl apply -f infra/k8s/`
5. `kubectl rollout status deployment/govflow-backend`
6. Smoke test: `curl http://<lb>/healthz && python scripts/demo/scenario_1_cpxd_gap.py`

---

## Documentation

| Directory | Content |
|---|---|
| `docs/03-architecture/` | Technical specs: agents, permissions, data model, GraphRAG, MCP |
| `docs/04-ux/` | Design system, screen catalog, graph visualization, realtime |
| `docs/06-compliance/` | Vietnamese legal framework mapping (NĐ 61, NĐ 30, Luật BVBMNN) |
| `docs/07-operations/` | DR runbook, alert playbook, retention |
| `docs/PRODUCTION.md` | Production deployment runbook |
| `docs/devpost-submission.md` | Devpost submission writeup |

---

## Demo Video

[PLACEHOLDER — link will be added before submission]

See `demo/video-link.txt` for YouTube/Loom URL once recorded.

---

## Devpost

[PLACEHOLDER — Devpost submission URL after 2026-04-17]

---

## Security & Compliance

| Văn bản pháp luật | Điều khoản | GovFlow Implementation |
|---|---|---|
| NĐ 61/2018/NĐ-CP | Điều 6–8 | 6-step TTHC pipeline |
| NĐ 107/2021/NĐ-CP | Điều 1 | API + Citizen Portal |
| **NĐ 30/2020/NĐ-CP** | Điều 8 + Phụ lục | Drafter (9 components) |
| **Luật BVBMNN 2018** | Điều 3, 8, 11–13 | SecurityOfficer + ClearanceLevel |
| Luật BVDLCN 2023 + **NĐ 13/2023** | Điều 4, 11–15 | DSR endpoints + PropertyMask |
| Luật ANM 2018 + NĐ 53/2022 | Điều 26 | On-prem Qwen3 path (PAI-EAS) |
| NĐ 45/2020/NĐ-CP | Điều 3, 4 | Electronic document handling |

### Security hardening (Wave 0)

- Argon2id password hashing
- JWT revocation (blacklist in Postgres, checked per request)
- SSRF protection — OSS URL allowlist, block localhost in cloud mode
- CSP + HSTS headers on all responses
- Gremlin injection prevention via SDK Guard AST parsing
- STS + SSE-KMS for OSS (short-lived credentials + server-side encryption)
- File upload validation (python-magic MIME check, not just extension)
- Rate limiting (slowapi, Redis-backed in production)

---

## Troubleshooting

**DashScope auth failed:**
```
# Ensure international endpoint in backend/.env:
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

**Port conflict (Docker):**
GovFlow ports: `3100` (frontend) `8100` (backend) `5433` (postgres) `8182` (gremlin) `9100/9101` (minio).
```bash
docker compose -f infra/docker-compose.yml down
```

**Gremlin connection refused:**
```bash
docker ps | grep govflow-gremlin
docker logs govflow-gremlin
docker restart govflow-gremlin
```

**JWT_SECRET weak (cloud mode):**
```bash
export JWT_SECRET=$(openssl rand -hex 32)
```

**Agents not running (DEMO_MODE):**
```bash
DEMO_MODE=false DEMO_CACHE_ENABLED=false ./scripts/start_demo.sh
```

---

## Roadmap

- **Mobile app** — React Native / Flutter cho công dân nộp hồ sơ qua điện thoại
- **SMS + Zalo notifications** — Zalo OA + SMS gateway cập nhật tiến độ
- **VNeID deep integration** — Đề án 06 digital identity API
- **Federated Knowledge Graph** — Liên kết KG giữa các Sở/Bộ
- **Qwen3 on-prem (PAI-EAS)** — NĐ 53/2022 compliant, Qwen3-32B tại Việt Nam
- **Predictive SLA** — Dự đoán hồ sơ trễ hạn 3 ngày trước
- **Multi-tenant** — Mỗi Sở/UBND là tenant riêng với KG riêng

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) file.

---

## Team

[PLACEHOLDER — Add team member names and roles]

---

## Acknowledgments

- **Alibaba Cloud Qwen Team** — Qwen3 models (Max, VL-Plus, Embedding v3) và DashScope API
- **Alibaba Cloud** — GDB, Hologres, OSS, KMS, ACK, PAI-EAS
- **Qwen AI Build Day 2026 Organizers** — Public Sector Track challenge
- **TinkerPop / Apache Gremlin** — Graph traversal language
- **Vietnamese legal data** — thuvienphapluat.vn, vbpl.vn, dichvucong.gov.vn

---

> Built with Qwen3-Max + Qwen3-VL-Plus + Qwen3-Embedding v3 via Alibaba Cloud Model Studio
> Alibaba Cloud GDB + Hologres + OSS + KMS + ACK | FastAPI + Next.js 15 + pytest + Playwright
