# Field Research Notes

Raw observations + findings from initial research phase (pre-hackathon).

## On Vietnamese TTHC painpoint

### Observation 1 — "Ngâm hồ sơ" là ngôn ngữ phổ thông

Vietnamese citizens + businesses use the term "ngâm hồ sơ" (literally "marinate the file") to describe when a case sits with a department for too long. This is slang that captures a cultural understanding: it's not always corruption, but the feeling is the same — opaque, delayed, out of your hands.

**Implication for GovFlow:**
- Citizen Portal must have clear "where is my file" at all times
- SLA countdown + auto-escalation addresses this painpoint directly
- Transparency IS the product

### Observation 2 — "Đi cửa sau" vs digital

Many citizens believe having "quan hệ" (connections) is the only way to get things done. Digital portals are distrusted: "trên giấy là gì, thực tế khác."

**Implication:**
- Building trust requires visible transparency, not claimed transparency
- Audit trail + forensic replay addresses "thực tế" concern
- Citizen Portal should visually show "no shortcuts, all documented"

### Observation 3 — "Đi lại nhiều lần" là chuyện bình thường

Business owners accept 3-5 trips per case as normal. Some even plan entire days for TTHC errands.

**Implication:**
- "Zero extra trips" is a genuinely surprising value prop
- Citizen Portal pre-check is the lever
- Demo Scene 4 (Anh Minh gets notification) is the emotional core

### Observation 4 — Civil servants are also frustrated

Not all civil servants are corrupt — many are overworked and constrained by broken systems. They don't want to process cases slowly — they physically can't keep up.

**Implication:**
- Message to civil servants: "GovFlow makes your job easier"
- Chuyên viên workspace (Compliance Workspace) should feel like a helpful tool, not surveillance
- Key metrics are throughput + compliance + job satisfaction

### Observation 5 — Leadership cares about SLA reporting

Sở leaders are under pressure from UBND tỉnh + Bộ chủ quản to meet SLA. They get monthly reports on violations.

**Implication:**
- Leadership Dashboard must export NĐ 61 compliance reports in one click
- SLA heatmap per TTHC is the must-have widget
- Auto-escalation of at-risk cases

## On Vietnamese legal corpus

### Observation 6 — Luật thay đổi liên tục

Every year sees dozens of new nghị định, thông tư. Keeping up is a full-time job.

**Implication:**
- Law update pipeline is critical for production
- KG versioning (AMENDED_BY, SUPERSEDED_BY) is must-have
- LegalLookup must filter by effective date

### Observation 7 — Cross-references are the norm

Law A refers to NĐ B which refers to TT C which supersedes QD D. Following these chains manually is extremely time-consuming.

**Implication:**
- Graph structure is perfect for this
- Compliance agent must traverse chains automatically
- This is a genuine technical moat

### Observation 8 — Vietnamese law uses specific terminology

"Điều", "Khoản", "Điểm", "Mục" — these are structural elements that matter. "Căn cứ vào Điều 41 Khoản 2 Điểm b NĐ 15/2021" is a precise citation that GovFlow must get right.

**Implication:**
- Citation agent must output this structure exactly
- Drafter agent must cite correctly
- Can't use generic "according to the regulation"

## On Alibaba Cloud ecosystem in Vietnam

### Observation 9 — Alibaba Cloud VN presence growing

Alibaba Cloud has active presence in Vietnam with:
- Solutions architects on the ground
- Regional marketing events (Alibaba Cloud Day HCMC)
- Partnership programs
- Government outreach

**Implication:**
- GovFlow alignment with Alibaba Cloud = alignment with their VN strategy
- Post-hackathon partnership is feasible
- Marketplace listing is realistic near-term

### Observation 10 — Qwen adoption lagging in VN

Despite Qwen's capabilities, adoption in VN lags behind OpenAI/Gemini due to:
- Brand familiarity (OpenAI is household name)
- Marketing presence
- Developer community

**Implication:**
- GovFlow becomes a case study for Alibaba/Qwen adoption in VN
- Both Alibaba and GovFlow win from partnership
- First-mover advantage on Qwen-based gov tech

## On Shinhan InnoBoost program

### Observation 11 — InnoBoost focuses on scaled commercialization

Shinhan's InnoBoost is designed for startups with commercial viability, not just tech demos. They want:
- Clear path to paying customers
- Proof of traction
- Scalable unit economics

**Implication:**
- GovFlow pitch must emphasize business case + GTM
- PoC proposal must have clear success metrics
- Commercial roadmap is as important as technical

### Observation 12 — Shinhan has B2G banking

Shinhan's Vietnam bank serves government contracts, state enterprises. They have relationships.

**Implication:**
- GovFlow can leverage Shinhan's gov network
- Win-win: Shinhan gets gov-tech portfolio addition, GovFlow gets customer intros

## On hackathon dynamics

### Observation 13 — Most teams will build pipeline AI

Most hackathon AI projects follow the standard pattern: upload → OCR → classify → route → summarize. Linear pipelines with 1-3 LLM calls.

**Implication:**
- GovFlow's graph-native approach stands out
- 10 agents + 3-tier permissions is unique
- Must highlight this differentiation prominently

### Observation 14 — Demo polish beats feature count

Hackathon judges consistently prefer polished demo of fewer features over broad shallow demos.

**Implication:**
- Focus on 5 TTHCs executed well, not 20 TTHCs shallow
- UI polish matters more than backend completeness
- Demo video quality is critical

### Observation 15 — Story matters as much as tech

Judges remember "anh Minh's story" more than architecture diagrams. Emotional narrative anchors technical claims.

**Implication:**
- Pitch structure: story → problem → tech → demo → story → ask
- Persona-driven narration throughout
- Demo video framed around specific user

## On competitive landscape

### Observation 16 — FPT is slow

FPT IS is a 20-year-old IT services company with deep gov relationships but slow product evolution. Their AI products are add-ons to legacy DMS, not graph-native platforms.

**Implication:**
- 12-18 month window before they could react
- Focus on speed of deployment
- Build reference customers fast

### Observation 17 — Viettel has AI capability but different focus

Viettel AI focuses on contact center automation + chatbots, not document intelligence. Their agent tech is more about customer service.

**Implication:**
- Not direct competition
- Potential partner for national rollout (they have gov access)

### Observation 18 — VNPT runs portals but not intelligence

VNPT iGate is the portal infrastructure for many Cổng DVC deployments but they don't do the AI brain.

**Implication:**
- GovFlow could be VNPT's AI partner
- Integration via API makes sense

## Unanswered questions (need follow-up)

1. Can Shinhan InnoBoost actually provide intros to Sở customers?
2. What's the actual procurement timeline at a Sở?
3. Does Alibaba Cloud GDB enterprise tier include label-level ACL?
4. What's the realistic pricing a Sở IT department would approve?
5. How do existing gov AI vendors handle data residency today?
6. Is there precedent for on-prem Qwen3 deployment in Vietnamese gov?

These questions can't be fully answered pre-hackathon. They'll become concrete during PoC phase.

## Data Sources — Pre-crawled Datasets (collected 12/04/2026)

### Legal Corpus (cho Knowledge Graph)

| Source | URL | Mô tả | Status |
|---|---|---|---|
| **th1nhng0/vietnamese-legal-documents** | https://huggingface.co/datasets/th1nhng0/vietnamese-legal-documents | Crawl từ vbpl.vn — full-text Luật/NĐ/TT + metadata + cross-document relationships (amended_by, superseded_by, repealed_by, citations). Format: Parquet/JSON. **Primary source cho KG.** | ⏳ downloading |
| **VLSP2025-LegalSML/legal-pretrain** | https://huggingface.co/datasets/VLSP2025-LegalSML/legal-pretrain | VLSP 2025 shared task corpus — preprocessed Vietnamese legal texts. Đặc biệt: VLSP đã pretrain **Qwen3-1.7B và Qwen3-4B** trên corpus này. | ⏳ pending |
| **NguyenNamUET/laws_project_crawler** | https://github.com/NguyenNamUET/laws_project_crawler | Scrapy crawler cho vbpl.vn + thuvienphapluat.vn → JSON + Postgres/ES import. Cũ (2022) nhưng useful nếu cần crawl bổ sung. | 📎 reference |

### Vietnamese OCR/Document Datasets (cho DocAnalyzer — DEFERRED)

| Source | URL | Mô tả |
|---|---|---|
| **5CD-AI/Viet-OCR-VQA** | https://huggingface.co/datasets/5CD-AI/Viet-OCR-VQA | 137k Vietnamese OCR images, 822k QA pairs |
| **5CD-AI/Viet-Doc-VQA-II** | https://huggingface.co/datasets/5CD-AI/Viet-Doc-VQA-II | 64,765 trang sách giáo khoa VN, diverse layout |
| **5CD-AI/Viet-Receipt-VQA** | https://huggingface.co/datasets/5CD-AI/Viet-Receipt-VQA | 2,034 hoá đơn VN — gần format mẫu đơn hành chính |
| **5CD-AI/Vintern-1B-v2** | https://huggingface.co/5CD-AI/Vintern-1B-v2 | Qwen-based Vietnamese multimodal model — potential baseline cho DocAnalyzer |
| **thelong0705/vietnamese-id-card-ocr** | https://github.com/thelong0705/vietnamese-id-card-ocr | CCCD/CMND OCR + sample images |
| **henryle97/IDCard-OCR** | https://github.com/henryle97/IDCard-OCR | Centernet + Seq2Seq OCR cho CCCD |

### Reference Data

| Source | URL | Mô tả | Status |
|---|---|---|---|
| **thanglequoc/vietnamese-provinces-database** | https://github.com/thanglequoc/vietnamese-provinces-database | 63 tỉnh/thành, 3,321 phường/xã, SQL+JSON. Dùng cho address normalization. | ✅ cloned |
| **thuvienphapluat.vn/bieumau** | https://thuvienphapluat.vn/bieumau | Bulk mẫu đơn Word/Excel — cần crawl thủ công hoặc dùng crawl4ai | 📎 reference |

### TTHC Specs (5 flagship)

Curated từ docs + dichvucong.gov.vn (không có public JSON API nên parse thủ công).
- Output: `data/tthc_specs/{code}.json` — 5 files
- KG data: `data/tthc_specs/kg_vertices.jsonl` (37 vertices) + `kg_edges.jsonl` (84 edges)
- Status: ✅ done

### Ingest Scripts

| Script | Mô tả | Status |
|---|---|---|
| `scripts/ingest_legal.py` | Parse HF legal corpus → KG vertices/edges + law_chunks cho Hologres | ✅ run thành công |
| `scripts/ingest_tthc.py` | 5 TTHC specs → KG vertices/edges | ✅ run thành công |

### Quality Report (12/04/2026)

**Legal Corpus Ingest Results:**

| Metric | Target (docs) | Actual | |
|---|---|---|---|
| Total vertices | ~700 | **10,688** | 15x target |
| Total edges | ~2,000 | **104,476** | 52x target |
| Articles (Điều) | ~500 | **861** | parsed từ 15 core laws |
| Clauses (Khoản) | — | **3,660** | |
| Points (Điểm) | — | **4,089** | |
| Law chunks for Hologres | — | **869** | ready for embedding |
| Core laws found | 15 | **15/15** | 100% |
| Document types | Law 61, Decree 176, Circular 266, Decision 1163, Resolution 409 | | |
| Edge types | BASED_ON 86k, SUPERSEDED_BY 2k, AMENDED_BY 2k, REFERENCES 1.7k | | |

**Verified quality:** Điều 95 Luật XD (hồ sơ GPXD) parse đúng; cross-references intact (QĐ UBND → Luật XD); law chunks chứa tiếng Việt chuẩn xác.

**TTHC Ingest Results:**

| Metric | Actual |
|---|---|
| TTHCSpec vertices | 5 |
| RequiredComponent vertices | 27 |
| REQUIRES edges | 27 |
| GOVERNED_BY edges | 52 |

**Combined KG totals (legal + TTHC):**
- Vertices: 10,688 + 37 = **10,725**
- Edges: 104,476 + 84 = **104,560**
- Chunks for Hologres: **869**

## Action items from research

- [x] ~~Collect 5 real sample TTHC documents per flagship~~ → curated specs in `data/tthc_specs/`
- [ ] Verify Alibaba Cloud GDB pricing + capability
- [ ] Verify Hologres AI Functions working as advertised
- [ ] Draft Shinhan InnoBoost application
- [ ] Reach out to 1-2 potential Sở customer contacts (low-key exploratory)
- [ ] Join Alibaba Cloud developer community (for quick help during build)
- [ ] Run `scripts/ingest_legal.py` after HF download completes
- [ ] Download VLSP2025 legal-pretrain corpus for Qwen3 warm-start
- [ ] Propose sample document strategy after KG shape is finalized

## Personal insights (founder reflection)

[This section to be filled by founder based on own observations + prior gov tech experience]

Things to add:
- Why this problem matters personally
- Why this team is right for this
- What drives us beyond the money
- Long-term vision for Vietnamese gov tech

These personal notes fuel the pitch emotional core.
