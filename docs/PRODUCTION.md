# GovFlow — Production Deployment Runbook

> Target environment: Alibaba Cloud (ACK + GDB + Hologres + OSS + KMS + Model Studio)
> Estimated time for first deployment: 2–4 hours

---

## Prerequisites

### Accounts and Access

- Alibaba Cloud account with sufficient quota for:
  - ACK (Container Service for Kubernetes) — 3-node cluster minimum
  - GDB (Graph Database) — smallest production tier
  - Hologres — 4-core compute unit minimum
  - OSS bucket with KMS enabled
  - Model Studio (DashScope) API key with Qwen3 access
  - KMS key for OSS SSE-KMS
  - DirectMail or Simple Message Service (optional, for notifications)
- `kubectl` CLI installed and configured
- `docker` CLI installed
- `helm` CLI installed (for cert-manager)
- `aliyun` CLI installed (for ACR image push)
- GitHub repository with Actions enabled

### Required Secrets (GitHub Actions)

Create these as GitHub repository secrets before running CI/CD:

| Secret | Description |
|---|---|
| `ALIBABA_CLOUD_ROLE_ARN` | RAM OIDC role ARN for GitHub Actions: `acs:ram::123456:role/GovFlowDeploy` |
| `ALIBABA_CLOUD_OIDC_PROVIDER_ARN` | OIDC provider ARN |
| `ACR_REGISTRY` | Container Registry endpoint: `registry.ap-southeast-1.aliyuncs.com` |
| `ACR_NAMESPACE` | Registry namespace: e.g. `govflow` |
| `ACK_CLUSTER_ID` | ACK cluster ID from console |
| `KUBECONFIG_BASE64` | Base64-encoded kubeconfig for `kubectl` |

---

## Step 1: Provision Infrastructure

### 1.1 ACK Kubernetes Cluster

1. Open [ACK Console](https://cs.console.aliyun.com/)
2. Create cluster: Standard Managed Kubernetes
   - Region: ap-southeast-1 (Singapore) — closest to Vietnam
   - Node type: ecs.c6.xlarge (4 vCPU, 8 GB) × 3 nodes minimum
   - OS: Alibaba Cloud Linux 3
   - Network: VPC (create new or use existing)
3. Enable ACK monitoring (Prometheus + Grafana built-in option)
4. Download kubeconfig after creation

Reference: https://www.alibabacloud.com/help/en/ack/ack-managed-and-dedicated/user-guide/create-an-ack-managed-cluster

### 1.2 GDB (Graph Database)

1. Open [GDB Console](https://gdb.console.aliyun.com/)
2. Create instance: GDB Enterprise Edition
   - Same VPC as ACK cluster
   - Storage: 100 GB (expandable)
   - TinkerPop version: 3.7.x
3. Create a database user for GovFlow with read/write privileges
4. Note the WebSocket endpoint: `wss://your-instance.gdb.aliyuncs.com:8182/gremlin`

Reference: https://www.alibabacloud.com/help/en/graph-database/getting-started/

### 1.3 Hologres

1. Open [Hologres Console](https://hologram.console.aliyun.com/)
2. Create instance:
   - Same region as ACK
   - Compute: 4 CU minimum
   - Enable Proxima vector extension
3. Create database `govflow`
4. Note DSN: `postgresql://user:pass@instance.hologres.aliyuncs.com:80/govflow`

Reference: https://www.alibabacloud.com/help/en/hologres/getting-started/

### 1.4 OSS Bucket

1. Open [OSS Console](https://oss.console.aliyun.com/)
2. Create bucket:
   - Name: `govflow-prod`
   - Region: ap-southeast-1
   - ACL: Private
   - Enable versioning
3. Enable Server-Side Encryption (SSE-KMS):
   - Go to bucket settings → Encryption
   - Select KMS → Create new key or use existing

Reference: https://www.alibabacloud.com/help/en/oss/user-guide/server-side-encryption

### 1.5 KMS Key

1. Open [KMS Console](https://kms.console.aliyun.com/)
2. Create key:
   - Type: Symmetric
   - Algorithm: AES_256
   - Alias: `govflow-oss-key`
3. Note the Key ARN: `acs:kms:ap-southeast-1:your-account:key/xxx`

Reference: https://www.alibabacloud.com/help/en/kms/user-guide/

### 1.6 Model Studio API Key

1. Open [Bailian Console](https://bailian.console.aliyun.com/)
2. Create API key for GovFlow application
3. Verify Qwen3-Max, Qwen3-VL-Max, and text-embedding-v3 are accessible
4. Set token quota per project if needed

Reference: https://www.alibabacloud.com/help/en/model-studio/getting-started/

### 1.7 RAM STS Role (for OSS short-lived credentials)

1. Open [RAM Console](https://ram.console.aliyun.com/)
2. Create Role: `govflow-oss-role`
   - Trust: ECS service
   - Policy: attach `AliyunOSSFullAccess` (or custom minimal policy)
3. Note Role ARN: `acs:ram::your-account-id:role/govflow-oss-role`

---

## Step 2: Configure Kubernetes Secrets

```bash
# 2.1 Create namespace
kubectl apply -f infra/k8s/namespace.yaml

# 2.2 Create secret from environment variables
kubectl -n govflow create secret generic govflow-secrets \
  --from-literal=DASHSCOPE_API_KEY="sk-your-key-here" \
  --from-literal=JWT_SECRET="$(openssl rand -hex 32)" \
  --from-literal=GDB_ENDPOINT="wss://your-gdb.gdb.aliyuncs.com:8182/gremlin" \
  --from-literal=GDB_USERNAME="govflow" \
  --from-literal=GDB_PASSWORD="your-gdb-password" \
  --from-literal=HOLOGRES_DSN="postgresql://govflow:pass@hologres.aliyuncs.com:80/govflow" \
  --from-literal=OSS_ENDPOINT="https://oss-ap-southeast-1.aliyuncs.com" \
  --from-literal=OSS_ACCESS_KEY_ID="your-access-key" \
  --from-literal=OSS_ACCESS_KEY_SECRET="your-access-secret" \
  --from-literal=OSS_BUCKET="govflow-prod" \
  --from-literal=OSS_REGION="ap-southeast-1" \
  --from-literal=OSS_KMS_KEY_ID="alias/govflow-oss-key" \
  --from-literal=OSS_STS_ROLE_ARN="acs:ram::your-account:role/govflow-oss-role" \
  --from-literal=GOVFLOW_ENV="cloud" \
  --from-literal=REDIS_URL="redis://govflow-redis:6379/0" \
  --from-literal=SENTRY_DSN="https://your-sentry-dsn" \
  --from-literal=OTEL_EXPORTER_OTLP_ENDPOINT="http://otel-collector:4317"

# 2.3 Verify secrets are set
kubectl -n govflow get secret govflow-secrets -o jsonpath='{.data}' | jq 'keys'
```

---

## Step 3: Build and Push Docker Images (GitHub Actions)

The CI/CD pipeline is in `.github/workflows/deploy-prod.yml`.

### Trigger a production deployment

1. Go to GitHub Actions → "Deploy to Production (ACK)"
2. Click "Run workflow"
3. Enter parameters:
   - `image_tag`: Git SHA or version tag (e.g. `sha-abc1234` or `v1.0.0`)
   - `component`: `both` (deploy backend and frontend)
   - `dry_run`: `false`
4. Monitor the workflow run

### Manual build (if needed)

```bash
# Backend
docker build -t registry.ap-southeast-1.aliyuncs.com/govflow/backend:latest \
  -f backend/Dockerfile backend/

# Frontend
docker build -t registry.ap-southeast-1.aliyuncs.com/govflow/frontend:latest \
  -f frontend/Dockerfile frontend/

# Push (requires aliyun login)
aliyun cr login --type=optional registry.ap-southeast-1.aliyuncs.com
docker push registry.ap-southeast-1.aliyuncs.com/govflow/backend:latest
docker push registry.ap-southeast-1.aliyuncs.com/govflow/frontend:latest
```

---

## Step 4: Deploy to Kubernetes

```bash
# 4.1 Apply all manifests
kubectl apply -f infra/k8s/

# 4.2 Verify deployments are running
kubectl -n govflow get pods -w

# 4.3 Check deployment status
kubectl -n govflow rollout status deployment/govflow-backend
kubectl -n govflow rollout status deployment/govflow-frontend

# 4.4 Check services + ingress
kubectl -n govflow get svc
kubectl -n govflow get ingress
```

### K8s Manifests Overview

| File | Description |
|---|---|
| `namespace.yaml` | Create `govflow` namespace |
| `configmap.yaml` | Non-secret config (ports, timeouts) |
| `secret.yaml` | Template — actual secrets via `kubectl create secret` |
| `deployment-backend.yaml` | FastAPI backend (2 replicas + HPA) |
| `deployment-frontend.yaml` | Next.js frontend (2 replicas) |
| `service.yaml` | ClusterIP services for backend + frontend |
| `ingress.yaml` | ALB Ingress (routes `/api` → backend, `/` → frontend) |
| `hpa.yaml` | HorizontalPodAutoscaler (scale 2–10 based on CPU) |
| `pdb.yaml` | PodDisruptionBudget (min 1 pod available during drain) |

---

## Step 5: Smoke Test

```bash
# 5.1 Get load balancer IP from ingress
LB_IP=$(kubectl -n govflow get ingress govflow-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Load Balancer IP: $LB_IP"

# 5.2 Health check
curl -f http://$LB_IP/healthz
# Expected: {"status": "ok", "version": "x.y.z"}

# 5.3 Backend API docs
curl -s http://$LB_IP/docs | grep "GovFlow"

# 5.4 Run Scenario 1 (requires demo data seeded)
GOVFLOW_API=http://$LB_IP python scripts/demo/scenario_1_cpxd_gap.py

# 5.5 Full smoke test script
GOVFLOW_API=http://$LB_IP ./scripts/smoke_test.sh
```

---

## Step 6: DNS and TLS Certificate

### 6.1 Configure DNS

1. Note your ALB load balancer IP from Step 5
2. In your DNS provider, create:
   ```
   A   govflow.yourdomain.com       → <ALB_IP>
   A   api.govflow.yourdomain.com   → <ALB_IP>
   ```
3. Update `infra/k8s/ingress.yaml` with your domain names

### 6.2 Install cert-manager

```bash
# Install cert-manager via Helm
helm repo add jetstack https://charts.jetstack.io
helm repo update
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --create-namespace \
  --set installCRDs=true

# Create ClusterIssuer for Let's Encrypt
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@domain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: alb
EOF
```

### 6.3 Update Ingress for TLS

Update `infra/k8s/ingress.yaml` to add TLS annotations:
```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - govflow.yourdomain.com
    - api.govflow.yourdomain.com
    secretName: govflow-tls
```

---

## Step 7: Configure Grafana Datasource and Dashboard

### 7.1 Access Grafana

If using ACK built-in monitoring:
```bash
kubectl -n monitoring port-forward svc/grafana 3000:3000
```
Then open http://localhost:3000 (default: admin/prom-operator).

### 7.2 Add Prometheus Datasource

1. Grafana → Configuration → Data Sources → Add
2. Type: Prometheus
3. URL: `http://prometheus-server.monitoring.svc.cluster.local`
4. Save + Test

### 7.3 Import GovFlow Dashboard

1. Grafana → Dashboards → Import
2. Upload `infra/grafana/govflow-dashboard.json` (if exists)
   or create panels manually for these metrics:
   - `govflow_cases_total` — total cases by status
   - `govflow_agent_duration_seconds` — p50/p95 per agent
   - `govflow_permission_denials_total` — by tier + agent
   - `http_request_duration_seconds` — API latency
   - `govflow_active_websockets` — realtime connections

---

## Step 8: Configure Sentry

1. Create a project at https://sentry.io
   - Platform: Python / FastAPI for backend
   - Platform: Next.js for frontend
2. Copy the DSN for each project
3. Update Kubernetes secret:
   ```bash
   kubectl -n govflow patch secret govflow-secrets \
     -p '{"data":{"SENTRY_DSN":"'$(echo -n "https://your-dsn" | base64)'"}}'
   ```
4. Restart deployments to pick up new secret:
   ```bash
   kubectl -n govflow rollout restart deployment/govflow-backend
   kubectl -n govflow rollout restart deployment/govflow-frontend
   ```
5. Verify: trigger a test error and check Sentry dashboard

---

## Step 9: Run Alembic Migrations

Alembic migrations run automatically during backend startup (via FastAPI lifespan hook). Verify:

```bash
# Check migration logs
kubectl -n govflow logs deployment/govflow-backend | grep -i "alembic\|migration"

# Manual migration (if needed)
kubectl -n govflow exec -it deployment/govflow-backend -- alembic upgrade head

# Check current migration version
kubectl -n govflow exec -it deployment/govflow-backend -- alembic current
```

---

## Step 10: Seed Initial Production Data

```bash
# 10.1 Port-forward to backend
kubectl -n govflow port-forward svc/govflow-backend 8100:8100 &

# 10.2 Seed organizations + departments
python scripts/seed_organizations.py

# 10.3 Seed initial users (change passwords immediately after)
python scripts/seed_users.py

# 10.4 Load TTHC knowledge graph
python scripts/load_kg_tthc.py

# 10.5 Load legal knowledge graph
python scripts/load_kg_legal.py

# 10.6 Generate embeddings for law chunks (requires DashScope)
python scripts/embed_chunks.py

# 10.7 Seed demo data (optional, for judge demo environment)
python scripts/seed_demo.py

# 10.8 Warm LLM cache for demo scenarios
python scripts/warm_cache.py
```

---

## Rollback Procedure

### Quick rollback (previous image tag)

```bash
# List recent deployments
kubectl -n govflow rollout history deployment/govflow-backend
kubectl -n govflow rollout history deployment/govflow-frontend

# Rollback to previous version
kubectl -n govflow rollout undo deployment/govflow-backend
kubectl -n govflow rollout undo deployment/govflow-frontend

# Rollback to specific revision
kubectl -n govflow rollout undo deployment/govflow-backend --to-revision=3
```

### Emergency rollback (specific image)

```bash
# Update image directly
kubectl -n govflow set image deployment/govflow-backend \
  backend=registry.ap-southeast-1.aliyuncs.com/govflow/backend:LAST_KNOWN_GOOD_TAG

# Verify
kubectl -n govflow rollout status deployment/govflow-backend
```

### Database rollback (Alembic)

```bash
# Rollback one migration
kubectl -n govflow exec -it deployment/govflow-backend -- alembic downgrade -1

# Rollback to specific revision
kubectl -n govflow exec -it deployment/govflow-backend -- alembic downgrade abc123
```

---

## Monitoring and Alerting

See [docs/07-operations/](07-operations/) for full DR documentation.

### Key Health Endpoints

| Endpoint | Description |
|---|---|
| `GET /healthz` | Overall health (DB + GDB + OSS connectivity) |
| `GET /metrics` | Prometheus metrics (IP-restricted) |
| `GET /api/agents/status` | Agent runtime status |

### Recommended Alerts (Prometheus/Grafana)

| Alert | Condition | Severity |
|---|---|---|
| HighErrorRate | `http_request_error_rate > 5%` for 5m | critical |
| SlowAgentPipeline | `govflow_pipeline_duration_p95 > 90s` | warning |
| PermissionDenialSpike | `govflow_permission_denials_total rate > 10/min` | warning |
| PodCrashLooping | Pod restarts > 3 in 10m | critical |
| GDBConnectionFailed | `/healthz` GDB check failing | critical |
| LowDiskOSS | OSS bucket > 80% quota | warning |

---

## Compliance Checklist

Before going live, verify:

### NĐ 13/2023/NĐ-CP (Data Subject Rights)

- [ ] DSR endpoints deployed: `GET /api/dsr/export`, `DELETE /api/dsr/erasure`
- [ ] Consent management: `POST /api/consent`, `DELETE /api/consent`
- [ ] Purpose limitation: per-agent data access documented in `AgentProfile.purpose`
- [ ] Data minimization: `PropertyMask` active for all agents
- [ ] Data residency: all storage in ap-southeast-1 or on-prem

### NĐ 30/2020/NĐ-CP (Document Standards)

- [ ] Drafter output contains all 9 required components (Điều 8)
- [ ] Font: Times New Roman 13 for all output documents
- [ ] Chữ ký số placeholder in all draft documents
- [ ] Retention policy cron active (Điều 28)
- [ ] NĐ 30/2020 format validation in `validate_nd30_format()` Drafter tool

### Luật BVBMNN 2018 (Classification)

- [ ] 4-level classification enforced: ClearanceLevel enum (0–3)
- [ ] SecurityOfficer agent active and running in pipeline
- [ ] AuditEvent created for every classified document access
- [ ] No downgrade of classification without SecurityOfficer approval

### Luật ANM 2018 + NĐ 53/2022 (Data Residency)

- [ ] All user PII stored in Vietnam or ap-southeast-1 (nearest feasible)
- [ ] On-prem Qwen3 deployment path documented (PAI-EAS)
- [ ] Data export controls active

### General Security

- [ ] Argon2id password hashing confirmed (not bcrypt, not SHA-256)
- [ ] JWT revocation list active and checked on every request
- [ ] SSRF guard active (`oss_allowed_domains` configured)
- [ ] CSP + HSTS headers verified in production responses
- [ ] Rate limiting active (Redis-backed)
- [ ] Gremlin injection guard: SDK Guard parsing all queries

---

## On-Call Escalation

| Issue | First responder | Escalate to |
|---|---|---|
| Backend pod crash | DevOps on-call | Backend lead |
| GDB connection failure | DevOps on-call | Alibaba Cloud TAM |
| DashScope API quota exceeded | Backend lead | Project manager |
| Security incident (classification breach) | Security officer | CISO + management |
| Data subject request (NĐ 13/2023) | Legal team | DPO |
| Production data loss | DevOps lead | Alibaba Cloud support ticket P1 |

For DR procedures (backup restore, multi-region failover), see [docs/07-operations/disaster-recovery.md](07-operations/disaster-recovery.md).
