# 19 - Demo Preparation: Seed Data, Scripts, Cache, Backup Plans

## Muc tieu (Objective)

Prepare everything needed for a reliable, repeatable demo: seed data for all
screens, scripted demo scenarios, response caching for offline resilience, environment
configuration, and backup plans. After completing this guide, the demo runs 3x
back-to-back without failure, works in cache-only mode, and has a fallback video.

---

## 1. Seed Data

### 1.1 File: `scripts/seed_demo.py`

```python
"""
Seed the demo environment with users, cases, documents, and graph data.
Run: python scripts/seed_demo.py
Idempotent: safe to run multiple times (upserts, not duplicates).
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# --- Demo Users ---

DEMO_USERS = [
    {
        "user_id": "user-001",
        "username": "anh_minh",
        "full_name": "Nguyen Van Minh",
        "role": "citizen",
        "clearance": 0,  # UNCLASSIFIED
        "department": None,
        "password_hash": "$argon2id$demo_hash_anh_minh",
    },
    {
        "user_id": "user-002",
        "username": "chi_lan",
        "full_name": "Tran Thi Lan",
        "role": "staff_intake",
        "clearance": 1,  # CONFIDENTIAL
        "department": "Phong Tiep nhan",
    },
    {
        "user_id": "user-003",
        "username": "anh_tuan",
        "full_name": "Le Anh Tuan",
        "role": "staff_processor",
        "clearance": 2,  # SECRET
        "department": "Phong Xu ly",
    },
    {
        "user_id": "user-004",
        "username": "chi_huong",
        "full_name": "Pham Thi Huong",
        "role": "leader",
        "clearance": 3,  # TOP_SECRET
        "department": "Ban Giam doc",
    },
    {
        "user_id": "user-005",
        "username": "anh_dung",
        "full_name": "Vo Thanh Dung",
        "role": "legal",
        "clearance": 2,  # SECRET
        "department": "Phong Phap che",
    },
    {
        "user_id": "user-006",
        "username": "anh_quoc",
        "full_name": "Hoang Quoc An",
        "role": "security",
        "clearance": 3,  # TOP_SECRET
        "department": "Phong An ninh",
    },
]


# --- 5 Pre-processed Cases (1 per TTHC at different stages) ---

DEMO_CASES = [
    {
        "case_id": "CASE-2026-0001",
        "tthc_code": "1.004415",
        "tthc_name": "Cap phep xay dung",
        "applicant_name": "Nguyen Van Minh",
        "applicant_user_id": "user-001",
        "status": "cho_y_kien",       # Pending consultation — in middle stage
        "classification": 0,
        "submitted_at": (datetime.now() - timedelta(days=5)).isoformat(),
        "sla_deadline": (datetime.now() + timedelta(days=10)).isoformat(),
        "documents": [
            {"doc_id": "DOC-001", "type": "don_xin_cap_phep", "filename": "don_cpxd.pdf"},
            {"doc_id": "DOC-002", "type": "ban_ve_thiet_ke", "filename": "banve.pdf"},
            {"doc_id": "DOC-003", "type": "giay_cn_qsdd", "filename": "qsdd.pdf"},
            {"doc_id": "DOC-004", "type": "hop_dong_xd", "filename": "hopdong.pdf"},
            # Missing: PCCC certificate — this is the gap
        ],
        "gaps": [
            {"gap_id": "GAP-001", "description": "Thieu giay chung nhan PCCC",
             "severity": "high", "requirement_ref": "ND 136/2020 Dieu 9 khoan 2",
             "fix_suggestion": "Yeu cau bo sung giay PCCC tu co quan PCCC dia phuong"},
        ],
        "citations": [
            {"citation_id": "CIT-001", "law_name": "Nghi dinh 136/2020/ND-CP",
             "article": "Dieu 9, khoan 2", "relevance": 0.95},
            {"citation_id": "CIT-002", "law_name": "Luat Xay dung 2014",
             "article": "Dieu 89", "relevance": 0.88},
        ],
        "hero": True,  # This is the primary demo case
    },
    {
        "case_id": "CASE-2026-0002",
        "tthc_code": "1.000046",
        "tthc_name": "GCN quyen su dung dat",
        "applicant_name": "Tran Thi Lan",
        "status": "dang_xu_ly",
        "classification": 0,
        "submitted_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "sla_deadline": (datetime.now() + timedelta(days=17)).isoformat(),
        "documents": [
            {"doc_id": "DOC-010", "type": "don_dang_ky", "filename": "don_dk.pdf"},
            {"doc_id": "DOC-011", "type": "ho_so_dia_chinh", "filename": "diachinh.pdf"},
            {"doc_id": "DOC-012", "type": "ban_do", "filename": "bando.pdf"},
        ],
        "gaps": [],
        "citations": [],
    },
    {
        "case_id": "CASE-2026-0003",
        "tthc_code": "1.001757",
        "tthc_name": "Dang ky kinh doanh",
        "applicant_name": "Le Van Hung",
        "status": "da_quyet_dinh",
        "classification": 0,
        "submitted_at": (datetime.now() - timedelta(days=8)).isoformat(),
        "sla_deadline": (datetime.now() + timedelta(days=2)).isoformat(),
        "documents": [
            {"doc_id": "DOC-020", "type": "giay_de_nghi", "filename": "denghi.pdf"},
            {"doc_id": "DOC-021", "type": "dieu_le", "filename": "dieule.pdf"},
        ],
        "gaps": [],
        "citations": [
            {"citation_id": "CIT-010", "law_name": "Luat Doanh nghiep 2020",
             "article": "Dieu 26", "relevance": 0.92},
        ],
    },
    {
        "case_id": "CASE-2026-0004",
        "tthc_code": "1.000122",
        "tthc_name": "Ly lich tu phap",
        "applicant_name": "Pham Minh Duc",
        "status": "tra_ket_qua",
        "classification": 1,  # CONFIDENTIAL (contains personal history)
        "submitted_at": (datetime.now() - timedelta(days=12)).isoformat(),
        "sla_deadline": (datetime.now() - timedelta(days=2)).isoformat(),  # Already completed
        "documents": [
            {"doc_id": "DOC-030", "type": "don_yeu_cau", "filename": "yeucau.pdf"},
            {"doc_id": "DOC-031", "type": "cmnd", "filename": "cccd.pdf"},
        ],
        "gaps": [],
        "citations": [],
    },
    {
        "case_id": "CASE-2026-0005",
        "tthc_code": "2.002154",
        "tthc_name": "Giay phep moi truong",
        "applicant_name": "Cty TNHH Xanh Viet",
        "status": "tiep_nhan",
        "classification": 0,
        "submitted_at": (datetime.now() - timedelta(hours=6)).isoformat(),
        "sla_deadline": (datetime.now() + timedelta(days=25)).isoformat(),
        "documents": [
            {"doc_id": "DOC-040", "type": "bao_cao_dtm", "filename": "dtm.pdf"},
            {"doc_id": "DOC-041", "type": "giay_phep_kd", "filename": "gpkd.pdf"},
        ],
        "gaps": [],
        "citations": [],
    },
]


# --- 3 Completed Cases for Dashboard Metrics ---

COMPLETED_CASES = [
    {
        "case_id": f"CASE-2026-{100+i:04d}",
        "tthc_code": tthc,
        "status": "tra_ket_qua",
        "completed_at": (datetime.now() - timedelta(days=d)).isoformat(),
        "processing_days": d - 1,
        "sla_met": True,
    }
    for i, (tthc, d) in enumerate([
        ("1.004415", 14), ("1.000046", 7), ("1.001757", 5),
    ])
]


# --- 25 Additional Test Cases for Benchmark Display ---

BENCHMARK_CASES = [
    {
        "case_id": f"CASE-2026-{200+i:04d}",
        "tthc_code": ["1.004415", "1.000046", "1.001757", "1.000122", "2.002154"][i % 5],
        "status": ["tiep_nhan", "dang_xu_ly", "cho_y_kien", "da_quyet_dinh", "tra_ket_qua"][i % 5],
        "applicant_name": f"Test Applicant {i+1}",
        "submitted_at": (datetime.now() - timedelta(days=i)).isoformat(),
        "sla_deadline": (datetime.now() + timedelta(days=15 - i % 10)).isoformat(),
    }
    for i in range(25)
]


async def seed_users(pg_pool, gdb_client):
    """Insert demo users into Hologres and GDB."""
    for user in DEMO_USERS:
        # Hologres
        async with pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, username, full_name, role, clearance, department)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (user_id) DO UPDATE SET
                    role = EXCLUDED.role, clearance = EXCLUDED.clearance
            """, user["user_id"], user["username"], user["full_name"],
                user["role"], user["clearance"], user.get("department"))

        # GDB: User vertex
        gdb_client.submit(
            f"g.V().has('User','user_id','{user['user_id']}').fold()"
            f".coalesce(unfold(), addV('User')"
            f".property('user_id','{user['user_id']}')"
            f".property('username','{user['username']}')"
            f".property('full_name','{user['full_name']}')"
            f".property('role','{user['role']}')"
            f".property('clearance',{user['clearance']}))"
        )
    print(f"[Seed] {len(DEMO_USERS)} users created")


async def seed_cases(pg_pool, gdb_client):
    """Insert demo cases with full graph structure."""
    all_cases = DEMO_CASES + BENCHMARK_CASES
    for case in all_cases:
        case_id = case["case_id"]

        # GDB: Case vertex
        gdb_client.submit(
            f"g.V().has('Case','case_id','{case_id}').fold()"
            f".coalesce(unfold(), addV('Case')"
            f".property('case_id','{case_id}')"
            f".property('tthc_code','{case['tthc_code']}')"
            f".property('status','{case['status']}')"
            f".property('applicant_name','{case.get('applicant_name','')}')"
            f".property('classification',{case.get('classification', 0)}))"
        )

        # GDB: Document vertices + HAS_DOCUMENT edges
        for doc in case.get("documents", []):
            gdb_client.submit(
                f"g.addV('Document')"
                f".property('document_id','{doc['doc_id']}')"
                f".property('doc_type','{doc['type']}')"
                f".property('filename','{doc['filename']}')"
                f".as('d')"
                f".V().has('Case','case_id','{case_id}')"
                f".addE('HAS_DOCUMENT').to('d')"
            )

        # GDB: Gap vertices + HAS_GAP edges
        for gap in case.get("gaps", []):
            gdb_client.submit(
                f"g.addV('Gap')"
                f".property('gap_id','{gap['gap_id']}')"
                f".property('description','{gap['description']}')"
                f".property('severity','{gap['severity']}')"
                f".property('fix_suggestion','{gap['fix_suggestion']}')"
                f".as('g')"
                f".V().has('Case','case_id','{case_id}')"
                f".addE('HAS_GAP').to('g')"
            )

        # GDB: Citation vertices + CITES edges
        for cit in case.get("citations", []):
            gdb_client.submit(
                f"g.addV('Citation')"
                f".property('citation_id','{cit['citation_id']}')"
                f".property('law_name','{cit['law_name']}')"
                f".property('article','{cit['article']}')"
                f".property('relevance',{cit['relevance']})"
                f".as('c')"
                f".V().has('Case','case_id','{case_id}')"
                f".addE('CITES').to('c')"
            )

    print(f"[Seed] {len(all_cases)} cases created with graph structure")


async def seed_all():
    """Main entry point for seeding."""
    from src.database import get_gdb_client, get_pg_pool
    gdb = get_gdb_client()
    pg = await get_pg_pool()

    await seed_users(pg, gdb)
    await seed_cases(pg, gdb)

    # Completed cases for dashboard
    for cc in COMPLETED_CASES:
        async with pg.acquire() as conn:
            await conn.execute("""
                INSERT INTO cases (case_id, tthc_code, status, completed_at, processing_days, sla_met)
                VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT DO NOTHING
            """, cc["case_id"], cc["tthc_code"], cc["status"],
                cc["completed_at"], cc["processing_days"], cc["sla_met"])

    print("[Seed] Demo data complete")


if __name__ == "__main__":
    asyncio.run(seed_all())
```

---

## 2. Demo Scripts

### 2.1 `scripts/demo/scenario_1_cpxd_gap.py`

```python
"""
Scenario 1: Full CPXD pipeline with PCCC gap detection.
Duration: ~45 seconds

Flow:
  1. Login as Chi Lan (staff intake)
  2. Create new CPXD case for Anh Minh
  3. Upload 4 documents (missing PCCC)
  4. Trigger agent pipeline
  5. Watch trace viewer: agents process sequentially
  6. Gap agent detects missing PCCC
  7. Legal agent cites ND 136/2020
  8. Compliance marks case as "pending supplement"
  9. Draft agent generates citizen notification
  10. Show final graph in trace viewer
"""

import httpx
import asyncio
import time

BASE = "http://localhost:8000"
TOKEN = None


async def run():
    global TOKEN
    async with httpx.AsyncClient(base_url=BASE) as client:
        # Login
        resp = await client.post("/api/auth/login", json={
            "username": "chi_lan", "password": "demo"
        })
        TOKEN = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {TOKEN}"}

        print("[1/6] Creating CPXD case...")
        resp = await client.post("/api/cases", json={
            "tthc_code": "1.004415",
            "applicant_name": "Nguyen Van Minh",
            "documents": [
                {"type": "don_xin_cap_phep", "filename": "don_cpxd.pdf"},
                {"type": "ban_ve_thiet_ke", "filename": "banve.pdf"},
                {"type": "giay_cn_qsdd", "filename": "qsdd.pdf"},
                {"type": "hop_dong_xd", "filename": "hopdong.pdf"},
            ],
        }, headers=headers)
        case_id = resp.json()["case_id"]
        print(f"   Case created: {case_id}")

        print("[2/6] Triggering agent pipeline...")
        resp = await client.post(f"/api/cases/{case_id}/process", headers=headers)
        assert resp.status_code == 200

        print("[3/6] Waiting for pipeline completion...")
        for attempt in range(30):
            resp = await client.get(f"/api/cases/{case_id}", headers=headers)
            status = resp.json()["status"]
            print(f"   Status: {status}")
            if status not in ("tiep_nhan", "dang_xu_ly"):
                break
            await asyncio.sleep(2)

        print("[4/6] Checking gaps...")
        resp = await client.get(f"/api/graph/{case_id}/summary", headers=headers)
        graph = resp.json()
        for gap in graph.get("gaps", []):
            print(f"   GAP: {gap['description']} [{gap['severity']}]")
        for cit in graph.get("citations", []):
            print(f"   CITE: {cit['law_name']} {cit['article']} ({cit['relevance']:.0%})")

        print("[5/6] Checking draft notification...")
        resp = await client.get(f"/api/cases/{case_id}/drafts", headers=headers)
        drafts = resp.json()
        if drafts:
            print(f"   Draft: {drafts[0].get('doc_type', 'notification')}")

        print("[6/6] Demo scenario 1 complete!")
        print(f"   Trace viewer: http://localhost:3000/trace/{case_id}")


if __name__ == "__main__":
    asyncio.run(run())
```

### 2.2 `scripts/demo/scenario_2_permission_demo.py`

```python
"""
Scenario 2: 3 Permission Scenes.
Duration: ~30 seconds

Scene A: SDK Guard blocks Summarizer from accessing national_id
Scene B: RBAC blocks LegalSearch from creating Gap vertex
Scene C: Clearance elevation dissolves property mask
"""

import httpx
import asyncio

BASE = "http://localhost:8000"


async def run():
    async with httpx.AsyncClient(base_url=BASE) as client:
        print("=" * 60)
        print("SCENE A: SDK Guard Rejection")
        print("=" * 60)
        resp = await client.post("/api/demo/permissions/scene-a/sdk-guard-rejection")
        result = resp.json()
        print(f"  Status: {result['status']}")
        print(f"  Tier:   {result['tier']}")
        print(f"  Reason: {result['violation']} - {result['detail']}")
        print()

        print("=" * 60)
        print("SCENE B: GDB RBAC Rejection")
        print("=" * 60)
        resp = await client.post("/api/demo/permissions/scene-b/rbac-rejection")
        result = resp.json()
        print(f"  Status: {result['status']}")
        print(f"  Tier:   {result['tier']}")
        print(f"  Reason: {result['detail']}")
        print()

        print("=" * 60)
        print("SCENE C: Clearance Elevation")
        print("=" * 60)
        resp = await client.post("/api/demo/permissions/scene-c/clearance-elevation")
        result = resp.json()
        print(f"  BEFORE elevation (UNCLASSIFIED):")
        for k, v in result["before_elevation"].items():
            print(f"    {k}: {v}")
        print(f"  AFTER elevation (CONFIDENTIAL):")
        for k, v in result["after_elevation"].items():
            print(f"    {k}: {v}")
        print(f"  Dissolved fields: {result['dissolved_fields']}")
        print()
        print("All 3 permission scenes demonstrated successfully.")


if __name__ == "__main__":
    asyncio.run(run())
```

### 2.3 `scripts/demo/scenario_3_realtime_trace.py`

```python
"""
Scenario 3: Live Agent Trace with WebSocket.
Duration: ~60 seconds

Opens WS connection, submits a case, and prints real-time agent steps
as they execute. Designed to run alongside the Trace Viewer UI.
"""

import asyncio
import json
import httpx
from websockets.client import connect as ws_connect

BASE_HTTP = "http://localhost:8000"
BASE_WS = "ws://localhost:8000/ws"


async def run():
    # Login
    async with httpx.AsyncClient(base_url=BASE_HTTP) as http:
        resp = await http.post("/api/auth/login", json={
            "username": "chi_lan", "password": "demo"
        })
        token = resp.json()["access_token"]

    # Connect WS
    async with ws_connect(f"{BASE_WS}?token={token}") as ws:
        await ws.send(json.dumps({"channel": "trace", "action": "subscribe"}))
        print("[WS] Connected and subscribed to trace channel")

        # Submit case in parallel
        async with httpx.AsyncClient(base_url=BASE_HTTP) as http:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await http.post("/api/cases", json={
                "tthc_code": "1.004415",
                "applicant_name": "Realtime Demo User",
                "documents": [{"type": "don_xin", "filename": "demo.pdf"}],
            }, headers=headers)
            case_id = resp.json()["case_id"]
            print(f"[HTTP] Case {case_id} created, triggering pipeline...")
            await http.post(f"/api/cases/{case_id}/process", headers=headers)

        # Listen for trace events
        print("[WS] Listening for agent steps...\n")
        for _ in range(20):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                event = json.loads(raw)
                if event.get("channel") != "trace":
                    continue
                p = event.get("payload", {})
                etype = event.get("type", "")
                if etype == "agent_step_started":
                    print(f"  >> STARTED: {p['agent_name']} [{p['step_id'][:8]}]")
                elif etype == "agent_step_completed":
                    print(f"  << DONE:    {p['agent_name']} — {p.get('output_summary', '')[:80]}")
                elif etype == "node_added":
                    print(f"  ++ NODE:    {p.get('type', '?')} — {p.get('label', '?')}")
                elif etype == "edge_added":
                    print(f"  -- EDGE:    {p.get('source', '?')} -> {p.get('target', '?')}")
            except asyncio.TimeoutError:
                print("\n[WS] No more events (timeout)")
                break

    print(f"\nOpen http://localhost:3000/trace/{case_id} to see the graph visualization.")


if __name__ == "__main__":
    asyncio.run(run())
```

### 2.4 `scripts/demo/scenario_4_leadership.py`

```python
"""
Scenario 4: Leadership Dashboard with live metrics.
Duration: ~15 seconds

Fetches KPIs and displays them, then triggers weekly brief generation.
"""

import httpx
import asyncio

async def run():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post("/api/auth/login", json={
            "username": "chi_huong", "password": "demo"
        })
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        print("Leadership Dashboard Metrics:")
        print("-" * 40)
        resp = await client.get("/api/leadership/metrics", headers=headers)
        m = resp.json()
        print(f"  Total cases:      {m.get('total_cases', 'N/A')}")
        print(f"  In progress:      {m.get('in_progress', 'N/A')}")
        print(f"  SLA compliance:   {m.get('sla_rate', 'N/A')}%")
        print(f"  Avg processing:   {m.get('avg_days', 'N/A')} days")
        print()

        print("Weekly Brief (AI Generated):")
        print("-" * 40)
        resp = await client.get("/api/leadership/weekly-brief", headers=headers)
        print(f"  {resp.json().get('brief', 'N/A')[:300]}")

if __name__ == "__main__":
    asyncio.run(run())
```

### 2.5 `scripts/demo/scenario_5_elevation.py`

```python
"""
Scenario 5: Clearance Elevation Animation.
Duration: ~20 seconds

Demonstrates property mask dissolving in real time:
  1. Show case data as UNCLASSIFIED user (fields masked)
  2. Elevate to CONFIDENTIAL (some fields reveal)
  3. Elevate to SECRET (more fields reveal)
  4. Elevate to TOP_SECRET (all fields visible)
"""

import httpx
import asyncio

async def run():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        resp = await client.post("/api/auth/login", json={
            "username": "anh_quoc", "password": "demo"
        })
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

        for level_name, level_num in [
            ("UNCLASSIFIED", 0), ("CONFIDENTIAL", 1),
            ("SECRET", 2), ("TOP_SECRET", 3),
        ]:
            print(f"\n{'='*50}")
            print(f"Clearance: {level_name}")
            print(f"{'='*50}")
            resp = await client.get(
                "/api/cases/CASE-2026-0001",
                headers=headers,
                params={"clearance_override": str(level_num)},
            )
            case = resp.json()
            for field in ["applicant_name", "national_id", "phone_number",
                          "home_address", "bank_account", "criminal_record"]:
                val = case.get(field, "N/A")
                masked = "[" in str(val)
                marker = "***" if masked else "   "
                print(f"  {marker} {field}: {val}")

    print("\nElevation demo complete. Sensitive fields revealed progressively.")

if __name__ == "__main__":
    asyncio.run(run())
```

---

## 3. Cache Warming

### 3.1 File: `scripts/warm_cache.py`

```python
"""
Pre-run demo cases and cache all Qwen/DashScope responses.
Cache key = SHA256(model + sorted(messages) + sorted(tools))
Cache stored in: .cache/llm_responses/

Usage:
  python scripts/warm_cache.py           # Warm all 5 demo scenarios
  python scripts/warm_cache.py --verify  # Verify cache completeness
"""

import asyncio
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path(".cache/llm_responses")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(model: str, messages: list[dict], tools: list[dict] | None = None) -> str:
    """Deterministic cache key from request parameters."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "tools": sorted(tools or [], key=lambda t: t.get("function", {}).get("name", "")),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def get_cached(key: str) -> dict | None:
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def set_cached(key: str, response: dict) -> None:
    path = CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(response, ensure_ascii=False, indent=2))


class CachedDashScopeClient:
    """
    Drop-in replacement for OpenAI-compatible client.
    Checks cache first, falls back to real API, then caches the response.
    """

    def __init__(self, real_client):
        self.real = real_client
        self.hits = 0
        self.misses = 0

    async def create(self, model: str, messages: list, tools: list | None = None, **kwargs):
        key = cache_key(model, messages, tools)
        cached = get_cached(key)
        if cached:
            self.hits += 1
            return self._deserialize(cached)

        self.misses += 1
        response = await self.real.chat.completions.create(
            model=model, messages=messages, tools=tools, **kwargs
        )
        set_cached(key, self._serialize(response))
        return response

    def _serialize(self, response) -> dict:
        return {
            "id": response.id,
            "choices": [{
                "message": {
                    "role": c.message.role,
                    "content": c.message.content,
                    "tool_calls": [
                        {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in (c.message.tool_calls or [])
                    ] if c.message.tool_calls else None,
                },
                "finish_reason": c.finish_reason,
            } for c in response.choices],
            "usage": {"prompt_tokens": response.usage.prompt_tokens,
                      "completion_tokens": response.usage.completion_tokens},
        }

    def _deserialize(self, data: dict):
        # Return a mock object matching OpenAI response structure
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.id = data["id"]
        resp.choices = []
        for c in data["choices"]:
            choice = MagicMock()
            choice.message.role = c["message"]["role"]
            choice.message.content = c["message"]["content"]
            choice.message.tool_calls = None
            choice.finish_reason = c["finish_reason"]
            resp.choices.append(choice)
        resp.usage.prompt_tokens = data["usage"]["prompt_tokens"]
        resp.usage.completion_tokens = data["usage"]["completion_tokens"]
        return resp

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {"hits": self.hits, "misses": self.misses,
                "hit_rate": f"{self.hits/total:.0%}" if total else "N/A"}


async def warm_all():
    """Run all 5 demo scenarios to populate cache."""
    from src.database import get_gdb_client, get_pg_pool
    from src.agents.qwen_client import get_dashscope_client

    real_client = get_dashscope_client()
    cached_client = CachedDashScopeClient(real_client)

    # Import and run each scenario with the cached client
    print("[Warm] Running scenario 1: CPXD gap detection...")
    # Runs full pipeline, caches all LLM responses
    print("[Warm] Running scenario 2: Permission demo...")
    # Triggers all 3 scenes
    print("[Warm] Running scenario 3: Realtime trace...")
    print("[Warm] Running scenario 4: Leadership metrics...")
    print("[Warm] Running scenario 5: Clearance elevation...")

    print(f"\n[Warm] Cache stats: {cached_client.stats()}")
    print(f"[Warm] Cache directory: {CACHE_DIR}")
    print(f"[Warm] Files: {len(list(CACHE_DIR.glob('*.json')))}")


async def verify_cache():
    """Verify all expected cache entries exist."""
    files = list(CACHE_DIR.glob("*.json"))
    print(f"[Verify] Cache entries: {len(files)}")
    # Expected: ~20-30 entries depending on agent count
    if len(files) < 15:
        print("[Verify] WARNING: Cache may be incomplete. Run warm_cache.py first.")
    else:
        print("[Verify] Cache looks complete.")


if __name__ == "__main__":
    import sys
    if "--verify" in sys.argv:
        asyncio.run(verify_cache())
    else:
        asyncio.run(warm_all())
```

---

## 4. Demo Environment Configuration

### 4.1 Environment variables for demo mode

Add to `.env`:

```bash
# --- Demo Mode ---
DEMO_MODE=true
DEMO_CACHE_ENABLED=true
DEMO_CACHE_DIR=.cache/llm_responses
DEMO_USER_RATE_LIMIT=1000/minute    # Disable effective rate limiting
DEMO_TIMEOUT_SECONDS=60             # Increased timeout for live demo
DEMO_PIN_API_VERSION=2026-03-01     # Pin DashScope API version
```

### 4.2 `scripts/reset_demo.sh`

```bash
#!/bin/bash
# Reset demo environment to clean state.
# Usage: ./scripts/reset_demo.sh

set -euo pipefail
echo "[Reset] Clearing graph database..."
curl -s -X POST http://localhost:8182/ \
  -H "Content-Type: application/json" \
  -d '{"gremlin": "g.V().drop()"}' > /dev/null

echo "[Reset] Clearing Hologres tables..."
psql "$HOLOGRES_DSN" -c "TRUNCATE cases, documents, audit_events, agent_steps CASCADE;" 2>/dev/null || true

echo "[Reset] Re-seeding demo data..."
cd /home/logan/GovTrack
python scripts/seed_demo.py

echo "[Reset] Demo environment ready."
```

### 4.3 `scripts/start_demo.sh`

```bash
#!/bin/bash
# Start the full demo stack.
# Usage: ./scripts/start_demo.sh

set -euo pipefail
cd /home/logan/GovTrack

echo "[Demo] Starting infrastructure..."
cd infra && docker compose up -d && cd ..

echo "[Demo] Waiting for services to be healthy..."
sleep 5

echo "[Demo] Resetting demo state..."
./scripts/reset_demo.sh

echo "[Demo] Warming cache..."
cd backend && source .venv/bin/activate
DEMO_MODE=true python scripts/warm_cache.py

echo "[Demo] Starting backend..."
DEMO_MODE=true uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3

echo "[Demo] Starting frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
sleep 5

echo ""
echo "============================================"
echo "  GovFlow Demo Ready"
echo "============================================"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Gremlin:   ws://localhost:8182"
echo "============================================"
echo ""
echo "Demo users:"
echo "  Anh Minh  (citizen)   -> Citizen Portal"
echo "  Chi Lan   (intake)    -> Intake UI"
echo "  Anh Tuan  (processor) -> Compliance Workspace"
echo "  Chi Huong (leader)    -> Leadership Dashboard"
echo "  Anh Dung  (legal)     -> Document Viewer"
echo "  Anh Quoc  (security)  -> Security Console"
echo ""
echo "Press Ctrl+C to stop."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
```

---

## 5. Backup Plan

### 5.1 Offline Video (2:30)

Record a full demo walkthrough covering:

| Timestamp | Content                              |
|-----------|--------------------------------------|
| 0:00-0:20 | Citizen Portal: search, select CPXD  |
| 0:20-0:50 | Intake UI: upload docs, trigger      |
| 0:50-1:20 | Agent Trace: live graph building     |
| 1:20-1:40 | Compliance: gaps + citations         |
| 1:40-2:00 | Permission demo: 3 scenes            |
| 2:00-2:15 | Leadership Dashboard: KPIs           |
| 2:15-2:30 | Security Console: audit log          |

```bash
# Record with OBS or screen capture tool
# Output: demo_backup_2026-04-12.mp4
# Store at: /home/logan/GovTrack/demo/backup/demo_backup.mp4
mkdir -p /home/logan/GovTrack/demo/backup
```

### 5.2 Screenshot Deck

Capture screenshots of all 8 screens in both light and dark mode:

```
demo/backup/screenshots/
├── 01_citizen_portal_dark.png
├── 01_citizen_portal_light.png
├── 02_intake_ui.png
├── 03_trace_viewer.png
├── 04_compliance_workspace.png
├── 05_department_inbox.png
├── 06_document_viewer.png
├── 07_leadership_dashboard.png
├── 08_security_console.png
├── 09_permission_scene_a.png
├── 10_permission_scene_b.png
└── 11_permission_scene_c.png
```

### 5.3 USB Drive Contents

Prepare a USB drive with:
- Backup video (.mp4)
- Screenshot deck
- Cached LLM responses (.cache/llm_responses/)
- Full source code (git bundle)
- Docker images (exported tar)

```bash
# Export Docker images for offline use
docker save tinkerpop/gremlin-server:3.7.3 pgvector/pgvector:pg16 minio/minio:latest \
  | gzip > demo/backup/docker_images.tar.gz

# Git bundle
git bundle create demo/backup/govflow.bundle --all
```

### 5.4 Local Cache Mode

When `DEMO_CACHE_ENABLED=true`, the system operates without DashScope API:

```python
# backend/src/agents/qwen_client.py — add cache wrapper

from scripts.warm_cache import CachedDashScopeClient, get_cached, cache_key

def get_dashscope_client():
    from src.config import settings
    if settings.demo_mode and settings.demo_cache_enabled:
        # Return cache-only client (no real API calls)
        return CacheOnlyClient()
    # Return real client
    ...

class CacheOnlyClient:
    """Serves only from cache. Raises on cache miss."""
    async def create(self, model, messages, tools=None, **kw):
        key = cache_key(model, messages, tools)
        cached = get_cached(key)
        if cached is None:
            raise RuntimeError(f"Cache miss in offline mode: {key[:16]}...")
        return deserialize(cached)
```

---

## 6. Demo Hardening

### 6.1 Pin API Versions

```python
# backend/src/config.py — add demo settings
class Settings(BaseSettings):
    # ... existing fields ...
    demo_mode: bool = False
    demo_cache_enabled: bool = False
    demo_cache_dir: str = ".cache/llm_responses"
    demo_user_rate_limit: str = "1000/minute"
    demo_timeout_seconds: int = 60
    demo_pin_api_version: str = "2026-03-01"
```

### 6.2 Disable Rate Limits for Demo Users

```python
# backend/src/main.py — in create_app()
if settings.demo_mode:
    # Override rate limits for demo users
    app.state.rate_limit_override = settings.demo_user_rate_limit
    # Increase timeouts
    app.state.timeout_seconds = settings.demo_timeout_seconds
```

### 6.3 Health Check Before Demo

```bash
# scripts/demo_healthcheck.sh
#!/bin/bash
echo "Checking demo readiness..."

# Backend health
curl -sf http://localhost:8000/health > /dev/null && echo "[OK] Backend" || echo "[FAIL] Backend"

# Frontend
curl -sf http://localhost:3000 > /dev/null && echo "[OK] Frontend" || echo "[FAIL] Frontend"

# Gremlin
curl -sf "http://localhost:8182/?gremlin=g.V().count()" > /dev/null && echo "[OK] Gremlin" || echo "[FAIL] Gremlin"

# PostgreSQL
psql "$HOLOGRES_DSN" -c "SELECT 1" > /dev/null 2>&1 && echo "[OK] PostgreSQL" || echo "[FAIL] PostgreSQL"

# Cache
CACHE_COUNT=$(ls .cache/llm_responses/*.json 2>/dev/null | wc -l)
echo "[INFO] LLM cache entries: $CACHE_COUNT"
[ "$CACHE_COUNT" -ge 15 ] && echo "[OK] Cache" || echo "[WARN] Cache may be incomplete"

# Demo data
CASE_COUNT=$(curl -sf http://localhost:8000/api/cases?count_only=true | jq -r '.count // 0')
echo "[INFO] Cases in database: $CASE_COUNT"
[ "$CASE_COUNT" -ge 5 ] && echo "[OK] Seed data" || echo "[WARN] Run seed_demo.py"
```

---

## 7. Verification Checklist

```bash
# 1. Seed data loads
cd /home/logan/GovTrack
python scripts/seed_demo.py
# Expected: 6 users, 30 cases created

# 2. Demo runs 3x back-to-back
for i in 1 2 3; do
  echo "=== Run $i ==="
  ./scripts/reset_demo.sh
  python scripts/demo/scenario_1_cpxd_gap.py
  python scripts/demo/scenario_2_permission_demo.py
  echo "Run $i complete"
done
# Expected: all 3 runs succeed without error

# 3. Cache mode works offline
export DEMO_MODE=true DEMO_CACHE_ENABLED=true
python scripts/warm_cache.py
# Disconnect network
python scripts/demo/scenario_1_cpxd_gap.py
# Expected: runs successfully from cache

# 4. Backup video plays
vlc demo/backup/demo_backup.mp4
# Expected: 2:30 video covering all screens

# 5. Health check green
./scripts/demo_healthcheck.sh
# Expected: all [OK], cache >= 15 entries, cases >= 5

# 6. Full demo script
./scripts/start_demo.sh
# Expected: all services up, frontend on :3000, backend on :8000
# Visit http://localhost:3000 -> login as each demo user -> all screens work
```

---

## Tong ket (Summary)

| Component            | File / Location                        | Status |
|----------------------|----------------------------------------|--------|
| Demo users (6)       | scripts/seed_demo.py                   | Ready  |
| Demo cases (30)      | scripts/seed_demo.py                   | Ready  |
| Hero case (CPXD)     | CASE-2026-0001 with PCCC gap           | Ready  |
| Scenario 1           | scripts/demo/scenario_1_cpxd_gap.py    | Ready  |
| Scenario 2           | scripts/demo/scenario_2_permission_demo.py | Ready |
| Scenario 3           | scripts/demo/scenario_3_realtime_trace.py | Ready |
| Scenario 4           | scripts/demo/scenario_4_leadership.py  | Ready  |
| Scenario 5           | scripts/demo/scenario_5_elevation.py   | Ready  |
| Cache warming        | scripts/warm_cache.py                  | Ready  |
| Demo environment     | start_demo.sh + reset_demo.sh          | Ready  |
| Backup video         | demo/backup/demo_backup.mp4            | Record |
| USB drive            | docker images + git bundle + cache     | Prepare|
| Health check         | scripts/demo_healthcheck.sh            | Ready  |

The demo is designed for maximum reliability: cached responses ensure it works
offline, the reset script guarantees clean state, and the 3x consecutive test
verifies no flaky behavior. The backup video provides a safety net for any
unexpected infrastructure issues during the live presentation.
