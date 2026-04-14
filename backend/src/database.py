"""
backend/src/database.py
Connection factories for GDB (Gremlin), Hologres (asyncpg), and OSS.
Switches between local Docker and Alibaba Cloud based on GOVFLOW_ENV.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from typing import Any

import asyncpg
import boto3
import oss2
from botocore.config import Config as BotoConfig
from gremlin_python.driver.client import Client as GremlinClient
from gremlin_python.driver.serializer import GraphSONSerializersV3d0

from .config import settings

logger = logging.getLogger("govflow.database")

# ============================================================
# Singleton holders (initialized in lifespan)
# ============================================================
_gremlin_client: GremlinClient | None = None
_pg_pool: asyncpg.Pool | None = None
_oss_client: Any = None  # oss2.Bucket (cloud) or boto3 S3 client (local)


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


def _gremlin_submit_sync(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query synchronously (must run in non-async thread)."""
    client = get_gremlin_client()
    result_set = client.submit(query, bindings or {})
    return result_set.all().result()


def gremlin_submit(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query and return results as a list.
    Safe to call from both sync and async contexts.
    When called from async context, runs in thread executor.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — call directly
        return _gremlin_submit_sync(query, bindings)
    # Running inside async loop — delegate to thread pool
    import concurrent.futures
    future = _gremlin_executor.submit(_gremlin_submit_sync, query, bindings)
    return future.result(timeout=30)


async def async_gremlin_submit(query: str, bindings: dict | None = None) -> list:
    """Submit a Gremlin query asynchronously without blocking the event loop.
    Use this from agent runtime code where multiple agents run concurrently.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _gremlin_executor, _gremlin_submit_sync, query, bindings
    )


# ============================================================
# Hologres / PostgreSQL (asyncpg)
# ============================================================
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
        return client.generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.oss_bucket, "Key": key},
            ExpiresIn=expires,
        )
    else:
        return client.sign_url("PUT", key, expires)


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
