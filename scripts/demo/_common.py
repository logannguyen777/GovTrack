"""Shared helpers for demo scenario scripts."""
from __future__ import annotations

import os

import httpx

BASE_HTTP = os.environ.get("GOVFLOW_API", "http://localhost:8100")
BASE_WS = os.environ.get("GOVFLOW_WS", "ws://localhost:8100/api/ws")


async def login(username: str, password: str = "demo") -> str:
    """POST /auth/login and return the JWT access token."""
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=30.0) as client:
        resp = await client.post(
            "/auth/login",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
