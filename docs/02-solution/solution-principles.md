# Solution Principles — 10 nguyên tắc dẫn dắt build

Khi bí, quay về đây. Mọi quyết định technical + UX + business phải tham chiếu ngược về 10 nguyên tắc này.

## 1. Graph-first, not pipeline-first

**Rule:** Mỗi khi phân vân "làm sao pass data giữa 2 agent?", câu trả lời mặc định là "ghi vào Context Graph, agent kia đọc ra". Không JSON blob. Không function return tuple.

**Why:** Single source of truth. Không state coordination bugs. Reasoning trace free.

**Counter-example:** Nếu anh viết `result = classifier.run(doc); router.run(result)` — sai. Phải là `classifier.run(case_id)` ghi vào graph, `router.run(case_id)` đọc từ graph.

## 2. Qwen is the brain, graph is the memory

**Rule:** Qwen3 làm reasoning; GDB giữ state + fact. Không lưu state trong agent memory — mất transparency.

**Why:** Cân bằng giữa "LLM suy nghĩ" và "audit trail đầy đủ". Khi audit, mọi thứ đều ở graph.

**Counter-example:** Agent giữ Python dict `self.known_gaps = [...]` — sai. Phải `g.V().has('Case', 'id', case_id).out('HAS_GAP')` khi cần.

## 3. Everything is auditable, nothing is implicit

**Rule:** Mọi agent action sinh `AgentStep` node. Mọi read/write sinh `AuditEvent`. Không có "silent" side effect.

**Why:** Hành chính công cần traceability. Khi có khiếu nại → có thể reconstruct.

**Counter-example:** Agent silently gọi 1 util function mà không log. Sai — mọi call phải qua instrumented wrapper.

## 4. Permissions enforced 3 tầng, không 1

**Rule:** Defense in depth. Mỗi operation phải đi qua (1) SDK Guard → (2) GDB native RBAC → (3) Property Mask.

**Why:** Defence-in-depth. Nếu 1 tầng có hole, 2 tầng còn lại catch.

**Counter-example:** "SDK Guard đủ rồi, khỏi cần GDB RBAC" — sai. Agent có thể bị prompt inject để bypass SDK Guard, GDB privilege phải reject.

## 5. Human-in-the-loop tại mọi điểm quyết định cuối

**Rule:** Agent *sinh đề xuất*, không *phát hành*. Drafter → human → publish. Decision → human → approved. Classification → human review possible.

**Why:** Cán bộ nhà nước phải chịu trách nhiệm pháp lý. AI không thay thế trách nhiệm.

**Counter-example:** Drafter auto-publish giấy phép XD — sai. Phải có "Human Review" gate ở mọi output citizen-facing.

## 6. Vietnamese-context-first, không bê Âu-Mỹ

**Rule:** Taxonomy TTHC theo Cổng DVC Quốc gia. VB output theo NĐ 30/2020. Compliance theo NĐ 61. Không dùng terminology Mỹ.

**Why:** Problem Relevance = "hiểu đúng context Việt Nam". Judge VN sẽ thấy sự khác biệt.

**Counter-example:** Gọi là "Administrative Procedure" mà không là "Thủ tục hành chính công" — ok cho audience quốc tế nhưng VN context phải chuẩn.

## 7. Traceability pháp lý là feature, không phải log

**Rule:** Mỗi `Gap` / `Decision` phải có `CITES` edge sang Article node trong KG. Có thể point-and-click từ quyết định về điều luật gốc.

**Why:** Cán bộ nhà nước khi bị hỏi "căn cứ gì?" phải trả lời ngay. Hệ thống giúp họ có câu trả lời sẵn.

**Counter-example:** Compliance agent trả "thiếu PCCC" mà không có cite điều luật — sai. Phải `-[:CITES]->(Article{law_code:'136/2020/ND-CP', num:13})`.

## 8. Alibaba Cloud-first commitment

**Rule:** Không hybrid với stack khác cho storage/AI layer. GDB + Hologres + Model Studio + OSS + ECS.

**Why:** Tối đa điểm "Use of Alibaba Cloud" cho judge Alibaba SA. Story "production stack từ ngày đầu" thuyết phục VC.

**Counter-example:** Dùng Neo4j vì dev loop nhanh hơn — chỉ OK cho local dev. Production path phải GDB từ đầu.

## 9. Realtime where it matters

**Rule:** Citizen tracking, agent trace, security audit, leadership SLA — all realtime qua WebSocket/SSE. Polish bar cao.

**Why:** PDF đòi "Real-time Tracking" (capability 6). Và realtime là thứ demo visible nhất.

**Counter-example:** Status polling 5s — sai. Phải push qua WebSocket khi agent hoàn thành step.

## 10. Simplicity at surface, depth underneath

**Rule:** Citizen Portal phải siêu đơn giản (5 thao tác). Leadership Dashboard chỉ 3 metric lớn. Công nghệ phức tạp ẩn dưới.

**Why:** End user (công dân, lãnh đạo) không care về graph. Họ care về "nộp xong → biết kết quả".

**Counter-example:** Citizen Portal hiện ra "Gremlin query returned 5 vertices" — sai. Hiện "Hồ sơ của bạn đang ở Phòng Quy hoạch, dự kiến hoàn tất ngày 15/04".

---

## Decision framework

Khi phân vân 1 quyết định, check theo thứ tự:

1. **Nguyên tắc nào áp dụng?** (thường có 2–3)
2. **Nếu 2 nguyên tắc xung đột, nguyên tắc nào priority cao hơn?**
   - #4 Security > #9 Realtime (nếu realtime phá security → chọn security)
   - #5 Human-in-loop > #10 Simplicity (nếu simplicity bỏ human review → giữ human review)
   - #7 Legal traceability > mọi thứ (không bao giờ skip cite)
3. **Nếu vẫn phân vân, hỏi team.**

## Anti-patterns to avoid

- **Feature creep** — thêm feature vì "có thể cool" mà không phục vụ 1 trong 10 nguyên tắc → cắt
- **Mock data** — dùng data giả trong demo → sai. Dùng mẫu thật từ dichvucong.gov.vn
- **UI debt** — "làm xấu trước, đẹp sau" → sai. UI phải đẹp từ commit đầu, vì polish không kịp
- **Over-engineering** — 10 agent có thể biến thành 15 nếu không kỷ luật. Dừng lại ở 10.
- **Tech demo không có context** — "Xem này, reasoning trace đẹp chưa!" mà user không biết đang làm gì → sai. Mọi tech demo phải có business context anh Minh / chị Lan.
