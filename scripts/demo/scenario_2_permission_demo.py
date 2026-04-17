"""
Scenario 2: Three permission-engine scenes.
Duration: ~10 seconds

Scene A: SDK Guard rejects Summarizer access to national_id
Scene B: GDB RBAC blocks LegalSearch from creating Gap vertex
Scene C: Clearance elevation dissolves property mask
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx
from _common import BASE_HTTP  # noqa: E402


async def run() -> None:
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=15.0) as client:
        # --- Scene A ---
        print("=" * 60)
        print("SCENE A: SDK Guard Rejection")
        print("=" * 60)
        resp = await client.post("/demo/permissions/scene-a/sdk-guard-rejection")
        r = resp.json()
        print(f"  Status:    {r.get('status', '?')}")
        print(f"  Tier:      {r.get('tier', '?')}")
        print(f"  Violation: {r.get('violation', '?')}")
        print(f"  Detail:    {r.get('detail', '?')}")
        print()

        # --- Scene B ---
        print("=" * 60)
        print("SCENE B: GDB RBAC Rejection")
        print("=" * 60)
        resp = await client.post("/demo/permissions/scene-b/rbac-rejection")
        r = resp.json()
        print(f"  Status:    {r.get('status', '?')}")
        print(f"  Tier:      {r.get('tier', '?')}")
        print(f"  Detail:    {r.get('detail', '?')}")
        print()

        # --- Scene C ---
        print("=" * 60)
        print("SCENE C: Clearance Elevation")
        print("=" * 60)
        resp = await client.post("/demo/permissions/scene-c/clearance-elevation")
        r = resp.json()
        before = r.get("before_elevation") or r.get("before") or {}
        after = r.get("after_elevation") or r.get("after") or {}
        print("  BEFORE elevation (low clearance):")
        for k, v in before.items():
            print(f"    {k}: {v}")
        print("  AFTER elevation (higher clearance):")
        for k, v in after.items():
            print(f"    {k}: {v}")
        if "dissolved_fields" in r:
            print(f"  Dissolved fields: {r['dissolved_fields']}")
        print()

        print("[done] All 3 permission scenes demonstrated successfully.")


if __name__ == "__main__":
    asyncio.run(run())
