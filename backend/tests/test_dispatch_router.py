"""
Wave 2 — Task 2.5: DispatchRouterAgent unit tests.

Tests:
  - 3 candidate depts -> 3 DispatchLog + DISPATCHED_TO edges written (mock LLM)
  - CaseType enum values correct
  - PIPELINE_DISPATCH registered in PIPELINES dict
  - migrate_case_types_default template registered
  - case_by_type template registered
  - Classifier dispatch mode returns subject_tags + urgency (no TTHC code)
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.enums import CaseType


# ── CaseType enum ─────────────────────────────────────────────────────────────


def test_case_type_enum_values():
    assert CaseType.CITIZEN_TTHC == "citizen_tthc"
    assert CaseType.INTERNAL_DISPATCH == "internal_dispatch"


# ── PIPELINE_DISPATCH registration ───────────────────────────────────────────


def test_pipeline_dispatch_registered():
    from src.agents.orchestrator import PIPELINES, PIPELINE_DISPATCH
    assert "dispatch" in PIPELINES
    assert PIPELINES["dispatch"] is PIPELINE_DISPATCH


def test_pipeline_dispatch_structure():
    from src.agents.orchestrator import PIPELINE_DISPATCH
    task_names = [t[0] for t in PIPELINE_DISPATCH]
    agent_names = [t[1] for t in PIPELINE_DISPATCH]
    assert "dispatch" in task_names
    assert "dispatch_router_agent" in agent_names
    # dispatch depends on security which depends on classify
    dispatch_step = next(t for t in PIPELINE_DISPATCH if t[0] == "dispatch")
    assert "security" in dispatch_step[2]


# ── Gremlin templates ─────────────────────────────────────────────────────────


def test_dispatch_templates_registered():
    from src.graph.templates import TEMPLATES
    assert "dispatch_recipients_by_clearance" in TEMPLATES
    assert "create_dispatch_log" in TEMPLATES
    assert "case_by_type" in TEMPLATES
    assert "migrate_case_types_default" in TEMPLATES


def test_dispatch_templates_params():
    from src.graph.templates import TEMPLATES
    t = TEMPLATES["create_dispatch_log"]
    assert "lid" in t.params
    assert "cid" in t.params
    assert "did" in t.params

    t2 = TEMPLATES["case_by_type"]
    assert "case_type" in t2.params
    assert "lim" in t2.params

    t3 = TEMPLATES["migrate_case_types_default"]
    assert t3.params == []  # no params — runs on all Case vertices


# ── DispatchRouterAgent unit test (mock LLM) ──────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dispatch_router_writes_3_logs():
    """
    Feed 3 candidate depts -> mock LLM returns all 3 -> assert 3 DispatchLog
    + DISPATCHED_TO edges written.
    Requires: live Gremlin server at localhost:8182.
    """
    import src.database as _db

    try:
        _db.create_gremlin_client()
    except Exception:
        pass

    from src.agents.implementations.dispatch_router import DispatchRouterAgent
    from src.auth import SYSTEM_SESSION

    agent = DispatchRouterAgent()
    agent._session = SYSTEM_SESSION
    case_id = f"case-dr-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    # Seed a Case vertex
    gdb = agent._get_gdb()
    await gdb.execute(
        "g.addV('Case')"
        ".property('case_id', cid).property('code', code)"
        ".property('status', 'classifying').property('submitted_at', ts)"
        ".property('case_type', 'internal_dispatch')"
        ".property('subject_tags', tags)"
        ".property('current_classification', '1')"
        ".property('department_id', 'dept-hanh-chinh').property('tthc_code', 'TEST')",
        {
            "cid": case_id,
            "code": f"HS-{case_id[:8]}",
            "ts": now,
            "tags": json.dumps(["PCCC", "phòng cháy", "hợp tác"], ensure_ascii=False),
        },
    )

    three_depts = [
        {"dept_id": "dept-phap-che", "dept_name": "Phòng Pháp chế", "confidence": 0.92, "rationale": "Liên quan pháp lý"},
        {"dept_id": "dept-ky-thuat", "dept_name": "Phòng Kỹ thuật", "confidence": 0.85, "rationale": "Chuyên môn PCCC"},
        {"dept_id": "dept-hanh-chinh", "dept_name": "Phòng Hành chính", "confidence": 0.75, "rationale": "Văn thư lưu"},
    ]

    llm_resp_content = json.dumps({"recipients": three_depts})

    # Mock the QwenClient.chat to return our controlled JSON
    mock_choice = MagicMock()
    mock_choice.message.content = llm_resp_content
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch.object(agent.client, "chat", new_callable=AsyncMock, return_value=mock_completion):
        result = await agent.run(case_id)

    assert result.status == "completed", f"Agent failed: {result.error}"

    output = json.loads(result.output)
    assert output["dispatch_count"] == 3, f"Expected 3 dispatches, got {output['dispatch_count']}"

    # Verify DispatchLog vertices in GDB
    logs = await gdb.execute(
        "g.V().has('DispatchLog', 'case_id', cid).valueMap(true)",
        {"cid": case_id},
    )
    assert len(logs) == 3, f"Expected 3 DispatchLog vertices, got {len(logs)}"

    # Verify DISPATCHED_TO edges
    edges = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).outE('DISPATCHED_TO').count()",
        {"cid": case_id},
    )
    edge_count = edges[0].get("value", 0) if edges and isinstance(edges[0], dict) else (edges[0] if edges else 0)
    assert int(edge_count) == 3, f"Expected 3 DISPATCHED_TO edges, got {edge_count}"

    # Cleanup
    await gdb.execute("g.V().has('Case', 'case_id', cid).drop()", {"cid": case_id})
    await gdb.execute("g.V().has('DispatchLog', 'case_id', cid).drop()", {"cid": case_id})


# ── Classifier dispatch mode ──────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classifier_dispatch_mode_no_tthc():
    """When case_type=internal_dispatch, classifier outputs subject_tags, not tthc_code.
    Requires: live Gremlin server at localhost:8182.
    """
    import src.database as _db

    try:
        _db.create_gremlin_client()
    except Exception:
        pass

    from src.agents.implementations.classifier import ClassifierAgent
    from src.auth import SYSTEM_SESSION

    agent = ClassifierAgent()
    agent._session = SYSTEM_SESSION
    agent._case_type = "internal_dispatch"  # inject dispatch context

    case_id = f"case-cls-{uuid.uuid4().hex[:8]}"
    now = datetime.now(UTC).isoformat()

    gdb = agent._get_gdb()
    await gdb.execute(
        "g.addV('Case')"
        ".property('case_id', cid).property('code', code)"
        ".property('status', 'classifying').property('submitted_at', ts)"
        ".property('case_type', 'internal_dispatch')"
        ".property('department_id', 'dept-hanh-chinh').property('tthc_code', '')",
        {"cid": case_id, "code": f"HS-{case_id[:8]}", "ts": now},
    )

    # Mock LLM returning subject_tags
    llm_resp = json.dumps({
        "subject_tags": ["PCCC", "phòng cháy chữa cháy", "phối hợp"],
        "urgency": "urgent",
        "summary": "Công văn đề nghị phối hợp xử lý hồ sơ PCCC",
    })
    mock_choice = MagicMock()
    mock_choice.message.content = llm_resp
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    with patch.object(agent.client, "chat", new_callable=AsyncMock, return_value=mock_completion):
        result = await agent.run(case_id)

    assert result.status == "completed", f"Agent failed: {result.error}"
    output = json.loads(result.output)

    assert output.get("case_type") == "internal_dispatch"
    assert "subject_tags" in output, "subject_tags missing from dispatch classifier output"
    assert "tthc_code" not in output, "tthc_code should NOT be in dispatch classifier output"
    assert output.get("urgency") in {"normal", "urgent", "emergency"}

    # Verify subject_tags stored on Case vertex
    rows = await gdb.execute(
        "g.V().has('Case', 'case_id', cid).values('subject_tags')",
        {"cid": case_id},
    )
    if rows:
        first = rows[0]
        tags_raw = first.get("value", "[]") if isinstance(first, dict) else str(first)
        tags = json.loads(tags_raw) if tags_raw else []
        assert len(tags) > 0, "subject_tags should be stored on Case vertex"

    # Cleanup
    await gdb.execute("g.V().has('Case', 'case_id', cid).drop()", {"cid": case_id})


# ── CaseResponse schema includes case_type ────────────────────────────────────


def test_case_response_has_case_type_field():
    from src.models.schemas import CaseResponse
    from datetime import datetime, timezone

    cr = CaseResponse(
        case_id="test-1",
        code="HS-TEST",
        status="submitted",
        tthc_code="TEST",
        department_id="dept-test",
        submitted_at=datetime.now(timezone.utc),
        applicant_name="Test",
        case_type=CaseType.INTERNAL_DISPATCH,
    )
    assert cr.case_type == CaseType.INTERNAL_DISPATCH


def test_case_create_default_case_type():
    from src.models.schemas import CaseCreate

    cc = CaseCreate(
        tthc_code="TEST",
        department_id="dept-test",
        applicant_name="Test",
        applicant_id_number="123456789",
    )
    assert cc.case_type == CaseType.CITIZEN_TTHC


def test_case_create_internal_dispatch():
    from src.models.schemas import CaseCreate

    cc = CaseCreate(
        tthc_code="TEST",
        department_id="dept-test",
        applicant_name="Test",
        applicant_id_number="123456789",
        case_type=CaseType.INTERNAL_DISPATCH,
    )
    assert cc.case_type == CaseType.INTERNAL_DISPATCH
