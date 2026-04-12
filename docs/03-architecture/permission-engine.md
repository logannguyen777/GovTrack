# Permission Engine — 3-tier ABAC-on-Graph

Đây là phần quan trọng nhất về security của GovFlow. Đòn bẩy #2 trong pitch. Demo hero.

## Design goal

Enforce fine-grained permission **tại mức node/edge/property** cho cả **user** và **agent**. Không chỉ RBAC theo role — mà ABAC theo attribute (clearance, department, case assignment, purpose).

Và quan trọng: **defense in depth — 3 tầng**. Nếu 1 tầng có hole, 2 tầng còn lại catch.

## Why 3 tiers?

| Tier | Catches | Performance cost |
|---|---|---|
| 1. Agent SDK Guard | Early rejection before any DB call. Catches: out-of-scope queries from misbehaving agent | Low (regex + AST parse) |
| 2. GDB Native RBAC | DB-level privilege enforcement. Catches: SDK Guard bypass, direct query injection | Zero (DB engine native) |
| 3. Property Mask Middleware | Post-query redaction. Catches: authorized query returning unauthorized properties (e.g., compliance agent accidentally sees PII field) | Low (middleware pass) |

All 3 together = defense in depth.

---

## Tier 1 — Agent SDK Guard

### Purpose
Parse the Gremlin traversal trước khi gửi về GDB. Reject nếu agent cố đọc/ghi label hoặc edge type ngoài scope đã cấp.

### Implementation

```python
# agents/permission/sdk_guard.py

from gremlin_python.process.traversal import Traversal
from typing import List

class AgentProfile:
    def __init__(
        self,
        name: str,
        role: str,
        read_node_labels: List[str],
        read_edge_types: List[str],
        write_node_labels: List[str],
        write_edge_types: List[str],
        property_masks: dict,
        clearance_cap: str
    ):
        self.name = name
        self.role = role
        self.read_node_labels = set(read_node_labels)
        self.read_edge_types = set(read_edge_types)
        self.write_node_labels = set(write_node_labels)
        self.write_edge_types = set(write_edge_types)
        self.property_masks = property_masks
        self.clearance_cap = clearance_cap

class SDKGuardViolation(Exception):
    pass

class SDKGuard:
    """Parse Gremlin traversal bytecode and enforce agent profile scope."""

    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def check_read(self, bytecode) -> None:
        """Check that this traversal only reads authorized labels/edges."""
        accessed_labels = self._extract_labels(bytecode)
        unauthorized = accessed_labels - self.profile.read_node_labels
        if unauthorized:
            raise SDKGuardViolation(
                f"Agent '{self.profile.name}' cannot read labels: {unauthorized}. "
                f"Authorized: {self.profile.read_node_labels}"
            )
        # Similar for edge types...

    def check_write(self, bytecode) -> None:
        """Check write operations against write scope."""
        created_labels = self._extract_create_labels(bytecode)
        unauthorized = created_labels - self.profile.write_node_labels
        if unauthorized:
            raise SDKGuardViolation(
                f"Agent '{self.profile.name}' cannot write labels: {unauthorized}"
            )

    def auto_rewrite(self, bytecode):
        """If authorized but missing classification filter, inject filter."""
        # e.g., add .has('classification', P.lte(self.profile.clearance_cap))
        return rewritten_bytecode
```

### Example violation

Agent `Summarizer` cố execute:
```groovy
g.V().has('Case', 'id', 'C-001')
 .out('SUBMITTED_BY')
 .values('national_id')  // ← PII access
```

SDKGuard parses the bytecode, sees `Applicant.national_id` is in `property_masks` for Summarizer → throws `SDKGuardViolation`. Query never hits GDB.

### Integration
```python
class PermittedGremlinClient:
    def __init__(self, gdb_client, agent_profile):
        self.gdb = gdb_client
        self.guard = SDKGuard(agent_profile)

    async def execute(self, traversal):
        self.guard.check_read(traversal.bytecode)
        self.guard.check_write(traversal.bytecode)
        rewritten = self.guard.auto_rewrite(traversal.bytecode)
        return await self.gdb.submit(rewritten)
```

Mỗi agent có 1 instance `PermittedGremlinClient` — không có cách nào bypass trong normal flow.

---

## Tier 2 — GDB Native RBAC

### Purpose
Alibaba Cloud GDB native database-level access control. Mỗi agent là 1 GDB user với privilege riêng. Ngay cả khi SDK Guard bị bypass (prompt injection, bug), GDB reject.

### Setup

```groovy
// Create agent users with distinct credentials
gdb> CREATE USER agent_planner PASSWORD '...'
gdb> CREATE USER agent_docanalyzer PASSWORD '...'
gdb> CREATE USER agent_classifier PASSWORD '...'
gdb> CREATE USER agent_compliance PASSWORD '...'
gdb> CREATE USER agent_legallookup PASSWORD '...'
gdb> CREATE USER agent_router PASSWORD '...'
gdb> CREATE USER agent_consult PASSWORD '...'
gdb> CREATE USER agent_summarizer PASSWORD '...'
gdb> CREATE USER agent_drafter PASSWORD '...'
gdb> CREATE USER agent_securityofficer PASSWORD '...'

// Grant privileges per label/edge type
gdb> GRANT TRAVERSE ON LABEL Case TO agent_planner
gdb> GRANT READ ON LABEL Case TO agent_planner
gdb> GRANT WRITE ON LABEL Task TO agent_planner
// ... more grants

gdb> GRANT TRAVERSE, READ ON LABEL * TO agent_securityofficer
gdb> GRANT WRITE ON LABEL AuditEvent TO agent_securityofficer
gdb> GRANT WRITE ON LABEL Classification TO agent_securityofficer
```

### Note on Gremlin
Alibaba Cloud GDB (compatible with Apache TinkerPop 3.x) supports user + role-based privilege. Fine-grained ACL per label/edge is an enterprise feature. For hackathon demo, we will simulate at SDK layer if GDB doesn't have full granularity; production path uses GDB enterprise features.

### Fallback
If GDB free tier lacks label-level ACL, we enforce equivalent at SDK Guard layer + audit log all attempts. Demo still shows 3 tiers logically.

---

## Tier 3 — Property Mask Middleware

### Purpose
Even after SDK Guard allows + GDB returns data, middleware redacts sensitive properties based on agent profile and user clearance.

### Why needed?
- Agent có quyền read `Applicant` vertex nhưng không được đọc `national_id` field
- User có clearance Confidential xem `Case` nhưng không được đọc field về vị trí nhạy cảm (classified Secret)
- Different agents need different redaction

### Implementation

```python
# agents/permission/property_mask.py

class PropertyMask:
    """Redact sensitive properties after query return."""

    def __init__(self, agent_profile, user_context=None):
        self.profile = agent_profile
        self.user_context = user_context  # for user-initiated queries

    def apply(self, results):
        """Traverse results, apply masks per label."""
        for vertex in results:
            label = vertex.get('_label')
            mask_rules = self.profile.property_masks.get(label, {})

            for prop, rule in mask_rules.items():
                if rule == 'redact':
                    vertex[prop] = '[REDACTED]'
                elif rule == 'mask_partial':
                    # e.g., national_id: 079***1234
                    vertex[prop] = self._partial_mask(vertex[prop])
                elif rule.startswith('classification_gated'):
                    required = rule.split(':')[1]
                    if not self._has_clearance(required):
                        vertex[prop] = '[CLASSIFIED]'
        return results

    def _has_clearance(self, required_level):
        clearance_order = {'Unclassified': 0, 'Confidential': 1, 'Secret': 2, 'Top Secret': 3}
        if self.user_context:
            return clearance_order[self.user_context.clearance] >= clearance_order[required_level]
        return clearance_order[self.profile.clearance_cap] >= clearance_order[required_level]
```

### Mask rules example (Compliance agent profile)

```yaml
agent: Compliance
property_masks:
  Applicant:
    national_id: redact
    phone: mask_partial
    address_detail: redact
    display_name: show  # allowed
  Document:
    blob_url: redact  # compliance doesn't need raw doc
    content_full: redact  # only sees extracted fields
  Case:
    location_detail: classification_gated:Confidential
    notes_internal: classification_gated:Secret
```

### Demo moment — Scene C property mask elevation

```
User clearance=Unclassified opens Case viewer:
  national_id: [REDACTED]
  address_detail: [REDACTED]
  location_notes: [CLASSIFIED]
  notes: [CLASSIFIED]

[User elevates to Confidential via Security Console]

Same view:
  national_id: 079***1234          ← partial unmask
  address_detail: 123 Đường X, Phường Y
  location_notes: "Vùng giáp KCN Mỹ Phước"
  notes: [CLASSIFIED]               ← still Secret only

[User elevates to Secret]

  notes: "Gần khu đất quốc phòng, cần SecurityOfficer review"
```

Animation: properties gradually "dissolve" from blurred → clear as clearance increases.

---

## Policy as Data (Graph)

The permission rules themselves are stored as **Graph vertices + edges** — not as hard-coded config.

### Schema

```
(Agent{name:'Compliance', clearance_cap:'Confidential'})
  -[:CAN_READ {mask:'redact'}]-> (Label{name:'Applicant', property:'national_id'})
  -[:CAN_READ]-> (Label{name:'Case'})
  -[:CAN_WRITE]-> (Label{name:'Gap'})
  -[:CAN_WRITE]-> (EdgeType{name:'HAS_GAP'})
```

### Benefits
- **Audit friendly:** "ai có quyền gì lúc nào?" = graph query
- **Mutable:** thêm permission = thêm edge, không redeploy
- **Versionable:** policy changes as timestamped edges
- **Queryable:** "agent nào có quyền write Classification?" = graph traversal

### Policy evaluation query

```groovy
// Does Compliance have read access to Applicant.national_id?
g.V().has('Agent', 'name', 'Compliance')
 .out('CAN_READ')
 .has('Label', 'name', 'Applicant')
 .has('property', 'national_id')
 .hasNext()  // → false (not present), therefore redact
```

---

## Audit of permission checks

Every permission decision (allow/deny) writes an `AuditEvent` vertex:

```
AuditEvent {
  actor: "agent:Compliance",
  action: "read",
  resource_type: "Applicant.national_id",
  result: "deny",
  reason: "Property 'national_id' not in CAN_READ edges for agent Compliance",
  tier: "SDK_Guard",  // which tier caught it
  timestamp: ...
}
```

AuditEvents are immutable and append-only. Forensic query can replay any time window.

---

## 3-Scene Demo Implementation

### Scene A — SDK Guard reject (Agent out-of-scope)

**Setup:** Chuyên viên phòng QLXD (user) asks system "tóm tắt hồ sơ này, bao gồm CCCD người nộp". Summarizer agent receives query.

**What happens:**
1. Summarizer constructs Gremlin: `.out('SUBMITTED_BY').values('national_id')`
2. SDK Guard intercepts → parses bytecode → detects `Applicant.national_id` in mask list with rule=redact → **rejects before GDB call**
3. Returns error: `SDKGuardViolation`
4. AuditEvent written with `tier="SDK_Guard"`
5. UI shows red shake animation + audit log panel slides in with full reasoning

**Demo UI:**
```
Agent: Summarizer
Attempted query: [expand to see Gremlin bytecode]
❌ DENIED at Tier 1: SDK Guard
Reason: Property 'Applicant.national_id' is in mask list for agent 'Summarizer'
Audit ID: #12345 (click to view audit trail)
```

### Scene B — GDB Native RBAC (Cross-agent violation)

**Setup:** LegalLookup agent has been prompt-injected (simulated) to try writing a `Gap` vertex — but its write scope only includes `Citation`.

**What happens:**
1. LegalLookup constructs: `g.addV('Gap').property('reason', '...')`
2. SDK Guard catches (write scope check)
3. But in demo, **disable SDK Guard temporarily** to show Tier 2 kicks in
4. GDB native RBAC: `agent_legallookup` user has no WRITE privilege on label `Gap`
5. GDB rejects: `AccessDeniedException`
6. AuditEvent written with `tier="GDB_RBAC"`

**Demo UI:**
```
Agent: LegalLookup (simulating prompt injection scenario)
Attempted operation: CREATE Vertex{label:Gap}
⚠️ Tier 1 SDK Guard disabled (demo)
❌ DENIED at Tier 2: GDB Native RBAC
Reason: User 'agent_legallookup' lacks WRITE privilege on label 'Gap'
Audit ID: #12346
```

### Scene C — Property Mask live elevation

**Setup:** User chuyên viên opens Document Viewer for a Case with sensitive location info.

**What happens:**
1. User's JWT: `clearance=Unclassified`
2. Query returns vertex data through middleware
3. Property Mask inspects every field, masks:
   - `national_id` → `[REDACTED]`
   - `address_detail` → `[REDACTED]`
   - `location_notes` → `[CLASSIFIED]`
4. UI renders with blurred/redacted fields

5. **Elevation moment:** SecurityOfficer grants temporary elevation to Confidential
6. WebSocket pushes new JWT claims to frontend
7. Query re-runs with new clearance
8. Property Mask now partial-masks (phone shows last 4 digits, address shows street)
9. UI animates: blurred text → crisp text with 400ms dissolve

10. Further elevation to Secret → `location_notes` reveals

**Demo UI:**
```
Document viewer showing bundle fields

Before (Unclassified):
┌────────────────────────┐
│ Applicant: N*** Văn A │
│ Phone: [REDACTED]      │
│ Address: [REDACTED]    │
│ Location: [CLASSIFIED] │
└────────────────────────┘

[Elevate clearance button → Confidential]
(animation: mask dissolves)

After (Confidential):
┌──────────────────────────────────────┐
│ Applicant: N*** Văn A                │
│ Phone: 090****1234                   │
│ Address: 123 Đường X, Phường Y, ...  │
│ Location: [CLASSIFIED]               │
└──────────────────────────────────────┘

[Elevate to Secret]

After (Secret):
┌──────────────────────────────────────────────────┐
│ Applicant: N*** Văn A                            │
│ Phone: 0901234567                                │
│ Address: 123 Đường X, Phường Y, ...              │
│ Location: Gần KCN Mỹ Phước, cách biên giới 3km  │
└──────────────────────────────────────────────────┘
```

## Implementation priorities

Day 13/04 morning — build permission engine:

1. **Day 13 sáng 1:** Agent profile loader (YAML → AgentProfile object)
2. **Day 13 sáng 2:** SDK Guard (Gremlin bytecode parse + label check + basic property mask)
3. **Day 13 sáng 3:** Property mask middleware (label + property level)
4. **Day 13 sáng 4:** Policy-as-graph storage (optional, can hardcode profiles for demo)
5. **Day 13 chiều:** Integration test — run 20+ negative permission scenarios
6. **Day 15:** UI for 3-scene demo (animation + audit log viewer)

## Testing checklist

- [ ] Summarizer cannot read Applicant.national_id (SDK Guard)
- [ ] LegalLookup cannot write Gap (write scope)
- [ ] Classifier cannot read Document.content_full (read scope)
- [ ] User clearance=Unclassified cannot see Classification=Secret fields (property mask)
- [ ] SecurityOfficer can read everything
- [ ] Every denial writes AuditEvent
- [ ] Denial UI shows reasoning from audit
- [ ] Elevation triggers re-query + animation
- [ ] 20+ negative scenarios all reject correctly
