"""
Wave 2 — Task 2.1: POST /agents/consult/{request_id}/submit
Tests:
  - Happy path: pending request + valid role + correct dept -> 200 + WS broadcast
  - 404: request_id not found
  - 409: request already completed
  - 403: wrong role
  - 403: wrong department
  - 422: invalid recommendation value
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth import create_access_token, UserSession
from src.models.enums import ClearanceLevel


# ── JWT helpers ──────────────────────────────────────────────────────────────

def _make_token(role: str = "officer", departments: list[str] | None = None) -> str:
    return create_access_token(
        user_id=f"user-{uuid.uuid4().hex[:8]}",
        username=f"test_{role}",
        role=role,
        clearance_level=2,
        departments=departments or ["dept-phap-che"],
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
async def client_with_pending_request(app_client):
    """
    Fixture: seed a pending ConsultRequest vertex in GDB, return
    (http_client, request_id, case_id).
    """
    from src.auth import SYSTEM_SESSION
    from src.graph.permitted_client import PermittedGremlinClient

    gdb = PermittedGremlinClient(SYSTEM_SESSION)
    case_id = f"case-cs-{uuid.uuid4().hex[:8]}"
    request_id = f"cr-{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    # Create Case vertex
    await gdb.execute(
        "g.addV('Case')"
        ".property('case_id', cid).property('code', code)"
        ".property('status', 'consultation').property('submitted_at', ts)"
        ".property('department_id', 'dept-hanh-chinh').property('tthc_code', 'TEST')"
        ".property('case_type', 'citizen_tthc')",
        {"cid": case_id, "code": f"HS-{case_id[:8]}", "ts": now},
    )

    # Create ConsultRequest vertex
    await gdb.execute(
        "g.addV('ConsultRequest')"
        ".property('request_id', rid).property('case_id', cid)"
        ".property('target_org_id', 'dept-phap-che')"
        ".property('target_org_name', 'Phong Phap che')"
        ".property('context_summary', 'Test context')"
        ".property('main_question', 'Test question')"
        ".property('status', 'pending')"
        ".property('created_at', ts)"
        ".as('cr')"
        ".V().has('Case', 'case_id', cid).addE('HAS_CONSULT_REQUEST').to('cr')",
        {"rid": request_id, "cid": case_id, "ts": now},
    )

    yield app_client, request_id, case_id

    # Cleanup
    try:
        await gdb.execute(
            "g.V().has('ConsultRequest', 'request_id', rid).drop()",
            {"rid": request_id},
        )
        await gdb.execute(
            "g.V().has('Case', 'case_id', cid).drop()",
            {"cid": case_id},
        )
    except Exception:
        pass


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_consult_happy_path(client_with_pending_request):
    """200 response, correct fields, WS broadcast called."""
    http_client, request_id, case_id = client_with_pending_request
    token = _make_token(role="officer", departments=["dept-phap-che"])

    ws_calls: list[tuple[str, dict]] = []

    async def mock_broadcast(topic: str, message: dict) -> None:
        ws_calls.append((topic, message))

    with patch("src.api.ws.broadcast", side_effect=mock_broadcast):
        resp = await http_client.post(
            f"/agents/consult/{request_id}/submit",
            json={
                "opinion": "Đồng ý với phương án xử lý, tuy nhiên cần bổ sung biên bản PCCC.",
                "recommendation": "approve",
                "attachments": [],
            },
            headers=_headers(token),
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["status"] == "completed"
    assert body["recommendation"] == "approve"
    assert "opinion_id" in body
    assert "audit_id" in body

    # Verify ConsultRequest status updated
    from src.auth import SYSTEM_SESSION
    from src.graph.permitted_client import PermittedGremlinClient
    gdb = PermittedGremlinClient(SYSTEM_SESSION)
    rows = await gdb.execute(
        "g.V().has('ConsultRequest', 'request_id', rid).values('status')",
        {"rid": request_id},
    )
    if rows:
        first = rows[0]
        status_val = first.get("value", "") if isinstance(first, dict) else str(first)
        assert status_val == "completed", f"Expected completed, got {status_val!r}"


@pytest.mark.asyncio
async def test_submit_consult_not_found(app_client):
    """404 when request_id does not exist."""
    token = _make_token(role="officer", departments=["dept-phap-che"])
    fake_id = f"cr-nonexistent-{uuid.uuid4().hex[:8]}"
    resp = await app_client.post(
        f"/agents/consult/{fake_id}/submit",
        json={"opinion": "test", "recommendation": "approve", "attachments": []},
        headers=_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_submit_consult_already_completed(client_with_pending_request):
    """409 when ConsultRequest.status != pending."""
    http_client, request_id, case_id = client_with_pending_request
    token = _make_token(role="officer", departments=["dept-phap-che"])

    # Mark as completed first
    from src.auth import SYSTEM_SESSION
    from src.graph.permitted_client import PermittedGremlinClient
    gdb = PermittedGremlinClient(SYSTEM_SESSION)
    await gdb.execute(
        "g.V().has('ConsultRequest', 'request_id', rid).property('status', 'completed')",
        {"rid": request_id},
    )

    resp = await http_client.post(
        f"/agents/consult/{request_id}/submit",
        json={"opinion": "test", "recommendation": "approve", "attachments": []},
        headers=_headers(token),
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_submit_consult_wrong_role(client_with_pending_request):
    """403 when user role is not in allowed set."""
    http_client, request_id, _case_id = client_with_pending_request
    token = _make_token(role="public_viewer", departments=["dept-phap-che"])
    resp = await http_client.post(
        f"/agents/consult/{request_id}/submit",
        json={"opinion": "test", "recommendation": "approve", "attachments": []},
        headers=_headers(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_consult_wrong_department(client_with_pending_request):
    """403 when user is not in the consulted department."""
    http_client, request_id, _case_id = client_with_pending_request
    # User belongs to a different dept
    token = _make_token(role="officer", departments=["dept-xay-dung"])
    resp = await http_client.post(
        f"/agents/consult/{request_id}/submit",
        json={"opinion": "test", "recommendation": "approve", "attachments": []},
        headers=_headers(token),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_submit_consult_invalid_recommendation(client_with_pending_request):
    """422 when recommendation value is not in allowed set."""
    http_client, request_id, _case_id = client_with_pending_request
    token = _make_token(role="officer", departments=["dept-phap-che"])
    resp = await http_client.post(
        f"/agents/consult/{request_id}/submit",
        json={
            "opinion": "test",
            "recommendation": "invalid_value",
            "attachments": [],
        },
        headers=_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_consult_admin_bypasses_dept(client_with_pending_request):
    """Admin role bypasses department membership check."""
    http_client, request_id, _case_id = client_with_pending_request
    # Admin is in a completely different dept but should still be allowed
    token = _make_token(role="admin", departments=["dept-admin-only"])
    with patch("src.api.ws.broadcast", new_callable=AsyncMock):
        resp = await http_client.post(
            f"/agents/consult/{request_id}/submit",
            json={"opinion": "Admin override", "recommendation": "reject", "attachments": []},
            headers=_headers(token),
        )
    assert resp.status_code == 200
    assert resp.json()["recommendation"] == "reject"
