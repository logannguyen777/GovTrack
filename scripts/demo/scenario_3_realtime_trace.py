"""
Scenario 3: Live agent trace via WebSocket.
Duration: ~60 seconds

Opens a WS connection, subscribes to case:{id} topic, creates a case + triggers
the pipeline, then streams agent events in real time. Designed to run alongside
the Trace Viewer UI.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import httpx
import websockets
from _common import BASE_HTTP, BASE_WS, auth_headers, login  # noqa: E402


async def run() -> None:
    print("[1/4] Login as staff_intake...")
    token = await login("staff_intake")
    h = auth_headers(token)

    print("[2/4] Creating case (so we can subscribe before pipeline runs)...")
    async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=30.0) as client:
        resp = await client.post(
            "/cases",
            json={
                "tthc_code": "1.004415",
                "department_id": "DEPT-QLDT",
                "applicant_name": "Realtime Demo User",
                "applicant_id_number": "024000000000",
                "applicant_phone": "0900000000",
                "applicant_address": "Binh Dinh",
                "notes": "Demo scenario 3 — realtime trace",
            },
            headers=h,
        )
        resp.raise_for_status()
        case_id = resp.json()["case_id"]
        print(f"     Case {case_id[:8]}... created")

    topic = f"case:{case_id}"

    print(f"[3/4] Connecting WS + subscribing to {topic}...")
    async with websockets.connect(BASE_WS) as ws:
        # Wave 0.7: auth handshake — first frame must be {action:auth, token}
        await ws.send(json.dumps({"action": "auth", "token": token}))
        auth_ack = await ws.recv()
        print(f"     WS auth: {auth_ack[:120]}")
        await ws.send(json.dumps({"action": "subscribe", "topic": topic}))
        ack = await ws.recv()
        print(f"     WS sub ack: {ack[:100]}")

        # Trigger pipeline in parallel
        async def trigger():
            async with httpx.AsyncClient(base_url=BASE_HTTP, timeout=30.0) as c:
                r = await c.post(
                    f"/agents/run/{case_id}",
                    json={"pipeline": "full"},
                    headers=h,
                )
                print(f"[trigger] pipeline started: {r.status_code}")

        asyncio.create_task(trigger())

        print("[4/4] Streaming events for up to 60s...\n")
        deadline = asyncio.get_event_loop().time() + 60
        event_count = 0
        try:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                except asyncio.TimeoutError:
                    print("[ws] idle 10s — stopping.")
                    break
                msg = json.loads(raw)
                ev = msg.get("event", "?")
                data = msg.get("data", {})
                event_count += 1
                if ev == "agent_started":
                    print(f"  >> STARTED  {data.get('agent_name', '?')}")
                elif ev == "agent_completed":
                    name = data.get("agent_name", "?")
                    summary = str(data.get("output_summary", ""))[:80]
                    print(f"  << DONE     {name} — {summary}")
                elif ev == "agent_failed":
                    print(f"  ** FAILED   {data.get('agent_name', '?')}: "
                          f"{data.get('error', '?')}")
                elif ev == "tool_executed":
                    print(f"  ++ TOOL     {data.get('tool_name', '?')}")
                else:
                    print(f"  -- {ev:<10} {json.dumps(data)[:100]}")
        finally:
            print(f"\n[done] {event_count} events received.")
            print(f"       View: http://localhost:3100/trace/{case_id}")


if __name__ == "__main__":
    asyncio.run(run())
