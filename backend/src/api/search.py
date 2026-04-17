"""backend/src/api/search.py"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from ..auth import CurrentUser
from ..config import settings
from ..database import pg_connection
from ..graph.deps import PermittedGDBDep
from ..models.schemas import LawSearchResult, TTHCSearchResult

logger = logging.getLogger("govflow.search")
router = APIRouter(prefix="/search", tags=["Search"])

# DashScope text-embedding-v3 supports 512, 768, 1024 only
_EMBEDDING_DIM = 1024

# Simple in-memory cache for law chunk lookups (TTL = 5 minutes)
_chunk_cache: dict[str, tuple[dict[str, Any], float]] = {}
_CHUNK_CACHE_TTL = 300.0  # seconds


class LawChunkResponse(BaseModel):
    chunk_id: str
    law_id: str
    article_number: str
    clause_path: str
    chunk_index: int
    title: str | None
    content: str
    metadata: dict[str, Any]
    created_at: str


@router.get("/law", response_model=list[LawSearchResult])
async def search_law(user: CurrentUser, query: str, top_k: int = 10, law_id: str | None = None):
    """Vector search over law chunks using Qwen3-Embedding."""
    # Check if embeddings exist
    async with pg_connection() as conn:
        has_embeddings = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM law_chunks WHERE embedding IS NOT NULL LIMIT 1)"
        )

    if not has_embeddings:
        # Fall back to text search when embeddings are not yet generated
        return await _text_search_law(query, top_k, law_id)

    try:
        client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
        emb_resp = client.embeddings.create(
            model="text-embedding-v3", input=query, dimensions=_EMBEDDING_DIM
        )
        query_vec = emb_resp.data[0].embedding
    except Exception as e:
        logger.warning(f"Embedding API failed, falling back to text search: {e}")
        return await _text_search_law(query, top_k, law_id)

    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    sql = """
        SELECT id, law_id, article_number, clause_path, content,
               1 - (embedding <=> $1::vector) as similarity
        FROM law_chunks
        WHERE embedding IS NOT NULL
    """
    params: list = [vec_str]
    if law_id:
        sql += " AND law_id = $2"
        params.append(law_id)
    sql += " ORDER BY embedding <=> $1::vector LIMIT $" + str(len(params) + 1)
    params.append(top_k)

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)

    # Broadcast vector search activity — no query text (PII)
    try:
        from ..services.activity_broadcaster import fire as _ab_fire
        _top = float(rows[0]["similarity"]) if rows else 0.0
        _ab_fire(
            "vector",
            "pgvector / Hologres Proxima: law chunk search",
            detail=f"top_sim={_top:.3f} · {len(rows)} hits · dim={_EMBEDDING_DIM}",
            model="text-embedding-v3",
        )
    except Exception:
        pass

    return [
        LawSearchResult(
            chunk_id=str(r["id"]),
            law_id=r["law_id"],
            article_number=r["article_number"],
            clause_path=r["clause_path"] or "",
            content=r["content"],
            similarity=float(r["similarity"]),
        )
        for r in rows
    ]


async def _text_search_law(
    query: str, top_k: int, law_id: str | None = None
) -> list[LawSearchResult]:
    """Fallback text search when embeddings are unavailable."""
    sql = """
        SELECT id, law_id, article_number, clause_path, content
        FROM law_chunks
        WHERE content ILIKE '%' || $1 || '%'
    """
    params: list = [query]
    if law_id:
        sql += " AND law_id = $2"
        params.append(law_id)
    sql += " LIMIT $" + str(len(params) + 1)
    params.append(top_k)

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        LawSearchResult(
            chunk_id=str(r["id"]),
            law_id=r["law_id"],
            article_number=r["article_number"],
            clause_path=r["clause_path"] or "",
            content=r["content"],
            similarity=0.5,
        )
        for r in rows
    ]


@router.get("/law/chunk/{chunk_id}", response_model=LawChunkResponse)
async def get_law_chunk(chunk_id: str):
    """Trả về nội dung đầy đủ của một điều khoản luật theo chunk_id.

    Endpoint công khai — citizen chatbot và LawChunkPopover đều dùng được.
    Response được cache 5 phút trong bộ nhớ.
    """
    import time

    # Check in-memory cache first
    now = time.monotonic()
    if chunk_id in _chunk_cache:
        payload, cached_at = _chunk_cache[chunk_id]
        if now - cached_at < _CHUNK_CACHE_TTL:
            return payload

    async with pg_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, law_id, article_number, clause_path, chunk_index,
                   title, content, metadata, created_at
            FROM law_chunks
            WHERE id = $1::uuid
            """,
            chunk_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy điều khoản")

    created_at_val = row["created_at"]
    if isinstance(created_at_val, datetime):
        created_at_str = created_at_val.isoformat()
    else:
        created_at_str = str(created_at_val)

    payload = {
        "chunk_id": str(row["id"]),
        "law_id": row["law_id"],
        "article_number": row["article_number"],
        "clause_path": row["clause_path"] or "",
        "chunk_index": row["chunk_index"],
        "title": row["title"],
        "content": row["content"],
        "metadata": row["metadata"] or {},
        "created_at": created_at_str,
    }

    _chunk_cache[chunk_id] = (payload, now)
    return payload


@router.get("/tthc", response_model=list[TTHCSearchResult])
async def search_tthc(query: str, user: CurrentUser, gdb: PermittedGDBDep):
    """Search TTHC procedures by keyword.

    Fetches all 5 TTHCSpecs and filters in Python with case- and diacritic-
    insensitive substring match — Vietnamese names with diacritics don't match
    cleanly through Gremlin's ``containing()`` text predicate.
    """
    import unicodedata

    def _norm(s: str) -> str:
        nfd = unicodedata.normalize("NFD", s or "")
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()

    q_norm = _norm(query)
    all_specs = await gdb.execute(
        "g.V().hasLabel('TTHCSpec').valueMap(true)",
        {},
    )
    results = [
        r
        for r in all_specs
        if q_norm in _norm(r.get("name", [""])[0] if isinstance(r.get("name"), list) else r.get("name", ""))
        or q_norm in _norm(r.get("tthc_code", r.get("code", [""]))[0] if isinstance(r.get("tthc_code", r.get("code", [])), list) else r.get("tthc_code", r.get("code", "")))
    ][:20]

    items = []
    for r in results:
        code = (r.get("tthc_code", r.get("code", [""]))[0] if isinstance(r.get("tthc_code", r.get("code", [])), list) else r.get("tthc_code", r.get("code", "")))
        components = await gdb.execute(
            "g.V().hasLabel('TTHCSpec').has('code', c).out('REQUIRES').values('name')",
            {"c": code},
        )
        comp_names = [
            c.get("value", "") if isinstance(c, dict) else str(c)
            for c in components
        ]
        items.append(
            TTHCSearchResult(
                tthc_code=code,
                name=r.get("name", [""])[0] if isinstance(r.get("name"), list) else r.get("name", ""),
                department=r.get("authority_name", r.get("department", [""]))[0] if isinstance(r.get("authority_name", r.get("department", [])), list) else r.get("authority_name", r.get("department", "")),
                sla_days=r.get("sla_days_law", r.get("sla_days", [15]))[0] if isinstance(r.get("sla_days_law", r.get("sla_days", [])), list) else r.get("sla_days_law", r.get("sla_days", 15)),
                required_components=comp_names,
            )
        )
    return items
