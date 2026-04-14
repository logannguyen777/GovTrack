# 20 — Deploy lên Alibaba Cloud

> Hướng dẫn từng bước provision + deploy GovFlow lên Alibaba Cloud.
> Yêu cầu: tài khoản Alibaba Cloud đã KYC, có payment method.

## Objective

Deploy toàn bộ GovFlow stack lên Alibaba Cloud Singapore region:
- GDB (Graph Database) cho Knowledge Graph + Context Graph
- Hologres cho relational + vector + AI Functions
- OSS cho blob storage
- ECS cho backend FastAPI + frontend Next.js
- Model Studio cho Qwen3 inference
- SLB cho load balancing + TLS
- CDN cho frontend static assets (optional)

## Prerequisites

- [x] Alibaba Cloud account KYC hoàn tất
- [ ] Payment method đã add (credit card hoặc prepay)
- [ ] `docs/implementation/00-project-setup.md` hoàn thành (code ready)
- [ ] Local dev đã test thành công

## Estimated Cost

| Service | Tier | Cost/tuần | Cost/tháng |
|---------|------|-----------|------------|
| GDB | gds.cluster.small (2vCPU, 4GB) | ~$30 | ~$120 |
| Hologres | 4-core compute | ~$50 | ~$200 |
| ECS | ecs.g7.large (2vCPU, 8GB) | ~$15 | ~$60 |
| OSS | ~5GB + traffic | ~$2 | ~$8 |
| Model Studio | ~1M tokens/tuần | ~$30 | ~$120 |
| SLB | small | ~$5 | ~$20 |
| Misc (DNS, SLS, bandwidth) | | ~$5 | ~$20 |
| **TOTAL** | | **~$137/tuần** | **~$548/tháng** |

---

## Phase 1: VPC + Networking (15 phút)

### 1.1 Tạo VPC

Console: https://vpc.console.alibabacloud.com/

```
Region:         ap-southeast-1 (Singapore)
VPC Name:       govflow-vpc
IPv4 CIDR:      172.16.0.0/12
Description:    GovFlow hackathon VPC
```

### 1.2 Tạo VSwitch (subnet)

```
VSwitch Name:   govflow-vsw-a
Zone:           ap-southeast-1a
CIDR Block:     172.16.0.0/24
```

Tạo thêm 1 VSwitch cho zone b (HA nếu cần):
```
VSwitch Name:   govflow-vsw-b
Zone:           ap-southeast-1b
CIDR Block:     172.16.1.0/24
```

### 1.3 Tạo Security Groups

**SG Backend (govflow-sg-backend):**

| Direction | Protocol | Port | Source | Mô tả |
|-----------|----------|------|--------|-------|
| Inbound | TCP | 22 | Your IP | SSH |
| Inbound | TCP | 8000 | govflow-sg-slb | FastAPI from SLB |
| Inbound | TCP | 3000 | govflow-sg-slb | Next.js from SLB |
| Outbound | All | All | 0.0.0.0/0 | Internet access |

**SG Database (govflow-sg-db):**

| Direction | Protocol | Port | Source | Mô tả |
|-----------|----------|------|--------|-------|
| Inbound | TCP | 8182 | govflow-sg-backend | GDB Gremlin |
| Inbound | TCP | 80 | govflow-sg-backend | Hologres PG |
| Outbound | All | All | 0.0.0.0/0 | Model Studio access |

**SG SLB (govflow-sg-slb):**

| Direction | Protocol | Port | Source | Mô tả |
|-----------|----------|------|--------|-------|
| Inbound | TCP | 443 | 0.0.0.0/0 | HTTPS public |
| Inbound | TCP | 80 | 0.0.0.0/0 | HTTP redirect |

---

## Phase 2: Provision Data Services (30 phút)

### 2.1 GDB (Graph Database)

Console: https://gdb.console.alibabacloud.com/

```
Product:        GDB
Edition:        Standard
Instance Type:  gds.cluster.small (2 vCPU, 4 GB)
Region:         ap-southeast-1 (Singapore)
VPC:            govflow-vpc
VSwitch:        govflow-vsw-a
Security Group: govflow-sg-db
Engine:         Gremlin (TinkerPop 3.x)
Storage:        20 GB (expandable)
```

Sau khi provision (~10 phút):
1. Ghi lại **Internal Endpoint**: `gds-xxx.gdb.rds.aliyuncs.com:8182`
2. Tạo **admin account** trong GDB console
3. Whitelist backend security group

**Tạo 10 agent users (nếu Enterprise ACL available):**

```groovy
// Chạy trong GDB Gremlin Console
:remote connect tinkerpop.server conf/remote.yaml session

// Agent users
mgmt.createUser('agent_planner', 'STRONG_PASSWORD_1')
mgmt.createUser('agent_docanalyzer', 'STRONG_PASSWORD_2')
mgmt.createUser('agent_classifier', 'STRONG_PASSWORD_3')
mgmt.createUser('agent_compliance', 'STRONG_PASSWORD_4')
mgmt.createUser('agent_legallookup', 'STRONG_PASSWORD_5')
mgmt.createUser('agent_router', 'STRONG_PASSWORD_6')
mgmt.createUser('agent_consult', 'STRONG_PASSWORD_7')
mgmt.createUser('agent_summarizer', 'STRONG_PASSWORD_8')
mgmt.createUser('agent_drafter', 'STRONG_PASSWORD_9')
mgmt.createUser('agent_securityofficer', 'STRONG_PASSWORD_10')

// Grant per-agent permissions (from agent-catalog.md)
mgmt.grant('agent_planner', 'READ', 'vertex', 'Case')
mgmt.grant('agent_planner', 'READ', 'vertex', 'Bundle')
mgmt.grant('agent_planner', 'READ', 'vertex', 'TTHCSpec')
mgmt.grant('agent_planner', 'WRITE', 'vertex', 'Task')
// ... repeat for each agent per permission table
```

**Test kết nối:**
```python
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection
from gremlin_python.process.anonymous_traversal import traversal

conn = DriverRemoteConnection(
    'ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin', 'g',
    username='admin', password='YOUR_PASSWORD'
)
g = traversal().withRemote(conn)
print(g.V().count().next())  # Should return 0 (empty)
conn.close()
```

### 2.2 Hologres

Console: https://hologres.console.alibabacloud.com/

```
Instance Name:   govflow-holo
Region:          ap-southeast-1
Compute:         4 CU (4 vCPU equivalent)
Storage:         40 GB
VPC:             govflow-vpc
VSwitch:         govflow-vsw-a
```

Sau khi provision (~5 phút):
1. Ghi lại **endpoint**: `hgcn-xxx.hologres.aliyuncs.com:80`
2. Tạo database `govflow`
3. Tạo user cho backend

**Chạy schema:**
```bash
# Từ máy local (hoặc ECS sau khi provision)
PGPASSWORD=xxx psql -h hgcn-xxx.hologres.aliyuncs.com -p 80 \
  -U admin -d govflow -f infra/hologres-schema.sql
```

**Enable AI Functions (quan trọng cho demo):**
```sql
-- Trong Hologres SQL console
-- Kích hoạt Model Studio integration
-- Docs: https://www.alibabacloud.com/help/en/hologres/user-guide/supported-models-from-alibaba-cloud-model-studio

-- Test AI Function
SELECT ai_generate_text('qwen-max', 'Hello from Hologres!');
```

**Enable Proxima vector extension:**
```sql
-- Tạo Proxima index trên law_chunks (nếu chưa có từ schema)
CALL set_table_property('law_chunks', 'proxima_vectors',
  '{"embedding":{"algorithm":"Graph","metric":"Cosine","builder_params":{"min_flush_proxima_row_count":100}}}');
```

### 2.3 OSS (Object Storage)

Console: https://oss.console.alibabacloud.com/

```
Bucket Name:     govflow-prod
Region:          ap-southeast-1 (Singapore)
Storage Class:   Standard
Redundancy:      Locally Redundant (LRS) — hackathon OK
ACL:             Private
Encryption:      SSE-KMS (enable)
Versioning:      Enable for published/ prefix
```

**Tạo folder structure:**
```bash
# Dùng ossutil hoặc Python
python3 -c "
import oss2
auth = oss2.Auth('ACCESS_KEY', 'SECRET_KEY')
bucket = oss2.Bucket(auth, 'oss-ap-southeast-1.aliyuncs.com', 'govflow-prod')
for prefix in ['bundles/', 'drafts/', 'published/', 'templates/nd30/', 'audit_archives/']:
    bucket.put_object(prefix, b'')
print('OSS folders created')
"
```

**Lifecycle rules:**

| Prefix | Rule | Action |
|--------|------|--------|
| `bundles/` | 365 ngày | Move to Archive, 7 năm delete |
| `drafts/` | 90 ngày | Delete |
| `published/` | Never | WORM lock, 10 năm retention |
| `audit_archives/` | Never | WORM lock, 10 năm retention |

**CORS configuration** (cho frontend direct upload):
```json
{
  "CORSRules": [{
    "AllowedOrigin": ["https://govflow.demo", "http://localhost:3000"],
    "AllowedMethod": ["GET", "PUT", "POST", "HEAD"],
    "AllowedHeader": ["*"],
    "ExposeHeader": ["ETag"],
    "MaxAgeSeconds": 3600
  }]
}
```

**Tạo RAM user cho backend:**
```
RAM User:     govflow-backend
Access Mode:  Programmatic (AccessKey)
Policy:       AliyunOSSFullAccess (scope to govflow-prod bucket)
```

Ghi lại AccessKey ID + Secret.

---

## Phase 3: Model Studio (10 phút)

Console: https://modelstudio.alibabacloud.com/

### 3.1 Activate Models

1. Vào Model Studio console
2. Enable các model:
   - `qwen-max-latest` (reasoning)
   - `qwen-vl-max-latest` (multimodal OCR)
   - `text-embedding-v3` (embeddings)
3. Generate **API Key** tại DashScope console
4. Ghi lại API Key → `DASHSCOPE_API_KEY`

### 3.2 Test

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_DASHSCOPE_API_KEY",
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
)

# Test text model
resp = client.chat.completions.create(
    model="qwen-max-latest",
    messages=[{"role": "user", "content": "Xin chào, bạn là ai?"}]
)
print(resp.choices[0].message.content)

# Test embedding
resp = client.embeddings.create(
    model="text-embedding-v3",
    input="Thủ tục cấp phép xây dựng",
    dimensions=1536
)
print(f"Embedding dimensions: {len(resp.data[0].embedding)}")
```

### 3.3 Rate Limits

| Model | RPM (requests/min) | TPM (tokens/min) |
|-------|--------------------|--------------------|
| qwen-max | 60 | 100,000 |
| qwen-vl-max | 30 | 50,000 |
| text-embedding-v3 | 120 | 1,000,000 |

Cho demo đủ dùng. Nếu cần tăng → contact Alibaba Cloud support.

---

## Phase 4: ECS Compute (20 phút)

Console: https://ecs.console.alibabacloud.com/

### 4.1 Provision ECS Instance

```
Instance Name:    govflow-backend
Instance Type:    ecs.g7.large (2 vCPU, 8 GB RAM)
Region:           ap-southeast-1
Zone:             ap-southeast-1a
Image:            Ubuntu 22.04 64-bit
System Disk:      40 GB SSD
VPC:              govflow-vpc
VSwitch:          govflow-vsw-a
Security Group:   govflow-sg-backend
Public IP:        Assign (for initial SSH setup)
Key Pair:         Create or use existing SSH key
```

### 4.2 Setup ECS Instance

SSH vào instance:
```bash
ssh -i govflow-key.pem root@<ECS_PUBLIC_IP>
```

**Install dependencies:**
```bash
#!/bin/bash
# scripts/setup-ecs.sh

# System
apt update && apt upgrade -y
apt install -y git curl wget unzip nginx certbot python3-certbot-nginx

# Python 3.11+
apt install -y python3.11 python3.11-venv python3-pip

# Node.js 22 LTS
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# Docker (for optional local services)
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu

# PM2 (process manager)
npm install -g pm2

# Caddy (reverse proxy + auto TLS)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install caddy

echo "✅ ECS setup complete"
```

### 4.3 Deploy Backend

```bash
# Clone repo
cd /opt
git clone https://github.com/YOUR_USER/GovTrack.git govflow
cd govflow

# Setup Python env
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .

# Create .env
cat > .env << 'EOF'
GOVFLOW_ENV=cloud
GDB_ENDPOINT=ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin
GDB_USERNAME=admin
GDB_PASSWORD=YOUR_GDB_PASSWORD
HOLOGRES_DSN=postgresql://admin:YOUR_HOLO_PASSWORD@hgcn-xxx.hologres.aliyuncs.com:80/govflow
OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com
OSS_ACCESS_KEY=YOUR_OSS_ACCESS_KEY
OSS_SECRET_KEY=YOUR_OSS_SECRET_KEY
OSS_BUCKET=govflow-prod
DASHSCOPE_API_KEY=YOUR_DASHSCOPE_API_KEY
JWT_SECRET=YOUR_STRONG_JWT_SECRET_32_CHARS
DEMO_MODE=false
EOF

# Test
source .venv/bin/activate
python -c "from src.main import app; print('Backend OK')"

# Run with PM2
pm2 start "cd /opt/govflow/backend && .venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2" --name govflow-api
pm2 save
```

### 4.4 Deploy Frontend

```bash
cd /opt/govflow/frontend

# Create .env.local
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=https://api.govflow.demo
NEXT_PUBLIC_WS_URL=wss://api.govflow.demo/api/ws
EOF

# Build
npm ci
npm run build

# Run with PM2
pm2 start "cd /opt/govflow/frontend && npm start -- -p 3000" --name govflow-web
pm2 save
```

### 4.5 Caddy Reverse Proxy

```bash
cat > /etc/caddy/Caddyfile << 'EOF'
# API backend
api.govflow.demo {
    reverse_proxy localhost:8000

    # WebSocket support
    @websocket {
        header Connection *Upgrade*
        header Upgrade websocket
    }
    reverse_proxy @websocket localhost:8000
}

# Frontend
govflow.demo {
    reverse_proxy localhost:3000
}
EOF

# Reload Caddy (auto TLS with Let's Encrypt)
systemctl reload caddy
```

**Nếu chưa có domain**, dùng IP trực tiếp:
```bash
cat > /etc/caddy/Caddyfile << 'EOF'
:80 {
    handle /api/* {
        reverse_proxy localhost:8000
    }
    handle {
        reverse_proxy localhost:3000
    }
}
EOF
```

---

## Phase 5: SLB Load Balancer (optional, recommend cho demo)

Console: https://slb.console.alibabacloud.com/

```
Type:           ALB (Application Load Balancer)
Region:         ap-southeast-1
VPC:            govflow-vpc
Listener:       HTTPS:443 → Backend:8000 (API) + Backend:3000 (Web)
Certificate:    Upload SSL cert hoặc dùng Alibaba Cloud Certificate Service
Health Check:   GET /api/public/stats → 200 OK
```

Nếu không dùng SLB, Caddy trên ECS đã handle TLS + routing đủ cho hackathon.

---

## Phase 6: DNS + Domain (10 phút)

### Option A: Dùng Alibaba Cloud DNS
1. Mua domain hoặc dùng domain có sẵn
2. Tạo A record: `govflow.demo` → ECS Public IP (hoặc SLB IP)
3. Tạo A record: `api.govflow.demo` → same IP

### Option B: Dùng IP trực tiếp
- Frontend: `http://<ECS_IP>:3000`
- API: `http://<ECS_IP>:8000`
- Cho hackathon đủ dùng, không cần domain

---

## Phase 7: Data Population (30 phút)

Chạy từ ECS (trong VPC, kết nối nhanh hơn):

```bash
cd /opt/govflow
source backend/.venv/bin/activate

# 1. Chạy Hologres schema
PGPASSWORD=$HOLO_PASSWORD psql -h hgcn-xxx.hologres.aliyuncs.com -p 80 \
  -U admin -d govflow -f infra/hologres-schema.sql

# 2. Populate Knowledge Graph
python scripts/ingest_legal.py
python scripts/ingest_tthc.py
python scripts/ingest_org.py        # (nếu có)
python scripts/load_kg_to_gdb.py    # Bulk load vertices + edges to GDB

# 3. Embed law chunks
python scripts/embed_law_chunks.py   # Gọi Qwen3-Embedding, insert vào Hologres

# 4. Seed test users
python scripts/seed_demo.py          # 6 users + 5 demo cases

# 5. Upload templates to OSS
python scripts/upload_templates.py   # ND 30 Jinja templates

# Verify
python -c "
from gremlin_python.driver.client import Client
c = Client('ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin', 'g',
    username='admin', password='$GDB_PASSWORD')
result = c.submit('g.V().count()').all().result()
print(f'GDB vertices: {result}')  # Expected: ~2000
"
```

---

## Phase 8: Monitoring + Logging

### 8.1 SLS (Log Service)

Console: https://sls.console.alibabacloud.com/

1. Tạo Project: `govflow-logs`, region Singapore
2. Tạo Logstore: `api-logs`, `agent-logs`, `audit-logs`
3. Cài SLS agent trên ECS:
```bash
wget http://logtail-release-ap-southeast-1.oss-ap-southeast-1.aliyuncs.com/linux64/logtail-linux64.tar.gz
tar -xzf logtail-linux64.tar.gz
cd logtail-linux64
./logtail_installer.sh install ap-southeast-1
```

4. Cấu hình thu thập log:
   - `/opt/govflow/backend/logs/*.log` → `api-logs`
   - PM2 stdout → `agent-logs`

### 8.2 CloudMonitor

Console: https://cloudmonitor.console.alibabacloud.com/

1. Enable monitoring cho: ECS, GDB, Hologres, OSS
2. Tạo alert rules:
   - ECS CPU > 80% → email
   - GDB connection count > 50 → email
   - Hologres query latency > 5s → email
   - API 5xx error rate > 5% → email

### 8.3 Health Check Endpoint

Backend đã có `/api/public/stats`. Thêm health check chi tiết:

```python
# backend/src/api/health.py
@router.get("/health")
async def health_check(gdb=Depends(get_gdb), holo=Depends(get_hologres)):
    checks = {}
    try:
        await gdb.submit("g.V().count()")
        checks["gdb"] = "ok"
    except Exception as e:
        checks["gdb"] = f"error: {e}"
    try:
        await holo.execute("SELECT 1")
        checks["hologres"] = "ok"
    except Exception as e:
        checks["hologres"] = f"error: {e}"

    checks["dashscope"] = "ok"  # cached check
    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "healthy" if all_ok else "degraded", "checks": checks}
```

---

## Phase 9: CI/CD Pipeline (optional cho hackathon)

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy GovFlow

on:
  push:
    branches: [main]

env:
  ECS_HOST: ${{ secrets.ECS_HOST }}
  ECS_KEY: ${{ secrets.ECS_SSH_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          cd backend
          pip install -e ".[test]"
          pytest tests/unit/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to ECS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ env.ECS_HOST }}
          key: ${{ env.ECS_KEY }}
          username: root
          script: |
            cd /opt/govflow
            git pull origin main
            cd backend && .venv/bin/pip install -e .
            cd ../frontend && npm ci && npm run build
            pm2 restart all
```

### Manual Deploy (cho hackathon, nhanh hơn)

```bash
# Chạy trên local, deploy lên ECS
ssh root@<ECS_IP> "cd /opt/govflow && git pull && cd backend && .venv/bin/pip install -e . && cd ../frontend && npm ci && npm run build && pm2 restart all"
```

---

## Phase 10: Demo Day Hardening

### 10.1 Pre-demo Checklist

```bash
#!/bin/bash
# scripts/pre-demo-check.sh

echo "=== GovFlow Pre-Demo Check ==="

# 1. Backend health
echo -n "API Health: "
curl -s https://api.govflow.demo/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['status'])"

# 2. GDB vertex count
echo -n "GDB Vertices: "
curl -s https://api.govflow.demo/api/public/stats | python3 -c "import sys,json; print(json.load(sys.stdin).get('kg_vertices', 'N/A'))"

# 3. Frontend loads
echo -n "Frontend: "
curl -s -o /dev/null -w "%{http_code}" https://govflow.demo/

# 4. WebSocket
echo -n "WebSocket: "
# Quick WS test via wscat or Python

# 5. DashScope API
echo -n "Qwen API: "
curl -s https://api.govflow.demo/api/agents/test-qwen | python3 -c "import sys,json; print('OK' if json.load(sys.stdin).get('status')=='ok' else 'FAIL')"

# 6. Demo scenario
echo "Running demo scenario 1..."
python3 scripts/demo/scenario_1_cpxd_gap.py

echo "=== Check Complete ==="
```

### 10.2 Demo Mode

```bash
# Bật demo mode (cache Qwen responses)
ssh root@<ECS_IP> "cd /opt/govflow/backend && echo 'DEMO_MODE=true' >> .env && pm2 restart govflow-api"
```

### 10.3 Cache Warming

```bash
# Chạy trước demo 1 giờ
ssh root@<ECS_IP> "cd /opt/govflow && python scripts/warm_cache.py"
```

### 10.4 Backup Plan

Nếu network fail lúc pitch:
1. **Video backup**: có sẵn trên USB + laptop
2. **Local demo**: chạy Docker Compose trên laptop với cached responses
3. **Screenshot deck**: 10 slides key screens

---

## Environment Variables Summary

Tạo file `/opt/govflow/backend/.env` trên ECS:

```bash
# === Core ===
GOVFLOW_ENV=cloud

# === GDB ===
GDB_ENDPOINT=ws://gds-xxx.gdb.rds.aliyuncs.com:8182/gremlin
GDB_USERNAME=admin
GDB_PASSWORD=<strong-password>

# === Hologres ===
HOLOGRES_DSN=postgresql://admin:<password>@hgcn-xxx.hologres.aliyuncs.com:80/govflow

# === OSS ===
OSS_ENDPOINT=https://oss-ap-southeast-1.aliyuncs.com
OSS_ACCESS_KEY=<access-key>
OSS_SECRET_KEY=<secret-key>
OSS_BUCKET=govflow-prod

# === Model Studio ===
DASHSCOPE_API_KEY=<api-key>

# === Auth ===
JWT_SECRET=<32-char-random-string>

# === Demo ===
DEMO_MODE=false
DEMO_CACHE_DIR=/opt/govflow/cache

# === Optional ===
LOG_LEVEL=INFO
CORS_ORIGINS=https://govflow.demo,http://localhost:3000
```

---

## Troubleshooting

### GDB không connect được
```bash
# Check security group: ECS → GDB port 8182
# Check VPC: cùng VPC + VSwitch
# Test: telnet gds-xxx.gdb.rds.aliyuncs.com 8182
```

### Hologres connection refused
```bash
# Hologres port là 80 (không phải 5432)
# Check: whitelist ECS IP trong Hologres console
psql -h hgcn-xxx.hologres.aliyuncs.com -p 80 -U admin -d govflow -c "SELECT 1"
```

### Qwen API rate limit
```bash
# Check remaining quota trong Model Studio console
# Enable DEMO_MODE=true để dùng cached responses
# Hoặc contact Alibaba Cloud support tăng quota
```

### Frontend build fail trên ECS
```bash
# RAM không đủ cho Next.js build
# Workaround: build local, scp .next/ lên ECS
cd frontend && npm run build
scp -r .next/ root@<ECS_IP>:/opt/govflow/frontend/
```

### PM2 process crash
```bash
pm2 logs govflow-api --lines 50   # Check error
pm2 restart govflow-api
pm2 monit                          # Real-time monitoring
```

---

## Deployment Timeline

| Thời gian | Việc | Ước tính |
|-----------|------|----------|
| T+0 | VPC + Security Groups | 15 phút |
| T+15 | GDB provision | 10 phút (+ 10 phút chờ) |
| T+25 | Hologres provision | 5 phút (+ 5 phút chờ) |
| T+30 | OSS bucket + config | 10 phút |
| T+40 | Model Studio activate | 10 phút |
| T+50 | ECS provision + setup | 20 phút |
| T+70 | Deploy backend + frontend | 15 phút |
| T+85 | Data population | 30 phút |
| T+115 | Monitoring setup | 15 phút |
| T+130 | Test E2E trên cloud | 15 phút |
| **Total** | | **~2.5 giờ** |

---

## Verification Checklist

- [ ] VPC + Security Groups tạo xong
- [ ] GDB instance running, gremlinpython connects, g.V().count() returns number
- [ ] Hologres instance running, tables created, SELECT 1 works
- [ ] AI Functions enabled: `SELECT ai_generate_text('qwen-max', 'test')` returns text
- [ ] Proxima vector index created on law_chunks
- [ ] OSS bucket exists với 5 folders, CORS configured
- [ ] Model Studio: 3 models activated, API key works
- [ ] ECS: SSH works, Python 3.11 + Node 22 installed
- [ ] Backend: `curl localhost:8000/health` returns healthy
- [ ] Frontend: `curl localhost:3000` returns HTML
- [ ] Caddy/SLB: HTTPS works from public internet
- [ ] KG populated: ~2000 vertices in GDB
- [ ] Law chunks: 500+ rows in Hologres with embeddings
- [ ] Demo users: 6 users seeded
- [ ] Demo scenario 1 runs E2E without errors
- [ ] Monitoring: SLS collecting logs, CloudMonitor alerts configured

---

## Spec References

- [docs/03-architecture/alibaba-cloud-stack.md](../03-architecture/alibaba-cloud-stack.md) — Product mapping + rationale
- [docs/09-research/alibaba-cloud-product-docs.md](../09-research/alibaba-cloud-product-docs.md) — API endpoints + code examples
- [docs/06-compliance/data-residency.md](../06-compliance/data-residency.md) — Singapore vs on-prem deployment modes
- [docs/08-execution/risk-register.md](../08-execution/risk-register.md) — R1 (GDB delays), R5 (rate limits)
