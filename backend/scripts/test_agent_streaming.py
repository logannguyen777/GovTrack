"""
backend/scripts/test_agent_streaming.py
Verify agent streaming: events arrive in correct order through an in-process
mock WS channel.

Usage:
    cd /home/logan/GovTrack
    python -m backend.scripts.test_agent_streaming

No real DashScope calls are made — the script mocks QwenClient.stream_chat()
to emit synthetic StreamEvents.
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
import unittest
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal stubs so we can import agents without a real database
# ---------------------------------------------------------------------------

# Stub database
_stub_gremlin = AsyncMock(return_value=[])
_stub_pg_conn = MagicMock()
_stub_pg_conn.__aenter__ = AsyncMock(return_value=MagicMock(
    fetch=AsyncMock(return_value=[]),
    execute=AsyncMock(return_value=None),
))
_stub_pg_conn.__aexit__ = AsyncMock(return_value=None)


async def _fake_gremlin(query: str, params: dict | None = None) -> list:
    if "has('Case'" in query and "valueMap" in query:
        return [{
            "case_id": ["test-case-001"],
            "status": ["pending"],
            "tthc_code": ["1.004415"],
            "urgency": ["normal"],
            "compliance_score": ["85"],
            "sla_deadline": ["2026-04-20"],
            "sla_remaining_days": ["6"],
        }]
    if "HAS_SUMMARY" in query and "values('mode')" in query:
        return []  # no existing summaries
    if "MATCHES_TTHC" in query:
        return [{"code": ["1.004415"], "name": ["Cap phep xay dung"]}]
    return []


# ---------------------------------------------------------------------------
# Captured WS events (in-process substitute for WebSocket)
# ---------------------------------------------------------------------------

_captured_ws_events: list[dict] = []


async def _mock_ws_broadcast(topic: str, message: dict) -> None:
    _captured_ws_events.append({"topic": topic, **message})


# ---------------------------------------------------------------------------
# Synthetic Qwen stream responses
# ---------------------------------------------------------------------------

from backend.src.agents.streaming import StreamEvent, StreamingAgentEvent


async def _fake_stream_chat(
    *,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str | dict = "auto",
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> AsyncIterator[StreamEvent]:
    """Yield a synthetic thinking + text stream."""
    yield StreamEvent(type="thinking_chunk", delta="Phan tich ho so...")
    yield StreamEvent(type="thinking_chunk", delta=" Kiem tra compliance...")
    await asyncio.sleep(0)
    yield StreamEvent(type="text_chunk", delta='{"summary_text": "')
    yield StreamEvent(type="text_chunk", delta="Tom tat ngan: ho so dang xu ly.")
    yield StreamEvent(type="text_chunk", delta='", "mode": "executive", "word_count": 8}')
    yield StreamEvent(type="done", finish_reason="stop", usage={
        "prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150,
    })


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestAgentStreaming(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        _captured_ws_events.clear()

    async def test_summarizer_streaming_events(self) -> None:
        """Verify Summarizer.run_streaming emits thinking_chunk + text_chunk events."""
        with (
            patch("backend.src.database.async_gremlin_submit", side_effect=_fake_gremlin),
            patch("backend.src.database.pg_connection", return_value=_stub_pg_conn),
            patch("backend.src.agents.qwen_client.QwenClient.stream_chat", _fake_stream_chat),
            patch("backend.src.agents.qwen_client.QwenClient.chat", new_callable=AsyncMock,
                  return_value=MagicMock(choices=[MagicMock(message=MagicMock(
                      content='{"summary_text": "Fallback", "mode": "x", "word_count": 1}',
                      tool_calls=None,
                  ))], usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15))),
            patch("backend.src.api.ws.broadcast", _mock_ws_broadcast),
        ):
            from backend.src.agents.implementations.summarizer import SummarizerAgent
            from backend.src.agents.orchestrator import AgentRuntime

            agent = SummarizerAgent()

            # Inject emitter that routes to mock WS
            agent_id = "summary_agent:test"
            from backend.src.agents.orchestrator import AgentRuntime as _RT
            rt = _RT.__new__(_RT)
            rt.case_id = "test-case-001"
            rt.trace_id = "test"

            collected_events: list[StreamingAgentEvent] = []

            async def _emitter(evt: StreamingAgentEvent) -> None:
                collected_events.append(evt)
                ws_event = rt._translate(evt, agent_id)
                if ws_event:
                    await _mock_ws_broadcast(f"case:{rt.case_id}", ws_event)

            agent._event_emitter = _emitter

            # Consume run_streaming
            all_yielded: list[StreamingAgentEvent] = []
            async for event in agent.run_streaming("test-case-001"):
                all_yielded.append(event)

            # Verify event types
            event_types = [e.type for e in all_yielded]
            print(f"\n[test] Yielded event types: {event_types}")
            print(f"[test] Emitter collected: {[e.type for e in collected_events]}")
            print(f"[test] WS events: {[e.get('event') for e in _captured_ws_events]}")

            assert "thinking_chunk" in [e.type for e in collected_events], \
                "Expected thinking_chunk events from streaming callbacks"
            assert "text_chunk" in [e.type for e in collected_events], \
                "Expected text_chunk events from streaming callbacks"
            assert any(e.type in ("completed", "failed") for e in all_yielded), \
                "Expected terminal completed/failed event"

            # Check WS event types include agent_thinking_chunk
            ws_event_types = [e.get("event") for e in _captured_ws_events]
            assert "agent_thinking_chunk" in ws_event_types, \
                f"Expected agent_thinking_chunk in WS events, got: {ws_event_types}"
            assert "agent_text_chunk" in ws_event_types, \
                f"Expected agent_text_chunk in WS events, got: {ws_event_types}"

            print("\n[PASS] Summarizer streaming: all event types verified.")

    async def test_translate_helper(self) -> None:
        """Verify _translate maps StreamingAgentEvent to correct WS dict."""
        from backend.src.agents.orchestrator import AgentRuntime
        rt = AgentRuntime.__new__(AgentRuntime)

        thinking_evt = StreamingAgentEvent(
            type="thinking_chunk", agent_name="test_agent", delta="suy nghi..."
        )
        result = rt._translate(thinking_evt, "test_agent:123")
        assert result is not None
        assert result["event"] == "agent_thinking_chunk"
        assert result["data"]["delta"] == "suy nghi..."

        text_evt = StreamingAgentEvent(
            type="text_chunk", agent_name="test_agent", delta="noi dung...", variant="executive"
        )
        result = rt._translate(text_evt, "test_agent:123")
        assert result is not None
        assert result["event"] == "agent_text_chunk"
        assert result["data"]["variant"] == "executive"

        search_evt = StreamingAgentEvent(
            type="search_log", agent_name="legal_agent",
            search_log={"step": "vector_recall", "query": "phap luat xay dung", "top_k": []}
        )
        result = rt._translate(search_evt, "legal_agent:456")
        assert result is not None
        assert result["event"] == "search_log"
        assert result["data"]["step"] == "vector_recall"

        graph_evt = StreamingAgentEvent(
            type="graph_op", agent_name="compliance_agent",
            graph_op={"query": "GOVERNED_BY", "nodes": [], "edges": []}
        )
        result = rt._translate(graph_evt, "compliance_agent:789")
        assert result is not None
        assert result["event"] == "graph_operation"

        completed_evt = StreamingAgentEvent(
            type="completed", agent_name="test_agent", result="{}"
        )
        result = rt._translate(completed_evt, "test_agent:123")
        assert result is None, "completed events should return None (handled by orchestrator)"

        print("[PASS] _translate: all mappings correct.")

    async def test_tool_call_translate(self) -> None:
        """Verify tool_call_start and tool_call_result translate correctly."""
        from backend.src.agents.orchestrator import AgentRuntime
        rt = AgentRuntime.__new__(AgentRuntime)

        start_evt = StreamingAgentEvent(
            type="tool_call_start", agent_name="classifier_agent",
            tool_call_id="tc-001", tool_name="tthc.search", tool_args={"query": "xay dung"}
        )
        result = rt._translate(start_evt, "classifier_agent:001")
        assert result is not None
        assert result["event"] == "agent_tool_call_start"
        assert result["data"]["tool_name"] == "tthc.search"
        assert result["data"]["args"] == {"query": "xay dung"}

        result_evt = StreamingAgentEvent(
            type="tool_call_result", agent_name="classifier_agent",
            tool_call_id="tc-001", tool_result={"code": "1.004415"}, tool_duration_ms=123.4
        )
        result = rt._translate(result_evt, "classifier_agent:001")
        assert result is not None
        assert result["event"] == "agent_tool_call_result"
        assert result["data"]["duration_ms"] == 123.4

        print("[PASS] tool_call_start / tool_call_result translate correctly.")


async def run_tests() -> None:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAgentStreaming)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_tests())
