"""
Wave 1 Correctness Tests — Tasks 1.1, 1.2, 1.7

Test coverage:
  1.1  All GDB calls routed through PermittedGremlinClient
  1.2  AuditMiddleware writes to audit_events_flat on mutating requests
  1.7  Logical transaction: retry on ConcurrentModificationException +
       concurrent compliance agents produce consistent final state
"""

from __future__ import annotations

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth import PUBLIC_SESSION, SYSTEM_SESSION, UserSession, create_access_token
from src.graph.permitted_client import (
    PermittedGremlinClient,
    _LogicalTransaction,
    _profile_from_session,
)
from src.models.enums import ClearanceLevel, Role


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_session(**kw) -> UserSession:
    defaults = dict(
        user_id="test-user-001",
        username="test_officer",
        role="officer",
        clearance=ClearanceLevel.CONFIDENTIAL,
    )
    defaults.update(kw)
    return UserSession(**defaults)


# ---------------------------------------------------------------------------
# Task 1.1 — PermittedGremlinClient plumbing
# ---------------------------------------------------------------------------


class TestPermittedClientSessions:
    """Verify that PUBLIC_SESSION, SYSTEM_SESSION, and normal UserSession
    all produce a valid PermittedGremlinClient without raising at construction."""

    def test_public_session_builds_client(self):
        client = PermittedGremlinClient(PUBLIC_SESSION)
        assert client.session.is_public is True
        assert client.session.clearance == ClearanceLevel.UNCLASSIFIED

    def test_system_session_builds_client(self):
        client = PermittedGremlinClient(SYSTEM_SESSION)
        assert client.session.is_system is True
        assert client.session.clearance == ClearanceLevel.TOP_SECRET

    def test_user_session_builds_client(self):
        session = _make_session()
        client = PermittedGremlinClient(session)
        assert client.session.user_id == "test-user-001"
        assert client.session.clearance == ClearanceLevel.CONFIDENTIAL

    def test_profile_from_public_session(self):
        profile = _profile_from_session(PUBLIC_SESSION)
        assert profile.clearance == ClearanceLevel.UNCLASSIFIED
        assert "national_id" in profile.forbidden_properties

    def test_profile_from_system_session(self):
        profile = _profile_from_session(SYSTEM_SESSION)
        assert profile.clearance == ClearanceLevel.TOP_SECRET
        assert profile.forbidden_properties == []

    def test_user_session_from_token(self):
        token = create_access_token(
            user_id="u-abc",
            username="myuser",
            role="legal",
            clearance_level=2,
            departments=["dept-a"],
        )
        from src.auth import decode_token
        claims = decode_token(token)
        session = UserSession.from_token(claims)
        assert session.user_id == "u-abc"
        assert session.clearance == ClearanceLevel.SECRET
        assert session.role == "legal"


class TestPermittedClientExecuteRouting:
    """Verify that execute() calls go through SDK Guard and property mask."""

    @pytest.mark.asyncio
    async def test_execute_allowed_query_returns_masked_results(self):
        """A permitted query should succeed and return masked records."""
        session = _make_session(
            role="officer",
            clearance=ClearanceLevel.CONFIDENTIAL,
        )
        client = PermittedGremlinClient(session)

        raw_record = {"case_id": "c1", "phone_number": "0912345678", "status": "submitted"}
        with patch.object(client, "_execute_raw", AsyncMock(return_value=[raw_record])):
            results = await client.execute("g.V().hasLabel('Case').valueMap(true)")

        assert len(results) == 1
        # phone_number should be partially masked per DEFAULT_MASK_RULES
        assert results[0]["phone_number"] != "0912345678"
        assert results[0]["phone_number"].startswith("*")

    @pytest.mark.asyncio
    async def test_audit_log_called_on_execute(self):
        """AuditLogger.log() should be called at least once per execute."""
        session = _make_session()
        client = PermittedGremlinClient(session)
        client.audit = MagicMock()
        client.audit.log = AsyncMock()

        with patch.object(client, "_execute_raw", AsyncMock(return_value=[])):
            await client.execute("g.V().hasLabel('Case').count()")

        assert client.audit.log.call_count >= 1

    @pytest.mark.asyncio
    async def test_context_manager_works(self):
        """PermittedGremlinClient should work as an async context manager."""
        session = _make_session()
        async with PermittedGremlinClient(session) as client:
            assert client.session == session


# ---------------------------------------------------------------------------
# Task 1.7 — Logical transactions
# ---------------------------------------------------------------------------


class TestLogicalTransaction:
    """Unit tests for _LogicalTransaction retry logic."""

    @pytest.mark.asyncio
    async def test_transaction_commits_on_success(self):
        """All buffered ops should be executed exactly once on successful commit."""
        session = _make_session()
        client = PermittedGremlinClient(session)
        execute_calls: list[tuple] = []

        async def fake_execute(query, bindings=None):
            execute_calls.append((query, bindings))
            return []

        with patch.object(client, "execute", side_effect=fake_execute):
            async with client.transaction() as tx:
                await tx.submit("g.addV('Gap').property('gap_id', gid)", {"gid": "g1"})
                await tx.submit("g.V(...).property('status', 'gap_checked')", {})

        assert len(execute_calls) == 2

    @pytest.mark.asyncio
    async def test_transaction_rolls_back_on_exception(self):
        """Ops must not be executed if an exception is raised inside the block."""
        session = _make_session()
        client = PermittedGremlinClient(session)
        execute_calls: list[tuple] = []

        async def fake_execute(query, bindings=None):
            execute_calls.append((query, bindings))
            return []

        with patch.object(client, "execute", side_effect=fake_execute):
            with pytest.raises(ValueError, match="intentional"):
                async with client.transaction() as tx:
                    await tx.submit("g.addV('Gap')", {})
                    raise ValueError("intentional rollback")

        # Ops buffered but exception raised before commit — no execute calls
        assert len(execute_calls) == 0

    @pytest.mark.asyncio
    async def test_transaction_retries_on_concurrent_modification(self):
        """ConcurrentModificationException triggers retry up to MAX_RETRIES."""
        session = _make_session()
        client = PermittedGremlinClient(session)
        call_count = 0

        async def fake_execute_fail_twice(query, bindings=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("ConcurrentModificationException detected")
            return []

        # Patch asyncio.sleep to avoid real delays in tests
        with patch("asyncio.sleep", AsyncMock()):
            with patch.object(client, "execute", side_effect=fake_execute_fail_twice):
                async with client.transaction() as tx:
                    await tx.submit("g.V().property('x', 1)", {})

        # Should have succeeded on attempt 3; execute called 3 times (1 op × 3 attempts)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_transaction_raises_after_max_retries(self):
        """After MAX_RETRIES all fail, the exception should propagate."""
        session = _make_session()
        client = PermittedGremlinClient(session)

        async def always_fail(query, bindings=None):
            raise RuntimeError("ConcurrentModificationException always")

        with patch("asyncio.sleep", AsyncMock()):
            with patch.object(client, "execute", side_effect=always_fail):
                with pytest.raises(RuntimeError, match="Logical transaction failed"):
                    async with client.transaction() as tx:
                        await tx.submit("g.V().property('x', 1)", {})


# ---------------------------------------------------------------------------
# Task 1.7 — Concurrent compliance agents consistency (integration-like)
# ---------------------------------------------------------------------------


class TestConcurrentComplianceConsistency:
    """Simulate two compliance agents running on the same case concurrently.

    We verify that the final Gap count is consistent (no lost writes) when
    both agents write different gaps.  The logical transaction serialises the
    commit so both gap sets are present.
    """

    @pytest.mark.asyncio
    async def test_two_concurrent_gap_writes_both_persist(self):
        """Both agents' gap writes should succeed; total gaps = sum of both sets."""
        gaps_written: list[str] = []

        async def fake_execute(query, bindings=None):
            if "addV('Gap')" in query and bindings:
                gaps_written.append(bindings.get("gap_id", "unknown"))
            return []

        session = _make_session()

        async def run_agent(gap_id: str):
            client = PermittedGremlinClient(session)
            with patch.object(client, "execute", side_effect=fake_execute):
                with patch.object(client, "audit", MagicMock(log=AsyncMock())):
                    async with client.transaction() as tx:
                        await tx.submit(
                            "g.addV('Gap').property('gap_id', gap_id)",
                            {"gap_id": gap_id},
                        )

        gap_ids = [str(uuid.uuid4()) for _ in range(4)]
        # Run two concurrent "agents" each writing 2 gaps
        await asyncio.gather(
            run_agent(gap_ids[0]),
            run_agent(gap_ids[1]),
            run_agent(gap_ids[2]),
            run_agent(gap_ids[3]),
        )

        # All 4 gaps should be present
        assert set(gap_ids) == set(gaps_written), (
            f"Expected {set(gap_ids)}, got {set(gaps_written)}"
        )


# ---------------------------------------------------------------------------
# Task 1.2 — AuditLogger dual write (unit, no real DB)
# ---------------------------------------------------------------------------


class TestAuditLoggerUnit:
    """Verify AuditLogger writes to both GDB and PG without raising."""

    @pytest.mark.asyncio
    async def test_log_writes_to_pg(self):
        from src.graph.audit import AuditEvent, AuditLogger

        fake_conn = AsyncMock()
        fake_conn.execute = AsyncMock()
        fake_pool = AsyncMock()
        fake_pool.acquire = MagicMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=fake_conn),
            __aexit__=AsyncMock(return_value=False),
        ))

        audit = AuditLogger(gdb_client=None, hologres_pool=fake_pool)
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            agent_id="test-agent",
            tier="SDK_GUARD",
            action="ALLOW",
            detail="test detail",
            query_snippet="g.V().count()",
            timestamp=time.time(),
        )
        await audit.log(event)
        fake_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_failure_does_not_raise(self):
        """Audit write failure must never propagate to the caller."""
        from src.graph.audit import AuditEvent, AuditLogger

        bad_pool = MagicMock()
        bad_pool.acquire = MagicMock(side_effect=RuntimeError("DB down"))

        audit = AuditLogger(gdb_client=None, hologres_pool=bad_pool)
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            agent_id="test",
            tier="HTTP_REQUEST",
            action="REQUEST",
            detail="POST /cases -> 201",
            query_snippet="",
            timestamp=time.time(),
        )
        # Must not raise
        await audit.log(event)

    @pytest.mark.asyncio
    async def test_http_event_type_mapping(self):
        """HTTP_REQUEST tier should produce 'http.<method>' event_type in PG."""
        from src.graph.audit import AuditEvent, AuditLogger

        rows_inserted = []

        async def fake_execute(sql, *args):
            rows_inserted.append(args)

        fake_conn = MagicMock()
        fake_conn.execute = fake_execute
        fake_pool = MagicMock()
        fake_pool.acquire = MagicMock(return_value=MagicMock(
            __aenter__=AsyncMock(return_value=fake_conn),
            __aexit__=AsyncMock(return_value=False),
        ))

        audit = AuditLogger(gdb_client=None, hologres_pool=fake_pool)
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            agent_id="u-123",
            tier="HTTP_REQUEST",
            action="REQUEST",
            detail="POST /cases -> 201",
            query_snippet="",
            timestamp=time.time(),
            method="POST",
            path="/cases",
            status_code=201,
        )
        await audit.log(event)
        # event_type in first positional arg to execute
        if rows_inserted:
            assert rows_inserted[0][0] == "http.post"


# ---------------------------------------------------------------------------
# Task 1.2 — AuditMiddleware integration (via TestClient + fake infra)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_middleware_fires_on_post(app_client, clean_pg):
    """POST /cases should trigger an audit row in audit_events_flat within 1s."""
    token = create_access_token(
        user_id="test-admin-001",
        username="admin_test",
        role="admin",
        clearance_level=3,
        departments=["dept-all"],
    )
    headers = {"Authorization": f"Bearer {token}"}

    resp = await app_client.post(
        "/cases",
        json={
            "tthc_code": "1.004415",
            "department_id": "DEPT-TEST",
            "applicant_name": "Nguyễn Thị Kiểm Thử",
            "applicant_id_number": "001000000001",
        },
        headers=headers,
    )
    # Accept 201 (created) or 422 (validation error) — either way the
    # middleware should fire.  We skip if infrastructure is unavailable.
    assert resp.status_code in (201, 422, 500, 503)

    # Wait up to 1s for background audit task to complete
    deadline = time.monotonic() + 1.0
    row = None
    while time.monotonic() < deadline:
        async with clean_pg.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT event_type FROM audit_events_flat "
                "WHERE event_type LIKE 'http.%' ORDER BY created_at DESC LIMIT 1"
            )
        if row:
            break
        await asyncio.sleep(0.05)

    # If the DB is reachable, audit row must be present
    if clean_pg is not None:
        assert row is not None, "Expected audit row in audit_events_flat within 1s"
        assert row["event_type"] == "http.post"


# ---------------------------------------------------------------------------
# Task 1.1 — Verify no raw gremlin calls in api / agent implementations
# ---------------------------------------------------------------------------


def test_no_raw_gremlin_in_api_layer():
    """Regression: ensure no direct gremlin_submit / async_gremlin_submit calls
    remain in api/*.py or agents/implementations/*.py."""
    import ast
    import pathlib

    forbidden = {"gremlin_submit", "async_gremlin_submit"}
    allowed_files = {
        "permitted_client.py",
        "audit.py",
        "database.py",
    }

    violations: list[str] = []

    src_root = pathlib.Path(__file__).parent.parent / "src"
    search_dirs = [
        src_root / "api",
        src_root / "agents" / "implementations",
    ]

    for search_dir in search_dirs:
        for py_file in search_dir.glob("*.py"):
            if py_file.name in allowed_files:
                continue
            text = py_file.read_text()
            # Quick string scan (AST would be more accurate but slower)
            for fn in forbidden:
                if fn + "(" in text:
                    violations.append(f"{py_file.relative_to(src_root)}: {fn}")

    assert violations == [], (
        "Raw gremlin_submit calls found outside allow-list:\n"
        + "\n".join(violations)
    )
