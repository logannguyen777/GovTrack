"""Reset demo case statuses to presentable demo states."""
import asyncio
import sys

sys.path.insert(0, "/app")
from src.database import (
    create_gremlin_client,
    gremlin_submit,
    close_gremlin_client,
    create_pg_pool,
    get_pg_pool,
    close_pg_pool,
)

RESET_MAP = {
    "CASE-2026-0001": "consultation",
    "CASE-2026-0002": "submitted",
    "CASE-2026-0003": "classifying",
    "CASE-2026-0004": "published",
    "CASE-2026-0005": "submitted",
}


async def main() -> int:
    create_gremlin_client()
    for cid, st in RESET_MAP.items():
        gremlin_submit(
            "g.V().has('Case', 'case_id', cid).property('status', st)",
            {"cid": cid, "st": st},
        )
        print(f"GDB {cid} -> {st}")
    close_gremlin_client()

    await create_pg_pool()
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        for cid, st in RESET_MAP.items():
            await conn.execute(
                "UPDATE analytics_cases SET status=$1 WHERE case_id=$2",
                st, cid,
            )
            print(f"PG {cid} -> {st}")
    await close_pg_pool()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
