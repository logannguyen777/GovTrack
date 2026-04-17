"""
Unified permission-aware Gremlin client.
Wraps the raw GDB connection. Every query flows:
  Tier 1 (SDK Guard) -> Tier 2 (RBAC) -> Execute -> Tier 3 (Property Mask)

Allow-list for modules that MAY call raw async_gremlin_submit / gremlin_submit directly:
  - src/graph/permitted_client.py   (this file — _execute_raw)
  - src/graph/audit.py              (AuditLogger writes its own AuditEvent vertices)
  - src/database.py                 (health checks, lifespan init)
  - scripts/*                       (data-pipeline / bootstrap scripts)

Any other module adding a direct call must be added here and reviewed by a human.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from ..models.enums import ClearanceLevel
from .audit import AuditEvent, AuditLogger
from .sdk_guard import SDKGuard, SDKGuardViolation

if TYPE_CHECKING:
    from ..auth import UserSession
    from ..models.schemas import AgentProfile

logger = logging.getLogger("govflow.permitted_client")

# ---------------------------------------------------------------------------
# Allow-list: modules permitted to call raw gremlin_submit / async_gremlin_submit
# ---------------------------------------------------------------------------
_RAW_GREMLIN_ALLOWED_MODULES = frozenset(
    {
        "src.graph.permitted_client",  # this file
        "src.graph.audit",             # AuditLogger dual-write
        "src.database",                # lifespan health checks
        "scripts",                     # data pipeline / bootstrap (prefix match)
    }
)


def _query_hash(query: str) -> str:
    """SHA-256 prefix of the query string for audit correlation."""
    return hashlib.sha256(query.encode()).hexdigest()[:16]


class _LogicalTransaction:
    """
    Logical transaction: collects Gremlin ops and executes them in order.

    Alibaba Cloud GDB supports TinkerPop 3.x sessions but not the full
    `g.tx()` bytecode protocol over the WebSocket transport.  We implement
    a logical transaction that:
      1. Buffers (query, bindings) pairs.
      2. On __aexit__ without exception: runs them sequentially via the
         PermittedGremlinClient, retrying on ConcurrentModificationException.
      3. On __aexit__ with exception: discards the buffer (rollback).

    Ops within the buffer are NOT isolated from concurrent writers, but they
    are guaranteed to be executed as a contiguous sequence, and the retry
    logic ensures eventual consistency under light contention.

    If the infrastructure ever supports native g.tx().commit(), replace the
    submit() calls below with a single batched traversal.
    """

    MAX_RETRIES = 3
    BASE_BACKOFF_S = 0.1  # 100 ms

    def __init__(self, client: PermittedGremlinClient) -> None:
        self._client = client
        self._ops: list[tuple[str, dict[str, Any] | None]] = []
        self._committed = False

    async def submit(
        self, query: str, bindings: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Buffer an op for execution at commit time; returns empty list immediately."""
        self._ops.append((query, bindings))
        return []

    async def _execute_all(self) -> None:
        """Execute buffered ops with retry on ConcurrentModificationException."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                for query, bindings in self._ops:
                    await self._client.execute(query, bindings)
                self._committed = True
                return
            except Exception as exc:
                if "ConcurrentModificationException" in str(exc):
                    if attempt < self.MAX_RETRIES:
                        backoff = self.BASE_BACKOFF_S * (2 ** (attempt - 1))
                        logger.warning(
                            "ConcurrentModificationException in logical tx "
                            "(attempt %d/%d), retrying in %.2fs",
                            attempt, self.MAX_RETRIES, backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    # Last attempt exhausted
                    raise RuntimeError(
                        f"Logical transaction failed after {self.MAX_RETRIES} retries "
                        "due to ConcurrentModificationException"
                    ) from exc
                raise

    async def __aenter__(self) -> _LogicalTransaction:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            # No exception — commit
            await self._execute_all()
        # Exception or commit — clear buffer either way
        self._ops.clear()
        return False  # Never suppress exceptions


class PermittedGremlinClient:
    """
    Permission-enforced wrapper around raw Gremlin client.

    Accepts either a UserSession (for API-layer requests) or an AgentProfile
    (legacy — converted internally via _session_from_profile).
    """

    def __init__(
        self,
        session: UserSession,
        audit_logger: AuditLogger | None = None,
        use_rbac_simulator: bool = True,
    ) -> None:
        from ..graph.rbac_simulator import RBACSimulator

        self.session = session
        # Build a minimal AgentProfile-compatible object for SDKGuard / RBACSimulator
        self._perm_profile = _profile_from_session(session)
        self.sdk_guard = SDKGuard(self._perm_profile)
        self.rbac_sim = RBACSimulator(self._perm_profile) if use_rbac_simulator else None

        from .property_mask import PropertyMask

        self.property_mask = PropertyMask()

        # Audit logger: use provided one or create a default (db-backed)
        if audit_logger is not None:
            self.audit = audit_logger
        else:
            from ..database import get_gremlin_client, get_pg_pool

            try:
                gdb = get_gremlin_client()
            except RuntimeError:
                gdb = None
            try:
                pg = get_pg_pool()
            except RuntimeError:
                pg = None
            self.audit = AuditLogger(gdb_client=gdb, hologres_pool=pg)

    # ------------------------------------------------------------------
    # Context manager support (for `async with PermittedGremlinClient(s)`)
    # ------------------------------------------------------------------

    async def __aenter__(self) -> PermittedGremlinClient:
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False

    # ------------------------------------------------------------------
    # Transaction support
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[_LogicalTransaction]:
        """
        Logical transaction context manager.

        Usage::

            async with client.transaction() as tx:
                await tx.submit("g.addE('HAS_GAP')...", {...})
                await tx.submit("g.V(...).property('status', 'gap_checked')", {...})
            # committed on exit; rolled back on exception
        """
        tx = _LogicalTransaction(self)
        async with tx:
            yield tx

    # ------------------------------------------------------------------
    # Core execute
    # ------------------------------------------------------------------

    async def execute(
        self,
        query: str,
        bindings: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a Gremlin query with full 3-tier permission enforcement."""
        clearance = self.session.clearance
        role = self.session.role
        event_id = str(uuid.uuid4())
        q_hash = _query_hash(query)

        # --- Tier 1: SDK Guard ---
        try:
            parsed = self.sdk_guard.parse_query(query)
            self.sdk_guard.check_read(parsed)
            self.sdk_guard.check_write(parsed)
            rewritten_query = self.sdk_guard.auto_rewrite(query)
        except SDKGuardViolation as exc:
            await self.audit.log(
                AuditEvent(
                    event_id=event_id,
                    agent_id=self.session.user_id,
                    tier="SDK_GUARD",
                    action="DENY",
                    detail=str(exc),
                    query_snippet=query[:200],
                    timestamp=time.time(),
                    user_id=self.session.user_id,
                )
            )
            raise

        await self.audit.log(
            AuditEvent(
                event_id=event_id,
                agent_id=self.session.user_id,
                tier="SDK_GUARD",
                action="ALLOW",
                detail=(
                    f"labels={parsed.accessed_labels},"
                    f"mutating={parsed.is_mutating},"
                    f"hash={q_hash}"
                ),
                query_snippet=query[:200],
                timestamp=time.time(),
                user_id=self.session.user_id,
            )
        )

        # --- Tier 2: RBAC ---
        if self.rbac_sim:
            try:
                self.rbac_sim.check_execution_privilege(rewritten_query, parsed)
            except PermissionError as exc:
                await self.audit.log(
                    AuditEvent(
                        event_id=event_id,
                        agent_id=self.session.user_id,
                        tier="GDB_RBAC",
                        action="DENY",
                        detail=str(exc),
                        query_snippet=query[:200],
                        timestamp=time.time(),
                        user_id=self.session.user_id,
                    )
                )
                raise

        # --- Execute ---
        start_ts = time.time()
        raw_results = await self._execute_raw(rewritten_query, bindings)
        elapsed_ms = (time.time() - start_ts) * 1000

        # --- Tier 3: Property Mask ---
        masked_results = self.property_mask.apply_batch(raw_results, clearance, role)

        await self.audit.log(
            AuditEvent(
                event_id=event_id,
                agent_id=self.session.user_id,
                tier="PROPERTY_MASK",
                action="APPLIED",
                detail=f"records={len(masked_results)},elapsed_ms={elapsed_ms:.1f},hash={q_hash}",
                query_snippet=query[:200],
                timestamp=time.time(),
                user_id=self.session.user_id,
            )
        )

        return masked_results

    # Alias used by legacy code
    async def submit(
        self, query: str, bindings: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        return await self.execute(query, bindings)

    # ------------------------------------------------------------------
    # Internal raw execution  (only this method may call async_gremlin_submit)
    # ------------------------------------------------------------------

    async def _execute_raw(
        self,
        query: str,
        bindings: dict[str, Any] | None,
        *,
        template_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Execute against raw GDB client and normalize results to list of dicts."""
        from ..database import (
            async_gremlin_submit,  # _RAW_GREMLIN_ALLOWED_MODULES: src.graph.permitted_client
        )

        # Wrap in OTel span for distributed tracing
        try:
            from ..telemetry import get_tracer

            tracer = get_tracer("govflow.gremlin")
            span_attrs: dict[str, str] = {"db.system": "gremlin"}
            if template_name:
                span_attrs["gremlin.template"] = template_name
            ctx_mgr = tracer.start_as_current_span(
                "gremlin.submit", attributes=span_attrs
            )
        except Exception:
            import contextlib

            ctx_mgr = contextlib.nullcontext()

        with ctx_mgr:
            raw = await async_gremlin_submit(query, bindings)
        results: list[dict[str, Any]] = []
        for result in raw:
            if isinstance(result, dict):
                results.append(result)
            elif isinstance(result, list):
                results.extend(r if isinstance(r, dict) else {"value": r} for r in result)
            else:
                results.append({"value": result})
        return results


# ---------------------------------------------------------------------------
# Helper: synthesise a minimal permission profile from a UserSession
# so that SDKGuard / RBACSimulator still work.
# ---------------------------------------------------------------------------

_FULL_LABELS = [
    "Case", "Document", "Bundle", "Task", "AgentStep",
    "LawArticle", "Citation", "Gap", "Decision", "Opinion",
    "Applicant", "Organization", "TTHCSpec", "ConsultRequest",
    "ConsultOpinion", "DispatchLog",
    "AuditEvent",
]
_FULL_EDGES = [
    "HAS_DOCUMENT", "HAS_BUNDLE", "PROCESSED_BY", "SUBMITTED_BY",
    "MATCHES_TTHC", "HAS_GAP", "CITES", "DECIDED_BY", "HAS_OPINION",
    "HAS_CONSULT_REQUEST", "DEPENDS_ON", "ASSIGNED_TO",
    "CLASSIFIED_AS", "REFERENCES", "HAS_SUMMARY", "HAS_DECISION",
    "HAS_DRAFT", "PRODUCED", "TRIGGERED_BY",
    "CONSULTED_BY", "REFERENCES_DOC", "DISPATCHED_TO",
]


def _profile_from_session(session: UserSession) -> AgentProfile:
    """
    Build a minimal AgentProfile from a UserSession for the permission engine.

    Rules:
    - SYSTEM_SESSION / TOP_SECRET + admin role: full access, no forbidden properties.
    - PUBLIC_SESSION: read-only, UNCLASSIFIED labels only.
    - Others: full label access (RBAC already gates at the route level),
      clearance from session, no extra forbidden properties.
    """
    from ..models.schemas import AgentProfile

    uid = session.user_id

    if session.is_system:
        return AgentProfile(
            agent_id=uid,
            agent_name="__system__",
            clearance=ClearanceLevel.TOP_SECRET,
            read_node_labels=_FULL_LABELS,
            write_node_labels=_FULL_LABELS,
            read_edge_types=_FULL_EDGES,
            write_edge_types=_FULL_EDGES,
            forbidden_properties=[],
            max_traversal_depth=10,
        )

    if session.is_public:
        public_labels = ["Case", "TTHCSpec", "Applicant", "Organization"]
        return AgentProfile(
            agent_id=uid,
            agent_name="__public__",
            clearance=ClearanceLevel.UNCLASSIFIED,
            read_node_labels=public_labels,
            write_node_labels=["Case", "Applicant", "Bundle"],
            read_edge_types=["SUBMITTED_BY", "HAS_BUNDLE", "MATCHES_TTHC"],
            write_edge_types=["SUBMITTED_BY", "HAS_BUNDLE"],
            forbidden_properties=[
                "national_id", "tax_id", "phone_number",
                "criminal_record", "investigation_notes",
                "medical_history", "mental_health_assessment",
                "internal_assessment", "bank_account",
            ],
            max_traversal_depth=3,
        )

    # Authenticated staff — derive forbidden props from clearance
    forbidden: list[str] = []
    if session.clearance < ClearanceLevel.SECRET:
        forbidden = ["criminal_record", "investigation_notes"]
    if session.clearance < ClearanceLevel.CONFIDENTIAL:
        forbidden += ["home_address", "bank_account", "internal_assessment"]

    return AgentProfile(
        agent_id=uid,
        agent_name=session.username,
        clearance=session.clearance,
        read_node_labels=_FULL_LABELS,
        write_node_labels=_FULL_LABELS,
        read_edge_types=_FULL_EDGES,
        write_edge_types=_FULL_EDGES,
        forbidden_properties=forbidden,
        max_traversal_depth=8,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------


async def get_permitted_gdb_for_session(session: UserSession) -> PermittedGremlinClient:
    """Return a PermittedGremlinClient bound to *session*."""
    return PermittedGremlinClient(session)


async def get_public_permitted_gdb() -> PermittedGremlinClient:
    """Return a PermittedGremlinClient bound to PUBLIC_SESSION."""
    from ..auth import PUBLIC_SESSION

    return PermittedGremlinClient(PUBLIC_SESSION)
