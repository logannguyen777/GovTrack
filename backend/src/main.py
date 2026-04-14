"""backend/src/main.py -- FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .database import init_all_connections, close_all_connections

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_all_connections()
    yield
    await close_all_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GovFlow API",
        description="Agentic GraphRAG for Vietnamese TTHC",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Auth endpoint
    from .api import auth_login
    app.include_router(auth_login.router)

    # Authenticated routes
    from .api import cases, documents, agents, graph, search
    from .api import notifications, leadership, audit
    app.include_router(cases.router)
    app.include_router(documents.router)
    app.include_router(agents.router)
    app.include_router(graph.router)
    app.include_router(search.router)
    app.include_router(notifications.router)
    app.include_router(leadership.router)
    app.include_router(audit.router)

    # Public routes (no auth)
    from .api import public
    app.include_router(public.router)

    # Demo routes (permission engine showcase)
    from .api import permission_demo
    app.include_router(permission_demo.router)

    # WebSocket
    from .api import ws
    app.include_router(ws.router)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
