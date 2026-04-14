# 01 - Infrastructure: Cloud Provisioning & Local Docker Fallback

> **Status: DONE** (2026-04-12)
> - [x] Docker Compose (Gremlin, PostgreSQL+pgvector, MinIO) — all healthy
> - [x] `backend/src/database.py` — connection factory (GDB, PG, OSS/MinIO)
> - [x] `backend/src/main.py` — lifespan wired with init/close
> - [x] Verification: GDB g.V().count()=[0], PG SELECT 1=1, MinIO put+sign OK
> - [x] Full lifespan startup+shutdown clean
> - [ ] DashScope — pending API key configuration
> - [ ] Alibaba Cloud provisioning — deferred to cloud deployment

## Muc tieu (Objective)

Provision Alibaba Cloud services (GDB, Hologres, OSS, ECS, Model Studio) for production,
OR configure the local Docker Compose fallback for development. Implement the connection
factory in `backend/src/database.py` that switches between environments transparently.

---

## 1. Alibaba Cloud: GDB (Graph Database Service)

### 1.1 Provision GDB Instance

```
Service:        Alibaba Cloud Graph Database (GDB)
Engine:         TinkerPop / Gremlin
Tier:           db.r6.large (2 vCPU, 16 GB) -- smallest production tier
Region:         ap-southeast-1 (Singapore)
VPC:            govflow-vpc (10.0.0.0/16)
vSwitch:        govflow-vsw-db (10.0.1.0/24, Zone A)
Security Group: sg-govflow-db
  - Inbound:    TCP 8182 from sg-govflow-app
  - Outbound:   All
Storage:        50 GB SSD (auto-expand)
Backup:         Daily, 7-day retention
```

### 1.2 GDB Security Group Rules

```bash
aliyun ecs CreateSecurityGroup \
  --RegionId ap-southeast-1 \
  --SecurityGroupName sg-govflow-db \
  --VpcId vpc-xxxxx

aliyun ecs AuthorizeSecurityGroup \
  --RegionId ap-southeast-1 \
  --SecurityGroupId sg-xxxxx \
  --IpProtocol tcp \
  --PortRange 8182/8182 \
  --SourceGroupId sg-govflow-app
```

### 1.3 Connection Details

After provisioning, note:
- **Endpoint**: `gdb-xxxxxxxx.graphdb.rds.aliyuncs.com:8182`
- **Username**: `root` (create app user via GDB console)
- **Password**: stored in env var, never committed

Set in `.env`:
```bash
GDB_ENDPOINT=wss://gdb-xxxxxxxx.graphdb.rds.aliyuncs.com:8182/gremlin
GDB_USERNAME=govflow_app
GDB_PASSWORD=<generated>
```

---

## 2. Alibaba Cloud: Hologres

### 2.1 Provision Hologres Instance

```
Service:        Hologres (Realtime Data Warehouse)
Tier:           4-core compute (32 CU)
Region:         ap-southeast-1 (Singapore)
VPC:            govflow-vpc (same VPC as GDB)
vSwitch:        govflow-vsw-db (same subnet)
Database:       govflow
Endpoint:       hgpostcn-cn-xxxxx-ap-southeast-1.hologres.aliyuncs.com:80
```

### 2.2 Enable Proxima Vector Engine

Proxima is Hologres' built-in ANN vector engine. Enable it at instance level:

```sql
-- Connect via psql to Hologres endpoint
-- Enable Proxima extension
CREATE EXTENSION IF NOT EXISTS proxima;

-- Verify
SELECT * FROM pg_extension WHERE extname = 'proxima';
```

### 2.3 Connection Details

Set in `.env`:
```bash
HOLOGRES_DSN=postgresql://govflow_app:<password>@hgpostcn-cn-xxxxx.hologres.aliyuncs.com:80/govflow
```

---

## 3. Alibaba Cloud: OSS (Object Storage Service)

### 3.1 Create Bucket

```bash
aliyun oss mb oss://govflow-prod \
  --region ap-southeast-1 \
  --acl private \
  --storage-class Standard
```

### 3.2 Enable Server-Side Encryption

```bash
aliyun oss bucket-encryption --method put \
  oss://govflow-prod \
  --sse-algorithm KMS
```

### 3.3 Lifecycle Policies

```xml
<LifecycleConfiguration>
  <Rule>
    <ID>archive-audit-90d</ID>
    <Prefix>audit-archives/</Prefix>
    <Status>Enabled</Status>
    <Transition>
      <Days>90</Days>
      <StorageClass>IA</StorageClass>
    </Transition>
    <Transition>
      <Days>365</Days>
      <StorageClass>Archive</StorageClass>
    </Transition>
  </Rule>
  <Rule>
    <ID>expire-temp-7d</ID>
    <Prefix>temp/</Prefix>
    <Status>Enabled</Status>
    <Expiration>
      <Days>7</Days>
    </Expiration>
  </Rule>
</LifecycleConfiguration>
```

### 3.4 CORS for Signed URL Direct Upload

```json
[
  {
    "AllowedOrigin": ["https://govflow.example.com"],
    "AllowedMethod": ["GET", "PUT"],
    "AllowedHeader": ["*"],
    "ExposeHeader": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

### 3.5 Connection Details

```bash
OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com
OSS_ACCESS_KEY_ID=LTAI5t...
OSS_ACCESS_KEY_SECRET=<generated>
OSS_BUCKET=govflow-prod
OSS_REGION=ap-southeast-1
```

---

## 4. Alibaba Cloud: ECS (Application Server)

```
Instance Type:  ecs.g7.large (2 vCPU, 8 GB)
Region:         ap-southeast-1
VPC:            govflow-vpc
vSwitch:        govflow-vsw-app (10.0.2.0/24, Zone A)
Security Group: sg-govflow-app
  - Inbound:    TCP 443 from 0.0.0.0/0 (via SLB)
  - Inbound:    TCP 8000 from SLB health check
  - Outbound:   All
OS:             Ubuntu 24.04 LTS
Disk:           40 GB ESSD PL1
```

---

## 5. Alibaba Cloud: Model Studio (DashScope)

### 5.1 Activate Models

Go to Alibaba Cloud Model Studio console. Activate:

| Model ID               | Use Case                          | Max Tokens |
|-------------------------|-----------------------------------|------------|
| `qwen-max-latest`      | Agent reasoning, drafting         | 32,768     |
| `qwen-vl-max-latest`   | Document OCR, image extraction    | 8,192      |
| `text-embedding-v3`    | Law chunk embeddings (1536 dim)   | 8,192      |

### 5.2 Get API Key

From Model Studio console -> API Keys -> Create Key.

```bash
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

### 5.3 Test Connection

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-xxxx",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

response = client.chat.completions.create(
    model="qwen-max-latest",
    messages=[{"role": "user", "content": "Xin chao! GovFlow san sang."}],
    max_tokens=50,
)
print(response.choices[0].message.content)
# Expected: Vietnamese greeting response

# Test embedding
emb = client.embeddings.create(
    model="text-embedding-v3",
    input="Luat Dat dai 2024",
    dimensions=1536,
)
print(f"Embedding dim: {len(emb.data[0].embedding)}")
# Expected: 1536
```

---

## 6. Local Docker Fallback

For local development, Docker Compose replaces all cloud services.
The mapping is:

| Cloud Service         | Local Equivalent                           | Port  |
|-----------------------|--------------------------------------------|-------|
| Alibaba GDB          | tinkerpop/gremlin-server:3.7.3 (TinkerGraph) | 8182  |
| Hologres + Proxima   | pgvector/pgvector:pg16                      | 5432  |
| OSS                   | MinIO                                       | 9000  |
| DashScope             | Same API (cloud-only, no local LLM)        | --    |

Start all services:

```bash
cd /home/logan/GovTrack/infra
docker compose up -d
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

Wait for health checks:

```bash
docker compose up -d --wait
# Blocks until all healthchecks pass
```

---

## 7. Connection Factory: backend/src/database.py

This is the central module that provides connections to all three data stores.
All other modules import from here.

```python
"""
backend/src/database.py
Connection factories for GDB (Gremlin), Hologres (asyncpg), and OSS.
Switches between local Docker and Alibaba Cloud based on GOVFLOW_ENV.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
import oss2
from gremlin_python.driver.client import Client as GremlinClient
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

from .config import settings

logger = logging.getLogger("govflow.database")

# ============================================================
# Singleton holders (initialized in lifespan)
# ============================================================
_gremlin_client: GremlinClient | None = None
_pg_pool: asyncpg.Pool | None = None
_oss_bucket: oss2.Bucket | None = None


# ============================================================
# GDB (Gremlin)
# ============================================================
def create_gremlin_client() -> GremlinClient:
    """Create a gremlinpython Client connected to GDB or local TinkerGraph."""
    global _gremlin_client

    url = settings.gdb_endpoint
    logger.info(f"Connecting to Gremlin at {url}")

    kwargs = {
        "url": url,
        "traversal_source": "g",
        "message_serializer": GraphSONSerializersV3d0(),
    }

    # Cloud GDB requires username/password
    if settings.govflow_env == "cloud" and settings.gdb_username:
        kwargs["username"] = settings.gdb_username
        kwargs["password"] = settings.gdb_password

    _gremlin_client = GremlinClient(**kwargs)
    return _gremlin_client


def get_gremlin_client() -> GremlinClient:
    """Return the singleton Gremlin client. Raises if not initialized."""
    if _gremlin_client is None:
        raise RuntimeError("Gremlin client not initialized. Call create_gremlin_client() first.")
    return _gremlin_client


def close_gremlin_client() -> None:
    """Close the Gremlin client."""
    global _gremlin_client
    if _gremlin_client:
        _gremlin_client.close()
        _gremlin_client = None
        logger.info("Gremlin client closed")


def gremlin_submit(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query and return results as a list."""
    client = get_gremlin_client()
    result_set = client.submit(query, bindings or {})
    return result_set.all().result()


# ============================================================
# Hologres / PostgreSQL (asyncpg)
# ============================================================
async def create_pg_pool() -> asyncpg.Pool:
    """Create an asyncpg connection pool to Hologres or local Postgres."""
    global _pg_pool

    dsn = settings.hologres_dsn
    logger.info(f"Connecting to PostgreSQL at {dsn.split('@')[1] if '@' in dsn else dsn}")

    _pg_pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    return _pg_pool


def get_pg_pool() -> asyncpg.Pool:
    """Return the singleton asyncpg pool. Raises if not initialized."""
    if _pg_pool is None:
        raise RuntimeError("PostgreSQL pool not initialized. Call create_pg_pool() first.")
    return _pg_pool


async def close_pg_pool() -> None:
    """Close the asyncpg pool."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("PostgreSQL pool closed")


@asynccontextmanager
async def pg_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool as an async context manager."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        yield conn


# ============================================================
# OSS / MinIO
# ============================================================
def create_oss_bucket() -> oss2.Bucket:
    """Create an oss2 Bucket client. Works with both OSS and MinIO."""
    global _oss_bucket

    endpoint = settings.oss_endpoint
    logger.info(f"Connecting to OSS at {endpoint}")

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)

    # MinIO requires is_cname=True to avoid virtual-hosted bucket resolution
    is_local = settings.govflow_env == "local"
    _oss_bucket = oss2.Bucket(
        auth,
        endpoint,
        settings.oss_bucket,
        is_cname=is_local,
    )
    return _oss_bucket


def get_oss_bucket() -> oss2.Bucket:
    """Return the singleton OSS bucket. Raises if not initialized."""
    if _oss_bucket is None:
        raise RuntimeError("OSS bucket not initialized. Call create_oss_bucket() first.")
    return _oss_bucket


def oss_put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload an object to OSS. Returns the object key."""
    bucket = get_oss_bucket()
    bucket.put_object(key, data, headers={"Content-Type": content_type})
    logger.info(f"Uploaded {key} ({len(data)} bytes)")
    return key


def oss_get_signed_url(key: str, expires: int = 3600) -> str:
    """Generate a pre-signed GET URL for an object."""
    bucket = get_oss_bucket()
    return bucket.sign_url("GET", key, expires)


# ============================================================
# Lifespan helpers (called from main.py)
# ============================================================
async def init_all_connections() -> None:
    """Initialize all database connections. Called during FastAPI lifespan startup."""
    create_gremlin_client()
    await create_pg_pool()
    create_oss_bucket()
    logger.info("All connections initialized")

    # Quick health check
    try:
        result = gremlin_submit("g.V().count()")
        logger.info(f"GDB vertex count: {result}")
    except Exception as e:
        logger.warning(f"GDB health check failed: {e}")

    try:
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT 1")
            logger.info(f"PostgreSQL health check: {val}")
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")


async def close_all_connections() -> None:
    """Close all database connections. Called during FastAPI lifespan shutdown."""
    close_gremlin_client()
    await close_pg_pool()
    logger.info("All connections closed")
```

---

## 8. Update main.py Lifespan

Update `backend/src/main.py` lifespan to use the connection factory:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_all_connections, close_all_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_all_connections()
    yield
    await close_all_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GovFlow API",
        description="Agentic GraphRAG for Vietnamese TTHC",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
```

---

## 9. Environment Switching

The `GOVFLOW_ENV` variable controls which infrastructure is used:

| `GOVFLOW_ENV` | GDB Endpoint             | Hologres DSN            | OSS Endpoint                   |
|---------------|--------------------------|-------------------------|--------------------------------|
| `local`       | `ws://localhost:8182/gremlin` | `postgresql://...@localhost:5432/govflow` | `http://localhost:9000` |
| `cloud`       | `wss://gdb-xxx.graphdb.rds.aliyuncs.com:8182/gremlin` | `postgresql://...@hgpostcn-xxx.hologres.aliyuncs.com:80/govflow` | `https://oss-ap-southeast-1.aliyuncs.com` |

The code in `database.py` automatically handles differences:
- Local GDB: no auth, ws:// protocol
- Cloud GDB: username/password auth, wss:// protocol
- Local MinIO: `is_cname=True` to bypass virtual-hosted bucket
- Cloud OSS: standard bucket resolution

---

## 10. Verification Checklist

### 10.1 All Docker services healthy

```bash
cd /home/logan/GovTrack/infra
docker compose up -d --wait
docker compose ps
# All services: Status = "Up ... (healthy)"
```

### 10.2 GDB connection from Python

```bash
cd /home/logan/GovTrack/backend
source .venv/bin/activate
python -c "
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client
create_gremlin_client()
result = gremlin_submit('g.V().count()')
print(f'GDB vertex count: {result}')
close_gremlin_client()
"
# Expected: GDB vertex count: [0]
```

### 10.3 Hologres/Postgres connection from Python

```bash
python -c "
import asyncio
from src.database import create_pg_pool, close_pg_pool, get_pg_pool

async def test():
    await create_pg_pool()
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        val = await conn.fetchval('SELECT 1')
        print(f'PostgreSQL result: {val}')
    await close_pg_pool()

asyncio.run(test())
"
# Expected: PostgreSQL result: 1
```

### 10.4 OSS/MinIO connection from Python

```bash
python -c "
from src.database import create_oss_bucket, oss_put_object, oss_get_signed_url
create_oss_bucket()
oss_put_object('test/hello.txt', b'GovFlow OK', 'text/plain')
url = oss_get_signed_url('test/hello.txt')
print(f'Signed URL: {url[:80]}...')
"
# Expected: Signed URL: http://localhost:9000/govflow-dev/test/hello.txt?...
```

### 10.5 DashScope returns completion

```bash
python -c "
from openai import OpenAI
from src.config import settings
client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
r = client.chat.completions.create(
    model='qwen-max-latest',
    messages=[{'role':'user','content':'Respond with: GovFlow OK'}],
    max_tokens=10,
)
print(r.choices[0].message.content)
"
# Expected: GovFlow OK (or similar)
```

### 10.6 Full lifespan startup

```bash
cd /home/logan/GovTrack/backend
source .venv/bin/activate
timeout 10 uvicorn src.main:app --host 0.0.0.0 --port 8000 || true
# Expected: logs show "All connections initialized", then timeout kills it
```

---

## Tong ket (Summary)

| Component       | Cloud                                  | Local Docker              |
|-----------------|----------------------------------------|---------------------------|
| Graph DB        | Alibaba GDB (TinkerPop)               | gremlin-server:3.7.3      |
| Vector Store    | Hologres + Proxima                     | pgvector/pgvector:pg16    |
| Object Storage  | OSS (SSE-KMS, lifecycle)               | MinIO                     |
| AI Models       | DashScope (qwen-max, qwen-vl, embed)  | DashScope (same API)      |
| Compute         | ECS g7.large                           | localhost                 |

The connection factory in `backend/src/database.py` transparently handles both environments.
Next step: proceed to `02-data-layer.md` to populate the knowledge graph and vector store.
