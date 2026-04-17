"""backend/src/main.py -- FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .database import GDBUnavailableError, RetryError, close_all_connections, init_all_connections
from .logging_config import setup_logging

# Import metrics module early so all Prometheus metrics are registered before
# the first scrape.  The module itself has no side-effects beyond registration.
try:
    from . import metrics as _metrics  # noqa: F401
except ImportError:
    pass  # metrics.py owned by Wave 3A — may not be present yet

logger = logging.getLogger("govflow.main")

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

# Module-level flag: Prometheus Instrumentator registers metrics globally
# and must only be registered once per process lifetime.
_INSTRUMENTATOR_REGISTERED: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 3.4 — structured JSON logging
    setup_logging(level=settings.log_level)

    # 3.6 — OpenTelemetry tracing
    try:
        from .telemetry import setup_tracing

        setup_tracing(service_name="govflow-backend", endpoint=settings.otel_endpoint)
    except Exception as _otel_exc:
        logger.warning("OTel setup failed: %s", _otel_exc)

    # 3.7 — Sentry error tracking
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.asyncio import AsyncioIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            def scrub_pii(event: dict, hint: dict) -> dict:  # noqa: ARG001
                """Redact PII from Sentry events before sending."""
                from .logging_config import _deep_redact

                # Scrub request body
                req = event.get("request", {})
                if req.get("data"):
                    event["request"]["data"] = _deep_redact(req["data"])

                # Scrub extra fields
                if event.get("extra"):
                    event["extra"] = _deep_redact(event["extra"])

                # Scrub user email
                user_data = event.get("user", {})
                if isinstance(user_data, dict) and user_data.get("email"):
                    from .logging_config import _EM_PATTERN

                    event["user"]["email"] = _EM_PATTERN.sub(
                        "[REDACTED_EMAIL]", user_data["email"]
                    )

                return event

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.govflow_env,
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
                integrations=[FastApiIntegration(), AsyncioIntegration()],
                before_send=scrub_pii,
            )
            logger.info("Sentry initialized for env=%s", settings.govflow_env)
        except Exception as _sentry_exc:
            logger.warning("Sentry init failed: %s", _sentry_exc)

    # 3.8 — Alembic migrations (programmatic)
    _skip_migrations = __import__("os").environ.get("SKIP_MIGRATIONS", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not _skip_migrations:
        try:
            import pathlib as _pathlib

            from alembic import command as _alembic_cmd
            from alembic.config import Config as _AlembicConfig

            _alembic_ini = (
                _pathlib.Path(__file__).resolve().parent.parent / "alembic.ini"
            )
            if _alembic_ini.exists():
                _alembic_cfg = _AlembicConfig(str(_alembic_ini))
                # Override DSN from settings at runtime
                _dsn = settings.hologres_dsn
                if _dsn.startswith("postgresql+asyncpg://"):
                    _dsn = _dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
                _alembic_cfg.set_main_option("sqlalchemy.url", _dsn)
                await __import__("asyncio").get_event_loop().run_in_executor(
                    None, _alembic_cmd.upgrade, _alembic_cfg, "head"
                )
                logger.info("Alembic migrations applied (head)")
            else:
                logger.warning("alembic.ini not found — skipping migrations")
        except Exception as _alembic_exc:
            logger.warning("Alembic migration failed (non-fatal): %s", _alembic_exc)

    await init_all_connections()

    # Idempotent migration: backfill case_type=citizen_tthc on legacy vertices
    try:
        from .database import async_gremlin_submit

        await async_gremlin_submit(
            "g.V().hasLabel('Case').not(has('case_type')).property('case_type', 'citizen_tthc')",
            {},
        )
        logger.info("lifespan: case_type migration complete")
    except Exception as exc:
        logger.warning(f"lifespan: case_type migration skipped: {exc}")
    yield
    await close_all_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title="GovFlow API",
        description="Agentic GraphRAG for Vietnamese TTHC",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # Request context middleware (3.4) — X-Request-ID / X-Correlation-ID
    # Must be added before CORS so the header is available to all handlers.
    # ------------------------------------------------------------------ #
    from .middleware.request_context import RequestContextMiddleware

    app.add_middleware(RequestContextMiddleware)

    # ------------------------------------------------------------------ #
    # CORS — explicit methods and headers (task 0.9)
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "Content-Type",
            "Authorization",
            "X-Request-ID",
            "X-Correlation-ID",
        ],
    )

    # ------------------------------------------------------------------ #
    # Audit middleware (task 1.2)
    # Logs every mutating request under /api to audit_events_flat.
    # Non-blocking: audit write runs in a fire-and-forget asyncio.create_task.
    # ------------------------------------------------------------------ #
    @app.middleware("http")
    async def audit_middleware(request: Request, call_next) -> Response:
        mutating = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        is_api = request.url.path.startswith("/api") or (
            # router prefixes don't include /api prefix — match them explicitly
            request.url.path.startswith("/cases")
            or request.url.path.startswith("/agents")
            or request.url.path.startswith("/graph")
            or request.url.path.startswith("/documents")
            or request.url.path.startswith("/search")
            or request.url.path.startswith("/leadership")
            or request.url.path.startswith("/audit")
            or request.url.path.startswith("/public")
        )
        if not (mutating and is_api):
            return await call_next(request)

        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        corr_id = request.headers.get("X-Correlation-ID")
        t0 = time.monotonic()

        response: Response = await call_next(request)
        duration_ms = (time.monotonic() - t0) * 1000

        # Resolve actor from JWT (best-effort — token may be absent on public routes)
        actor_user_id: str | None = None
        actor_role: str | None = None
        actor_clearance: int | None = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                from .auth import decode_token

                claims = decode_token(auth_header.removeprefix("Bearer ").strip())
                actor_user_id = claims.sub
                actor_role = claims.role
                actor_clearance = claims.clearance_level
        except Exception:
            pass

        # Resolve client IP: honour X-Forwarded-For in cloud mode
        client_ip: str | None = None
        fwd = request.headers.get("X-Forwarded-For")
        if fwd:
            client_ip = fwd.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host

        async def _write_audit() -> None:
            try:
                import uuid as _uuid

                from .database import get_pg_pool
                from .graph.audit import AuditEvent, AuditLogger

                try:
                    pg = get_pg_pool()
                except RuntimeError:
                    return

                audit = AuditLogger(gdb_client=None, hologres_pool=pg)
                await audit.log(
                    AuditEvent(
                        event_id=str(_uuid.uuid4()),
                        agent_id=actor_user_id or "anonymous",
                        tier="HTTP_REQUEST",
                        action="REQUEST",
                        detail=f"{request.method} {request.url.path} -> {response.status_code}",
                        query_snippet="",
                        timestamp=t0 + time.time() - time.monotonic(),  # wall clock
                        user_id=actor_user_id,
                        actor_user_id=actor_user_id,
                        actor_role=actor_role,
                        actor_clearance=actor_clearance,
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        client_ip=client_ip,
                        duration_ms=round(duration_ms, 2),
                        user_agent=request.headers.get("User-Agent"),
                        request_id=req_id,
                        correlation_id=corr_id,
                    )
                )
            except Exception as exc:
                from .graph.audit import _inc_failure

                _inc_failure()
                logger.debug("audit_middleware write failed: %s", exc)

        asyncio.create_task(_write_audit())
        return response

    # ------------------------------------------------------------------ #
    # Security headers middleware (task 0.9)
    # ------------------------------------------------------------------ #
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # HSTS — only when the request came over HTTPS or we are in cloud env
        is_https = request.url.scheme == "https"
        if is_https or settings.govflow_env == "cloud":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'"
        )

        return response

    # Rate limiting (3.9)
    from .middleware.rate_limit import limiter as _limiter
    from .middleware.rate_limit import rate_limit_exceeded_handler

    app.state.limiter = _limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    # Auth endpoint
    from .api import auth_login

    app.include_router(auth_login.router)

    # Authenticated routes
    from .api import agents, audit, cases, documents, graph, leadership, notifications, search

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

    # AI Assistant (public, SSE + JSON)
    from .api import assistant

    app.include_router(assistant.router)

    # Demo routes (permission engine showcase)
    from .api import permission_demo

    app.include_router(permission_demo.router)

    # Demo reset + utility endpoints
    from .api import demo

    app.include_router(demo.router)

    # WebSocket
    from .api import ws

    app.include_router(ws.router)

    # Data Subject Rights (3.11 — NĐ 13/2023)
    from .api import data_subject

    app.include_router(data_subject.router)

    # Static demo sample files (served at /public/samples/*)
    # Judges can fetch these via "Điền mẫu" one-click button.
    from pathlib import Path as _Path

    from fastapi.staticfiles import StaticFiles

    _samples_dir = _Path(__file__).resolve().parent.parent / "public_assets" / "samples"
    _samples_dir.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/public/samples",
        StaticFiles(directory=str(_samples_dir)),
        name="public_samples",
    )

    # ------------------------------------------------------------------ #
    # Prometheus metrics (task 3.5)
    # Exposed at /metrics (excluded from OpenAPI schema).
    # If PROMETHEUS_ALLOW_IPS is set, requests from other IPs get 403.
    # ------------------------------------------------------------------ #
    from prometheus_fastapi_instrumentator import Instrumentator

    _prometheus_allow_ips: list[str] = [
        ip.strip()
        for ip in settings.prometheus_allow_ips.split(",")
        if ip.strip()
    ]

    @app.middleware("http")
    async def prometheus_ip_guard(request: Request, call_next) -> Response:
        if request.url.path == "/metrics" and _prometheus_allow_ips:
            # Resolve the real client IP (honour X-Forwarded-For in cloud mode)
            client_ip: str = ""
            fwd = request.headers.get("X-Forwarded-For")
            if fwd:
                client_ip = fwd.split(",")[0].strip()
            elif request.client:
                client_ip = request.client.host
            if client_ip not in _prometheus_allow_ips:
                return Response(status_code=403, content="Forbidden")
        return await call_next(request)

    # Guard: only register Instrumentator once per process to avoid
    # "Duplicated timeseries in CollectorRegistry" errors in test suites
    # where create_app() is called multiple times.
    global _INSTRUMENTATOR_REGISTERED  # noqa: PLW0603
    if not _INSTRUMENTATOR_REGISTERED:
        try:
            Instrumentator(
                should_group_status_codes=True,
                should_ignore_untemplated=True,
                should_instrument_requests_inprogress=True,
                excluded_handlers=["/healthz", "/health"],
            ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
            _INSTRUMENTATOR_REGISTERED = True
        except ValueError:
            # Prometheus registry already has these metrics.
            _INSTRUMENTATOR_REGISTERED = True

    # ------------------------------------------------------------------ #
    # DB / Graph error handlers (Task 4)
    # ------------------------------------------------------------------ #
    from fastapi.responses import JSONResponse

    @app.exception_handler(GDBUnavailableError)
    async def gdb_unavailable_handler(
        request: Request, exc: GDBUnavailableError
    ) -> JSONResponse:
        logger.warning("GDB unavailable: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"error": "graph_unavailable", "retry_after": 60},
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(asyncio.TimeoutError)
    async def timeout_handler(
        request: Request, exc: asyncio.TimeoutError
    ) -> JSONResponse:
        logger.error("DB operation timed out on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=504,
            content={"error": "timeout"},
        )

    @app.exception_handler(RetryError)
    async def pg_retry_exhausted_handler(
        request: Request, exc: RetryError
    ) -> JSONResponse:
        logger.error("PostgreSQL retry exhausted on %s %s: %s", request.method, request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={"error": "database_unavailable"},
        )

    # Health check
    @app.get("/healthz", tags=["Health"])
    async def healthz():
        return {"status": "ok", "env": settings.govflow_env}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
