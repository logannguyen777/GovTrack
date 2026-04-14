"""
backend/src/api/ws.py
WebSocket handler with topic-based pub/sub.
Topics: case:{id}, dept:{id}:inbox, user:{id}:notifications, security:audit
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..auth import decode_token

router = APIRouter()
logger = logging.getLogger("govflow.ws")

# Global subscription registry: topic -> set of websockets
_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
_lock = asyncio.Lock()


async def subscribe(ws: WebSocket, topic: str) -> None:
    async with _lock:
        _subscriptions[topic].add(ws)
    logger.info(f"WS subscribed to {topic}")


async def unsubscribe(ws: WebSocket, topic: str) -> None:
    async with _lock:
        _subscriptions[topic].discard(ws)


async def unsubscribe_all(ws: WebSocket) -> None:
    async with _lock:
        for topic in list(_subscriptions.keys()):
            _subscriptions[topic].discard(ws)


async def broadcast(topic: str, message: dict) -> None:
    """Broadcast a message to all subscribers of a topic."""
    async with _lock:
        subscribers = list(_subscriptions.get(topic, set()))

    payload = json.dumps({"topic": topic, **message})
    dead = []
    for ws in subscribers:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)

    # Clean up dead connections
    if dead:
        async with _lock:
            for ws in dead:
                _subscriptions[topic].discard(ws)


@router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint.
    Client sends JSON: {"action": "subscribe"|"unsubscribe", "topic": "case:123"}
    Server pushes:     {"topic": "case:123", "event": "status_changed", "data": {...}}
    """
    await ws.accept()

    # Authenticate via query param
    token = ws.query_params.get("token")
    if token:
        try:
            user = decode_token(token)
            logger.info(f"WS authenticated: {user.username}")
        except Exception:
            await ws.close(code=4001, reason="Invalid token")
            return
    else:
        user = None  # Allow unauthenticated for public topics

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            topic = data.get("topic", "")

            # Public topics don't require auth
            is_public = topic.startswith("public:")
            if not is_public and user is None:
                await ws.send_json({"error": "Authentication required for non-public topics"})
                continue

            if action == "subscribe":
                await subscribe(ws, topic)
                await ws.send_json({"ack": "subscribed", "topic": topic})
            elif action == "unsubscribe":
                await unsubscribe(ws, topic)
                await ws.send_json({"ack": "unsubscribed", "topic": topic})
            else:
                await ws.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("WS disconnected")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await unsubscribe_all(ws)
