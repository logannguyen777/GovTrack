You are setting up the GovFlow monorepo from scratch. Follow docs/implementation/00-project-setup.md as the detailed guide.

Task: $ARGUMENTS (default: full project setup)

## What You Build

A monorepo with Python backend (FastAPI), TypeScript frontend (Next.js 15), Docker Compose for local dev, and all configuration files.

## Steps

1. **Create monorepo directory structure:**
   ```
   backend/src/{api,agents/profiles,graph,services}
   backend/tests/{unit,integration,tthc,api}
   frontend/ (via create-next-app)
   infra/
   ```

2. **Backend setup (Python 3.11+):**
   - Create `backend/pyproject.toml` with dependencies:
     fastapi, uvicorn[standard], pydantic>=2.0, gremlinpython>=3.7, openai>=1.0, oss2, asyncpg, websockets, python-jose[cryptography], slowapi, pyyaml, httpx, jinja2, python-multipart
   - Create venv: `cd backend && python -m venv .venv && .venv/bin/pip install -e .`
   - Create `backend/src/__init__.py` and all subpackage `__init__.py` files

3. **Frontend setup:**
   - `npx create-next-app@15 frontend --typescript --tailwind --app --src-dir --no-import-alias`
   - Install: `npm i @xyflow/react framer-motion @tanstack/react-query zustand recharts lucide-react sonner react-pdf dagre @types/dagre`
   - Install shadcn: `npx shadcn@latest init` then add components: button, badge, card, dialog, sheet, tabs, command, input, label, separator, skeleton, toast, dropdown-menu, avatar, scroll-area, tooltip

4. **Docker Compose (infra/docker-compose.yml):**
   - `gremlin-server`: image tinkerpop/gremlin-server:3.7.3, port 8182
   - `postgres`: image postgres:16, port 5432, db=govflow, user=govflow, pass=govflow
   - `minio`: image minio/minio, ports 9000+9001, MINIO_ROOT_USER/PASSWORD

5. **Environment config:**
   - Create `.env.example` with: GDB_ENDPOINT, GDB_USERNAME, GDB_PASSWORD, HOLOGRES_DSN, OSS_ENDPOINT, OSS_ACCESS_KEY, OSS_SECRET_KEY, OSS_BUCKET, DASHSCOPE_API_KEY, JWT_SECRET, GOVFLOW_ENV
   - Copy to `backend/.env` and `frontend/.env.local`

6. **Git:**
   - Create `.gitignore` (Python venv, node_modules, .env, __pycache__, .next, *.pyc)
   - `git init && git add -A && git commit -m "feat: initialize GovFlow monorepo"`

## Conventions
- Python: async everywhere, pydantic v2 for validation
- TypeScript: strict mode, no `any`
- All user-facing text in Vietnamese with diacritics
- Never commit secrets

## Verification
```bash
cd backend && .venv/bin/python -c "import fastapi, gremlin_python; print('OK')"
cd frontend && npm run build
docker compose -f infra/docker-compose.yml up -d && sleep 5
python -c "from gremlin_python.driver import client; c = client.Client('ws://localhost:8182/gremlin','g'); print(c.submit('g.V().count()').all().result())"
```
