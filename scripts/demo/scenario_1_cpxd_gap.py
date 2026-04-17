"""
Scenario 1: Full CPXD pipeline with PCCC gap detection.
Duration: ~45 seconds

Flow:
  1. Login as staff_intake
  2. Create a CPXD case for applicant
  3. Request document bundle (upload URLs)
  4. Trigger agent pipeline
  5. Poll trace until pipeline completes (or times out)
  6. Read subgraph for gaps + citations
  7. Print summary
"""
from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx
from _common import BASE_HTTP, auth_headers, login  # noqa: E402


async def run() -> None:
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=30.0) as client:
        print("[1/6] Login as staff_intake...")
        token = await login("staff_intake")
        h = auth_headers(token)

        print("[2/6] Creating CPXD case...")
        resp = await client.post(
            "/cases",
            json={
                "tthc_code": "1.004415",
                "department_id": "DEPT-QLDT",
                "applicant_name": "Nguyen Van Minh",
                "applicant_id_number": "024090000123",
                "applicant_phone": "0901234567",
                "applicant_address": "12 Tran Phu, Binh Dinh",
                "notes": "Demo scenario 1 — CPXD with PCCC gap",
            },
            headers=h,
        )
        resp.raise_for_status()
        case = resp.json()
        case_id = case["case_id"]
        print(f"     Case created: {case['code']} (id={case_id[:8]}...)")

        print("[3/6] Requesting document bundle...")
        resp = await client.post(
            f"/cases/{case_id}/bundles",
            json={
                "files": [
                    {"filename": "don_cpxd.pdf", "content_type": "application/pdf", "size_bytes": 123456},
                    {"filename": "banve.pdf",    "content_type": "application/pdf", "size_bytes": 234567},
                    {"filename": "qsdd.pdf",     "content_type": "application/pdf", "size_bytes": 345678},
                    {"filename": "hopdong.pdf",  "content_type": "application/pdf", "size_bytes": 456789},
                ]
            },
            headers=h,
        )
        # Don't hard-fail if bundle schema differs; scenario still works
        # because seed_demo pre-wires the hero case's Documents anyway.
        if resp.status_code >= 400:
            print(f"     WARN bundle {resp.status_code}: {resp.text[:120]}")
        else:
            print(f"     Bundle {resp.json().get('bundle_id', '?')[:8]}... created")

        print("[4/6] Triggering agent pipeline...")
        resp = await client.post(
            f"/agents/run/{case_id}",
            json={"pipeline": "full"},
            headers=h,
        )
        if resp.status_code >= 400:
            print(f"     Pipeline trigger returned {resp.status_code}: {resp.text[:120]}")
        else:
            print("     Pipeline triggered")

        print("[5/6] Polling trace (up to 60s)...")
        start = time.monotonic()
        last_status = None
        while time.monotonic() - start < 60:
            resp = await client.get(f"/agents/trace/{case_id}", headers=h)
            if resp.status_code == 200:
                trace = resp.json()
                steps = trace.get("steps", [])
                running = sum(1 for s in steps if s.get("status") == "running")
                done = sum(1 for s in steps if s.get("status") == "completed")
                status = f"steps={len(steps)} running={running} done={done}"
                if status != last_status:
                    print(f"     {status}")
                    last_status = status
                if steps and running == 0 and done > 0:
                    break
            await asyncio.sleep(2)

        print("[6/6] Reading subgraph...")
        resp = await client.get(f"/graph/case/{case_id}/subgraph", headers=h)
        if resp.status_code == 200:
            graph = resp.json()
            nodes = graph.get("nodes", [])
            gaps = [n for n in nodes if n.get("type") == "Gap"
                    or n.get("label") == "Gap"]
            citations = [n for n in nodes if n.get("type") == "Citation"
                         or n.get("label") == "Citation"]
            print(f"     Subgraph: {len(nodes)} nodes, "
                  f"{len(graph.get('edges', []))} edges")
            for g in gaps:
                data = g.get("data") or g
                print(f"     GAP:  {data.get('description', '?')} "
                      f"[{data.get('severity', '?')}]")
            for c in citations:
                data = c.get("data") or c
                print(f"     CITE: {data.get('law_name', '?')} "
                      f"{data.get('article', '?')}")
        else:
            print(f"     WARN subgraph {resp.status_code}")

        print(f"\n[done] Scenario 1 complete — case {case_id[:8]} "
              f"@ {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
        print(f"       Trace UI: http://localhost:3100/trace/{case_id}")

        # --- Also show the pre-seeded hero case, which has the full graph ---
        print("\n" + "=" * 60)
        print("HERO CASE CASE-2026-0001 (pre-seeded, fully wired)")
        print("=" * 60)
        resp = await client.get(
            "/graph/case/CASE-2026-0001/subgraph", headers=h,
        )
        if resp.status_code == 200:
            hero = resp.json()
            nodes = hero.get("nodes", [])
            edges = hero.get("edges", [])
            by_type: dict[str, list] = {}
            for n in nodes:
                props = n.get("properties", {}) if isinstance(n, dict) else {}
                t = props.get("label") or n.get("type") or "?"
                by_type.setdefault(str(t), []).append(props)
            print(f"  Total: {len(nodes)} nodes / {len(edges)} edges")
            for t, ps in sorted(by_type.items()):
                labels = []
                for p in ps[:3]:
                    lbl = (p.get("code") or p.get("description")
                           or p.get("filename") or p.get("law_name")
                           or p.get("full_name") or p.get("citation_id")
                           or p.get("gap_id") or "?")
                    labels.append(str(lbl)[:40])
                print(f"    {t:12s}: {len(ps)} — {', '.join(labels)}")
        else:
            print(f"  WARN subgraph {resp.status_code}: {resp.text[:120]}")
        print(f"  UI: http://localhost:3100/trace/CASE-2026-0001")


if __name__ == "__main__":
    asyncio.run(run())
