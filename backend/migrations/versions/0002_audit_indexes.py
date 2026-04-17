"""Add composite audit_events_flat indexes for time-range + actor queries.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_flat_type_time
            ON audit_events_flat (event_type, created_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_flat_actor
            ON audit_events_flat (actor_id, created_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_audit_events_flat_target
            ON audit_events_flat (target_type, target_id);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_events_flat_type_time")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_flat_actor")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_flat_target")
