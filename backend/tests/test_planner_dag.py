"""
tests/test_planner_dag.py
Unit tests for PlannerAgent DAG validation: ghost deps and cycle detection.
"""

from __future__ import annotations

import pytest

from src.agents.implementations.planner import PlannerAgent, PlannerInvalidDAG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(name: str, depends_on: list[str]) -> dict:
    return {
        "name": name,
        "agent": PlannerAgent.TASK_TO_AGENT.get(name, "unknown_agent"),
        "depends_on": depends_on,
        "priority": "normal",
        "conditional": None,
    }


# ---------------------------------------------------------------------------
# Ghost dependency test
# ---------------------------------------------------------------------------


def test_ghost_dependency_raises():
    """A task whose depends_on references a task not in the plan raises PlannerInvalidDAG."""
    tasks = [
        _make_task("doc_analyze", depends_on=[]),
        _make_task("classify", depends_on=["doc_analyze"]),
        # "ghost_task" is neither in KNOWN_TASK_NAMES nor in the plan
        _make_task("compliance_check", depends_on=["ghost_task"]),
    ]
    with pytest.raises(PlannerInvalidDAG, match="ghost_task"):
        PlannerAgent._detect_cycles(tasks)


def test_known_but_absent_from_plan_raises():
    """
    A task that IS in KNOWN_TASK_NAMES but NOT in the plan still raises because
    closure requires both conditions.
    """
    # "legal_lookup" is known but not in this mini-plan
    tasks = [
        _make_task("doc_analyze", depends_on=[]),
        _make_task("classify", depends_on=["doc_analyze"]),
        _make_task("compliance_check", depends_on=["legal_lookup"]),
    ]
    with pytest.raises(PlannerInvalidDAG, match="legal_lookup"):
        PlannerAgent._detect_cycles(tasks)


# ---------------------------------------------------------------------------
# Cycle detection tests
# ---------------------------------------------------------------------------


def test_direct_cycle_raises():
    """A → B → A cycle must raise PlannerInvalidDAG."""
    tasks = [
        _make_task("doc_analyze", depends_on=["classify"]),
        _make_task("classify", depends_on=["doc_analyze"]),
    ]
    with pytest.raises(PlannerInvalidDAG, match="[Cc]ycle"):
        PlannerAgent._detect_cycles(tasks)


def test_three_way_cycle_raises():
    """A → B → C → A cycle raises."""
    tasks = [
        _make_task("doc_analyze", depends_on=["compliance_check"]),
        _make_task("classify", depends_on=["doc_analyze"]),
        _make_task("compliance_check", depends_on=["classify"]),
    ]
    with pytest.raises(PlannerInvalidDAG, match="[Cc]ycle"):
        PlannerAgent._detect_cycles(tasks)


def test_valid_dag_returns_false():
    """A valid DAG returns False (no cycle, no invalid deps)."""
    tasks = [
        _make_task("doc_analyze", depends_on=[]),
        _make_task("security_scan_initial", depends_on=[]),
        _make_task("classify", depends_on=["doc_analyze"]),
        _make_task("compliance_check", depends_on=["classify", "doc_analyze"]),
        _make_task("legal_lookup", depends_on=["compliance_check"]),
        _make_task("route", depends_on=["classify"]),
        _make_task("summarize", depends_on=["compliance_check", "legal_lookup"]),
        _make_task("draft_notice_if_gap", depends_on=["compliance_check"]),
    ]
    result = PlannerAgent._detect_cycles(tasks)
    assert result is False


def test_empty_plan_returns_false():
    """Empty task list is always valid."""
    assert PlannerAgent._detect_cycles([]) is False


def test_single_task_no_deps_returns_false():
    """Single task with no dependencies is valid."""
    tasks = [_make_task("doc_analyze", depends_on=[])]
    assert PlannerAgent._detect_cycles(tasks) is False
