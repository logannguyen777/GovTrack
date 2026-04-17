"""
Shared fixtures for all GovFlow integration tests.
All fixtures use REAL infrastructure — no mocks.
- TinkerGraph via Gremlin Server (Docker)
- PostgreSQL via asyncpg (Docker)
- MinIO via boto3 (Docker)
- FastAPI app via httpx AsyncClient (in-process)
"""
from __future__ import annotations

import os
import pytest
import asyncpg
import boto3
from botocore.config import Config as BotoConfig
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY as _PROM_REGISTRY

from gremlin_python.driver.client import Client as GremlinRawClient
from gremlin_python.driver.serializer import GraphSONSerializersV3d0
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.driver.driver_remote_connection import DriverRemoteConnection

from src.auth import create_access_token
from src.models.schemas import AgentProfile
from src.models.enums import ClearanceLevel
from src.graph.audit import AuditLogger


# ---------------------------------------------------------------------------
# Prometheus registry cleanup
# Runs before every test to prevent "Duplicated timeseries" errors when
# multiple test functions call create_app() in the same process.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_prometheus_registry():
    """Clear the default Prometheus REGISTRY and reset the instrumentation flag
    before each test so that create_app() can re-register metrics safely."""
    # Unregister all collectors from the default registry
    collectors = list(_PROM_REGISTRY._collector_to_names.keys())
    for c in collectors:
        try:
            _PROM_REGISTRY.unregister(c)
        except Exception:
            pass

    # Reset the module-level guard so the next create_app() re-instruments
    try:
        import src.main as _main_module
        _main_module._INSTRUMENTATOR_REGISTERED = False
    except Exception:
        pass

    yield


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GREMLIN_URL = os.getenv("GDB_ENDPOINT", "ws://localhost:8182/gremlin")
PG_DSN = os.getenv("HOLOGRES_DSN", "postgresql://govflow:govflow_dev_2026@localhost:5433/govflow")
MINIO_ENDPOINT = os.getenv("OSS_ENDPOINT", "http://localhost:9100")
MINIO_ACCESS_KEY = os.getenv("OSS_ACCESS_KEY_ID", "minioadmin")
MINIO_SECRET_KEY = os.getenv("OSS_ACCESS_KEY_SECRET", "minioadmin")
MINIO_BUCKET = os.getenv("OSS_BUCKET", "govflow-dev")

# DashScope availability (tests that need LLM are skipped if not set)
# Read from pydantic settings which loads .env, fallback to os.getenv
try:
    from src.config import settings as _settings
    DASHSCOPE_API_KEY = _settings.dashscope_api_key or ""
except Exception:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")


# ---------------------------------------------------------------------------
# Gremlin connection (session-scoped for performance)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def gremlin_connection():
    """Real TinkerGraph Gremlin Server connection (session-scoped)."""
    try:
        conn = DriverRemoteConnection(GREMLIN_URL, "g")
        g = traversal().withRemote(conn)
        # Verify connection
        g.V().count().next()
        yield g
        conn.close()
    except Exception:
        pytest.skip("Gremlin Server not available at " + GREMLIN_URL)


@pytest.fixture
def clean_graph(gremlin_connection):
    """Drop all vertices before each test for isolation."""
    gremlin_connection.V().drop().iterate()
    yield gremlin_connection
    # Cleanup after test as well
    gremlin_connection.V().drop().iterate()


# ---------------------------------------------------------------------------
# PostgreSQL pool (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
async def pg_pool():
    """Real asyncpg connection pool to PostgreSQL."""
    try:
        pool = await asyncpg.create_pool(dsn=PG_DSN, min_size=1, max_size=5, command_timeout=15)
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        yield pool
        await pool.close()
    except Exception:
        pytest.skip("PostgreSQL not available at " + PG_DSN)


@pytest.fixture
async def clean_pg():
    """Clean analytics and audit tables before each test.

    Creates a fresh asyncpg pool in the current function-scoped event loop
    rather than reusing the session-scoped pg_pool, which may be bound to a
    different event loop when tests run in asyncio_mode=auto.
    """
    try:
        pool = await asyncpg.create_pool(dsn=PG_DSN, min_size=1, max_size=3, command_timeout=15)
    except Exception:
        pytest.skip("PostgreSQL not available at " + PG_DSN)
        return

    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM audit_events_flat")
            await conn.execute("DELETE FROM analytics_agents")
            await conn.execute("DELETE FROM analytics_cases")
            await conn.execute("DELETE FROM notifications")
        yield pool
    finally:
        await pool.close()


# ---------------------------------------------------------------------------
# MinIO / OSS client (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def oss_client():
    """Real boto3 S3 client pointing to MinIO."""
    try:
        client = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=BotoConfig(signature_version="s3v4"),
        )
        # Verify connection
        client.list_buckets()
        yield client
    except Exception:
        pytest.skip("MinIO not available at " + MINIO_ENDPOINT)


# ---------------------------------------------------------------------------
# JWT auth tokens (session-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def auth_headers_admin():
    """JWT headers for admin user."""
    token = create_access_token(
        user_id="test-admin-001",
        username="admin_test",
        role="admin",
        clearance_level=3,
        departments=["dept-all"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_headers_officer():
    """JWT headers for officer user."""
    token = create_access_token(
        user_id="test-officer-001",
        username="officer_test",
        role="officer",
        clearance_level=1,
        departments=["dept-xaydung"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_headers_leader():
    """JWT headers for leader user."""
    token = create_access_token(
        user_id="test-leader-001",
        username="leader_test",
        role="leader",
        clearance_level=2,
        departments=["dept-all"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def auth_headers_citizen():
    """JWT headers for public_viewer (citizen) user."""
    token = create_access_token(
        user_id="test-citizen-001",
        username="citizen_test",
        role="public_viewer",
        clearance_level=0,
        departments=[],
    )
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# FastAPI test client (function-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture
async def app_client():
    """
    Real FastAPI app with full lifespan (GDB + PG + OSS connections).
    Forces re-initialization of all connections to handle stale state
    from prior test modules (e.g., after benchmark tests close pools).
    """
    from src.main import create_app
    import src.database as db

    # Force re-create all connections (handles stale pools from prior tests)
    try:
        db.create_gremlin_client()
    except Exception:
        pass
    try:
        # Re-create the executor if it was shut down
        from concurrent.futures import ThreadPoolExecutor
        if db._gremlin_executor._shutdown:
            db._gremlin_executor = ThreadPoolExecutor(
                max_workers=4, thread_name_prefix="gremlin"
            )
    except Exception:
        pass
    try:
        await db.create_pg_pool()
    except Exception:
        pass
    try:
        db.create_oss_client()
    except Exception:
        pass

    fresh_app = create_app()
    transport = ASGITransport(app=fresh_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# Agent profile factory (helper, not a fixture)
# ---------------------------------------------------------------------------
def make_agent_profile(agent_id: str, **overrides) -> AgentProfile:
    """Create an AgentProfile for testing. Matches real YAML profiles."""
    PROFILES = {
        "intake_agent": dict(
            agent_id="intake_agent", agent_name="Intake",
            clearance=ClearanceLevel.UNCLASSIFIED,
            read_node_labels=["Case", "Document", "Task"],
            write_node_labels=["Case", "Task", "AgentStep"],
            read_edge_types=["HAS_DOCUMENT", "TRIGGERED_BY"],
            write_edge_types=["PRODUCED", "HAS_DOCUMENT"],
            forbidden_properties=["national_id", "tax_id"],
        ),
        "summary_agent": dict(
            agent_id="summary_agent", agent_name="Summary",
            clearance=ClearanceLevel.UNCLASSIFIED,
            read_node_labels=["Case", "Document", "Gap", "Citation", "Decision"],
            write_node_labels=[],
            read_edge_types=["HAS_DOCUMENT", "HAS_GAP", "CITES", "DECIDED_BY"],
            write_edge_types=[],
            forbidden_properties=["national_id", "tax_id", "phone_number"],
        ),
        "legal_search_agent": dict(
            agent_id="legal_search_agent", agent_name="LegalSearch",
            clearance=ClearanceLevel.CONFIDENTIAL,
            read_node_labels=["LawArticle", "Citation", "Case"],
            write_node_labels=["Citation", "Task"],
            read_edge_types=["CITES", "REFERENCES"],
            write_edge_types=["CITES"],
            forbidden_properties=["national_id"],
        ),
        "compliance_agent": dict(
            agent_id="compliance_agent", agent_name="Compliance",
            clearance=ClearanceLevel.SECRET,
            read_node_labels=["Case", "Document", "Gap", "Citation", "Requirement"],
            write_node_labels=["Decision", "Task"],
            read_edge_types=["HAS_DOCUMENT", "HAS_GAP", "CITES", "REQUIRES"],
            write_edge_types=["DECIDED_BY"],
            forbidden_properties=[],
        ),
    }
    defaults = PROFILES.get(agent_id, PROFILES["intake_agent"])
    defaults.update(overrides)
    return AgentProfile(**defaults)


# ---------------------------------------------------------------------------
# Audit logger (real, function-scoped)
# ---------------------------------------------------------------------------
@pytest.fixture
async def real_audit_logger(pg_pool):
    """Real AuditLogger backed by real Gremlin + PostgreSQL."""
    from src.database import get_gremlin_client
    try:
        gdb = get_gremlin_client()
    except RuntimeError:
        gdb = None
    return AuditLogger(gdb_client=gdb, hologres_pool=pg_pool)


# ---------------------------------------------------------------------------
# DashScope availability marker
# ---------------------------------------------------------------------------
requires_dashscope = pytest.mark.skipif(
    not DASHSCOPE_API_KEY,
    reason="DASHSCOPE_API_KEY not set — skipping tests that require real LLM"
)
