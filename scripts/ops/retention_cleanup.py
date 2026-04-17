#!/usr/bin/env python3
"""
scripts/ops/retention_cleanup.py
Delete audit_events_flat rows older than 10 years per NĐ 30/2020 Điều 28.

NĐ 30/2020 Điều 28: Thời hạn bảo quản hồ sơ là 10 năm kể từ khi kết thúc năm
tài chính hoặc năm hành chính mà tài liệu được hình thành.

Schedule: Run monthly via cron / Cloud Scheduler.
  0 2 1 * *  python /app/scripts/ops/retention_cleanup.py

Dry-run mode: set DRY_RUN=1 to preview deletions without executing.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("retention_cleanup")

# Retention period per NĐ 30/2020 Điều 28
_RETENTION_YEARS = 10


async def run_cleanup(dry_run: bool = False) -> None:
    """Delete audit events older than _RETENTION_YEARS years."""
    try:
        import asyncpg
    except ImportError:
        logger.error("asyncpg not installed")
        sys.exit(1)

    # Import after path setup
    from backend.src.config import settings  # type: ignore[import]

    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_YEARS * 365)
    logger.info(
        "Retention cleanup: deleting audit_events_flat rows older than %s (dry_run=%s)",
        cutoff.date(),
        dry_run,
    )

    pool = await asyncpg.create_pool(settings.hologres_dsn, min_size=1, max_size=3)
    try:
        async with pool.acquire() as conn:
            # Count first
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_events_flat WHERE created_at < $1",
                cutoff,
            )
            logger.info("Rows eligible for deletion: %d", count)

            if dry_run:
                logger.info("DRY RUN: no rows deleted")
                return

            if count == 0:
                logger.info("Nothing to delete")
                return

            # Delete in batches of 10_000 to avoid long-lock transactions
            total_deleted = 0
            while True:
                deleted = await conn.execute(
                    """
                    DELETE FROM audit_events_flat
                    WHERE id IN (
                        SELECT id FROM audit_events_flat
                        WHERE created_at < $1
                        LIMIT 10000
                    )
                    """,
                    cutoff,
                )
                # asyncpg returns "DELETE N" string
                n = int(deleted.split()[-1]) if deleted else 0
                total_deleted += n
                logger.info("Deleted batch: %d rows (total so far: %d)", n, total_deleted)
                if n == 0:
                    break
                await asyncio.sleep(0.1)  # brief pause between batches

            logger.info(
                "Retention cleanup complete: %d rows deleted, cutoff=%s",
                total_deleted,
                cutoff.date(),
            )
    finally:
        await pool.close()


def main() -> None:
    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    asyncio.run(run_cleanup(dry_run=dry_run))


if __name__ == "__main__":
    main()
