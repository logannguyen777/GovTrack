# 02 - Data Layer: Knowledge Graph, Vector Store, Object Storage

## Muc tieu (Objective)

Populate the GDB knowledge graph with legal/organizational/TTHC schema (30+ vertex labels,
30+ edge types), create Hologres/Postgres tables with Proxima vector indexes, embed law
chunks with Qwen3-Embedding v3, configure OSS bucket structure, seed test users, and
implement the Gremlin Template Library.

---

## 1. Hologres / PostgreSQL DDL

Write to `infra/postgres/init.sql`. This runs automatically on first `docker compose up`.
For Hologres cloud, run the same SQL after connecting via psql.

```sql
-- ============================================================
-- GovFlow: Hologres / PostgreSQL Schema
-- Local: pgvector extension replaces Proxima
-- ============================================================

-- Enable vector extension (pgvector locally, Proxima on Hologres)
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(100) UNIQUE NOT NULL,
    full_name       VARCHAR(200) NOT NULL,
    email           VARCHAR(200),
    password_hash   VARCHAR(200) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'officer',
        -- roles: admin, leader, officer, public_viewer
    clearance_level INTEGER NOT NULL DEFAULT 1,
        -- 1=Binh thuong, 2=Han che, 3=Mat, 4=Toi mat
    departments     TEXT[] NOT NULL DEFAULT '{}',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_role ON users (role);
CREATE INDEX idx_users_departments ON users USING GIN (departments);

-- ============================================================
-- law_chunks: vector-indexed law article chunks
-- ============================================================
CREATE TABLE IF NOT EXISTS law_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    law_id          VARCHAR(100) NOT NULL,
        -- e.g. "luat_dat_dai_2024", "nd_43_2014"
    article_number  VARCHAR(50) NOT NULL,
        -- e.g. "Dieu 35", "Khoan 2"
    clause_path     VARCHAR(200),
        -- e.g. "Dieu 35 > Khoan 2 > Diem a"
    chunk_index     INTEGER NOT NULL DEFAULT 0,
    title           TEXT,
    content         TEXT NOT NULL,
    embedding       vector(1536) NOT NULL,
        -- Qwen3-Embedding v3, 1536 dimensions
    metadata        JSONB DEFAULT '{}',
        -- {effective_date, gazette_number, issuing_body, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector similarity index (pgvector: ivfflat; Hologres: Proxima ANN)
-- For pgvector local dev:
CREATE INDEX idx_law_chunks_embedding ON law_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

-- For Hologres cloud (run instead of above):
-- CALL set_table_property('law_chunks', 'proxima_vectors',
--     '{"embedding":{"algorithm":"Graph","distance_method":"InnerProduct","build_params":{"min_flush_segment_count":1}}}');

CREATE INDEX idx_law_chunks_law_id ON law_chunks (law_id);
CREATE INDEX idx_law_chunks_article ON law_chunks (article_number);

-- ============================================================
-- analytics_cases: case processing metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(100) NOT NULL,
    department_id   VARCHAR(100) NOT NULL,
    tthc_code       VARCHAR(100),
    status          VARCHAR(50) NOT NULL DEFAULT 'submitted',
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    processing_days INTEGER,
    sla_days        INTEGER,
    is_overdue      BOOLEAN DEFAULT FALSE,
    agent_steps     INTEGER DEFAULT 0,
    total_tokens    INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_analytics_cases_dept ON analytics_cases (department_id);
CREATE INDEX idx_analytics_cases_status ON analytics_cases (status);
CREATE INDEX idx_analytics_cases_submitted ON analytics_cases (submitted_at);

-- ============================================================
-- analytics_agents: per-agent-step metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         VARCHAR(100) NOT NULL,
    agent_name      VARCHAR(100) NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    duration_ms     INTEGER,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    tool_calls      INTEGER DEFAULT 0,
    status          VARCHAR(50) NOT NULL DEFAULT 'running',
        -- running, completed, failed, retrying
    error_message   TEXT,
    metadata        JSONB DEFAULT '{}'
);

CREATE INDEX idx_analytics_agents_case ON analytics_agents (case_id);
CREATE INDEX idx_analytics_agents_name ON analytics_agents (agent_name);

-- ============================================================
-- notifications
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    body            TEXT,
    category        VARCHAR(50) NOT NULL DEFAULT 'info',
        -- info, action_required, alert, system
    link            VARCHAR(500),
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_notifications_user ON notifications (user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications (created_at DESC);

-- ============================================================
-- audit_events_flat: denormalized audit log (mirrors GDB AuditEvent)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_events_flat (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(100) NOT NULL,
        -- case.created, document.uploaded, agent.completed, permission.denied, ...
    actor_id        UUID,
    actor_name      VARCHAR(200),
    target_type     VARCHAR(100),
    target_id       VARCHAR(200),
    case_id         VARCHAR(200),
    department_id   VARCHAR(100),
    details         JSONB DEFAULT '{}',
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_events_type ON audit_events_flat (event_type);
CREATE INDEX idx_audit_events_actor ON audit_events_flat (actor_id);
CREATE INDEX idx_audit_events_case ON audit_events_flat (case_id);
CREATE INDEX idx_audit_events_created ON audit_events_flat (created_at DESC);

-- ============================================================
-- templates_nd30: Nghi dinh 30 document templates
-- ============================================================
CREATE TABLE IF NOT EXISTS templates_nd30 (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_code   VARCHAR(100) UNIQUE NOT NULL,
        -- e.g. "mau_01_nd30", "mau_02_nd30"
    template_name   VARCHAR(500) NOT NULL,
    category        VARCHAR(100),
    content_html    TEXT NOT NULL,
    placeholders    JSONB DEFAULT '[]',
        -- [{"key": "ho_ten", "label": "Ho va ten", "type": "string"}, ...]
    version         INTEGER NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_templates_code ON templates_nd30 (template_code);
```

---

## 2. GDB Schema: Vertex Labels

Submit these Gremlin queries to create the schema. For TinkerGraph (local), vertices are
created implicitly. For Alibaba GDB (cloud), create schema explicitly:

### 2.1 Create all 30 vertex labels

```python
"""scripts/create_gdb_schema.py -- Run once to establish GDB schema."""
import sys
sys.path.insert(0, "backend")

from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

create_gremlin_client()

# ---- Vertex Labels ----
vertex_labels = [
    # Legal hierarchy
    "Law", "Decree", "Circular", "Article", "Clause", "Point",
    # TTHC
    "TTHCSpec", "RequiredComponent", "ProcedureCategory",
    # Organization
    "Organization", "Position",
    # Templates
    "Template", "ClassificationLevel",
    # Case processing
    "Case", "Applicant", "Bundle", "Document", "ExtractedEntity",
    "Task", "Gap", "Citation",
    # Agent outputs
    "Opinion", "Summary", "Classification", "Decision", "Draft",
    "PublishedDoc",
    # Audit
    "AuditEvent", "AgentStep",
    # Consultation
    "ConsultRequest",
]

for label in vertex_labels:
    # Create a sentinel vertex to register the label, then remove it
    # (TinkerGraph creates labels on first use)
    gremlin_submit(f"g.addV('{label}').property('_schema_sentinel', true)")

print(f"Created {len(vertex_labels)} vertex labels")

# Verify
result = gremlin_submit("g.V().label().dedup()")
print(f"Labels in graph: {result}")

# Clean up sentinels
gremlin_submit("g.V().has('_schema_sentinel', true).drop()")
print("Sentinel vertices removed")

close_gremlin_client()
```

### 2.2 Vertex Property Definitions

Key properties per vertex label (not exhaustive -- agents add more at runtime):

| Vertex Label       | Key Properties                                                              |
|--------------------|-----------------------------------------------------------------------------|
| Law                | law_id, title, gazette_number, effective_date, issuing_body, status         |
| Decree             | decree_id, title, number, effective_date, issuing_body                      |
| Circular           | circular_id, title, number, effective_date, issuing_body                    |
| Article            | article_number, title, content_text, parent_law_id                          |
| Clause             | clause_number, content_text, parent_article                                 |
| Point              | point_letter, content_text, parent_clause                                   |
| TTHCSpec           | tthc_code, name, department, sla_days, fee, legal_basis                     |
| RequiredComponent  | component_name, is_mandatory, description, template_ref                     |
| ProcedureCategory  | category_name, parent_category                                             |
| Organization       | org_id, name, level, parent_org_id, province, district                      |
| Position           | position_id, title, org_id, clearance_level                                 |
| Template           | template_code, name, category, oss_key, version                             |
| ClassificationLevel| level, name_vi, description                                                 |
| Case               | case_id, code, status, submitted_at, department_id, tthc_code, applicant_id |
| Applicant          | applicant_id, full_name, id_number, phone, address                          |
| Bundle             | bundle_id, case_id, uploaded_at, status                                     |
| Document           | doc_id, filename, oss_key, content_type, page_count, ocr_status             |
| ExtractedEntity    | entity_type, value, confidence, source_doc_id, bounding_box                 |
| Task               | task_id, name, status, agent_name, depends_on[], case_id                    |
| Gap                | gap_id, description, severity, component_name, resolution                   |
| Citation           | citation_id, law_ref, article_ref, relevance_score, snippet                 |
| Opinion            | opinion_id, agent_name, verdict, reasoning, confidence                      |
| Summary            | summary_id, text, case_id, generated_at                                     |
| Classification     | classification_id, level, justification                                     |
| Decision           | decision_id, approved_by, decision_type, reasoning                          |
| Draft              | draft_id, template_code, oss_key, version, status                           |
| PublishedDoc       | pub_id, oss_key, published_at, signed_by                                    |
| AuditEvent         | event_type, actor_id, target_type, target_id, timestamp, details            |
| AgentStep          | step_id, agent_name, action, input_tokens, output_tokens, duration_ms       |
| ConsultRequest     | request_id, from_dept, to_dept, question, deadline, status                  |

---

## 3. GDB Schema: Edge Types

### 3.1 Complete edge type list with source -> target

```
CONTAINS:        Law -> Article, Article -> Clause, Clause -> Point,
                 Organization -> Position, Bundle -> Document
AMENDED_BY:      Law -> Law (newer amends older)
SUPERSEDED_BY:   Law -> Law
REPEALED_BY:     Law -> Law
REFERENCES:      Article -> Article (cross-reference between laws)
REQUIRES:        TTHCSpec -> RequiredComponent
GOVERNED_BY:     TTHCSpec -> Article (legal basis link)
AUTHORIZED_FOR:  Position -> TTHCSpec (who can process which TTHC)
PARENT_OF:       Organization -> Organization, ProcedureCategory -> ProcedureCategory
REPORTS_TO:      Position -> Position
BELONGS_TO:      Case -> ProcedureCategory, Position -> Organization
SUBMITTED_BY:    Case -> Applicant
HAS_BUNDLE:      Case -> Bundle
EXTRACTED:       Document -> ExtractedEntity
MATCHES_TTHC:    Case -> TTHCSpec (classification result)
HAS_GAP:         Case -> Gap
GAP_FOR:         Gap -> RequiredComponent (which component is missing)
CITES:           Opinion -> Citation, Summary -> Citation, Draft -> Citation
SATISFIES:       Document -> RequiredComponent (document fulfills requirement)
DEPENDS_ON:      Task -> Task (DAG dependency)
ASSIGNED_TO:     Task -> AgentStep
CONSULTED:       Case -> ConsultRequest
HAS_OPINION:     Case -> Opinion
HAS_DECISION:    Case -> Decision
PUBLISHED_AS:    Case -> PublishedDoc
AUDITS:          AuditEvent -> Case (or any target vertex)
PROCESSED_BY:    Case -> AgentStep
CLASSIFIED_AS:   Case -> Classification
HAS_DRAFT:       Case -> Draft
RESULT_TEMPLATE: Draft -> Template (which ND30 template was used)
```

### 3.2 Create edges script

```python
"""scripts/create_gdb_edges.py -- Document edge types in GDB."""
# Edge types are created implicitly in TinkerGraph when first used.
# This script documents the canonical edge labels.

EDGE_TYPES = [
    ("CONTAINS",       "Hierarchical containment"),
    ("AMENDED_BY",     "Legal amendment relationship"),
    ("SUPERSEDED_BY",  "Legal supersession"),
    ("REPEALED_BY",    "Legal repeal"),
    ("REFERENCES",     "Cross-reference between legal articles"),
    ("REQUIRES",       "TTHC requires a component"),
    ("GOVERNED_BY",    "TTHC governed by legal article"),
    ("AUTHORIZED_FOR", "Position authorized for TTHC procedure"),
    ("PARENT_OF",      "Hierarchical parent"),
    ("REPORTS_TO",     "Organizational reporting line"),
    ("BELONGS_TO",     "Membership / categorization"),
    ("SUBMITTED_BY",   "Case submitted by applicant"),
    ("HAS_BUNDLE",     "Case has document bundle"),
    ("EXTRACTED",      "Document has extracted entity"),
    ("MATCHES_TTHC",   "Case matched to TTHC spec"),
    ("HAS_GAP",        "Case has identified gap"),
    ("GAP_FOR",        "Gap relates to required component"),
    ("CITES",          "Output cites a legal reference"),
    ("SATISFIES",      "Document satisfies requirement"),
    ("DEPENDS_ON",     "Task depends on another task"),
    ("ASSIGNED_TO",    "Task assigned to agent step"),
    ("CONSULTED",      "Case has consultation request"),
    ("HAS_OPINION",    "Case has agent opinion"),
    ("HAS_DECISION",   "Case has decision"),
    ("PUBLISHED_AS",   "Case published as official document"),
    ("AUDITS",         "Audit event targets entity"),
    ("PROCESSED_BY",   "Case processed by agent step"),
    ("CLASSIFIED_AS",  "Case classified at security level"),
    ("HAS_DRAFT",      "Case has draft document"),
    ("RESULT_TEMPLATE","Draft uses ND30 template"),
]

for label, desc in EDGE_TYPES:
    print(f"  {label:20s} -- {desc}")
print(f"\nTotal: {len(EDGE_TYPES)} edge types")
```

---

## 4. KG Ingestion Pipeline

### 4.1 Legal Ingestion: scripts/ingest_legal.py

```python
"""
scripts/ingest_legal.py
Ingest Vietnamese legal documents into GDB.
Input:  data/laws/*.jsonl  (one JSON object per line)
Output: GDB vertices (Law, Article, Clause, Point) + edges (CONTAINS, REFERENCES)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

DATA_DIR = Path("data/laws")


def ingest_law(law: dict) -> None:
    """Ingest a single law and its articles into GDB."""
    law_id = law["law_id"]

    # Create Law vertex
    gremlin_submit(
        "g.addV('Law')"
        ".property('law_id', law_id)"
        ".property('title', title)"
        ".property('gazette_number', gazette)"
        ".property('effective_date', eff_date)"
        ".property('issuing_body', body)"
        ".property('status', status)",
        {
            "law_id": law_id,
            "title": law["title"],
            "gazette": law.get("gazette_number", ""),
            "eff_date": law.get("effective_date", ""),
            "body": law.get("issuing_body", ""),
            "status": law.get("status", "hieu_luc"),
        },
    )

    # Create Article vertices + CONTAINS edges
    for art in law.get("articles", []):
        art_num = art["article_number"]
        gremlin_submit(
            "g.addV('Article')"
            ".property('article_number', art_num)"
            ".property('title', title)"
            ".property('content_text', content)"
            ".property('parent_law_id', law_id)",
            {
                "art_num": art_num,
                "title": art.get("title", ""),
                "content": art.get("content", ""),
                "law_id": law_id,
            },
        )

        # Edge: Law -CONTAINS-> Article
        gremlin_submit(
            "g.V().has('Law', 'law_id', law_id)"
            ".addE('CONTAINS')"
            ".to(g.V().has('Article', 'article_number', art_num)"
            ".has('parent_law_id', law_id))",
            {"law_id": law_id, "art_num": art_num},
        )

        # Create Clause vertices if present
        for clause in art.get("clauses", []):
            clause_num = clause["clause_number"]
            gremlin_submit(
                "g.addV('Clause')"
                ".property('clause_number', clause_num)"
                ".property('content_text', content)"
                ".property('parent_article', art_num)"
                ".property('parent_law_id', law_id)",
                {
                    "clause_num": clause_num,
                    "content": clause.get("content", ""),
                    "art_num": art_num,
                    "law_id": law_id,
                },
            )

            # Edge: Article -CONTAINS-> Clause
            gremlin_submit(
                "g.V().has('Article', 'article_number', art_num)"
                ".has('parent_law_id', law_id)"
                ".addE('CONTAINS')"
                ".to(g.V().has('Clause', 'clause_number', clause_num)"
                ".has('parent_law_id', law_id))",
                {"art_num": art_num, "clause_num": clause_num, "law_id": law_id},
            )

            # Create Point vertices if present
            for point in clause.get("points", []):
                pt_letter = point["point_letter"]
                gremlin_submit(
                    "g.addV('Point')"
                    ".property('point_letter', pt_letter)"
                    ".property('content_text', content)"
                    ".property('parent_clause', clause_num)"
                    ".property('parent_law_id', law_id)",
                    {
                        "pt_letter": pt_letter,
                        "content": point.get("content", ""),
                        "clause_num": clause_num,
                        "law_id": law_id,
                    },
                )


def main():
    create_gremlin_client()

    for jsonl_file in sorted(DATA_DIR.glob("*.jsonl")):
        print(f"Ingesting {jsonl_file.name}...")
        with open(jsonl_file) as f:
            for line in f:
                law = json.loads(line.strip())
                ingest_law(law)

    # Print stats
    result = gremlin_submit("g.V().groupCount().by(label)")
    print(f"Vertex counts: {result}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
```

### 4.2 TTHC Ingestion: scripts/ingest_tthc.py

```python
"""
scripts/ingest_tthc.py
Ingest TTHC procedure specifications into GDB.
Input:  data/tthc/*.jsonl
Output: GDB vertices (TTHCSpec, RequiredComponent, ProcedureCategory) + edges
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

DATA_DIR = Path("data/tthc")


def ingest_tthc(spec: dict) -> None:
    """Ingest a single TTHC spec with its required components."""
    code = spec["tthc_code"]

    gremlin_submit(
        "g.addV('TTHCSpec')"
        ".property('tthc_code', code)"
        ".property('name', name)"
        ".property('department', dept)"
        ".property('sla_days', sla)"
        ".property('fee', fee)"
        ".property('legal_basis', legal)",
        {
            "code": code,
            "name": spec["name"],
            "dept": spec.get("department", ""),
            "sla": spec.get("sla_days", 15),
            "fee": spec.get("fee", "0"),
            "legal": spec.get("legal_basis", ""),
        },
    )

    # Link to category
    cat = spec.get("category", "")
    if cat:
        # Ensure category exists
        gremlin_submit(
            "g.V().has('ProcedureCategory', 'category_name', cat)"
            ".fold().coalesce(unfold(), addV('ProcedureCategory')"
            ".property('category_name', cat))",
            {"cat": cat},
        )
        gremlin_submit(
            "g.V().has('TTHCSpec', 'tthc_code', code)"
            ".addE('BELONGS_TO')"
            ".to(g.V().has('ProcedureCategory', 'category_name', cat))",
            {"code": code, "cat": cat},
        )

    # Required components
    for comp in spec.get("required_components", []):
        comp_name = comp["name"]
        gremlin_submit(
            "g.addV('RequiredComponent')"
            ".property('component_name', comp_name)"
            ".property('is_mandatory', mandatory)"
            ".property('description', desc)"
            ".property('template_ref', tmpl)"
            ".property('tthc_code', code)",
            {
                "comp_name": comp_name,
                "mandatory": comp.get("is_mandatory", True),
                "desc": comp.get("description", ""),
                "tmpl": comp.get("template_ref", ""),
                "code": code,
            },
        )
        gremlin_submit(
            "g.V().has('TTHCSpec', 'tthc_code', code)"
            ".addE('REQUIRES')"
            ".to(g.V().has('RequiredComponent', 'component_name', comp_name)"
            ".has('tthc_code', code))",
            {"code": code, "comp_name": comp_name},
        )

    # Legal basis links (GOVERNED_BY -> Article)
    for ref in spec.get("legal_refs", []):
        gremlin_submit(
            "g.V().has('Article', 'article_number', art)"
            ".has('parent_law_id', law_id)"
            ".fold().coalesce("
            "  unfold(),"
            "  constant('missing')"
            ").is(neq('missing'))"
            ".as('a')"
            ".V().has('TTHCSpec', 'tthc_code', code)"
            ".addE('GOVERNED_BY').to('a')",
            {"art": ref["article"], "law_id": ref["law_id"], "code": code},
        )


def main():
    create_gremlin_client()

    for jsonl_file in sorted(DATA_DIR.glob("*.jsonl")):
        print(f"Ingesting {jsonl_file.name}...")
        with open(jsonl_file) as f:
            for line in f:
                spec = json.loads(line.strip())
                ingest_tthc(spec)

    result = gremlin_submit("g.V().groupCount().by(label)")
    print(f"Vertex counts: {result}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
```

---

## 5. Organization Hierarchy

Seed the organization structure for Binh Duong province:

```python
"""scripts/seed_organizations.py"""
import sys
sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

ORGS = [
    # (org_id, name, level, parent_org_id, province, district)
    ("ubnd_bd",       "UBND tinh Binh Duong",             "tinh",   None,        "Binh Duong", None),
    ("so_xd_bd",      "So Xay dung tinh Binh Duong",     "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_tnmt_bd",    "So TN&MT tinh Binh Duong",        "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_tp_bd",      "So Tu phap tinh Binh Duong",      "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_nv_bd",      "So Noi vu tinh Binh Duong",       "so",     "ubnd_bd",   "Binh Duong", None),
    ("ubnd_tdi",      "UBND TP Thu Dau Mot",             "huyen",  "ubnd_bd",   "Binh Duong", "Thu Dau Mot"),
    ("phong_qldt_xd", "Phong QLDT - So Xay dung",       "phong",  "so_xd_bd",  "Binh Duong", None),
    ("phong_qldd",    "Phong QLDD - So TN&MT",           "phong",  "so_tnmt_bd","Binh Duong", None),
]

POSITIONS = [
    # (position_id, title, org_id, clearance_level)
    ("gd_so_xd",      "Giam doc So Xay dung",        "so_xd_bd",      3),
    ("pgd_so_xd",     "Pho Giam doc So Xay dung",    "so_xd_bd",      2),
    ("tp_qldt",       "Truong phong QLDT",            "phong_qldt_xd", 2),
    ("cv_qldt_1",     "Chuyen vien QLDT 1",           "phong_qldt_xd", 1),
    ("cv_qldt_2",     "Chuyen vien QLDT 2",           "phong_qldt_xd", 1),
    ("gd_so_tnmt",    "Giam doc So TN&MT",            "so_tnmt_bd",    3),
    ("tp_qldd",       "Truong phong QLDD",            "phong_qldd",    2),
    ("cv_qldd_1",     "Chuyen vien QLDD 1",           "phong_qldd",    1),
]


def main():
    create_gremlin_client()

    for org_id, name, level, parent_id, province, district in ORGS:
        gremlin_submit(
            "g.addV('Organization')"
            ".property('org_id', org_id)"
            ".property('name', name)"
            ".property('level', level)"
            ".property('parent_org_id', parent_id)"
            ".property('province', province)"
            ".property('district', district)",
            {
                "org_id": org_id, "name": name, "level": level,
                "parent_id": parent_id or "", "province": province or "",
                "district": district or "",
            },
        )

    # Create PARENT_OF edges
    for org_id, _, _, parent_id, _, _ in ORGS:
        if parent_id:
            gremlin_submit(
                "g.V().has('Organization', 'org_id', parent_id)"
                ".addE('PARENT_OF')"
                ".to(g.V().has('Organization', 'org_id', child_id))",
                {"parent_id": parent_id, "child_id": org_id},
            )

    for pos_id, title, org_id, clearance in POSITIONS:
        gremlin_submit(
            "g.addV('Position')"
            ".property('position_id', pos_id)"
            ".property('title', title)"
            ".property('org_id', org_id)"
            ".property('clearance_level', clearance)",
            {"pos_id": pos_id, "title": title, "org_id": org_id, "clearance": clearance},
        )
        gremlin_submit(
            "g.V().has('Position', 'position_id', pos_id)"
            ".addE('BELONGS_TO')"
            ".to(g.V().has('Organization', 'org_id', org_id))",
            {"pos_id": pos_id, "org_id": org_id},
        )

    result = gremlin_submit("g.V().has(label, within('Organization','Position')).groupCount().by(label)")
    print(f"Org/Position counts: {result}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
```

---

## 6. Law Chunk Embedding Pipeline

### scripts/embed_chunks.py

```python
"""
scripts/embed_chunks.py
Chunk law articles, embed with Qwen3-Embedding v3, insert into law_chunks table.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

from openai import OpenAI

sys.path.insert(0, "backend")
from src.config import settings
from src.database import create_pg_pool, get_pg_pool, close_pg_pool

DATA_DIR = Path("data/laws")
CHUNK_SIZE = 800  # characters per chunk
CHUNK_OVERLAP = 100
EMBED_MODEL = "text-embedding-v3"
EMBED_DIM = 1536
BATCH_SIZE = 20  # embeddings per API call


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def get_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts."""
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        dimensions=EMBED_DIM,
    )
    return [item.embedding for item in response.data]


async def insert_chunks(pool, chunks: list[dict]) -> None:
    """Insert embedded chunks into law_chunks table."""
    async with pool.acquire() as conn:
        for chunk in chunks:
            await conn.execute(
                """
                INSERT INTO law_chunks (id, law_id, article_number, clause_path,
                    chunk_index, title, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, $9::jsonb)
                """,
                uuid.uuid4(),
                chunk["law_id"],
                chunk["article_number"],
                chunk.get("clause_path", ""),
                chunk["chunk_index"],
                chunk.get("title", ""),
                chunk["content"],
                str(chunk["embedding"]),
                json.dumps(chunk.get("metadata", {})),
            )


async def main():
    # Initialize
    qwen = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
    await create_pg_pool()
    pool = get_pg_pool()

    total_chunks = 0

    for jsonl_file in sorted(DATA_DIR.glob("*.jsonl")):
        print(f"Processing {jsonl_file.name}...")
        with open(jsonl_file) as f:
            for line in f:
                law = json.loads(line.strip())
                law_id = law["law_id"]

                for art in law.get("articles", []):
                    content = art.get("content", "")
                    if not content:
                        continue

                    text_chunks = chunk_text(content)
                    batch_records = []

                    for idx, chunk_text_str in enumerate(text_chunks):
                        batch_records.append({
                            "law_id": law_id,
                            "article_number": art["article_number"],
                            "clause_path": art.get("clause_path", art["article_number"]),
                            "chunk_index": idx,
                            "title": art.get("title", ""),
                            "content": chunk_text_str,
                            "metadata": {
                                "effective_date": law.get("effective_date", ""),
                                "issuing_body": law.get("issuing_body", ""),
                            },
                        })

                    # Embed in batches
                    for i in range(0, len(batch_records), BATCH_SIZE):
                        batch = batch_records[i : i + BATCH_SIZE]
                        texts = [r["content"] for r in batch]
                        embeddings = get_embeddings(qwen, texts)

                        for record, emb in zip(batch, embeddings):
                            record["embedding"] = emb

                        await insert_chunks(pool, batch)
                        total_chunks += len(batch)

    print(f"Total chunks embedded and inserted: {total_chunks}")

    # Verify
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM law_chunks")
        print(f"law_chunks table row count: {count}")

    await close_pg_pool()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. OSS Bucket Structure

```
govflow-dev/                  (or govflow-prod)
├── bundles/
│   └── {case_id}/
│       └── {bundle_id}/
│           ├── doc_001.pdf
│           ├── doc_002.jpg
│           └── manifest.json
├── drafts/
│   └── {case_id}/
│       └── {draft_id}.docx
├── published/
│   └── {case_id}/
│       └── {pub_id}.pdf
├── templates/
│   └── nd30/
│       ├── mau_01_nd30.html
│       ├── mau_02_nd30.html
│       └── ...
└── audit-archives/
    └── {year}/{month}/
        └── audit_{date}.jsonl.gz
```

---

## 8. Seed Users

### scripts/seed_users.py

```python
"""scripts/seed_users.py -- Create 6 test users with varying roles/clearance."""
import asyncio
import hashlib
import sys
import uuid

sys.path.insert(0, "backend")
from src.database import create_pg_pool, get_pg_pool, close_pg_pool

USERS = [
    # (username, full_name, role, clearance, departments[])
    ("admin",       "Quan Tri Vien",            "admin",         4, ["ubnd_bd"]),
    ("gd_xd",      "Nguyen Van Giam Doc",      "leader",        3, ["so_xd_bd"]),
    ("tp_qldt",     "Tran Thi Truong Phong",    "leader",        2, ["phong_qldt_xd"]),
    ("cv_qldt",     "Le Van Chuyen Vien",       "officer",       1, ["phong_qldt_xd"]),
    ("cv_tnmt",     "Pham Thi Moi Truong",      "officer",       1, ["phong_qldd"]),
    ("public",      "Cong Dan Thu Nghiem",       "public_viewer", 0, []),
]


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


async def main():
    await create_pg_pool()
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        for username, full_name, role, clearance, depts in USERS:
            await conn.execute(
                """
                INSERT INTO users (id, username, full_name, email, password_hash,
                    role, clearance_level, departments)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (username) DO NOTHING
                """,
                uuid.uuid4(),
                username,
                full_name,
                f"{username}@govflow.test",
                hash_password(f"{username}123"),  # hackathon passwords
                role,
                clearance,
                depts,
            )
            print(f"  Created user: {username} (role={role}, clearance={clearance})")

    # Verify
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT username, role, clearance_level FROM users ORDER BY clearance_level DESC")
        for r in rows:
            print(f"  {r['username']:12s} role={r['role']:15s} clearance={r['clearance_level']}")

    await close_pg_pool()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 9. Gremlin Template Library

Write to `backend/src/graph/templates.py`. These are the 30 parameterized Gremlin queries
used by agents via the MCP server.

```python
"""
backend/src/graph/templates.py
Gremlin Template Library -- 30 parameterized queries for agent tools.
Each template is a (query_string, description, parameter_names) tuple.
"""
from dataclasses import dataclass


@dataclass
class GremlinTemplate:
    name: str
    description: str
    query: str
    params: list[str]


TEMPLATES: dict[str, GremlinTemplate] = {}


def _register(name: str, description: str, query: str, params: list[str]) -> None:
    TEMPLATES[name] = GremlinTemplate(name=name, description=description, query=query, params=params)


# ---- 1. Lookup ----
_register(
    "get_law_by_id",
    "Retrieve a Law vertex by law_id",
    "g.V().has('Law', 'law_id', law_id).valueMap(true)",
    ["law_id"],
)

_register(
    "get_article",
    "Retrieve an Article by number and parent law",
    "g.V().has('Article', 'article_number', art_num).has('parent_law_id', law_id).valueMap(true)",
    ["art_num", "law_id"],
)

_register(
    "get_tthc_spec",
    "Retrieve a TTHCSpec by tthc_code",
    "g.V().has('TTHCSpec', 'tthc_code', code).valueMap(true)",
    ["code"],
)

_register(
    "get_case",
    "Retrieve a Case vertex by case_id",
    "g.V().has('Case', 'case_id', case_id).valueMap(true)",
    ["case_id"],
)

# ---- 2. Traversal ----
_register(
    "law_articles",
    "Get all articles contained in a law",
    "g.V().has('Law', 'law_id', law_id).out('CONTAINS').hasLabel('Article').valueMap(true)",
    ["law_id"],
)

_register(
    "article_clauses",
    "Get all clauses in an article",
    "g.V().has('Article', 'article_number', art_num).has('parent_law_id', law_id).out('CONTAINS').hasLabel('Clause').valueMap(true)",
    ["art_num", "law_id"],
)

_register(
    "tthc_required_components",
    "Get all required components for a TTHC",
    "g.V().has('TTHCSpec', 'tthc_code', code).out('REQUIRES').valueMap(true)",
    ["code"],
)

_register(
    "tthc_legal_basis",
    "Get legal articles governing a TTHC",
    "g.V().has('TTHCSpec', 'tthc_code', code).out('GOVERNED_BY').valueMap(true)",
    ["code"],
)

_register(
    "case_documents",
    "Get all documents in a case's bundles",
    "g.V().has('Case', 'case_id', case_id).out('HAS_BUNDLE').out('CONTAINS').hasLabel('Document').valueMap(true)",
    ["case_id"],
)

_register(
    "case_gaps",
    "Get all identified gaps for a case",
    "g.V().has('Case', 'case_id', case_id).out('HAS_GAP').valueMap(true)",
    ["case_id"],
)

_register(
    "case_opinions",
    "Get all agent opinions for a case",
    "g.V().has('Case', 'case_id', case_id).out('HAS_OPINION').valueMap(true)",
    ["case_id"],
)

_register(
    "case_agent_steps",
    "Get all agent processing steps for a case",
    "g.V().has('Case', 'case_id', case_id).out('PROCESSED_BY').valueMap(true).order().by('started_at')",
    ["case_id"],
)

# ---- 3. Subgraph ----
_register(
    "case_subgraph",
    "Get full case subgraph (2-hop neighborhood)",
    "g.V().has('Case', 'case_id', case_id).bothE().bothV().path().by(valueMap(true)).by(label)",
    ["case_id"],
)

_register(
    "org_hierarchy",
    "Get organization hierarchy from a root org",
    "g.V().has('Organization', 'org_id', org_id).repeat(out('PARENT_OF')).until(outE('PARENT_OF').count().is(0)).path().by(valueMap(true))",
    ["org_id"],
)

# ---- 4. Amendment chain ----
_register(
    "amendment_chain",
    "Get the amendment chain for a law",
    "g.V().has('Law', 'law_id', law_id).repeat(out('AMENDED_BY')).until(outE('AMENDED_BY').count().is(0)).path().by(valueMap(true))",
    ["law_id"],
)

_register(
    "supersession_chain",
    "Get the supersession chain for a law",
    "g.V().has('Law', 'law_id', law_id).repeat(out('SUPERSEDED_BY')).until(outE('SUPERSEDED_BY').count().is(0)).path().by(valueMap(true))",
    ["law_id"],
)

# ---- 5. Cross-reference ----
_register(
    "article_references",
    "Get articles referenced by a given article",
    "g.V().has('Article', 'article_number', art_num).has('parent_law_id', law_id).out('REFERENCES').valueMap(true)",
    ["art_num", "law_id"],
)

_register(
    "citing_articles",
    "Get articles that reference a given article (reverse)",
    "g.V().has('Article', 'article_number', art_num).has('parent_law_id', law_id).in('REFERENCES').valueMap(true)",
    ["art_num", "law_id"],
)

# ---- 6. Case processing ----
_register(
    "create_case",
    "Create a new Case vertex",
    "g.addV('Case').property('case_id', case_id).property('code', code).property('status', 'submitted').property('submitted_at', submitted_at).property('department_id', dept_id).property('tthc_code', tthc_code)",
    ["case_id", "code", "submitted_at", "dept_id", "tthc_code"],
)

_register(
    "update_case_status",
    "Update the status of a Case",
    "g.V().has('Case', 'case_id', case_id).property('status', status)",
    ["case_id", "status"],
)

_register(
    "add_gap",
    "Add a Gap vertex linked to a Case",
    "g.addV('Gap').property('gap_id', gap_id).property('description', desc).property('severity', severity).property('component_name', comp).as('gap').V().has('Case', 'case_id', case_id).addE('HAS_GAP').to('gap')",
    ["gap_id", "desc", "severity", "comp", "case_id"],
)

_register(
    "add_citation",
    "Add a Citation vertex",
    "g.addV('Citation').property('citation_id', cit_id).property('law_ref', law_ref).property('article_ref', art_ref).property('relevance_score', score).property('snippet', snippet)",
    ["cit_id", "law_ref", "art_ref", "score", "snippet"],
)

_register(
    "add_opinion",
    "Add an Opinion from an agent to a Case",
    "g.addV('Opinion').property('opinion_id', op_id).property('agent_name', agent).property('verdict', verdict).property('reasoning', reasoning).property('confidence', conf).as('op').V().has('Case', 'case_id', case_id).addE('HAS_OPINION').to('op')",
    ["op_id", "agent", "verdict", "reasoning", "conf", "case_id"],
)

_register(
    "add_agent_step",
    "Log an AgentStep vertex",
    "g.addV('AgentStep').property('step_id', step_id).property('agent_name', agent).property('action', action).property('input_tokens', in_tok).property('output_tokens', out_tok).property('duration_ms', dur).as('step').V().has('Case', 'case_id', case_id).addE('PROCESSED_BY').to('step')",
    ["step_id", "agent", "action", "in_tok", "out_tok", "dur", "case_id"],
)

# ---- 7. Task DAG ----
_register(
    "create_task",
    "Create a Task vertex for the agent DAG",
    "g.addV('Task').property('task_id', task_id).property('name', name).property('status', 'pending').property('agent_name', agent).property('case_id', case_id)",
    ["task_id", "name", "agent", "case_id"],
)

_register(
    "add_task_dependency",
    "Create DEPENDS_ON edge between tasks",
    "g.V().has('Task', 'task_id', downstream).addE('DEPENDS_ON').to(g.V().has('Task', 'task_id', upstream))",
    ["downstream", "upstream"],
)

_register(
    "get_ready_tasks",
    "Get tasks that are pending and have all dependencies completed",
    "g.V().has('Task', 'case_id', case_id).has('status', 'pending').where(out('DEPENDS_ON').has('status', neq('completed')).count().is(0)).valueMap(true)",
    ["case_id"],
)

_register(
    "update_task_status",
    "Update a task's status",
    "g.V().has('Task', 'task_id', task_id).property('status', status)",
    ["task_id", "status"],
)

# ---- 8. Audit ----
_register(
    "add_audit_event",
    "Create an AuditEvent vertex",
    "g.addV('AuditEvent').property('event_type', ev_type).property('actor_id', actor).property('target_type', tgt_type).property('target_id', tgt_id).property('timestamp', ts).property('details', details)",
    ["ev_type", "actor", "tgt_type", "tgt_id", "ts", "details"],
)

# ---- 9. Search support ----
_register(
    "find_tthc_by_department",
    "Find all TTHC specs for a department",
    "g.V().has('TTHCSpec', 'department', dept).valueMap(true)",
    ["dept"],
)


def get_template(name: str) -> GremlinTemplate:
    """Get a template by name. Raises KeyError if not found."""
    return TEMPLATES[name]


def list_templates() -> list[dict]:
    """List all templates as dicts (for MCP tool registration)."""
    return [
        {"name": t.name, "description": t.description, "params": t.params}
        for t in TEMPLATES.values()
    ]
```

---

## 10. Verification Checklist

### 10.1 Hologres/Postgres tables created

```bash
psql postgresql://govflow:govflow_dev_2026@localhost:5432/govflow \
  -c "\dt"
# Expected: users, law_chunks, analytics_cases, analytics_agents,
#           notifications, audit_events_flat, templates_nd30
```

### 10.2 GDB vertex count after ingestion

```bash
cd /home/logan/GovTrack
source backend/.venv/bin/activate
python scripts/ingest_legal.py
python scripts/ingest_tthc.py
python scripts/seed_organizations.py

python -c "
from backend.src.database import create_gremlin_client, gremlin_submit, close_gremlin_client
create_gremlin_client()
result = gremlin_submit('g.V().groupCount().by(label)')
print(result)
total = gremlin_submit('g.V().count()')
print(f'Total vertices: {total}')
close_gremlin_client()
"
# Expected: ~2000 vertices across all labels
```

### 10.3 Vector search returns results

```bash
python -c "
import asyncio
from backend.src.database import create_pg_pool, get_pg_pool, close_pg_pool

async def test():
    await create_pg_pool()
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        # Use a dummy vector for testing (real query would use embedding)
        rows = await conn.fetch('''
            SELECT law_id, article_number, content,
                   1 - (embedding <=> (SELECT embedding FROM law_chunks LIMIT 1)) as similarity
            FROM law_chunks
            ORDER BY embedding <=> (SELECT embedding FROM law_chunks LIMIT 1)
            LIMIT 5
        ''')
        for r in rows:
            print(f'{r[\"law_id\"]} {r[\"article_number\"]}: sim={r[\"similarity\"]:.4f}')
    await close_pg_pool()

asyncio.run(test())
"
# Expected: 5 rows with similarity scores (first row = 1.0000, self-match)
```

### 10.4 Seed users exist

```bash
psql postgresql://govflow:govflow_dev_2026@localhost:5432/govflow \
  -c "SELECT username, role, clearance_level FROM users ORDER BY clearance_level DESC;"
# Expected: 6 users (admin, gd_xd, tp_qldt, cv_qldt, cv_tnmt, public)
```

### 10.5 Gremlin templates load

```bash
python -c "
from backend.src.graph.templates import list_templates
templates = list_templates()
print(f'Loaded {len(templates)} Gremlin templates')
for t in templates[:5]:
    print(f'  {t[\"name\"]}: {t[\"description\"]}')
"
# Expected: 30 Gremlin templates loaded
```

---

## Tong ket (Summary)

| Component               | Count / Status                        |
|--------------------------|---------------------------------------|
| Hologres tables          | 7 tables with indexes                 |
| GDB vertex labels        | 30 labels                             |
| GDB edge types           | 30 edge types                         |
| Org hierarchy            | 8 orgs + 8 positions                  |
| Law chunks embedded      | 500+ (target)                         |
| Seed users               | 6 test users                          |
| Gremlin templates        | 30 parameterized queries              |
| OSS bucket structure     | 5 prefixes configured                 |

Next step: proceed to `03-backend-api.md` to build the FastAPI application.
