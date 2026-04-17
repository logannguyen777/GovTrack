"""
tests/test_legal_lookup_repealed.py
Tests for LegalLookup REPEALED/SUPERSEDED article filtering.
"""

from __future__ import annotations

import pytest

from src.agents.implementations.legal_lookup import LegalLookupAgent


# ---------------------------------------------------------------------------
# Helper: minimal fake GDB client
# ---------------------------------------------------------------------------


class _FakeGDB:
    """Minimal fake PermittedGremlinClient — execute() returns items from a queue."""

    def __init__(self, responses: list):
        """
        Args:
            responses: ordered list of return values for successive execute() calls.
                       If exhausted, further calls return [].
        """
        self._queue = list(responses)
        self.calls: list[tuple[str, dict]] = []

    async def execute(self, query: str, params: dict | None = None):
        self.calls.append((query, params or {}))
        if self._queue:
            return self._queue.pop(0)
        return []


def _make_agent(gdb_responses: list) -> tuple[LegalLookupAgent, _FakeGDB]:
    """Create a bare LegalLookupAgent with a mocked _get_gdb()."""
    agent = LegalLookupAgent.__new__(LegalLookupAgent)
    fake_gdb = _FakeGDB(gdb_responses)
    # Override _get_gdb to return the same fake_gdb instance every time
    agent._get_gdb = lambda: fake_gdb  # type: ignore[method-assign]
    return agent, fake_gdb


# ---------------------------------------------------------------------------
# _is_historical_query
# ---------------------------------------------------------------------------


def test_is_historical_query_trươc_đây():
    assert LegalLookupAgent._is_historical_query("trước đây quy định như thế nào") is True


def test_is_historical_query_da_bi_thay_the():
    assert LegalLookupAgent._is_historical_query("điều này đã bị thay thế bởi qd mới") is True


def test_is_historical_query_old_year():
    """A query explicitly mentioning a year ≥ 5 years ago triggers historical mode."""
    assert LegalLookupAgent._is_historical_query("theo Nghị định năm 2010") is True


def test_is_historical_query_current_year_not_historical():
    """A query mentioning the current/recent year is NOT historical."""
    assert LegalLookupAgent._is_historical_query("theo Nghị định năm 2025") is False


def test_is_historical_query_normal():
    assert LegalLookupAgent._is_historical_query("điều kiện cấp phép xây dựng") is False


# ---------------------------------------------------------------------------
# _article_is_active (mock GDB via _get_gdb)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_article_is_active_no_edges():
    """Article with no REPEALED_BY or SUPERSEDED_BY edges is active."""
    agent, fake_gdb = _make_agent([
        [],  # REPEALED_BY query → no results
        [],  # SUPERSEDED_BY query → no results
    ])

    is_active, warning = await agent._article_is_active("kg_abc")
    assert is_active is True
    assert warning is None


@pytest.mark.asyncio
async def test_article_is_active_repealed():
    """Article with REPEALED_BY edge is NOT active."""
    agent, _ = _make_agent([
        # First execute() call: REPEALED_BY query → article found
        [{"_kg_id": ["kg_new"], "law_code": ["ND99/2020"], "num": ["5"]}],
    ])

    is_active, warning = await agent._article_is_active("kg_old")
    assert is_active is False
    assert warning is not None
    assert "bãi bỏ" in warning.lower() or "bai bo" in warning.lower()


@pytest.mark.asyncio
async def test_article_is_active_superseded():
    """Article with SUPERSEDED_BY edge returns warning with newer article info."""
    agent, _ = _make_agent([
        [],  # REPEALED_BY query → not repealed
        # SUPERSEDED_BY query → newer article found
        [{"law_code": ["ND99/2020"], "num": ["Điều 10"], "law_id": []}],
    ])

    is_active, warning = await agent._article_is_active("kg_old")
    assert is_active is False
    assert warning is not None
    assert "thay thế" in warning or "ND99/2020" in warning


# ---------------------------------------------------------------------------
# _resolve_effective_article — repealed returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_effective_article_not_in_kg():
    """Article not in KG returns None (uses vector content as-is)."""
    agent, _ = _make_agent([
        [],  # Initial Article lookup → not found
    ])

    result = await agent._resolve_effective_article("ND123/2020", "5", query="test")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_effective_article_repealed_returns_none():
    """Article with REPEALED_BY edge and normal query → returns None."""
    agent, _ = _make_agent([
        # Initial Article lookup → found
        [{"_kg_id": ["kg_old"], "law_code": ["ND123"], "num": ["5"], "status": [""]}],
        # REPEALED_BY check → repealed
        [{"_kg_id": ["kg_new"]}],
        # Subsequent calls would not be reached
    ])

    result = await agent._resolve_effective_article("ND123/2020", "5", query="normal query")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_effective_article_historical_query_keeps_repealed():
    """With historical query, even a repealed article is kept (user asked for history)."""
    agent, _ = _make_agent([
        # Initial Article lookup → found
        [{"_kg_id": ["kg_old"], "law_code": ["ND123"], "num": ["5"],
          "status": ["active"], "title": ["Test"], "text": ["Content"]}],
        # REPEALED_BY check (allow_historical=True so we don't return None, but still called)
        [{"_kg_id": ["kg_replaced"]}],
        # SUPERSEDED_BY chain traversal → nothing
        [],
        # AMENDED_BY chain traversal → nothing
        [],
    ])

    result = await agent._resolve_effective_article(
        "ND123/2020", "5",
        query="trước đây điều này quy định gì",  # historical query
    )
    # Should NOT be None — historical query allows repealed content
    assert result is not None
