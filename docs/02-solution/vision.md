# Vision — GovFlow

## One-sentence pitch

*GovFlow là graph-native agentic system chạy trên Qwen3 + MCP, xây trên Knowledge Graph pháp luật Việt Nam + Context Graph động cho mỗi hồ sơ, với 10 agent có phân quyền tại mức node/edge. Biến toàn bộ vòng đời thủ tục hành chính công — từ lúc công dân nộp hồ sơ đến lúc nhận kết quả — từ hàng tuần/tháng xuống vài phút, bám đúng NĐ 61/2018, 107/2021, 45/2020, 30/2020, Đề án 06, triển khai full Alibaba Cloud stack tuân thủ Luật ANM + BVDLCN + BVBMNN, có reasoning trace minh bạch trực tiếp trên đồ thị.*

## Core reframe

> **Không phải "AI xử lý văn bản"** — mà là **"AI điều hành toàn bộ bộ máy thủ tục hành chính trên một đồ thị sống"**.

Văn bản chỉ là biểu hiện vật lý của TTHC. Cái đau thật là quy trình — nơi 6 bước PDF mô tả (Intake → Registration → Distribution → Review → Consultation → Response) đang chạy bằng tay trên hàng nghìn loại thủ tục, dựa trên mạng lưới phức tạp của luật-nghị định-thông tư-quy trình-phòng ban.

**GovFlow biểu diễn mạng lưới đó bằng Knowledge Graph, xử lý từng hồ sơ bằng Context Graph, và dùng Qwen3 agent để traverse + reason trên cả hai — với human-in-the-loop ở mọi điểm quyết định quan trọng.**

## Why we win — 3 đòn bẩy

### Đòn bẩy #1 (primary) — "Graph-native Agentic AI, not a prompt chain"

Phần lớn đội hackathon sẽ làm **pipeline LangChain tuần tự** (OCR → classify → route → summarize), prompt rời nối nhau. GovFlow khác biệt bằng cách build:

- **Living Knowledge Graph** của pháp luật + TTHC + tổ chức (Law/Article/TTHCSpec/Organization, edges GOVERNED_BY/REQUIRES/AMENDED_BY/REFERENCES). Đây là bộ não dài hạn.
- **Dynamic Context Graph** cho mỗi hồ sơ — mọi agent đọc/ghi vào cùng 1 đồ thị, grow theo runtime, reasoning trace chính là subgraph.
- **Agent-level Permissions** tại mức node/edge property (ABAC-on-graph) — 3 tầng enforcement: SDK guard, GDB native RBAC, property mask middleware. Đây là best practice 2026 nhưng chưa được áp dụng rộng rãi.
- **Qwen3 + MCP** — orchestrator expose graph tools qua Model Context Protocol, Qwen3 sinh Gremlin traversal có kiểm soát để traverse + reason trên Alibaba Cloud GDB.
- **Agentic GraphRAG cho legal reasoning** — `LegalLookup` dùng vector recall + graph traversal để lấy chính xác các điều luật có hiệu lực chi phối 1 case.

**Research backing:** AGENTiGraph paper (arxiv 2508.02999, 2025) đạt **95.12% vs 83.34% zero-shot GPT-4o** cho agentic KG tasks. Neo4j Agentic GraphRAG cho legal contracts. "GraphRAG + MCP là chuẩn mới cho agentic data architecture 2026" (Hyperight).

### Đòn bẩy #2 — "Security as the demo hero"

Ít đội demo access control đa cấp mật một cách thuyết phục. Đề bài nhấn mạnh nhiều nhất ở "strict security", "multi-level classification", "audit logging". GovFlow biến security thành điểm demo với **3 scene distinct**:

- **Scene A — SDK Guard reject** với agent out-of-scope query → parse Gremlin AST → reject + audit
- **Scene B — GDB RBAC** cho cross-agent violation → GDB native privilege reject
- **Scene C — Property Mask live** — user clearance tăng thì mask dissolve gradually

Đây là "wow moment" mà không đội nào khác build kịp trong 6 ngày.

### Đòn bẩy #3 — "Vietnamese public-service-first, compliance-aware"

Ghim vào khung pháp lý TTHC công Việt Nam:
- NĐ 61/2018 + 107/2021 về một cửa liên thông (backbone của 6 bước)
- NĐ 45/2020 + 42/2022 về TTHC điện tử
- NĐ 30/2020 về thể thức văn bản (Drafter tuân thủ)
- Đề án 06 + VNeID (Citizen Portal integrate)
- Luật BVBMNN 2018 (4 cấp mật)
- Luật ANM + NĐ 53/2022 (on-prem option)
- Luật BVDLCN + NĐ 13/2023 (data minimization)

Judge thấy team *hiểu* đúng vùng đau của bộ máy hành chính Việt Nam, không bê giải pháp Âu-Mỹ về → điểm tuyệt đối ở **Problem Relevance**.

## Big picture flow

```
    PUBLIC CITIZEN / BUSINESS
             │
             ▼
    ┌────────────────┐
    │ Citizen Portal │  ← upload bundle, track, notifications
    └────────┬───────┘
             │
             ▼
    ┌────────────────────────────────────────────────────┐
    │           GovFlow Core — 10 Qwen3 Agents           │
    │                                                      │
    │  Planner → DocAnalyzer → Classifier → Compliance   │
    │     ↓          ↓             ↓            ↓         │
    │  LegalLookup → SecurityOfficer → Router            │
    │     ↓              ↓                ↓               │
    │  Consult → Summarizer → Drafter                    │
    │                                                      │
    │  [All read/write on Context Graph through           │
    │   3-tier permission engine]                         │
    └────────────┬───────────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │  Knowledge Graph (GDB)          │
    │  - Vietnam law corpus           │
    │  - TTHC catalog                 │
    │  - Org structure                │
    │  - Templates                    │
    └────────────────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────┐
    │  Human-in-the-loop              │
    │  - Leadership approval          │
    │  - Pháp chế review              │
    │  - Security reclassify          │
    └────────┬───────────────────────┘
             │
             ▼
    ┌────────────────┐
    │ Citizen Portal │  ← result notification, download
    └────────────────┘
```

## What success looks like

**Day 17/04 submission:** working end-to-end trên 5 TTHC flagship, UI 8 màn hình đạt bar "đẳng cấp hàng đầu", 3-scene permission demo, demo video 2:30, full Alibaba Cloud stack live.

**Day 21/04 pitch:** 3-phút (hoặc 5-phút tuỳ slot) pitch hook → problem → solution → demo video → security → impact → ask. Judge hiểu ngay GovFlow là platform khác biệt so với OCR+DMS truyền thống.

**Win condition:**
- Problem Relevance ≥ 9/10 (cover đủ 100% PDF + Vietnamese context)
- Solution Quality ≥ 9/10 (graph-native architecture + UI polished)
- Use of Qwen ≥ 10/10 (8 roles + GraphRAG + MCP)
- Execution ≥ 9/10 (5 TTHC live + 3 wow moments)
- **Total: 37+/40**

**Secondary win:** Shinhan InnoBoost 200M VND PoC funding để pilot 1 Sở trong 3 tháng.
