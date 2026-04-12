# Data Model — Graph + Relational + Blob

GovFlow uses **polyglot persistence** by design. Each store does what it's best at.

## Overview

| Store | Technology | Purpose |
|---|---|---|
| Primary graph | Alibaba Cloud GDB (Gremlin/TinkerPop) | KG + Context Graph — case truth, relationships, reasoning trace, audit |
| Relational + Vector | Alibaba Cloud Hologres (PG-compatible + Proxima) | Users, policies, analytics aggregations, law_chunks vector, audit projection |
| Blob | Alibaba Cloud OSS (Object Storage) | Raw document files, generated PDFs, templates |

See [`dual-graph-design.md`](dual-graph-design.md) for complete graph schema. This doc covers Hologres + OSS + integration.

## Hologres schema

Hologres is PG-compatible → standard SQL DDL. Proxima is vector search extension.

### `users` — identity
```sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  sub TEXT UNIQUE NOT NULL,              -- JWT subject
  full_name TEXT NOT NULL,
  email TEXT,
  clearance_level TEXT NOT NULL CHECK (clearance_level IN
    ('Unclassified','Confidential','Secret','Top Secret')),
  department_ids TEXT[] NOT NULL DEFAULT '{}',
  role TEXT NOT NULL CHECK (role IN
    ('citizen','staff','supervisor','leader','security','admin')),
  vneid_subject TEXT,                    -- for citizens via Đề án 06
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_login TIMESTAMPTZ
);

CREATE INDEX idx_users_department ON users USING gin(department_ids);
CREATE INDEX idx_users_clearance ON users(clearance_level);
```

### `law_chunks` — vector store
```sql
CREATE TABLE law_chunks (
  id SERIAL PRIMARY KEY,
  law_code TEXT NOT NULL,
  article_num INT NOT NULL,
  clause_num INT,
  point_label TEXT,
  chunk_seq INT NOT NULL,        -- for long articles split
  text TEXT NOT NULL,
  embedding FLOAT4[1536] NOT NULL,
  classification TEXT NOT NULL DEFAULT 'Unclassified',
  effective_date DATE,
  status TEXT NOT NULL DEFAULT 'effective',  -- effective/amended/superseded/repealed
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Proxima vector index
CALL set_table_property('law_chunks', 'proxima_vectors',
  '{"embedding":{"algorithm":"Graph","metric":"Cosine","builder_params":{"min_flush_proxima_row_count":1000}}}');

CREATE INDEX idx_law_chunks_status ON law_chunks(status, classification);
CREATE INDEX idx_law_chunks_law ON law_chunks(law_code, article_num);
```

### `analytics_cases` — materialized view for Leadership Dashboard
```sql
-- Refreshed every 5 minutes from GDB via data pipeline
CREATE TABLE analytics_cases (
  case_id TEXT PRIMARY KEY,
  tthc_code TEXT NOT NULL,
  tthc_name TEXT,
  classification TEXT,
  status TEXT,
  created_at TIMESTAMPTZ,
  sla_deadline TIMESTAMPTZ,
  sla_status TEXT,  -- 'on_track', 'at_risk', 'overdue'
  current_owner TEXT,
  processing_time_seconds INT,
  compliance_score FLOAT,
  gap_count INT,
  consult_count INT,
  decision_type TEXT
);

CREATE INDEX idx_analytics_sla ON analytics_cases(sla_status, sla_deadline);
CREATE INDEX idx_analytics_tthc ON analytics_cases(tthc_code, created_at);
```

### `analytics_agents` — agent performance
```sql
CREATE TABLE analytics_agents (
  date DATE,
  agent_name TEXT,
  total_runs INT,
  successful_runs INT,
  failed_runs INT,
  avg_latency_ms FLOAT,
  p95_latency_ms FLOAT,
  total_tokens_in BIGINT,
  total_tokens_out BIGINT,
  PRIMARY KEY (date, agent_name)
);
```

### `notifications` — notification outbox
```sql
CREATE TABLE notifications (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  case_id TEXT,
  type TEXT NOT NULL,  -- 'gap_citizen', 'result_ready', 'consult_request'
  channel TEXT NOT NULL,  -- 'push', 'email', 'sms', 'zalo'
  payload JSONB NOT NULL,
  status TEXT DEFAULT 'pending',  -- 'pending', 'sent', 'failed'
  created_at TIMESTAMPTZ DEFAULT now(),
  sent_at TIMESTAMPTZ
);

CREATE INDEX idx_notifications_status ON notifications(status, created_at);
```

### `audit_events_flat` — projection from GDB for fast analytics query
```sql
-- GDB AuditEvent vertices are projected here for OLAP queries
CREATE TABLE audit_events_flat (
  id BIGSERIAL PRIMARY KEY,
  actor_id TEXT NOT NULL,
  actor_type TEXT NOT NULL,  -- 'user', 'agent'
  action TEXT NOT NULL,      -- 'read', 'write', 'delete', 'publish'
  resource_label TEXT NOT NULL,
  resource_id TEXT,
  case_id TEXT,
  result TEXT NOT NULL,      -- 'allow', 'deny'
  reason TEXT,
  ip INET,
  user_agent TEXT,
  tier TEXT,                 -- 'SDK_Guard', 'GDB_RBAC', 'Property_Mask', 'User_ABAC'
  timestamp TIMESTAMPTZ NOT NULL,
  trace_id TEXT
);

CREATE INDEX idx_audit_time ON audit_events_flat(timestamp DESC);
CREATE INDEX idx_audit_actor ON audit_events_flat(actor_id, timestamp DESC);
CREATE INDEX idx_audit_case ON audit_events_flat(case_id, timestamp);
CREATE INDEX idx_audit_denied ON audit_events_flat(result, timestamp) WHERE result = 'deny';
```

### `templates_nd30` — VB output templates
```sql
CREATE TABLE templates_nd30 (
  id SERIAL PRIMARY KEY,
  tthc_code TEXT NOT NULL,
  doc_type TEXT NOT NULL,          -- 'QuyetDinh', 'CongVan', 'ThongBao', 'GiayPhep'
  decision_type TEXT,               -- 'approve', 'deny', 'request_more'
  body_template TEXT NOT NULL,      -- Jinja2 template
  required_fields JSONB,
  compliance_rules_json JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (tthc_code, doc_type, decision_type)
);
```

## Hologres AI Functions — calling Qwen in SQL

One of Hologres' killer features: **AI Functions** to call Alibaba Cloud Model Studio directly in SQL.

```sql
-- Example: generate executive briefing for daily report
SELECT
  case_id,
  tthc_name,
  ai_generate_text(
    'qwen-max',
    'Summarize this case timeline for executive: ' ||
    jsonb_build_object(
      'tthc', tthc_name,
      'status', status,
      'days_elapsed', EXTRACT(DAYS FROM (now() - created_at)),
      'compliance_score', compliance_score
    )::text
  ) AS briefing
FROM analytics_cases
WHERE sla_status = 'at_risk'
  AND created_at > now() - interval '7 days';
```

This is ultra-impressive for Alibaba SA judges — shows deep integration.

## OSS bucket structure

```
s3://govflow-prod/
├── bundles/
│   └── {case_id}/
│       ├── {doc_id}_original.{ext}
│       ├── {doc_id}_ocr.json
│       └── metadata.json
├── drafts/
│   └── {case_id}/
│       ├── {draft_id}.md
│       └── {draft_id}.pdf
├── published/
│   └── {year}/{month}/
│       └── {doc_number}.pdf      (signed + immutable)
├── templates/
│   └── nd30/
│       ├── quyet_dinh_cpxd.jinja
│       └── ...
└── audit_archives/
    └── {year}/{month}/
        └── audit_{date}.jsonl   (compressed audit log archive)
```

### Bucket policies

- **bundles/** — SSE-KMS, time-limited signed URLs only, lifecycle: 1 year → archive, 7 year → delete
- **drafts/** — SSE-KMS, revocable URLs
- **published/** — **Write once, immutable.** SSE-KMS. Lifecycle: 10 years retention per NĐ 30/2020.
- **templates/** — read-only for agents, admin write
- **audit_archives/** — WORM (Write Once Read Many), 10+ year retention

### Presigned URL pattern

```python
# For upload (citizen)
url = oss_client.presign_put(
    bucket='govflow-prod',
    key=f'bundles/{case_id}/{doc_id}_original.pdf',
    expires=300,  # 5 minutes
    content_type='application/pdf',
    max_size_bytes=50_000_000
)

# For download (signed URL, short-lived)
url = oss_client.presign_get(
    bucket='govflow-prod',
    key=f'published/{year}/{month}/{doc_number}.pdf',
    expires=600  # 10 minutes
)
```

## Data flow diagram

```
                    ┌─────────────────────────────┐
                    │    CITIZEN PORTAL / UI      │
                    └──────┬──────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        ┌──────────┐              ┌─────────┐
        │ FastAPI  │              │   OSS   │
        │  API GW  │              │ (blobs) │
        └─────┬────┘              └─────────┘
              │
   ┌──────────┼──────────┬────────────┐
   ▼          ▼          ▼            ▼
┌──────┐  ┌────────┐  ┌────────┐  ┌────────┐
│ GDB  │  │ Holo   │  │ Notify │  │Orchest.│
│(KG+  │  │(OLAP + │  │service │  │        │
│ CG)  │  │ vector)│  │        │  │        │
└──────┘  └────┬───┘  └────────┘  └────┬───┘
               │                        │
               │         ┌──────────────┘
               │         │
               ▼         ▼
           ┌────────────────┐
           │  Model Studio  │
           │  Qwen3 family  │
           └────────────────┘
               │
               │ AI Functions
               ▼
           (back to Hologres
            for in-SQL LLM)
```

## Write path — sequence

**Citizen uploads bundle:**

1. Frontend → FastAPI `POST /cases` with bundle metadata
2. FastAPI returns presigned OSS URLs
3. Frontend uploads blobs directly to OSS (bypass backend)
4. Frontend → FastAPI `POST /cases/{id}/finalize` (bundle upload done)
5. FastAPI writes:
   - GDB: `Case`, `Bundle`, `Document` vertices + edges
   - Hologres `analytics_cases`: insert row
6. FastAPI triggers `Orchestrator.run(case_id)` async
7. Agents write to GDB as they work
8. AuditEvents projected to `audit_events_flat` via CDC (5-min delay OK)
9. Analytics refreshed from GDB → `analytics_cases` every 5 min (or on-demand for leadership)

## Read path — examples

### Citizen tracks status
```python
# FastAPI /public/cases/{code}
case = gdb.query_template(
    "case.get_public_status",
    {"case_code": public_code}
)
# Returns only public-safe fields (no PII, no internal notes)
```

### Leadership dashboard load
```python
# FastAPI /leadership/dashboard
# Pure Hologres query — fast analytics
rows = hologres.execute("""
    SELECT tthc_code, tthc_name, status, sla_status, count(*)
    FROM analytics_cases
    WHERE current_owner_dept = $1
      AND created_at > now() - interval '30 days'
    GROUP BY 1,2,3,4
""", [user_department])
```

### Agent Compliance check
```python
# Agent runtime with permissioned GDB client
client = gdb_client_for_agent(agent='Compliance')
missing = await client.execute(
    "case.find_missing_components",
    {"case_id": case_id}
)
# SDK Guard checked scope, returns filtered results
```

## Backup + disaster recovery

### GDB
- **Alibaba Cloud GDB automated daily snapshots**
- **Point-in-time restore** available
- **Cross-region replication** for PoC (production only)

### Hologres
- **Automated daily backups** to OSS
- **Point-in-time recovery**
- **Read replicas** for analytics isolation

### OSS
- **Versioning enabled** on `published/` bucket
- **Cross-region replication** to Hangzhou for DR
- **WORM lock** on audit archives

## Data retention policies

| Data type | Retention | Justification |
|---|---|---|
| Active Case in GDB | 1 year active | NĐ 61/2018 + operational need |
| Archived Case | 10 years | Luật BVBMNN 2018 + administrative law |
| AuditEvents | 10 years | Luật BVBMNN 2018 forensic requirement |
| Published docs | 10+ years | NĐ 30/2020 + state archives |
| Bundles (raw) | 5 years | Standard retention |
| Analytics aggs | 3 years | Rolling window |
| Law chunks (KG) | Indefinite | Reference data, versioned |

## Scaling considerations

### Hackathon demo
- Single GDB small instance
- Single Hologres small
- Single OSS bucket
- Single FastAPI ECS instance

### PoC 1 Sở
- Same instances, ~5–10GB data
- Hologres compute nodes 2
- ECS backend: 2 vCPU, 8GB

### 10 Sở multi-tenant
- GDB larger instance with shards
- Hologres compute nodes 4, storage 100GB
- ECS ASG 3 instances with load balancer
- Consider graph sharding per tenant

### 63 tỉnh national
- Federated GDB architecture
- Central KG (shared), per-tenant CG
- Hologres cluster
- Multi-region deployment
