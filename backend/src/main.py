from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Connect to GDB, Hologres, OSS on startup; close on shutdown."""
    # Connections initialized in 01-infrastructure.md
    print(f"[GovFlow] Starting in {settings.govflow_env} mode")
    yield
    print("[GovFlow] Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="GovFlow API",
        description="Agentic GraphRAG for Vietnamese TTHC",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes registered in 03-backend-api.md
    @app.get("/health")
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
