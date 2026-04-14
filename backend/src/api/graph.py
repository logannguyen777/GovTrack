"""backend/src/api/graph.py"""
import time

from fastapi import APIRouter, Depends

from ..auth import CurrentUser, TokenClaims, require_role
from ..database import gremlin_submit
from ..models.schemas import (
    GraphQueryRequest, GraphQueryResponse,
    SubgraphResponse, GraphNode, GraphEdge,
)

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(
    body: GraphQueryRequest,
    user: TokenClaims = Depends(require_role("admin")),
):
    """Execute a raw Gremlin query (admin only)."""
    start = time.monotonic()
    result = gremlin_submit(body.query, body.bindings)
    elapsed = (time.monotonic() - start) * 1000
    return GraphQueryResponse(result=result, execution_time_ms=round(elapsed, 2))


@router.get("/case/{case_id}/subgraph", response_model=SubgraphResponse)
async def get_case_subgraph(case_id: str, user: CurrentUser):
    """Get the case subgraph for React Flow visualization."""
    # Get vertices using elementMap() which returns id, label, and properties
    vertices = gremlin_submit(
        "g.V().has('Case', 'case_id', cid)"
        ".bothE().bothV().dedup().elementMap()",
        {"cid": case_id},
    )
    # Get edges
    edges = gremlin_submit(
        "g.V().has('Case', 'case_id', cid)"
        ".bothE().project('id','source','target','label')"
        ".by(id).by(outV().id()).by(inV().id()).by(label)",
        {"cid": case_id},
    )

    nodes = []
    for v in vertices:
        v_id = ""
        v_label = ""
        props = {}
        for k, val in v.items():
            k_str = str(k)
            # gremlin_python T enum: <T.id: 1>, <T.label: 4>
            if "T.id" in k_str:
                v_id = str(val)
            elif "T.label" in k_str:
                v_label = str(val)
            else:
                props[str(k)] = val
        nodes.append(GraphNode(id=v_id, label=v_label, properties=props))

    edge_list = [
        GraphEdge(
            id=str(e["id"]), source=str(e["source"]),
            target=str(e["target"]), label=e["label"],
        )
        for e in edges
    ]
    return SubgraphResponse(nodes=nodes, edges=edge_list)
