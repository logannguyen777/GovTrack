"""
scripts/embed_chunks.py
Chunk law articles, embed with Qwen3-Embedding v3, insert into law_chunks table.
Reads: data/legal/processed/law_chunks.jsonl (869 pre-chunked entries)

If DASHSCOPE_API_KEY is not set, inserts chunks WITHOUT embeddings (text-only mode).
When a real key is available, re-run to add embeddings.
"""
import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, "backend")
from src.config import settings
from src.database import create_pg_pool, get_pg_pool, close_pg_pool

DATA_FILE = Path("data/legal/processed/law_chunks.jsonl")
EMBED_MODEL = "text-embedding-v3"
EMBED_DIM = 1536
BATCH_SIZE = 20


def has_valid_api_key() -> bool:
    key = settings.dashscope_api_key
    return bool(key) and not key.startswith("sk-xxxx")


def get_embeddings(client, texts: list[str]) -> list[list[float]]:
    """Get embeddings for a batch of texts via DashScope."""
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
        dimensions=EMBED_DIM,
    )
    return [item.embedding for item in response.data]


async def main():
    await create_pg_pool()
    pool = get_pg_pool()

    # Check if already populated
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT count(*) FROM law_chunks")
        if existing > 0:
            print(f"law_chunks already has {existing} rows. Skipping.")
            await close_pg_pool()
            return

    # Load chunks
    chunks = [json.loads(line) for line in open(DATA_FILE)]
    print(f"Loaded {len(chunks)} chunks from {DATA_FILE}")

    # Check API key
    use_embeddings = has_valid_api_key()
    qwen = None
    if use_embeddings:
        from openai import OpenAI
        qwen = OpenAI(
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
        )
        print(f"DashScope API key found. Will embed with {EMBED_MODEL} ({EMBED_DIM}d)")
    else:
        print("WARNING: No valid DASHSCOPE_API_KEY. Inserting chunks WITHOUT embeddings.")
        print("  Re-run with a valid key to add embeddings later.")

    # Insert in batches
    total_inserted = 0
    async with pool.acquire() as conn:
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]

            # Get embeddings if API key available
            embeddings = None
            if use_embeddings and qwen:
                texts = [c["text"] for c in batch]
                try:
                    embeddings = get_embeddings(qwen, texts)
                except Exception as ex:
                    print(f"\n  Embedding batch {i} failed: {ex}")
                    embeddings = None

            for j, chunk in enumerate(batch):
                emb = embeddings[j] if embeddings else None
                emb_str = str(emb) if emb else None

                await conn.execute(
                    """
                    INSERT INTO law_chunks (id, law_id, article_number, clause_path,
                        chunk_index, title, content, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8::vector, $9::jsonb)
                    """,
                    uuid.uuid4(),
                    chunk["law_code"],
                    f"Dieu {chunk['article_num']}",
                    f"Dieu {chunk['article_num']}",
                    chunk["chunk_seq"],
                    "",
                    chunk["text"],
                    emb_str,
                    json.dumps({
                        "effective_date": chunk.get("effective_date", ""),
                        "status": chunk.get("status", ""),
                        "classification": chunk.get("classification", ""),
                    }),
                )
                total_inserted += 1

            pct = min(i + BATCH_SIZE, len(chunks)) * 100 // len(chunks)
            print(f"\r  Inserted: {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} ({pct}%)", end="", flush=True)

    print(f"\n  Total chunks inserted: {total_inserted}")

    # Create vector index if embeddings were added
    if use_embeddings and embeddings:
        print("Creating ivfflat vector index...")
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_law_chunks_embedding
                ON law_chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 20)
            """)
        print("  Vector index created")

    # Verify
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT count(*) FROM law_chunks")
        has_emb = await conn.fetchval("SELECT count(*) FROM law_chunks WHERE embedding IS NOT NULL")
        print(f"\nVerification: {count} rows, {has_emb} with embeddings")

    await close_pg_pool()


if __name__ == "__main__":
    asyncio.run(main())
