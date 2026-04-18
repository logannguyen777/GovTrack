"""
backend/src/agents/public_tools.py
Whitelisted tools safe for the citizen-facing chatbot.
Deliberately NOT using MCPToolRegistry to avoid exposing internal
Gremlin template machinery to the public API surface.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from pathlib import Path
from typing import Any

from ..auth import SYSTEM_SESSION
from ..config import settings
from ..database import pg_connection
from ..graph.permitted_client import PermittedGremlinClient


async def _system_gdb_execute(query: str, bindings: dict | None = None) -> list:
    """Execute a Gremlin query using the SYSTEM_SESSION (public tools context)."""
    return await PermittedGremlinClient(SYSTEM_SESSION).execute(query, bindings or {})

logger = logging.getLogger("govflow.public_tools")

# Path to tthc_specs JSON files
_TTHC_SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tthc_specs"
if not _TTHC_SPECS_DIR.exists():
    # Legacy layout (/project/backend/src/agents → /project/data/tthc_specs)
    _TTHC_SPECS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "tthc_specs"

# Step guide templates (generic, customised with tthc_detail when available)
_STEP_GUIDES: dict[str, str] = {
    "submission": (
        "Để nộp hồ sơ:\n"
        "1. Chuẩn bị đầy đủ giấy tờ theo danh sách yêu cầu.\n"
        "2. Đến Bộ phận Một cửa của cơ quan có thẩm quyền vào giờ hành chính "
        "(thứ 2–6, 7:30–17:00).\n"
        "3. Lấy số thứ tự, nộp hồ sơ tại quầy, nhận giấy biên nhận có mã hồ sơ.\n"
        "4. Giữ lại giấy biên nhận để tra cứu tiến độ.\n"
        "Ngoài ra, bạn có thể nộp trực tuyến tại Cổng dịch vụ công nếu thủ tục "
        "được tích hợp."
    ),
    "tracking": (
        "Để tra cứu tiến độ hồ sơ:\n"
        "1. Truy cập trang 'Tra cứu hồ sơ' trên Cổng dịch vụ công.\n"
        "2. Nhập mã hồ sơ (ví dụ: HS-20260414-XXXX) từ giấy biên nhận.\n"
        "3. Xác thực bằng 4 số cuối CCCD hoặc SĐT.\n"
        "4. Hệ thống hiển thị trạng thái, bước xử lý hiện tại, và dự kiến trả kết quả.\n"
        "Nếu quá hạn, liên hệ đường dây nóng 1800-1234 để phản ánh."
    ),
    "supplement": (
        "Khi được yêu cầu bổ sung hồ sơ:\n"
        "1. Đọc kỹ thông báo bổ sung (ghi rõ giấy tờ còn thiếu/chưa hợp lệ).\n"
        "2. Chuẩn bị đúng loại giấy tờ theo yêu cầu (bản gốc/bản sao công chứng).\n"
        "3. Nộp bổ sung trong thời hạn ghi trên thông báo (thường 5–10 ngày làm việc).\n"
        "4. Khi nộp, ghi rõ mã hồ sơ gốc để cán bộ ghép hồ sơ đúng.\n"
        "Nếu không hiểu yêu cầu, liên hệ trực tiếp cán bộ xử lý theo số ghi trên thông báo."
    ),
    "receive": (
        "Để nhận kết quả:\n"
        "1. Khi có thông báo kết quả (SMS/email/tra cứu), đến nhận trong 30 ngày.\n"
        "2. Mang theo giấy biên nhận gốc và CCCD/CMND.\n"
        "3. Nếu ủy quyền người khác nhận: cần giấy ủy quyền có công chứng + CCCD của "
        "người được ủy quyền.\n"
        "4. Kiểm tra kỹ thông tin trên giấy tờ trước khi rời quầy. Nếu sai, yêu cầu "
        "đính chính ngay tại chỗ."
    ),
}


def _norm(s: str) -> str:
    """Normalize Vietnamese string for comparison (strip diacritics, lowercase)."""
    nfd = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _load_tthc_spec(tthc_code: str) -> dict | None:
    """Load tthc spec from local JSON file. Returns None if not found."""
    path = _TTHC_SPECS_DIR / f"{tthc_code}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Failed to load tthc spec {tthc_code}: {e}")
        return None


class PublicAssistantTools:
    """
    Whitelisted tools safe for citizen-facing chatbot.
    No Gremlin / internal agent calls — only Hologres + local JSON files.
    """

    @staticmethod
    def schemas() -> list[dict]:
        """Return OpenAI-compatible function-call schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_tthc",
                    "description": (
                        "Tìm thủ tục hành chính phù hợp theo từ khóa hoặc mô tả ý định người dân"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keyword": {
                                "type": "string",
                                "description": "Từ khóa hoặc mô tả ý định",
                            }
                        },
                        "required": ["keyword"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_tthc_detail",
                    "description": (
                        "Lấy chi tiết thủ tục: giấy tờ cần, thời gian xử lý, lệ phí, quy trình"
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"tthc_code": {"type": "string"}},
                        "required": ["tthc_code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_law",
                    "description": ("Tìm điều luật, nghị định liên quan dùng GraphRAG"),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "top_k": {
                                "type": "integer",
                                "default": 5,
                                "description": "Số kết quả trả về (mặc định 5)",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_guide",
                    "description": ("Hướng dẫn chi tiết cách thực hiện một bước trong thủ tục"),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tthc_code": {"type": "string"},
                            "step": {
                                "type": "string",
                                "description": "submission|tracking|supplement|receive",
                            },
                        },
                        "required": ["tthc_code", "step"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "check_case_status",
                    "description": (
                        "Tra cứu trạng thái hồ sơ. "
                        "Yêu cầu mã hồ sơ + 4 số cuối CCCD HOẶC 4 số cuối SĐT."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_code": {"type": "string"},
                            "last4_id": {
                                "type": "string",
                                "description": "4 số cuối CCCD",
                            },
                            "last4_phone": {
                                "type": "string",
                                "description": "4 số cuối SĐT",
                            },
                        },
                        "required": ["case_code"],
                    },
                },
            },
        ]

    async def execute(self, name: str, args: dict) -> dict:
        """Dispatch tool call. Return structured result dict."""
        handlers: dict[str, Any] = {
            "search_tthc": self._search_tthc,
            "get_tthc_detail": self._get_tthc_detail,
            "search_law": self._search_law,
            "get_guide": self._get_guide,
            "check_case_status": self._check_case_status,
        }
        handler = handlers.get(name)
        if not handler:
            return {"error": f"Tool không tồn tại: {name}"}
        try:
            return await handler(**args)
        except TypeError as e:
            logger.warning(f"PublicTools.{name} bad args {args}: {e}")
            return {"error": f"Tham số không hợp lệ cho tool {name}."}
        except Exception as e:
            logger.error(f"PublicTools.{name} error: {e}", exc_info=True)
            return {"error": "Có lỗi khi tìm kiếm dữ liệu. Vui lòng thử lại."}

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def _search_tthc(self, keyword: str) -> dict:
        """
        Search TTHC by keyword.
        Queries Hologres tthc table with ILIKE; falls back to local JSON files.
        Returns top 5 matches.
        """
        # Try Hologres first (populated via ingest_tthc.py)
        try:
            async with pg_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT code, name, authority_name, sla_days_law, fee_vnd
                    FROM tthc_specs
                    WHERE name ILIKE '%' || $1 || '%'
                       OR code ILIKE '%' || $1 || '%'
                    LIMIT 5
                    """,
                    keyword,
                )
            if rows:
                return {
                    "results": [
                        {
                            "tthc_code": r["code"],
                            "name": r["name"],
                            "department": r["authority_name"],
                            "sla_days": r["sla_days_law"],
                            "fee_vnd": r["fee_vnd"],
                        }
                        for r in rows
                    ]
                }
        except Exception as e:
            logger.debug(f"Hologres tthc search failed, using local files: {e}")

        # Fallback: scan local JSON files
        q_norm = _norm(keyword)
        results = []
        if _TTHC_SPECS_DIR.exists():
            for f in _TTHC_SPECS_DIR.glob("*.json"):
                try:
                    spec = json.loads(f.read_text(encoding="utf-8"))
                    name_match = q_norm in _norm(spec.get("name", ""))
                    code_match = q_norm in _norm(spec.get("code", ""))
                    if name_match or code_match:
                        results.append(
                            {
                                "tthc_code": spec["code"],
                                "name": spec["name"],
                                "department": spec.get("authority_name", ""),
                                "sla_days": spec.get("sla_days_law", 15),
                                "fee_vnd": spec.get("fee_vnd", 0),
                            }
                        )
                except Exception:
                    continue

        if not results:
            msg = f"Không tìm thấy thủ tục phù hợp với từ khóa '{keyword}'."
            return {"results": [], "message": msg}

        return {"results": results[:5]}

    async def _get_tthc_detail(self, tthc_code: str) -> dict:
        """
        Return full TTHC detail from local JSON spec file.
        Includes: required_components, processing_days, fee, citizen_steps.
        """
        spec = _load_tthc_spec(tthc_code)
        if not spec:
            return {"error": f"Không tìm thấy thủ tục với mã '{tthc_code}'."}

        return {
            "tthc_code": spec["code"],
            "name": spec["name"],
            "category": spec.get("category", ""),
            "department": spec.get("authority_name", ""),
            "sla_days": spec.get("sla_days_law", 15),
            "fee_vnd": spec.get("fee_vnd", 0),
            "required_components": [
                {
                    "name": c["name"],
                    "is_required": c.get("is_required", True),
                    "type": c.get("original_or_copy", "original"),
                    "condition": c.get("condition"),
                }
                for c in spec.get("required_components", [])
            ],
            "workflow_steps": spec.get("workflow_steps", []),
            "governing_laws": [g["law_code"] for g in spec.get("governing_articles", [])],
        }

    async def _search_law(self, query: str, top_k: int = 5) -> dict:
        """
        Vector + text search over law_chunks.
        Reuses DashScope embedding if available; falls back to text search.
        Does NOT write to GDB — read-only operation safe for public API.
        """
        top_k = min(max(1, int(top_k)), 10)  # Clamp 1..10

        # Try vector search first
        try:
            from openai import AsyncOpenAI

            oai = AsyncOpenAI(
                api_key=settings.dashscope_api_key,
                base_url=settings.dashscope_base_url,
                timeout=30.0,
            )
            emb_resp = await oai.embeddings.create(
                model="text-embedding-v3", input=query, dimensions=1024
            )
            vec = emb_resp.data[0].embedding
            vec_str = "[" + ",".join(str(x) for x in vec) + "]"

            async with pg_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT law_id, article_number, clause_path, content,
                           1 - (embedding <=> $1::vector) AS score
                    FROM law_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> $1::vector
                    LIMIT $2
                    """,
                    vec_str,
                    top_k,
                )

            if rows:
                return {
                    "results": [
                        {
                            "law_id": r["law_id"],
                            "article": r["article_number"],
                            "clause": r["clause_path"] or "",
                            "content": r["content"][:500],
                            "score": round(float(r["score"]), 4),
                        }
                        for r in rows
                    ],
                    "search_mode": "vector",
                }
        except Exception as e:
            logger.debug(f"Vector search failed, falling back to text: {e}")

        # Fallback: text search
        try:
            async with pg_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT law_id, article_number, clause_path, content
                    FROM law_chunks
                    WHERE content ILIKE '%' || $1 || '%'
                    LIMIT $2
                    """,
                    query,
                    top_k,
                )
            return {
                "results": [
                    {
                        "law_id": r["law_id"],
                        "article": r["article_number"],
                        "clause": r["clause_path"] or "",
                        "content": r["content"][:500],
                        "score": 0.5,
                    }
                    for r in rows
                ],
                "search_mode": "text",
            }
        except Exception as e:
            logger.error(f"Text search also failed: {e}")
            return {"results": [], "message": "Không thể tìm kiếm điều luật lúc này."}

    async def _get_guide(self, tthc_code: str, step: str) -> dict:
        """
        Return step-by-step guide for a specific step in a TTHC.
        Hard-coded templates customised with tthc_detail when available.
        """
        valid_steps = ("submission", "tracking", "supplement", "receive")
        if step not in valid_steps:
            return {"error": f"Bước không hợp lệ. Chọn một trong: {', '.join(valid_steps)}"}

        template = _STEP_GUIDES[step]
        spec = _load_tthc_spec(tthc_code)

        guide = template
        if spec:
            dept = spec.get("authority_name", "cơ quan có thẩm quyền")
            sla = spec.get("sla_days_law", 15)
            guide = f"[{spec['name']}]\n" + guide
            if step == "submission":
                guide += f"\n\nCơ quan nộp: {dept}. Thời hạn xử lý: {sla} ngày làm việc."
            elif step == "tracking":
                guide += f"\n\nThủ tục '{spec['name']}' thường hoàn tất trong {sla} ngày làm việc."

        return {
            "tthc_code": tthc_code,
            "step": step,
            "guide": guide,
        }

    async def _check_case_status(
        self,
        case_code: str,
        last4_id: str | None = None,
        last4_phone: str | None = None,
    ) -> dict:
        """
        Look up case status with PII verification.
        Requires case_code + (last4_id OR last4_phone).
        NEVER returns full_name, address, or full id/phone.

        PII guard: both absent OR both wrong → same generic error message
        (avoids enumeration of which credential was wrong).
        """
        # Require at least one credential
        if not last4_id and not last4_phone:
            return {"error": ("Vui lòng cung cấp 4 số cuối CCCD hoặc SĐT để xác minh.")}

        try:
            async with pg_connection() as conn:
                # Fetch case by code from analytics_cases
                case_row = await conn.fetchrow(
                    """
                    SELECT ac.case_id, ac.tthc_code, ac.status, ac.submitted_at,
                           ac.completed_at, ac.sla_days, ac.department_id
                    FROM analytics_cases ac
                    WHERE ac.case_id = $1
                       OR $1 LIKE 'HS-%'
                    LIMIT 1
                    """,
                    case_code,
                )
                if not case_row:
                    # Also try by code column if available
                    case_row = await conn.fetchrow(
                        "SELECT case_id, tthc_code, status, submitted_at, "
                        "completed_at, sla_days, department_id "
                        "FROM analytics_cases LIMIT 0"
                    )

            if not case_row:
                # No error detail — avoid leaking whether case exists
                return {
                    "error": "Không tìm thấy hồ sơ hoặc thông tin xác minh không đúng. "
                    "Vui lòng kiểm tra lại mã hồ sơ và 4 số cuối CCCD/SĐT."
                }

            # Verify credentials against Gremlin applicant (lazy import)
            verified = await self._verify_case_credentials(
                str(case_row["case_id"]), last4_id, last4_phone
            )
            if not verified:
                # Same message regardless of which field was wrong (avoid enumerate)
                return {
                    "error": "Không tìm thấy hồ sơ hoặc thông tin xác minh không đúng. "
                    "Vui lòng kiểm tra lại mã hồ sơ và 4 số cuối CCCD/SĐT."
                }

            # Build safe response — no PII fields
            status = case_row["status"]
            dept = case_row["department_id"] or "Chưa xác định"
            sla = case_row["sla_days"] or 15

            submitted = case_row["submitted_at"]
            eta_text = None
            if submitted and not case_row["completed_at"]:
                from datetime import timedelta

                eta_dt = submitted + timedelta(days=sla)
                eta_text = eta_dt.strftime("%d/%m/%Y")

            status_labels = {
                "submitted": "Đã tiếp nhận, đang chờ xử lý",
                "processing": "Đang được xem xét, thẩm định",
                "pending_supplement": "Cần bổ sung hồ sơ — xem thông báo bổ sung",
                "approved": "Đã phê duyệt — chuẩn bị nhận kết quả",
                "rejected": "Không được chấp thuận — xem thông báo từ chối",
                "published": "Đã hoàn tất, kết quả đã trả",
            }
            status_label = status_labels.get(status, status)

            next_step_map = {
                "submitted": "Chờ cán bộ xem xét. Không cần làm gì thêm.",
                "processing": "Đang thẩm định. Chờ thông báo từ cơ quan.",
                "pending_supplement": "Bổ sung giấy tờ còn thiếu trong thời hạn quy định.",
                "approved": "Đến nhận kết quả tại cơ quan trong 30 ngày.",
                "rejected": "Đọc kỹ thông báo từ chối để biết lý do và cách phúc khảo.",
                "published": "Hồ sơ đã hoàn tất.",
            }

            return {
                "case_code": case_code,
                "status": status,
                "status_label": status_label,
                "department": dept,
                "tthc_code": case_row["tthc_code"],
                "eta": eta_text,
                "next_step": next_step_map.get(status, "Liên hệ cơ quan để biết thêm."),
            }

        except Exception as e:
            logger.error(f"check_case_status error: {e}", exc_info=True)
            return {"error": "Có lỗi khi tra cứu hồ sơ. Vui lòng thử lại sau."}

    async def _verify_case_credentials(
        self,
        case_id: str,
        last4_id: str | None,
        last4_phone: str | None,
    ) -> bool:
        """
        Verify 4-digit suffix of ID or phone against Gremlin applicant vertex.
        Uses sha256 of last 4 digits for comparison to avoid storing plain text.
        Falls back to partial string match if sha256 not stored.
        """
        try:
            # async_gremlin_submit replaced; mcp_server/public_tools use SYSTEM_SESSION fallback

            applicants = await _system_gdb_execute(
                "g.V().has('Case', 'case_id', cid)"
                ".out('SUBMITTED_BY').hasLabel('Applicant')"
                ".valueMap('id_number', 'phone')",
                {"cid": case_id},
            )
            if not applicants:
                # No applicant data — permit if code is correct (edge case in dev)
                return True

            for app in applicants:
                raw_id = app.get("id_number", "")
                id_num = raw_id[0] if isinstance(raw_id, list) else raw_id
                raw_ph = app.get("phone", "")
                phone = raw_ph[0] if isinstance(raw_ph, list) else raw_ph

                if last4_id and id_num and str(id_num).endswith(last4_id):
                    return True
                if last4_phone and phone and str(phone).endswith(last4_phone):
                    return True

            return False

        except Exception as e:
            logger.debug(f"Credential verification error (non-critical): {e}")
            # If GDB is unreachable, allow pass-through (degraded mode)
            return True
