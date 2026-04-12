You are implementing GovFlow's 3-tier permission engine. Follow docs/implementation/15-permission-engine.md as the detailed guide.

Task: $ARGUMENTS (default: full permission engine)

## What You Build

3-tier ABAC-on-Graph defense in depth: SDK Guard (pre-DB), GDB RBAC (DB-level), Property Mask (post-query). Plus audit logging and 3-scene demo endpoints.

## Steps

### Tier 1 — SDK Guard (`backend/src/graph/sdk_guard.py`)

```python
class SDKGuard:
    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def check_read(self, traversal_bytecode) -> None:
        """Parse Gremlin bytecode, extract accessed labels.
        Raise SDKGuardViolation if label not in profile.read_node_labels."""

    def check_write(self, traversal_bytecode) -> None:
        """Parse bytecode for addV/addE operations.
        Raise SDKGuardViolation if label not in profile.write_node_labels."""

    def auto_rewrite(self, traversal) -> Traversal:
        """Inject .has('classification', P.lte(clearance_cap)) filter."""

class SDKGuardViolation(PermissionError):
    def __init__(self, agent, action, label, tier="SDK_Guard"): ...
```

### Tier 2 — GDB Native RBAC (`infra/gdb-rbac.groovy`)
- Create 10 GDB users with per-label GRANT statements
- Reference permission table in docs/03-architecture/agent-catalog.md
- Fallback for free-tier GDB: enforce at SDK layer, log as RBAC rejection

### Tier 3 — Property Mask (`backend/src/graph/property_mask.py`)

```python
class PropertyMask:
    def apply(self, results, agent_or_user_clearance) -> list:
        """Post-query redaction per clearance level.
        Rules: redact (remove), mask_partial (last 4 chars), classification_gated."""
```

### PermittedGremlinClient (`backend/src/graph/permitted_client.py`)
- Wraps raw GDB client
- Flow: SDK Guard check_read -> check_write -> auto_rewrite -> execute -> Property Mask apply
- Each agent gets its own instance with its profile

### Audit Logging (`backend/src/graph/audit.py`)
- Every permission check (allow/deny) writes AuditEvent vertex to GDB
- Also projects to Hologres audit_events_flat table
- Fields: actor, action, resource_type, resource_id, result, reason, tier, timestamp

### 3-Scene Demo Endpoints
- Scene A: POST /api/demo/scene-a — Summarizer tries Applicant.national_id -> SDK Guard rejects
- Scene B: POST /api/demo/scene-b — LegalLookup tries CREATE Gap -> RBAC rejects
- Scene C: POST /api/demo/scene-c?level=Secret — User elevation -> Property Mask re-evaluates -> fields revealed

## 20+ Negative Test Scenarios
1. Summarizer reads Applicant.national_id -> SDK Guard DENY
2. LegalLookup writes Gap -> SDK Guard DENY (write scope)
3. Classifier reads Document.content_full -> SDK Guard DENY
4. Planner reads Classification vertex -> SDK Guard DENY
5. Unclassified user views Secret field -> Property Mask REDACT
6. Confidential user views Top Secret field -> Property Mask REDACT
7. SecurityOfficer reads everything -> ALLOW
8. DocAnalyzer reads raw blob -> ALLOW (Top Secret cap)
9. Drafter tries publish -> DENY (no PUBLISH action allowed)
10-20. More scenarios per docs/03-architecture/permission-engine.md

## Spec References
- docs/03-architecture/permission-engine.md — Full 3-tier design with code sketches
- docs/03-architecture/agent-catalog.md — Permission table per agent

## Verification
```python
# All 20+ negative scenarios reject correctly
# Every denial writes AuditEvent with correct tier
# Scene A/B/C endpoints produce expected behavior
# SecurityOfficer can read everything
# Property Mask elevation: same query, different clearance -> different fields visible
```
