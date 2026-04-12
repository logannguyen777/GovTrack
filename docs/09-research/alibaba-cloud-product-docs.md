# Alibaba Cloud Product Docs — Links + Key Facts

Quick reference for Alibaba Cloud products GovFlow uses.

## Alibaba Cloud Model Studio

**Overview:** https://modelstudio.alibabacloud.com/
**Docs:** https://www.alibabacloud.com/help/en/model-studio

### Key features
- Hosted Qwen3 models: Qwen3-Max, Qwen3-VL, Qwen3-Embedding
- OpenAI-compatible API (use OpenAI SDK)
- Function calling (tools)
- MCP (Model Context Protocol) support
- DashScope SDK for Python
- Singapore region (closest to Vietnam)
- Pay-per-token pricing

### Qwen3 models (as of 2026)
- `qwen-max` / `qwen-max-latest` — flagship reasoning model, 30k context
- `qwen-vl-max` / `qwen-vl-plus` — multimodal OCR + layout + visual understanding
- `qwen-embedding-v3` / `text-embedding-v3` — embeddings for semantic search
- `qwen-turbo` — faster/cheaper for simple tasks
- `qwen3-coder` — specialized for code (not used in GovFlow)

### API endpoint (OpenAI-compatible)
```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

### Authentication
- API key via DashScope console
- Store in env var `DASHSCOPE_API_KEY`

### Sample call (Python)
```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ['DASHSCOPE_API_KEY'],
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-max-latest",
    messages=[
        {"role": "system", "content": "You are a compliance officer."},
        {"role": "user", "content": "Check this case..."}
    ],
    tools=[...],  # function calling
    tool_choice="auto"
)
```

### Pricing (approximate, per 1M tokens)
- Qwen3-Max input: ~$4
- Qwen3-Max output: ~$12
- Qwen3-VL: similar
- Qwen3-Embedding: ~$0.05

### Quick start
1. Create Alibaba Cloud account
2. Activate Model Studio
3. Generate API key
4. Test with OpenAI SDK

## Alibaba Cloud GDB (Graph Database)

**Overview:** https://www.alibabacloud.com/en/product/gdb
**Docs:** https://www.alibabacloud.com/help/en/gdb

### Key features
- Fully managed graph database service
- Compatible with Apache TinkerPop 3.x (Gremlin)
- Supports openCypher (limited)
- VPC-native deployment
- Enterprise ACL (paid tiers)
- Automated backups
- Single-AZ or multi-AZ

### Gremlin compatibility
- TinkerPop 3.4+
- Full Gremlin traversal language
- Bulk import via CSV / JSON
- Gremlin Console for ad-hoc queries
- Python driver: `gremlinpython`

### Connection (Python)
```python
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal

endpoint = 'ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin'
conn = DriverRemoteConnection(
    endpoint,
    'g',
    username=os.environ['GDB_USERNAME'],
    password=os.environ['GDB_PASSWORD']
)
g = traversal().withRemote(conn)

# Query
result = g.V().hasLabel('Case').has('id', 'C-001').toList()
```

### Sizing for hackathon
- **Small tier:** ~2 vCPU, 4GB RAM — enough for ~100k vertices
- Estimated cost: ~$30/month for hackathon duration

### Limitations for hackathon
- Provision time: ~10 minutes
- Access requires Alibaba Cloud account + VPC setup
- Enterprise ACL (for 3-tier RBAC) might require paid tier

### Mitigation
- Use `gremlin-server` + TinkerGraph locally for fast iteration
- Deploy to GDB for integration testing + demo
- Simulate ACL at SDK Guard layer if GDB ACL not available in small tier

## Hologres

**Overview:** https://www.alibabacloud.com/en/product/hologres
**Docs:** https://www.alibabacloud.com/help/en/hologres

### Key features
- PostgreSQL-compatible interface
- Real-time OLAP engine
- Built-in **Proxima vector search** (no separate vector DB)
- **AI Functions** — call Model Studio directly in SQL
- MaxCompute integration
- Columnar storage for analytics
- Auto-scaling compute

### Connection (Python)
```python
import psycopg2

conn = psycopg2.connect(
    host='hgcn-xxx.hologres.aliyuncs.com',
    port=80,
    user=os.environ['HOLOGRES_USER'],
    password=os.environ['HOLOGRES_PASSWORD'],
    database='govflow'
)
```

### Proxima vector index
```sql
-- Create table with vector column
CREATE TABLE law_chunks(
  id serial PRIMARY KEY,
  law_code TEXT,
  article_num INT,
  text TEXT,
  embedding FLOAT4[1536]
);

-- Create Proxima index
CALL set_table_property('law_chunks', 'proxima_vectors',
  '{"embedding":{"algorithm":"Graph","metric":"Cosine"}}');

-- Query
SELECT *, pm_approx_inner_product(embedding, '[0.1, 0.2, ...]') AS score
FROM law_chunks
ORDER BY embedding <=> '[0.1, 0.2, ...]'
LIMIT 10;
```

### AI Functions (pitch-worthy feature)
```sql
-- Call Qwen3-Max directly in SQL
SELECT case_id,
       ai_generate_text('qwen-max', 'Summarize: ' || details) AS summary
FROM cases_details
WHERE updated_at > now() - interval '1 day';
```

**Note:** AI Functions require Hologres ↔ Model Studio integration enabled.

### Sizing
- **Small instance:** 4-core compute, 40GB storage
- Estimated cost: ~$50/month

**Docs:** https://www.alibabacloud.com/help/en/hologres/user-guide/supported-models-from-alibaba-cloud-model-studio

## Alibaba Cloud OSS (Object Storage Service)

**Overview:** https://www.alibabacloud.com/en/product/oss
**Docs:** https://www.alibabacloud.com/help/en/oss

### Key features
- S3-compatible API
- SSE-KMS encryption
- Versioning
- Lifecycle policies
- Presigned URLs
- Cross-region replication
- WORM (compliance retention)

### Connection (Python)
```python
import oss2

auth = oss2.Auth(access_key_id, access_key_secret)
bucket = oss2.Bucket(auth, 'oss-ap-southeast-1.aliyuncs.com', 'govflow-prod')

# Upload
bucket.put_object('bundles/C-001/doc1.pdf', file_data)

# Generate presigned URL
url = bucket.sign_url('GET', 'bundles/C-001/doc1.pdf', 600)
```

### Key management
- Enable SSE-KMS with Alibaba Cloud KMS
- Data keys per object
- Key rotation every 90 days

## PAI (Platform for AI)

**Overview:** https://www.alibabacloud.com/product/machine-learning
**Docs:** https://www.alibabacloud.com/help/en/pai

### Key products for GovFlow

- **PAI-EAS** (Elastic Algorithm Service) — model deployment
- **PAI LangStudio** — visual agent builder
- **PAI-RAG** — managed RAG solutions
- **PAI-DLC** — training platform

### Why relevant
- Production path for on-prem deployment
- Qwen3-32B open-weight deployment via PAI-EAS
- Alternative to Model Studio for data residency cases

### Not used in hackathon
- Too complex for 6-day timeline
- Included only in architecture slide as "production roadmap"

## ECS (Elastic Compute Service)

**Overview:** https://www.alibabacloud.com/en/product/ecs

### Key specs used
- **Instance:** ecs.g7.large (2 vCPU, 8 GB RAM)
- **Region:** Singapore (ap-southeast-1)
- **OS:** Ubuntu 22.04 LTS
- **Storage:** 40GB SSD
- **Network:** VPC with SLB

### Deployment
- Docker Compose for GovFlow backend
- Caddy for TLS + reverse proxy
- Running FastAPI + background workers

## SLB (Server Load Balancer)

Used to expose FastAPI backend + frontend to internet with TLS termination.

## Alibaba Cloud SLS (Log Service)

- Centralized logging
- Real-time log processing
- Long-term log storage
- Integration with CloudMonitor for alerts

Used for: audit event projection + monitoring.

## CloudMonitor

- Resource metrics
- Custom metrics
- Alert rules

Used for: infrastructure monitoring + anomaly alerts.

## DirectMail

- SMTP service
- High deliverability
- Vietnamese content support

Used for: email notifications to civil servants.

## Networking

- **VPC** — isolated network
- **Security Groups** — firewall rules
- **NAT Gateway** — outbound only
- **PrivateLink** — secure service-to-service (production)

## Cost summary for hackathon

| Service | Tier | Est. cost (1 week) |
|---|---|---|
| GDB small | gds.small | ~$30 |
| Hologres | 4-core | ~$50 |
| ECS g7.large | 1 instance | ~$15 |
| OSS | 5GB | ~$2 |
| Model Studio | ~1M tokens | ~$30 |
| DirectMail + SLS | free tier | $0 |
| Network + misc | | ~$10 |
| **TOTAL** | | **~$137** |

Less than $150 for full hackathon. Very affordable.

## Documentation gaps

As of 2026, some Alibaba Cloud docs are more complete in Chinese than English. When English docs are thin:
- Check Chinese version: https://help.aliyun.com
- Use browser translate
- Ask on Alibaba Cloud community

## Support channels

- **Community:** https://www.alibabacloud.com/campaign/contact-us
- **Documentation:** https://www.alibabacloud.com/help
- **GitHub:** https://github.com/aliyun (SDKs)
- **Issue tracker:** per product

## Quick start for GovFlow team (day 12 morning)

1. Create Alibaba Cloud account (if not already)
2. Activate: Model Studio, GDB, Hologres, OSS, ECS
3. Get API keys for Model Studio
4. Provision GDB small + Hologres small
5. Create ECS instance in Singapore
6. Create OSS bucket + security config
7. Generate all necessary API keys / credentials
8. Store in env vars / `.env` file

Estimated time: 2–3 hours for all provisioning + initial config.
