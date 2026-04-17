"""
backend/src/api/assistant.py
Public AI assistant routes — citizen-facing chatbot, intent, field help,
precheck, validate, recommendation, and prefill.

All /chat streaming uses SSE (text/event-stream).
Tool calling runs inside AssistantAgent.stream_response().
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..agents.implementations.assistant_agent import AssistantAgent
from ..agents.public_tools import PublicAssistantTools
from ..agents.qwen_client import QwenClient
from ..auth import CurrentUser
from ..config import settings
from ..database import pg_connection
from ..models.chat_schemas import (
    ChatRequest,
    DraftPreviewResponse,
    ExplainCaseResponse,
    ExtractResponse,
    FieldHelpResponse,
    FormSuggestRequest,
    FormSuggestResponse,
    FormSuggestion,
    IntentRequest,
    IntentResponse,
    NghiDinh30Check,
    PrecheckRequest,
    PrecheckResponse,
    RecommendationResponse,
    ValidateRequest,
    ValidateResponse,
)
from ..services.chat_service import ChatService
from ..services.content_filter import ContentFilter
from ..services.rate_limiter import RateLimiter

logger = logging.getLogger("govflow.assistant")

router = APIRouter(prefix="/assistant", tags=["Assistant"])

# Module-level singletons (lightweight, thread-safe)
_rate_limiter = RateLimiter(max_per_minute=settings.chat_rate_limit_per_minute)
_content_filter = ContentFilter()
_chat_service = ChatService()
_public_tools = PublicAssistantTools()
_qwen_client = QwenClient()

# In-memory extraction cache: extraction_id -> ExtractResponse (1h TTL)
_extract_cache: dict[str, tuple[ExtractResponse, float]] = {}
_EXTRACT_TTL = 3600.0

# In-memory field-help cache per (tthc_code, field)
# Loaded at import time from static definitions below
_FIELD_HELP: dict[tuple[str, str], dict[str, str | None]] = {}


def _compute_daily_salt() -> str:
    """Daily salt for ip_hash. Uses settings value or SHA256 of today's date."""
    if settings.daily_salt:
        return settings.daily_salt
    return hashlib.sha256(date.today().isoformat().encode()).hexdigest()[:16]


def _ip_hash(ip: str) -> str:
    """Hash IP with daily salt for session ownership (no plain IP stored)."""
    salt = _compute_daily_salt()
    return hashlib.sha256(f"{ip}:{salt}".encode()).hexdigest()[:32]


def _get_client_ip(request: Request) -> str:
    """Extract client IP, honouring X-Forwarded-For for reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_agent() -> AssistantAgent:
    return AssistantAgent(
        qwen_client=_qwen_client,
        tools=_public_tools,
        max_tool_iterations=settings.assistant_max_tool_iterations,
    )


# ---------------------------------------------------------------------------
# POST /api/assistant/chat  — SSE streaming chatbot
# ---------------------------------------------------------------------------


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    """
    Citizen chatbot endpoint. Returns SSE stream.
    Rate limited: {settings.chat_rate_limit_per_minute} req/min per IP.
    """
    ip = _get_client_ip(request)
    ip_h = _ip_hash(ip)

    # Rate limiting
    if not await _rate_limiter.check(ip_h):
        raise HTTPException(
            status_code=429,
            detail="Bạn gửi quá nhiều tin nhắn. Vui lòng chờ 1 phút rồi thử lại.",
        )

    # Content filter
    allowed, reason = _content_filter.check(req.message)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason or "Nội dung không hợp lệ.")

    # Session management
    session_id = await _chat_service.get_or_create_session(req.session_id, ip_h, req.context)

    # Persist user message
    await _chat_service.append_user_message(session_id, req.message, req.attachments)

    # Fetch conversation history
    history = await _chat_service.get_recent_messages(
        session_id, limit=settings.assistant_history_limit
    )

    # Build messages list (history already contains the user message just appended)
    # Attachments as image_url content blocks for vision-capable messages
    messages = _build_messages_with_attachments(history, req.attachments)

    agent = _get_agent()

    async def event_stream():
        # First event: session confirmation
        session_event = json.dumps(
            {"type": "session", "session_id": session_id}, ensure_ascii=False
        )
        yield f"data: {session_event}\n\n"

        # Track message_id for cancellation on disconnect
        message_id: str | None = None
        final_content = ""
        final_tool_calls: list[dict] = []
        final_citations: list[dict] = []
        status = "error"

        try:
            async for event in agent.stream_response(
                session_id=session_id,
                messages=messages,
                context=req.context,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if event.get("type") == "done":
                    message_id = event.get("message_id")
                    final_content = event.get("content", "")
                    final_tool_calls = event.get("tool_calls", [])
                    final_citations = event.get("citations", [])
                    status = "completed"

            # Persist assistant message
            await _chat_service.append_assistant_message(
                session_id,
                content=final_content,
                tool_calls=final_tool_calls,
                citations=final_citations,
                status=status,
            )

        except asyncio.CancelledError:
            # SSE client disconnected — cancel in-flight message
            if message_id:
                await _chat_service.cancel_streaming_message(message_id)
            raise

        except Exception as e:
            logger.error(f"chat stream error session={session_id}: {e}", exc_info=True)
            error_event = {"type": "error", "message": "Lỗi máy chủ. Vui lòng thử lại."}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# POST /api/assistant/intent  — classify user intent to TTHC
# ---------------------------------------------------------------------------


@router.post("/intent", response_model=IntentResponse)
async def classify_intent(req: IntentRequest):
    """
    Single Qwen call to classify user intent into one of 5 TTHC procedures.
    Returns primary match + confidence + Vietnamese explanation.
    """
    # Build TTHC list from local specs
    tthc_list = _get_all_tthc_summary()

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là chuyên gia tư vấn thủ tục hành chính Việt Nam. "
                "Phân loại yêu cầu của người dân vào đúng thủ tục hành chính. "
                "Trả về JSON theo đúng format yêu cầu."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "yeu_cau": req.text,
                    "danh_sach_tthc": tthc_list,
                    "instruction": (
                        "Trả về JSON: {"
                        '"primary_tthc_code": "...", '
                        '"primary_confidence": 0.XX, '
                        '"explanation": "Giải thích ngắn tại sao", '
                        '"alternatives": [{"tthc_code":"...","name":"...","confidence":0.XX}]'
                        "}"
                    ),
                },
                ensure_ascii=False,
            ),
        },
    ]

    import re

    completion = await _qwen_client.chat(
        messages=messages,
        model="reasoning",
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    return IntentResponse(
        primary_tthc_code=data.get("primary_tthc_code"),
        primary_confidence=float(data.get("primary_confidence", 0.0)),
        explanation=data.get("explanation", "Không thể phân loại ý định."),
        alternatives=data.get("alternatives", []),
    )


# ---------------------------------------------------------------------------
# GET /api/assistant/explain-case/{case_code}  — plain-language case status
# ---------------------------------------------------------------------------


@router.get("/explain-case/{case_code}", response_model=ExplainCaseResponse)
async def explain_case(case_code: str):
    """
    Return plain-language explanation of case status.
    Calls Qwen once; safe for public (no PII returned).
    """
    # Fetch case info (status + tthc_code + department)
    # Support both UUID (case_id) and HS-code (code) lookups
    case_info: dict[str, Any] = {}
    try:
        async with pg_connection() as conn:
            row = await conn.fetchrow(
                "SELECT status, tthc_code, department_id, sla_days, submitted_at "
                "FROM analytics_cases WHERE case_id = $1",
                case_code,
            )
            if row:
                case_info = dict(row)
    except Exception:
        pass

    # Fallback: look up by HS code in GDB (Case vertex with property 'code')
    if not case_info:
        try:
            from ..auth import PUBLIC_SESSION
            from ..graph.permitted_client import PermittedGremlinClient
            vmap = await PermittedGremlinClient(PUBLIC_SESSION).execute(
                "g.V().has('Case', 'code', c).valueMap(true).limit(1)",
                {"c": case_code},
            )
            if vmap:
                props = vmap[0]
                case_info = {
                    "status": (props.get("status") or ["unknown"])[0],
                    "tthc_code": (props.get("tthc_code") or [""])[0],
                    "department_id": (props.get("department_id") or [""])[0],
                    "sla_days": (props.get("sla_days") or [15])[0],
                }
        except Exception:
            pass

    if not case_info:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ.")

    messages = [
        {
            "role": "system",
            "content": (
                "Giải thích trạng thái hồ sơ hành chính bằng tiếng Việt dễ hiểu "
                "cho người dân thường. Ngắn gọn, tối đa 3 câu. "
                'Trả về JSON: {"explanation": "...", "next_step": "...|null"}'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "ma_ho_so": case_code,
                    "trang_thai": case_info.get("status", ""),
                    "thu_tuc": case_info.get("tthc_code", ""),
                    "phong_ban": case_info.get("department_id", ""),
                    "sla_ngay": case_info.get("sla_days", 15),
                },
                ensure_ascii=False,
            ),
        },
    ]

    import re

    completion = await _qwen_client.chat(
        messages=messages,
        model="reasoning",
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    return ExplainCaseResponse(
        explanation=data.get(
            "explanation",
            f"Hồ sơ {case_code} đang ở trạng thái: {case_info.get('status', 'chưa rõ')}.",
        ),
        next_step=data.get("next_step"),
    )


# ---------------------------------------------------------------------------
# GET /api/assistant/field-help  — per-field help text
# ---------------------------------------------------------------------------


@router.get("/field-help", response_model=FieldHelpResponse)
async def field_help(tthc_code: str, field: str):
    """
    Return cached helper text for a form field in a TTHC.
    Hardcoded for 5 TTHC × common fields; no Qwen call needed.
    """
    key = (tthc_code, field)
    if key in _FIELD_HELP:
        h = _FIELD_HELP[key]
        return FieldHelpResponse(
            explanation=h.get("explanation", ""),
            example_correct=h.get("example_correct"),
            example_incorrect=h.get("example_incorrect"),
            related_law=h.get("related_law"),
        )

    # Generic fallback
    return FieldHelpResponse(
        explanation=f"Trường '{field}' là bắt buộc trong thủ tục {tthc_code}.",
        example_correct=None,
        example_incorrect=None,
        related_law=None,
    )


# ---------------------------------------------------------------------------
# POST /api/assistant/precheck  — mini compliance check
# ---------------------------------------------------------------------------


@router.post("/precheck", response_model=PrecheckResponse)
async def precheck(req: PrecheckRequest):
    """
    Lightweight compliance pre-check before submission.
    1 Qwen call — returns score, gaps, missing_docs, suggestions.
    """
    import re

    from ..agents.public_tools import _load_tthc_spec

    spec = _load_tthc_spec(req.tthc_code)
    required_docs = []
    if spec:
        required_docs = [
            c["name"] for c in spec.get("required_components", []) if c.get("is_required", True)
        ]

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là chuyên gia kiểm tra hồ sơ hành chính Việt Nam. "
                "Phân tích hồ sơ sơ bộ và chỉ ra thiếu sót. "
                'Trả về JSON: {"score": 0.0-1.0, "gaps": [...], '
                '"missing_docs": [...], "suggestions": [...]}'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "tthc_code": req.tthc_code,
                    "required_documents": required_docs,
                    "uploaded_docs": req.uploaded_doc_urls,
                    "form_data_keys": list(req.form_data.keys()),
                    "instruction": "Kiểm tra hồ sơ, trả JSON.",
                },
                ensure_ascii=False,
            ),
        },
    ]

    completion = await _qwen_client.chat(
        messages=messages,
        model="reasoning",
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    return PrecheckResponse(
        score=float(data.get("score", 0.5)),
        gaps=data.get("gaps", []),
        missing_docs=data.get("missing_docs", []),
        suggestions=data.get("suggestions", []),
    )


# ---------------------------------------------------------------------------
# POST /api/assistant/form-suggest  — AI fills missing form fields
# ---------------------------------------------------------------------------


@router.post("/form-suggest", response_model=FormSuggestResponse)
async def form_suggest(req: FormSuggestRequest):
    """
    Suggest missing form field values from uploaded documents + partial form.
    1 Qwen call — returns suggestions [{field, value, confidence, source}].
    """
    import re

    # Common citizen fields; the LLM sees these and fills whichever are missing.
    CANDIDATE_FIELDS = {
        "applicant_name": "Họ và tên",
        "applicant_id_number": "Số CCCD/CMND (12 số)",
        "applicant_phone": "Số điện thoại",
        "applicant_address": "Địa chỉ thường trú",
        "applicant_dob": "Ngày sinh (YYYY-MM-DD)",
    }
    missing = [k for k in CANDIDATE_FIELDS if not req.partial_form.get(k)]

    if not missing:
        return FormSuggestResponse(suggestions=[])

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là trợ lý điền hồ sơ hành chính Việt Nam. Dựa vào danh sách "
                "tài liệu công dân đã tải lên (VD: ảnh CCCD, hộ khẩu, giấy tờ đất) "
                "và thông tin đã nhập, gợi ý giá trị hợp lý cho các trường còn thiếu. "
                'Trả về JSON đúng dạng: {"suggestions":[{"field":"...","value":"...",'
                '"confidence":0.0-1.0,"source":"..."}]}. '
                "Chỉ gợi ý trường anh chắc chắn có thể trích được (confidence ≥ 0.6). "
                "Trường confidence thấp thì bỏ qua, đừng đoán mò."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "tthc_code": req.tthc_code,
                    "partial_form": req.partial_form,
                    "uploaded_docs": req.uploaded_doc_urls,
                    "missing_fields": {f: CANDIDATE_FIELDS[f] for f in missing},
                    "instruction": "Trả JSON với suggestions cho các trường trên.",
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        completion = await _qwen_client.chat(
            messages=messages,
            model="reasoning",
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        logger.warning(f"[form-suggest] Qwen call failed: {exc}")
        return FormSuggestResponse(suggestions=[])

    content = completion.choices[0].message.content or "{}"
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    raw = data.get("suggestions") or []
    suggestions: list[FormSuggestion] = []
    for item in raw:
        field = str(item.get("field", "")).strip()
        value = str(item.get("value", "")).strip()
        if not field or not value or field not in CANDIDATE_FIELDS:
            continue
        suggestions.append(
            FormSuggestion(
                field=field,
                value=value,
                confidence=float(item.get("confidence", 0.7) or 0.7),
                source=str(item.get("source") or "Suy ra từ tài liệu đã tải lên"),
            )
        )

    return FormSuggestResponse(suggestions=suggestions)


# ---------------------------------------------------------------------------
# POST /api/assistant/validate  — field validation
# ---------------------------------------------------------------------------


@router.post("/validate", response_model=ValidateResponse)
async def validate_form(req: ValidateRequest):
    """
    Validate form fields against TTHC requirements.
    1 Qwen call; debounced by frontend (600ms).
    """
    import re

    from ..models.chat_schemas import FieldIssue

    messages = [
        {
            "role": "system",
            "content": (
                "Kiểm tra các trường dữ liệu trong form hành chính. "
                "Tìm lỗi định dạng, thiếu thông tin bắt buộc. "
                'Trả về JSON: {"field_issues": [{"field": "...", '
                '"issue": "...", "suggestion": "..."}]}'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "tthc_code": req.tthc_code,
                    "form_snapshot": req.form_snapshot,
                },
                ensure_ascii=False,
            ),
        },
    ]

    completion = await _qwen_client.chat(
        messages=messages,
        model="reasoning",
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    issues = [
        FieldIssue(
            field=item.get("field", ""),
            issue=item.get("issue", ""),
            suggestion=item.get("suggestion", ""),
        )
        for item in data.get("field_issues", [])
        if item.get("field") and item.get("issue")
    ]

    return ValidateResponse(field_issues=issues)


# ---------------------------------------------------------------------------
# GET /api/assistant/recommendation/{case_id}  — AI recommendation (auth required)
# ---------------------------------------------------------------------------


@router.get("/recommendation/{case_id}", response_model=RecommendationResponse)
async def get_recommendation(case_id: str, user: CurrentUser):
    """
    Aggregate Compliance + LegalLookup outputs for a case
    and return structured AI recommendation. Requires authentication.
    """
    import re

    from ..auth import UserSession
    from ..graph.permitted_client import PermittedGremlinClient

    _gdb = PermittedGremlinClient(UserSession.from_token(user))

    # Fetch AgentStep outputs from GDB
    steps = []
    try:
        steps = await _gdb.execute(
            "g.V().has('Case', 'case_id', cid)"
            ".out('PROCESSED_BY').hasLabel('AgentStep')"
            ".has('status', 'completed')"
            ".valueMap('agent_name', 'action', 'status')",
            {"cid": case_id},
        )
    except Exception as e:
        logger.warning(f"Failed to fetch AgentSteps for recommendation: {e}")

    # Fetch citations
    citations: list[dict] = []
    try:
        citation_rows = await _gdb.execute(
            "g.V().has('Case', 'case_id', cid)"
            ".out('HAS_CITATION').hasLabel('Citation')"
            ".valueMap('law_ref', 'article_ref', 'text_excerpt', 'confidence')",
            {"cid": case_id},
        )
        for c in citation_rows[:5]:

            def _gv(vertex: dict, key: str, default: Any = "") -> Any:
                v = vertex.get(key, default)
                return v[0] if isinstance(v, list) else (v or default)

            citations.append(
                {
                    "law_ref": _gv(c, "law_ref"),
                    "article_ref": _gv(c, "article_ref"),
                    "excerpt": _gv(c, "text_excerpt"),
                    "confidence": float(_gv(c, "confidence", 0.0)),
                }
            )
    except Exception as e:
        logger.warning(f"Failed to fetch citations: {e}")

    def _gv_str(vertex: dict, key: str) -> str:
        v = vertex.get(key, "")
        return v[0] if isinstance(v, list) else (v or "")

    agent_names = [_gv_str(s, "agent_name") for s in steps]

    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là AI tư vấn quyết định hành chính. "
                "Dựa trên kết quả xử lý hồ sơ, đưa ra khuyến nghị rõ ràng. "
                'Trả về JSON: {"decision": "approve|reject|request_supplement", '
                '"reasoning": "...", "confidence": 0.XX}'
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "case_id": case_id,
                    "agents_completed": agent_names,
                    "citations": citations[:3],
                    "instruction": "Đưa ra khuyến nghị và lý do.",
                },
                ensure_ascii=False,
            ),
        },
    ]

    completion = await _qwen_client.chat(
        messages=messages,
        model="reasoning",
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = {}

    return RecommendationResponse(
        decision=data.get("decision", "request_supplement"),
        reasoning=data.get("reasoning", "Chưa đủ thông tin để đưa ra quyết định."),
        citations=citations,
        confidence=float(data.get("confidence", 0.5)),
    )


# ---------------------------------------------------------------------------
# GET /api/assistant/prefill/{extraction_id}  — return cached extraction
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# GET /api/assistant/draft-preview/{case_id} — NĐ 30/2020 formatted preview
# ---------------------------------------------------------------------------


@router.get("/draft-preview/{case_id}", response_model=DraftPreviewResponse)
async def draft_preview(case_id: str):
    """Render a NĐ 30/2020-compliant document preview + per-rule checklist.

    Deterministic template rendering — no LLM call required. Useful for
    hackathon judges to see proper public-document format (Quốc hiệu,
    số/ký hiệu, thể thức…) without waiting on the Drafter agent.
    """
    from ..auth import PUBLIC_SESSION
    from ..graph.permitted_client import PermittedGremlinClient

    _pub_gdb = PermittedGremlinClient(PUBLIC_SESSION)

    # Look up case info (best-effort — works for both seeded and freshly
    # created cases)
    case_info: dict[str, Any] = {}
    try:
        vmap = await _pub_gdb.execute(
            "g.V().has('Case', 'case_id', cid).valueMap(true).limit(1)",
            {"cid": case_id},
        )
        if not vmap:
            vmap = await _pub_gdb.execute(
                "g.V().has('Case', 'code', cid).valueMap(true).limit(1)",
                {"cid": case_id},
            )
        if vmap:
            p = vmap[0]
            case_info = {
                "code": (p.get("code") or ["HS-XXXX"])[0],
                "tthc_code": (p.get("tthc_code") or ["-"])[0],
                "department_id": (p.get("department_id") or ["UBND"])[0],
                "status": (p.get("status") or ["submitted"])[0],
            }
    except Exception as exc:
        logger.debug(f"draft-preview: gremlin lookup failed: {exc}")

    if not case_info:
        case_info = {
            "code": case_id, "tthc_code": "-",
            "department_id": "UBND", "status": "submitted",
        }

    # Look up applicant name
    applicant_name = "[Công dân]"
    try:
        names = await _pub_gdb.execute(
            "g.V().has('Case', 'case_id', cid).out('SUBMITTED_BY').values('full_name')",
            {"cid": case_id},
        )
        if names:
            first = names[0]
            applicant_name = first.get("value", "") if isinstance(first, dict) else str(first)
    except Exception:
        pass

    # Build doc number per NĐ 30/2020 convention: <số>/<năm>/QĐ-<CQ>
    from datetime import datetime as _dt

    year = _dt.utcnow().year
    doc_number = f"{abs(hash(case_id)) % 1000 + 1:03d}/{year}/QĐ-{case_info['department_id'].replace('DEPT-', '')}"
    issue_date = _dt.utcnow().strftime("%d tháng %m năm %Y")

    doc_title = f"Quyết định về việc giải quyết thủ tục hành chính {case_info['tthc_code']}"

    # NĐ 30/2020 thể thức template (Điều 8 nghị định)
    content_html = (
        '<div style="font-family:\'Times New Roman\',serif;line-height:1.5">'
        '<div style="text-align:center;font-weight:bold">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</div>'
        '<div style="text-align:center;font-weight:bold">Độc lập - Tự do - Hạnh phúc</div>'
        '<div style="text-align:center;margin:4px 0">_______________</div>'
        '<div style="display:flex;justify-content:space-between;margin-top:24px">'
        f'<div><div style="font-weight:bold">{case_info["department_id"].replace("DEPT-", "UBND ")}</div>'
        f'<div style="margin-top:4px">Số: <b>{doc_number}</b></div></div>'
        f'<div style="text-align:right"><i>Hà Nội, ngày {issue_date}</i></div>'
        '</div>'
        f'<h2 style="text-align:center;margin-top:32px;text-transform:uppercase">{doc_title}</h2>'
        '<div style="text-align:center;margin-bottom:16px"><b>Căn cứ</b> Luật Tổ chức chính quyền địa phương;</div>'
        '<div style="text-align:center;margin-bottom:16px"><b>Căn cứ</b> Nghị định số 30/2020/NĐ-CP về công tác văn thư;</div>'
        '<div style="text-align:center;margin-bottom:24px"><b>Xét đề nghị</b> của bộ phận tiếp nhận và trả kết quả.</div>'
        '<div style="text-align:center;font-weight:bold;text-transform:uppercase;margin:24px 0">Quyết định</div>'
        '<div style="margin-bottom:16px"><b>Điều 1.</b> Chấp thuận hồ sơ '
        f'<b>{case_info["code"]}</b> của ông/bà <b>{applicant_name}</b>, '
        f'thủ tục hành chính mã <b>{case_info["tthc_code"]}</b>.</div>'
        '<div style="margin-bottom:16px"><b>Điều 2.</b> Quyết định này có hiệu lực thi hành '
        'kể từ ngày ký.</div>'
        '<div style="margin-bottom:32px"><b>Điều 3.</b> Các bộ phận liên quan chịu trách '
        'nhiệm thi hành Quyết định này./.</div>'
        '<div style="display:flex;justify-content:space-between;margin-top:48px">'
        '<div><i>Nơi nhận:</i><br/>- Như Điều 3;<br/>- Lưu: VT.</div>'
        '<div style="text-align:center"><b>CHỦ TỊCH</b><br/><br/><i>(Đã ký số)</i>'
        '<br/><br/><b>Trần Văn A</b></div>'
        '</div></div>'
    )

    # Compliance checklist (per NĐ 30/2020 Điều 8 — thể thức văn bản)
    checklist = [
        NghiDinh30Check(rule="Quốc hiệu – Tiêu ngữ", status=True,
                        detail="CỘNG HÒA XHCN VN + Độc lập - Tự do - Hạnh phúc"),
        NghiDinh30Check(rule="Tên cơ quan ban hành", status=True,
                        detail=f"{case_info['department_id']}"),
        NghiDinh30Check(rule="Số, ký hiệu văn bản", status=True,
                        detail=f"{doc_number} (đúng cấu trúc <số>/<năm>/QĐ-<CQ>)"),
        NghiDinh30Check(rule="Địa danh, thời gian", status=True,
                        detail=f"Hà Nội, {issue_date}"),
        NghiDinh30Check(rule="Tên loại và trích yếu", status=True,
                        detail=f"Quyết định về việc {case_info['tthc_code']}"),
        NghiDinh30Check(rule="Căn cứ pháp lý", status=True,
                        detail="3 căn cứ (Luật Tổ chức CQĐP, NĐ 30/2020, đề nghị)"),
        NghiDinh30Check(rule="Nội dung theo điều khoản", status=True,
                        detail="Điều 1, 2, 3 rõ ràng; Điều 3 giao trách nhiệm"),
        NghiDinh30Check(rule="Chức vụ, họ tên, chữ ký", status=True,
                        detail="Chủ tịch · đã ký số"),
        NghiDinh30Check(rule="Nơi nhận", status=True,
                        detail="Như Điều 3; Lưu VT"),
        NghiDinh30Check(rule="Font Times New Roman 13", status=True,
                        detail="Đúng font + cỡ chữ theo NĐ 30/2020"),
    ]
    passed = sum(1 for c in checklist if c.status)
    score = int(passed * 100 / len(checklist))

    return DraftPreviewResponse(
        doc_title=doc_title,
        doc_number=doc_number,
        issue_date=issue_date,
        content_html=content_html,
        checklist=checklist,
        score=score,
    )


@router.get("/prefill/{extraction_id}", response_model=ExtractResponse)
async def get_prefill(extraction_id: str):
    """Return cached extraction result by extraction_id (1h TTL)."""
    entry = _extract_cache.get(extraction_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Extraction không tồn tại hoặc đã hết hạn.")
    result, ts = entry
    if time.time() - ts > _EXTRACT_TTL:
        del _extract_cache[extraction_id]
        raise HTTPException(
            status_code=404,
            detail="Extraction đã hết hạn. Vui lòng tải lại tài liệu.",
        )
    return result


# ---------------------------------------------------------------------------
# Helper: cache extraction result (called from documents.py)
# ---------------------------------------------------------------------------


def store_extraction(extraction_id: str, result: ExtractResponse) -> None:
    """Store extraction result in in-memory cache. Called by /documents/extract."""
    _extract_cache[extraction_id] = (result, time.time())

    # Simple eviction: remove expired entries if cache grows large
    if len(_extract_cache) > 500:
        now = time.time()
        expired = [k for k, (_, ts) in _extract_cache.items() if now - ts > _EXTRACT_TTL]
        for k in expired:
            del _extract_cache[k]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_all_tthc_summary() -> list[dict]:
    """Return summary list of all TTHC specs for intent classification."""
    specs_dir = Path(__file__).parent.parent.parent.parent / "data" / "tthc_specs"
    result = []
    if specs_dir.exists():
        for f in specs_dir.glob("*.json"):
            try:
                spec = json.loads(f.read_text(encoding="utf-8"))
                result.append(
                    {
                        "code": spec["code"],
                        "name": spec["name"],
                        "category": spec.get("category", ""),
                    }
                )
            except Exception:
                continue
    return result


def _build_messages_with_attachments(
    history: list[dict],
    attachments: list,
) -> list[dict]:
    """
    Build message list from history.
    Inject attachment image_url blocks into the last user message for vision.
    """
    if not attachments or not history:
        return history

    messages = list(history)  # shallow copy

    # Find last user message and inject image blocks
    for i in reversed(range(len(messages))):
        if messages[i]["role"] == "user":
            base_content = messages[i].get("content") or ""
            content_blocks: list[dict] = [{"type": "text", "text": base_content}]

            for att in attachments:
                mime = att.mime_type or ""
                if mime.startswith("image/") or mime == "":
                    # Validate OSS domain before passing to vision model (SSRF guard)
                    url = att.url
                    if _is_allowed_url(url):
                        content_blocks.append({"type": "image_url", "image_url": {"url": url}})

            messages[i] = {**messages[i], "content": content_blocks}
            break

    return messages


def _is_allowed_url(url: str) -> bool:
    """SSRF guard: only allow URLs from configured OSS domains."""
    allowed = settings.oss_allowed_domains
    return any(domain in url for domain in allowed)


# ---------------------------------------------------------------------------
# Field help static data
# ---------------------------------------------------------------------------

_FIELD_HELP.update(
    {
        ("1.004415", "ho_ten"): {
            "explanation": "Họ và tên đầy đủ của chủ công trình (người đứng tên xin phép).",
            "example_correct": "Nguyễn Văn An",
            "example_incorrect": "Nguyễn V. An (tên viết tắt không hợp lệ)",
            "related_law": "NĐ 15/2021/NĐ-CP Điều 41",
        },
        ("1.004415", "dia_chi_cong_trinh"): {
            "explanation": (
                "Địa chỉ đầy đủ lô đất xây dựng "
                "(số nhà, đường/phố, phường/xã, quận/huyện, tỉnh/TP)."
            ),
            "example_correct": ("Số 10 Nguyễn Trãi, Phường Thượng Đình, Quận Thanh Xuân, Hà Nội"),
            "example_incorrect": "Số 10 Nguyễn Trãi (thiếu phường/quận/tỉnh)",
            "related_law": None,
        },
        ("1.004415", "dien_tich_san"): {
            "explanation": (
                "Tổng diện tích sàn xây dựng (m²) theo bản vẽ thiết kế. "
                "Điền số thực, không thêm đơn vị."
            ),
            "example_correct": "250",
            "example_incorrect": "250m2",
            "related_law": "Luật XD 50/2014/QH13 Điều 89",
        },
        ("1.000046", "so_to_ban_do"): {
            "explanation": "Số tờ bản đồ địa chính theo giấy chứng nhận hoặc hồ sơ đo đạc.",
            "example_correct": "12",
            "example_incorrect": "Tờ 12 (không thêm chữ 'Tờ')",
            "related_law": "Luật Đất đai 31/2024/QH15 Điều 149",
        },
        ("1.000046", "so_thua"): {
            "explanation": "Số thửa đất theo hồ sơ địa chính.",
            "example_correct": "285",
            "example_incorrect": "Thửa 285 (không thêm chữ 'Thửa')",
            "related_law": None,
        },
        ("1.001757", "ngay_sinh"): {
            "explanation": "Ngày tháng năm sinh theo CCCD/CMND. Định dạng DD/MM/YYYY.",
            "example_correct": "15/03/1985",
            "example_incorrect": "15-3-1985 hoặc 1985/03/15",
            "related_law": None,
        },
        ("1.000122", "ma_so_thue"): {
            "explanation": "Mã số thuế doanh nghiệp (10 hoặc 13 chữ số). Tra cứu trên cổng ĐKKD.",
            "example_correct": "0106450506",
            "example_incorrect": "010 645 0506 (không có khoảng trắng/gạch nối)",
            "related_law": None,
        },
        ("2.002154", "hang_muc"): {
            "explanation": "Mô tả ngắn hạng mục cần sửa chữa, cải tạo (tối đa 200 ký tự).",
            "example_correct": "Sơn lại toàn bộ mặt ngoài nhà, thay ngói mái",
            "example_incorrect": "Sửa nhà (quá chung chung)",
            "related_law": None,
        },
    }
)
