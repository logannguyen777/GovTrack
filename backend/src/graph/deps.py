"""
FastAPI dependency factories for the permission-aware Gremlin client.

Usage in route handlers::

    from ..graph.deps import get_permitted_gdb, PermittedGDBDep
    from ..graph.deps import get_public_permitted_gdb, PublicPermittedGDBDep

    @router.get("/cases/{case_id}")
    async def get_case(case_id: str, gdb: PermittedGDBDep):
        results = await gdb.execute("g.V().has('Case','case_id',cid)", {"cid": case_id})
        ...

    # For public (no-auth) routes:
    @router.get("/public/track/{code}")
    async def track(code: str, gdb: PublicPermittedGDBDep):
        ...
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPBearer

from ..auth import UserSession, get_current_session
from .permitted_client import PermittedGremlinClient

_bearer = HTTPBearer()


async def get_permitted_gdb(
    session: UserSession = Depends(get_current_session),
) -> PermittedGremlinClient:
    """Return a per-request PermittedGremlinClient for authenticated routes."""
    return PermittedGremlinClient(session)


async def get_public_permitted_gdb() -> PermittedGremlinClient:
    """Return a per-request PermittedGremlinClient for public (no-auth) routes."""
    from ..auth import PUBLIC_SESSION

    return PermittedGremlinClient(PUBLIC_SESSION)


# Annotated type aliases for concise route signatures
PermittedGDBDep = Annotated[PermittedGremlinClient, Depends(get_permitted_gdb)]
PublicPermittedGDBDep = Annotated[PermittedGremlinClient, Depends(get_public_permitted_gdb)]
