"""
backend/scripts/test_qwen_streaming.py
Standalone verification for QwenClient.stream_chat() + llm_cache.replay_as_chunks().

Run from the backend/ directory:
    cd /home/logan/GovTrack/backend
    python scripts/test_qwen_streaming.py

Tests:
  1. test_text_streaming    — live DashScope call, verify text_chunk + done events
  2. test_tool_call_streaming — live DashScope call with a dummy tool, verify
                               tool_call_delta + tool_call_finalized + done
  3. test_cache_replay      — offline replay from a pre-built cached response,
                               no DashScope key required

Tests 1 and 2 are skipped automatically when DASHSCOPE_API_KEY is not set.
Test 3 always runs (pure in-memory, no I/O).
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback

# Ensure the src/ package is importable when running from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Silence noisy startup warnings so test output is readable
os.environ.setdefault("DEMO_MODE", "false")
os.environ.setdefault("DEMO_CACHE_ENABLED", "false")


async def test_text_streaming() -> bool:
    """Verify that a simple text prompt yields text_chunk events followed by done."""
    from src.agents.qwen_client import QwenClient
    from src.agents.streaming import StreamEvent

    print("\n[1] test_text_streaming — live DashScope call")
    client = QwenClient()

    events: list[StreamEvent] = []
    async for event in await client.stream_chat(
        model="qwen-max-latest",
        messages=[{"role": "user", "content": "Xin chào, bạn là ai? Trả lời ngắn gọn."}],
        max_tokens=128,
    ):
        events.append(event)
        if event.type == "text_chunk":
            print(f"  text_chunk: {event.delta!r}")
        elif event.type == "thinking_chunk":
            print(f"  thinking_chunk: {repr(event.delta)[:60]}")
        elif event.type == "done":
            print(f"  done: finish_reason={event.finish_reason!r}, usage={event.usage}")
        elif event.type == "error":
            print(f"  ERROR: {event.error}")
            return False

    text_chunks = [e for e in events if e.type == "text_chunk"]
    done_events = [e for e in events if e.type == "done"]

    ok = len(text_chunks) >= 1 and len(done_events) == 1
    # done must be the final event
    ok = ok and events[-1].type == "done"
    print(f"  PASS={ok}  ({len(text_chunks)} text_chunk(s), done={len(done_events)})")
    return ok


async def test_tool_call_streaming() -> bool:
    """
    Verify that a tool-calling prompt yields:
      - At least one tool_call_delta
      - Exactly one tool_call_finalized with parsed args dict
      - A done event as the final event
    """
    from src.agents.qwen_client import QwenClient
    from src.agents.streaming import StreamEvent

    print("\n[2] test_tool_call_streaming — live DashScope call with dummy tool")
    client = QwenClient()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Lấy thông tin thời tiết cho một thành phố",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "Tên thành phố"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    events: list[StreamEvent] = []
    async for event in await client.stream_chat(
        model="qwen-max-latest",
        messages=[{"role": "user", "content": "Thời tiết Hà Nội hôm nay thế nào?"}],
        tools=tools,
        tool_choice="auto",
        max_tokens=256,
    ):
        events.append(event)
        if event.type == "tool_call_delta":
            print(f"  tool_call_delta: {event.tool_name!r} args_delta={event.tool_args_delta!r}")
        elif event.type == "tool_call_finalized":
            print(f"  tool_call_finalized: {event.tool_name!r} args={event.tool_args}")
        elif event.type == "text_chunk":
            print(f"  text_chunk: {event.delta!r}")
        elif event.type == "done":
            print(f"  done: finish_reason={event.finish_reason!r}, usage={event.usage}")
        elif event.type == "error":
            print(f"  ERROR: {event.error}")
            return False

    # The model may choose not to call the tool; that is a valid response.
    # Only assert structure: if tool_call_finalized exists, tool_call_delta >= 1.
    finalized = [e for e in events if e.type == "tool_call_finalized"]
    deltas = [e for e in events if e.type == "tool_call_delta"]
    done_events = [e for e in events if e.type == "done"]

    if finalized:
        # Tool was called — verify coalescing worked
        ok = (
            len(deltas) >= 1
            and len(finalized) >= 1
            and all(isinstance(e.tool_args, dict) for e in finalized)
            and events[-1].type == "done"
        )
        print(
            f"  Tool called: {len(deltas)} delta(s), {len(finalized)} finalized,"
            f" args parsed={[e.tool_args for e in finalized]}"
        )
    else:
        # Model answered directly — still valid, just check done
        ok = len(done_events) == 1 and events[-1].type == "done"
        print("  Model answered without tool call — also acceptable")

    print(f"  PASS={ok}")
    return ok


async def test_cache_replay() -> bool:
    """
    Verify replay_as_chunks() with a synthetic cached response (no API key needed).
    Checks ordering and event completeness for both text and tool-call variants.
    """
    from src.agents.llm_cache import replay_as_chunks
    from src.agents.streaming import StreamEvent

    print("\n[3] test_cache_replay — offline replay (no API key required)")

    # --- Sub-test A: text response replay ---
    cached_text = {
        "content": "Đây là câu trả lời mẫu từ cache.",
        "tool_calls": None,
        "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        "finish_reason": "stop",
    }
    text_events: list[StreamEvent] = []
    async for ev in replay_as_chunks(cached_text, chars_per_chunk=8, delay_ms=0):
        text_events.append(ev)

    text_chunks = [e for e in text_events if e.type == "text_chunk"]
    reconstructed = "".join(e.delta or "" for e in text_chunks)
    text_ok = (
        len(text_chunks) >= 1
        and reconstructed == cached_text["content"]
        and text_events[-1].type == "done"
        and text_events[-1].usage == cached_text["usage"]
    )
    print(f"  Sub-test A (text): PASS={text_ok}")
    if not text_ok:
        print(f"    reconstructed={reconstructed!r}")

    # --- Sub-test B: tool-call response replay ---
    cached_tool = {
        "content": None,
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "search_tthc",
                    "arguments": '{"query": "cấp phép xây dựng"}',
                },
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 15, "total_tokens": 35},
        "finish_reason": "tool_calls",
    }
    tool_events: list[StreamEvent] = []
    async for ev in replay_as_chunks(cached_tool, chars_per_chunk=8, delay_ms=0):
        tool_events.append(ev)

    tc_deltas = [e for e in tool_events if e.type == "tool_call_delta"]
    tc_finalized = [e for e in tool_events if e.type == "tool_call_finalized"]

    # All deltas should come BEFORE finalized for the same tool
    # and finalized args should be a parsed dict
    tool_ok = (
        len(tc_deltas) >= 1
        and len(tc_finalized) == 1
        and isinstance(tc_finalized[0].tool_args, dict)
        and tc_finalized[0].tool_name == "search_tthc"
        and tc_finalized[0].tool_args == {"query": "cấp phép xây dựng"}
        and tool_events[-1].type == "done"
    )
    print(f"  Sub-test B (tool_call): PASS={tool_ok}")
    if not tool_ok:
        print(f"    finalized={tc_finalized}")

    # --- Sub-test C: serialize_completion() format compatibility ---
    cached_compat = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": "Compat format OK",
                    "tool_calls": None,
                },
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    compat_events: list[StreamEvent] = []
    async for ev in replay_as_chunks(cached_compat, chars_per_chunk=8, delay_ms=0):
        compat_events.append(ev)

    compat_text = "".join(e.delta or "" for e in compat_events if e.type == "text_chunk")
    compat_ok = compat_text == "Compat format OK" and compat_events[-1].type == "done"
    print(f"  Sub-test C (compat format): PASS={compat_ok}")

    overall = text_ok and tool_ok and compat_ok
    print(f"  OVERALL PASS={overall}")
    return overall


async def main() -> None:
    has_api_key = bool(os.getenv("DASHSCOPE_API_KEY", "").strip())

    results: dict[str, bool | str] = {}

    if has_api_key:
        try:
            results["test_text_streaming"] = await test_text_streaming()
        except Exception:
            print("  EXCEPTION in test_text_streaming:")
            traceback.print_exc()
            results["test_text_streaming"] = False

        try:
            results["test_tool_call_streaming"] = await test_tool_call_streaming()
        except Exception:
            print("  EXCEPTION in test_tool_call_streaming:")
            traceback.print_exc()
            results["test_tool_call_streaming"] = False
    else:
        print("\n[1] test_text_streaming    — SKIPPED (no DASHSCOPE_API_KEY)")
        print("[2] test_tool_call_streaming — SKIPPED (no DASHSCOPE_API_KEY)")
        results["test_text_streaming"] = "SKIPPED"
        results["test_tool_call_streaming"] = "SKIPPED"

    try:
        results["test_cache_replay"] = await test_cache_replay()
    except Exception:
        print("  EXCEPTION in test_cache_replay:")
        traceback.print_exc()
        results["test_cache_replay"] = False

    print("\n" + "=" * 50)
    print("RESULTS:")
    all_pass = True
    for name, result in results.items():
        emoji = "OK" if result is True else ("SKIP" if result == "SKIPPED" else "FAIL")
        print(f"  [{emoji}] {name}")
        if result is False:
            all_pass = False
    print("=" * 50)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
