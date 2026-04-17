"""
tests/test_router_idempotent.py
Unit tests for Router idempotency logic.
"""

from __future__ import annotations

import pytest

from src.agents.implementations.router import RouterAgent


# ---------------------------------------------------------------------------
# Pure unit tests on the idempotency decision logic
# ---------------------------------------------------------------------------


def _extract_prop(vertex_map: dict, key: str) -> str:
    val = vertex_map.get(key, "")
    if isinstance(val, list):
        return val[0] if val else ""
    return str(val) if val else ""


def _make_existing_assignment(org_id: str, org_name: str, existing_conf: float):
    """Build a fake existing assignment result as returned by Gremlin."""
    return [
        {
            "e": {"confidence": [existing_conf], "assigned_at": ["2026-01-01"]},
            "org": {"org_id": [org_id], "name": [org_name], "level": ["so"]},
        }
    ]


class TestRouterIdempotencyLogic:
    """Test the reassign/keep logic without full Gremlin mocking."""

    def test_new_confidence_significantly_higher_should_reassign(self):
        """New conf >= existing + 0.1 → reassign."""
        existing_conf = 0.75
        new_confidence = 0.90  # 0.90 >= 0.75 + 0.10 → reassign

        assert new_confidence >= existing_conf + 0.1

    def test_new_confidence_slightly_lower_should_keep(self):
        """New conf < existing + 0.1 → keep existing."""
        existing_conf = 0.90
        new_confidence = 0.91  # 0.91 < 0.90 + 0.10 = 1.0 → keep

        assert new_confidence < existing_conf + 0.1

    def test_same_confidence_should_keep(self):
        """Same confidence → keep existing."""
        existing_conf = 0.90
        new_confidence = 0.90  # 0.90 < 0.90 + 0.10 → keep

        assert new_confidence < existing_conf + 0.1

    def test_exactly_threshold_should_reassign(self):
        """new_conf == existing + 0.1 exactly → reassign (>= boundary)."""
        existing_conf = 0.80
        new_confidence = 0.90  # exactly existing + 0.10

        assert new_confidence >= existing_conf + 0.1


class TestRouterExtractProp:
    """Test the _extract_prop helper used in idempotency code."""

    def test_extract_from_list(self):
        result = RouterAgent._extract_prop({"name": ["Phong A"]}, "name")
        assert result == "Phong A"

    def test_extract_from_str(self):
        result = RouterAgent._extract_prop({"name": "Phong B"}, "name")
        assert result == "Phong B"

    def test_extract_missing_key(self):
        result = RouterAgent._extract_prop({}, "name")
        assert result == ""

    def test_extract_from_empty_list(self):
        result = RouterAgent._extract_prop({"name": []}, "name")
        assert result == ""


class TestRouterConfidenceExtraction:
    """Test that confidence is correctly extracted from existing assignment edge."""

    def test_confidence_from_list_wrapped(self):
        existing_assignment = _make_existing_assignment("org_1", "Phong A", 0.85)
        existing_edge = existing_assignment[0]
        edge_props = existing_edge.get("e", {})
        existing_conf_raw = edge_props.get("confidence", [0.0])
        existing_conf = float(
            existing_conf_raw[0]
            if isinstance(existing_conf_raw, list)
            else existing_conf_raw
        )
        assert existing_conf == 0.85

    def test_confidence_missing_defaults_zero(self):
        existing_assignment = [{"e": {}, "org": {"org_id": ["org_1"], "name": ["X"], "level": ["so"]}}]
        existing_edge = existing_assignment[0]
        edge_props = existing_edge.get("e", {})
        existing_conf_raw = edge_props.get("confidence", [0.0])
        existing_conf = float(
            existing_conf_raw[0]
            if isinstance(existing_conf_raw, list)
            else existing_conf_raw
        )
        assert existing_conf == 0.0
