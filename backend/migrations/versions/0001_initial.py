"""Initial schema — runs infra/postgres/init.sql

Revision ID: 0001
Revises:
Create Date: 2026-04-16
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Resolve init.sql relative to this file's repo root
_INIT_SQL = (
    Path(__file__).resolve().parent.parent.parent.parent  # GovTrack/
    / "infra"
    / "postgres"
    / "init.sql"
)


def upgrade() -> None:
    if _INIT_SQL.exists():
        sql = _INIT_SQL.read_text(encoding="utf-8")
        op.execute(sql)
    else:
        # Inline minimal schema when init.sql is unavailable (CI environments)
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                username        VARCHAR(100) UNIQUE NOT NULL,
                full_name       VARCHAR(200) NOT NULL,
                email           VARCHAR(200),
                password_hash   VARCHAR(200) NOT NULL,
                role            VARCHAR(50) NOT NULL DEFAULT 'officer',
                clearance_level INTEGER NOT NULL DEFAULT 0,
                departments     TEXT[] NOT NULL DEFAULT '{}',
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_users_role ON users (role);
            """
        )


def downgrade() -> None:
    # Destructive: drops all GovFlow tables.
    # Only run in dev / test environments.
    for table in [
        "assistant_messages",
        "assistant_sessions",
        "revoked_tokens",
        "audit_events_flat",
        "notifications",
        "analytics_agents",
        "analytics_cases",
        "templates_nd30",
        "law_chunks",
        "users",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
