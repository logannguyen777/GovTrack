"""backend/src/api/search.py"""
import logging

from fastapi import APIRouter, HTTPException
from openai import OpenAI

from ..auth import CurrentUser
from ..config import settings
from ..database import pg_connection, gremlin_submit
from ..models.schemas import LawSearchResult, TTHCSearchResult

logger = logging.getLogger("govflow.search")
router = APIRouter(prefix="/search", tags=["Search"])

# DashScope text-embedding-v3 supports 512, 768, 1024 only
_EMBEDDING_DIM = 1024


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

    return [
        LawSearchResult(
            chunk_id=str(r["id"]), law_id=r["law_id"],
            article_number=r["article_number"], clause_path=r["clause_path"] or "",
            content=r["content"], similarity=float(r["similarity"]),
        )
        for r in rows
    ]


async def _text_search_law(query: str, top_k: int, law_id: str | None = None) -> list[LawSearchResult]:
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
            chunk_id=str(r["id"]), law_id=r["law_id"],
            article_number=r["article_number"], clause_path=r["clause_path"] or "",
            content=r["content"], similarity=0.5,
        )
        for r in rows
    ]


@router.get("/tthc", response_model=list[TTHCSearchResult])
async def search_tthc(query: str, user: CurrentUser):
    """Search TTHC procedures by keyword (Gremlin text match)."""
    results = gremlin_submit(
        "g.V().hasLabel('TTHCSpec')"
        ".has('name', containing(q))"
        ".valueMap(true).limit(20)",
        {"q": query},
    )
    items = []
    for r in results:
        code = r.get("tthc_code", r.get("code", [""]))[0]
        components = gremlin_submit(
            "g.V().hasLabel('TTHCSpec').has('code', c).out('REQUIRES').values('name')",
            {"c": code},
        )
        items.append(TTHCSearchResult(
            tthc_code=code, name=r.get("name", [""])[0],
            department=r.get("authority_name", r.get("department", [""]))[0],
            sla_days=r.get("sla_days_law", r.get("sla_days", [15]))[0],
            required_components=components,
        ))
    return items
