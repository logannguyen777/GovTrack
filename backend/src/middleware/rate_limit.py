"""
backend/src/middleware/rate_limit.py
slowapi Limiter factory + DashScope token budget middleware.
"""

from __future__ import annotations

import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from ..config import settings

logger = logging.getLogger("govflow.rate_limit")

# ---------------------------------------------------------------------------
# Limiter instance
# ---------------------------------------------------------------------------
# Use Redis storage when redis_url is configured; else in-memory (default).


def _make_limiter() -> Limiter:
    storage_uri = settings.redis_url
    if storage_uri:
        try:
            return Limiter(
                key_func=get_remote_address,
                default_limits=[settings.rate_limit_default],
                storage_uri=storage_uri,
            )
        except Exception as exc:
            logger.warning("Redis limiter init failed (%s) — falling back to in-memory", exc)

    return Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_default],
    )


limiter: Limiter = _make_limiter()


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return a structured 429 response."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Vượt quá giới hạn yêu cầu. Vui lòng thử lại sau.",
            "code": "RATE_LIMIT_EXCEEDED",
            "retry_after": getattr(exc, "retry_after", None),
        },
        headers={"Retry-After": str(getattr(exc, "retry_after", 60))},
    )


# ---------------------------------------------------------------------------
# DashScope token budget (per user per day)
# ---------------------------------------------------------------------------
# Tracks tokens in-memory (dict) when no Redis is available.
# Redis path: keys govflow:token_budget:{user_id}:{date}  TTL=86400s

_in_memory_budget: dict[str, int] = {}


def _budget_key(user_id: str) -> str:
    from datetime import date

    return f"govflow:token_budget:{user_id}:{date.today().isoformat()}"


async def _get_tokens_used(user_id: str) -> int:
    key = _budget_key(user_id)
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]

            r = aioredis.from_url(settings.redis_url)
            val = await r.get(key)
            await r.aclose()
            return int(val) if val else 0
        except Exception:
            pass
    return _in_memory_budget.get(key, 0)


async def _add_tokens_used(user_id: str, tokens: int) -> int:
    key = _budget_key(user_id)
    if settings.redis_url:
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]

            r = aioredis.from_url(settings.redis_url)
            new_val = await r.incrby(key, tokens)
            await r.expire(key, 86400)
            await r.aclose()
            return int(new_val)
        except Exception:
            pass
    _in_memory_budget[key] = _in_memory_budget.get(key, 0) + tokens
    return _in_memory_budget[key]


async def check_token_budget(user_id: str, estimated_tokens: int = 0) -> None:
    """Raise 429 HTTPException if user has exceeded their daily token budget.

    Called from agent base before each LLM call.

    Args:
        user_id:          Authenticated user's ID.
        estimated_tokens: Tokens we expect to consume (for pre-check).
    """
    from fastapi import HTTPException

    limit = settings.dashscope_tokens_per_user_per_day
    used = await _get_tokens_used(user_id)
    if used + estimated_tokens > limit:
        logger.warning(
            "Token budget exceeded: user=%s used=%d limit=%d", user_id, used, limit
        )
        raise HTTPException(
            status_code=429,
            detail={
                "detail": "Đã vượt hạn mức token trong ngày.",
                "code": "DAILY_QUOTA_EXCEEDED",
                "used": used,
                "limit": limit,
            },
        )


async def record_tokens_used(user_id: str, tokens: int) -> None:
    """Record tokens consumed after an LLM call returns."""
    await _add_tokens_used(user_id, tokens)
