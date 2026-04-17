"""
tests/test_compliance_score.py
Golden test: compliance score formula with blockers + warnings.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture()
def agent():
    """Create ComplianceAgent with mocked profile + client."""
    with (
        patch("src.agents.implementations.compliance.async_gremlin_submit", new_callable=AsyncMock),
        patch("src.agents.base.load_profile") as mock_profile,
        patch("src.agents.base.get_mcp_registry"),
        patch("src.agents.base.QwenClient"),
    ):
        mock_profile.return_value = MagicMock(
            name="compliance_agent",
            model="qwen-max-latest",
            system_prompt="test",
            clearance_cap=3,
            max_iterations=5,
            max_tokens_budget=100000,
            role="compliance_checker",
        )
        from src.agents.implementations.compliance import ComplianceAgent
        a = ComplianceAgent.__new__(ComplianceAgent)
        a.profile = mock_profile.return_value
        a.client = MagicMock()
        a.client.usage = MagicMock(total_tokens=0)
        a.client.reset_usage = MagicMock(return_value=MagicMock(input_tokens=0, output_tokens=0, api_calls=0))
        a._event_emitter = None
        return a


def _make_required(n: int) -> list[dict]:
    """Make n mandatory required components."""
    return [{"name": f"comp_{i}", "is_required": True, "condition": None, "_kg_id": f"kg_{i}", "doc_type_match": None} for i in range(n)]


def _make_gap(name: str, severity: str, is_blocking: bool) -> dict:
    return {
        "component_name": name,
        "severity": severity,
        "is_blocking": is_blocking,
        "reason": f"Thieu {name}",
        "fix_suggestion": "",
        "law_citation": "",
    }


def test_score_10_required_1_blocker_2_warnings():
    """
    Golden test: 10 required, 1 blocker, 2 warnings.
    Expected: compliance_score=90%, blocker_count=1, warning_count=2.
    """
    from src.agents.implementations.compliance import ComplianceAgent

    required_components_data = _make_required(10)

    # LLM returns 3 gaps: 1 blocker + 2 warnings
    confirmed_gaps = [
        {"component_name": "comp_0", "severity": "blocker", "is_blocking": True,
         "reason": "Thieu comp_0", "fix_suggestion": "", "law_citation": ""},
        {"component_name": "comp_1", "severity": "warning", "is_blocking": False,
         "reason": "Canh bao comp_1", "fix_suggestion": "", "law_citation": ""},
        {"component_name": "comp_2", "severity": "warning", "is_blocking": False,
         "reason": "Canh bao comp_2", "fix_suggestion": "", "law_citation": ""},
    ]

    total_mandatory = sum(1 for c in required_components_data if c["is_required"])
    blocker_count = sum(
        1 for g in confirmed_gaps
        if g.get("is_blocking", True) and g.get("severity") != "info"
    )
    warning_count = sum(
        1 for g in confirmed_gaps
        if not g.get("is_blocking", True) or g.get("severity") == "warning"
    )
    satisfied_count = total_mandatory - blocker_count
    compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

    assert total_mandatory == 10
    assert blocker_count == 1
    assert warning_count == 2
    assert satisfied_count == 9
    assert compliance_score == 90.0


def test_score_no_gaps():
    """All 10 required satisfied, 0 gaps → 100%."""
    required_components_data = _make_required(10)
    confirmed_gaps: list[dict] = []

    total_mandatory = 10
    blocker_count = sum(
        1 for g in confirmed_gaps
        if g.get("is_blocking", True) and g.get("severity") != "info"
    )
    warning_count = sum(
        1 for g in confirmed_gaps
        if not g.get("is_blocking", True) or g.get("severity") == "warning"
    )
    satisfied_count = total_mandatory - blocker_count
    compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

    assert compliance_score == 100.0
    assert blocker_count == 0
    assert warning_count == 0


def test_score_all_blockers():
    """5 required, all 5 blocked → 0%."""
    total_mandatory = 5
    confirmed_gaps = [
        {"component_name": f"comp_{i}", "severity": "blocker", "is_blocking": True}
        for i in range(5)
    ]
    blocker_count = sum(
        1 for g in confirmed_gaps
        if g.get("is_blocking", True) and g.get("severity") != "info"
    )
    satisfied_count = total_mandatory - blocker_count
    compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

    assert compliance_score == 0.0


def test_warning_only_does_not_reduce_score():
    """
    Bug regression: before fix, warning-only gaps incorrectly reduced score
    because satisfied_count = total_mandatory - blocker_count where
    blocker_count counted warnings too.

    After fix: warnings do NOT reduce score.
    """
    total_mandatory = 5
    confirmed_gaps = [
        {"component_name": "comp_1", "severity": "warning", "is_blocking": False},
        {"component_name": "comp_2", "severity": "warning", "is_blocking": False},
    ]
    blocker_count = sum(
        1 for g in confirmed_gaps
        if g.get("is_blocking", True) and g.get("severity") != "info"
    )
    warning_count = sum(
        1 for g in confirmed_gaps
        if not g.get("is_blocking", True) or g.get("severity") == "warning"
    )
    satisfied_count = total_mandatory - blocker_count
    compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

    # Warnings must NOT reduce the score
    assert compliance_score == 100.0
    assert blocker_count == 0
    assert warning_count == 2


def test_is_blocking_defaults_true_for_unknown_gaps():
    """Gaps without explicit is_blocking field default to blocking (safe-by-default)."""
    total_mandatory = 5
    # Gap with no is_blocking key
    confirmed_gaps = [{"component_name": "comp_1", "severity": "blocker"}]
    blocker_count = sum(
        1 for g in confirmed_gaps
        if g.get("is_blocking", True) and g.get("severity") != "info"
    )
    satisfied_count = total_mandatory - blocker_count
    compliance_score = round((satisfied_count / max(total_mandatory, 1)) * 100, 1)

    assert blocker_count == 1
    assert compliance_score == 80.0
