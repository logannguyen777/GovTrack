"""
tests/test_security_officer_no_downgrade.py
Unit tests for SecurityOfficer no-downgrade invariant (4 scenarios from spec).
"""

from __future__ import annotations

import pytest

from src.agents.implementations.security_officer import SecurityOfficerAgent


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _compute_final_level(
    agent: SecurityOfficerAgent,
    existing_level: str,
    llm_level: str,
    keyword_suggested: str,
    aggregation_risk: bool,
    location_sensitive: bool,
) -> tuple[str, str, str]:
    """
    Re-implement the no-downgrade logic from security_officer.run() as a pure function
    so we can test it without the full pipeline.

    Returns (proposed_level, final_level, rationale_vi).
    """
    aggregation_suggested = "Confidential" if aggregation_risk else "Unclassified"
    location_suggested = "Confidential" if location_sensitive else "Unclassified"

    proposed_level = agent._max_level(
        llm_level,
        agent._max_level(
            keyword_suggested,
            agent._max_level(aggregation_suggested, location_suggested),
        ),
    )

    final_level = agent._max_level(existing_level, proposed_level)

    if agent.CLEARANCE_ORDER.get(final_level, 0) > agent.CLEARANCE_ORDER.get(existing_level, 0):
        triggers = []
        if agent.CLEARANCE_ORDER.get(keyword_suggested, 0) >= agent.CLEARANCE_ORDER.get(final_level, 0):
            triggers.append(f"từ khóa nhạy cảm ({keyword_suggested})")
        if aggregation_risk:
            triggers.append("nguy cơ tổng hợp thông tin cá nhân")
        if location_sensitive:
            triggers.append("địa điểm nhạy cảm")
        if agent.CLEARANCE_ORDER.get(llm_level, 0) >= agent.CLEARANCE_ORDER.get(final_level, 0):
            triggers.append(f"đánh giá LLM ({llm_level})")
        rationale_vi = (
            f"Mức phân loại được nâng từ {existing_level} lên {final_level} "
            f"do: {'; '.join(triggers) if triggers else 'đánh giá tổng hợp'}."
        )
    else:
        rationale_vi = "Giữ nguyên mức phân loại hiện tại."

    return proposed_level, final_level, rationale_vi


@pytest.fixture()
def agent():
    return SecurityOfficerAgent.__new__(SecurityOfficerAgent)


# ---------------------------------------------------------------------------
# Scenario (a): existing=UNCLASSIFIED, llm=CONFIDENTIAL → bumped
# ---------------------------------------------------------------------------


def test_scenario_a_unclassified_to_confidential(agent):
    _, final, rationale = _compute_final_level(
        agent,
        existing_level="Unclassified",
        llm_level="Confidential",
        keyword_suggested="Unclassified",
        aggregation_risk=False,
        location_sensitive=False,
    )
    assert final == "Confidential"
    assert "Unclassified" in rationale
    assert "Confidential" in rationale
    assert "Giữ nguyên" not in rationale


# ---------------------------------------------------------------------------
# Scenario (b): existing=SECRET, llm=CONFIDENTIAL → kept Secret (no downgrade)
# ---------------------------------------------------------------------------


def test_scenario_b_no_downgrade_secret(agent):
    _, final, rationale = _compute_final_level(
        agent,
        existing_level="Secret",
        llm_level="Confidential",
        keyword_suggested="Unclassified",
        aggregation_risk=False,
        location_sensitive=False,
    )
    assert final == "Secret"  # No downgrade
    assert "Giữ nguyên" in rationale


# ---------------------------------------------------------------------------
# Scenario (c): existing=CONFIDENTIAL + aggregation risk → bumped via aggregation
# ---------------------------------------------------------------------------


def test_scenario_c_aggregation_bumps(agent):
    _, final, rationale = _compute_final_level(
        agent,
        existing_level="Unclassified",
        llm_level="Unclassified",
        keyword_suggested="Unclassified",
        aggregation_risk=True,
        location_sensitive=False,
    )
    assert final == "Confidential"
    assert "tổng hợp" in rationale or "aggregation" in rationale.lower() or "nguy cơ" in rationale


# ---------------------------------------------------------------------------
# Scenario (d): existing=UNCLASSIFIED, no triggers → stays UNCLASSIFIED
# ---------------------------------------------------------------------------


def test_scenario_d_no_triggers_stays_unclassified(agent):
    _, final, rationale = _compute_final_level(
        agent,
        existing_level="Unclassified",
        llm_level="Unclassified",
        keyword_suggested="Unclassified",
        aggregation_risk=False,
        location_sensitive=False,
    )
    assert final == "Unclassified"
    assert "Giữ nguyên" in rationale


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


def test_top_secret_existing_never_downgrades(agent):
    """Top Secret existing can NEVER be downgraded by any input."""
    _, final, _ = _compute_final_level(
        agent,
        existing_level="Top Secret",
        llm_level="Unclassified",
        keyword_suggested="Unclassified",
        aggregation_risk=False,
        location_sensitive=False,
    )
    assert final == "Top Secret"


def test_location_sensitive_bumps_to_confidential(agent):
    _, final, rationale = _compute_final_level(
        agent,
        existing_level="Unclassified",
        llm_level="Unclassified",
        keyword_suggested="Unclassified",
        aggregation_risk=False,
        location_sensitive=True,
    )
    assert final == "Confidential"
    assert "địa điểm" in rationale


def test_max_level_ordering(agent):
    """_max_level returns the higher clearance level."""
    assert agent._max_level("Unclassified", "Confidential") == "Confidential"
    assert agent._max_level("Secret", "Confidential") == "Secret"
    assert agent._max_level("Top Secret", "Secret") == "Top Secret"
    assert agent._max_level("Unclassified", "Unclassified") == "Unclassified"


def test_proposed_level_is_max_of_all_inputs(agent):
    """proposed_level must be max of llm + keyword + aggregation + location."""
    proposed, final, _ = _compute_final_level(
        agent,
        existing_level="Unclassified",
        llm_level="Unclassified",
        keyword_suggested="Secret",   # keyword drives it
        aggregation_risk=False,
        location_sensitive=False,
    )
    assert proposed == "Secret"
    assert final == "Secret"
