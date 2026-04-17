"""
backend/src/agents/qwen_client.py
OpenAI-compatible async client for Alibaba DashScope (Qwen models).
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import settings
from . import llm_cache
from .streaming import StreamEvent

logger = logging.getLogger("govflow.qwen")

# ── Custom exceptions ─────────────────────────────────────────────────────

class TokenBudgetExceeded(RuntimeError):
    """Raised when the projected token usage would exceed the configured budget."""


class CircuitOpenError(RuntimeError):
    """Raised when the DashScope circuit breaker is in open state."""

# Model routing table — resolved from settings (env-overridable)
MODELS = {
    "reasoning_max": settings.qwen_reasoning_max,
    "reasoning": settings.qwen_reasoning,
    "reasoning_lite": settings.qwen_reasoning_lite,
    "vision": settings.qwen_vision,
    "vision_max": settings.qwen_vision_max,
    "embedding": "text-embedding-v3",
}

# Default parameters per model
MODEL_DEFAULTS = {
    "qwen-max-latest": {"max_tokens": 4096, "temperature": 0.3},
    "qwen-plus-latest": {"max_tokens": 2048, "temperature": 0.3},
    "qwen-turbo-latest": {"max_tokens": 1024, "temperature": 0.2},
    "qwen-vl-max-latest": {"max_tokens": 2048, "temperature": 0.1},
    "qwen-vl-plus-latest": {"max_tokens": 1536, "temperature": 0.1},
}


@dataclass
class TokenUsage:
    """Accumulated token usage for a session."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    api_calls: int = 0
    total_latency_ms: float = 0

    def add(self, completion: ChatCompletion, latency_ms: float) -> None:
        if completion.usage:
            self.input_tokens += completion.usage.prompt_tokens
            self.output_tokens += completion.usage.completion_tokens
            self.total_tokens += completion.usage.total_tokens
        self.api_calls += 1
        self.total_latency_ms += latency_ms


@dataclass
class QwenClient:
    """
    Async wrapper around OpenAI client for DashScope.
    Provides model routing, token tracking, adaptive timeouts,
    429 Retry-After handling, and a circuit breaker.
    """

    client: AsyncOpenAI = field(default=None)
    usage: TokenUsage = field(default_factory=TokenUsage)
    max_retries: int = 3

    # ── Circuit breaker state (per-instance) ─────────────────────
    # Protected by _cb_lock
    _cb_failure_timestamps: list[float] = field(default_factory=list)
    _cb_open_until: float = field(default=0.0)  # epoch seconds
    _cb_window_s: float = field(default=60.0)    # rolling window
    _cb_threshold: int = field(default=5)        # failures to open
    _cb_open_duration_s: float = field(default=300.0)
    _cb_half_open_allowed: bool = field(default=False)
    _cb_lock: asyncio.Lock = field(default=None)

    def __post_init__(self):
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=settings.dashscope_api_key,
                base_url=settings.dashscope_base_url,
                timeout=120.0,
            )
        if self._cb_lock is None:
            self._cb_lock = asyncio.Lock()

    # ── Task-type → timeout mapping ──────────────────────────────

    @staticmethod
    def _timeout_for_task(task_type: str) -> float:
        """Return the configured timeout (seconds) for the given task type."""
        mapping = {
            "vision": settings.qwen_timeout_vision_s,
            "reasoning": settings.qwen_timeout_reasoning_s,
            "embedding": settings.qwen_timeout_embedding_s,
        }
        return float(mapping.get(task_type, settings.qwen_timeout_reasoning_s))

    # ── Circuit breaker helpers ───────────────────────────────────

    async def _cb_check(self) -> None:
        """Raise CircuitOpenError if the circuit is open."""
        async with self._cb_lock:
            now = time.monotonic()
            if now < self._cb_open_until:
                if not self._cb_half_open_allowed:
                    raise CircuitOpenError("dashscope_circuit_open")
            # Clean stale timestamps outside the rolling window
            cutoff = now - self._cb_window_s
            self._cb_failure_timestamps = [
                t for t in self._cb_failure_timestamps if t > cutoff
            ]

    async def _cb_record_failure(self) -> None:
        """Record a failure and open the circuit if threshold is reached."""
        async with self._cb_lock:
            now = time.monotonic()
            self._cb_failure_timestamps.append(now)
            # Clean stale entries
            cutoff = now - self._cb_window_s
            self._cb_failure_timestamps = [
                t for t in self._cb_failure_timestamps if t > cutoff
            ]
            if len(self._cb_failure_timestamps) >= self._cb_threshold:
                self._cb_open_until = now + self._cb_open_duration_s
                self._cb_half_open_allowed = False
                logger.error(
                    f"[QwenClient] Circuit opened after {len(self._cb_failure_timestamps)} "
                    f"failures in {self._cb_window_s}s — pausing for {self._cb_open_duration_s}s"
                )

    async def _cb_record_success(self) -> None:
        """Reset failure state on a successful call."""
        async with self._cb_lock:
            self._cb_failure_timestamps.clear()
            self._cb_open_until = 0.0
            self._cb_half_open_allowed = False

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        task_type: Literal["vision", "reasoning", "embedding"] = "reasoning",
        **kwargs,
    ) -> ChatCompletion:
        """
        Send a chat completion request.

        Args:
            messages:   OpenAI-format messages
            model:      Model ID or alias (reasoning/vision). Defaults to reasoning.
            tools:      OpenAI-format tool definitions
            tool_choice: "auto", "none", or "required"
            task_type:  Controls the per-call timeout (vision=180s, reasoning=120s).
            **kwargs:   Additional parameters (temperature, max_tokens, etc.)
        """
        # ── Circuit breaker check ──────────────────────────────────
        await self._cb_check()

        # Resolve model alias
        resolved_model = MODELS.get(model, model) or MODELS["reasoning"]

        # Apply defaults
        params = {**MODEL_DEFAULTS.get(resolved_model, {}), **kwargs}

        timeout = self._timeout_for_task(task_type)

        request_kwargs = {
            "model": resolved_model,
            "messages": messages,
            **params,
        }

        if tools:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = tool_choice

        # --- Demo cache check (before network call) ---
        use_cache = settings.demo_mode and settings.demo_cache_enabled
        cache_k: str | None = None
        if use_cache:
            cache_k = llm_cache.cache_key(resolved_model, messages, tools)
            cached = llm_cache.get_cached(cache_k)
            if cached is not None:
                completion = llm_cache.deserialize_completion(cached)
                # Still track usage so stats reflect cached responses
                self.usage.add(completion, latency_ms=0.0)
                logger.debug(f"Qwen cache HIT {cache_k[:12]} ({resolved_model})")
                try:
                    from ..services.activity_broadcaster import fire as _ab_fire
                    _ab_fire(
                        "cache",
                        f"LLM cache HIT: {resolved_model}",
                        detail="offline-ready",
                        model=resolved_model,
                    )
                except Exception:
                    pass
                return completion
            if settings.demo_cache_offline_only:
                raise RuntimeError(f"Cache miss in offline mode: {cache_k[:16]} ({resolved_model})")

        # Retry loop — max_retries total; 429 uses Retry-After; others use backoff
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                start = time.monotonic()
                # Apply per-task timeout via asyncio.wait_for
                completion = await asyncio.wait_for(
                    self.client.chat.completions.create(**request_kwargs),
                    timeout=timeout,
                )
                latency = (time.monotonic() - start) * 1000

                self.usage.add(completion, latency)

                # OTel span for this successful call attempt
                try:
                    from ..telemetry import get_tracer as _get_tracer

                    _u = completion.usage
                    _tracer = _get_tracer("govflow.dashscope")
                    with _tracer.start_as_current_span(
                        "dashscope.chat",
                        attributes={
                            "model": resolved_model,
                            "task_type": task_type,
                            "tokens_in": (_u.prompt_tokens if _u else 0),
                            "tokens_out": (_u.completion_tokens if _u else 0),
                        },
                    ):
                        pass  # span recorded retroactively
                except Exception:
                    pass

                logger.debug(
                    f"Qwen {resolved_model}: {completion.usage.prompt_tokens}in/"
                    f"{completion.usage.completion_tokens}out, {latency:.0f}ms"
                )

                # Write-through cache
                if use_cache and cache_k:
                    try:
                        llm_cache.set_cached(cache_k, llm_cache.serialize_completion(completion))
                    except Exception as cache_err:
                        logger.warning(f"Cache write failed for {cache_k[:12]}: {cache_err}")

                # Broadcast stack-level activity (no PII — just model + tokens)
                try:
                    from ..services.activity_broadcaster import fire as _ab_fire
                    _u = completion.usage
                    _detail = (
                        f"tokens {_u.prompt_tokens}/{_u.completion_tokens}"
                        if _u else ""
                    )
                    _ab_fire(
                        "llm",
                        f"{resolved_model}: chat completion",
                        detail=_detail,
                        duration_ms=latency,
                        model=resolved_model,
                    )
                except Exception:
                    pass

                await self._cb_record_success()
                return completion

            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                raise  # Never retry these — allow graceful shutdown

            except openai.RateLimitError as e:
                # 429: read Retry-After header; default 30s
                retry_after = 30
                try:
                    if hasattr(e, "response") and e.response is not None:
                        ra_header = e.response.headers.get("retry-after") or e.response.headers.get("Retry-After")
                        if ra_header:
                            retry_after = int(ra_header)
                except Exception:
                    pass

                last_error = e
                await self._cb_record_failure()
                logger.warning(
                    f"Qwen 429 RateLimitError (attempt {attempt + 1}/{self.max_retries}), "
                    f"sleeping {retry_after}s"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(retry_after)

            except Exception as e:
                last_error = e
                await self._cb_record_failure()
                logger.warning(f"Qwen API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = (1.0 * (attempt + 1)) + random.uniform(0, 1.0)
                    await asyncio.sleep(delay)  # Backoff with jitter

        raise RuntimeError(f"Qwen API failed after {self.max_retries} retries: {last_error}")

    async def embed(self, texts: list[str], dimensions: int = 1024) -> list[list[float]]:
        """Get embeddings for a batch of texts."""
        await self._cb_check()

        timeout = self._timeout_for_task("embedding")
        start = time.monotonic()
        try:
            response = await asyncio.wait_for(
                self.client.embeddings.create(
                    model=MODELS["embedding"],
                    input=texts,
                    dimensions=dimensions,
                ),
                timeout=timeout,
            )
        except Exception:
            await self._cb_record_failure()
            raise

        latency = (time.monotonic() - start) * 1000
        await self._cb_record_success()

        # OTel span
        try:
            from ..telemetry import get_tracer as _get_tracer

            with _get_tracer("govflow.dashscope").start_as_current_span(
                "dashscope.embed",
                attributes={
                    "model": MODELS["embedding"],
                    "input_count": len(texts),
                    "tokens_in": getattr(getattr(response, "usage", None), "prompt_tokens", 0),
                },
            ):
                pass
        except Exception:
            pass

        self.usage.api_calls += 1
        self.usage.total_latency_ms += latency
        # Embedding API reports token usage differently
        if hasattr(response, "usage") and response.usage:
            self.usage.input_tokens += response.usage.prompt_tokens

        logger.debug(f"Qwen embedding: {len(texts)} texts, {latency:.0f}ms")
        return [item.embedding for item in response.data]

    async def vision(
        self,
        prompt: str,
        image_urls: list[str],
        **kwargs,
    ) -> ChatCompletion:
        """Send a vision request with images."""
        content: list[dict] = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": url},
                }
            )

        messages = [{"role": "user", "content": content}]
        return await self.chat(messages, model="vision", **kwargs)

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict = "auto",
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream a chat completion from DashScope with stream=True.

        Yields StreamEvent objects.  Consumers should switch on event.type:
          text_chunk / thinking_chunk → incremental display
          tool_call_delta             → show tool-arg typing animation
          tool_call_finalized         → render ToolCallCard (args fully parsed)
          done                        → terminal event with usage stats
          error                       → non-fatal; stream stops after this

        Tool-call coalescing rationale: the OpenAI streaming protocol delivers
        function.arguments as raw string fragments across many deltas.  We must
        accumulate the full string before json.loads() — emitting the raw
        fragments as tool_call_delta lets the UI show a typing effect while we
        buffer, and tool_call_finalized arrives with the parsed dict once
        finish_reason == "tool_calls".
        """
        resolved_model = MODELS.get(model, model) or MODELS["reasoning"]

        # --- Demo cache check (same key as non-stream path) ---
        use_cache = settings.demo_mode and settings.demo_cache_enabled
        cache_k: str | None = None
        if use_cache:
            cache_k = llm_cache.cache_key(resolved_model, messages, tools)
            cached = llm_cache.get_cached(cache_k)
            if cached is not None:
                logger.debug(f"Qwen stream cache HIT {cache_k[:12]} ({resolved_model})")
                async for event in llm_cache.replay_as_chunks(cached):
                    yield event
                return
            if settings.demo_cache_offline_only:
                yield StreamEvent(
                    type="error",
                    error=f"Cache miss in offline mode: {cache_k[:16]} ({resolved_model})",
                )
                return

        # Build request kwargs
        request_kwargs: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            # Request usage in the final chunk — not all providers honour this
            # but DashScope does.
            "stream_options": {"include_usage": True},
        }
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        if tools:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = tool_choice

        # Accumulators for write-through cache and tool-call coalescing
        # key = tool_call_id, value = {"name": str, "args_str": str, "index": int}
        _tool_buffers: dict[str, dict] = {}
        _full_text: list[str] = []
        _finish_reason: str | None = None
        _usage: dict | None = None

        try:
            start = time.monotonic()
            stream = await self.client.chat.completions.create(**request_kwargs)

            async for chunk in stream:
                if not chunk.choices:
                    # Final usage-only chunk from some providers
                    if chunk.usage:
                        _usage = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens,
                        }
                    continue

                choice = chunk.choices[0]
                delta = choice.delta
                _finish_reason = choice.finish_reason or _finish_reason

                # --- Thinking / reasoning tokens (Qwen3 extended thinking mode) ---
                # DashScope adds reasoning_content as an extra attribute; guard
                # gracefully because it is absent on non-reasoning models.
                reasoning_text = getattr(delta, "reasoning_content", None)
                if reasoning_text:
                    yield StreamEvent(type="thinking_chunk", delta=reasoning_text)

                # --- Regular text content ---
                if delta.content:
                    _full_text.append(delta.content)
                    yield StreamEvent(type="text_chunk", delta=delta.content)

                # --- Tool call argument fragments ---
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        tc_id = tc_delta.id
                        fn = tc_delta.function

                        # First delta for a tool call carries id + name
                        if tc_id and tc_id not in _tool_buffers:
                            _tool_buffers[tc_id] = {
                                "name": fn.name or "",
                                "args_str": "",
                                "index": tc_delta.index or 0,
                            }
                        elif not tc_id:
                            # Subsequent fragments lack id; match by index
                            idx = tc_delta.index or 0
                            for existing_id, buf in _tool_buffers.items():
                                if buf["index"] == idx:
                                    tc_id = existing_id
                                    break

                        if tc_id is None:
                            continue

                        buf = _tool_buffers[tc_id]

                        # Name may arrive in a later delta for some models
                        if fn and fn.name:
                            buf["name"] = fn.name

                        args_fragment = (fn.arguments or "") if fn else ""
                        if args_fragment:
                            buf["args_str"] += args_fragment
                            yield StreamEvent(
                                type="tool_call_delta",
                                tool_call_id=tc_id,
                                tool_name=buf["name"],
                                tool_args_delta=args_fragment,
                            )

                # --- Finalize when the model signals it wants to call tools ---
                if choice.finish_reason == "tool_calls":
                    for tc_id, buf in _tool_buffers.items():
                        try:
                            parsed_args = json.loads(buf["args_str"]) if buf["args_str"] else {}
                        except json.JSONDecodeError:
                            # Defensive: surface raw string so caller can decide
                            parsed_args = {"_raw": buf["args_str"]}
                            logger.warning(
                                "stream_chat: could not parse tool args for"
                                f" {buf['name']}: {buf['args_str'][:80]}"
                            )
                        yield StreamEvent(
                            type="tool_call_finalized",
                            tool_call_id=tc_id,
                            tool_name=buf["name"],
                            tool_args=parsed_args,
                        )

                # Capture usage from final streaming chunk
                if chunk.usage:
                    _usage = {
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens,
                    }

            latency_ms = (time.monotonic() - start) * 1000
            logger.debug(
                f"Qwen stream {resolved_model}: finish={_finish_reason}, "
                f"{(_usage or {}).get('total_tokens', '?')} tokens, {latency_ms:.0f}ms"
            )

            # Update token usage tracker (same as non-stream path)
            if _usage:
                self.usage.input_tokens += _usage.get("prompt_tokens", 0)
                self.usage.output_tokens += _usage.get("completion_tokens", 0)
                self.usage.total_tokens += _usage.get("total_tokens", 0)
            self.usage.api_calls += 1
            self.usage.total_latency_ms += latency_ms

            # Write-through cache: aggregate the full response in non-stream format
            # so the same cache entry works for both stream and non-stream paths.
            if use_cache and cache_k:
                try:
                    aggregated: dict[str, Any] = {
                        "content": "".join(_full_text) or None,
                        "tool_calls": [
                            {
                                "id": tc_id,
                                "type": "function",
                                "function": {
                                    "name": buf["name"],
                                    "arguments": buf["args_str"],
                                },
                            }
                            for tc_id, buf in _tool_buffers.items()
                        ]
                        or None,
                        "usage": _usage or {},
                        "finish_reason": _finish_reason or "stop",
                    }
                    llm_cache.set_cached(cache_k, aggregated)
                except Exception as cache_err:
                    logger.warning(f"Stream cache write failed for {cache_k[:12]}: {cache_err}")

            yield StreamEvent(
                type="done",
                finish_reason=_finish_reason or "stop",
                usage=_usage,
            )

        except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            logger.error(f"stream_chat error ({resolved_model}): {exc}", exc_info=True)
            yield StreamEvent(type="error", error=str(exc))

    def reset_usage(self) -> TokenUsage:
        """Reset and return the accumulated usage."""
        usage = self.usage
        self.usage = TokenUsage()
        return usage
