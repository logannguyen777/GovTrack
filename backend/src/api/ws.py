"""
backend/src/api/ws.py
WebSocket handler with topic-based pub/sub.
Topics: case:{id}, dept:{id}:inbox, user:{id}:notifications, security:audit

Authentication protocol (0.7):
  1. Client connects (no token in query params).
  2. Server awaits the FIRST message within 5 seconds.
  3. First message must be: {"action": "auth", "token": "<JWT>"}
  4. Server validates the token. On failure or timeout, close code 1008.
  5. After successful auth, normal subscribe/unsubscribe messages proceed.
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

_AUTH_TIMEOUT_SECONDS = 5.0

# Global subscription registry: topic -> set of websockets
_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
_lock = asyncio.Lock()


async def subscribe(ws: WebSocket, topic: str) -> None:
    async with _lock:
        _subscriptions[topic].add(ws)
    logger.info("WS subscribed to %s", topic)


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
    WebSocket endpoint — server-side auth handshake (0.7).

    Protocol:
      1. Server accepts the TCP/WS connection.
      2. Server waits up to 5 s for {"action": "auth", "token": "..."}.
      3. Token is validated; on failure or timeout → close(1008).
      4. On success → normal subscribe/unsubscribe loop.
    """
    await ws.accept()

    # --- Phase 1: auth handshake ---
    user = None
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=_AUTH_TIMEOUT_SECONDS)
        msg = json.loads(raw)
        if msg.get("action") != "auth" or not msg.get("token"):
            await ws.close(code=1008, reason="First message must be auth handshake")
            return
        user = decode_token(msg["token"])
        await ws.send_json({"ack": "authenticated", "username": user.username})
        logger.info("WS authenticated: %s", user.username)
    except TimeoutError:
        logger.warning("WS auth timeout — closing connection")
        await ws.close(code=1008, reason="Authentication timeout")
        return
    except Exception as exc:
        logger.warning("WS auth failed: %s", exc)
        await ws.close(code=1008, reason="Authentication failed")
        return

    # --- Phase 2: normal message loop ---
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            topic = data.get("topic", "")

            if action == "subscribe":
                await subscribe(ws, topic)
                await ws.send_json({"ack": "subscribed", "topic": topic})
            elif action == "unsubscribe":
                await unsubscribe(ws, topic)
                await ws.send_json({"ack": "unsubscribed", "topic": topic})
            else:
                await ws.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("WS disconnected: %s", user.username if user else "unknown")
    except Exception as e:
        logger.error("WS error: %s", e)
    finally:
        await unsubscribe_all(ws)
