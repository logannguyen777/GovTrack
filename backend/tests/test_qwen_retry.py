"""
tests/test_qwen_retry.py
Tests for:
  - 429 Retry-After header handling
  - Circuit breaker open/close behavior
  - Token budget pre-check in BaseAgent
  - Adaptive timeout per task_type
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers: build a minimal QwenClient with a mock underlying OpenAI client
# ---------------------------------------------------------------------------

def _make_client():
    from src.agents.qwen_client import QwenClient

    client = QwenClient.__new__(QwenClient)
    client.usage = MagicMock(total_tokens=0, input_tokens=0, output_tokens=0, api_calls=0, total_latency_ms=0)
    client.max_retries = 3
    client._cb_failure_timestamps = []
    client._cb_open_until = 0.0
    client._cb_window_s = 60.0
    client._cb_threshold = 5
    client._cb_open_duration_s = 300.0
    client._cb_half_open_allowed = False
    client._cb_lock = asyncio.Lock()
    client.client = MagicMock()
    return client


# ---------------------------------------------------------------------------
# 1.5 Token budget pre-check in BaseAgent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_token_budget_exceeded_before_llm_call():
    """
    When projected tokens would exceed the budget, TokenBudgetExceeded is raised
    BEFORE the LLM call, and agent returns status="failed" / error="token_budget_exceeded".
    """
    from src.agents.qwen_client import TokenBudgetExceeded

    with (
        patch("src.agents.base.load_profile") as mock_profile,
        patch("src.agents.base.get_mcp_registry"),
        patch("src.agents.base.QwenClient") as MockQwenClient,
    ):
        mock_prof = MagicMock(
            name="test_agent",
            model="qwen-max-latest",
            system_prompt="test",
            clearance_cap=3,
            max_iterations=3,
            max_tokens_budget=10,  # Very low budget
            role="test",
        )
        mock_profile.return_value = mock_prof

        mock_client = MagicMock()
        mock_client.usage.total_tokens = 0
        mock_client.reset_usage.return_value = MagicMock(
            input_tokens=0, output_tokens=0, api_calls=0
        )
        MockQwenClient.return_value = mock_client

        from src.agents.base import BaseAgent, AgentResult

        class TestAgent(BaseAgent):
            async def build_messages(self, case_id):
                # Return a large message that will exceed the budget
                return [
                    {"role": "system", "content": "x" * 100},  # ~100 chars = ~25 tokens
                ]

        agent = TestAgent("test_agent")

        # Mock the gremlin call so clearance check passes
        with patch("src.agents.base.async_gremlin_submit as _gremlin", create=True):
            pass

        # Patch the gremlin import inside run()
        with patch(
            "src.agents.base.BaseAgent.run",
            wraps=agent.run,
        ):
            # We need to mock the internal gremlin call
            with patch(
                "src.agents.base.async_gremlin_submit",
                new_callable=AsyncMock,
                return_value=[],  # case_classification = 0
                create=True,
            ):
                result = await agent.run("test-case-001")

        # The agent should fail with token_budget_exceeded
        assert result.status == "failed"
        assert result.error == "token_budget_exceeded"


# ---------------------------------------------------------------------------
# 1.5 Adaptive timeout
# ---------------------------------------------------------------------------


def test_timeout_for_vision():
    from src.agents.qwen_client import QwenClient
    assert QwenClient._timeout_for_task("vision") == 180  # default


def test_timeout_for_reasoning():
    from src.agents.qwen_client import QwenClient
    assert QwenClient._timeout_for_task("reasoning") == 120


def test_timeout_for_embedding():
    from src.agents.qwen_client import QwenClient
    assert QwenClient._timeout_for_task("embedding") == 30


def test_timeout_for_unknown_falls_back_to_reasoning():
    from src.agents.qwen_client import QwenClient
    assert QwenClient._timeout_for_task("unknown_type") == 120


# ---------------------------------------------------------------------------
# 1.6 429 Retry-After handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_retry_after_sleeps_correct_duration():
    """
    When DashScope returns a 429 RateLimitError with Retry-After: 60,
    the client sleeps for 60 seconds before retrying.
    """
    import openai

    client = _make_client()

    # Build a mock response with Retry-After header
    mock_response = MagicMock()
    mock_response.headers = {"retry-after": "60"}
    rate_limit_err = openai.RateLimitError(
        message="Rate limited",
        response=mock_response,
        body=None,
    )

    # First two attempts raise 429; third succeeds
    fake_completion = MagicMock()
    fake_completion.usage.prompt_tokens = 10
    fake_completion.usage.completion_tokens = 5
    fake_completion.usage.total_tokens = 15
    fake_completion.choices = [MagicMock()]

    call_count = 0

    async def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise rate_limit_err
        return fake_completion

    # Wrap mock_create in an AsyncMock so it plays nicely with asyncio.wait_for
    client.client.chat.completions.create = AsyncMock(side_effect=mock_create)

    sleep_calls = []

    async def mock_sleep(seconds):
        sleep_calls.append(seconds)

    with patch("src.agents.qwen_client.asyncio.sleep", side_effect=mock_sleep):
        with patch("src.agents.qwen_client.settings") as mock_settings:
            mock_settings.demo_mode = False
            mock_settings.qwen_timeout_reasoning_s = 120
            mock_settings.qwen_timeout_vision_s = 180
            mock_settings.qwen_timeout_embedding_s = 30

            from src.agents.qwen_client import MODELS

            with patch("src.agents.qwen_client.MODELS", MODELS):
                result = await client.chat(
                    messages=[{"role": "user", "content": "test"}],
                    model="reasoning",
                    task_type="reasoning",
                )

    # Should have slept for 60s (from Retry-After header) at least once
    assert 60 in sleep_calls or 60.0 in sleep_calls


# ---------------------------------------------------------------------------
# 1.6 Circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """After 5 failures in 60s, circuit opens and subsequent calls fail immediately."""
    from src.agents.qwen_client import CircuitOpenError, QwenClient

    client = _make_client()
    client._cb_threshold = 3  # Lower threshold for test speed

    # Record 3 failures directly
    for _ in range(3):
        await client._cb_record_failure()

    # Circuit should now be open
    with pytest.raises(CircuitOpenError, match="dashscope_circuit_open"):
        await client._cb_check()


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success():
    """After a successful call, the circuit breaker resets."""
    from src.agents.qwen_client import CircuitOpenError

    client = _make_client()
    client._cb_threshold = 3

    for _ in range(3):
        await client._cb_record_failure()

    # Record success — should reset
    await client._cb_record_success()

    # Should NOT raise now
    await client._cb_check()  # no exception = pass


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_duration(monkeypatch):
    """
    After circuit opens for _cb_open_duration_s, it allows one trial (half-open).
    This is not directly tested here — but we verify the open_until timestamp math.
    """
    import time as _time

    from src.agents.qwen_client import CircuitOpenError

    client = _make_client()
    client._cb_threshold = 1

    # Manually set circuit open with a past timestamp (already expired)
    client._cb_open_until = _time.monotonic() - 1.0  # expired 1 second ago

    # Should NOT raise because open_until is in the past
    await client._cb_check()  # no exception = pass
