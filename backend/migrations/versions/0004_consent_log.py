"""Create consent_log table for NĐ 13/2023 data subject rights (Wave 3.11).

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-16
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS consent_log (
            consent_id  TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL,
            purpose     TEXT NOT NULL,
            action      TEXT NOT NULL CHECK (action IN ('granted', 'revoked')),
            ip_address  INET,
            user_agent  TEXT,
            timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_consent_log_user_time
            ON consent_log (user_id, timestamp DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS consent_log CASCADE")
