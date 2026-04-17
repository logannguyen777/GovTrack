"""
scripts/embed_chunks_update.py
Populate embeddings for law_chunks rows that have NULL embedding.

Why separate from embed_chunks.py: that script refuses to run if chunks already
exist. This one works the other direction — fills embeddings into the rows that
were inserted text-only.

Idempotent: safe to re-run; only touches rows where embedding IS NULL.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, "backend")

from openai import AsyncOpenAI  # noqa: E402

from src.config import settings  # noqa: E402
from src.database import close_pg_pool, create_pg_pool, get_pg_pool  # noqa: E402

EMBED_MODEL = "text-embedding-v3"
EMBED_DIM = 1024         # DashScope v3 only supports 512 | 768 | 1024
BATCH_SIZE = 10          # DashScope v3 max batch size


async def main() -> None:
    if not settings.dashscope_api_key or settings.dashscope_api_key.startswith("sk-xxxx"):
        print("FATAL: DASHSCOPE_API_KEY not set. Add it to backend/.env.")
        sys.exit(1)

    await create_pg_pool()
    pool = get_pg_pool()

    # Count pending rows
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            "SELECT count(*) FROM law_chunks WHERE embedding IS NULL"
        )
        already = await conn.fetchval(
            "SELECT count(*) FROM law_chunks WHERE embedding IS NOT NULL"
        )
    print(f"pending: {total} rows without embedding ({already} already done)")
    if total == 0:
        print("nothing to do.")
        await close_pg_pool()
        return

    client = AsyncOpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
        timeout=120.0,
    )

    processed = 0
    while True:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, content FROM law_chunks WHERE embedding IS NULL "
                "LIMIT $1",
                BATCH_SIZE,
            )
        if not rows:
            break

        texts = [r["content"] for r in rows]
        try:
            resp = await client.embeddings.create(
                model=EMBED_MODEL, input=texts, dimensions=EMBED_DIM,
            )
        except Exception as e:
            print(f"\nembed batch failed: {e}")
            break
        embeddings = [item.embedding for item in resp.data]

        async with pool.acquire() as conn:
            async with conn.transaction():
                for row, emb in zip(rows, embeddings):
                    await conn.execute(
                        "UPDATE law_chunks SET embedding = $1::vector WHERE id = $2",
                        str(emb), row["id"],
                    )

        processed += len(rows)
        pct = (processed + already) * 100 // (total + already)
        print(f"\r  embedded: {processed}/{total} ({pct}%)", end="", flush=True)

    print()

    # Create vector index if missing
    async with pool.acquire() as conn:
        idx_exists = await conn.fetchval(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_law_chunks_embedding'"
        )
        if not idx_exists:
            print("creating ivfflat vector index...")
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_law_chunks_embedding "
                "ON law_chunks USING ivfflat (embedding vector_cosine_ops) "
                "WITH (lists = 20)"
            )
            print("  done.")
        else:
            print("vector index already exists.")

        done = await conn.fetchval(
            "SELECT count(*) FROM law_chunks WHERE embedding IS NOT NULL"
        )
        print(f"verification: {done} rows now have embeddings.")

    await close_pg_pool()


if __name__ == "__main__":
    asyncio.run(main())
