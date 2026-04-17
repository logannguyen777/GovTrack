"""
tests/test_request_id.py
Verify X-Request-ID echo and uuid4 generation (Task 3.4).
"""

from __future__ import annotations

import re
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app

UUID4_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@pytest.mark.asyncio
async def test_request_id_echoed_when_provided():
    """If client sends X-Request-ID, response echoes the same value."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/healthz", headers={"X-Request-ID": "test-req-123"})

    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == "test-req-123"


@pytest.mark.asyncio
async def test_request_id_generated_when_absent():
    """If no X-Request-ID header, server generates a uuid4."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get("/healthz")

    assert resp.status_code == 200
    req_id = resp.headers.get("x-request-id", "")
    assert req_id != "", "X-Request-ID header should be present"
    assert UUID4_RE.match(req_id), f"Expected uuid4, got: {req_id!r}"


@pytest.mark.asyncio
async def test_correlation_id_echoed():
    """X-Correlation-ID is echoed back when provided."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        resp = await client.get(
            "/healthz",
            headers={
                "X-Request-ID": "req-abc",
                "X-Correlation-ID": "corr-xyz",
            },
        )

    assert resp.headers.get("x-request-id") == "req-abc"
    assert resp.headers.get("x-correlation-id") == "corr-xyz"


@pytest.mark.asyncio
async def test_different_requests_get_different_ids():
    """Without a provided ID, two requests get different generated IDs."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        r1 = await client.get("/healthz")
        r2 = await client.get("/healthz")

    id1 = r1.headers.get("x-request-id")
    id2 = r2.headers.get("x-request-id")
    assert id1 != id2, "Each request should get a unique request ID"
