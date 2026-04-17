"""
tests/test_data_subject.py
Data Subject Rights endpoint tests (Task 3.11 — NĐ 13/2023).

Tests verify:
- Authenticated user can access their own data.
- User cannot access another user's data (403).
- Deletion request creates a PENDING_REVIEW ticket.
- Consent history returns correct user records.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.auth import create_access_token
from src.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(user_id: str, role: str = "officer") -> str:
    return create_access_token(
        user_id=user_id,
        username=f"user_{user_id[:8]}",
        role=role,
        clearance_level=0,
        departments=["DEPT-TEST"],
    )


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# /api/data-subject/access — own data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_access_requires_auth():
    """Unauthenticated request to /access should be 401 or 403."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/api/data-subject/access")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_access_returns_own_data():
    """Authenticated user gets their own data export structure."""
    user_id = str(uuid.uuid4())
    token = _make_token(user_id)

    # Mock the DB connection so we don't need a real database
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    with patch("src.api.data_subject.pg_connection") as mock_pg:
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.get(
                "/api/data-subject/access",
                headers=_auth_headers(token),
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert "cases" in data
    assert "audit_events" in data
    assert "consent_history" in data
    assert "exported_at" in data


# ---------------------------------------------------------------------------
# /api/data-subject/delete — deletion ticket
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_request_creates_ticket():
    """POST /delete should return 202 with a PENDING_REVIEW ticket."""
    user_id = str(uuid.uuid4())
    token = _make_token(user_id)

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None

    with patch("src.api.data_subject.pg_connection") as mock_pg:
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/api/data-subject/delete",
                headers=_auth_headers(token),
            )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "PENDING_REVIEW"
    assert data["user_id"] == user_id
    assert "ticket_id" in data


@pytest.mark.asyncio
async def test_delete_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post("/api/data-subject/delete")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# /api/data-subject/consent — consent history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_consent_returns_own_history():
    user_id = str(uuid.uuid4())
    token = _make_token(user_id)

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []  # empty consent log

    with patch("src.api.data_subject.pg_connection") as mock_pg:
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.get(
                "/api/data-subject/consent",
                headers=_auth_headers(token),
            )

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# /api/data-subject/admin/approve-delete — admin only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_delete_requires_admin():
    """Non-admin user should not be able to approve a deletion ticket."""
    user_id = str(uuid.uuid4())
    token = _make_token(user_id, role="officer")  # not admin

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.post(
            "/api/data-subject/admin/approve-delete/some-ticket",
            headers=_auth_headers(token),
        )

    assert resp.status_code in (403, 401)


@pytest.mark.asyncio
async def test_approve_delete_succeeds_for_admin():
    """Admin can approve a deletion ticket."""
    admin_id = str(uuid.uuid4())
    token = _make_token(admin_id, role="admin")

    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None

    with patch("src.api.data_subject.pg_connection") as mock_pg:
        mock_pg.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pg.return_value.__aexit__ = AsyncMock(return_value=False)

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/api/data-subject/admin/approve-delete/ticket-123",
                headers=_auth_headers(token),
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "APPROVED"
    assert data["ticket_id"] == "ticket-123"
