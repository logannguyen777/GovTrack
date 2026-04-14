"""
backend/src/models/schemas.py
Pydantic v2 request/response models for all API routes.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .enums import CaseStatus, ClearanceLevel, NotificationCategory, Role


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
class BundleFileInfo(BaseModel):
    filename: str
    content_type: str
    size_bytes: int


class BundleCreate(BaseModel):
    """Metadata for a new document bundle upload."""
    files: list[BundleFileInfo]


class UploadURL(BaseModel):
    filename: str
    signed_url: str
    oss_key: str


class BundleResponse(BaseModel):
    bundle_id: str
    case_id: str
    upload_urls: list[UploadURL]
    status: str = "pending"


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


class AgentTraceResponse(BaseModel):
    case_id: str
    steps: list[AgentStepResponse]
    status: str  # running | completed | failed
    total_tokens: int
    total_duration_ms: int


# ---- Consult ----
class ConsultOpinionSubmit(BaseModel):
    """Submit a department opinion for a consult request."""
    content: str = Field(..., min_length=1, max_length=5000)
    verdict: str = Field(default="neutral", description="dong_y | khong_dong_y | dong_y_co_dieu_kien | neutral")
    source_org_id: str
    source_org_name: str


class ConsultRequestResponse(BaseModel):
    request_id: str
    case_id: str
    target_org_id: str
    target_org_name: str
    context_summary: str
    main_question: str
    sub_questions: str = "[]"
    deadline: str
    urgency: str = "normal"
    status: str = "pending"
    created_at: str | None = None


# ---- Graph ----
class GraphQueryRequest(BaseModel):
    """Admin-only raw Gremlin query."""
    query: str
    bindings: dict = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    result: list
    execution_time_ms: float


class GraphNode(BaseModel):
    id: str
    label: str
    properties: dict


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str


class SubgraphResponse(BaseModel):
    """Case subgraph for React Flow visualization."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]


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
class AgentPerformanceItem(BaseModel):
    agent_name: str
    total_runs: int
    avg_duration_ms: float
    avg_tokens: int


class DashboardResponse(BaseModel):
    total_cases: int
    pending_cases: int
    overdue_cases: int
    completed_today: int
    avg_processing_days: float
    cases_by_status: dict[str, int]
    cases_by_department: dict[str, int]
    agent_performance: list[AgentPerformanceItem]


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


# ---- Permission Engine ----
class AgentProfile(BaseModel):
    """Permission profile for an agent, used by the 3-tier permission engine."""
    agent_id: str
    agent_name: str
    clearance: ClearanceLevel
    read_node_labels: list[str]
    write_node_labels: list[str]
    read_edge_types: list[str]
    write_edge_types: list[str]
    forbidden_properties: list[str] = []
    max_traversal_depth: int = 5
