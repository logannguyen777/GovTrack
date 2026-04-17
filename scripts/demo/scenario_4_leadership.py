"""
Scenario 4: Leadership dashboard.
Duration: ~10 seconds

Logs in as ld_phong, fetches /leadership/dashboard and /leadership/inbox,
and prints a readable summary of the leadership KPIs + leader inbox.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx
from _common import BASE_HTTP, auth_headers, login  # noqa: E402


async def run() -> None:
    print("[1/3] Login as ld_phong (leader)...")
    token = await login("ld_phong")
    h = auth_headers(token)

    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=30.0) as client:
        print("\n[2/3] Leadership Dashboard")
        print("-" * 48)
        resp = await client.get("/leadership/dashboard", headers=h)
        if resp.status_code == 200:
            d = resp.json()
            print(f"  Total cases:       {d.get('total_cases', 'N/A')}")
            print(f"  Pending:           {d.get('pending_cases', 'N/A')}")
            print(f"  Overdue:           {d.get('overdue_cases', 'N/A')}")
            print(f"  Completed:         {d.get('completed_cases', 'N/A')}")
            print(f"  Avg processing d:  {d.get('avg_processing_days', 'N/A')}")
            print(f"  SLA compliance %:  {d.get('sla_compliance_rate', 'N/A')}")
            brief = d.get("weekly_brief") or d.get("brief")
            if brief:
                print(f"\n  Weekly brief: {str(brief)[:300]}")
            perf = d.get("agent_performance") or []
            if perf:
                print(f"\n  Agent performance ({len(perf)} agents):")
                for a in perf[:5]:
                    print(f"    {a.get('agent_name', '?'):15s} "
                          f"runs={a.get('total_runs', '?')} "
                          f"fail={a.get('failure_rate', '?')}")
        else:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")

        print("\n[3/3] Leader Inbox")
        print("-" * 48)
        resp = await client.get("/leadership/inbox", headers=h)
        if resp.status_code == 200:
            items = resp.json()
            print(f"  {len(items)} items awaiting leader action")
            for item in items[:8]:
                print(f"    - {item.get('code', '?'):24s} "
                      f"[{item.get('priority', '?'):6s}] "
                      f"{item.get('action_required', '?'):18s} "
                      f"— {item.get('title', '?')}")
        else:
            print(f"  ERROR {resp.status_code}: {resp.text[:200]}")

    print("\n[done] Scenario 4 complete.")


if __name__ == "__main__":
    asyncio.run(run())
