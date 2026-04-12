# Why Graph-Native — Deep rationale

Tại sao phải dùng graph database + graph-native architecture? Tại sao không dùng relational + vector RAG như 95% team AI khác?

## Short answer

**Vì bản chất bài toán là graph.** Pháp luật Việt Nam là mạng tham chiếu chéo. TTHC là chuỗi phụ thuộc. Tổ chức là cây phân cấp. Case là chuỗi quyết định. Permission là quan hệ. Audit là chain of events. Tất cả đều là quan hệ, không phải bảng.

Khi bản chất là graph, dùng graph = 1× cost, dùng relational = 10× cost (joins + state coordination bugs + query explosion).

## Long answer — 5 lý do

### Lý do 1 — Pháp luật là mạng tham chiếu chéo, không phải bảng

Một ví dụ thực tế: để cấp phép xây dựng cho nhà xưởng 500m², cán bộ phải check:

- Luật XD 2014 Điều 95 (điều kiện cấp phép)
- Luật XD 2014 Điều 95 **đã bị sửa đổi bởi** Luật số 62/2020/QH14
- NĐ 15/2021 Điều 41 (hướng dẫn thành phần hồ sơ)
- NĐ 15/2021 Điều 41 **tham chiếu** Điều 80 (về PCCC)
- NĐ 136/2020 Điều 13 (quy định công trình phải thẩm duyệt PCCC)
- TT 06/2021/TT-BXD (biểu mẫu)
- QĐ địa phương về quy hoạch

**Câu hỏi:** "Cho tôi tất cả các điều luật có hiệu lực hiện tại chi phối hồ sơ CPXD cho nhà xưởng sản xuất tại khu công nghiệp".

**Với relational DB:** cần JOIN ít nhất 4–5 bảng, filter theo ngày hiệu lực, kiểm tra amendment chain — query phức tạp, chậm, dễ sai.

**Với graph DB:**
```groovy
g.V().has('TTHCSpec', 'code', '1.004415')  // CPXD
 .out('GOVERNED_BY')                         // → Articles
 .until(__.not(__.out('SUPERSEDED_BY')))     // chain đến version mới nhất
 .repeat(__.out('SUPERSEDED_BY'))
 .out('REFERENCES').emit()                   // expand cross-refs
 .dedup().valueMap()
```
Một query, 200ms. Không JOIN, không filter manual.

**Graph thắng vì bản chất là quan hệ nhiều hop.**

### Lý do 2 — Multi-agent cần shared state không có race conditions

Khi có 10 agent chạy song song và sequential trên cùng 1 case, state sharing là vấn đề lớn:

**Với JSON blob passing (naive):**
```python
result1 = agent_a.run(doc)          # agent_a trả dict
result2 = agent_b.run(result1)      # agent_b modify dict
result3 = agent_c.run(result2)      # agent_c expect field X trong result2 nhưng bị agent_b xoá
# Race conditions, lost updates, hard to debug
```

**Với Context Graph (GovFlow):**
```python
agent_a.run(case_id)  # writes to graph
agent_b.run(case_id)  # reads from graph, writes more
agent_c.run(case_id)  # reads everything current, writes more
# Single source of truth, ACID per operation, no lost updates
```

Context Graph cho phép 10 agent collaborate mà **không cần orchestrator biết detail của từng agent**. Orchestrator chỉ spawn tasks, agents tự coordinate qua graph. Đây là đặc tính của **blackboard pattern** trong multi-agent systems.

### Lý do 3 — Permission ở mức node/edge, không phải row

Security yêu cầu của gov là **fine-grained at the data element level**:

- Một hồ sơ CPXD ở khu quân sự có property `location.sensitive = true` → chỉ user clearance Confidential+ thấy field này
- Property `applicant.national_id` chỉ SecurityOfficer + DocAnalyzer thấy raw
- Edge `Case -[:HAS_CLASSIFICATION]-> Classification` chỉ SecurityOfficer được write

**Với relational DB:** cần row-level security (RLS) + column-level security (Postgres có) + nhiều check trong application layer → phân tán, khó audit.

**Với graph DB:** policy cũng là graph. Agent → `HAS_PERMISSION` → NodeLabel/EdgeType → with conditions. Evaluate = traversal. Thêm permission = thêm edge, không deploy code.

**Graph thắng vì permission tự nhiên expresses as relationships.**

### Lý do 4 — Audit trail là chuỗi event → graph free

Audit trail yêu cầu:
- Mọi action sinh event
- Event có actor, timestamp, resource, reason
- Có thể replay theo thời gian
- Có thể filter theo user / resource / time window
- Forensic: "tất cả access vào case X trong ngày Y bởi ai?"

**Với relational DB:** bảng `audit_log` + indexes + JOIN với users + resources để có context. OK nhưng clunky cho forensic.

**Với graph DB:** `(Actor)-[:PERFORMED]->(Action)-[:ON]->(Resource)` và `(Action)-[:AT]->(Timestamp)`. Forensic query là traversal. Replay = order by timestamp.

Thêm vào đó, **agent reasoning trace** cũng là graph: `(Case)-[:PROCESSED_BY]->(AgentStep)-[:NEXT]->(AgentStep)`. Audit trail + reasoning trace ở **cùng 1 store** = 1 query để forensic.

### Lý do 5 — Tổ chức nhà nước là hierarchy + network

Cơ cấu nhà nước VN:
- Thủ tướng → Bộ → Cục/Vụ → Phòng → Nhân viên
- Tỉnh → Sở → Phòng → Nhân viên
- UBND tỉnh → UBND huyện → UBND xã
- Và có cross-functional: Pháp chế, Thanh tra, Tổ chức cán bộ...

Query điển hình của Router: *"tìm phòng có thẩm quyền xử lý CPXD tại Sở XD Bình Dương, đang có workload thấp nhất"*.

**Graph:**
```groovy
g.V().has('Organization', 'name', 'Sở XD Bình Dương')
 .in('BELONGS_TO').has('Position', 'role', 'chuyên viên')
 .where(__.out('AUTHORIZED_FOR').has('code', '1.004415'))
 .order().by('workload', asc).limit(1)
```

**Relational:** multi-level JOIN qua hierarchy table, CTE recursive, headache.

## Counter-arguments

**"Graph DB có overhead, latency cao hơn."**

True, nhưng:
- GovFlow chỉ dùng graph cho hot path (case processing + permission). Analytics dùng Hologres.
- Alibaba Cloud GDB có thể handle 10k+ query/s, thừa cho gov workload.
- Latency 50–200ms per query vs Postgres 5ms — OK vì LLM call là bottleneck (500–2000ms), graph không phải critical path.

**"Team không quen Gremlin."**

Mitigation:
- Gremlin Template Library (~30 templates prebuilt) → 80% query chỉ cần pick template
- Qwen3 sinh Gremlin ad-hoc qua SDK Guard validate
- Dev cycle ngắn vì Template Library thay vì học Gremlin from scratch

**"Graph DB overkill cho hackathon."**

Counter: overkill đúng là *điểm khác biệt*. Mọi đội khác sẽ dùng vector RAG + Postgres. GovFlow khác biệt bằng graph — đây là moat. Overkill = competitive advantage.

**"Risk cao hơn."**

True, nhưng reward cũng cao hơn. Alibaba SA judge thấy GDB = instant gật đầu. VC thấy graph-native = "moat rõ ràng". Judge operator thấy agent trace graph = "UX wow".

## Research backing

1. **Neo4j "Agentic GraphRAG for Commercial Contracts"** (2025) — xác nhận graph-based reasoning vượt trội vector RAG cho legal domain, đặc biệt khi có cross-reference phức tạp.

2. **AGENTiGraph** (arxiv 2508.02999, 2025) — multi-agent KG framework đạt 95.12% vs 83.34% zero-shot GPT-4o cho knowledge-intensive tasks.

3. **Hyperight 2026 report** — "GraphRAG + MCP là chuẩn mới cho agentic data architecture 2026".

4. **Microsoft GraphRAG** (2024) — Microsoft Research paper và open-source implementation cho graph-enhanced retrieval.

5. **AWS Neptune blog** (2024) — "Graph-powered authorization" — argue cho graph-based ABAC vs traditional RBAC.

## Trade-off table

| Aspect | Graph-native | Relational + vector |
|---|---|---|
| Legal cross-reference | ✅ Native traversal | ❌ Complex joins |
| Multi-agent state | ✅ Shared context | ❌ Coordination bugs |
| Fine-grained permission | ✅ Natural | ⚠️ RLS + CLS hacks |
| Audit forensic | ✅ Replay subgraph | ⚠️ Event tables + joins |
| Analytics aggregation | ⚠️ Slower | ✅ Native |
| Team familiarity | ⚠️ Gremlin learning curve | ✅ SQL everywhere |
| Ecosystem maturity | ⚠️ Smaller | ✅ Massive |
| Hackathon differentiation | ✅ Strong moat | ❌ Everyone has it |

GovFlow address analytics gap bằng Hologres (PG-compatible OLAP). Team familiarity bằng Template Library + SDK Guard. Còn lại toàn bộ advantage.

## Conclusion

Graph-native không phải "tech choice for fun". Nó là **structural match** với bản chất bài toán — pháp luật + tổ chức + permission + audit đều là graph bởi bản chất. Chọn graph là chọn đúng tool cho đúng việc, và đó là moat mạnh nhất của GovFlow.
