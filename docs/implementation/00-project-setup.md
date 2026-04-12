# 00 - Project Setup: Monorepo, Dependencies, Docker Compose

## Muc tieu (Objective)

Initialize the GovFlow monorepo structure, install all Python and Node dependencies,
configure Docker Compose for local development, and establish environment configuration.
After completing this guide, `docker compose up` starts all infrastructure,
the backend serves on :8000, and the frontend on :3000.

---

## 1. Monorepo Directory Tree

Create the full directory structure first. Every subsequent implementation doc
references these paths.

```
GovFlow/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app factory
│   │   ├── config.py            # Pydantic Settings
│   │   ├── auth.py              # JWT encode/decode, dependency
│   │   ├── database.py          # GDB, Hologres, OSS connection factories
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── cases.py         # /cases routes
│   │   │   ├── documents.py     # /documents routes
│   │   │   ├── agents.py        # /agents routes
│   │   │   ├── graph.py         # /graph routes
│   │   │   ├── search.py        # /search routes
│   │   │   ├── notifications.py # /notifications routes
│   │   │   ├── leadership.py    # /leadership routes
│   │   │   ├── audit.py         # /audit routes
│   │   │   ├── public.py        # /public routes (no auth)
│   │   │   └── ws.py            # WebSocket handler
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # BaseAgent ABC
│   │   │   ├── orchestrator.py  # AgentRuntime, DAG dispatch
│   │   │   ├── mcp_server.py    # MCP tool registry
│   │   │   ├── qwen_client.py   # DashScope OpenAI-compat wrapper
│   │   │   └── profiles/        # YAML agent profiles
│   │   │       ├── intake_agent.yaml
│   │   │       ├── classifier_agent.yaml
│   │   │       ├── extraction_agent.yaml
│   │   │       ├── gap_agent.yaml
│   │   │       ├── legal_search_agent.yaml
│   │   │       ├── compliance_agent.yaml
│   │   │       ├── summary_agent.yaml
│   │   │       ├── draft_agent.yaml
│   │   │       ├── review_agent.yaml
│   │   │       └── publish_agent.yaml
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   └── templates.py     # 30 Gremlin query templates
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py       # Pydantic v2 request/response models
│   │   │   └── enums.py         # Shared enums (CaseStatus, Role, etc.)
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── permission.py    # 3-tier permission engine
│   │       └── embedding.py     # Qwen3-Embedding calls
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_cases.py
│   │   └── test_agents.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── (dashboard)/
│   │   │   ├── (cases)/
│   │   │   ├── (agents)/
│   │   │   ├── (graph)/
│   │   │   ├── (leadership)/
│   │   │   ├── (public)/
│   │   │   └── api/              # Next.js API routes (proxy)
│   │   ├── components/
│   │   │   ├── ui/               # shadcn/ui components
│   │   │   ├── graph/            # React Flow graph components
│   │   │   ├── cases/            # Case-related components
│   │   │   └── agents/           # Agent trace/status components
│   │   ├── lib/
│   │   │   ├── api.ts            # fetch wrapper, auth headers
│   │   │   ├── ws.ts             # WebSocket client
│   │   │   ├── store.ts          # Zustand stores
│   │   │   └── utils.ts
│   │   └── hooks/
│   │       ├── use-cases.ts
│   │       ├── use-agents.ts
│   │       └── use-ws.ts
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml
│   ├── gremlin-server/
│   │   └── gremlin-server.yaml   # TinkerGraph config
│   ├── postgres/
│   │   └── init.sql              # Hologres-equivalent DDL
│   └── minio/
│       └── init.sh               # Bucket creation script
├── data/
│   ├── laws/                     # Raw legal JSON/JSONL
│   ├── tthc/                     # TTHC procedure specs
│   ├── templates/                # ND30 templates
│   └── seed/                     # Seed data (users, orgs)
├── scripts/
│   ├── ingest_legal.py           # Law -> GDB + Hologres
│   ├── ingest_tthc.py            # TTHC -> GDB
│   ├── seed_users.py             # Create test users
│   └── embed_chunks.py           # Chunk + embed law articles
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

### Shell command to scaffold:

```bash
cd /home/logan/GovTrack

# Backend
mkdir -p backend/src/{api,agents/profiles,graph,models,services}
mkdir -p backend/tests
touch backend/src/__init__.py backend/src/api/__init__.py \
      backend/src/agents/__init__.py backend/src/graph/__init__.py \
      backend/src/models/__init__.py backend/src/services/__init__.py \
      backend/tests/__init__.py

# Frontend
mkdir -p frontend/src/{app/{\"(dashboard)\",\"(cases)\",\"(agents)\",\"(graph)\",\"(leadership)\",\"(public)\",api},components/{ui,graph,cases,agents},lib,hooks}
mkdir -p frontend/public

# Infra
mkdir -p infra/{gremlin-server,postgres,minio}

# Data + Scripts
mkdir -p data/{laws,tthc,templates,seed}
mkdir -p scripts
```

---

## 2. Backend: pyproject.toml

Write to `backend/pyproject.toml`:

```toml
[project]
name = "govflow-backend"
version = "0.1.0"
description = "GovFlow Agentic GraphRAG Backend"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "gremlinpython>=3.7.0",
    "openai>=1.0",
    "oss2>=2.18",
    "asyncpg>=0.30.0",
    "websockets>=14.0",
    "python-jose[cryptography]>=3.3",
    "slowapi>=0.1.9",
    "pyyaml>=6.0",
    "httpx>=0.28.0",
    "jinja2>=3.1",
    "python-multipart>=0.0.18",
    "aiofiles>=24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
    "httpx>=0.28",
    "ruff>=0.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Install:

```bash
cd /home/logan/GovTrack/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## 3. Frontend: package.json

Write to `frontend/package.json`:

```json
{
  "name": "govflow-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "^15.3.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@xyflow/react": "^12.6.0",
    "framer-motion": "^12.0.0",
    "@tanstack/react-query": "^5.68.0",
    "zustand": "^5.0.0",
    "recharts": "^2.15.0",
    "lucide-react": "^0.475.0",
    "sonner": "^2.0.0",
    "react-pdf": "^9.2.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^3.0.0",
    "class-variance-authority": "^0.7.1",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-toast": "^1.2.0",
    "@radix-ui/react-tooltip": "^1.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-separator": "^1.1.0",
    "@radix-ui/react-avatar": "^1.1.0",
    "@radix-ui/react-badge": "^1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@types/node": "^22.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.5.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.3.0",
    "@eslint/eslintrc": "^3.0.0"
  }
}
```

### Install:

```bash
cd /home/logan/GovTrack/frontend
npm install
```

### Tailwind v4 setup (`frontend/postcss.config.mjs`):

```js
/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};
export default config;
```

### Tailwind config (`frontend/src/app/globals.css`):

```css
@import "tailwindcss";
```

### Next.js config (`frontend/next.config.ts`):

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;
```

---

## 4. Docker Compose: infra/docker-compose.yml

Write to `infra/docker-compose.yml`:

```yaml
version: "3.9"

services:
  # --- GDB local fallback: Apache TinkerPop Gremlin Server ---
  gremlin-server:
    image: tinkerpop/gremlin-server:3.7.3
    container_name: govflow-gremlin
    ports:
      - "8182:8182"
    volumes:
      - ./gremlin-server/gremlin-server.yaml:/opt/gremlin-server/conf/gremlin-server.yaml
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8182/ || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  # --- Hologres local fallback: PostgreSQL 16 with pgvector ---
  postgres:
    image: pgvector/pgvector:pg16
    container_name: govflow-postgres
    environment:
      POSTGRES_DB: govflow
      POSTGRES_USER: govflow
      POSTGRES_PASSWORD: govflow_dev_2026
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U govflow -d govflow"]
      interval: 5s
      timeout: 3s
      retries: 5

  # --- OSS local fallback: MinIO ---
  minio:
    image: minio/minio:latest
    container_name: govflow-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - miniodata:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 3

  # --- MinIO bucket initialization ---
  minio-init:
    image: minio/mc:latest
    container_name: govflow-minio-init
    depends_on:
      minio:
        condition: service_healthy
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minioadmin123;
      mc mb --ignore-existing local/govflow-dev;
      mc mb --ignore-existing local/govflow-dev/bundles;
      mc mb --ignore-existing local/govflow-dev/drafts;
      mc mb --ignore-existing local/govflow-dev/published;
      mc mb --ignore-existing local/govflow-dev/templates;
      mc mb --ignore-existing local/govflow-dev/audit-archives;
      echo 'MinIO buckets created';
      "

volumes:
  pgdata:
  miniodata:
```

### Gremlin Server config (`infra/gremlin-server/gremlin-server.yaml`):

```yaml
host: 0.0.0.0
port: 8182
evaluationTimeout: 30000
channelizer: org.apache.tinkerpop.gremlin.server.channel.WebSocketChannelizer
graphs:
  graph: conf/tinkergraph-empty.properties
scriptEngines:
  gremlin-groovy:
    plugins:
      org.apache.tinkerpop.gremlin.server.jsr223.GremlinServerGremlinPlugin: {}
      org.apache.tinkerpop.gremlin.tinkergraph.jsr223.TinkerGraphGremlinPlugin: {}
      org.apache.tinkerpop.gremlin.jsr223.ImportGremlinPlugin:
        classImports:
          - java.lang.Math
        methodImports:
          - java.lang.Math#*
      org.apache.tinkerpop.gremlin.jsr223.ScriptFileGremlinPlugin:
        files: []
serializers:
  - className: org.apache.tinkerpop.gremlin.util.ser.GraphSONMessageSerializerV3
    config:
      ioRegistries:
        - org.apache.tinkerpop.gremlin.tinkergraph.structure.TinkerIoRegistryV3
  - className: org.apache.tinkerpop.gremlin.util.ser.GraphBinaryMessageSerializerV4
```

---

## 5. Environment Configuration

Write to `.env.example`:

```bash
# ============================================================
# GovFlow Environment Configuration
# Copy to .env and fill in values
# ============================================================

# --- Environment mode ---
GOVFLOW_ENV=local          # local | cloud

# --- GDB (Gremlin) ---
GDB_ENDPOINT=ws://localhost:8182/gremlin
GDB_USERNAME=
GDB_PASSWORD=

# --- Hologres / PostgreSQL ---
HOLOGRES_DSN=postgresql://govflow:govflow_dev_2026@localhost:5432/govflow

# --- DashScope (Qwen AI) ---
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1

# --- OSS / MinIO ---
OSS_ENDPOINT=http://localhost:9000
OSS_ACCESS_KEY_ID=minioadmin
OSS_ACCESS_KEY_SECRET=minioadmin123
OSS_BUCKET=govflow-dev
OSS_REGION=us-east-1

# --- JWT ---
JWT_SECRET=dev-secret-change-in-production-2026
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480

# --- CORS ---
CORS_ORIGINS=http://localhost:3000

# --- Rate Limiting ---
RATE_LIMIT_DEFAULT=60/minute
RATE_LIMIT_SEARCH=30/minute

# --- Logging ---
LOG_LEVEL=DEBUG
```

### Copy and customize:

```bash
cp .env.example .env
# Edit .env: at minimum set DASHSCOPE_API_KEY
```

---

## 6. .gitignore

Write to `.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.venv/
*.egg
.pytest_cache/
.ruff_cache/

# Node
node_modules/
.next/
out/
.turbo/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker volumes
pgdata/
miniodata/

# Data artifacts (keep structure, ignore large files)
data/laws/*.jsonl
data/tthc/*.jsonl
data/embeddings/

# Logs
*.log
logs/
```

---

## 7. Minimal Backend Entrypoint

Write `backend/src/config.py` (needed to verify imports):

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """GovFlow configuration loaded from environment variables."""

    govflow_env: str = "local"

    # GDB
    gdb_endpoint: str = "ws://localhost:8182/gremlin"
    gdb_username: str = ""
    gdb_password: str = ""

    # Hologres / PostgreSQL
    hologres_dsn: str = "postgresql://govflow:govflow_dev_2026@localhost:5432/govflow"

    # DashScope
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    # OSS / MinIO
    oss_endpoint: str = "http://localhost:9000"
    oss_access_key_id: str = "minioadmin"
    oss_access_key_secret: str = "minioadmin123"
    oss_bucket: str = "govflow-dev"
    oss_region: str = "us-east-1"

    # JWT
    jwt_secret: str = "dev-secret-change-in-production-2026"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_default: str = "60/minute"
    rate_limit_search: str = "30/minute"

    # Logging
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

Write `backend/src/main.py` (stub to verify startup):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to GDB, Hologres, OSS on startup; close on shutdown."""
    # Connections initialized in 01-infrastructure.md
    print(f"[GovFlow] Starting in {settings.govflow_env} mode")
    yield
    print("[GovFlow] Shutting down")


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

    # Routes registered in 03-backend-api.md
    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
```

---

## 8. Verification Checklist

Run each check and confirm the expected result.

### 8.1 Docker Compose starts all services

```bash
cd /home/logan/GovTrack/infra
docker compose up -d
docker compose ps
# Expected: gremlin-server (healthy), postgres (healthy), minio (healthy)
```

### 8.2 Gremlin Server responds

```bash
# Using websocat or curl
curl -s http://localhost:8182/?gremlin=g.V().count()
# Expected: {"result":{"data":{"@type":"g:List","@value":[{"@type":"g:Int64","@value":0}]}}}
```

### 8.3 PostgreSQL accessible

```bash
psql postgresql://govflow:govflow_dev_2026@localhost:5432/govflow -c "SELECT 1;"
# Expected: 1
```

### 8.4 MinIO accessible

```bash
curl -s http://localhost:9000/minio/health/live
# Expected: HTTP 200
```

### 8.5 Python imports resolve

```bash
cd /home/logan/GovTrack/backend
source .venv/bin/activate
python -c "
import fastapi; import uvicorn; import pydantic
import gremlin_python; import openai; import oss2
import asyncpg; import websockets; import jose
import slowapi; import yaml; import httpx; import jinja2
print('All Python imports OK')
"
```

### 8.6 Backend serves

```bash
cd /home/logan/GovTrack/backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl -s http://localhost:8000/health
# Expected: {"status":"ok","env":"local"}
kill %1
```

### 8.7 Frontend builds

```bash
cd /home/logan/GovTrack/frontend
npm run dev &
sleep 5
curl -s http://localhost:3000 | head -20
# Expected: HTML content from Next.js
kill %1
```

---

## Tong ket (Summary)

After completing this guide you have:

| Component         | Status                          |
|-------------------|---------------------------------|
| Monorepo tree     | All directories created         |
| Backend deps      | Installed in .venv              |
| Frontend deps     | Installed via npm               |
| Docker services   | Gremlin + Postgres + MinIO up   |
| Env config        | .env.example copied to .env     |
| Health endpoint   | /health returns OK              |

Next step: proceed to `01-infrastructure.md` for cloud provisioning or Docker fallback wiring.
