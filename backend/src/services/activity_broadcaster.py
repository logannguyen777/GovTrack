"""
backend/src/services/activity_broadcaster.py

Fire-and-forget broadcaster for the public:system:activity WebSocket topic.
Powers the "Architecture Live Panel" shown to hackathon judges.

Contract:
- Events are PII-FREE (no case_id, applicant name, query text, etc.)
- Broadcast is non-blocking — callers use fire() which schedules via create_task
- Throttle: max 10 events / event_type / second (drop excess silently)
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger("govflow.activity")

_TOPIC = "public:system:activity"
_MAX_EVENTS_PER_TYPE_PER_SEC = 10

_event_windows: dict[str, deque[float]] = defaultdict(
    lambda: deque(maxlen=_MAX_EVENTS_PER_TYPE_PER_SEC)
)

EventType = Literal["llm", "vector", "graph", "ocr", "oss", "cache"]


def _throttle_ok(event_type: str) -> bool:
    """Sliding-window throttle. True if ok to publish this event now."""
    now = time.monotonic()
    dq = _event_windows[event_type]
    while dq and now - dq[0] > 1.0:
        dq.popleft()
    if len(dq) >= _MAX_EVENTS_PER_TYPE_PER_SEC:
        return False
    dq.append(now)
    return True


async def _publish(
    event_type: EventType,
    label: str,
    detail: str,
    duration_ms: float,
    model: str | None,
) -> None:
    # Import here to break potential circular import
    from ..api.ws import broadcast

    payload = {
        "type": event_type,
        "label": label,
        "detail": detail,
        "duration_ms": round(duration_ms, 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if model:
        payload["model"] = model

    try:
        await broadcast(_TOPIC, {"event": "activity", "data": payload})
    except Exception as exc:
        logger.debug(f"activity broadcast failed (non-critical): {exc}")


def fire(
    event_type: EventType,
    label: str,
    detail: str = "",
    duration_ms: float = 0.0,
    model: str | None = None,
) -> None:
    """
    Fire-and-forget activity broadcast. Safe from sync or async contexts.
    Drops silently if no event loop, or throttle triggered, or ws unavailable.
    """
    if not _throttle_ok(event_type):
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(
        _publish(event_type, label, detail, duration_ms, model),
        name=f"activity:{event_type}",
    )
