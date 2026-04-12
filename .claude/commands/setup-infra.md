You are configuring GovFlow infrastructure connections and verifying connectivity. Follow docs/implementation/01-infrastructure.md as the detailed guide.

Task: $ARGUMENTS (default: full infrastructure setup)

## What You Build

Connection factories for GDB, Hologres, and OSS. Hologres schema. Infrastructure verification.

## Steps

1. **Create `backend/src/database.py`** — connection factories:
   ```python
   # GDB: gremlinpython DriverRemoteConnection
   # Hologres: asyncpg pool
   # OSS: oss2.Auth + oss2.Bucket
   # All configured via backend/src/config.py (pydantic Settings)
   ```

2. **Create `backend/src/config.py`** — Pydantic Settings:
   - Load from .env: GDB_ENDPOINT, GDB_USERNAME, GDB_PASSWORD, HOLOGRES_DSN, OSS_ENDPOINT, OSS_ACCESS_KEY, OSS_SECRET_KEY, OSS_BUCKET, DASHSCOPE_API_KEY, JWT_SECRET, GOVFLOW_ENV
   - Local defaults: GDB=ws://localhost:8182/gremlin, HOLOGRES=postgresql://govflow:govflow@localhost:5432/govflow

3. **Create `infra/hologres-schema.sql`** — full DDL from docs/03-architecture/data-model.md:
   - Tables: users, law_chunks (with Proxima vector index on FLOAT4[1536]), analytics_cases, analytics_agents, notifications, audit_events_flat, templates_nd30
   - For local Postgres: skip Proxima-specific syntax, use pgvector extension instead

4. **Run Hologres DDL:**
   ```bash
   psql "$HOLOGRES_DSN" -f infra/hologres-schema.sql
   ```

5. **Create OSS bucket structure** (or MinIO equivalent):
   - Folders: bundles/, drafts/, published/, templates/nd30/, audit_archives/

6. **Test DashScope connectivity:**
   ```python
   from openai import OpenAI
   client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
   resp = client.chat.completions.create(model="qwen-max-latest", messages=[{"role":"user","content":"Hello"}])
   print(resp.choices[0].message.content)
   ```

## Conventions
- Use env vars for all credentials, never hardcode
- GOVFLOW_ENV=local uses Docker services, GOVFLOW_ENV=cloud uses Alibaba Cloud
- Connection factories should be async-compatible and return pooled connections

## Spec References
- docs/03-architecture/data-model.md — Hologres DDL
- docs/03-architecture/alibaba-cloud-stack.md — Cloud service details

## Verification
```bash
# GDB connects
python -c "from gremlin_python.driver.client import Client; c=Client('ws://localhost:8182/gremlin','g'); print(c.submit('g.V().count()').all().result())"
# Hologres connects
psql "$HOLOGRES_DSN" -c "SELECT count(*) FROM users"
# OSS/MinIO connects
python -c "import oss2; print('OSS OK')"
# DashScope responds
python -c "from openai import OpenAI; c=OpenAI(base_url='https://dashscope-intl.aliyuncs.com/compatible-mode/v1'); print('DashScope OK')"
```
