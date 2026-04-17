"""
backend/src/database.py
Connection factories for GDB (Gremlin), Hologres (asyncpg), and OSS.
Switches between local Docker and Alibaba Cloud based on GOVFLOW_ENV.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
import boto3
import oss2
from botocore.config import Config as BotoConfig
from gremlin_python.driver.client import Client as GremlinClient
from gremlin_python.driver.serializer import GraphSONSerializersV3d0
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .config import settings

logger = logging.getLogger("govflow.database")

# ============================================================
# Custom exceptions
# ============================================================


class GDBUnavailableError(RuntimeError):
    """Raised when the GDB circuit breaker is open or the query times out."""


# ============================================================
# Singleton holders (initialized in lifespan)
# ============================================================
_gremlin_client: GremlinClient | None = None
_pg_pool: asyncpg.Pool | None = None
_oss_client: Any = None  # oss2.Bucket (cloud) or boto3 S3 client (local)


# ============================================================
# GDB Circuit Breaker
# ============================================================


class GDBCircuitBreaker:
    """
    Thread-safe circuit breaker for the GDB (Gremlin) connection.

    State machine:
        CLOSED  → normal operation
        OPEN    → fast-fail for ``open_duration_s`` seconds after threshold failures
        HALF_OPEN → one probe request allowed after open_duration_s expires;
                    success → CLOSED, failure → OPEN again

    All public methods are synchronous so they can be called from the
    ThreadPoolExecutor that wraps the blocking Gremlin driver.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        window_s: float = 30.0,
        open_duration_s: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.window_s = window_s
        self.open_duration_s = open_duration_s

        self._failure_timestamps: list[float] = []
        self._open_until: float = 0.0  # monotonic epoch
        self._half_open_probe_allowed: bool = False
        self._state: str = self.CLOSED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prune_window(self, now: float) -> None:
        cutoff = now - self.window_s
        self._failure_timestamps = [t for t in self._failure_timestamps if t > cutoff]

    def _transition(self, new_state: str) -> None:
        if new_state != self._state:
            logger.warning(
                "GDBCircuitBreaker state: %s → %s",
                self._state,
                new_state,
            )
            self._state = new_state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def can_proceed(self) -> bool:
        """Return True if a query may proceed; updates state if open window expired."""
        now = time.monotonic()

        if self._state == self.CLOSED:
            return True

        if self._state == self.OPEN:
            if now >= self._open_until:
                # Window expired — allow one probe
                self._half_open_probe_allowed = True
                self._transition(self.HALF_OPEN)
                return True
            return False

        # HALF_OPEN
        if self._half_open_probe_allowed:
            # Consume the single probe slot
            self._half_open_probe_allowed = False
            return True
        return False

    def record_success(self) -> None:
        """Record a successful Gremlin call; transitions HALF_OPEN → CLOSED."""
        self._failure_timestamps.clear()
        self._open_until = 0.0
        self._half_open_probe_allowed = False
        self._transition(self.CLOSED)

    def record_failure(self) -> None:
        """Record a failed Gremlin call; opens circuit if threshold is reached."""
        now = time.monotonic()
        self._failure_timestamps.append(now)
        self._prune_window(now)

        if len(self._failure_timestamps) >= self.failure_threshold:
            self._open_until = now + self.open_duration_s
            self._half_open_probe_allowed = False
            self._transition(self.OPEN)


# Singleton breaker shared across all callers
_gdb_circuit_breaker = GDBCircuitBreaker()


# ============================================================
# GDB (Gremlin)
# ============================================================
def create_gremlin_client() -> GremlinClient:
    """Create a gremlinpython Client connected to GDB or local TinkerGraph."""
    global _gremlin_client

    url = settings.gdb_endpoint
    logger.info(f"Connecting to Gremlin at {url}")

    kwargs = {
        "url": url,
        "traversal_source": "g",
        "message_serializer": GraphSONSerializersV3d0(),
    }

    # Cloud GDB requires username/password
    if settings.govflow_env == "cloud" and settings.gdb_username:
        kwargs["username"] = settings.gdb_username
        kwargs["password"] = settings.gdb_password

    _gremlin_client = GremlinClient(**kwargs)
    return _gremlin_client


def get_gremlin_client() -> GremlinClient:
    """Return the singleton Gremlin client. Raises if not initialized."""
    if _gremlin_client is None:
        raise RuntimeError("Gremlin client not initialized. Call create_gremlin_client() first.")
    return _gremlin_client


def _close_gremlin_sync() -> None:
    """Close the Gremlin client (sync, safe to call from thread)."""
    global _gremlin_client
    if _gremlin_client:
        _gremlin_client.close()
        _gremlin_client = None
        logger.info("Gremlin client closed")


def close_gremlin_client() -> None:
    """Close the Gremlin client. Handles event loop conflicts."""
    global _gremlin_client
    if _gremlin_client:
        try:
            _gremlin_client.close()
        except RuntimeError:
            # Event loop conflict — force cleanup without async close
            _gremlin_client = None
            logger.info("Gremlin client released (forced)")
            return
        _gremlin_client = None
        logger.info("Gremlin client closed")


# Gremlin Python driver is synchronous. We wrap it in a ThreadPoolExecutor
# to avoid blocking the async event loop. Pool size of 4 matches typical
# concurrent agent count. For production with Alibaba Cloud GDB, consider
# evaluating aiohttp-based async Gremlin drivers if/when they mature.
_GREMLIN_POOL_SIZE = 4
_gremlin_executor = ThreadPoolExecutor(
    max_workers=_GREMLIN_POOL_SIZE, thread_name_prefix="gremlin"
)


def _sanitize_gremlin(value: Any) -> Any:
    """Convert Gremlin results to JSON-safe Python types.

    ValueMap(true) returns dicts keyed by Gremlin T enum (T.id, T.label) — those
    blow up json.dumps downstream. Stringify all keys and recurse through lists.
    """
    # Import here to avoid hard dependency on gremlinpython internals
    try:
        from gremlin_python.process.traversal import T
    except Exception:  # pragma: no cover
        T = None
    if isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            if T is not None and isinstance(k, T):
                cleaned[k.name] = _sanitize_gremlin(v)
            elif not isinstance(k, (str, int, float, bool, type(None))):
                cleaned[str(k)] = _sanitize_gremlin(v)
            else:
                cleaned[k] = _sanitize_gremlin(v)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_gremlin(v) for v in value]
    return value


def _gremlin_submit_sync(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query synchronously (must run in non-async thread).

    Checks the circuit breaker before attempting the query; records success/failure
    so the breaker can transition between CLOSED / OPEN / HALF_OPEN.
    """
    cb = _gdb_circuit_breaker
    if not cb.can_proceed():
        raise GDBUnavailableError(
            "GDB circuit breaker is OPEN — refusing query to avoid thread pool exhaustion"
        )
    try:
        client = get_gremlin_client()
        result_set = client.submit(query, bindings or {})
        raw = result_set.all().result()
        result = _sanitize_gremlin(raw)
        cb.record_success()
        return result
    except GDBUnavailableError:
        raise
    except Exception:
        cb.record_failure()
        raise


def gremlin_submit(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query and return results as a list.
    Safe to call from both sync and async contexts.
    When called from async context, runs in thread executor.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — call directly
        return _gremlin_submit_sync(query, bindings)
    # Running inside async loop — delegate to thread pool
    future = _gremlin_executor.submit(_gremlin_submit_sync, query, bindings)
    return future.result(timeout=30)


def _gdb_activity_label(query: str) -> tuple[str, str] | None:
    """Summarize a Gremlin query for the activity panel (no PII leaked).

    Returns (label, detail) or None if we should skip (too chatty).
    """
    q = query.strip()
    lower = q.lower()
    # Only broadcast interesting queries: vertex/edge creates and major traversals
    if ".addv(" in lower:
        # Extract vertex label from addV('Label')
        m = re.search(r"addV\(\s*['\"]([^'\"]+)", q)
        label = m.group(1) if m else "vertex"
        return ("Alibaba GDB: addVertex", f"label={label}")
    if ".adde(" in lower:
        m = re.search(r"addE\(\s*['\"]([^'\"]+)", q)
        label = m.group(1) if m else "edge"
        return ("Alibaba GDB: addEdge", f"label={label}")
    if ".out(" in lower or ".in(" in lower or ".valuemap" in lower or ".count()" in lower:
        return ("Alibaba GDB: traversal", "Gremlin query")
    return None


async def async_gremlin_submit(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query asynchronously without blocking the event loop.
    Use this from agent runtime code where multiple agents run concurrently.
    """
    loop = asyncio.get_running_loop()
    _t0 = time.monotonic()
    result = await loop.run_in_executor(
        _gremlin_executor, _gremlin_submit_sync, query, bindings
    )
    _dur = (time.monotonic() - _t0) * 1000
    try:
        summary = _gdb_activity_label(query)
        if summary:
            from .services.activity_broadcaster import fire as _ab_fire
            label, detail = summary
            _ab_fire("graph", label, detail=detail, duration_ms=_dur)
    except Exception:
        pass
    return result


# ============================================================
# Timeout envelope helper
# ============================================================


async def with_timeout(coro: Any, timeout: float = 25.0, op_name: str = "db-op") -> Any:
    """Await *coro* with a hard timeout.

    On ``asyncio.TimeoutError``, logs the event at ERROR level and re-raises so
    the HTTP layer can map it to a 504 response.

    Args:
        coro:     An awaitable (coroutine or task).
        timeout:  Seconds before timeout (default 25 — safely under the 30s GDB pool
                  timeout and the 30s asyncpg command_timeout).
        op_name:  Label used in the log message for fast triage.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except TimeoutError:
        logger.error(
            "with_timeout: operation '%s' exceeded %.1fs deadline — aborting",
            op_name,
            timeout,
        )
        raise


# ============================================================
# Hologres / PostgreSQL (asyncpg)
# ============================================================

# Tenacity retry decorator: only retries on transient connection errors.
# Syntax/authentication errors are NOT retried (reraise=True propagates them).
_PG_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=0.5, max=8.0),
    retry=retry_if_exception_type(
        (asyncpg.PostgresConnectionError, asyncpg.ConnectionDoesNotExistError)
    ),
    reraise=True,
)


async def create_pg_pool() -> asyncpg.Pool:
    """Create an asyncpg connection pool to Hologres or local Postgres."""
    global _pg_pool

    dsn = settings.hologres_dsn
    logger.info(f"Connecting to PostgreSQL at {dsn.split('@')[1] if '@' in dsn else dsn}")

    _pg_pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )
    return _pg_pool


def get_pg_pool() -> asyncpg.Pool:
    """Return the singleton asyncpg pool. Raises if not initialized."""
    if _pg_pool is None:
        raise RuntimeError("PostgreSQL pool not initialized. Call create_pg_pool() first.")
    return _pg_pool


async def close_pg_pool() -> None:
    """Close the asyncpg pool."""
    global _pg_pool
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
        logger.info("PostgreSQL pool closed")


@asynccontextmanager
async def pg_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """Acquire a connection from the pool as an async context manager."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        yield conn


@_PG_RETRY
async def pg_fetch(sql: str, *args: Any) -> list[asyncpg.Record]:
    """Execute a SELECT and return all rows, with automatic retry on connection errors."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)


@_PG_RETRY
async def pg_fetchrow(sql: str, *args: Any) -> asyncpg.Record | None:
    """Execute a SELECT and return the first row, with automatic retry on connection errors."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)


@_PG_RETRY
async def pg_fetchval(sql: str, *args: Any) -> Any:
    """Execute a SELECT and return a scalar value, with automatic retry on connection errors."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, *args)


@_PG_RETRY
async def pg_execute(sql: str, *args: Any) -> str:
    """Execute a DML/DDL statement, with automatic retry on connection errors."""
    pool = get_pg_pool()
    async with pool.acquire() as conn:
        return await conn.execute(sql, *args)


# ============================================================
# OSS / MinIO
# ============================================================
def create_oss_client() -> Any:
    """Create storage client. Uses boto3 for local MinIO, oss2 for cloud OSS."""
    global _oss_client

    endpoint = settings.oss_endpoint
    logger.info(f"Connecting to OSS at {endpoint}")

    if settings.govflow_env == "local":
        # MinIO requires S3-compatible client with AWS4-HMAC-SHA256
        _oss_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.oss_access_key_id,
            aws_secret_access_key=settings.oss_access_key_secret,
            region_name=settings.oss_region,
            config=BotoConfig(signature_version="s3v4"),
        )
    else:
        # Alibaba Cloud OSS
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        _oss_client = oss2.Bucket(auth, endpoint, settings.oss_bucket)

    return _oss_client


def get_oss_client() -> Any:
    """Return the singleton OSS client. Raises if not initialized."""
    if _oss_client is None:
        raise RuntimeError("OSS client not initialized. Call create_oss_client() first.")
    return _oss_client


def oss_put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Upload an object to OSS/MinIO. Returns the object key."""
    client = get_oss_client()
    if settings.govflow_env == "local":
        client.put_object(
            Bucket=settings.oss_bucket, Key=key, Body=data, ContentType=content_type
        )
    else:
        client.put_object(key, data, headers={"Content-Type": content_type})
    logger.info(f"Uploaded {key} ({len(data)} bytes)")
    return key


def oss_put_signed_url(key: str, expires: int = 3600) -> str:
    """Generate a pre-signed PUT URL for uploading an object."""
    client = get_oss_client()
    if settings.govflow_env == "local":
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.oss_bucket, "Key": key},
            ExpiresIn=expires,
        )
    else:
        url = client.sign_url("PUT", key, expires)
    # Broadcast OSS activity (extension only, no key path with PII)
    try:
        from .services.activity_broadcaster import fire as _ab_fire
        _ext = key.rsplit(".", 1)[-1] if "." in key else "bin"
        _ab_fire(
            "oss",
            "Alibaba Cloud OSS: presigned PUT",
            detail=f"ext={_ext} · expires={expires}s",
        )
    except Exception:
        pass
    return url


def oss_get_signed_url(key: str, expires: int = 3600) -> str:
    """Generate a pre-signed GET URL for an object."""
    client = get_oss_client()
    if settings.govflow_env == "local":
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.oss_bucket, "Key": key},
            ExpiresIn=expires,
        )
    else:
        return client.sign_url("GET", key, expires)


# ============================================================
# Lifespan helpers (called from main.py)
# ============================================================
async def init_all_connections() -> None:
    """Initialize all database connections. Called during FastAPI lifespan startup."""
    create_gremlin_client()
    await create_pg_pool()
    create_oss_client()
    logger.info("All connections initialized")

    # Quick health check — reuse the shared gremlin executor
    try:
        result = await async_gremlin_submit("g.V().count()")
        logger.info(f"GDB vertex count: {result}")
    except Exception as e:
        logger.warning(f"GDB health check failed: {e}")

    try:
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT 1")
            logger.info(f"PostgreSQL health check: {val}")
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")


async def close_all_connections() -> None:
    """Close all database connections. Called during FastAPI lifespan shutdown."""
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(_gremlin_executor, _close_gremlin_sync)
    await close_pg_pool()
    _gremlin_executor.shutdown(wait=False)
    logger.info("All connections closed")


# Re-export RetryError so callers can catch tenacity exhaustion without
# importing tenacity directly.
__all__ = [
    "GDBUnavailableError",
    "GDBCircuitBreaker",
    "RetryError",
    "with_timeout",
    "pg_fetch",
    "pg_fetchrow",
    "pg_fetchval",
    "pg_execute",
]
