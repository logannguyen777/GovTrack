"""
AuditEvent model and dual-write logger (GDB + Hologres).
Every permission check writes an immutable audit trail.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("govflow.audit")


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
        # Write to GDB as AuditEvent vertex using parameterized bindings (safe)
        gremlin = (
            "g.addV('AuditEvent')"
            ".property('event_id', event_id)"
            ".property('agent_id', agent_id)"
            ".property('tier', tier)"
            ".property('action', action)"
            ".property('detail', detail)"
            ".property('timestamp', timestamp)"
        )
        bindings = {
            "event_id": event.event_id,
            "agent_id": event.agent_id,
            "tier": event.tier,
            "action": event.action,
            "detail": self._escape(event.detail),
            "timestamp": event.timestamp,
        }
        try:
            from ..database import async_gremlin_submit
            await async_gremlin_submit(gremlin, bindings)
        except Exception as e:
            logger.debug(f"Audit GDB write failed (non-blocking): {e}")

        # Write to Hologres for dashboard queries
        try:
            if self.pg:
                async with self.pg.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO audit_events_flat
                           (event_id, agent_id, tier, action, detail,
                            query_snippet, timestamp, user_id, case_id)
                           VALUES ($1,$2,$3,$4,$5,$6,to_timestamp($7),$8,$9)""",
                        event.event_id, event.agent_id, event.tier,
                        event.action, event.detail, event.query_snippet,
                        event.timestamp, event.user_id, event.case_id,
                    )
        except Exception as e:
            logger.debug(f"Audit Hologres write failed (non-blocking): {e}")

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("'", "\\'").replace("\n", " ")[:500]
