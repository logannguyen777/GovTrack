You are populating GovFlow's Knowledge Graph, embedding law chunks, and setting up OSS. Follow docs/implementation/02-data-layer.md as the detailed guide.

Task: $ARGUMENTS (default: full data layer)

## What You Build

~2000 KG vertices + ~5000 edges in GDB. 500+ law chunk embeddings in Hologres. OSS bucket with templates. 30 Gremlin template queries.

## Steps

1. **Run/enhance data ingestion scripts:**
   - `scripts/ingest_legal.py` — parse Vietnamese legal corpus -> vertices.jsonl + edges.jsonl
   - `scripts/ingest_tthc.py` — parse 5 TTHC specs -> tthc_vertices.jsonl + tthc_edges.jsonl
   - Both scripts already exist, may need enhancement

2. **Create `scripts/ingest_org.py`** — organization hierarchy:
   - 20+ Organization vertices (So XD, So TN&MT, So TP, So KH&DT, UBND tinh Binh Duong, etc.)
   - 50+ Position vertices
   - AUTHORIZED_FOR edges (which org handles which TTHC)
   - REPORTS_TO, PARENT_OF edges

3. **Create `scripts/load_kg_to_gdb.py`** — bulk load to GDB:
   - Read processed JSONL files
   - Insert vertices with labels + properties via gremlinpython
   - Insert edges with types + properties
   - Idempotent: check exists before insert

4. **Create `scripts/embed_law_chunks.py`** — vector embeddings:
   - Chunk Article text (max 512 tokens per chunk)
   - Call Qwen3-Embedding v3 via DashScope: model="text-embedding-v3", dimensions=1536
   - Insert into Hologres law_chunks table

5. **Implement `backend/src/graph/templates.py`** — 30 Gremlin template queries:
   - Case lifecycle: case.create, case.get_initial_metadata, case.find_missing_components, case.get_full_context, case.get_sla_status, case.list_active_by_dept, case.count_overdue_by_dept, case.add_gap, case.assign_to_dept, case.update_status
   - Law/TTHC: law.get_effective_article, law.get_cross_references, law.get_amendment_history, tthc.find_by_category, tthc.list_common, tthc.get_spec_with_requirements, org.find_authorized_for_tthc, org.find_positions_in_dept
   - Agent/audit: agent.log_step, agent.get_case_trace, audit.log_event, audit.replay_case, audit.find_denials_by_user, audit.count_denials_window
   - Search: search.related_cases_by_tthc, search.precedent_similar_cases

6. **Seed test users in Hologres:**
   - 6 users: citizen (Unclassified), staff intake (Confidential), staff processor (Confidential), leader (Secret), legal (Confidential), security (Top Secret)

7. **Upload ND 30 templates to OSS:**
   - Jinja2 templates for: QuyetDinh, CongVan, ThongBao, GiayPhep per TTHC

## Graph Schema (GDB vertex labels)
KG: Law, Decree, Circular, Article, Clause, Point, TTHCSpec, RequiredComponent, ProcedureCategory, Organization, Position, Template, ClassificationLevel
CG: Case, Applicant, Bundle, Document, ExtractedEntity, Task, Gap, Citation, Opinion, Summary, Classification, Decision, Draft, PublishedDoc, AuditEvent, AgentStep, ConsultRequest

## Spec References
- docs/03-architecture/dual-graph-design.md — vertex/edge schema
- docs/03-architecture/data-model.md — Hologres DDL + OSS structure
- docs/03-architecture/gremlin-template-library.md — template specs

## Verification
```bash
# KG populated
python -c "# g.V().count() should return ~2000"
python -c "# g.V().hasLabel('TTHCSpec').count() should return 5"
python -c "# g.V().has('TTHCSpec','code','1.004415').out('REQUIRES').count() should return ~7"
# Embeddings
psql "$HOLOGRES_DSN" -c "SELECT count(*) FROM law_chunks"  # should be 500+
# Templates work
python -c "# Execute case.get_initial_metadata template on GDB"
```
