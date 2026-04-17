"""dispatch_log table for Wave 2.5 DispatchLog persistence.

Note: DispatchLog state is primarily stored in GDB (graph vertices).
This migration adds a PostgreSQL projection table for analytics /
reporting queries that need SQL joins with case/user data.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-16
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dispatch_log (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            case_id         TEXT NOT NULL,
            from_dept_id    TEXT,
            to_dept_id      TEXT NOT NULL,
            dispatch_type   TEXT NOT NULL DEFAULT 'assignment',
                -- assignment | consult | escalation | return
            reason          TEXT,
            dispatched_by   TEXT,
                -- user_id of dispatcher (may be agent or human)
            dispatched_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata        JSONB DEFAULT '{}'
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_dispatch_log_case
            ON dispatch_log (case_id, dispatched_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_dispatch_log_dept
            ON dispatch_log (to_dept_id, dispatched_at DESC);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dispatch_log CASCADE")
