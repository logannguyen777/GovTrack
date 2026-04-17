"""Ensure revoked_tokens table exists (idempotent — may already be in 0001).

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-16
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent — init.sql already creates this table.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti         TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            expires_at  TIMESTAMPTZ NOT NULL,
            revoked_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires
            ON revoked_tokens (expires_at);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS revoked_tokens CASCADE")
