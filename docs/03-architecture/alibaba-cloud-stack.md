# Alibaba Cloud Stack — Product mapping & rationale

Full commitment to Alibaba Cloud from day 1. Không hybrid. Lý do: max điểm "Use of Alibaba Cloud" cho judge Alibaba SA + production story thuyết phục VC.

## Product mapping

| GovFlow component | Alibaba Cloud product | Why this product |
|---|---|---|
| Knowledge Graph + Context Graph | **Alibaba Cloud GDB (Graph Database)** | Fully managed, TinkerPop/Gremlin, VPC-native, enterprise ACL |
| Relational data + Vector search | **Hologres** | PG-compatible, built-in Proxima vector, **AI Functions** (call Qwen in SQL) |
| LLM inference (text + vision) | **Alibaba Cloud Model Studio** | Qwen3-Max, Qwen3-VL-Plus, Qwen3-Embedding; function calling + MCP support |
| Blob storage | **Alibaba Cloud OSS** | SSE-KMS, lifecycle policy, presigned URLs |
| Compute (backend + workers) | **Alibaba Cloud ECS** | Singapore region (low latency to VN), VPC |
| Container orchestration (prod) | **ACK (Container Service for Kubernetes)** | Future scaling |
| Message queue | **MQ for RocketMQ** (optional) | Async task dispatch at scale |
| Scheduled jobs | **Cron-like via backend** | For KG refresh, analytics rollup |
| Email / DirectMail | **Alibaba Cloud DirectMail** | Outbound notifications to civil servants |
| SMS | **Alibaba Cloud SMS** | Citizen notifications |
| Object key management | **Alibaba Cloud KMS** | Encryption keys for OSS SSE-KMS + secrets |
| Secrets management | **KMS Secrets** or Parameter Store | API credentials, DB passwords |
| Logging + monitoring | **SLS (Log Service)** + **CloudMonitor** | Centralized logs + metrics |
| CDN (static assets) | **Alibaba Cloud CDN** | Frontend static serving |
| Load balancer | **SLB** or **ALB** | HA for backend |
| DNS | **Alibaba Cloud DNS** | Custom domain |

## Deep dives

### Alibaba Cloud GDB (Graph Database)

**Product page:** https://www.alibabacloud.com/en/product/gdb

**Key features:**
- Fully managed graph database
- Compatible với Apache TinkerPop 3.x (Gremlin)
- Supports also openCypher queries
- VPC-native deployment — isolated from public internet
- Automated backups + point-in-time recovery
- Enterprise ACL (per-label grant/revoke in paid tiers)
- Connection via gremlinpython driver

**Why chosen over Neo4j:**
- Alibaba Cloud native → max integration + performance
- Enterprise support from Alibaba
- Latency optimized within Alibaba Cloud region
- Judge optics — "running on Alibaba Cloud GDB" >> "running on Neo4j"

**Development setup:**
- Day 12/04: provision GDB instance (small tier for hackathon)
- Local dev: use `gremlin-server` with TinkerGraph (in-memory) for fast iteration
- Day 13/04: switch to GDB for integration testing
- Demo: runs on GDB production

**Connection example:**
```python
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal

# Alibaba Cloud GDB endpoint (VPC-internal)
graph_url = 'ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin'
conn = DriverRemoteConnection(graph_url, 'g',
    username='agent_compliance',
    password=os.environ['GDB_PASSWORD_COMPLIANCE'])

g = traversal().withRemote(conn)

# Example query
missing = g.V().has('Case', 'id', case_id) \
    .out('MATCHES_TTHC').out('REQUIRES') \
    .where(__.not_(__.in_('SATISFIES'))) \
    .values('name').toList()
```

### Hologres

**Product page:** https://www.alibabacloud.com/en/product/hologres

**Key features:**
- PostgreSQL-compatible interface (can use psycopg2, SQLAlchemy)
- Real-time OLAP — sub-second queries on billions of rows
- **Built-in Proxima vector search engine** (no need for separate vector DB)
- **AI Functions** — call Alibaba Cloud Model Studio Qwen directly in SQL
- Integrates with MaxCompute, DataWorks, Flink
- Auto-scaling compute nodes

**Why chosen over Postgres + pgvector:**
- 1 store for relational + vector (simpler ops)
- AI Functions = killer feature for pitch ("Qwen inside SQL!")
- Alibaba Cloud native
- OLAP performance much better for analytics dashboard
- Proxima vector faster than pgvector for >1M vectors

**Development setup:**
- Day 12/04: provision Hologres small instance
- Connect via psycopg2 / asyncpg
- Schema in `data-model.md`

**AI Functions example (pitch-worthy):**
```sql
-- During demo, run this live:
SELECT
  tthc_code,
  COUNT(*) as case_count,
  ai_generate_text(
    'qwen-max',
    'Summarize trends: ' || jsonb_agg(
      jsonb_build_object(
        'status', status,
        'days_avg', avg_days
      )
    )::text
  ) as trend_summary
FROM analytics_cases
WHERE created_at > now() - interval '7 days'
GROUP BY tthc_code;
```

**→ Judge Alibaba SA will light up seeing LLM called from inside Hologres.**

### Alibaba Cloud Model Studio

**Product page:** https://www.alibabacloud.com/en/solutions/generative-ai/qwen

**Key features:**
- Hosted Qwen3 family: Qwen3-Max, Qwen3-VL, Qwen3-Embedding
- **OpenAI-compatible API** — can use OpenAI SDK
- Function calling + **MCP (Model Context Protocol)** support in Qwen3
- DashScope SDK (Alibaba official Python client)
- Integrated with Alibaba Cloud VPC (private endpoint)
- Data residency — runs in Alibaba Cloud regions (including Singapore for VN)

**Models used:**

| Model | Context length | Use in GovFlow |
|---|---|---|
| `qwen-max-latest` | 30k tokens | Planner, Classifier, Compliance, LegalLookup, Router, Consult, Summarizer, Drafter, SecurityOfficer |
| `qwen-vl-max-latest` | 30k tokens | DocAnalyzer (OCR + layout + stamp detection) |
| `qwen-embedding-v3` | 8k input | law_chunks embedding |

**Client setup:**
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ['DASHSCOPE_API_KEY'],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = await client.chat.completions.create(
    model="qwen-max-latest",
    messages=[...],
    tools=mcp_tools,  # MCP tool definitions
    tool_choice="auto"
)
```

### Alibaba Cloud OSS (Object Storage Service)

**Key features:**
- S3-compatible API
- SSE-KMS encryption at rest
- Versioning + lifecycle policies
- Presigned URLs for direct upload/download
- Bucket policies for fine-grained access
- Cross-region replication
- WORM locking (for audit archives)

**Usage:**
- Bundle raw files (citizen uploads)
- Generated draft PDFs
- Published VB (with WORM lock)
- Audit log archives (long-term)
- Template files (Jinja)

**Setup:**
```python
import oss2

auth = oss2.Auth(access_key, secret_key)
bucket = oss2.Bucket(auth, 'oss-cn-singapore.aliyuncs.com', 'govflow-prod')

# Presigned upload URL for citizen
url = bucket.sign_url('PUT', f'bundles/{case_id}/doc_1.pdf', 300,
    slash_safe=True,
    headers={'x-oss-server-side-encryption': 'KMS'})
```

### ECS (Elastic Compute Service)

**Tier choice for hackathon:**
- `ecs.g7.large` (2 vCPU, 8GB) — backend
- Region: Singapore (closest to VN for demo day latency)
- OS: Ubuntu 22.04 + Docker
- VPC: same as GDB + Hologres for internal networking

**Deployment:**
- Docker Compose for simplicity on day 14–17
- Caddy + TLS for HTTPS
- Secrets from KMS Parameter Store

### PAI-EAS (optional, production path showcase)

**What for:**
- Deploy Qwen3-32B open-weight on dedicated infrastructure (for customer with data residency requirement)
- LangStudio visual agent builder (alternative to Python)

**Why included in pitch even if not used in demo:**
- Shows **production roadmap** for when customer requires on-prem
- Demonstrates Alibaba Cloud has full spectrum from hosted to dedicated

## Integration diagram

```
                    ┌─────────────────────┐
                    │  GovFlow Frontend   │
                    │  (Next.js on CDN)   │
                    └─────────┬───────────┘
                              │ HTTPS
                              │
        ┌─────────────────────▼─────────────────────┐
        │              Alibaba Cloud SLB             │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────┐
        │          ECS (FastAPI backend)               │
        │          Region: Singapore                   │
        └─────────────┬───────────────────────────────┘
                      │ VPC-internal (private endpoint)
            ┌─────────┼─────────────┬────────┬─────────┐
            ▼         ▼             ▼        ▼         ▼
        ┌──────┐  ┌─────────┐  ┌─────────┐  ┌───┐  ┌──────┐
        │ GDB  │  │ Holog.  │  │ Model   │  │OSS│  │Direct│
        │      │  │         │  │ Studio  │  │   │  │ Mail │
        │(KG+  │  │(OLAP+   │  │(Qwen3   │  │   │  │      │
        │ CG)  │  │ Vec+AI) │  │ family) │  │   │  │      │
        └──────┘  └─────────┘  └─────────┘  └───┘  └──────┘
                       ▲
                       │ AI Functions (SQL → Qwen)
                       │
                       └──► Model Studio
                            (inline from SQL!)
```

## Cost estimate for hackathon

| Service | Tier | Est. cost (1 week) |
|---|---|---|
| GDB small | gds.cluster.small | ~$30 |
| Hologres | general compute 4-core | ~$50 |
| ECS g7.large | 1 instance | ~$15 |
| OSS | ~5GB + minimal traffic | ~$2 |
| Model Studio | pay per token (~1M tokens for dev + demo) | ~$30 |
| DirectMail + SMS | free tier sufficient | $0 |
| Data transfer + misc | | ~$10 |
| **TOTAL** | | **~$137** |

Tiny cost for hackathon. Production would be higher but still manageable for a 1-Sở PoC.

## Vietnam data residency compliance

Alibaba Cloud has:
- **Singapore region** (closest, lowest latency to VN)
- **Hong Kong region** (secondary)

For Vietnamese government data strictly requiring on-shore storage, production path:
- Use **PAI-EAS** to deploy Qwen3 open-weight on customer on-prem hardware
- Sync schema + code via **Alibaba Cloud Dedicated Region** (if available in VN) or customer own datacenter
- This is the "production roadmap" narrative in pitch

## Links for team

- Alibaba Cloud Model Studio: https://modelstudio.alibabacloud.com/
- Qwen API reference: https://www.alibabacloud.com/help/en/model-studio/qwen-api-reference/
- GDB docs: https://www.alibabacloud.com/help/en/gdb
- Hologres docs: https://www.alibabacloud.com/help/en/hologres
- OSS docs: https://www.alibabacloud.com/help/en/oss
- PAI docs: https://www.alibabacloud.com/help/en/pai
