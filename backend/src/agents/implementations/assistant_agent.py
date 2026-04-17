"""
backend/src/agents/implementations/assistant_agent.py
Citizen-facing chatbot agent. Streaming with tool calling.
Uses Qwen3-Max + PublicAssistantTools whitelist (no GDB exposure).
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from ...models.chat_schemas import ChatContext
from ..public_tools import PublicAssistantTools
from ..qwen_client import QwenClient

logger = logging.getLogger("govflow.agent.assistant")

_SYSTEM_PROMPT = (
    "Bạn là trợ lý AI của Cổng Dịch vụ công Việt Nam. "
    "Trả lời thân thiện, ngắn gọn, dùng tiếng Việt phổ thông "
    "(tránh thuật ngữ chuyên ngành nặng). "
    "Khi cần thông tin chính xác về thủ tục/luật, GỌI tool — đừng đoán. "
    "Khi người dân hỏi tra cứu hồ sơ, yêu cầu mã hồ sơ + 4 số cuối CCCD hoặc SĐT trước. "
    "Trả lời ngắn (tối đa 200 từ) và đề xuất hành động cụ thể "
    "(link nộp, bổ sung, tra cứu). "
    "Không bịa thông tin pháp luật. Nếu không chắc, hướng dẫn người dân liên hệ cơ quan."
)


class AssistantAgent:
    """
    Citizen chatbot agent. Streaming with tool calling loop.
    Iteration cap = 4 to prevent infinite loops on confused tool chains.
    """

    def __init__(
        self,
        qwen_client: QwenClient,
        tools: PublicAssistantTools,
        max_tool_iterations: int = 4,
    ):
        self.qwen = qwen_client
        self.tools = tools
        self.max_tool_iterations = max_tool_iterations

    async def stream_response(
        self,
        session_id: str,
        messages: list[dict],
        context: ChatContext,
        max_tool_iterations: int | None = None,
    ) -> AsyncIterator[dict]:
        """
        Stream response events for a chat turn.

        Emits dicts with 'type' field:
          {"type":"thinking","text":...}
          {"type":"tool_call","name":...,"args":...,"id":...}
          {"type":"tool_result","name":...,"result":...,"id":...}
          {"type":"text_delta","content":...}
          {"type":"citation","law_id":...,"article":...,"content":...}
          {"type":"suggestion","tthc_code":...,"name":...}
          {"type":"done","message_id":...,"content":...}
        """
        async for event in self._stream(session_id, messages, context, max_tool_iterations):
            yield event

    async def _stream(
        self,
        session_id: str,
        messages: list[dict],
        context: ChatContext,
        max_iterations: int | None,
    ) -> AsyncIterator[dict]:
        cap = max_iterations or self.max_tool_iterations
        message_id = str(uuid.uuid4())

        # Build full message list: system prompt + optional context inject + history
        system_msg = {"role": "system", "content": _SYSTEM_PROMPT}
        context_inject = _build_context_inject(context)
        full_messages: list[dict] = [system_msg]
        if context_inject:
            full_messages.append(context_inject)
        full_messages.extend(messages)

        tool_schemas = self.tools.schemas()

        # Accumulators for final message persistence
        _full_text: list[str] = []
        _all_tool_calls: list[dict] = []
        _citations: list[dict] = []
        _suggestions: list[dict] = []

        for iteration in range(cap):
            logger.debug(f"[AssistantAgent] session={session_id} iteration={iteration + 1}/{cap}")

            # Accumulators for this iteration's tool calls
            _pending_tool_calls: dict[str, dict] = {}  # id -> {name, args}
            _iter_text: list[str] = []
            _finish_reason: str | None = None

            async for event in self.qwen.stream_chat(
                model="reasoning",
                messages=full_messages,
                tools=tool_schemas,
                tool_choice="auto",
            ):
                etype = event.type

                if etype == "thinking_chunk" and event.delta:
                    yield {"type": "thinking", "text": event.delta}

                elif etype == "text_chunk" and event.delta:
                    _iter_text.append(event.delta)
                    _full_text.append(event.delta)
                    yield {"type": "text_delta", "content": event.delta}

                elif etype == "tool_call_finalized":
                    tc_id = event.tool_call_id or str(uuid.uuid4())
                    _pending_tool_calls[tc_id] = {
                        "name": event.tool_name or "",
                        "args": event.tool_args or {},
                    }
                    # Emit pre-execution event with parsed args
                    yield {
                        "type": "tool_call",
                        "id": tc_id,
                        "name": event.tool_name,
                        "args": event.tool_args or {},
                    }

                elif etype == "done":
                    _finish_reason = event.finish_reason

                elif etype == "error":
                    logger.error(f"[AssistantAgent] Stream error: {event.error}")
                    yield {"type": "error", "message": "Lỗi kết nối AI. Vui lòng thử lại."}
                    return

            # If no tool calls, we're done
            if not _pending_tool_calls:
                break

            # Append assistant turn (with tool_calls list)
            assistant_turn: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(_iter_text) or None,
                "tool_calls": [
                    {
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": info["name"],
                            "arguments": json.dumps(info["args"], ensure_ascii=False),
                        },
                    }
                    for tc_id, info in _pending_tool_calls.items()
                ],
            }
            full_messages.append(assistant_turn)
            _all_tool_calls.extend(
                [
                    {"id": k, "name": v["name"], "args": v["args"]}
                    for k, v in _pending_tool_calls.items()
                ]
            )

            # Execute tools sequentially (whitelist is IO-bound, parallel safe)
            for tc_id, info in _pending_tool_calls.items():
                tool_name = info["name"]
                tool_args = info["args"]
                result = await self.tools.execute(tool_name, tool_args)

                # Emit result event
                yield {
                    "type": "tool_result",
                    "id": tc_id,
                    "name": tool_name,
                    "result": result,
                }

                # Collect citations from search_law results
                if tool_name == "search_law" and isinstance(result, dict):
                    for item in result.get("results", []):
                        citation = {
                            "law_id": item.get("law_id", ""),
                            "article": item.get("article", ""),
                            "content": item.get("content", "")[:300],
                        }
                        _citations.append(citation)
                        yield {"type": "citation", **citation}

                # Collect TTHC suggestions from search_tthc results
                if tool_name == "search_tthc" and isinstance(result, dict):
                    for item in result.get("results", []):
                        sugg = {
                            "tthc_code": item.get("tthc_code", ""),
                            "name": item.get("name", ""),
                        }
                        _suggestions.append(sugg)
                        yield {"type": "suggestion", **sugg}

                # Append tool result to conversation
                full_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )

        # Final done event with aggregated content
        final_content = "".join(_full_text)
        yield {
            "type": "done",
            "message_id": message_id,
            "content": final_content,
            "tool_calls": _all_tool_calls,
            "citations": _citations,
        }


def _build_context_inject(context: ChatContext) -> dict | None:
    """Build a system-like user message to prime the AI with page context."""
    if context.type == "case" and context.ref:
        return {
            "role": "user",
            "content": (
                f"[Ngữ cảnh: Người dân đang xem hồ sơ mã {context.ref}. "
                "Ưu tiên trả lời liên quan đến hồ sơ này.]"
            ),
        }
    elif context.type == "submit" and context.ref:
        return {
            "role": "user",
            "content": (
                f"[Ngữ cảnh: Người dân đang chuẩn bị nộp hồ sơ thủ tục {context.ref}. "
                "Ưu tiên hướng dẫn chuẩn bị giấy tờ và quy trình nộp.]"
            ),
        }
    return None
