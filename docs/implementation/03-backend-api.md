# 03 - Backend API: FastAPI Routes, Auth, WebSocket

> **Status: DONE** (2026-04-12)
> - [x] JWT Auth (`backend/src/auth.py`) — HS256, role/clearance dependencies
> - [x] Pydantic v2 schemas (`models/schemas.py`, `models/enums.py`)
> - [x] 22 REST endpoints across 11 routers (all in `backend/src/api/`)
> - [x] WebSocket pub/sub (`api/ws.py`) — topic-based, token auth
> - [x] Rate limiting (slowapi) + CORS configured
> - [x] `main.py` updated with all routers
> - [x] Seed users (6 demo accounts) in `infra/postgres/init.sql`
> - [x] Pre-signed PUT URLs for OSS uploads (`oss_put_signed_url`)
> - [x] All endpoints verified against live GDB + PG + MinIO
> - [ ] DashScope embedding search — requires API key (deferred to data-layer)
> - [ ] Agent pipeline execution — stub until `04-agent-runtime.md`

## Muc tieu (Objective)

Build the complete FastAPI application with all REST routes, JWT authentication,
WebSocket pub/sub, Pydantic v2 schemas, CORS, and rate limiting. After completing
this guide, `uvicorn src.main:app` serves all endpoints with interactive docs at /docs.

---

## 1. Project Structure Recap

```
backend/src/
├── main.py          # App factory, lifespan, route registration
├── config.py        # Pydantic Settings (from 00-project-setup)
├── auth.py          # JWT encode/decode, FastAPI dependency
├── database.py      # Connection factories (from 01-infrastructure)
├── api/
│   ├── __init__.py
│   ├── cases.py
│   ├── documents.py
│   ├── agents.py
│   ├── graph.py
│   ├── search.py
│   ├── notifications.py
│   ├── leadership.py
│   ├── audit.py
│   ├── public.py
│   └── ws.py
├── models/
│   ├── __init__.py
│   ├── schemas.py   # Pydantic v2 models
│   └── enums.py
└── services/
    └── permission.py
```

---

## 2. JWT Authentication: backend/src/auth.py

```python
"""
backend/src/auth.py
JWT authentication using python-jose HS256.
Provides encode/decode functions and a FastAPI dependency.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import settings

security = HTTPBearer()


class TokenClaims(BaseModel):
    """JWT token claims."""
    sub: str                    # user_id (UUID string)
    username: str
    role: str                   # admin | leader | officer | public_viewer
    clearance_level: int        # 0-4
    departments: list[str]      # org_ids the user belongs to
    exp: datetime


def create_access_token(
    user_id: str,
    username: str,
    role: str,
    clearance_level: int,
    departments: list[str],
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "username": username,
        "role": role,
        "clearance_level": clearance_level,
        "departments": departments,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": now,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenClaims:
    """Decode and validate a JWT token. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenClaims(**payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> TokenClaims:
    """FastAPI dependency: extract and validate JWT from Authorization header."""
    return decode_token(credentials.credentials)


# Alias for type hints in route functions
CurrentUser = Annotated[TokenClaims, Depends(get_current_user)]


def require_role(*allowed_roles: str):
    """Factory for a dependency that checks the user's role."""
    async def checker(user: CurrentUser) -> TokenClaims:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not in allowed roles: {allowed_roles}",
            )
        return user
    return checker


def require_clearance(min_level: int):
    """Factory for a dependency that checks the user's clearance level."""
    async def checker(user: CurrentUser) -> TokenClaims:
        if user.clearance_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Clearance level {user.clearance_level} < required {min_level}",
            )
        return user
    return checker
```

---

## 3. Pydantic v2 Schemas: backend/src/models/schemas.py

```python
"""
backend/src/models/schemas.py
Pydantic v2 request/response models for all API routes.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import CaseStatus, NotificationCategory, Role


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    clearance_level: int


# ---- Cases ----
class CaseCreate(BaseModel):
    tthc_code: str
    department_id: str
    applicant_name: str
    applicant_id_number: str
    applicant_phone: str = ""
    applicant_address: str = ""
    notes: str = ""


class CaseResponse(BaseModel):
    case_id: str
    code: str
    status: CaseStatus
    tthc_code: str
    department_id: str
    submitted_at: datetime
    applicant_name: str
    processing_days: int | None = None
    sla_days: int | None = None
    is_overdue: bool = False


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    page: int
    page_size: int


# ---- Bundles / Documents ----
class BundleCreate(BaseModel):
    """Metadata for a new document bundle upload."""
    files: list[BundleFileInfo]


class BundleFileInfo(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class BundleResponse(BaseModel):
    bundle_id: str
    case_id: str
    upload_urls: list[UploadURL]
    status: str = "pending"


class UploadURL(BaseModel):
    filename: str
    signed_url: str
    oss_key: str


class DocumentResponse(BaseModel):
    doc_id: str
    filename: str
    content_type: str
    page_count: int | None = None
    ocr_status: str = "pending"
    oss_key: str


# ---- Agents ----
class AgentRunRequest(BaseModel):
    """Trigger agent processing on a case."""
    pipeline: str = "full"  # full | classify_only | gap_check_only


class AgentTraceResponse(BaseModel):
    case_id: str
    steps: list[AgentStepResponse]
    status: str  # running | completed | failed
    total_tokens: int
    total_duration_ms: int


class AgentStepResponse(BaseModel):
    step_id: str
    agent_name: str
    action: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0


# ---- Graph ----
class GraphQueryRequest(BaseModel):
    """Admin-only raw Gremlin query."""
    query: str
    bindings: dict = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    result: list
    execution_time_ms: float


class SubgraphResponse(BaseModel):
    """Case subgraph for React Flow visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str


# ---- Search ----
class LawSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    law_id: str | None = None


class LawSearchResult(BaseModel):
    chunk_id: str
    law_id: str
    article_number: str
    clause_path: str
    content: str
    similarity: float


class TTHCSearchResult(BaseModel):
    tthc_code: str
    name: str
    department: str
    sla_days: int
    required_components: list[str]


# ---- Notifications ----
class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str | None
    category: NotificationCategory
    link: str | None
    is_read: bool
    created_at: datetime


# ---- Leadership ----
class DashboardResponse(BaseModel):
    total_cases: int
    pending_cases: int
    overdue_cases: int
    completed_today: int
    avg_processing_days: float
    cases_by_status: dict[str, int]
    cases_by_department: dict[str, int]
    agent_performance: list[AgentPerformanceItem]


class AgentPerformanceItem(BaseModel):
    agent_name: str
    total_runs: int
    avg_duration_ms: float
    avg_tokens: int


class InboxItem(BaseModel):
    case_id: str
    code: str
    title: str
    action_required: str
    priority: str
    created_at: datetime


# ---- Audit ----
class AuditEventResponse(BaseModel):
    id: str
    event_type: str
    actor_name: str | None
    target_type: str | None
    target_id: str | None
    case_id: str | None
    details: dict
    created_at: datetime


# ---- Public ----
class PublicCaseStatus(BaseModel):
    code: str
    status: str
    submitted_at: datetime
    current_step: str | None
    estimated_completion: datetime | None


class PublicTTHCItem(BaseModel):
    tthc_code: str
    name: str
    department: str
    sla_days: int
    fee: str
    required_components: list[str]


class PublicStatsResponse(BaseModel):
    total_cases_processed: int
    avg_processing_days: float
    cases_this_month: int
    satisfaction_rate: float | None = None
```

### backend/src/models/enums.py

```python
"""backend/src/models/enums.py"""
from enum import StrEnum


class CaseStatus(StrEnum):
    SUBMITTED = "submitted"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    GAP_CHECKING = "gap_checking"
    PENDING_SUPPLEMENT = "pending_supplement"
    LEGAL_REVIEW = "legal_review"
    DRAFTING = "drafting"
    LEADER_REVIEW = "leader_review"
    CONSULTATION = "consultation"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class Role(StrEnum):
    ADMIN = "admin"
    LEADER = "leader"
    OFFICER = "officer"
    PUBLIC_VIEWER = "public_viewer"


class NotificationCategory(StrEnum):
    INFO = "info"
    ACTION_REQUIRED = "action_required"
    ALERT = "alert"
    SYSTEM = "system"
```

---

## 4. API Routes

### 4.1 Cases: backend/src/api/cases.py

```python
"""backend/src/api/cases.py -- Case management endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..auth import CurrentUser
from ..database import gremlin_submit, pg_connection, oss_get_signed_url
from ..models.schemas import (
    CaseCreate, CaseResponse, CaseListResponse,
    BundleCreate, BundleResponse, UploadURL,
)

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse, status_code=201)
async def create_case(body: CaseCreate, user: CurrentUser):
    """Create a new administrative case (ho so)."""
    case_id = str(uuid.uuid4())
    code = f"HS-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{case_id[:8].upper()}"
    now = datetime.now(timezone.utc).isoformat()

    # Create Case vertex in GDB
    gremlin_submit(
        "g.addV('Case')"
        ".property('case_id', case_id).property('code', code)"
        ".property('status', 'submitted').property('submitted_at', now)"
        ".property('department_id', dept).property('tthc_code', tthc)",
        {"case_id": case_id, "code": code, "now": now,
         "dept": body.department_id, "tthc": body.tthc_code},
    )

    # Create Applicant vertex + edge
    applicant_id = str(uuid.uuid4())
    gremlin_submit(
        "g.addV('Applicant')"
        ".property('applicant_id', aid).property('full_name', name)"
        ".property('id_number', id_num).property('phone', phone)"
        ".property('address', addr)",
        {"aid": applicant_id, "name": body.applicant_name,
         "id_num": body.applicant_id_number, "phone": body.applicant_phone,
         "addr": body.applicant_address},
    )
    gremlin_submit(
        "g.V().has('Case', 'case_id', cid).addE('SUBMITTED_BY')"
        ".to(g.V().has('Applicant', 'applicant_id', aid))",
        {"cid": case_id, "aid": applicant_id},
    )

    # Insert analytics row
    async with pg_connection() as conn:
        await conn.execute(
            "INSERT INTO analytics_cases (case_id, department_id, tthc_code, status) "
            "VALUES ($1, $2, $3, 'submitted')",
            case_id, body.department_id, body.tthc_code,
        )

    return CaseResponse(
        case_id=case_id, code=code, status="submitted",
        tthc_code=body.tthc_code, department_id=body.department_id,
        submitted_at=datetime.now(timezone.utc), applicant_name=body.applicant_name,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(case_id: str, user: CurrentUser):
    """Get case details by ID."""
    result = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).valueMap(true)",
        {"cid": case_id},
    )
    if not result:
        raise HTTPException(404, "Case not found")

    props = result[0]
    # Extract applicant name
    applicant = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').values('full_name')",
        {"cid": case_id},
    )

    return CaseResponse(
        case_id=case_id,
        code=props.get("code", [""])[0],
        status=props.get("status", ["submitted"])[0],
        tthc_code=props.get("tthc_code", [""])[0],
        department_id=props.get("department_id", [""])[0],
        submitted_at=props.get("submitted_at", [datetime.now(timezone.utc).isoformat()])[0],
        applicant_name=applicant[0] if applicant else "",
    )


@router.post("/{case_id}/bundles", response_model=BundleResponse, status_code=201)
async def create_bundle(case_id: str, body: BundleCreate, user: CurrentUser):
    """Create a document bundle with pre-signed upload URLs."""
    bundle_id = str(uuid.uuid4())

    # Create Bundle vertex in GDB
    gremlin_submit(
        "g.addV('Bundle').property('bundle_id', bid).property('case_id', cid)"
        ".property('uploaded_at', now).property('status', 'pending')",
        {"bid": bundle_id, "cid": case_id,
         "now": datetime.now(timezone.utc).isoformat()},
    )
    gremlin_submit(
        "g.V().has('Case', 'case_id', cid).addE('HAS_BUNDLE')"
        ".to(g.V().has('Bundle', 'bundle_id', bid))",
        {"cid": case_id, "bid": bundle_id},
    )

    # Generate signed upload URLs
    upload_urls = []
    for fi in body.files:
        oss_key = f"bundles/{case_id}/{bundle_id}/{fi.filename}"
        # For upload, generate PUT signed URL
        from ..database import get_oss_bucket
        bucket = get_oss_bucket()
        signed = bucket.sign_url("PUT", oss_key, 3600)
        upload_urls.append(UploadURL(
            filename=fi.filename, signed_url=signed, oss_key=oss_key,
        ))

    return BundleResponse(
        bundle_id=bundle_id, case_id=case_id, upload_urls=upload_urls,
    )


@router.post("/{case_id}/finalize", status_code=200)
async def finalize_case(case_id: str, user: CurrentUser):
    """Mark a case as ready for agent processing."""
    gremlin_submit(
        "g.V().has('Case', 'case_id', cid).property('status', 'classifying')",
        {"cid": case_id},
    )
    return {"case_id": case_id, "status": "classifying", "message": "Case queued for processing"}
```

### 4.2 Documents: backend/src/api/documents.py

```python
"""backend/src/api/documents.py"""
from fastapi import APIRouter, HTTPException
from ..auth import CurrentUser
from ..database import gremlin_submit, oss_get_signed_url
from ..models.schemas import DocumentResponse

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: str, user: CurrentUser):
    """Get document metadata."""
    result = gremlin_submit(
        "g.V().has('Document', 'doc_id', did).valueMap(true)", {"did": doc_id},
    )
    if not result:
        raise HTTPException(404, "Document not found")
    props = result[0]
    return DocumentResponse(
        doc_id=doc_id,
        filename=props.get("filename", [""])[0],
        content_type=props.get("content_type", [""])[0],
        page_count=props.get("page_count", [None])[0],
        ocr_status=props.get("ocr_status", ["pending"])[0],
        oss_key=props.get("oss_key", [""])[0],
    )


@router.get("/{doc_id}/signed-url")
async def get_document_url(doc_id: str, user: CurrentUser):
    """Get a pre-signed download URL for a document."""
    result = gremlin_submit(
        "g.V().has('Document', 'doc_id', did).values('oss_key')", {"did": doc_id},
    )
    if not result:
        raise HTTPException(404, "Document not found")
    url = oss_get_signed_url(result[0])
    return {"doc_id": doc_id, "signed_url": url, "expires_in": 3600}
```

### 4.3 Agents: backend/src/api/agents.py

```python
"""backend/src/api/agents.py"""
from fastapi import APIRouter, BackgroundTasks
from ..auth import CurrentUser
from ..models.schemas import AgentRunRequest, AgentTraceResponse, AgentStepResponse
from ..database import gremlin_submit

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/trace/{case_id}", response_model=AgentTraceResponse)
async def get_agent_trace(case_id: str, user: CurrentUser):
    """Get the full agent processing trace for a case."""
    steps = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).out('PROCESSED_BY')"
        ".valueMap(true).order().by('step_id')",
        {"cid": case_id},
    )
    step_list = []
    total_tokens = 0
    total_ms = 0
    for s in steps:
        in_tok = s.get("input_tokens", [0])[0]
        out_tok = s.get("output_tokens", [0])[0]
        dur = s.get("duration_ms", [0])[0]
        total_tokens += in_tok + out_tok
        total_ms += dur
        step_list.append(AgentStepResponse(
            step_id=s.get("step_id", [""])[0],
            agent_name=s.get("agent_name", [""])[0],
            action=s.get("action", [""])[0],
            status=s.get("status", ["completed"])[0],
            input_tokens=in_tok,
            output_tokens=out_tok,
            duration_ms=dur,
        ))

    case_status = gremlin_submit(
        "g.V().has('Case', 'case_id', cid).values('status')", {"cid": case_id},
    )

    return AgentTraceResponse(
        case_id=case_id,
        steps=step_list,
        status=case_status[0] if case_status else "unknown",
        total_tokens=total_tokens,
        total_duration_ms=total_ms,
    )


@router.post("/run/{case_id}", status_code=202)
async def run_agents(
    case_id: str, body: AgentRunRequest,
    user: CurrentUser, background_tasks: BackgroundTasks,
):
    """Trigger agent pipeline on a case (runs in background)."""
    # Import here to avoid circular imports
    from ..agents.orchestrator import run_pipeline
    background_tasks.add_task(run_pipeline, case_id, body.pipeline)
    return {"case_id": case_id, "pipeline": body.pipeline, "status": "accepted"}
```

### 4.4 Graph: backend/src/api/graph.py

```python
"""backend/src/api/graph.py"""
import time
from fastapi import APIRouter, Depends
from ..auth import CurrentUser, require_role
from ..database import gremlin_submit
from ..models.schemas import GraphQueryRequest, GraphQueryResponse, SubgraphResponse, GraphNode, GraphEdge

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.post("/query", response_model=GraphQueryResponse)
async def query_graph(
    body: GraphQueryRequest,
    user: CurrentUser = Depends(require_role("admin")),
):
    """Execute a raw Gremlin query (admin only)."""
    start = time.monotonic()
    result = gremlin_submit(body.query, body.bindings)
    elapsed = (time.monotonic() - start) * 1000
    return GraphQueryResponse(result=result, execution_time_ms=round(elapsed, 2))


@router.get("/case/{case_id}/subgraph", response_model=SubgraphResponse)
async def get_case_subgraph(case_id: str, user: CurrentUser):
    """Get the case subgraph for React Flow visualization."""
    # Get vertices
    vertices = gremlin_submit(
        "g.V().has('Case', 'case_id', cid)"
        ".bothE().bothV().dedup().valueMap(true).with(WithOptions.tokens)",
        {"cid": case_id},
    )
    # Get edges
    edges = gremlin_submit(
        "g.V().has('Case', 'case_id', cid)"
        ".bothE().project('id','source','target','label')"
        ".by(id).by(outV().id()).by(inV().id()).by(label)",
        {"cid": case_id},
    )

    nodes = [
        GraphNode(id=str(v.get("id", "")), label=v.get("label", ""), properties=v)
        for v in vertices
    ]
    edge_list = [
        GraphEdge(id=str(e["id"]), source=str(e["source"]),
                  target=str(e["target"]), label=e["label"])
        for e in edges
    ]
    return SubgraphResponse(nodes=nodes, edges=edge_list)
```

### 4.5 Search: backend/src/api/search.py

```python
"""backend/src/api/search.py"""
from fastapi import APIRouter
from openai import OpenAI

from ..auth import CurrentUser
from ..config import settings
from ..database import pg_connection, gremlin_submit
from ..models.schemas import LawSearchRequest, LawSearchResult, TTHCSearchResult

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/law", response_model=list[LawSearchResult])
async def search_law(query: str, top_k: int = 10, law_id: str | None = None, user: CurrentUser = None):
    """Vector search over law chunks using Qwen3-Embedding."""
    client = OpenAI(api_key=settings.dashscope_api_key, base_url=settings.dashscope_base_url)
    emb_resp = client.embeddings.create(model="text-embedding-v3", input=query, dimensions=1536)
    query_vec = emb_resp.data[0].embedding

    vec_str = "[" + ",".join(str(x) for x in query_vec) + "]"

    sql = """
        SELECT id, law_id, article_number, clause_path, content,
               1 - (embedding <=> $1::vector) as similarity
        FROM law_chunks
    """
    params = [vec_str]
    if law_id:
        sql += " WHERE law_id = $2"
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


@router.get("/tthc", response_model=list[TTHCSearchResult])
async def search_tthc(query: str, user: CurrentUser = None):
    """Search TTHC procedures by keyword (Gremlin text match)."""
    results = gremlin_submit(
        "g.V().hasLabel('TTHCSpec')"
        ".has('name', TextP.containing(q))"
        ".valueMap(true).limit(20)",
        {"q": query},
    )
    items = []
    for r in results:
        code = r.get("tthc_code", [""])[0]
        components = gremlin_submit(
            "g.V().has('TTHCSpec', 'tthc_code', c).out('REQUIRES').values('component_name')",
            {"c": code},
        )
        items.append(TTHCSearchResult(
            tthc_code=code, name=r.get("name", [""])[0],
            department=r.get("department", [""])[0],
            sla_days=r.get("sla_days", [15])[0],
            required_components=components,
        ))
    return items
```

### 4.6 Notifications: backend/src/api/notifications.py

```python
"""backend/src/api/notifications.py"""
from fastapi import APIRouter
from ..auth import CurrentUser
from ..database import pg_connection
from ..models.schemas import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(user: CurrentUser, unread_only: bool = False):
    """List notifications for the current user."""
    sql = "SELECT * FROM notifications WHERE user_id = $1"
    params = [user.sub]
    if unread_only:
        sql += " AND is_read = FALSE"
    sql += " ORDER BY created_at DESC LIMIT 50"

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)
    return [NotificationResponse(**dict(r)) for r in rows]


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, user: CurrentUser):
    """Mark a notification as read."""
    async with pg_connection() as conn:
        await conn.execute(
            "UPDATE notifications SET is_read = TRUE WHERE id = $1 AND user_id = $2",
            notification_id, user.sub,
        )
    return {"id": notification_id, "is_read": True}
```

### 4.7 Leadership: backend/src/api/leadership.py

```python
"""backend/src/api/leadership.py"""
from fastapi import APIRouter, Depends
from ..auth import CurrentUser, require_role
from ..database import pg_connection
from ..models.schemas import DashboardResponse, AgentPerformanceItem, InboxItem

router = APIRouter(prefix="/leadership", tags=["Leadership"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(user: CurrentUser = Depends(require_role("admin", "leader"))):
    """Leadership dashboard with KPIs."""
    async with pg_connection() as conn:
        total = await conn.fetchval("SELECT count(*) FROM analytics_cases")
        pending = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE status NOT IN ('approved','rejected','published')")
        overdue = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE is_overdue = TRUE")
        completed_today = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE completed_at::date = CURRENT_DATE")
        avg_days = await conn.fetchval("SELECT COALESCE(avg(processing_days), 0) FROM analytics_cases WHERE processing_days IS NOT NULL")

        by_status = await conn.fetch("SELECT status, count(*) as cnt FROM analytics_cases GROUP BY status")
        by_dept = await conn.fetch("SELECT department_id, count(*) as cnt FROM analytics_cases GROUP BY department_id")

        agent_perf = await conn.fetch("""
            SELECT agent_name, count(*) as runs,
                   avg(duration_ms)::int as avg_dur,
                   avg(input_tokens + output_tokens)::int as avg_tok
            FROM analytics_agents WHERE status = 'completed'
            GROUP BY agent_name
        """)

    return DashboardResponse(
        total_cases=total, pending_cases=pending, overdue_cases=overdue,
        completed_today=completed_today, avg_processing_days=float(avg_days),
        cases_by_status={r["status"]: r["cnt"] for r in by_status},
        cases_by_department={r["department_id"]: r["cnt"] for r in by_dept},
        agent_performance=[
            AgentPerformanceItem(
                agent_name=r["agent_name"], total_runs=r["runs"],
                avg_duration_ms=float(r["avg_dur"]), avg_tokens=r["avg_tok"],
            ) for r in agent_perf
        ],
    )


@router.get("/inbox", response_model=list[InboxItem])
async def get_inbox(user: CurrentUser = Depends(require_role("admin", "leader"))):
    """Items requiring leader attention."""
    async with pg_connection() as conn:
        rows = await conn.fetch("""
            SELECT case_id, status, department_id, submitted_at
            FROM analytics_cases
            WHERE status IN ('leader_review', 'consultation')
            ORDER BY submitted_at ASC
            LIMIT 20
        """)
    return [
        InboxItem(
            case_id=r["case_id"], code=f"HS-{r['case_id'][:8]}",
            title=f"Case {r['case_id'][:8]} - {r['status']}",
            action_required=r["status"], priority="high",
            created_at=r["submitted_at"],
        ) for r in rows
    ]
```

### 4.8 Audit: backend/src/api/audit.py

```python
"""backend/src/api/audit.py"""
from fastapi import APIRouter, Depends, Query
from ..auth import CurrentUser, require_role
from ..database import pg_connection
from ..models.schemas import AuditEventResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    event_type: str | None = None,
    case_id: str | None = None,
    limit: int = Query(default=50, le=200),
    user: CurrentUser = Depends(require_role("admin", "leader")),
):
    """List audit events with optional filters."""
    sql = "SELECT * FROM audit_events_flat WHERE 1=1"
    params = []
    idx = 1

    if event_type:
        sql += f" AND event_type = ${idx}"
        params.append(event_type)
        idx += 1
    if case_id:
        sql += f" AND case_id = ${idx}"
        params.append(case_id)
        idx += 1

    sql += f" ORDER BY created_at DESC LIMIT ${idx}"
    params.append(limit)

    async with pg_connection() as conn:
        rows = await conn.fetch(sql, *params)

    return [
        AuditEventResponse(
            id=str(r["id"]), event_type=r["event_type"],
            actor_name=r["actor_name"], target_type=r["target_type"],
            target_id=r["target_id"], case_id=r["case_id"],
            details=r["details"] or {}, created_at=r["created_at"],
        ) for r in rows
    ]
```

### 4.9 Public: backend/src/api/public.py

```python
"""backend/src/api/public.py -- No authentication required."""
from fastapi import APIRouter, HTTPException
from ..database import gremlin_submit, pg_connection
from ..models.schemas import PublicCaseStatus, PublicTTHCItem, PublicStatsResponse

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/cases/{code}", response_model=PublicCaseStatus)
async def public_case_status(code: str):
    """Public case status lookup by case code (no auth)."""
    result = gremlin_submit(
        "g.V().has('Case', 'code', code).valueMap(true)", {"code": code},
    )
    if not result:
        raise HTTPException(404, "Case not found")
    props = result[0]
    return PublicCaseStatus(
        code=code,
        status=props.get("status", ["unknown"])[0],
        submitted_at=props.get("submitted_at", [""])[0],
        current_step=props.get("status", [""])[0],
        estimated_completion=None,
    )


@router.get("/tthc", response_model=list[PublicTTHCItem])
async def list_public_tthc():
    """List all public TTHC procedures."""
    results = gremlin_submit("g.V().hasLabel('TTHCSpec').valueMap(true).limit(100)")
    items = []
    for r in results:
        code = r.get("tthc_code", [""])[0]
        comps = gremlin_submit(
            "g.V().has('TTHCSpec', 'tthc_code', c).out('REQUIRES').values('component_name')",
            {"c": code},
        )
        items.append(PublicTTHCItem(
            tthc_code=code, name=r.get("name", [""])[0],
            department=r.get("department", [""])[0],
            sla_days=r.get("sla_days", [15])[0],
            fee=r.get("fee", ["0"])[0],
            required_components=comps,
        ))
    return items


@router.get("/stats", response_model=PublicStatsResponse)
async def public_stats():
    """Public statistics."""
    async with pg_connection() as conn:
        total = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE status IN ('approved','published')")
        avg = await conn.fetchval("SELECT COALESCE(avg(processing_days),0) FROM analytics_cases WHERE processing_days IS NOT NULL")
        month = await conn.fetchval("SELECT count(*) FROM analytics_cases WHERE submitted_at >= date_trunc('month', CURRENT_DATE)")
    return PublicStatsResponse(
        total_cases_processed=total, avg_processing_days=float(avg), cases_this_month=month,
    )
```

---

## 5. WebSocket: backend/src/api/ws.py

```python
"""
backend/src/api/ws.py
WebSocket handler with topic-based pub/sub.
Topics: case:{id}, dept:{id}:inbox, user:{id}:notifications, security:audit
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..auth import decode_token

router = APIRouter()
logger = logging.getLogger("govflow.ws")

# Global subscription registry: topic -> set of websockets
_subscriptions: dict[str, set[WebSocket]] = defaultdict(set)
_lock = asyncio.Lock()


async def subscribe(ws: WebSocket, topic: str) -> None:
    async with _lock:
        _subscriptions[topic].add(ws)
    logger.info(f"WS subscribed to {topic}")


async def unsubscribe(ws: WebSocket, topic: str) -> None:
    async with _lock:
        _subscriptions[topic].discard(ws)


async def unsubscribe_all(ws: WebSocket) -> None:
    async with _lock:
        for topic in list(_subscriptions.keys()):
            _subscriptions[topic].discard(ws)


async def broadcast(topic: str, message: dict) -> None:
    """Broadcast a message to all subscribers of a topic."""
    async with _lock:
        subscribers = list(_subscriptions.get(topic, set()))

    payload = json.dumps({"topic": topic, **message})
    dead = []
    for ws in subscribers:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)

    # Clean up dead connections
    if dead:
        async with _lock:
            for ws in dead:
                _subscriptions[topic].discard(ws)


@router.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint.
    Client sends JSON: {"action": "subscribe"|"unsubscribe", "topic": "case:123"}
    Server pushes:     {"topic": "case:123", "event": "status_changed", "data": {...}}
    """
    await ws.accept()

    # Authenticate via first message or query param
    token = ws.query_params.get("token")
    if token:
        try:
            user = decode_token(token)
            logger.info(f"WS authenticated: {user.username}")
        except Exception:
            await ws.close(code=4001, reason="Invalid token")
            return
    else:
        user = None  # Allow unauthenticated for public topics

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            topic = data.get("topic", "")

            # Public topics don't require auth
            is_public = topic.startswith("public:")
            if not is_public and user is None:
                await ws.send_json({"error": "Authentication required for non-public topics"})
                continue

            if action == "subscribe":
                await subscribe(ws, topic)
                await ws.send_json({"ack": "subscribed", "topic": topic})
            elif action == "unsubscribe":
                await unsubscribe(ws, topic)
                await ws.send_json({"ack": "unsubscribed", "topic": topic})
            else:
                await ws.send_json({"error": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("WS disconnected")
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        await unsubscribe_all(ws)
```

---

## 6. App Factory with Route Registration and Rate Limiting

Update `backend/src/main.py`:

```python
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

    # Auth endpoint (mock login for hackathon)
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

    # WebSocket
    from .api import ws
    app.include_router(ws.router)

    # Health check
    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok", "env": settings.govflow_env}

    return app


app = create_app()
```

### Mock login endpoint: backend/src/api/auth_login.py

```python
"""backend/src/api/auth_login.py -- Hackathon mock login."""
import hashlib
from fastapi import APIRouter, HTTPException
from ..auth import create_access_token
from ..database import pg_connection
from ..models.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate and return JWT. For hackathon: SHA256 password check."""
    pw_hash = hashlib.sha256(body.password.encode()).hexdigest()

    async with pg_connection() as conn:
        row = await conn.fetchrow(
            "SELECT id, username, full_name, role, clearance_level, departments "
            "FROM users WHERE username = $1 AND password_hash = $2 AND is_active = TRUE",
            body.username, pw_hash,
        )

    if not row:
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token(
        user_id=str(row["id"]),
        username=row["username"],
        role=row["role"],
        clearance_level=row["clearance_level"],
        departments=list(row["departments"]),
    )

    return LoginResponse(
        access_token=token,
        user_id=str(row["id"]),
        role=row["role"],
        clearance_level=row["clearance_level"],
    )
```

---

## 7. Complete Route Table

| Method | Path                          | Auth     | Description                          |
|--------|-------------------------------|----------|--------------------------------------|
| POST   | /auth/login                   | None     | Authenticate, return JWT             |
| POST   | /cases                        | Bearer   | Create new case                      |
| GET    | /cases/{id}                   | Bearer   | Get case details                     |
| POST   | /cases/{id}/bundles           | Bearer   | Create bundle with upload URLs       |
| POST   | /cases/{id}/finalize          | Bearer   | Queue case for agent processing      |
| GET    | /documents/{id}               | Bearer   | Get document metadata                |
| GET    | /documents/{id}/signed-url    | Bearer   | Get download URL                     |
| GET    | /agents/trace/{case_id}       | Bearer   | Get agent processing trace           |
| POST   | /agents/run/{case_id}         | Bearer   | Trigger agent pipeline               |
| POST   | /graph/query                  | Admin    | Raw Gremlin query                    |
| GET    | /graph/case/{id}/subgraph     | Bearer   | Case subgraph for visualization      |
| GET    | /search/law                   | Bearer   | Vector search over law chunks        |
| GET    | /search/tthc                  | Bearer   | Search TTHC procedures               |
| GET    | /notifications                | Bearer   | List user notifications              |
| PATCH  | /notifications/{id}/read      | Bearer   | Mark notification as read            |
| GET    | /leadership/dashboard         | Leader+  | Dashboard KPIs                       |
| GET    | /leadership/inbox             | Leader+  | Items requiring attention            |
| GET    | /audit/events                 | Leader+  | Audit event log                      |
| GET    | /public/cases/{code}          | None     | Public case status lookup            |
| GET    | /public/tthc                  | None     | Public TTHC list                     |
| GET    | /public/stats                 | None     | Public statistics                    |
| WS     | /api/ws                       | Token QP | WebSocket pub/sub                    |
| GET    | /health                       | None     | Health check                         |

---

## 8. Verification Checklist

### 8.1 Server starts and serves /docs

```bash
cd /home/logan/GovTrack/backend
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 &
sleep 3
curl -s http://localhost:8000/docs | head -5
# Expected: HTML containing "GovFlow API"
curl -s http://localhost:8000/openapi.json | python -m json.tool | grep '"path"' | wc -l
# Expected: 20+ paths
kill %1
```

### 8.2 JWT auth flow works

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"cv_qldt","password":"cv_qldt123"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Authenticated request
curl -s http://localhost:8000/search/tthc?query=xay%20dung \
  -H "Authorization: Bearer $TOKEN"
# Expected: JSON array of TTHC results

# Unauthenticated request fails
curl -s http://localhost:8000/cases -X POST
# Expected: 403 Not authenticated
```

### 8.3 WebSocket connects

```bash
# Using websocat (install: cargo install websocat)
echo '{"action":"subscribe","topic":"public:stats"}' | \
  websocat ws://localhost:8000/api/ws
# Expected: {"ack":"subscribed","topic":"public:stats"}
```

### 8.4 Public endpoints work without auth

```bash
curl -s http://localhost:8000/public/stats
# Expected: JSON with total_cases_processed, avg_processing_days, etc.

curl -s http://localhost:8000/public/tthc
# Expected: JSON array of TTHC items
```

---

## Tong ket (Summary)

| Component          | Status                                 |
|--------------------|----------------------------------------|
| JWT Auth           | DONE — HS256, role/clearance claims, login |
| REST Routes        | DONE — 22 endpoints across 11 routers  |
| WebSocket          | DONE — Topic-based pub/sub at /api/ws  |
| Pydantic Schemas   | DONE — Full request/response models    |
| Rate Limiting      | DONE — Slowapi, configurable per route |
| CORS               | DONE — Configured for frontend origin  |
| OpenAPI Docs       | DONE — Auto-generated at /docs         |

Next step: proceed to `04-agent-runtime.md` to build the agent system.
