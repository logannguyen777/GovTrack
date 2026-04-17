"""
backend/src/agents/llm_cache.py
Deterministic file-based cache for Qwen/DashScope chat completions.

Used by QwenClient when demo_mode + demo_cache_enabled are ON. Enables offline
demo playback: the backend reads cached responses instead of calling DashScope.

Cache layout:
    {settings.demo_cache_dir}/<sha256>.json

Cache key = SHA256 of JSON(model, messages, sorted(tools)).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from ..config import settings
from .streaming import StreamEvent

logger = logging.getLogger("govflow.llm_cache")


def _cache_dir() -> Path:
    p = Path(settings.demo_cache_dir)
    if not p.is_absolute():
        # Resolve relative to the repo root (parent of backend/).
        # __file__ = backend/src/agents/llm_cache.py → parents[3] = repo root
        p = Path(__file__).resolve().parents[3] / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_key(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict] | None = None,
) -> str:
    """Deterministic SHA256 key over (model, messages, sorted tools)."""
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "tools": sorted(
                tools or [],
                key=lambda t: t.get("function", {}).get("name", ""),
            ),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached(key: str) -> dict | None:
    path = _cache_dir() / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Corrupt cache entry {key[:12]}: {e}")
        return None


def set_cached(key: str, data: dict) -> None:
    path = _cache_dir() / f"{key}.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def serialize_completion(completion) -> dict:
    """Serialize an openai ChatCompletion into a JSON-safe dict."""
    choices = []
    for c in completion.choices:
        msg = c.message
        tool_calls = None
        if getattr(msg, "tool_calls", None):
            tool_calls = [
                {
                    "id": tc.id,
                    "type": getattr(tc, "type", "function"),
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]
        choices.append(
            {
                "index": getattr(c, "index", 0),
                "finish_reason": c.finish_reason,
                "message": {
                    "role": msg.role,
                    "content": msg.content,
                    "tool_calls": tool_calls,
                },
            }
        )

    usage = getattr(completion, "usage", None)
    return {
        "id": getattr(completion, "id", "cached"),
        "model": getattr(completion, "model", ""),
        "choices": choices,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
            "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
        },
    }


async def replay_as_chunks(
    cached_response: dict,
    chars_per_chunk: int = 8,
    delay_ms: int = 12,
) -> AsyncIterator[StreamEvent]:
    """
    Simulate streaming chunks from a cached non-streaming response.

    This lets the demo run fully offline while still giving the UI the smooth
    token-by-token feel judges expect from a live Qwen3 call.  The same 8-char
    / 12ms cadence is used for both text and tool-call argument replay so
    timing is consistent regardless of response type.

    The cached_response dict uses the aggregate format written by
    stream_chat()'s write-through path:
      {"content": str|None, "tool_calls": list|None, "usage": dict, "finish_reason": str}

    It also accepts the richer serialize_completion() format (nested choices)
    because warm_cache.py may have written that variant before streaming was
    implemented.
    """
    delay_s = delay_ms / 1000.0

    # --- Normalise: accept both the aggregate stream format and the
    #     serialize_completion() format so warm_cache entries work too. ---
    if "choices" in cached_response:
        # serialize_completion() format → unwrap
        choice = cached_response["choices"][0] if cached_response["choices"] else {}
        msg = choice.get("message", {})
        content: str | None = msg.get("content")
        raw_tool_calls: list[dict] | None = msg.get("tool_calls")
        finish_reason: str = choice.get("finish_reason", "stop")
        usage: dict = cached_response.get("usage", {})
    else:
        # stream write-through format
        content = cached_response.get("content")
        raw_tool_calls = cached_response.get("tool_calls")
        finish_reason = cached_response.get("finish_reason", "stop")
        usage = cached_response.get("usage", {})

    # --- Replay tool-call arguments fragment by fragment ---
    if raw_tool_calls:
        for tc in raw_tool_calls:
            tc_id: str = tc.get("id", "replay-0")
            fn: dict = tc.get("function", {})
            name: str = fn.get("name", "unknown")
            args_str: str = fn.get("arguments", "{}")

            # Slice the raw JSON string to mimic DashScope arg streaming
            for i in range(0, len(args_str), chars_per_chunk):
                fragment = args_str[i : i + chars_per_chunk]
                yield StreamEvent(
                    type="tool_call_delta",
                    tool_call_id=tc_id,
                    tool_name=name,
                    tool_args_delta=fragment,
                )
                await asyncio.sleep(delay_s)

            # Emit finalized once all fragments for this tool call are done
            try:
                parsed_args = json.loads(args_str) if args_str else {}
            except json.JSONDecodeError:
                parsed_args = {"_raw": args_str}

            yield StreamEvent(
                type="tool_call_finalized",
                tool_call_id=tc_id,
                tool_name=name,
                tool_args=parsed_args,
            )

    # --- Replay text content character by character ---
    if content:
        for i in range(0, len(content), chars_per_chunk):
            yield StreamEvent(type="text_chunk", delta=content[i : i + chars_per_chunk])
            await asyncio.sleep(delay_s)

    yield StreamEvent(type="done", finish_reason=finish_reason, usage=usage)


def deserialize_completion(data: dict):
    """Reconstruct a ChatCompletion from a cached dict.

    Uses the real openai type classes so downstream code accessing
    `completion.usage.prompt_tokens`, `completion.choices[0].message.tool_calls`,
    etc. works without surprises.
    """
    from openai.types.chat import ChatCompletion
    from openai.types.chat.chat_completion import Choice
    from openai.types.chat.chat_completion_message import ChatCompletionMessage
    from openai.types.chat.chat_completion_message_tool_call import (
        ChatCompletionMessageToolCall,
        Function,
    )
    from openai.types.completion_usage import CompletionUsage

    choices = []
    for c in data["choices"]:
        m = c["message"]
        tool_calls = None
        if m.get("tool_calls"):
            tool_calls = [
                ChatCompletionMessageToolCall(
                    id=tc["id"],
                    type="function",
                    function=Function(
                        name=tc["function"]["name"],
                        arguments=tc["function"]["arguments"],
                    ),
                )
                for tc in m["tool_calls"]
            ]
        choices.append(
            Choice(
                index=c.get("index", 0),
                finish_reason=c.get("finish_reason", "stop"),
                message=ChatCompletionMessage(
                    role=m["role"],
                    content=m.get("content"),
                    tool_calls=tool_calls,
                ),
            )
        )

    u = data.get("usage", {})
    return ChatCompletion(
        id=data.get("id", "cached"),
        model=data.get("model", "qwen-max-latest"),
        object="chat.completion",
        created=0,
        choices=choices,
        usage=CompletionUsage(
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
        ),
    )
