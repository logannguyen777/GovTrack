"""
backend/src/services/chat_service.py
Persistence layer for citizen assistant chat sessions and messages.
Uses asyncpg pool from database.py.
"""

from __future__ import annotations

import json
import logging
import uuid

from ..database import pg_connection
from ..models.chat_schemas import ChatContext

logger = logging.getLogger("govflow.chat_service")


class ChatService:
    """Manages assistant_sessions + assistant_messages tables."""

    async def get_or_create_session(
        self,
        session_id: str | None,
        ip_hash: str,
        context: ChatContext,
    ) -> str:
        """
        Return existing session_id if valid (belongs to same ip_hash),
        otherwise create a new session. Returns the canonical session_id.
        Ownership is verified by ip_hash to prevent session hijacking.
        """
        context_json = context.model_dump_json()

        async with pg_connection() as conn:
            if session_id:
                row = await conn.fetchrow(
                    "SELECT id, ip_hash FROM assistant_sessions WHERE id = $1",
                    session_id,
                )
                if row and row["ip_hash"] == ip_hash:
                    # Touch last_message_at to keep session alive
                    await conn.execute(
                        "UPDATE assistant_sessions SET last_message_at = NOW() WHERE id = $1",
                        session_id,
                    )
                    return session_id

            # Create new session
            new_id = str(uuid.uuid4())
            await conn.execute(
                """
                INSERT INTO assistant_sessions (id, ip_hash, context, metadata)
                VALUES ($1, $2, $3::jsonb, '{}'::jsonb)
                """,
                new_id,
                ip_hash,
                context_json,
            )
            return new_id

    async def append_user_message(
        self,
        session_id: str,
        content: str,
        attachments: list,
    ) -> str:
        """Persist a user message. Returns message_id."""
        msg_id = str(uuid.uuid4())
        attachments_json = json.dumps(
            [a.model_dump() if hasattr(a, "model_dump") else a for a in attachments]
        )

        async with pg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO assistant_messages
                    (id, session_id, role, content, attachments, status)
                VALUES ($1, $2, 'user', $3, $4::jsonb, 'completed')
                """,
                msg_id,
                session_id,
                content,
                attachments_json,
            )
            await conn.execute(
                "UPDATE assistant_sessions SET last_message_at = NOW() WHERE id = $1",
                session_id,
            )
        return msg_id

    async def append_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: list,
        citations: list,
        status: str,
    ) -> str:
        """Persist an assistant message. Returns message_id."""
        msg_id = str(uuid.uuid4())

        async with pg_connection() as conn:
            await conn.execute(
                """
                INSERT INTO assistant_messages
                    (id, session_id, role, content, tool_calls, citations, status)
                VALUES ($1, $2, 'assistant', $3, $4::jsonb, $5::jsonb, $6)
                """,
                msg_id,
                session_id,
                content,
                json.dumps(tool_calls),
                json.dumps(citations),
                status,
            )
            await conn.execute(
                "UPDATE assistant_sessions SET last_message_at = NOW() WHERE id = $1",
                session_id,
            )
        return msg_id

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict]:
        """
        Return the last `limit` messages for a session, oldest-first.
        Returns only role+content fields to build LLM message list.
        """
        async with pg_connection() as conn:
            rows = await conn.fetch(
                """
                SELECT role, content, tool_calls, created_at
                FROM assistant_messages
                WHERE session_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                session_id,
                limit,
            )

        # Reverse to get chronological order
        messages = []
        for r in reversed(rows):
            msg: dict = {"role": r["role"], "content": r["content"] or ""}
            # Intentionally DROP tool_calls on history reload: intermediate tool result
            # messages are not persisted, so keeping assistant.tool_calls without matching
            # tool-role responses produces invalid DashScope conversations. The final content
            # is a text summary of tool outputs — enough context for continuity.
            messages.append(msg)

        return messages

    async def update_message_status(self, message_id: str, status: str) -> None:
        """Update message status (e.g., 'completed', 'error', 'cancelled')."""
        async with pg_connection() as conn:
            await conn.execute(
                "UPDATE assistant_messages SET status = $1 WHERE id = $2",
                status,
                message_id,
            )

    async def cancel_streaming_message(self, message_id: str) -> None:
        """Mark a streaming message as cancelled (called on SSE disconnect)."""
        await self.update_message_status(message_id, "cancelled")
        logger.debug(f"Cancelled streaming message {message_id}")
