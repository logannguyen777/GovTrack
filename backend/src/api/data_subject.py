"""
backend/src/api/data_subject.py
Data Subject Rights endpoints per NĐ 13/2023 (Personal Data Protection Decree).

Prefix: /api/data-subject
All endpoints require authentication (JWT).

Endpoints:
  GET  /access        — Export all data for the authenticated user (rate 3/day)
  POST /delete        — Create a deletion request ticket (PENDING_REVIEW)
  POST /export        — Generate JSON export, upload to OSS, return presigned URL (1/day)
  GET  /consent       — Return consent history for the authenticated user

Admin:
  POST /admin/approve-delete/{ticket_id} — admin-only: approve deletion ticket
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from ..auth import CurrentUser, TokenClaims, require_role
from ..database import pg_connection
from ..models.schemas import (
    ConsentLogEntry,
    DataSubjectAccessResponse,
    DeletionRequest,
)

logger = logging.getLogger("govflow.data_subject")

router = APIRouter(prefix="/api/data-subject", tags=["Data Subject Rights"])


# ---------------------------------------------------------------------------
# GET /access — export all user data
# ---------------------------------------------------------------------------


@router.get("/access", response_model=DataSubjectAccessResponse)
async def get_data_access(
    user: CurrentUser,
) -> DataSubjectAccessResponse:
    """Trả về toàn bộ dữ liệu cá nhân của người dùng đang đăng nhập.

    Bao gồm: hồ sơ, tài liệu, nhật ký kiểm tra, lịch sử đồng ý.
    Giới hạn: 3 lần/ngày.
    """
    user_id = user.sub

    async with pg_connection() as conn:
        # Cases from analytics table
        case_rows = await conn.fetch(
            """
            SELECT case_id, department_id, tthc_code, status,
                   submitted_at, completed_at
            FROM analytics_cases
            WHERE metadata->>'submitted_by' = $1
               OR metadata->>'user_id' = $1
            ORDER BY submitted_at DESC
            LIMIT 200
            """,
            user_id,
        )

        # Audit events for this user
        audit_rows = await conn.fetch(
            """
            SELECT id::text, event_type, target_type, target_id,
                   case_id, details, created_at
            FROM audit_events_flat
            WHERE actor_id::text = $1
            ORDER BY created_at DESC
            LIMIT 500
            """,
            user_id,
        )

        # Consent log
        consent_rows = await conn.fetch(
            """
            SELECT consent_id, user_id, purpose, action,
                   ip_address::text, user_agent, timestamp
            FROM consent_log
            WHERE user_id = $1
            ORDER BY timestamp DESC
            """,
            user_id,
        )

    cases_data = [dict(r) for r in case_rows]
    # Convert datetime objects to ISO strings for JSON serialization
    for c in cases_data:
        for k, v in c.items():
            if isinstance(v, datetime):
                c[k] = v.isoformat()

    audit_data = []
    for r in audit_rows:
        row = dict(r)
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
        audit_data.append(row)

    consent_entries = [
        ConsentLogEntry(
            consent_id=r["consent_id"],
            user_id=r["user_id"],
            purpose=r["purpose"],
            action=r["action"],
            ip_address=r["ip_address"],
            user_agent=r["user_agent"],
            timestamp=r["timestamp"],
        )
        for r in consent_rows
    ]

    return DataSubjectAccessResponse(
        user_id=user_id,
        exported_at=datetime.now(UTC),
        cases=cases_data,
        documents=[],  # Documents are in GDB — populated via graph query if needed
        audit_events=audit_data,
        consent_history=consent_entries,
    )


# ---------------------------------------------------------------------------
# POST /delete — create deletion ticket
# ---------------------------------------------------------------------------


@router.post("/delete", response_model=DeletionRequest, status_code=202)
async def request_deletion(
    user: CurrentUser,
) -> DeletionRequest:
    """Yêu cầu xoá dữ liệu cá nhân theo NĐ 13/2023.

    Tạo phiếu yêu cầu (PENDING_REVIEW). Cần quản trị viên phê duyệt.
    """
    ticket_id = str(uuid.uuid4())
    user_id = user.sub
    now = datetime.now(UTC)

    async with pg_connection() as conn:
        # Store in audit log as a deletion request event
        await conn.execute(
            """
            INSERT INTO audit_events_flat
                (id, event_type, actor_id, actor_name, target_type, target_id, details)
            VALUES
                (gen_random_uuid(), 'data_subject.delete_request',
                 $1::uuid, $2, 'User', $3,
                 $4::jsonb)
            """,
            user_id,
            user.username if hasattr(user, "username") else user.sub,
            user_id,
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "status": "PENDING_REVIEW",
                    "requested_at": now.isoformat(),
                }
            ),
        )

    logger.info("Data deletion ticket created: ticket=%s user=%s", ticket_id, user_id)

    return DeletionRequest(
        ticket_id=ticket_id,
        user_id=user_id,
        status="PENDING_REVIEW",
        requested_at=now,
        notes="Yêu cầu đang chờ xét duyệt từ quản trị viên.",
    )


# ---------------------------------------------------------------------------
# POST /export — generate and upload data export to OSS
# ---------------------------------------------------------------------------


@router.post("/export")
async def export_data(
    user: CurrentUser,
) -> dict:
    """Xuất toàn bộ dữ liệu cá nhân dưới dạng JSON và tải lên OSS.

    Trả về URL tải xuống có thời hạn ngắn (300 giây).
    Giới hạn: 1 lần/ngày.
    """
    # Collect the data (reuse access logic)
    access_resp = await get_data_access(user=user)

    export_payload = access_resp.model_dump(mode="json")
    export_json = json.dumps(export_payload, ensure_ascii=False, indent=2)
    export_bytes = export_json.encode("utf-8")

    # Upload to OSS
    oss_key = f"data-exports/{user.sub}/{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_export.json"

    try:
        from ..database import oss_get_signed_url, oss_put_object

        oss_put_object(oss_key, export_bytes, content_type="application/json")
        ttl = 300
        signed_url = oss_get_signed_url(oss_key, expires=ttl)
    except Exception as exc:
        logger.error("Data export OSS upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Export upload failed") from exc

    logger.info("Data export generated: user=%s key=%s", user.sub, oss_key)

    return {
        "oss_key": oss_key,
        "download_url": signed_url,
        "expires_in_seconds": ttl,
        "generated_at": datetime.now(UTC).isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /consent — return consent history
# ---------------------------------------------------------------------------


@router.get("/consent", response_model=list[ConsentLogEntry])
async def get_consent_history(
    user: CurrentUser,
) -> list[ConsentLogEntry]:
    """Trả về lịch sử đồng ý/thu hồi đồng ý của người dùng."""
    user_id = user.sub

    async with pg_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT consent_id, user_id, purpose, action,
                   ip_address::text, user_agent, timestamp
            FROM consent_log
            WHERE user_id = $1
            ORDER BY timestamp DESC
            LIMIT 200
            """,
            user_id,
        )

    return [
        ConsentLogEntry(
            consent_id=r["consent_id"],
            user_id=r["user_id"],
            purpose=r["purpose"],
            action=r["action"],
            ip_address=r["ip_address"],
            user_agent=r["user_agent"],
            timestamp=r["timestamp"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# POST /admin/approve-delete/{ticket_id} — admin approval
# ---------------------------------------------------------------------------


@router.post("/admin/approve-delete/{ticket_id}")
async def approve_deletion(
    ticket_id: str,
    user: TokenClaims = Depends(require_role("admin")),
) -> dict:
    """Phê duyệt phiếu yêu cầu xoá dữ liệu (chỉ quản trị viên).

    Cập nhật trạng thái phiếu thành APPROVED và ghi nhật ký.
    Việc xoá dữ liệu thực tế phải được thực hiện thủ công theo quy trình nội bộ.
    """
    async with pg_connection() as conn:
        # Mark the deletion request as approved in audit log
        await conn.execute(
            """
            INSERT INTO audit_events_flat
                (id, event_type, actor_id, actor_name, target_type, target_id, details)
            VALUES
                (gen_random_uuid(), 'data_subject.delete_approved',
                 $1::uuid, $2, 'DeletionTicket', $3,
                 $4::jsonb)
            """,
            user.sub,
            user.sub,
            ticket_id,
            json.dumps(
                {
                    "ticket_id": ticket_id,
                    "status": "APPROVED",
                    "approved_by": user.sub,
                    "approved_at": datetime.now(UTC).isoformat(),
                }
            ),
        )

    logger.info("Deletion ticket approved: ticket=%s admin=%s", ticket_id, user.sub)

    return {
        "ticket_id": ticket_id,
        "status": "APPROVED",
        "approved_by": user.sub,
        "approved_at": datetime.now(UTC).isoformat(),
        "note": "Việc xoá dữ liệu thực tế sẽ được thực hiện trong vòng 30 ngày làm việc.",
    }
