"""
Unified permission-aware Gremlin client.
Wraps the raw GDB connection. Every query flows:
  Tier 1 (SDK Guard) -> Tier 2 (RBAC) -> Execute -> Tier 3 (Property Mask)
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from ..models.schemas import AgentProfile
from ..models.enums import ClearanceLevel
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
        from ..database import async_gremlin_submit
        raw = await async_gremlin_submit(query, bindings)
        results = []
        for result in raw:
            if isinstance(result, dict):
                results.append(result)
            elif isinstance(result, list):
                results.extend(r if isinstance(r, dict) else {"value": r} for r in result)
            else:
                results.append({"value": result})
        return results
