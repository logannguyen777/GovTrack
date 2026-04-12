# Differentiation — vs FPT/Viettel/VNPT/Misa và generic AI

## The question judges will ask

*"Khác gì so với FPT.AI / Viettel AI / VNPT / Misa, họ đã làm OCR + DMS cho gov rồi?"*

Đây là câu hỏi kill-or-win. Nếu trả lời mơ hồ → thua ngay. Dưới đây là câu trả lời rõ ràng.

## Head-to-head comparison

| Dimension | FPT.IS AKAMINDS | Viettel AI | VNPT iGate | Misa AMIS | **GovFlow** |
|---|---|---|---|---|---|
| **Primary scope** | Document mgmt (DMS) + OCR | Contact center + AI ops | Cổng DVC frontend | SME suite | **End-to-end TTHC công** |
| **Target user** | Văn thư nội bộ | Call center / công dân | Citizen portal | Doanh nghiệp | **Toàn bộ 6 nhóm stakeholder** |
| **AI foundation** | Computer vision OCR + rules | Tổng hợp (nhiều vendor) | Workflow engine | ERP logic | **Qwen3 agentic + MCP** |
| **Architecture paradigm** | Pipeline + rule engine | Microservices | Portal + BPM | Monolith | **Graph-native multi-agent** |
| **Legal reasoning** | Manual rules | N/A | N/A | N/A | **Agentic GraphRAG với citation** |
| **Multi-level security** | Role-based | Role-based | Role-based | Role-based | **3-tier ABAC-on-graph** |
| **Audit traceability** | DB logs | Logs | Logs | ERP logs | **Immutable subgraph, forensic replay** |
| **Cross-reference pháp luật** | Không | Không | Không | Không | **KG với AMENDED_BY/REFERENCES edges** |
| **Context sharing giữa agent** | N/A | N/A | Workflow state | Process state | **Single Context Graph** |
| **Reasoning transparency** | Black box | Black box | Không có AI reasoning | Không | **Visible agent trace realtime** |
| **Data residency** | On-prem option | On-prem | On-prem | SaaS chính | **On-prem + Qwen open-weight roadmap** |
| **Integration với Cổng DVC** | Tuỳ dự án | Có | Là chính họ | Không gov focus | **OpenAPI compatible** |

## Moat analysis

GovFlow có 5 moat không đội nào khác có thể copy trong 6 ngày:

### Moat 1 — Graph-native architecture
Không phải "add graph DB vào stack", mà là **toàn bộ data model + reasoning + audit là graph**. Build lại cái này mất weeks, không phải days.

### Moat 2 — Vietnamese legal corpus trong KG
5 TTHC full cross-reference + 10 luật cốt lõi trong Neo4j-style graph với AMENDED_BY/SUPERSEDED_BY/REFERENCES edges. Data này chưa ai có sẵn — ai copy phải build lại.

### Moat 3 — Agentic GraphRAG cho legal reasoning
LegalLookup không phải vector RAG đơn thuần. Nó là hybrid: vector recall → graph traversal → cite. Pattern này research 2025–2026 (Neo4j, AGENTiGraph) nhưng chưa được áp dụng TTHC VN.

### Moat 4 — 3-tier agent-level permissions
SDK Guard + GDB native RBAC + property mask — 3 tầng phòng thủ. Không ai khác trong hackathon space nghĩ tới mức "agent có permission" — vì thường dùng 1 LLM call trực tiếp.

### Moat 5 — Vietnamese regulatory depth
9 văn bản pháp luật được map chính xác vào từng feature. Không thể fake — phải hiểu bộ máy.

## Response script cho judge

> *"Em đi thẳng vào câu hỏi này. FPT, Viettel, VNPT, Misa đều có DMS + OCR truyền thống. Họ làm rất tốt cho 1 Sở số hoá văn thư nội bộ. Nhưng họ không giải quyết được câu hỏi trong PDF — đó là **secure, AI-assisted document intelligence** cho toàn bộ TTHC công.*
>
> *GovFlow khác 5 điểm:*
>
> *(1) **Graph-native, không pipeline**. Mọi thứ là đồ thị — Knowledge Graph pháp luật + Context Graph per case. Đây là paradigm 2026 (GraphRAG + Agentic RAG từ Neo4j, arxiv 2508.02999 đạt 95% vs 83% của GPT-4o). Không đội nào khác build kịp trong 6 ngày.*
>
> *(2) **Legal reasoning có cite**. LegalLookup agent dùng vector recall rồi graph traversal qua AMENDED_BY/SUPERSEDED_BY edges để trả về điều luật có hiệu lực chính xác, cite điều/khoản/điểm. Cán bộ mở quyết định của mình, click thẳng về điều luật gốc.*
>
> *(3) **Permission tại mức agent, không chỉ user**. 3 tầng enforcement: SDK Guard parse Gremlin AST, GDB native RBAC, property mask middleware. Demo được 3 scene phân biệt.*
>
> *(4) **Scope là TTHC công end-to-end**, không phải văn thư. Mình có Citizen Portal, 5 TTHC flagship với full cross-reference, compliance check tự động theo NĐ 61.*
>
> *(5) **Full Alibaba Cloud stack từ ngày đầu**. GDB + Hologres + Model Studio + OSS. Không hybrid, không migration story — ngay production path.*
>
> *Đó là lý do tại sao Shinhan InnoBoost nên đầu tư: không phải 'thêm 1 DMS nữa' mà là 'nền tảng OS cho TTHC công Việt Nam'."*

## Generic AI app vs GovFlow

Một số đội hackathon sẽ dùng generic LLM app framework. So sánh:

| Aspect | Generic LLM app | GovFlow |
|---|---|---|
| LLM usage | 1 prompt → output | 10 agents × 8 roles × MCP tools |
| Data model | Docs trong blob | KG + Context Graph |
| State sharing | JSON blobs giữa call | Single Context Graph |
| Reasoning trace | Text log | Graph subgraph visible |
| Permissions | User RBAC | 3-tier ABAC-on-graph |
| Citation | Hallucinate | Grounded Gremlin traversal |
| Compliance | Prompt-based | Graph structure enforced |

## "Build vs buy" framing cho gov customer

Gov client cân nhắc:

**Build internal** — 18 tháng, 5+ engineer, chưa chắc thành công. Không phải core competency.

**Buy FPT/Viettel/VNPT DMS** — 6 tháng deploy, giải quyết 30% painpoint (chỉ phần văn thư), không có agentic reasoning, không có legal citation.

**Buy GovFlow** — 3 tháng PoC, giải quyết 80%+ painpoint end-to-end, built-in legal reasoning, production-grade security, chạy trên Alibaba Cloud.

**Value = 80% vs 30% với cost tương đương + time tới 2× nhanh hơn.**

## Risk acknowledgment

GovFlow mới, chưa có reference. Mitigation:
- Hackathon là reference đầu tiên — "first to market" narrative
- Shinhan InnoBoost PoC = proof point
- Alibaba Cloud backing (infrastructure partner) + academic research backing (GraphRAG papers)

## Bottom line

> GovFlow không phải "DMS cộng AI". Nó là **operating system mới cho TTHC công** — nơi đồ thị pháp luật + đồ thị hồ sơ + đồ thị tổ chức + đồ thị quyền truy cập kết hợp để chạy tự động toàn bộ vòng đời thủ tục, với Qwen3 làm brain và human-in-the-loop ở đúng điểm cần.
