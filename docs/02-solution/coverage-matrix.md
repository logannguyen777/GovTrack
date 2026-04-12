# Coverage Matrix — PDF đòi hỏi gì, GovFlow giải quyết thế nào

Đây là phần rà soát toàn bộ đòi hỏi của đề bài và tự chấm điểm coverage. Judge sẽ dùng các bullet chính xác trong PDF để chấm. Mình phải cover 100%.

## 1. Executive Problem Statement (PDF trang 1) — coverage 3/3

| Problem từ PDF | GovFlow giải quyết | Agent/Component | Coverage |
|---|---|---|---|
| **Processing Delays** — manual, multi-step workflows to classify, route, review, respond → significant delays | Auto classify (Classifier) + route (Router) + review (Compliance) + draft response (Drafter) — cắt 6 bước thủ công thành pipeline graph-native với parallel execution | Planner, Classifier, Router, Compliance, Drafter, Orchestrator | ✅ Full |
| **Fragmented Flow** — limited visibility into document status + inefficient cross-dept coordination | Single Context Graph là source of truth + real-time Agent Trace Viewer + Leadership Dashboard + Consult agent có state machine | Context Graph, Agent Trace Viewer, Leadership Dashboard, Consult Agent | ✅ Full |
| **Security Constraints** — strict security + multi-level classification (Unclassified → Top Secret) | 4 classification levels enforced at every layer (Agent SDK Guard + GDB RBAC + Property Mask) + SecurityOfficer agent tự suy luận độ mật | 3-tier Permission Engine + SecurityOfficer Agent | ✅ Full |

## 2. Key Impact Areas (PDF trang 1) — coverage 3/3

| Impact Area | GovFlow solution | Evidence in demo |
|---|---|---|
| **Citizen Experience** — slower response, reduced service quality | Citizen Portal với real-time tracking, push notifications, pre-check hồ sơ tại nguồn, plain-language explanation khi từ chối, guided wizard. Cắt 1–3 tháng → 1–2 ngày. | Demo Scene 2 & 4: anh Minh nộp hồ sơ + nhận thông báo thiếu ngay + bổ sung không phải đi lại |
| **Compliance Risk** — missed deadlines, regulatory non-compliance, unresolved cases | SLA clock tự động per TTHC, escalation khi gần deadline, Compliance Agent check tất cả điều kiện luật, báo cáo NĐ 61 tự động. | Leadership Dashboard slide + compliance score per case |
| **Cost Efficiency** — increased administrative workload, high operational costs | Auto hoá 80%+ phần thủ công. 1 Sở XD tiết kiệm 300–600k ngày doanh nghiệp × N Sở × 63 tỉnh. | Business case slide |

## 3. 6-Step Manual Workflow (PDF trang 2) — coverage 6/6

| Bước | Hiện tại (manual) | GovFlow (automated + human-in-loop) | Agent owner |
|---|---|---|---|
| **1. Intake** — docs via physical + digital | Cán bộ tiếp nhận thủ công, nhập liệu | Citizen Portal upload trực tiếp, DocAnalyzer (Qwen3-VL) OCR + extract metadata auto | DocAnalyzer |
| **2. Registration** — logged at records unit | Cán bộ đánh máy vào hệ thống một cửa | Classifier auto classify TTHC + sinh mã hồ sơ chuẩn NĐ 30/2020 | Classifier |
| **3. Distribution** — forwarded to depts | Cán bộ chuyển thủ công, dễ sai | Router traverse Org graph → chọn phòng phụ trách + consult targets | Router |
| **4. Review** — content review, scope determination, summarization | Chuyên viên đọc, đối chiếu luật | Compliance Agent check thành phần + điều kiện; LegalLookup cite luật; Summarizer role-aware | Compliance + LegalLookup + Summarizer |
| **5. Consultation** — cross-dept feedback | Gửi công văn xin ý kiến thủ công, 3–7 ngày | Consult Agent auto draft yêu cầu + tổng hợp phản hồi; parallel khi có thể | Consult |
| **6. Response** — final response to citizens | Soạn công văn trả lời thủ công | Drafter sinh VB theo NĐ 30/2020 + plain-language version cho citizen; human review → publish | Drafter |

## 4. Digital Transformation Gaps (PDF trang 2) — coverage 4/4

| Gap | GovFlow addresses |
|---|---|
| Many submissions still delivered in hard copy | Intake UI hỗ trợ camera capture + scan; Qwen3-VL xử lý scan chất lượng kém |
| Document identification numbers not standardized | DocAnalyzer extract + normalize số hiệu; Gremlin Template `normalize_doc_number` |
| Scanned copies vary in quality | Qwen3-VL robust với scan kém + có fallback "cần người duyệt" khi confidence < threshold |
| Hybrid paper-digital workflows | Support cả 2 qua Citizen Portal (digital) + Intake UI (scan giấy) |

## 5. 3 Key Operational Challenges (PDF trang 3) — coverage 3/3

### Challenge 1 — Manual Identification

| Sub-issue | GovFlow solution |
|---|---|
| Time-intensive review | `Classifier` auto match TTHC với taxonomy trong <2s |
| Risk of misrouting | `Router` với confidence threshold → escalate human nếu < 85% |
| Increased backlog | Pipeline parallel + auto → intake không còn là bottleneck |

### Challenge 2 — Cross-Department Consolidation

| Sub-issue | GovFlow solution |
|---|---|
| Duplication of effort | Single Context Graph = single source of truth → không duplication |
| Inconsistent interpretation | LegalLookup đảm bảo tất cả phòng cite cùng 1 điều luật |
| Delayed responses | `Consult` parallel + state machine → cắt 3–7 ngày → vài giờ |

### Challenge 3 — Extended Approval Cycles

| Sub-issue | GovFlow solution |
|---|---|
| Multiple review layers | `Planner` lên plan động, giảm layer thừa |
| Repeated consultations | `Consult` track repetition + đề xuất "tái dùng opinion trước" |
| Limited visibility | Real-time graph visualization = visibility đầy đủ |

## 6. Key Operational Constraints (PDF trang 4) — coverage 4/4

| Constraint | GovFlow addresses | Evidence |
|---|---|---|
| **Physical Document Reliance** — hard copy, scanned copies vary in quality | Qwen3-VL mạnh với scan xấu + stamp/signature detection | Demo scene 2 |
| **Strict Security & Confidentiality** — restricted access, audit logging | 3-tier Permission Engine + immutable `AuditEvent` subgraph | 3-scene permission demo |
| **Multi-Level Document Classification** (4 levels) | `SecurityOfficer` agent tự suy luận cấp mật; classification enforced | Demo scene 7 |
| **Fragmented Systems** — docs across disconnected systems | Single Context Graph là canonical store; OpenAPI với Cổng DVC; VNeID integration | Architecture slide |

## 7. 8 Future-State Capabilities (PDF trang 5) — coverage 8/8

| # | Capability | PDF text | GovFlow implementation | Demo moment |
|---|---|---|---|---|
| 1 | **Automated Ingestion** | Physical & digital document processing | Citizen Portal bulk upload + camera capture; `DocAnalyzer` (Qwen3-VL) OCR + layout + stamp detection | Demo Scene 2: anh Minh upload 5 tài liệu |
| 2 | **Intelligent Classification** | Document type & subject detection | `Classifier` với TTHC taxonomy + subject detection (Qwen3-Max few-shot); grounding vào TTHCSpec vertices trong KG | Scene 3: "TTHC = Cấp phép XD 1.004415" |
| 3 | **Auto-Routing** | Department identification | `Router` traverse Organization subgraph theo thẩm quyền + workload | Scene 5: route tới Sở XD + consult Pháp chế |
| 4 | **AI Summarization** | Key information extraction | `Summarizer` role-aware (executive/staff/citizen), `DocAnalyzer` extract entities; all stored trong Context Graph | Scene 5: lãnh đạo thấy TL;DR 3 dòng + compliance score |
| 5 | **Cross-Dept Collaboration** | Structured workflow | `Consult` agent state machine + Opinion vertices; parallel khi có thể | Scene 5: consult Pháp chế + Quy hoạch tự động |
| 6 | **Real-time Tracking** | Lifecycle status visibility | Context Graph subgraph status + WebSocket stream; Citizen Portal + Leadership Dashboard đều realtime | Xuyên suốt demo; Citizen Portal update live |
| 7 | **Centralized Indexing** | Document retrieval | KG là central index; LegalLookup dùng Hologres Proxima + GDB traversal cho semantic + structural search | Compliance Workspace: related laws + related precedents |
| 8 | **Access Control** | Multi-level security | 3-tier Permission Engine; 4 classification levels; ABAC trên graph | Scene 7 & 3-scene permission demo |

## 8. Innovation Challenge (PDF trang 5) — direct answer

**PDF hỏi:**
> How might public sector organizations implement a secure, AI-assisted document intelligence capability that can automatically classify, summarize, route, and track administrative documents across departments while complying with strict security and confidentiality requirements?

**GovFlow's answer (one paragraph):**
> GovFlow là **graph-native agentic system** chạy hoàn toàn trên Alibaba Cloud (GDB + Hologres + Model Studio + OSS), dùng 10 agent Qwen3 có phân quyền tại mức node/edge của một Knowledge Graph pháp luật Việt Nam + Context Graph động cho mỗi hồ sơ. Hệ thống auto **classify** (Classifier Agent với TTHC taxonomy), **summarize** (role-aware Summarizer), **route** (Router traverse Organization subgraph), **track** (Context Graph là live case file + audit trail) across departments, với security enforced 3-tầng (SDK Guard, GDB native RBAC, Property Mask) tuân thủ Luật Bảo vệ Bí mật Nhà nước, Luật ANM, Luật BVDLCN, NĐ 61/107/45/42/30, và Đề án 06.

## Coverage score tự chấm

| PDF section | Items | Coverage |
|---|---|---|
| Executive Problem Statement | 3 | **3/3 ✅** |
| Key Impact Areas | 3 | **3/3 ✅** |
| 6-Step Workflow | 6 | **6/6 ✅** |
| Digital Transformation Gaps | 4 | **4/4 ✅** |
| 3 Operational Challenges | 3 (9 sub) | **3/3 ✅** |
| 4 Operational Constraints | 4 | **4/4 ✅** |
| 8 Future-State Capabilities | 8 | **8/8 ✅** |
| Innovation Challenge | 1 | **Direct answer ✅** |
| **TOTAL** | **32 items** | **32/32 ✅** |

**Không có gì PDF đòi hỏi mà GovFlow không làm.**

Đây là slide "Problem–Solution Fit" cho pitch + là bằng chứng cho judge về **Problem Relevance** tiêu chí #1.
