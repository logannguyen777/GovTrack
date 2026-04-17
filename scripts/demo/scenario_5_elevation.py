"""
Scenario 5: Clearance elevation.
Duration: ~15 seconds

Logs in as progressively-cleared users and diffs which fields of
CASE-2026-0001 are visible vs. masked. This demonstrates the Tier-3
property-mask of the permission engine.

Users (all password "demo") in ascending clearance order:
  citizen_demo  <  staff_intake  <  cv_qldt  <  legal_expert / security_officer
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx
from _common import BASE_HTTP, auth_headers  # noqa: E402

HERO_CASE_ID = "CASE-2026-0001"

# (username) — clearance level is read from login response (authoritative)
USERS = [
    "citizen_demo",
    "staff_intake",
    "cv_qldt",
    "legal_expert",
    "security_officer",
]

FIELDS_OF_INTEREST = [
    "code", "status", "tthc_code", "department_id",
    "applicant_name",
    # Sensitive — masked by property_mask engine per role + clearance
    "applicant_id_number",   # REDACT always (national ID never exposed)
    "applicant_phone",       # MASK_PARTIAL always
    "applicant_address",     # CLASSIFICATION_GATED ≥ CONFIDENTIAL
    "submitted_at",
]


def _is_masked(v) -> bool:
    if v is None:
        return True
    s = str(v)
    return "***" in s or "[REDACTED]" in s.upper() or s == "" or s == "N/A"


async def fetch_case(token: str) -> dict | None:
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=15.0) as c:
        resp = await c.get(
            f"/cases/{HERO_CASE_ID}", headers=auth_headers(token),
        )
        if resp.status_code >= 400:
            return {"_error": resp.status_code, "_detail": resp.text[:150]}
        return resp.json()


async def login_and_clearance(username: str) -> tuple[str, int] | None:
    """POST /auth/login; return (token, clearance_level) or None on failure."""
    try:
        async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=15.0) as c:
            resp = await c.post(
                "/auth/login",
                json={"username": username, "password": "demo"},
            )
            resp.raise_for_status()
            j = resp.json()
            return j["access_token"], int(j.get("clearance_level", 0))
    except Exception as e:
        print(f"  login failed: {e}")
        return None


async def run() -> None:
    print(f"Elevation demo on {HERO_CASE_ID} — "
          f"viewing progressively cleared users\n")
    for username in USERS:
        res = await login_and_clearance(username)
        if res is None:
            print(f"[skip] {username}: cannot login\n")
            continue
        token, clearance = res
        print("=" * 56)
        print(f"User: {username}  |  Clearance: {clearance}")
        print("=" * 56)

        case = await fetch_case(token)
        if not case or "_error" in (case or {}):
            print(f"  fetch error: {case}")
            continue

        for f in FIELDS_OF_INTEREST:
            v = case.get(f, "<absent>")
            marker = "***" if _is_masked(v) else "   "
            print(f"  {marker} {f:18s} = {v}")
        print()

    print("[done] Elevation demo complete — fields reveal as clearance rises.")


if __name__ == "__main__":
    asyncio.run(run())
