You are deploying GovFlow to Alibaba Cloud or managing the production environment. Follow docs/implementation/20-deploy-alibaba-cloud.md as the detailed guide.

Task: $ARGUMENTS (default: full deployment status check)

Valid arguments:
- `provision` — Provision all Alibaba Cloud services (GDB, Hologres, OSS, ECS, Model Studio)
- `setup-ecs` — Install dependencies and configure ECS instance
- `deploy-backend` — Deploy/update FastAPI backend on ECS
- `deploy-frontend` — Build and deploy Next.js frontend on ECS
- `deploy-all` — Full deploy (backend + frontend + restart)
- `populate-data` — Run KG population + embeddings + seed data on cloud
- `configure-caddy` — Set up Caddy reverse proxy with TLS
- `setup-monitoring` — Configure SLS + CloudMonitor
- `health-check` — Run full health check on all services
- `demo-mode` — Enable/disable demo mode with cached responses
- `warm-cache` — Pre-run demo scenarios to warm Qwen response cache
- `pre-demo-check` — Full pre-demo verification checklist

## Architecture on Alibaba Cloud

```
Internet → SLB/Caddy (HTTPS:443)
              ├── FastAPI backend (:8000)
              └── Next.js frontend (:3000)
                      │
         VPC (172.16.0.0/12, Singapore)
              ├── GDB (:8182) — Knowledge Graph + Context Graph
              ├── Hologres (:80) — Users, analytics, law_chunks vectors
              ├── OSS — Document blobs, templates, archives
              └── Model Studio — Qwen3-Max, VL, Embedding
```

## Key Connection Details

All credentials come from environment variables in `backend/.env`:
- **GDB**: `ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin` (VPC internal)
- **Hologres**: `postgresql://admin:pass@hgcn-xxx.hologres.aliyuncs.com:80/govflow`
- **OSS**: `oss-ap-southeast-1.aliyuncs.com`, bucket `govflow-prod`
- **DashScope**: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- **ECS**: SSH via key pair

## Deploy Commands

```bash
# Quick deploy (from local to ECS)
ssh root@$ECS_IP "cd /opt/govflow && git pull origin main"
ssh root@$ECS_IP "cd /opt/govflow/backend && .venv/bin/pip install -e ."
ssh root@$ECS_IP "cd /opt/govflow/frontend && npm ci && npm run build"
ssh root@$ECS_IP "pm2 restart all"

# Health check
curl -s https://api.govflow.demo/health | python3 -m json.tool

# View logs
ssh root@$ECS_IP "pm2 logs govflow-api --lines 50"
ssh root@$ECS_IP "pm2 logs govflow-web --lines 50"

# Restart services
ssh root@$ECS_IP "pm2 restart govflow-api"
ssh root@$ECS_IP "pm2 restart govflow-web"
```

## Conventions
- Never commit .env files or credentials
- Always test locally before deploying to cloud
- Use PM2 for process management (auto-restart on crash)
- Caddy for TLS (auto Let's Encrypt) + reverse proxy
- All data services in same VPC for low latency

## Pre-Demo Checklist
1. All services healthy (GDB, Hologres, OSS, DashScope)
2. KG populated (~2000 vertices)
3. Demo users seeded (6 users)
4. Demo scenario 1 runs E2E
5. Cache warmed for demo cases
6. Backup video on USB + laptop

## Troubleshooting
- GDB connection: check security group port 8182, same VPC
- Hologres: port is 80 not 5432, whitelist ECS IP
- Qwen rate limit: enable DEMO_MODE=true for cached responses
- Frontend build OOM: build locally, scp .next/ to ECS

## Spec References
- docs/implementation/20-deploy-alibaba-cloud.md — Full step-by-step guide
- docs/03-architecture/alibaba-cloud-stack.md — Product mapping
- docs/06-compliance/data-residency.md — Singapore vs on-prem modes
