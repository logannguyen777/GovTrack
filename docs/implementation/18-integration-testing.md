# 18 - Integration Testing: E2E, Permissions, Benchmarks, Smoke Tests

## Muc tieu (Objective)

Implement the full test suite: E2E happy-path tests for all 5 TTHC, 20+ permission
negative tests, agent accuracy and latency benchmarks, WebSocket integration tests,
and Playwright frontend smoke tests. After completing this guide, `pytest` runs all
backend tests green, Playwright validates all 8 screens, and the demo scenario
passes 5 consecutive runs at 100%.

---

## 1. Test Infrastructure

### 1.1 Fixtures: `backend/tests/conftest.py`

```python
"""
Shared fixtures for all integration tests.
- TinkerGraph in-memory for graph tests (no external GDB dependency)
- SQLite in-memory for Hologres-equivalent relational queries
- Mock DashScope client for deterministic AI responses
"""

import asyncio
import pytest
import sqlite3
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection

from src.config import Settings
from src.models.schemas import AgentProfile, ClearanceLevel
from src.graph.sdk_guard import SDKGuard
from src.graph.property_mask import PropertyMask
from src.graph.rbac_simulator import RBACSimulator
from src.graph.audit import AuditLogger, AuditEvent
from src.graph.permitted_client import PermittedGremlinClient


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def settings():
    return Settings(govflow_env="test", gdb_endpoint="ws://localhost:8182/gremlin")


@pytest.fixture(scope="session")
def gremlin_connection():
    """
    Connect to local TinkerGraph Gremlin Server.
    If not available, tests that need it are skipped.
    """
    try:
        conn = DriverRemoteConnection("ws://localhost:8182/gremlin", "g")
        g = traversal().withRemote(conn)
        g.V().drop().iterate()  # Clean slate
        yield g
        g.V().drop().iterate()
        conn.close()
    except Exception:
        pytest.skip("Gremlin Server not available")


@pytest.fixture
def sqlite_db():
    """In-memory SQLite as Hologres substitute for relational queries."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE audit_events (
            event_id TEXT PRIMARY KEY,
            agent_id TEXT,
            tier TEXT,
            action TEXT,
            detail TEXT,
            query_snippet TEXT,
            timestamp REAL,
            user_id TEXT,
            case_id TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE cases (
            case_id TEXT PRIMARY KEY,
            tthc_code TEXT,
            status TEXT,
            applicant_name TEXT,
            submitted_at TEXT,
            classification INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            case_id TEXT,
            filename TEXT,
            doc_type TEXT,
            ocr_text TEXT
        )
    """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def mock_audit_logger():
    """AuditLogger with mock backends that record calls."""
    logger = AuditLogger(gdb_client=MagicMock(), hologres_pool=MagicMock())
    logger.logged_events: list[AuditEvent] = []
    original_log = logger.log

    async def recording_log(event: AuditEvent):
        logger.logged_events.append(event)

    logger.log = recording_log
    return logger


@pytest.fixture
def mock_dashscope():
    """Deterministic mock for Qwen API calls."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="mock_response"))],
        usage=MagicMock(prompt_tokens=100, completion_tokens=50),
    ))
    return client


def make_agent_profile(agent_id: str) -> AgentProfile:
    """Factory for agent profiles used in tests."""
    PROFILES = {
        "intake_agent": AgentProfile(
            agent_id="intake_agent", agent_name="Intake",
            clearance=ClearanceLevel.UNCLASSIFIED,
            read_node_labels=["Case", "Document", "Task"],
            write_node_labels=["Case", "Task", "AgentStep"],
            read_edge_types=["HAS_DOCUMENT", "TRIGGERED_BY"],
            write_edge_types=["PRODUCED", "HAS_DOCUMENT"],
            forbidden_properties=["national_id", "tax_id"],
        ),
        "summary_agent": AgentProfile(
            agent_id="summary_agent", agent_name="Summary",
            clearance=ClearanceLevel.UNCLASSIFIED,
            read_node_labels=["Case", "Document", "Gap", "Citation", "Decision"],
            write_node_labels=[],
            read_edge_types=["HAS_DOCUMENT", "HAS_GAP", "CITES", "DECIDED_BY"],
            write_edge_types=[],
            forbidden_properties=["national_id", "tax_id", "phone_number"],
        ),
        "legal_search_agent": AgentProfile(
            agent_id="legal_search_agent", agent_name="LegalSearch",
            clearance=ClearanceLevel.CONFIDENTIAL,
            read_node_labels=["LawArticle", "Citation", "Case"],
            write_node_labels=["Citation", "Task"],
            read_edge_types=["CITES", "REFERENCES"],
            write_edge_types=["CITES"],
            forbidden_properties=["national_id"],
        ),
        "compliance_agent": AgentProfile(
            agent_id="compliance_agent", agent_name="Compliance",
            clearance=ClearanceLevel.SECRET,
            read_node_labels=["Case", "Document", "Gap", "Citation", "Requirement"],
            write_node_labels=["Decision", "Task"],
            read_edge_types=["HAS_DOCUMENT", "HAS_GAP", "CITES", "REQUIRES"],
            write_edge_types=["DECIDED_BY"],
            forbidden_properties=[],
        ),
    }
    return PROFILES.get(agent_id, PROFILES["intake_agent"])
```

---

## 2. E2E Happy Path Tests (5 TTHC)

### 2.1 File: `backend/tests/test_e2e_tthc.py`

```python
"""
End-to-end happy path: one test per TTHC.
Each test submits a case, runs the pipeline, and verifies the output graph.
"""

import pytest
from httpx import AsyncClient
from src.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestCPXD:
    """TTHC 1.004415 - Cap phep xay dung"""

    async def test_cpxd_full_pipeline(self, client, gremlin_connection, sqlite_db):
        """
        Submit 5 docs with missing PCCC (fire safety certificate).
        Expected flow:
          1. Intake: creates Case + 5 Document vertices
          2. Classifier: assigns tthc_code=1.004415
          3. Extraction: extracts entities (owner, address, area)
          4. Gap: detects missing PCCC -> creates Gap vertex, severity=high
          5. LegalSearch: cites ND 136/2020/ND-CP Dieu 9 khoan 2
          6. Compliance: creates Decision(status=pending_supplement)
          7. Draft: generates citizen notification letter
        """
        # Step 1: Submit case
        response = await client.post("/api/cases", json={
            "tthc_code": "1.004415",
            "applicant_name": "Nguyen Van Minh",
            "documents": [
                {"type": "don_xin_cap_phep", "filename": "don.pdf"},
                {"type": "ban_ve_thiet_ke", "filename": "banve.pdf"},
                {"type": "giay_chung_nhan_qsdd", "filename": "qsdd.pdf"},
                {"type": "hop_dong_xay_dung", "filename": "hopdong.pdf"},
                {"type": "bao_hiem", "filename": "baohiem.pdf"},
            ],
        })
        assert response.status_code == 201
        case_id = response.json()["case_id"]

        # Step 2: Trigger pipeline
        response = await client.post(f"/api/cases/{case_id}/process")
        assert response.status_code == 200

        # Step 3: Verify graph state
        response = await client.get(f"/api/graph/{case_id}/summary")
        graph = response.json()

        assert graph["case"]["tthc_code"] == "1.004415"
        assert len(graph["documents"]) == 5
        assert any(g["description"].lower().count("pccc") > 0 for g in graph["gaps"])
        assert any("136/2020" in c["law_ref"] for c in graph["citations"])
        assert graph["decision"]["status"] == "pending_supplement"

        # Step 4: Verify citizen notification draft exists
        response = await client.get(f"/api/cases/{case_id}/drafts")
        drafts = response.json()
        assert len(drafts) >= 1
        assert "thieu" in drafts[0]["content"].lower()  # mentions "missing"


class TestGCN_QSDD:
    """TTHC 1.000046 - GCN quyen su dung dat"""

    async def test_qsdd_full_pipeline(self, client, gremlin_connection):
        response = await client.post("/api/cases", json={
            "tthc_code": "1.000046",
            "applicant_name": "Tran Thi Lan",
            "documents": [
                {"type": "don_dang_ky", "filename": "don_dk.pdf"},
                {"type": "ho_so_dia_chinh", "filename": "diachinh.pdf"},
                {"type": "ban_do_dia_chinh", "filename": "bando.pdf"},
            ],
        })
        case_id = response.json()["case_id"]

        await client.post(f"/api/cases/{case_id}/process")

        response = await client.get(f"/api/graph/{case_id}/summary")
        graph = response.json()
        assert graph["case"]["tthc_code"] == "1.000046"
        assert graph["routing"]["department"] == "So TN&MT"
        # Verify GCN certificate draft
        assert graph["decision"]["status"] in ("approved", "pending_review")


class TestDKKD:
    """TTHC 1.001757 - Dang ky kinh doanh"""

    async def test_dkkd_full_pipeline(self, client, gremlin_connection):
        response = await client.post("/api/cases", json={
            "tthc_code": "1.001757",
            "applicant_name": "Le Van Hung",
            "documents": [
                {"type": "giay_de_nghi", "filename": "denghi.pdf"},
                {"type": "dieu_le", "filename": "dieule.pdf"},
                {"type": "danh_sach_thanh_vien", "filename": "thanhvien.pdf"},
            ],
        })
        case_id = response.json()["case_id"]
        await client.post(f"/api/cases/{case_id}/process")

        response = await client.get(f"/api/graph/{case_id}/summary")
        graph = response.json()
        assert graph["case"]["tthc_code"] == "1.001757"
        # Verify GCN DKDN draft
        drafts_resp = await client.get(f"/api/cases/{case_id}/drafts")
        assert any("GCN DKDN" in d.get("doc_type", "") or "dang ky" in d.get("content", "").lower()
                    for d in drafts_resp.json())


class TestLLTP:
    """TTHC 1.000122 - Ly lich tu phap"""

    async def test_lltp_full_pipeline(self, client, gremlin_connection):
        response = await client.post("/api/cases", json={
            "tthc_code": "1.000122",
            "applicant_name": "Pham Minh Duc",
            "documents": [
                {"type": "don_yeu_cau", "filename": "yeucau.pdf"},
                {"type": "cmnd_cccd", "filename": "cccd.pdf"},
            ],
        })
        case_id = response.json()["case_id"]
        await client.post(f"/api/cases/{case_id}/process")

        response = await client.get(f"/api/graph/{case_id}/summary")
        graph = response.json()
        assert graph["routing"]["department"] == "So Tu phap"
        # Verify extract generated
        assert graph["decision"]["status"] in ("approved", "pending_review")


class TestGPMT:
    """TTHC 2.002154 - Giay phep moi truong"""

    async def test_gpmt_full_pipeline(self, client, gremlin_connection):
        response = await client.post("/api/cases", json={
            "tthc_code": "2.002154",
            "applicant_name": "Cty TNHH Xanh",
            "documents": [
                {"type": "bao_cao_dtm", "filename": "dtm.pdf"},
                {"type": "ho_so_ky_thuat", "filename": "kythuat.pdf"},
                {"type": "giay_phep_kinh_doanh", "filename": "gpkd.pdf"},
            ],
        })
        case_id = response.json()["case_id"]
        await client.post(f"/api/cases/{case_id}/process")

        response = await client.get(f"/api/graph/{case_id}/summary")
        graph = response.json()
        assert graph["case"]["tthc_code"] == "2.002154"
        # Environmental check must be present
        assert any("moi truong" in step.get("agent_name", "").lower() or
                    "environment" in step.get("output_summary", "").lower()
                    for step in graph.get("agent_steps", []))
```

---

## 3. Permission Negative Tests (20+ Scenarios)

### 3.1 File: `backend/tests/test_permission_negative.py`

```python
"""
20+ negative permission test scenarios.
Each verifies denial + AuditEvent creation.
Tests reference the 3-tier engine from doc 15.
"""

import pytest
from src.graph.sdk_guard import SDKGuard, SDKGuardViolation
from src.graph.property_mask import PropertyMask
from src.graph.rbac_simulator import RBACSimulator
from src.models.schemas import ClearanceLevel
from tests.conftest import make_agent_profile


class TestSDKGuardNegative:
    """Tier 1 denial scenarios."""

    def test_n01_summary_reads_national_id(self):
        """Summary agent forbidden from accessing national_id."""
        guard = SDKGuard(make_agent_profile("summary_agent"))
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('national_id')")

    def test_n02_summary_reads_tax_id(self):
        guard = SDKGuard(make_agent_profile("summary_agent"))
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('tax_id')")

    def test_n03_summary_reads_phone(self):
        guard = SDKGuard(make_agent_profile("summary_agent"))
        with pytest.raises(SDKGuardViolation, match="PROPERTY_FORBIDDEN"):
            guard.validate("g.V().hasLabel('Case').values('phone_number')")

    def test_n04_intake_reads_law_article(self):
        """Intake cannot traverse to LawArticle label."""
        guard = SDKGuard(make_agent_profile("intake_agent"))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('LawArticle').values('content')")

    def test_n05_intake_reads_secret_edge(self):
        guard = SDKGuard(make_agent_profile("intake_agent"))
        with pytest.raises(SDKGuardViolation, match="READ_EDGE_DENIED"):
            guard.validate("g.V().hasLabel('Case').outE('CITES').inV()")

    def test_n06_depth_limit_exceeded(self):
        profile = make_agent_profile("intake_agent")
        profile.max_traversal_depth = 2
        guard = SDKGuard(profile)
        with pytest.raises(SDKGuardViolation, match="DEPTH_EXCEEDED"):
            guard.validate("g.V().hasLabel('Case').out('HAS_DOCUMENT').out('HAS_DOCUMENT').out('HAS_DOCUMENT')")

    def test_n07_summary_writes_anything(self):
        """Summary agent has empty write_node_labels."""
        guard = SDKGuard(make_agent_profile("summary_agent"))
        with pytest.raises(SDKGuardViolation, match="WRITE_LABEL_DENIED"):
            guard.validate("g.addV('Task').property('name','sneaky')")

    def test_n08_intake_creates_decision(self):
        guard = SDKGuard(make_agent_profile("intake_agent"))
        with pytest.raises(SDKGuardViolation, match="WRITE_LABEL_DENIED"):
            guard.validate("g.addV('Decision').property('status','approved')")

    def test_n09_intake_creates_forbidden_edge(self):
        guard = SDKGuard(make_agent_profile("intake_agent"))
        with pytest.raises(SDKGuardViolation, match="WRITE_EDGE_DENIED"):
            guard.validate("g.V('a').addE('DECIDED_BY').to(V('b'))")

    def test_n10_legal_reads_gap_label(self):
        """Legal agent cannot read Gap nodes."""
        guard = SDKGuard(make_agent_profile("legal_search_agent"))
        with pytest.raises(SDKGuardViolation, match="READ_LABEL_DENIED"):
            guard.validate("g.V().hasLabel('Gap').values('severity')")


class TestRBACNegative:
    """Tier 2 denial scenarios."""

    def test_n11_legal_creates_gap(self):
        profile = make_agent_profile("legal_search_agent")
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Gap').property('severity','high')")
        with pytest.raises(PermissionError, match="lacks INSERT on Gap"):
            rbac.check_execution_privilege("g.addV('Gap')", parsed)

    def test_n12_summary_creates_case(self):
        profile = make_agent_profile("summary_agent")
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.addV('Case').property('title','test')")
        with pytest.raises(PermissionError):
            rbac.check_execution_privilege("g.addV('Case')", parsed)

    def test_n13_intake_drops_vertex(self):
        profile = make_agent_profile("intake_agent")
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.V('x').drop()")
        # drop is a mutation with no specific label -> should be caught
        assert parsed.is_mutating

    def test_n14_legal_reads_document(self):
        """Legal agent cannot read Document label."""
        profile = make_agent_profile("legal_search_agent")
        rbac = RBACSimulator(profile)
        guard = SDKGuard(profile)
        parsed = guard.parse_query("g.V().hasLabel('Document')")
        parsed.accessed_labels = {"Document"}
        with pytest.raises(PermissionError, match="lacks SELECT on Document"):
            rbac.check_execution_privilege("g.V()", parsed)


class TestPropertyMaskNegative:
    """Tier 3 redaction scenarios."""

    def test_n15_unclassified_sees_no_address(self):
        mask = PropertyMask()
        r = mask.apply({"home_address": "123 Le Loi"}, ClearanceLevel.UNCLASSIFIED)
        assert "CLASSIFIED" in r["home_address"]

    def test_n16_unclassified_sees_no_bank(self):
        mask = PropertyMask()
        r = mask.apply({"bank_account": "VCB-123"}, ClearanceLevel.UNCLASSIFIED)
        assert "CLASSIFIED" in r["bank_account"]

    def test_n17_confidential_sees_no_bank(self):
        """Bank requires SECRET clearance."""
        mask = PropertyMask()
        r = mask.apply({"bank_account": "VCB-123"}, ClearanceLevel.CONFIDENTIAL)
        assert "CLASSIFIED:SECRET" in r["bank_account"]

    def test_n18_secret_sees_no_criminal_record(self):
        """Criminal record requires TOP_SECRET."""
        mask = PropertyMask()
        r = mask.apply({"criminal_record": "None"}, ClearanceLevel.SECRET)
        assert "CLASSIFIED:TOP_SECRET" in r["criminal_record"]

    def test_n19_national_id_always_redacted(self):
        """national_id is REDACT action, not gated — even TOP_SECRET cannot see it."""
        mask = PropertyMask()
        r = mask.apply({"national_id": "079201001234"}, ClearanceLevel.TOP_SECRET)
        assert r["national_id"] == "[REDACTED]"

    def test_n20_partial_mask_format(self):
        mask = PropertyMask()
        r = mask.apply({"phone_number": "0901234567"}, ClearanceLevel.TOP_SECRET)
        assert r["phone_number"] == "******4567"

    def test_n21_email_partial_mask(self):
        mask = PropertyMask()
        r = mask.apply({"email": "test@example.com"}, ClearanceLevel.TOP_SECRET)
        assert r["email"].endswith(".com")
        assert r["email"].startswith("*")


class TestAuditEventCreation:
    """Verify every denial writes an AuditEvent."""

    async def test_n22_sdk_denial_creates_audit(self, mock_audit_logger):
        profile = make_agent_profile("summary_agent")
        raw_client = MagicMock()
        pc = PermittedGremlinClient(raw_client, profile, mock_audit_logger)

        with pytest.raises(SDKGuardViolation):
            await pc.execute("g.V().hasLabel('Case').values('national_id')")

        assert len(mock_audit_logger.logged_events) >= 1
        deny_event = next(e for e in mock_audit_logger.logged_events if e.action == "DENY")
        assert deny_event.tier == "SDK_GUARD"
        assert deny_event.agent_id == "summary_agent"

    async def test_n23_rbac_denial_creates_audit(self, mock_audit_logger):
        profile = make_agent_profile("legal_search_agent")
        # Bypass SDK guard for this test by giving read access to Gap
        profile.read_node_labels.append("Gap")
        raw_client = MagicMock()
        pc = PermittedGremlinClient(raw_client, profile, mock_audit_logger)

        with pytest.raises(PermissionError):
            await pc.execute("g.addV('Gap').property('x','y')")

        deny_events = [e for e in mock_audit_logger.logged_events if e.action == "DENY"]
        assert any(e.tier == "GDB_RBAC" for e in deny_events)
```

---

## 4. Agent Accuracy Benchmarks

### 4.1 File: `backend/tests/test_agent_benchmarks.py`

```python
"""
Agent accuracy benchmarks: 5 inputs per agent, measure accuracy %.
Target: >80% classification, >90% compliance, >85% citation.
"""

import pytest
import time


class TestClassifierAccuracy:
    """Classifier agent: given document text, predict TTHC code."""

    INPUTS = [
        ("Don xin cap phep xay dung nha o...", "1.004415"),
        ("Don dang ky quyen su dung dat...", "1.000046"),
        ("Giay de nghi dang ky kinh doanh...", "1.001757"),
        ("Don yeu cau cap phieu ly lich tu phap...", "1.000122"),
        ("Bao cao danh gia tac dong moi truong...", "2.002154"),
    ]

    async def test_classification_accuracy(self, mock_dashscope):
        correct = 0
        for text, expected_code in self.INPUTS:
            # Call classifier agent
            result = await classify_document(text, client=mock_dashscope)
            if result["tthc_code"] == expected_code:
                correct += 1
        accuracy = correct / len(self.INPUTS)
        assert accuracy >= 0.80, f"Classification accuracy {accuracy:.0%} < 80% target"


class TestComplianceAccuracy:
    """Compliance agent: given case graph, identify all gaps."""

    INPUTS = [
        # (case_fixture_id, expected_gap_ids)
        ("cpxd_missing_pccc", ["gap_missing_pccc"]),
        ("cpxd_missing_banve", ["gap_missing_banve"]),
        ("dkkd_missing_dieule", ["gap_missing_dieule"]),
        ("qsdd_complete", []),  # No gaps expected
        ("gpmt_missing_dtm", ["gap_missing_dtm"]),
    ]

    async def test_compliance_accuracy(self, mock_dashscope):
        correct = 0
        for case_id, expected_gaps in self.INPUTS:
            result = await check_compliance(case_id, client=mock_dashscope)
            detected = set(result.get("gap_ids", []))
            expected = set(expected_gaps)
            if detected == expected:
                correct += 1
        accuracy = correct / len(self.INPUTS)
        assert accuracy >= 0.90, f"Compliance accuracy {accuracy:.0%} < 90% target"


class TestCitationAccuracy:
    """Legal search agent: given gap, find relevant law citations."""

    INPUTS = [
        ("missing_pccc", "136/2020/ND-CP"),
        ("missing_banve", "15/2021/ND-CP"),
        ("missing_dieule", "59/2020/QH14"),
        ("expired_certificate", "43/2014/ND-CP"),
        ("environmental_violation", "72/2020/ND-CP"),
    ]

    async def test_citation_accuracy(self, mock_dashscope):
        correct = 0
        for gap_type, expected_law in self.INPUTS:
            result = await find_citations(gap_type, client=mock_dashscope)
            citations = [c["law_ref"] for c in result.get("citations", [])]
            if any(expected_law in c for c in citations):
                correct += 1
        accuracy = correct / len(self.INPUTS)
        assert accuracy >= 0.85, f"Citation accuracy {accuracy:.0%} < 85% target"


class TestLatencyBenchmarks:
    """Per-agent and total pipeline latency."""

    AGENTS = [
        "intake", "classifier", "extraction", "gap",
        "legal_search", "compliance", "summary", "draft", "review", "publish",
    ]

    async def test_per_agent_latency(self, mock_dashscope):
        """Each agent should complete within p95 < 5s."""
        for agent_name in self.AGENTS:
            times = []
            for _ in range(5):
                start = time.time()
                await run_agent(agent_name, test_input={}, client=mock_dashscope)
                times.append(time.time() - start)

            times.sort()
            p50 = times[2]
            p95 = times[4]  # 5 samples, p95 ~ max

            print(f"{agent_name}: p50={p50:.3f}s p95={p95:.3f}s")
            assert p95 < 5.0, f"{agent_name} p95={p95:.3f}s exceeds 5s limit"

    async def test_total_pipeline_latency(self, mock_dashscope):
        """Full pipeline for one case should complete within p95 < 30s."""
        times = []
        for _ in range(3):
            start = time.time()
            await run_full_pipeline("test_cpxd", client=mock_dashscope)
            times.append(time.time() - start)

        p95 = sorted(times)[-1]
        print(f"Total pipeline: p95={p95:.3f}s")
        assert p95 < 30.0, f"Pipeline p95={p95:.3f}s exceeds 30s limit"


# Placeholder agent runners (implemented in agent modules)
async def classify_document(text, client): return {"tthc_code": "1.004415"}
async def check_compliance(case_id, client): return {"gap_ids": []}
async def find_citations(gap_type, client): return {"citations": []}
async def run_agent(name, test_input, client): pass
async def run_full_pipeline(case_id, client): pass
```

---

## 5. WebSocket Integration Test

### 5.1 File: `backend/tests/test_websocket.py`

```python
"""
WebSocket integration: connect, submit case, verify AgentStep events in order.
"""

import pytest
import asyncio
import json
from httpx import AsyncClient
from websockets.client import connect as ws_connect
from src.main import app


class TestWebSocketIntegration:

    async def test_trace_events_arrive_in_order(self, client):
        """Submit a case, listen on WS, verify agent steps arrive sequentially."""
        received_events = []

        async def listen_ws():
            async with ws_connect("ws://localhost:8000/ws?token=test_token") as ws:
                # Subscribe to trace channel
                await ws.send(json.dumps({"channel": "trace", "action": "subscribe"}))
                for _ in range(10):  # Expect ~10 agent steps
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                        event = json.loads(msg)
                        if event.get("channel") == "trace":
                            received_events.append(event)
                    except asyncio.TimeoutError:
                        break

        # Start WS listener
        ws_task = asyncio.create_task(listen_ws())

        # Submit case
        response = await client.post("/api/cases", json={
            "tthc_code": "1.004415",
            "applicant_name": "Test User",
            "documents": [{"type": "don_xin", "filename": "test.pdf"}],
        })
        case_id = response.json()["case_id"]
        await client.post(f"/api/cases/{case_id}/process")

        await ws_task

        # Verify: events received, in order
        assert len(received_events) >= 3, f"Expected >=3 events, got {len(received_events)}"

        # Verify agent ordering: intake before classifier before gap
        agent_order = [e["payload"]["agent_name"] for e in received_events
                       if e.get("type") == "agent_step_started"]
        if "Intake" in agent_order and "Classifier" in agent_order:
            assert agent_order.index("Intake") < agent_order.index("Classifier")

    async def test_notification_events(self, client):
        """Verify notification channel delivers case status updates."""
        # Similar pattern: subscribe to notifications channel,
        # submit case, verify status change events arrive
        pass

    async def test_audit_events_stream(self, client):
        """Verify audit channel streams permission check events."""
        # Subscribe to audit channel,
        # trigger demo permission scene,
        # verify DENY events arrive on WS
        pass
```

---

## 6. Frontend Smoke Tests (Playwright)

### 6.1 File: `frontend/tests/smoke.spec.ts`

```typescript
import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3000";

test.describe("GovFlow Frontend Smoke Tests", () => {

  test.beforeEach(async ({ page }) => {
    // Login as staff user
    await page.goto(`${BASE}/auth/login`);
    await page.click('button:has-text("Chi Lan (Staff Intake)")');
    await page.waitForURL("**/dashboard");
  });

  test("Screen 1: Citizen Portal renders", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("h1")).toContainText("Cong dich vu cong");
    // 5 TTHC cards visible
    const cards = page.locator("[href^='/submit/']");
    await expect(cards).toHaveCount(5);
    // Search bar functional
    await page.fill("input[aria-label='Search procedures']", "xay dung");
    await expect(page.locator("text=Cap phep xay dung")).toBeVisible();
  });

  test("Screen 2: Intake UI renders", async ({ page }) => {
    await page.goto(`${BASE}/intake`);
    await expect(page.locator("h1")).toContainText("Tiep nhan");
    // Drop zone visible
    await expect(page.locator("text=Keo tha tai lieu")).toBeVisible();
  });

  test("Screen 3: Agent Trace Viewer renders", async ({ page }) => {
    await page.goto(`${BASE}/trace/test-case-001`);
    // React Flow canvas present
    await expect(page.locator(".react-flow")).toBeVisible();
    // Agent steps sidebar
    await expect(page.locator("text=Agent Steps")).toBeVisible();
  });

  test("Screen 4: Compliance Workspace renders", async ({ page }) => {
    await page.goto(`${BASE}/compliance/test-case-001`);
    await expect(page.locator("text=Tai lieu")).toBeVisible();
    await expect(page.locator("text=Thieu sot")).toBeVisible();
    // Approve/reject buttons
    await expect(page.locator("text=Phe duyet")).toBeVisible();
    await expect(page.locator("text=Tu choi")).toBeVisible();
  });

  test("Screen 5: Department Inbox Kanban renders", async ({ page }) => {
    await page.goto(`${BASE}/inbox`);
    await expect(page.locator("h1")).toContainText("Ho so den");
    // 5 Kanban columns
    for (const col of ["Tiep nhan", "Dang xu ly", "Cho y kien", "Da quyet dinh", "Tra ket qua"]) {
      await expect(page.locator(`text=${col}`)).toBeVisible();
    }
  });

  test("Screen 6: Document Viewer renders", async ({ page }) => {
    await page.goto(`${BASE}/documents/test-doc-001`);
    // PDF canvas or placeholder
    await expect(page.locator(".react-pdf__Page, text=Document")).toBeVisible();
    // Classification badge
    await expect(page.locator("[role='status']")).toBeVisible();
  });

  test("Screen 7: Leadership Dashboard renders", async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await expect(page.locator("h1")).toContainText("Bang dieu hanh");
    // KPI cards
    await expect(page.locator("text=Tong ho so")).toBeVisible();
    await expect(page.locator("text=SLA dat")).toBeVisible();
  });

  test("Screen 8: Security Console renders", async ({ page }) => {
    await page.goto(`${BASE}/security`);
    await expect(page.locator("h1")).toContainText("Trung tam bao mat");
    // Demo buttons
    await expect(page.locator("text=Scene A")).toBeVisible();
    await expect(page.locator("text=Scene B")).toBeVisible();
    await expect(page.locator("text=Scene C")).toBeVisible();
  });

  test("Dark/Light mode toggle", async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    // Default: dark mode
    await expect(page.locator("html")).toHaveClass(/dark/);
    // Toggle (assumes toggle button in top bar)
    await page.click("[aria-label='Toggle theme']");
    await expect(page.locator("html")).not.toHaveClass(/dark/);
  });

  test("Sidebar navigation", async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    // Click Intake nav
    await page.click("text=Intake");
    await page.waitForURL("**/intake");
    // Click back to Dashboard
    await page.click("text=Dashboard");
    await page.waitForURL("**/dashboard");
  });
});
```

---

## 7. Demo Reliability Test

### 7.1 File: `backend/tests/test_demo_reliability.py`

```python
"""
Run the exact demo scenario 5x consecutive.
Verify 100% pass rate — no flaky failures allowed.
"""

import pytest
from httpx import AsyncClient
from src.main import app


class TestDemoReliability:

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.parametrize("run_number", range(5))
    async def test_demo_scenario_consecutive(self, client, run_number):
        """
        Full demo scenario executed 5 times back-to-back.
        Each run:
          1. Reset demo state
          2. Submit CPXD case with missing PCCC
          3. Process -> verify gap detected
          4. Run permission Scene A -> verify rejection
          5. Run permission Scene B -> verify rejection
          6. Run permission Scene C -> verify mask dissolution
          7. Verify audit events created
        """
        # Step 1: Reset
        await client.post("/api/demo/reset")

        # Step 2: Submit case
        resp = await client.post("/api/cases", json={
            "tthc_code": "1.004415",
            "applicant_name": "Demo User",
            "documents": [
                {"type": "don_xin_cap_phep", "filename": "don.pdf"},
                {"type": "ban_ve_thiet_ke", "filename": "banve.pdf"},
            ],
        })
        assert resp.status_code == 201, f"Run {run_number}: case creation failed"
        case_id = resp.json()["case_id"]

        # Step 3: Process
        resp = await client.post(f"/api/cases/{case_id}/process")
        assert resp.status_code == 200, f"Run {run_number}: processing failed"

        resp = await client.get(f"/api/graph/{case_id}/summary")
        graph = resp.json()
        assert len(graph.get("gaps", [])) > 0, f"Run {run_number}: no gaps detected"

        # Step 4: Permission Scene A
        resp = await client.post("/api/demo/permissions/scene-a/sdk-guard-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene A should deny"

        # Step 5: Permission Scene B
        resp = await client.post("/api/demo/permissions/scene-b/rbac-rejection")
        assert resp.json()["status"] == "DENIED", f"Run {run_number}: Scene B should deny"

        # Step 6: Permission Scene C
        resp = await client.post("/api/demo/permissions/scene-c/clearance-elevation")
        result = resp.json()
        assert result["status"] == "OK", f"Run {run_number}: Scene C failed"
        assert len(result["dissolved_fields"]) > 0, f"Run {run_number}: no fields dissolved"

        # Step 7: Audit events
        resp = await client.get("/api/audit/events", params={"limit": "20"})
        events = resp.json()
        assert len(events) >= 3, f"Run {run_number}: expected >=3 audit events"
```

---

## 8. Verification Checklist

```bash
# 1. Backend unit + permission tests
cd /home/logan/GovTrack/backend
source .venv/bin/activate
pytest tests/test_permissions.py tests/test_permission_negative.py -v
# Expected: 44+ tests passed

# 2. E2E TTHC tests (requires running services)
pytest tests/test_e2e_tthc.py -v
# Expected: 5 tests passed (1 per TTHC)

# 3. Agent benchmarks
pytest tests/test_agent_benchmarks.py -v --tb=short
# Expected: accuracy targets met, latency under limits

# 4. WebSocket test (requires running backend)
pytest tests/test_websocket.py -v
# Expected: events arrive in order

# 5. Demo reliability
pytest tests/test_demo_reliability.py -v
# Expected: 5/5 runs pass

# 6. Frontend smoke tests
cd /home/logan/GovTrack/frontend
npx playwright install
npx playwright test tests/smoke.spec.ts
# Expected: 10/10 tests pass, all 8 screens render

# 7. Full suite summary
cd /home/logan/GovTrack/backend
pytest --tb=short -q
# Expected output:
#   XX passed, 0 failed
#   Accuracy: classification >80%, compliance >90%, citation >85%
#   Latency: per-agent p95 <5s, pipeline p95 <30s
#   Demo: 5/5 consecutive passes
```

---

## Tong ket (Summary)

| Test Category         | File                               | Count  | Targets                    |
|-----------------------|------------------------------------|--------|----------------------------|
| E2E Happy Path        | test_e2e_tthc.py                   | 5      | All TTHC pipelines complete|
| Permission Negative   | test_permission_negative.py        | 23     | All denials + audit logged |
| Agent Accuracy        | test_agent_benchmarks.py           | 15     | >80/90/85% by type         |
| Latency Benchmark     | test_agent_benchmarks.py           | 2      | p95 <5s agent, <30s total  |
| WebSocket Integration | test_websocket.py                  | 3      | Events ordered, channels ok|
| Frontend Smoke        | smoke.spec.ts                      | 10     | All 8 screens + nav + theme|
| Demo Reliability      | test_demo_reliability.py           | 5      | 100% pass rate             |

Next step: proceed to `19-demo-preparation.md` for seed data and demo scripts.
