"""backend/src/api/demo.py -- Demo reset endpoint (admin/security only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from ..auth import SYSTEM_SESSION, TokenClaims, require_role
from ..database import pg_connection
from ..graph.permitted_client import PermittedGremlinClient

router = APIRouter(prefix="/demo", tags=["Demo"])

# Canonical demo cases to re-seed on reset.
_DEMO_CASES = [
    {
        "tthc_code": "1.004415",
        "department_id": "DEPT-QLDT",
        "applicant_name": "Nguyễn Văn Bình",
        "applicant_id_number": "001085012345",
        "applicant_phone": "0912345678",
        "applicant_address": "Số 18 Nguyễn Trãi, Phường Thượng Đình, Quận Thanh Xuân, Hà Nội",
    },
    {
        "tthc_code": "1.000046",
        "department_id": "DEPT-TNMT",
        "applicant_name": "Trần Thị Hoa",
        "applicant_id_number": "052075067890",
        "applicant_phone": "0987654321",
        "applicant_address": "Số 45 Lê Hồng Phong, Phường Trần Phú, TP Quy Nhơn, Bình Định",
    },
    {
        "tthc_code": "1.001757",
        "department_id": "DEPT-DKKD",
        "applicant_name": "Lê Minh Tuấn",
        "applicant_id_number": "079082034567",
        "applicant_phone": "0903456789",
        "applicant_address": "Số 7 Đinh Tiên Hoàng, Phường Đa Kao, Quận 1, TP Hồ Chí Minh",
    },
    {
        "tthc_code": "1.000122",
        "department_id": "DEPT-TUPHAP",
        "applicant_name": "Phạm Thị Lan",
        "applicant_id_number": "036095089012",
        "applicant_phone": "0978901234",
        "applicant_address": "Số 22 Bà Triệu, Phường Lê Đại Hành, Quận Hai Bà Trưng, Hà Nội",
    },
    {
        "tthc_code": "2.002154",
        "department_id": "DEPT-TNMT",
        "applicant_name": "Công ty TNHH Xanh Việt",
        "applicant_id_number": "0106789012",
        "applicant_phone": "02438765432",
        "applicant_address": "Lô B12 KCN Thăng Long, Huyện Đông Anh, Hà Nội",
    },
]


async def _seed_case(case_spec: dict, gdb: PermittedGremlinClient) -> str:
    """Create one demo case in GDB + postgres. Returns the case code."""
    case_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    code = f"DEMO-{case_spec['tthc_code'].replace('.', '')}-{case_id[:6].upper()}"
    now_iso = now.isoformat()

    await gdb.execute(
        "g.addV('Case')"
        ".property('case_id', case_id).property('code', code)"
        ".property('status', 'submitted').property('submitted_at', now)"
        ".property('department_id', dept).property('tthc_code', tthc)",
        {
            "case_id": case_id, "code": code, "now": now_iso,
            "dept": case_spec["department_id"], "tthc": case_spec["tthc_code"],
        },
    )

    applicant_id = str(uuid.uuid4())
    await gdb.execute(
        "g.addV('Applicant')"
        ".property('applicant_id', aid).property('full_name', name)"
        ".property('id_number', id_num).property('phone', phone)"
        ".property('address', addr)",
        {
            "aid": applicant_id,
            "name": case_spec["applicant_name"],
            "id_num": case_spec["applicant_id_number"],
            "phone": case_spec["applicant_phone"],
            "addr": case_spec["applicant_address"],
        },
    )
    await gdb.execute(
        "g.V().has('Applicant', 'applicant_id', aid)"
        ".as('a').V().has('Case', 'case_id', cid)"
        ".addE('SUBMITTED_BY').to('a')",
        {"cid": case_id, "aid": applicant_id},
    )

    async with pg_connection() as conn:
        await conn.execute(
            "INSERT INTO analytics_cases "
            "(case_id, department_id, tthc_code, status, submitted_at) "
            "VALUES ($1, $2, $3, 'submitted', $4) "
            "ON CONFLICT DO NOTHING",
            case_id, case_spec["department_id"], case_spec["tthc_code"], now,
        )

    return code


@router.post("/reset")
async def demo_reset(
    user: TokenClaims = Depends(require_role("admin", "security")),
):
    """Re-seed the 5 canonical demo cases for live demonstrations."""
    # Use SYSTEM_SESSION for demo reset — admin endpoint, audit-logged as system
    gdb = PermittedGremlinClient(SYSTEM_SESSION)
    created_codes: list[str] = []
    errors: list[dict] = []

    for spec in _DEMO_CASES:
        try:
            code = await _seed_case(spec, gdb)
            created_codes.append(code)
        except Exception as exc:
            errors.append({"tthc_code": spec["tthc_code"], "error": str(exc)})

    return {
        "reset": True,
        "cases_created": created_codes,
        "errors": errors,
    }
