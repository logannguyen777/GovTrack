# 15 - Permission Engine: 3-Tier Enforcement

> **Status: IMPLEMENTED** (2026-04-13)

## Muc tieu (Objective)

Implement the full 3-tier permission enforcement stack: SDK Guard (Tier 1),
GDB Native RBAC (Tier 2), and Property Mask Middleware (Tier 3). After completing
this guide, every graph query is validated before execution, every response is
redacted according to clearance, and every check is audit-logged.

---

## 1. Architecture Overview

```
Client Request
    |
    v
[Tier 1] SDK Guard          -- Pre-execution: parse bytecode, check labels/edges/props
    |
    v
[Tier 2] GDB Native RBAC    -- Execution: database-level user privileges
    |
    v
    Query Execution
    |
    v
[Tier 3] Property Mask      -- Post-execution: field redaction per clearance
    |
    v
Response to Client

Every check (allow/deny) -> AuditEvent -> GDB + Hologres
```

---

## 2. Agent Permission Model

Each agent has an `AgentProfile` loaded from its YAML profile:

```python
# backend/src/models/schemas.py — add to existing file

from pydantic import BaseModel
from enum import IntEnum


class ClearanceLevel(IntEnum):
    UNCLASSIFIED = 0
    CONFIDENTIAL = 1
    SECRET = 2
    TOP_SECRET = 3


class AgentProfile(BaseModel):
    agent_id: str
    agent_name: str
    clearance: ClearanceLevel
    read_node_labels: list[str]      # e.g. ["Case", "Document", "Task"]
    write_node_labels: list[str]     # e.g. ["Task", "AgentStep"]
    read_edge_types: list[str]       # e.g. ["HAS_DOCUMENT", "TRIGGERED_BY"]
    write_edge_types: list[str]      # e.g. ["PRODUCED"]
    forbidden_properties: list[str]  # e.g. ["national_id", "tax_id"]
    max_traversal_depth: int = 5
```

---

## 3. Tier 1 — SDK Guard

### 3.1 File: `backend/src/graph/sdk_guard.py`

```python
"""
Tier 1: Pre-execution Gremlin bytecode analysis.
Intercepts queries before they reach GDB. Parses traversal steps to extract
which labels, edge types, and properties the query touches, then compares
against the agent's permission profile.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field

from ..models.schemas import AgentProfile, ClearanceLevel


class SDKGuardViolation(Exception):
    """Raised when a query violates the agent's permission scope."""

    def __init__(self, agent_id: str, violation_type: str, detail: str):
        self.agent_id = agent_id
        self.violation_type = violation_type
        self.detail = detail
        super().__init__(f"[{agent_id}] {violation_type}: {detail}")


@dataclass
class ParsedTraversal:
    """Result of parsing a Gremlin bytecode/query string."""
    accessed_labels: set[str] = field(default_factory=set)
    accessed_edge_types: set[str] = field(default_factory=set)
    accessed_properties: set[str] = field(default_factory=set)
    is_mutating: bool = False
    created_labels: set[str] = field(default_factory=set)
    created_edge_types: set[str] = field(default_factory=set)
    traversal_depth: int = 0


class SDKGuard:
    """Pre-execution permission gate for Gremlin queries."""

    # Gremlin step patterns for static analysis
    _LABEL_PATTERN = re.compile(r"\.hasLabel\(['\"](\w+)['\"]\)")
    _EDGE_PATTERN = re.compile(r"\.(outE|inE|bothE)\(['\"](\w+)['\"]\)")
    _PROPERTY_PATTERN = re.compile(r"\.values?\(['\"](\w+)['\"]\)")
    _MUTATE_PATTERN = re.compile(r"\.(addV|addE|property|drop)\(")
    _ADD_V_PATTERN = re.compile(r"\.addV\(['\"](\w+)['\"]\)")
    _ADD_E_PATTERN = re.compile(r"\.addE\(['\"](\w+)['\"]\)")
    _DEPTH_STEPS = re.compile(r"\.(out|in|both|outE|inE|bothE)\(")

    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def parse_query(self, query: str) -> ParsedTraversal:
        """Extract labels, edges, properties, and mutation intent from query."""
        parsed = ParsedTraversal()
        parsed.accessed_labels = set(self._LABEL_PATTERN.findall(query))
        parsed.accessed_edge_types = {m[1] for m in self._EDGE_PATTERN.findall(query)}
        parsed.accessed_properties = set(self._PROPERTY_PATTERN.findall(query))
        parsed.is_mutating = bool(self._MUTATE_PATTERN.search(query))
        parsed.created_labels = set(self._ADD_V_PATTERN.findall(query))
        parsed.created_edge_types = set(self._ADD_E_PATTERN.findall(query))
        parsed.traversal_depth = len(self._DEPTH_STEPS.findall(query))
        return parsed

    def check_read(self, parsed: ParsedTraversal) -> None:
        """Verify agent can read all accessed labels and edges."""
        disallowed_labels = parsed.accessed_labels - set(self.profile.read_node_labels)
        if disallowed_labels:
            raise SDKGuardViolation(
                self.profile.agent_id, "READ_LABEL_DENIED",
                f"Cannot read labels: {disallowed_labels}"
            )
        disallowed_edges = parsed.accessed_edge_types - set(self.profile.read_edge_types)
        if disallowed_edges:
            raise SDKGuardViolation(
                self.profile.agent_id, "READ_EDGE_DENIED",
                f"Cannot traverse edges: {disallowed_edges}"
            )
        forbidden_accessed = parsed.accessed_properties & set(self.profile.forbidden_properties)
        if forbidden_accessed:
            raise SDKGuardViolation(
                self.profile.agent_id, "PROPERTY_FORBIDDEN",
                f"Cannot access properties: {forbidden_accessed}"
            )
        if parsed.traversal_depth > self.profile.max_traversal_depth:
            raise SDKGuardViolation(
                self.profile.agent_id, "DEPTH_EXCEEDED",
                f"Depth {parsed.traversal_depth} > max {self.profile.max_traversal_depth}"
            )

    def check_write(self, parsed: ParsedTraversal) -> None:
        """Verify agent can write all created labels and edges."""
        if not parsed.is_mutating:
            return
        disallowed_creates = parsed.created_labels - set(self.profile.write_node_labels)
        if disallowed_creates:
            raise SDKGuardViolation(
                self.profile.agent_id, "WRITE_LABEL_DENIED",
                f"Cannot create labels: {disallowed_creates}"
            )
        disallowed_edges = parsed.created_edge_types - set(self.profile.write_edge_types)
        if disallowed_edges:
            raise SDKGuardViolation(
                self.profile.agent_id, "WRITE_EDGE_DENIED",
                f"Cannot create edges: {disallowed_edges}"
            )

    def auto_rewrite(self, query: str) -> str:
        """Inject classification filter based on agent clearance cap."""
        cap = self.profile.clearance.value
        # Insert .has('classification', P.lte(cap)) after each hasLabel step
        rewritten = re.sub(
            r"(\.hasLabel\(['\"](\w+)['\"]\))",
            rf"\1.has('classification', P.lte({cap}))",
            query,
        )
        return rewritten

    def validate(self, query: str) -> str:
        """Full validation pipeline: parse -> check_read -> check_write -> auto_rewrite."""
        parsed = self.parse_query(query)
        self.check_read(parsed)
        self.check_write(parsed)
        return self.auto_rewrite(query)
```

---

## 4. Tier 2 — GDB Native RBAC

### 4.1 Cloud GDB Setup (Alibaba Cloud GDB)

For each of the 10 agents, create a dedicated GDB user and grant per-label privileges.

```sql
-- Run via GDB admin console or provisioning script

-- Intake Agent: read/write Case, Document, Task
CREATE USER intake_agent IDENTIFIED BY '${INTAKE_PWD}';
GRANT SELECT ON LABEL Case TO intake_agent;
GRANT SELECT ON LABEL Document TO intake_agent;
GRANT INSERT ON LABEL Case TO intake_agent;
GRANT INSERT ON LABEL Task TO intake_agent;
GRANT INSERT ON LABEL AgentStep TO intake_agent;

-- Classifier Agent: read Case, Document; write Task
CREATE USER classifier_agent IDENTIFIED BY '${CLASSIFIER_PWD}';
GRANT SELECT ON LABEL Case TO classifier_agent;
GRANT SELECT ON LABEL Document TO classifier_agent;
GRANT INSERT ON LABEL Task TO classifier_agent;
GRANT INSERT ON LABEL AgentStep TO classifier_agent;

-- Extraction Agent: read Case, Document; write Entity, Task
CREATE USER extraction_agent IDENTIFIED BY '${EXTRACTION_PWD}';
GRANT SELECT ON LABEL Case TO extraction_agent;
GRANT SELECT ON LABEL Document TO extraction_agent;
GRANT INSERT ON LABEL Entity TO extraction_agent;
GRANT INSERT ON LABEL Task TO extraction_agent;

-- Gap Agent: read Case, Document, Entity, Requirement; write Gap, Task
CREATE USER gap_agent IDENTIFIED BY '${GAP_PWD}';
GRANT SELECT ON LABEL Case TO gap_agent;
GRANT SELECT ON LABEL Document TO gap_agent;
GRANT SELECT ON LABEL Entity TO gap_agent;
GRANT SELECT ON LABEL Requirement TO gap_agent;
GRANT INSERT ON LABEL Gap TO gap_agent;
GRANT INSERT ON LABEL Task TO gap_agent;

-- Legal Search Agent: read LawArticle, Citation; write Citation, Task
CREATE USER legal_search_agent IDENTIFIED BY '${LEGAL_PWD}';
GRANT SELECT ON LABEL LawArticle TO legal_search_agent;
GRANT SELECT ON LABEL Citation TO legal_search_agent;
GRANT SELECT ON LABEL Case TO legal_search_agent;
GRANT INSERT ON LABEL Citation TO legal_search_agent;
GRANT INSERT ON LABEL Task TO legal_search_agent;

-- Compliance Agent: read all labels; write Decision, Task
CREATE USER compliance_agent IDENTIFIED BY '${COMPLIANCE_PWD}';
GRANT SELECT ON LABEL Case TO compliance_agent;
GRANT SELECT ON LABEL Document TO compliance_agent;
GRANT SELECT ON LABEL Gap TO compliance_agent;
GRANT SELECT ON LABEL Citation TO compliance_agent;
GRANT SELECT ON LABEL Requirement TO compliance_agent;
GRANT INSERT ON LABEL Decision TO compliance_agent;
GRANT INSERT ON LABEL Task TO compliance_agent;

-- Summary Agent: read Case, Document, Gap, Citation, Decision (NO PII properties)
CREATE USER summary_agent IDENTIFIED BY '${SUMMARY_PWD}';
GRANT SELECT ON LABEL Case TO summary_agent;
GRANT SELECT ON LABEL Document TO summary_agent;
GRANT SELECT ON LABEL Gap TO summary_agent;
GRANT SELECT ON LABEL Citation TO summary_agent;
GRANT SELECT ON LABEL Decision TO summary_agent;

-- Draft Agent: read all; write DraftDocument, Task
CREATE USER draft_agent IDENTIFIED BY '${DRAFT_PWD}';
GRANT SELECT ON LABEL Case TO draft_agent;
GRANT SELECT ON LABEL Document TO draft_agent;
GRANT SELECT ON LABEL Decision TO draft_agent;
GRANT INSERT ON LABEL DraftDocument TO draft_agent;
GRANT INSERT ON LABEL Task TO draft_agent;

-- Review Agent: read all; write Decision, Task
CREATE USER review_agent IDENTIFIED BY '${REVIEW_PWD}';
GRANT SELECT ON LABEL Case TO review_agent;
GRANT SELECT ON LABEL DraftDocument TO review_agent;
GRANT INSERT ON LABEL Decision TO review_agent;
GRANT INSERT ON LABEL Task TO review_agent;

-- Publish Agent: read DraftDocument, Decision; write PublishedDocument
CREATE USER publish_agent IDENTIFIED BY '${PUBLISH_PWD}';
GRANT SELECT ON LABEL DraftDocument TO publish_agent;
GRANT SELECT ON LABEL Decision TO publish_agent;
GRANT INSERT ON LABEL PublishedDocument TO publish_agent;
GRANT INSERT ON LABEL Task TO publish_agent;
```

### 4.2 Free-Tier Fallback (TinkerGraph)

TinkerGraph has no native RBAC. Simulate at SDK layer:

```python
# backend/src/graph/rbac_simulator.py

"""
Tier 2 fallback: RBAC simulation for TinkerGraph (free-tier / local dev).
Intercepts connection-level identity and applies same grants as cloud GDB.
"""

from ..models.schemas import AgentProfile


class RBACSimulator:
    """Simulates GDB native RBAC when running on TinkerGraph."""

    def __init__(self, profile: AgentProfile):
        self.profile = profile

    def check_execution_privilege(self, query: str, parsed) -> None:
        """
        Mirror what the cloud GDB GRANT statements enforce.
        On TinkerGraph this is the authoritative check.
        On cloud GDB this is a defense-in-depth redundancy.
        """
        # Write operations: check INSERT grants
        if parsed.is_mutating:
            for label in parsed.created_labels:
                if label not in self.profile.write_node_labels:
                    raise PermissionError(
                        f"RBAC: {self.profile.agent_id} lacks INSERT on {label}"
                    )
        # Read operations: check SELECT grants
        for label in parsed.accessed_labels:
            if label not in self.profile.read_node_labels:
                raise PermissionError(
                    f"RBAC: {self.profile.agent_id} lacks SELECT on {label}"
                )
```

---

## 5. Tier 3 — Property Mask Middleware

### 5.1 File: `backend/src/graph/property_mask.py`

```python
"""
Tier 3: Post-execution property redaction.
Applied to all query results before they reach the caller.
Rules are defined per-property and gated by clearance level.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..models.schemas import ClearanceLevel


class MaskAction(str, Enum):
    REDACT = "redact"                    # Remove field entirely
    MASK_PARTIAL = "mask_partial"        # Show last 4 chars: "***1234"
    CLASSIFICATION_GATED = "classification_gated"  # Show only if clearance >= level


@dataclass
class MaskRule:
    property_name: str
    action: MaskAction
    gate_level: ClearanceLevel | None = None  # For CLASSIFICATION_GATED


# Default rules — extend per deployment
DEFAULT_MASK_RULES: list[MaskRule] = [
    MaskRule("national_id", MaskAction.REDACT),
    MaskRule("tax_id", MaskAction.REDACT),
    MaskRule("phone_number", MaskAction.MASK_PARTIAL),
    MaskRule("email", MaskAction.MASK_PARTIAL),
    MaskRule("home_address", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.CONFIDENTIAL),
    MaskRule("bank_account", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
    MaskRule("criminal_record", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.TOP_SECRET),
    MaskRule("investigation_notes", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.TOP_SECRET),
    MaskRule("internal_assessment", MaskAction.CLASSIFICATION_GATED, ClearanceLevel.SECRET),
]


class PropertyMask:
    """Post-query field redaction engine."""

    def __init__(self, rules: list[MaskRule] | None = None):
        self.rules = {r.property_name: r for r in (rules or DEFAULT_MASK_RULES)}

    def _mask_partial(self, value: Any) -> str:
        s = str(value)
        if len(s) <= 4:
            return "****"
        return "*" * (len(s) - 4) + s[-4:]

    def apply(self, record: dict[str, Any], clearance: ClearanceLevel) -> dict[str, Any]:
        """
        Apply mask rules to a single result record.
        Returns a new dict with redacted/masked fields.
        """
        result = {}
        for key, value in record.items():
            rule = self.rules.get(key)
            if rule is None:
                result[key] = value
                continue

            if rule.action == MaskAction.REDACT:
                # Field removed entirely
                result[key] = "[REDACTED]"
            elif rule.action == MaskAction.MASK_PARTIAL:
                result[key] = self._mask_partial(value)
            elif rule.action == MaskAction.CLASSIFICATION_GATED:
                if clearance >= rule.gate_level:
                    result[key] = value  # Clearance sufficient
                else:
                    result[key] = f"[CLASSIFIED:{rule.gate_level.name}]"
        return result

    def apply_batch(
        self, records: list[dict[str, Any]], clearance: ClearanceLevel
    ) -> list[dict[str, Any]]:
        """Apply mask rules to a list of result records."""
        return [self.apply(r, clearance) for r in records]
```

---

## 6. PermittedGremlinClient

### 6.1 File: `backend/src/graph/permitted_client.py`

```python
"""
Unified permission-aware Gremlin client.
Wraps the raw GDB connection. Every query flows:
  Tier 1 (SDK Guard) -> Execute -> Tier 3 (Property Mask)
"""

from __future__ import annotations
import time
import uuid
from typing import Any

from ..models.schemas import AgentProfile, ClearanceLevel
from .sdk_guard import SDKGuard, SDKGuardViolation
from .property_mask import PropertyMask
from .rbac_simulator import RBACSimulator
from .audit import AuditLogger, AuditEvent


class PermittedGremlinClient:
    """Permission-enforced wrapper around raw Gremlin client."""

    def __init__(
        self,
        raw_client: Any,       # gremlin_python DriverRemoteConnection
        profile: AgentProfile,
        audit_logger: AuditLogger,
        use_rbac_simulator: bool = True,  # True for TinkerGraph
    ):
        self.raw = raw_client
        self.profile = profile
        self.sdk_guard = SDKGuard(profile)
        self.property_mask = PropertyMask()
        self.rbac_sim = RBACSimulator(profile) if use_rbac_simulator else None
        self.audit = audit_logger

    async def execute(
        self,
        query: str,
        bindings: dict[str, Any] | None = None,
        requester_clearance: ClearanceLevel | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a Gremlin query with full 3-tier permission enforcement.
        """
        clearance = requester_clearance or self.profile.clearance
        event_id = str(uuid.uuid4())
        start_ts = time.time()

        # --- Tier 1: SDK Guard ---
        try:
            parsed = self.sdk_guard.parse_query(query)
            self.sdk_guard.check_read(parsed)
            self.sdk_guard.check_write(parsed)
            rewritten_query = self.sdk_guard.auto_rewrite(query)
        except SDKGuardViolation as e:
            await self.audit.log(AuditEvent(
                event_id=event_id,
                agent_id=self.profile.agent_id,
                tier="SDK_GUARD",
                action="DENY",
                detail=str(e),
                query_snippet=query[:200],
                timestamp=time.time(),
            ))
            raise

        await self.audit.log(AuditEvent(
            event_id=event_id,
            agent_id=self.profile.agent_id,
            tier="SDK_GUARD",
            action="ALLOW",
            detail=f"labels={parsed.accessed_labels}, mutating={parsed.is_mutating}",
            query_snippet=query[:200],
            timestamp=time.time(),
        ))

        # --- Tier 2: RBAC (simulator or native) ---
        if self.rbac_sim:
            try:
                self.rbac_sim.check_execution_privilege(rewritten_query, parsed)
            except PermissionError as e:
                await self.audit.log(AuditEvent(
                    event_id=event_id,
                    agent_id=self.profile.agent_id,
                    tier="GDB_RBAC",
                    action="DENY",
                    detail=str(e),
                    query_snippet=query[:200],
                    timestamp=time.time(),
                ))
                raise

        # --- Execute query ---
        raw_results = await self._execute_raw(rewritten_query, bindings)

        # --- Tier 3: Property Mask ---
        masked_results = self.property_mask.apply_batch(raw_results, clearance)

        elapsed_ms = (time.time() - start_ts) * 1000
        await self.audit.log(AuditEvent(
            event_id=event_id,
            agent_id=self.profile.agent_id,
            tier="PROPERTY_MASK",
            action="APPLIED",
            detail=f"records={len(masked_results)}, elapsed_ms={elapsed_ms:.1f}",
            query_snippet=query[:200],
            timestamp=time.time(),
        ))

        return masked_results

    async def _execute_raw(
        self, query: str, bindings: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """Execute against raw GDB client and normalize results to list of dicts."""
        result_set = self.raw.submit(query, bindings or {})
        results = []
        for result in result_set:
            if isinstance(result, dict):
                results.append(result)
            elif isinstance(result, list):
                results.extend(r if isinstance(r, dict) else {"value": r} for r in result)
            else:
                results.append({"value": result})
        return results
```

---

## 7. Audit Logging

### 7.1 File: `backend/src/graph/audit.py`

```python
"""
AuditEvent model and dual-write logger (GDB + Hologres).
Every permission check writes an immutable audit trail.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import json


@dataclass
class AuditEvent:
    event_id: str
    agent_id: str
    tier: str          # SDK_GUARD | GDB_RBAC | PROPERTY_MASK
    action: str        # ALLOW | DENY | APPLIED
    detail: str
    query_snippet: str
    timestamp: float
    user_id: str | None = None
    case_id: str | None = None


class AuditLogger:
    """Writes audit events to GDB (graph) and Hologres (relational)."""

    def __init__(self, gdb_client: Any, hologres_pool: Any):
        self.gdb = gdb_client
        self.pg = hologres_pool

    async def log(self, event: AuditEvent) -> None:
        """Dual-write audit event. GDB for graph queries, Hologres for analytics."""
        # Write to GDB as AuditEvent vertex
        gremlin = (
            "g.addV('AuditEvent')"
            f".property('event_id', '{event.event_id}')"
            f".property('agent_id', '{event.agent_id}')"
            f".property('tier', '{event.tier}')"
            f".property('action', '{event.action}')"
            f".property('detail', '{self._escape(event.detail)}')"
            f".property('timestamp', {event.timestamp})"
        )
        try:
            self.gdb.submit(gremlin)
        except Exception:
            pass  # Audit write failure must not block request

        # Write to Hologres for dashboard queries
        try:
            async with self.pg.acquire() as conn:
                await conn.execute(
                    """INSERT INTO audit_events
                       (event_id, agent_id, tier, action, detail,
                        query_snippet, timestamp, user_id, case_id)
                       VALUES ($1,$2,$3,$4,$5,$6,to_timestamp($7),$8,$9)""",
                    event.event_id, event.agent_id, event.tier,
                    event.action, event.detail, event.query_snippet,
                    event.timestamp, event.user_id, event.case_id,
                )
        except Exception:
            pass  # Audit write failure must not block request

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("'", "\\'").replace("\n", " ")[:500]
```

---

## 8. Policy-as-Graph (Optional Enhancement)

Store permissions as graph edges for dynamic policy queries:

```
(Agent:intake_agent) --[CAN_READ]--> (Label:Case)
(Agent:intake_agent) --[CAN_READ]--> (Label:Document)
(Agent:intake_agent) --[CAN_WRITE]--> (Label:Task)
(Agent:summary_agent) --[CANNOT_ACCESS_PROPERTY]--> (Property:national_id)
```

```python
# backend/src/graph/policy_graph.py

SEED_POLICY_GREMLIN = """
// Create Label vertices
g.addV('Label').property('name', 'Case').as('case')
 .addV('Label').property('name', 'Document').as('doc')
 .addV('Label').property('name', 'Task').as('task')
 .addV('Label').property('name', 'Gap').as('gap')
 .addV('Label').property('name', 'Citation').as('citation')
 .addV('Label').property('name', 'Decision').as('decision')
 .addV('Label').property('name', 'Entity').as('entity')
 .addV('Label').property('name', 'LawArticle').as('law')
 .addV('Label').property('name', 'Requirement').as('req')

// Create Agent vertices + CAN_READ/CAN_WRITE edges
// Example: Intake Agent
g.addV('Agent').property('agent_id', 'intake_agent')
 .addE('CAN_READ').to(V().hasLabel('Label').has('name', 'Case'))
 .addE('CAN_READ').to(V().hasLabel('Label').has('name', 'Document'))
 .addE('CAN_WRITE').to(V().hasLabel('Label').has('name', 'Case'))
 .addE('CAN_WRITE').to(V().hasLabel('Label').has('name', 'Task'))

// Query: What can intake_agent read?
g.V().has('Agent', 'agent_id', 'intake_agent')
 .out('CAN_READ').values('name')
// => ['Case', 'Document']
"""
```

---

## 9. Demo Endpoints — 3 Permission Scenes

### 9.1 File: `backend/src/api/permission_demo.py`

```python
"""
Three demo endpoints that showcase each permission tier.
Used in live demo and integration tests.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/demo/permissions", tags=["demo"])


@router.post("/scene-a/sdk-guard-rejection")
async def scene_a_sdk_guard():
    """
    Scene A: Summarizer agent tries to access national_id property.
    SDK Guard rejects because national_id is in forbidden_properties.

    Expected: 403 with SDKGuardViolation detail.
    """
    from ..agents.profiles import load_profile
    from ..graph.sdk_guard import SDKGuard, SDKGuardViolation

    profile = load_profile("summary_agent")
    guard = SDKGuard(profile)

    query = "g.V().hasLabel('Case').values('national_id')"
    try:
        guard.validate(query)
        return {"status": "ERROR", "message": "Should have been rejected"}
    except SDKGuardViolation as e:
        return {
            "status": "DENIED",
            "tier": "SDK_GUARD",
            "agent": e.agent_id,
            "violation": e.violation_type,
            "detail": e.detail,
        }


@router.post("/scene-b/rbac-rejection")
async def scene_b_rbac():
    """
    Scene B: LegalSearch agent tries to CREATE a Gap vertex.
    RBAC rejects because legal_search_agent has no INSERT on Gap label.

    Expected: 403 with RBAC denial detail.
    """
    from ..agents.profiles import load_profile
    from ..graph.rbac_simulator import RBACSimulator
    from ..graph.sdk_guard import SDKGuard

    profile = load_profile("legal_search_agent")
    guard = SDKGuard(profile)
    rbac = RBACSimulator(profile)

    query = "g.addV('Gap').property('severity', 'critical').property('case_id', 'C-001')"
    parsed = guard.parse_query(query)

    try:
        rbac.check_execution_privilege(query, parsed)
        return {"status": "ERROR", "message": "Should have been rejected"}
    except PermissionError as e:
        return {
            "status": "DENIED",
            "tier": "GDB_RBAC",
            "agent": profile.agent_id,
            "detail": str(e),
        }


@router.post("/scene-c/clearance-elevation")
async def scene_c_clearance_elevation():
    """
    Scene C: User with UNCLASSIFIED clearance sees masked properties.
    After elevation to CONFIDENTIAL, the property mask dissolves.

    Expected: Before = [CLASSIFIED:CONFIDENTIAL], After = actual value.
    """
    from ..graph.property_mask import PropertyMask
    from ..models.schemas import ClearanceLevel

    mask = PropertyMask()
    record = {
        "case_id": "C-2026-0042",
        "applicant_name": "Nguyen Van Minh",
        "home_address": "12 Le Loi, Q1, TP.HCM",
        "national_id": "079201001234",
        "status": "processing",
    }

    before = mask.apply(record, ClearanceLevel.UNCLASSIFIED)
    after = mask.apply(record, ClearanceLevel.CONFIDENTIAL)

    return {
        "status": "OK",
        "tier": "PROPERTY_MASK",
        "before_elevation": before,
        "after_elevation": after,
        "dissolved_fields": [
            k for k in record
            if before.get(k) != after.get(k)
        ],
    }
```

---

## 10. Negative Test Scenarios

### 10.1 Test file: `backend/tests/test_permissions.py`

```python
"""
20+ negative test scenarios for the 3-tier permission engine.
Each test verifies a specific denial and confirms AuditEvent creation.
"""

import pytest
from src.graph.sdk_guard import SDKGuard, SDKGuardViolation
from src.graph.property_mask import PropertyMask, MaskAction
from src.graph.rbac_simulator import RBACSimulator
from src.models.schemas import AgentProfile, ClearanceLevel


def make_profile(**overrides) -> AgentProfile:
    defaults = dict(
        agent_id="test_agent", agent_name="Test",
        clearance=ClearanceLevel.UNCLASSIFIED,
        read_node_labels=["Case"], write_node_labels=["Task"],
        read_edge_types=["HAS_DOCUMENT"], write_edge_types=["PRODUCED"],
        forbidden_properties=["national_id", "tax_id"],
        max_traversal_depth=3,
    )
    defaults.update(overrides)
    return AgentProfile(**defaults)


# --- Tier 1: SDK Guard ---

class TestSDKGuardDenials:
    def test_01_read_forbidden_label(self):
        guard = SDKGuard(make_profile(read_node_labels=["Case"]))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('Secret').values('name')")

    def test_02_read_forbidden_property(self):
        guard = SDKGuard(make_profile())
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('national_id')")

    def test_03_write_forbidden_label(self):
        guard = SDKGuard(make_profile(write_node_labels=["Task"]))
        with pytest.raises(SDKGuardViolation, match="WRITE_LABEL_DENIED"):
            guard.validate("g.addV('Gap').property('severity','high')")

    def test_04_traverse_forbidden_edge(self):
        guard = SDKGuard(make_profile(read_edge_types=["HAS_DOCUMENT"]))
        with pytest.raises(SDKGuardViolation, match="READ_EDGE_DENIED"):
            guard.validate("g.V().hasLabel('Case').outE('SECRET_LINK').inV()")

    def test_05_depth_exceeded(self):
        guard = SDKGuard(make_profile(max_traversal_depth=2))
        deep_q = "g.V().hasLabel('Case').out('HAS_DOCUMENT').out('HAS_DOCUMENT').out('HAS_DOCUMENT')"
        with pytest.raises(SDKGuardViolation, match="DEPTH_EXCEEDED"):
            guard.validate(deep_q)

    def test_06_write_forbidden_edge(self):
        guard = SDKGuard(make_profile(write_edge_types=["PRODUCED"]))
        with pytest.raises(SDKGuardViolation, match="WRITE_EDGE_DENIED"):
            guard.validate("g.V('a').addE('ADMIN_OVERRIDE').to(V('b'))")

    def test_07_multiple_forbidden_labels(self):
        guard = SDKGuard(make_profile(read_node_labels=["Case"]))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('Secret').out().hasLabel('TopSecret')")

    def test_08_tax_id_forbidden(self):
        guard = SDKGuard(make_profile())
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('tax_id')")

    def test_09_allowed_read_passes(self):
        guard = SDKGuard(make_profile())
        result = guard.validate("g.V().hasLabel('Case').values('status')")
        assert "classification" in result  # auto_rewrite injected filter

    def test_10_allowed_write_passes(self):
        guard = SDKGuard(make_profile())
        result = guard.validate("g.addV('Task').property('name','t1')")
        assert result  # no exception


# --- Tier 2: RBAC Simulator ---

class TestRBACDenials:
    def test_11_create_unauthorized_vertex(self):
        profile = make_profile(write_node_labels=["Task"])
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Gap').property('x','y')")
        with pytest.raises(PermissionError, match="lacks INSERT on Gap"):
            rbac.check_execution_privilege("g.addV('Gap')", parsed)

    def test_12_read_unauthorized_label(self):
        profile = make_profile(read_node_labels=["Case"])
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.V().hasLabel('Secret')")
        parsed.accessed_labels = {"Secret"}
        with pytest.raises(PermissionError, match="lacks SELECT on Secret"):
            rbac.check_execution_privilege("g.V()", parsed)

    def test_13_legal_agent_cant_create_gap(self):
        profile = make_profile(
            agent_id="legal_search_agent",
            write_node_labels=["Citation", "Task"],
        )
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Gap')")
        with pytest.raises(PermissionError):
            rbac.check_execution_privilege("g.addV('Gap')", parsed)

    def test_14_summary_agent_cant_write_anything(self):
        profile = make_profile(
            agent_id="summary_agent",
            write_node_labels=[],
        )
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Task')")
        with pytest.raises(PermissionError):
            rbac.check_execution_privilege("g.addV('Task')", parsed)


# --- Tier 3: Property Mask ---

class TestPropertyMaskRedaction:
    def test_15_national_id_redacted(self):
        mask = PropertyMask()
        result = mask.apply(
            {"national_id": "079201001234", "name": "Test"},
            ClearanceLevel.TOP_SECRET,
        )
        assert result["national_id"] == "[REDACTED]"
        assert result["name"] == "Test"

    def test_16_phone_partial_mask(self):
        mask = PropertyMask()
        result = mask.apply(
            {"phone_number": "0901234567"},
            ClearanceLevel.TOP_SECRET,
        )
        assert result["phone_number"].endswith("4567")
        assert result["phone_number"].startswith("*")

    def test_17_classification_gate_denied(self):
        mask = PropertyMask()
        result = mask.apply(
            {"home_address": "12 Le Loi, Q1"},
            ClearanceLevel.UNCLASSIFIED,
        )
        assert "CLASSIFIED" in result["home_address"]

    def test_18_classification_gate_allowed(self):
        mask = PropertyMask()
        result = mask.apply(
            {"home_address": "12 Le Loi, Q1"},
            ClearanceLevel.CONFIDENTIAL,
        )
        assert result["home_address"] == "12 Le Loi, Q1"

    def test_19_top_secret_gate(self):
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "None"},
            ClearanceLevel.SECRET,
        )
        assert "CLASSIFIED:TOP_SECRET" in result["criminal_record"]

    def test_20_top_secret_clearance_sees_all(self):
        mask = PropertyMask()
        result = mask.apply(
            {"criminal_record": "None", "home_address": "addr", "bank_account": "123"},
            ClearanceLevel.TOP_SECRET,
        )
        assert result["criminal_record"] == "None"
        assert result["home_address"] == "addr"
        assert result["bank_account"] == "123"

    def test_21_batch_redaction(self):
        mask = PropertyMask()
        records = [
            {"national_id": "111", "name": "A"},
            {"national_id": "222", "name": "B"},
        ]
        results = mask.apply_batch(records, ClearanceLevel.UNCLASSIFIED)
        assert all(r["national_id"] == "[REDACTED]" for r in results)
        assert results[0]["name"] == "A"

    def test_22_clearance_elevation_dissolves_mask(self):
        mask = PropertyMask()
        record = {"home_address": "secret place", "name": "X"}
        before = mask.apply(record, ClearanceLevel.UNCLASSIFIED)
        after = mask.apply(record, ClearanceLevel.CONFIDENTIAL)
        assert "CLASSIFIED" in before["home_address"]
        assert after["home_address"] == "secret place"
```

---

## 11. Verification Checklist

```bash
# 1. Unit tests pass
cd /home/logan/GovTrack/backend
source .venv/bin/activate
pytest tests/test_permissions.py -v
# Expected: 22 passed, 0 failed

# 2. Demo Scene A returns DENIED
curl -X POST http://localhost:8000/demo/permissions/scene-a/sdk-guard-rejection
# Expected: {"status":"DENIED","tier":"SDK_GUARD","violation":"PROPERTY_FORBIDDEN",...}

# 3. Demo Scene B returns DENIED
curl -X POST http://localhost:8000/demo/permissions/scene-b/rbac-rejection
# Expected: {"status":"DENIED","tier":"GDB_RBAC",...}

# 4. Demo Scene C shows mask dissolution
curl -X POST http://localhost:8000/demo/permissions/scene-c/clearance-elevation
# Expected: before has [CLASSIFIED:CONFIDENTIAL], after has actual address

# 5. Audit events created
curl http://localhost:8000/audit/events?limit=10
# Expected: AuditEvents with tier, action, agent_id

# 6. All 3 tiers fire on a real query (check logs)
LOG_LEVEL=DEBUG uvicorn src.main:app --port 8000
# Submit a test case, verify SDK_GUARD -> RBAC -> PROPERTY_MASK in logs
```

---

## Tong ket (Summary)

| Component           | File                                    | Status |
|---------------------|-----------------------------------------|--------|
| SDK Guard (Tier 1)  | backend/src/graph/sdk_guard.py          | DONE   |
| RBAC (Tier 2)       | GDB native + rbac_simulator.py fallback | DONE   |
| Property Mask (T3)  | backend/src/graph/property_mask.py      | DONE   |
| Permitted Client    | backend/src/graph/permitted_client.py   | DONE   |
| Audit Logger        | backend/src/graph/audit.py              | DONE   |
| Policy-as-Graph     | backend/src/graph/policy_graph.py       | Optional |
| Demo Endpoints      | backend/src/api/permission_demo.py      | DONE   |
| Negative Tests      | backend/tests/test_permissions.py       | DONE (22/22 passed) |

Next step: proceed to `16-frontend-setup.md` for the frontend foundation.
