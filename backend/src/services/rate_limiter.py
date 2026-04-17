"""
backend/src/services/rate_limiter.py
In-memory sliding window rate limiter per key.
Thread-safe via asyncio.Lock. No external deps needed.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class RateLimiter:
    """
    Sliding window rate limiter.
    Default: 20 requests per 60 seconds per key.
    Key is typically ip_hash from the caller.
    """

    def __init__(self, max_per_minute: int = 20, window_seconds: int = 60):
        self.max = max_per_minute
        self.window = window_seconds
        # Deque of timestamps per key; auto-evict old entries on check
        self.windows: dict[str, deque[float]] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        """
        Return True if request is allowed, False if rate-limited.
        Side-effect: records the current timestamp if allowed.
        """
        now = time.monotonic()
        cutoff = now - self.window

        async with self.lock:
            dq = self.windows[key]

            # Evict timestamps outside the sliding window
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= self.max:
                return False

            dq.append(now)
            return True

    async def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        now = time.monotonic()
        cutoff = now - self.window

        async with self.lock:
            dq = self.windows[key]
            while dq and dq[0] < cutoff:
                dq.popleft()
            return max(0, self.max - len(dq))
