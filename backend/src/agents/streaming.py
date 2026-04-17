"""
backend/src/agents/streaming.py
Shared streaming event types for QwenClient.stream_chat() output and
agent-level streaming events forwarded via WebSocket.

Kept in a dedicated leaf module to break the potential circular import:
  qwen_client → llm_cache → (needs StreamEvent) → qwen_client
Both qwen_client and llm_cache import from here; neither imports the other
for StreamEvent.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

StreamEventType = Literal[
    "thinking_chunk",
    "text_chunk",
    "tool_call_delta",
    "tool_call_finalized",
    "done",
    "error",
]


class StreamEvent(BaseModel):
    """
    Unified streaming event emitted by QwenClient.stream_chat()
    and replayed by llm_cache.replay_as_chunks().

    UI consumers should switch on `type`:
      - thinking_chunk / text_chunk  → append `delta` to display buffer
      - tool_call_delta              → show typing animation for tool args
      - tool_call_finalized          → render ToolCallCard with parsed args
      - done                         → close stream, render usage stats
      - error                        → show error banner, allow retry
    """

    type: StreamEventType

    # Incremental text payload (thinking_chunk, text_chunk)
    delta: str | None = None

    # Tool-call identity (tool_call_delta, tool_call_finalized)
    tool_call_id: str | None = None
    tool_name: str | None = None

    # Raw string fragment as it streams in (tool_call_delta only)
    tool_args_delta: str | None = None

    # Fully-parsed arguments dict; populated after finish_reason=='tool_calls'
    # (tool_call_finalized only)
    tool_args: dict | None = None

    # Terminal event metadata
    finish_reason: str | None = None  # done
    usage: dict | None = None  # done
    error: str | None = None  # error


# ---------------------------------------------------------------------------
# Agent-level streaming events (superset of StreamEvent, with agent context)
# ---------------------------------------------------------------------------

StreamingAgentEventType = Literal[
    "thinking_chunk",
    "tool_call_start",
    "tool_call_result",
    "text_chunk",
    "search_log",
    "graph_op",
    "completed",
    "failed",
]


class StreamingAgentEvent(BaseModel):
    """
    Agent-aware streaming event yielded by BaseAgent.run_streaming() and
    forwarded via WebSocket to the frontend artifact panel.

    Consumers switch on `type`:
      thinking_chunk   → Thinking tab: append delta token-by-token
      tool_call_start  → Tool Calls tab: show card (pre-execution, args parsed)
      tool_call_result → Tool Calls tab: fill result + duration
      text_chunk       → Artifact panel: stream document/summary being drafted
      search_log       → Search Logs tab: vector recall / rerank stats
      graph_op         → Graph Operations tab: Gremlin query + result nodes
      completed        → terminal — result payload
      failed           → terminal — error payload
    """

    type: StreamingAgentEventType

    # Agent context (set by BaseAgent._stream_qwen / _emit)
    agent_name: str | None = None

    # Incremental text (thinking_chunk, text_chunk)
    delta: str | None = None

    # Metadata for text_chunk to distinguish parallel streams
    # e.g. "executive" | "staff" | "citizen" in Summarizer
    variant: str | None = None

    # Tool-call fields
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_args: dict | None = None
    tool_result: Any | None = None
    tool_duration_ms: float | None = None

    # Search log payload — emitted by LegalLookup after each pipeline step
    # {"step": "vector_recall", "query": ..., "top_k": [...], "reranked": [...], "citations_kept": [...]}
    search_log: dict | None = None

    # Graph operation payload — emitted by LegalLookup / Compliance
    # {"query": ..., "nodes": [...], "edges": [...]}
    graph_op: dict | None = None

    # Terminal payloads
    result: Any | None = None
    error: str | None = None
