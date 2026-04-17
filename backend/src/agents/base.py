"""
backend/src/agents/base.py
Abstract base class for all GovFlow agents.
Implements the ReAct-style tool-calling loop:
  1. Send messages to Qwen
  2. Check for tool_calls in response
  3. Execute tools via MCP
  4. Append tool results to conversation
  5. Repeat until no more tool_calls or max iterations
  6. Log AgentStep to GDB + broadcast via WebSocket
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ..metrics import (
    cases_in_flight_dec,
    cases_in_flight_inc,
    record_agent_duration,
    record_tokens,
)
from .mcp_server import get_mcp_registry
from .profile import AgentProfile, load_profile
from .qwen_client import CircuitOpenError, QwenClient, TokenBudgetExceeded, TokenUsage
from .streaming import StreamingAgentEvent

if TYPE_CHECKING:
    from ..auth import UserSession

logger = logging.getLogger("govflow.agent")


@dataclass
class AgentResult:
    """Result of an agent run."""

    agent_name: str
    case_id: str
    status: str  # completed | failed
    output: str  # Final text output from the agent
    tool_calls_count: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)
    duration_ms: float = 0
    error: str | None = None


class BaseAgent(ABC):
    """
    Abstract base class for GovFlow agents.

    Subclasses must implement:
        - build_messages(case_id) -> list[dict]
            Build the initial message list (system + user messages with case context).

    The tool-calling loop, MCP integration, logging, and WebSocket broadcast
    are handled by the base class.
    """

    def __init__(self, profile_name: str | None = None):
        """
        Initialize the agent.

        Args:
            profile_name: Name of the YAML profile file (without extension).
                         If None, uses the class attribute `profile_name`.
        """
        name = profile_name or getattr(self, "profile_name", self.__class__.__name__.lower())
        self.profile: AgentProfile = load_profile(name)
        self.client: QwenClient = QwenClient()
        self.mcp = get_mcp_registry()
        # Set by orchestrator before calling run_streaming so events are forwarded to WS
        self._event_emitter: Callable[[StreamingAgentEvent], Awaitable[None]] | None = None
        # Set by orchestrator to propagate the caller's session to GDB calls
        self._session: UserSession | None = None
        # Set by orchestrator to convey case_type context (citizen_tthc | internal_dispatch)
        self._case_type: str = "citizen_tthc"

    def _get_gdb(self):
        """Return a PermittedGremlinClient for this agent's GDB calls.

        Uses the caller session propagated by the orchestrator when available;
        otherwise falls back to SYSTEM_SESSION so internal / maintenance calls
        are still audited distinctly.
        """
        from ..auth import SYSTEM_SESSION
        from ..graph.permitted_client import PermittedGremlinClient

        session = self._session if self._session is not None else SYSTEM_SESSION
        return PermittedGremlinClient(session)

    @abstractmethod
    async def build_messages(self, case_id: str) -> list[dict[str, Any]]:
        """
        Build the initial conversation messages for the agent.

        Returns OpenAI-format messages, typically:
        [
            {"role": "system", "content": self.profile.system_prompt},
            {"role": "user", "content": "<case context and instructions>"},
        ]
        """
        ...

    async def run(self, case_id: str) -> AgentResult:
        """
        Execute the agent's tool-calling loop on a case.

        This is the main entry point called by the Orchestrator.
        """
        start_time = time.monotonic()
        step_id = str(uuid.uuid4())
        tool_calls_count = 0

        logger.info(f"[{self.profile.name}] Starting on case {case_id}")
        cases_in_flight_inc()

        # Broadcast start via WebSocket
        await self._broadcast(
            case_id,
            "agent_started",
            {
                "agent_name": self.profile.name,
                "step_id": step_id,
            },
        )

        try:
            # Clearance cap enforcement: reject if case classification exceeds agent clearance
            gdb = self._get_gdb()
            try:
                cls_result = await gdb.execute(
                    "g.V().has('Case', 'case_id', cid).values('current_classification')",
                    {"cid": case_id},
                )
                first = cls_result[0] if cls_result else {}
                raw_cls = first.get("value", 0) if isinstance(first, dict) else first
                case_classification = int(raw_cls) if raw_cls else 0
            except Exception:
                case_classification = 0  # Default to unclassified if not set

            if case_classification > self.profile.clearance_cap:
                logger.warning(
                    f"[{self.profile.name}] Clearance denied: case={case_classification} > cap={self.profile.clearance_cap}"
                )
                return AgentResult(
                    agent_name=self.profile.name,
                    case_id=case_id,
                    status="failed",
                    output="",
                    error=f"Clearance insufficient: case level {case_classification} exceeds agent cap {self.profile.clearance_cap}",
                )

            # Build initial messages
            messages = await self.build_messages(case_id)

            # Get tools available for this agent
            tools = self.mcp.get_tools_for_profile(self.profile)

            # Tool-calling loop
            for iteration in range(self.profile.max_iterations):
                logger.debug(
                    f"[{self.profile.name}] Iteration {iteration + 1}/{self.profile.max_iterations}"
                )

                # ── Token budget PRE-CHECK ────────────────────────────────
                # Estimate tokens for the current message list (rough heuristic:
                # total chars / 4) and compare against the remaining budget.
                estimated_prompt_tokens = sum(
                    len(str(m.get("content") or "")) // 4 for m in messages
                )
                projected_total = self.client.usage.total_tokens + estimated_prompt_tokens
                if projected_total >= self.profile.max_tokens_budget:
                    raise TokenBudgetExceeded(
                        f"[{self.profile.name}] Token budget would be exceeded: "
                        f"projected={projected_total} >= budget={self.profile.max_tokens_budget}"
                    )

                # Call Qwen
                completion = await self.client.chat(
                    messages=messages,
                    model=self.profile.model,
                    tools=tools if tools else None,
                )

                assistant_msg = completion.choices[0].message

                # Append assistant message to conversation
                messages.append(
                    {
                        "role": "assistant",
                        "content": assistant_msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in (assistant_msg.tool_calls or [])
                        ]
                        if assistant_msg.tool_calls
                        else None,
                    }
                )

                # If no tool calls, agent is done
                if not assistant_msg.tool_calls:
                    logger.info(f"[{self.profile.name}] Completed (no more tool calls)")
                    break

                # Execute all tool calls in parallel
                async def _exec_one_tool(tc):
                    fn_name = tc.function.name
                    try:
                        fn_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        logger.warning(f"[{self.profile.name}] Bad tool args: {e}")
                        return (
                            tc.id,
                            fn_name,
                            json.dumps(
                                {"error": f"Invalid JSON in arguments: {e}. Please fix and retry."}
                            ),
                        )

                    logger.debug(f"[{self.profile.name}] Tool: {fn_name}({list(fn_args.keys())})")
                    result = await self.mcp.execute_tool(fn_name, fn_args, self.profile)
                    return tc.id, fn_name, result

                tool_results = await asyncio.gather(
                    *[_exec_one_tool(tc) for tc in assistant_msg.tool_calls]
                )

                for tc_id, fn_name, result in tool_results:
                    tool_calls_count += 1
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc_id,
                            "content": result,
                        }
                    )
                    await self._broadcast(
                        case_id,
                        "tool_executed",
                        {
                            "agent_name": self.profile.name,
                            "tool": fn_name,
                            "iteration": iteration + 1,
                        },
                    )

                # Sliding window: keep system message + last 30 messages to prevent unbounded growth
                if len(messages) > 40:
                    messages = [messages[0]] + messages[-30:]

            # Extract final output
            final_output = ""
            for msg in reversed(messages):
                if msg["role"] == "assistant" and msg.get("content"):
                    final_output = msg["content"]
                    break

            duration_ms = (time.monotonic() - start_time) * 1000
            usage = self.client.reset_usage()

            # Log AgentStep to GDB
            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action=f"pipeline_{self.profile.role}",
                usage=usage,
                duration_ms=duration_ms,
                status="completed",
            )

            # Broadcast completion
            await self._broadcast(
                case_id,
                "agent_completed",
                {
                    "agent_name": self.profile.name,
                    "step_id": step_id,
                    "tool_calls": tool_calls_count,
                    "duration_ms": round(duration_ms),
                },
            )

            # Prometheus: record duration + token usage
            record_agent_duration(self.profile.name, "completed", duration_ms / 1000)
            record_tokens(self.profile.model, usage.input_tokens, usage.output_tokens)
            cases_in_flight_dec()

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=final_output,
                tool_calls_count=tool_calls_count,
                usage=usage,
                duration_ms=duration_ms,
            )

        except TokenBudgetExceeded as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.warning(f"[{self.profile.name}] Token budget exceeded: {e}")

            _budget_usage = self.client.reset_usage()
            record_agent_duration(self.profile.name, "token_budget_exceeded", duration_ms / 1000)
            record_tokens(
                self.profile.model, _budget_usage.input_tokens, _budget_usage.output_tokens
            )
            cases_in_flight_dec()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action=f"pipeline_{self.profile.role}",
                usage=_budget_usage,
                duration_ms=duration_ms,
                status="failed",
                error="token_budget_exceeded",
            )

            await self._broadcast(
                case_id,
                "agent_failed",
                {
                    "agent_name": self.profile.name,
                    "error": "token_budget_exceeded",
                },
            )

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                usage=_budget_usage,
                duration_ms=duration_ms,
                error="token_budget_exceeded",
            )

        except (CircuitOpenError,) as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.warning(f"[{self.profile.name}] Circuit open: {e}")

            _circuit_usage = self.client.reset_usage()
            record_agent_duration(self.profile.name, "circuit_open", duration_ms / 1000)
            record_tokens(
                self.profile.model, _circuit_usage.input_tokens, _circuit_usage.output_tokens
            )
            cases_in_flight_dec()

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                usage=_circuit_usage,
                duration_ms=duration_ms,
                error="dashscope_circuit_open",
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[{self.profile.name}] Failed: {e}", exc_info=True)

            _exc_usage = self.client.reset_usage()
            record_agent_duration(self.profile.name, "failed", duration_ms / 1000)
            record_tokens(self.profile.model, _exc_usage.input_tokens, _exc_usage.output_tokens)
            cases_in_flight_dec()

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action=f"pipeline_{self.profile.role}",
                usage=_exc_usage,
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

            await self._broadcast(
                case_id,
                "agent_failed",
                {
                    "agent_name": self.profile.name,
                    "error": str(e),
                },
            )

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                usage=_exc_usage,
                duration_ms=duration_ms,
                error=str(e),
            )

    # ------------------------------------------------------------------ #
    # Streaming API                                                        #
    # ------------------------------------------------------------------ #

    async def run_streaming(self, case_id: str) -> AsyncIterator[StreamingAgentEvent]:
        """
        Default implementation: call run() then yield a single 'completed' event.

        Agents that support token-by-token streaming (Summarizer, Drafter,
        Consult) override this method and yield StreamingAgentEvent objects
        from _stream_qwen callbacks.  The orchestrator always calls
        run_streaming() so it gets a uniform async-generator interface.
        """
        result = await self.run(case_id)
        if result.status == "completed":
            yield StreamingAgentEvent(
                type="completed",
                agent_name=self.profile.name,
                result=result.output,
            )
        else:
            yield StreamingAgentEvent(
                type="failed",
                agent_name=self.profile.name,
                error=result.error,
            )

    async def _emit(self, event_type: str, **payload: Any) -> None:
        """
        Emit a StreamingAgentEvent via the orchestrator-injected event emitter.
        No-op when running outside the streaming orchestrator path.
        """
        if self._event_emitter is None:
            return
        try:
            await self._event_emitter(
                StreamingAgentEvent(
                    type=event_type,  # type: ignore[arg-type]
                    agent_name=self.profile.name,
                    **payload,
                )
            )
        except Exception as exc:
            logger.debug(f"[{self.profile.name}] _emit failed (non-critical): {exc}")

    async def _stream_qwen(
        self,
        *,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        on_thinking: Callable[[str], Awaitable[None]] | None = None,
        on_text: Callable[[str], Awaitable[None]] | None = None,
        on_tool_call_finalized: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        """
        Wrap QwenClient.stream_chat(), aggregate tool calls and text, fire
        per-event callbacks, and return the final aggregated response dict:
            {"content": str, "tool_calls": list[dict], "usage": dict | None}

        If stream_chat() raises (e.g. network error) the method falls back to
        QwenClient.chat() and synthesises callbacks from the non-stream response
        so the caller always gets a complete result.
        """

        content_parts: list[str] = []
        tool_calls_out: list[dict] = []
        usage_out: dict | None = None

        try:
            async for event in self.client.stream_chat(
                model=model,
                messages=messages,
                tools=tools,
            ):
                if event.type == "thinking_chunk" and event.delta:
                    if on_thinking:
                        await on_thinking(event.delta)

                elif event.type == "text_chunk" and event.delta:
                    content_parts.append(event.delta)
                    if on_text:
                        await on_text(event.delta)

                elif event.type == "tool_call_finalized":
                    tc = {
                        "id": event.tool_call_id,
                        "name": event.tool_name,
                        "args": event.tool_args or {},
                    }
                    tool_calls_out.append(tc)
                    if on_tool_call_finalized:
                        await on_tool_call_finalized(tc)

                elif event.type == "done":
                    usage_out = event.usage

                elif event.type == "error":
                    logger.warning(f"[{self.profile.name}] stream_chat error event: {event.error}")
                    # Fall through — may still have partial content

        except Exception as exc:
            logger.warning(
                f"[{self.profile.name}] stream_chat raised ({exc}), "
                "falling back to non-streaming chat()"
            )
            # Graceful degradation: non-streaming fallback
            completion = await self.client.chat(
                messages=messages,
                model=model,
                tools=tools if tools else None,
            )
            msg = completion.choices[0].message
            content = msg.content or ""
            if content:
                content_parts.append(content)
                if on_text:
                    await on_text(content)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    parsed: dict = {}
                    try:
                        parsed = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        parsed = {"_raw": tc.function.arguments}
                    entry = {"id": tc.id, "name": tc.function.name, "args": parsed}
                    tool_calls_out.append(entry)
                    if on_tool_call_finalized:
                        await on_tool_call_finalized(entry)
            if completion.usage:
                usage_out = {
                    "prompt_tokens": completion.usage.prompt_tokens,
                    "completion_tokens": completion.usage.completion_tokens,
                    "total_tokens": completion.usage.total_tokens,
                }

        return {
            "content": "".join(content_parts),
            "tool_calls": tool_calls_out,
            "usage": usage_out,
        }

    async def _log_step(
        self,
        step_id: str,
        case_id: str,
        action: str,
        usage: TokenUsage,
        duration_ms: float,
        status: str,
        error: str | None = None,
    ) -> None:
        """Log an AgentStep vertex in GDB and a row in analytics_agents."""
        from ..database import pg_connection

        # GDB
        try:
            gdb = self._get_gdb()
            await gdb.execute(
                "g.addV('AgentStep')"
                ".property('step_id', sid).property('agent_name', name)"
                ".property('action', action)"
                ".property('input_tokens', in_tok).property('output_tokens', out_tok)"
                ".property('duration_ms', dur).property('status', status)"
                ".property('started_at', started_at)"
                # System metadata — not sensitive data; always readable by callers
                # with sufficient clearance to view the parent Case.
                ".property('classification', 0)"
                ".as('step')"
                ".V().has('Case', 'case_id', cid).addE('PROCESSED_BY').to('step')",
                {
                    "sid": step_id,
                    "name": self.profile.name,
                    "action": action,
                    "in_tok": usage.input_tokens,
                    "out_tok": usage.output_tokens,
                    "dur": int(duration_ms),
                    "status": status,
                    "cid": case_id,
                    "started_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as e:
            logger.warning(f"Failed to log GDB AgentStep: {e}")

        # Hologres analytics
        try:
            async with pg_connection() as conn:
                await conn.execute(
                    "INSERT INTO analytics_agents "
                    "(case_id, agent_name, duration_ms, input_tokens, output_tokens, "
                    "tool_calls, status, error_message) "
                    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
                    case_id,
                    self.profile.name,
                    int(duration_ms),
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.api_calls,
                    status,
                    error,
                )
        except Exception as e:
            logger.warning(f"Failed to log analytics_agents: {e}")

    async def _broadcast(self, case_id: str, event: str, data: dict) -> None:
        """Broadcast an event via WebSocket."""
        try:
            from ..api.ws import broadcast

            await broadcast(f"case:{case_id}", {"event": event, "data": data})
        except Exception as e:
            logger.debug(f"WS broadcast failed (non-critical): {e}")
