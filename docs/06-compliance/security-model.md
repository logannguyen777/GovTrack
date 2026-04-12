# Security Model — 4-layer defense

GovFlow's security story is one of 3 main levers in pitch (Đòn bẩy #2). 4-layer defense in depth, graph-native.

## Threat model

### Assets to protect
1. **Citizen PII** — CCCD, phone, address, financial info
2. **Case data** — especially classified cases (Confidential+)
3. **Legal reasoning + decisions** — manipulation could affect outcomes
4. **Audit trail** — must be tamper-proof
5. **KG — law corpus** — if tampered, bad legal citations

### Threat actors
1. **External attackers** — SQL injection, credential stuffing, DDoS
2. **Insider threats** — authorized users exceeding their legitimate access
3. **Compromised agents** — prompt injection, RCE in agent runtime
4. **Privilege escalation** — lower clearance user seeking higher data
5. **Data exfiltration** — bulk download of sensitive data
6. **Audit tampering** — attempting to delete log entries

## Defense layers

```
┌──────────────────────────────────────────────────────┐
│ Layer 0 — Perimeter Security                          │
│                                                        │
│  VPC + Security Groups + WAF + DDoS                   │
│  TLS 1.3 everywhere                                   │
│  Rate limiting per endpoint                           │
│  CORS strict                                          │
└────────────────┬─────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────┐
│ Layer 1 — Application Auth                            │
│                                                        │
│  User: VNeID (citizen) / SSO (civil servant)          │
│  Agent: service accounts with short-lived credentials │
│  JWT with clearance_level + department_ids claims     │
│  Session management + refresh token                   │
└────────────────┬─────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────┐
│ Layer 2 — ABAC on Graph (3 tiers for agents)          │
│                                                        │
│  Tier 1: Agent SDK Guard (parse Gremlin AST)         │
│  Tier 2: GDB Native RBAC (per-agent DB user)         │
│  Tier 3: Property Mask Middleware                     │
│                                                        │
│  For users: same ABAC policy with clearance +         │
│  department + case_assignment                         │
└────────────────┬─────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────┐
│ Layer 3 — Data at Rest                                │
│                                                        │
│  OSS: SSE-KMS, unique key per object                  │
│  GDB: disk encryption                                 │
│  Hologres: column-level encryption for PII            │
│  KMS for key management (rotated)                     │
└────────────────┬─────────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────────┐
│ Layer 4 — Audit & Anomaly Detection                   │
│                                                        │
│  Immutable AuditEvent for every operation             │
│  Forensic replay via subgraph query                   │
│  Anomaly detection: excessive denies, off-hour access │
│  SIEM integration: stream to Alibaba Cloud SLS        │
└──────────────────────────────────────────────────────┘
```

## Layer detail

### Layer 0 — Perimeter

- **Alibaba Cloud VPC** — backend in private subnet, only SLB exposed
- **Security Groups** — strict egress + ingress rules
- **WAF (Web Application Firewall)** — rule-based + managed rules
- **DDoS protection** — Alibaba Cloud Anti-DDoS Basic
- **TLS 1.3 minimum** — HSTS + cert pinning for mobile app
- **Rate limiting** — per endpoint, per user, per IP
- **CORS** — strict allowlist for Citizen Portal domain

### Layer 1 — Authentication

#### Citizens via VNeID (Đề án 06)
- OAuth 2.0 flow with VNeID
- Receive Vietnamese national ID identity
- GovFlow creates `Applicant` vertex with `vneid_subject`
- Refresh every 24h

#### Civil servants
- SSO with Alibaba Cloud IAM
- Multi-factor authentication required
- Short session (8 hours working day)
- Refresh token rotation

#### Agents
- Service account per agent (not shared)
- Short-lived credentials (1 hour) rotated automatically
- Credentials injected via env vars, never in code
- No human access to agent credentials

### Layer 2 — ABAC on Graph

See [`../03-architecture/permission-engine.md`](../03-architecture/permission-engine.md) for deep dive.

**For agents — 3 tiers:**
- Tier 1: SDK Guard (AST parse)
- Tier 2: GDB native RBAC (per-agent DB user)
- Tier 3: Property Mask middleware

**For users — ABAC policy:**
```
Allow user to access resource IF:
  user.clearance_level >= resource.classification
  AND (
    resource.owner_department IN user.departments
    OR user IN resource.assigned_users
    OR user.role IN ['security', 'audit']
  )
  AND resource.status != 'archived_sealed'
```

Policy itself stored as graph edges for flexibility.

### Layer 3 — Data at rest

**OSS encryption:**
- SSE-KMS enabled by default on all buckets
- Unique KMS data key per object
- Key rotation every 90 days

**GDB encryption:**
- Disk encryption enabled
- Backup encryption
- Transport TLS

**Hologres PII:**
- `users.national_id_encrypted` column uses app-level encryption with KMS key
- Decryption only in authorized service at query time

### Layer 4 — Audit & Anomaly

**Immutable audit:**
- `AuditEvent` vertices in GDB — append only
- No DELETE privilege on AuditEvent for any user/agent
- Projection to Hologres `audit_events_flat` for fast query

**Anomaly detection:**
- Nightly job query: users with >10 denied access in past 24h
- Off-hour access alerts (2am–5am)
- Excessive data volume per user (download >100 docs/day)
- Agent attempting out-of-scope writes (should be 0)

**SIEM:**
- All audit events stream to Alibaba Cloud SLS (Log Service)
- Dashboard for security team
- Alert rules via CloudMonitor

## Security principles mapping

| Principle | Implementation |
|---|---|
| Principle of least privilege | Each agent has minimal scope + clearance cap |
| Defense in depth | 3-tier permission engine + 4-layer architecture |
| Separation of duties | SecurityOfficer separate from operational agents |
| Need to know | Property mask + case assignment check |
| Trust but verify | Immutable audit on every action |
| Fail securely | Unknown error → deny + log |
| Assume breach | Forensic replay + anomaly detection |

## Incident response

### Detection
- Real-time anomaly alerts in Security Console
- Nightly batch analysis
- User reports

### Triage
- Security officer reviews via Security Console
- Forensic replay via audit subgraph query
- Determine severity + scope

### Contain
- Disable compromised user via Security Console (1 click)
- Revoke agent credentials if agent compromised
- Rotate keys if key leak suspected

### Eradicate + Recover
- Fix root cause
- Restore from backup if data compromised
- Reset sessions

### Lessons learned
- Update policy rules
- Update anomaly detection
- Team post-mortem

## Compliance mapping

- **Luật BVBMNN 2018** — 4-level classification + access control
- **Luật ANM 2018** — data residency + network security
- **NĐ 53/2022** — audit trail for gov data
- **Luật BVDLCN 2023** — PII protection + purpose limitation
- **NĐ 13/2023** — consent + data minimization
- **ISO 27001** — information security management (PoC target)

## Limitations for hackathon demo

What we'll demo vs what we'd do in production:

| Feature | Hackathon | Production |
|---|---|---|
| VPC + Security Groups | Show in architecture slide | Fully configured |
| WAF + DDoS | Not applicable (single demo) | Enabled |
| MFA for civil servants | Simulated in mockup | Fully integrated with IAM |
| Agent credential rotation | Static for demo | Every 1 hour |
| Immutable audit | Working in GDB | Same |
| Anomaly detection | Simple rule demo | ML-based + full SIEM |
| Forensic replay | Working on 1 case | Same, at scale |
| 3-tier permission | Working full demo | Same |
| Data encryption at rest | Enabled | Same |

**Key demo moments (3 permission scenes):** all working for pitch.

**Claim in pitch:** *"GovFlow's 4-layer security model is production-ready, not demo-hacky. Each layer is designed per best practices: perimeter (VPC+WAF), auth (VNeID+SSO), ABAC-on-graph (3-tier), data-at-rest (KMS), audit (immutable graph). The 3-tier permission engine alone is a pattern that 99% of AI apps don't have."*
