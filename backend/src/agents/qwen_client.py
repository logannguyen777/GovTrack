"""
backend/src/agents/qwen_client.py
OpenAI-compatible async client for Alibaba DashScope (Qwen models).
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ..config import settings

logger = logging.getLogger("govflow.qwen")

# Model routing table
MODELS = {
    "reasoning": "qwen-max-latest",        # Agent reasoning, analysis
    "vision": "qwen-vl-max-latest",         # Document OCR, image analysis
    "embedding": "text-embedding-v3",        # Vector embeddings
}

# Default parameters per model
MODEL_DEFAULTS = {
    "qwen-max-latest": {"max_tokens": 4096, "temperature": 0.3},
    "qwen-vl-max-latest": {"max_tokens": 2048, "temperature": 0.1},
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
    Provides model routing, token tracking, and retry logic.
    """
    client: AsyncOpenAI = field(default=None)
    usage: TokenUsage = field(default_factory=TokenUsage)
    max_retries: int = 3

    def __post_init__(self):
        if self.client is None:
            self.client = AsyncOpenAI(
                api_key=settings.dashscope_api_key,
                base_url=settings.dashscope_base_url,
                timeout=120.0,
            )

    async def chat(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
        **kwargs,
    ) -> ChatCompletion:
        """
        Send a chat completion request.

        Args:
            messages: OpenAI-format messages
            model: Model ID or alias (reasoning/vision). Defaults to reasoning.
            tools: OpenAI-format tool definitions
            tool_choice: "auto", "none", or "required"
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        """
        # Resolve model alias
        resolved_model = MODELS.get(model, model) or MODELS["reasoning"]

        # Apply defaults
        params = {**MODEL_DEFAULTS.get(resolved_model, {}), **kwargs}

        request_kwargs = {
            "model": resolved_model,
            "messages": messages,
            **params,
        }

        if tools:
            request_kwargs["tools"] = tools
            request_kwargs["tool_choice"] = tool_choice

        # Retry loop
        last_error = None
        for attempt in range(self.max_retries):
            try:
                start = time.monotonic()
                completion = await self.client.chat.completions.create(**request_kwargs)
                latency = (time.monotonic() - start) * 1000

                self.usage.add(completion, latency)
                logger.debug(
                    f"Qwen {resolved_model}: {completion.usage.prompt_tokens}in/"
                    f"{completion.usage.completion_tokens}out, {latency:.0f}ms"
                )
                return completion

            except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
                raise  # Never retry these — allow graceful shutdown
            except Exception as e:
                last_error = e
                logger.warning(f"Qwen API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = (1.0 * (attempt + 1)) + random.uniform(0, 1.0)
                    await asyncio.sleep(delay)  # Backoff with jitter

        raise RuntimeError(f"Qwen API failed after {self.max_retries} retries: {last_error}")

    async def embed(self, texts: list[str], dimensions: int = 1536) -> list[list[float]]:
        """Get embeddings for a batch of texts."""
        start = time.monotonic()
        response = await self.client.embeddings.create(
            model=MODELS["embedding"],
            input=texts,
            dimensions=dimensions,
        )
        latency = (time.monotonic() - start) * 1000

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
            content.append({
                "type": "image_url",
                "image_url": {"url": url},
            })

        messages = [{"role": "user", "content": content}]
        return await self.chat(messages, model="vision", **kwargs)

    def reset_usage(self) -> TokenUsage:
        """Reset and return the accumulated usage."""
        usage = self.usage
        self.usage = TokenUsage()
        return usage
