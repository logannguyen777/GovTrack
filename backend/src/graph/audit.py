"""
AuditEvent model and dual-write logger (GDB + Hologres).
Every permission check and every mutating HTTP request writes an immutable
audit trail.

Two categories of events:
  1. Permission-layer events (SDK_GUARD / GDB_RBAC / PROPERTY_MASK) —
     written by PermittedGremlinClient on every query.
  2. HTTP-layer events (HTTP_REQUEST) — written by AuditMiddleware for
     every mutating request (POST / PUT / PATCH / DELETE) under /api.

Failure policy: audit write failures are swallowed and counter-incremented.
They must NEVER crash or slow the request.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("govflow.audit")

# ---------------------------------------------------------------------------
# Failure counter (stub — replace with Prometheus counter in production)
# ---------------------------------------------------------------------------
_audit_write_failures_total: int = 0


def _inc_failure() -> None:
    global _audit_write_failures_total
    _audit_write_failures_total += 1


def get_audit_failure_count() -> int:
    return _audit_write_failures_total


# ---------------------------------------------------------------------------
# AuditEvent dataclass
# ---------------------------------------------------------------------------


@dataclass
class AuditEvent:
    event_id: str
    agent_id: str          # user_id or agent name
    tier: str              # SDK_GUARD | GDB_RBAC | PROPERTY_MASK | HTTP_REQUEST
    action: str            # ALLOW | DENY | APPLIED | REQUEST
    detail: str
    query_snippet: str
    timestamp: float
    # Optional fields
    user_id: str | None = None
    case_id: str | None = None
    # HTTP-layer fields (populated by AuditMiddleware)
    actor_user_id: str | None = None
    actor_role: str | None = None
    actor_clearance: int | None = None
    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    client_ip: str | None = None
    duration_ms: float | None = None
    user_agent: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------


class AuditLogger:
    """Writes audit events to GDB (graph) and Hologres (relational)."""

    def __init__(self, gdb_client: Any, hologres_pool: Any) -> None:
        self.gdb = gdb_client
        self.pg = hologres_pool

    async def log(self, event: AuditEvent) -> None:
        """
        Dual-write audit event.

        - GDB: AuditEvent vertex (graph queries / permission events)
        - Hologres: audit_events_flat row (analytics / compliance queries)

        Failure in either path is silently absorbed (logged to stderr,
        counter incremented) so audit writes never crash the request.
        """
        await self._write_gdb(event)
        await self._write_pg(event)

    async def _write_gdb(self, event: AuditEvent) -> None:
        try:
            gremlin = (
                "g.addV('AuditEvent')"
                ".property('event_id', event_id)"
                ".property('agent_id', agent_id)"
                ".property('tier', tier)"
                ".property('action', action)"
                ".property('detail', detail)"
                ".property('timestamp', timestamp)"
            )
            bindings: dict[str, Any] = {
                "event_id": event.event_id,
                "agent_id": event.agent_id,
                "tier": event.tier,
                "action": event.action,
                "detail": self._escape(event.detail),
                "timestamp": event.timestamp,
            }
            # Add optional HTTP fields when present
            if event.method:
                gremlin += ".property('method', ev_method)"
                bindings["ev_method"] = event.method
            if event.path:
                gremlin += ".property('path', ev_path)"
                bindings["ev_path"] = event.path
            if event.status_code is not None:
                gremlin += ".property('status_code', ev_status)"
                bindings["ev_status"] = event.status_code

            from ..database import async_gremlin_submit  # _RAW_GREMLIN_ALLOWED_MODULES: src.graph.audit

            await async_gremlin_submit(gremlin, bindings)
        except Exception as exc:
            _inc_failure()
            print(f"[AUDIT][GDB-WRITE-FAIL] {exc}", file=sys.stderr)

    async def _write_pg(self, event: AuditEvent) -> None:
        if not self.pg:
            return
        try:
            import json

            details_dict: dict[str, Any] = {}
            if event.query_snippet:
                details_dict["query_snippet"] = event.query_snippet
            if event.detail:
                details_dict["detail"] = event.detail
            if event.duration_ms is not None:
                details_dict["duration_ms"] = event.duration_ms
            if event.user_agent:
                details_dict["user_agent"] = event.user_agent
            if event.request_id:
                details_dict["request_id"] = event.request_id
            if event.correlation_id:
                details_dict["correlation_id"] = event.correlation_id
            details_dict.update(event.extra)

            # Map to audit_events_flat columns
            # event_type: prefer tier+action compound for permission events,
            # or HTTP_REQUEST for middleware events
            if event.tier == "HTTP_REQUEST":
                event_type = f"http.{(event.method or 'UNKNOWN').lower()}"
            else:
                event_type = f"{event.tier}.{event.action}"

            async with self.pg.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO audit_events_flat
                        (event_type, actor_name, target_type, target_id,
                         case_id, details, ip_address, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, to_timestamp($8))
                    """,
                    event_type,
                    event.actor_role or event.agent_id,
                    event.target_type or event.tier,
                    event.target_id or event.event_id,
                    event.case_id,
                    json.dumps(details_dict),
                    event.client_ip,
                    event.timestamp,
                )
        except Exception as exc:
            _inc_failure()
            print(f"[AUDIT][PG-WRITE-FAIL] {exc}", file=sys.stderr)

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("'", "\\'").replace("\n", " ")[:500]
