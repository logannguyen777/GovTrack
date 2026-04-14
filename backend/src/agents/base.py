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
from dataclasses import dataclass, field
from typing import Any

from .mcp_server import get_mcp_registry
from .profile import AgentProfile, load_profile
from .qwen_client import QwenClient, TokenUsage

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

        # Broadcast start via WebSocket
        await self._broadcast(case_id, "agent_started", {
            "agent_name": self.profile.name,
            "step_id": step_id,
        })

        try:
            # Clearance cap enforcement: reject if case classification exceeds agent clearance
            from ..database import async_gremlin_submit as _gremlin
            try:
                cls_result = await _gremlin(
                    "g.V().has('Case', 'case_id', cid).values('current_classification')",
                    {"cid": case_id},
                )
                case_classification = int(cls_result[0]) if cls_result else 0
            except Exception:
                case_classification = 0  # Default to unclassified if not set

            if case_classification > self.profile.clearance_cap:
                logger.warning(
                    f"[{self.profile.name}] Clearance denied: case={case_classification} > cap={self.profile.clearance_cap}"
                )
                return AgentResult(
                    agent_name=self.profile.name, case_id=case_id,
                    status="failed", output="",
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

                # Check token budget
                if self.client.usage.total_tokens >= self.profile.max_tokens_budget:
                    logger.warning(f"[{self.profile.name}] Token budget exhausted")
                    break

                # Call Qwen
                completion = await self.client.chat(
                    messages=messages,
                    model=self.profile.model,
                    tools=tools if tools else None,
                )

                assistant_msg = completion.choices[0].message

                # Append assistant message to conversation
                messages.append({
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
                    ] if assistant_msg.tool_calls else None,
                })

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
                        return tc.id, fn_name, json.dumps({
                            "error": f"Invalid JSON in arguments: {e}. Please fix and retry."
                        })

                    logger.debug(f"[{self.profile.name}] Tool: {fn_name}({list(fn_args.keys())})")
                    result = await self.mcp.execute_tool(fn_name, fn_args, self.profile)
                    return tc.id, fn_name, result

                tool_results = await asyncio.gather(
                    *[_exec_one_tool(tc) for tc in assistant_msg.tool_calls]
                )

                for tc_id, fn_name, result in tool_results:
                    tool_calls_count += 1
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": result,
                    })
                    await self._broadcast(case_id, "tool_executed", {
                        "agent_name": self.profile.name,
                        "tool": fn_name,
                        "iteration": iteration + 1,
                    })

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
            await self._broadcast(case_id, "agent_completed", {
                "agent_name": self.profile.name,
                "step_id": step_id,
                "tool_calls": tool_calls_count,
                "duration_ms": round(duration_ms),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="completed",
                output=final_output,
                tool_calls_count=tool_calls_count,
                usage=usage,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            logger.error(f"[{self.profile.name}] Failed: {e}", exc_info=True)

            await self._log_step(
                step_id=step_id,
                case_id=case_id,
                action=f"pipeline_{self.profile.role}",
                usage=self.client.reset_usage(),
                duration_ms=duration_ms,
                status="failed",
                error=str(e),
            )

            await self._broadcast(case_id, "agent_failed", {
                "agent_name": self.profile.name,
                "error": str(e),
            })

            return AgentResult(
                agent_name=self.profile.name,
                case_id=case_id,
                status="failed",
                output="",
                usage=self.client.usage,
                duration_ms=duration_ms,
                error=str(e),
            )

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
        from ..database import async_gremlin_submit, pg_connection

        # GDB
        try:
            await async_gremlin_submit(
                "g.addV('AgentStep')"
                ".property('step_id', sid).property('agent_name', name)"
                ".property('action', action)"
                ".property('input_tokens', in_tok).property('output_tokens', out_tok)"
                ".property('duration_ms', dur).property('status', status)"
                ".as('step')"
                ".V().has('Case', 'case_id', cid).addE('PROCESSED_BY').to('step')",
                {
                    "sid": step_id, "name": self.profile.name,
                    "action": action, "in_tok": usage.input_tokens,
                    "out_tok": usage.output_tokens, "dur": int(duration_ms),
                    "status": status, "cid": case_id,
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
                    case_id, self.profile.name, int(duration_ms),
                    usage.input_tokens, usage.output_tokens,
                    usage.api_calls, status, error,
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
