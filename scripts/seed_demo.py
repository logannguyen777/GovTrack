"""
scripts/seed_demo.py
Seed the demo environment with deterministic users, cases, documents, gaps and
citations. Idempotent — safe to run multiple times.

Usage:
    python scripts/seed_demo.py

Produces (in GDB + PostgreSQL analytics_cases):
    - 1 new user (citizen_demo); other users come from init.sql
    - 5 primary cases (1 hero CPXD case with PCCC gap, full graph structure)
    - 3 completed cases (analytics_cases rows only)
    - 25 benchmark cases (analytics_cases rows only)
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher as _PH

sys.path.insert(0, "backend")

from src.database import (  # noqa: E402
    close_gremlin_client,
    close_pg_pool,
    create_gremlin_client,
    create_pg_pool,
    get_pg_pool,
    gremlin_submit,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("seed_demo")

# ============================================================
# Constants
# ============================================================
PW_HASH = _PH().hash("demo")  # argon2 hash for demo password
NOW = datetime.now(timezone.utc)

# Additional user (the existing users in init.sql cover staff; we add one
# citizen persona for the elevation scenario).
EXTRA_USERS = [
    # (username, full_name, email, role, clearance, departments)
    ("citizen_demo", "Nguyen Van Minh", "citizen@govflow.vn",
     "public_viewer", 0, []),
]


# ============================================================
# Primary demo cases (full graph structure)
# ============================================================
def _iso(dt: datetime) -> str:
    return dt.isoformat()


PRIMARY_CASES = [
    {
        # --- HERO CASE: CPXD with PCCC gap ---
        "case_id": "CASE-2026-0001",
        "code": "HS-20260101-CASE0001",
        "tthc_code": "1.004415",
        "tthc_name": "Cap phep xay dung",
        "department_id": "DEPT-QLDT",
        "status": "consultation",
        "classification": 0,
        "submitted_at": _iso(NOW - timedelta(days=5)),
        "sla_days": 15,
        "applicant": {
            "name": "Nguyen Van Minh",
            "id_number": "024090000123",
            "phone": "0901234567",
            "address": "12 Tran Phu, Binh Dinh",
        },
        "documents": [
            ("DOC-001", "don_xin_cap_phep", "don_cpxd.pdf"),
            ("DOC-002", "ban_ve_thiet_ke",  "banve.pdf"),
            ("DOC-003", "giay_cn_qsdd",     "qsdd.pdf"),
            ("DOC-004", "hop_dong_xd",      "hopdong.pdf"),
        ],
        "gaps": [
            ("GAP-001",
             "Thieu giay chung nhan PCCC",
             "high",
             "ND 136/2020 Dieu 9 khoan 2",
             "Yeu cau bo sung giay chung nhan PCCC tu co quan PCCC dia phuong"),
        ],
        "citations": [
            ("CIT-001", "Nghi dinh 136/2020/ND-CP", "Dieu 9, khoan 2", 0.95),
            ("CIT-002", "Luat Xay dung 2014",        "Dieu 89",         0.88),
        ],
    },
    {
        "case_id": "CASE-2026-0002",
        "code": "HS-20260101-CASE0002",
        "tthc_code": "1.000046",
        "tthc_name": "GCN quyen su dung dat",
        "department_id": "DEPT-TNMT",
        "status": "extracting",
        "classification": 0,
        "submitted_at": _iso(NOW - timedelta(days=3)),
        "sla_days": 20,
        "applicant": {
            "name": "Tran Thi Lan",
            "id_number": "024090000456",
            "phone": "0912345678",
            "address": "45 Le Loi, Binh Dinh",
        },
        "documents": [
            ("DOC-010", "don_dang_ky",    "don_dk.pdf"),
            ("DOC-011", "ho_so_dia_chinh","diachinh.pdf"),
            ("DOC-012", "ban_do",          "bando.pdf"),
        ],
        "gaps": [],
        "citations": [],
    },
    {
        "case_id": "CASE-2026-0003",
        "code": "HS-20260101-CASE0003",
        "tthc_code": "1.001757",
        "tthc_name": "Dang ky kinh doanh",
        "department_id": "DEPT-QLDT",
        "status": "approved",
        "classification": 0,
        "submitted_at": _iso(NOW - timedelta(days=8)),
        "sla_days": 10,
        "applicant": {
            "name": "Le Van Hung",
            "id_number": "024090000789",
            "phone": "0987654321",
            "address": "78 Nguyen Hue, Binh Dinh",
        },
        "documents": [
            ("DOC-020", "giay_de_nghi", "denghi.pdf"),
            ("DOC-021", "dieu_le",      "dieule.pdf"),
        ],
        "gaps": [],
        "citations": [
            ("CIT-010", "Luat Doanh nghiep 2020", "Dieu 26", 0.92),
        ],
    },
    {
        "case_id": "CASE-2026-0004",
        "code": "HS-20260101-CASE0004",
        "tthc_code": "1.000122",
        "tthc_name": "Ly lich tu phap",
        "department_id": "DEPT-PHAPCHE",
        "status": "published",
        "classification": 1,  # CONFIDENTIAL — contains personal history
        "submitted_at": _iso(NOW - timedelta(days=12)),
        "sla_days": 15,
        "applicant": {
            "name": "Pham Minh Duc",
            "id_number": "024090000101",
            "phone": "0909111222",
            "address": "101 Le Duan, Binh Dinh",
        },
        "documents": [
            ("DOC-030", "don_yeu_cau", "yeucau.pdf"),
            ("DOC-031", "cmnd",        "cccd.pdf"),
        ],
        "gaps": [],
        "citations": [],
    },
    {
        "case_id": "CASE-2026-0005",
        "code": "HS-20260101-CASE0005",
        "tthc_code": "2.002154",
        "tthc_name": "Giay phep moi truong",
        "department_id": "DEPT-TNMT",
        "status": "submitted",
        "classification": 0,
        "submitted_at": _iso(NOW - timedelta(hours=6)),
        "sla_days": 30,
        "applicant": {
            "name": "Cty TNHH Xanh Viet",
            "id_number": "0300123456",
            "phone": "0283800800",
            "address": "KCN Phu Tai, Binh Dinh",
        },
        "documents": [
            ("DOC-040", "bao_cao_dtm",  "dtm.pdf"),
            ("DOC-041", "giay_phep_kd", "gpkd.pdf"),
        ],
        "gaps": [],
        "citations": [],
    },
]

# ============================================================
# Completed cases (analytics_cases rows only — for dashboard KPIs)
# ============================================================
COMPLETED_CASES = [
    {
        "case_id": f"CASE-2026-{100 + i:04d}",
        "tthc_code": tthc,
        "department_id": "DEPT-QLDT",
        "status": "published",
        "submitted_at": _iso(NOW - timedelta(days=d + 2)),
        "completed_at": _iso(NOW - timedelta(days=d - processing_days)),
        "processing_days": processing_days,
        "sla_days": 15,
        "is_overdue": False,
    }
    for i, (tthc, d, processing_days) in enumerate([
        ("1.004415", 14, 13),
        ("1.000046", 7, 6),
        ("1.001757", 5, 4),
    ])
]

# 25 benchmark cases across TTHCs and statuses (for dashboard coverage)
_BENCH_TTHCS = ["1.004415", "1.000046", "1.001757", "1.000122", "2.002154"]
_BENCH_STATUSES = [
    "submitted", "extracting", "gap_checking", "legal_review",
    "drafting", "leader_review", "consultation", "approved",
]
_BENCH_DEPTS = ["DEPT-QLDT", "DEPT-TNMT", "DEPT-PHAPCHE", "DEPT-ADMIN"]

BENCHMARK_CASES = [
    {
        "case_id": f"CASE-2026-{200 + i:04d}",
        "tthc_code": _BENCH_TTHCS[i % len(_BENCH_TTHCS)],
        "department_id": _BENCH_DEPTS[i % len(_BENCH_DEPTS)],
        "status": _BENCH_STATUSES[i % len(_BENCH_STATUSES)],
        "submitted_at": _iso(NOW - timedelta(days=i % 20)),
        "sla_days": 15,
        "is_overdue": (i % 7 == 0),
    }
    for i in range(25)
]


# ============================================================
# Seeders
# ============================================================
async def seed_users(conn) -> None:
    created = 0
    for username, full_name, email, role, clearance, depts in EXTRA_USERS:
        result = await conn.execute(
            """
            INSERT INTO users (id, username, full_name, email, password_hash,
                role, clearance_level, departments)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (username) DO NOTHING
            """,
            uuid.uuid4(), username, full_name, email,
            PW_HASH, role, clearance, depts,
        )
        if result.endswith(" 1"):
            created += 1
    log.info(f"[users] {created} new / {len(EXTRA_USERS)} total in EXTRA_USERS")


def upsert_case_vertex(c: dict) -> None:
    gremlin_submit(
        "g.V().has('Case','case_id',cid).fold()"
        ".coalesce(unfold(),"
        " addV('Case').property('case_id',cid).property('code',code)"
        ".property('tthc_code',tthc).property('department_id',dept)"
        ".property('status',status).property('submitted_at',sub)"
        ".property('classification',classif))",
        {
            "cid": c["case_id"], "code": c["code"], "tthc": c["tthc_code"],
            "dept": c["department_id"], "status": c["status"],
            "sub": c["submitted_at"], "classif": c.get("classification", 0),
        },
    )


def upsert_applicant_and_edge(case_id: str, app: dict) -> None:
    applicant_id = f"APP-{case_id}"
    gremlin_submit(
        "g.V().has('Applicant','applicant_id',aid).fold()"
        ".coalesce(unfold(),"
        " addV('Applicant').property('applicant_id',aid)"
        ".property('full_name',name).property('id_number',idn)"
        ".property('phone',phone).property('address',addr))",
        {
            "aid": applicant_id, "name": app["name"],
            "idn": app["id_number"], "phone": app["phone"],
            "addr": app["address"],
        },
    )
    # Idempotent edge: only add SUBMITTED_BY if missing
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('SUBMITTED_BY').where(__.inV().has('Applicant','applicant_id',aid)),"
        " __.addE('SUBMITTED_BY').to(__.V().has('Applicant','applicant_id',aid))"
        ")",
        {"cid": case_id, "aid": applicant_id},
    )


def upsert_document_and_edge(case_id: str, doc_id: str, doc_type: str, filename: str) -> None:
    gremlin_submit(
        "g.V().has('Document','document_id',did).fold()"
        ".coalesce(unfold(),"
        " addV('Document').property('document_id',did)"
        ".property('doc_type',dtype).property('filename',fn))",
        {"did": doc_id, "dtype": doc_type, "fn": filename},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('HAS_DOCUMENT').where(__.inV().has('Document','document_id',did)),"
        " __.addE('HAS_DOCUMENT').to(__.V().has('Document','document_id',did))"
        ")",
        {"cid": case_id, "did": doc_id},
    )


def upsert_gap_and_edge(
    case_id: str, gap_id: str, description: str,
    severity: str, requirement_ref: str, fix_suggestion: str,
) -> None:
    gremlin_submit(
        "g.V().has('Gap','gap_id',gid).fold()"
        ".coalesce(unfold(),"
        " addV('Gap').property('gap_id',gid).property('description',d)"
        ".property('severity',s).property('requirement_ref',rr)"
        ".property('fix_suggestion',fx))",
        {"gid": gap_id, "d": description, "s": severity,
         "rr": requirement_ref, "fx": fix_suggestion},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('HAS_GAP').where(__.inV().has('Gap','gap_id',gid)),"
        " __.addE('HAS_GAP').to(__.V().has('Gap','gap_id',gid))"
        ")",
        {"cid": case_id, "gid": gap_id},
    )


def upsert_citation_and_edge(
    case_id: str, citation_id: str, law_name: str,
    article: str, relevance: float,
) -> None:
    gremlin_submit(
        "g.V().has('Citation','citation_id',cit).fold()"
        ".coalesce(unfold(),"
        " addV('Citation').property('citation_id',cit)"
        ".property('law_name',l).property('article',a).property('relevance',r))",
        {"cit": citation_id, "l": law_name, "a": article, "r": relevance},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('CITES').where(__.inV().has('Citation','citation_id',cit)),"
        " __.addE('CITES').to(__.V().has('Citation','citation_id',cit))"
        ")",
        {"cid": case_id, "cit": citation_id},
    )


def _parse_dt(v):
    """Accept datetime, ISO string, or None — return datetime or None."""
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(v)


async def insert_analytics_row(conn, case: dict) -> None:
    # analytics_cases has no UNIQUE constraint on case_id, so ON CONFLICT doesn't
    # fire. Guard against duplicate seeds manually.
    await conn.execute(
        """
        INSERT INTO analytics_cases (
            case_id, department_id, tthc_code, status,
            submitted_at, completed_at, processing_days, sla_days, is_overdue
        )
        SELECT $1::varchar, $2::varchar, $3::varchar, $4::varchar,
               $5::timestamptz, $6::timestamptz,
               $7::integer, $8::integer, $9::boolean
        WHERE NOT EXISTS (
            SELECT 1 FROM analytics_cases WHERE case_id = $1::varchar
        )
        """,
        case["case_id"], case["department_id"], case["tthc_code"],
        case["status"],
        _parse_dt(case["submitted_at"]),
        _parse_dt(case.get("completed_at")),
        case.get("processing_days"),
        case.get("sla_days", 15),
        case.get("is_overdue", False),
    )


async def seed_primary_cases(conn) -> None:
    for c in PRIMARY_CASES:
        upsert_case_vertex(c)
        upsert_applicant_and_edge(c["case_id"], c["applicant"])
        for doc_id, dtype, fn in c.get("documents", []):
            upsert_document_and_edge(c["case_id"], doc_id, dtype, fn)
        for gap in c.get("gaps", []):
            upsert_gap_and_edge(c["case_id"], *gap)
        for cit in c.get("citations", []):
            upsert_citation_and_edge(c["case_id"], *cit)
        await insert_analytics_row(conn, c)
        log.info(f"[case] {c['case_id']} ({c['tthc_code']}) — "
                 f"{len(c.get('documents', []))} docs, "
                 f"{len(c.get('gaps', []))} gaps, "
                 f"{len(c.get('citations', []))} cites")
    log.info(f"[primary] {len(PRIMARY_CASES)} cases seeded")


async def seed_analytics_only(conn) -> None:
    for c in COMPLETED_CASES:
        await insert_analytics_row(conn, c)
    for c in BENCHMARK_CASES:
        await insert_analytics_row(conn, c)
    log.info(f"[analytics] {len(COMPLETED_CASES)} completed + "
             f"{len(BENCHMARK_CASES)} benchmark rows")


# ============================================================
# Hero case agent trace (10-step pipeline with realistic thinking)
# ============================================================
HERO_STEPS = [
    {
        "step_id": "STEP-HERO-01",
        "agent_name": "intake_agent",
        "action": "Tiếp nhận hồ sơ và kiểm tra tài liệu đầu vào",
        "status": "completed",
        "input_tokens": 420, "output_tokens": 180, "duration_ms": 1250,
        "output_summary": "Nhận 4 tài liệu: đơn CPXD, bản vẽ, GCN QSDĐ, hợp đồng XD. Đã tạo Bundle-001.",
        "reasoning_excerpt": (
            "Bắt đầu xử lý hồ sơ CPXD của ông Nguyễn Văn Bình. Tôi kiểm tra "
            "danh mục tài liệu đính kèm: (1) Đơn đề nghị cấp phép, (2) Bản vẽ "
            "thiết kế, (3) Giấy chứng nhận QSDĐ, (4) Hợp đồng xây dựng. Tất cả "
            "4 file đều ở trạng thái đã tải lên OSS. Tiếp theo gọi "
            "`doc_analyze_agent` để OCR và trích xuất entity."
        ),
    },
    {
        "step_id": "STEP-HERO-02",
        "agent_name": "doc_analyze_agent",
        "action": "OCR Qwen3-VL và trích xuất entity từ 4 tài liệu",
        "status": "completed",
        "input_tokens": 2340, "output_tokens": 890, "duration_ms": 8420,
        "output_summary": "Trích được 23 entity. CCCD: 001085012345. Thửa 285, tờ 12, 82m². Công trình 3 tầng.",
        "reasoning_excerpt": (
            "Gọi Qwen3-VL-Plus trên từng file. `don_cpxd.pdf`: OCR trả "
            "họ tên='Nguyễn Văn Bình', CCCD='001085012345', địa chỉ='Số 18 "
            "Nguyễn Trãi, Thanh Xuân, Hà Nội'. `banve.pdf`: trích được "
            "diện tích xây dựng 82m², chiều cao 10.8m, kết cấu BTCT. "
            "`qsdd.pdf`: thửa 285, tờ bản đồ 12, diện tích 82m², mục đích "
            "'đất ở đô thị'. `hopdong.pdf`: nhà thầu 'Cty TNHH XD Minh Anh'. "
            "Độ tin cậy OCR trung bình 0.94 — đạt ngưỡng tự động."
        ),
    },
    {
        "step_id": "STEP-HERO-03",
        "agent_name": "classifier_agent",
        "action": "Phân loại TTHC từ nội dung tài liệu",
        "status": "completed",
        "input_tokens": 780, "output_tokens": 120, "duration_ms": 1540,
        "output_summary": "Match TTHC 1.004415 'Cấp phép xây dựng' với confidence 0.97. Đã ghi MATCHES_TTHC edge.",
        "reasoning_excerpt": (
            "Dựa trên các entity trích xuất (diện tích 82m², công trình 3 tầng, "
            "có bản vẽ thiết kế, có GCN QSDĐ), tôi match hồ sơ này với TTHC "
            "1.004415 'Cấp giấy phép xây dựng'. Confidence 0.97 > 0.85 nên "
            "không escalate cho cán bộ. Ghi cạnh MATCHES_TTHC trên GDB."
        ),
    },
    {
        "step_id": "STEP-HERO-04",
        "agent_name": "legal_search_agent",
        "action": "Tìm căn cứ pháp lý qua Qwen3-Embedding + GDB",
        "status": "completed",
        "input_tokens": 1120, "output_tokens": 340, "duration_ms": 3210,
        "output_summary": "Vector search (pgvector) top-10 + GDB expansion. Tìm được 2 điều luật áp dụng.",
        "reasoning_excerpt": (
            "Gọi Qwen3-Embedding v3 (dim=1024) trên query 'cấp phép xây dựng "
            "nhà ở 3 tầng yêu cầu PCCC'. Top-10 chunk từ Hologres pgvector: "
            "similarity cao nhất 0.82 → NĐ 136/2020/NĐ-CP Điều 9 khoản 2 "
            "(quy định thẩm duyệt PCCC). Tiếp theo traverse GDB từ "
            "`Article[136/2020:Dieu 9]` qua `SUPERSEDED_BY` để check hiệu "
            "lực — vẫn còn hiệu lực. Thêm căn cứ Luật Xây dựng 2014 Điều 89."
        ),
    },
    {
        "step_id": "STEP-HERO-05",
        "agent_name": "compliance_agent",
        "action": "Đối chiếu yêu cầu TTHC với tài liệu đã nộp",
        "status": "completed",
        "input_tokens": 1560, "output_tokens": 520, "duration_ms": 4180,
        "output_summary": "Phát hiện 1 gap CRITICAL: thiếu văn bản thẩm duyệt PCCC (ND 136/2020 Điều 9.2).",
        "reasoning_excerpt": (
            "TTHCSpec 1.004415 yêu cầu 7 thành phần: (1) Đơn đề nghị ✓, "
            "(2) Bản vẽ thiết kế ✓, (3) GCN QSDĐ ✓, (4) Hợp đồng XD ✓, "
            "(5) Báo cáo thẩm định thiết kế ✗, (6) Văn bản thẩm duyệt PCCC ✗, "
            "(7) Bản kê năng lực đơn vị thiết kế ✗. Trong đó PCCC là bắt buộc "
            "theo NĐ 136/2020 Điều 9.2 với công trình ≥ 3 tầng. Severity: "
            "HIGH — không thể cấp phép mà không có văn bản PCCC. Ghi Gap vertex "
            "và edge HAS_GAP + CITES lên Citation NĐ 136/2020."
        ),
    },
    {
        "step_id": "STEP-HERO-06",
        "agent_name": "router_agent",
        "action": "Định tuyến tới phòng chức năng + tạo consult tickets",
        "status": "completed",
        "input_tokens": 620, "output_tokens": 140, "duration_ms": 1120,
        "output_summary": "Route → Phòng Quản lý ĐT UBND Thanh Xuân. Tham vấn: Công an PCCC khu vực.",
        "reasoning_excerpt": (
            "Địa điểm xây dựng tại quận Thanh Xuân → thẩm quyền UBND "
            "quận Thanh Xuân, phòng Quản lý đô thị. Có gap PCCC → tạo ticket "
            "tham vấn Công an PCCC khu vực Thanh Xuân. Ghi cạnh ASSIGNED_TO "
            "+ CONSULTED trên GDB."
        ),
    },
    {
        "step_id": "STEP-HERO-07",
        "agent_name": "consult_agent",
        "action": "Tổng hợp ý kiến tham vấn đa cơ quan",
        "status": "completed",
        "input_tokens": 840, "output_tokens": 230, "duration_ms": 2560,
        "output_summary": "1/1 ticket chờ trả lời (PCCC). Mô phỏng: hồ sơ cần bổ sung trước khi thẩm định.",
        "reasoning_excerpt": (
            "Đọc các ý kiến của Consult ticket. Hiện chưa có phản hồi thực từ "
            "PCCC (24h). Giả định theo chính sách: với công trình dân dụng "
            "3 tầng ở quận nội thành, yêu cầu văn bản thẩm duyệt là "
            "bắt buộc. Đề xuất chuyển trạng thái sang `pending_supplement` "
            "và thông báo công dân."
        ),
    },
    {
        "step_id": "STEP-HERO-08",
        "agent_name": "summary_agent",
        "action": "Tóm tắt hồ sơ cho Lãnh đạo (role-aware)",
        "status": "completed",
        "input_tokens": 1980, "output_tokens": 410, "duration_ms": 2120,
        "output_summary": "Bản tóm tắt 3 dòng + compliance score 72% + khuyến nghị bổ sung PCCC.",
        "reasoning_excerpt": (
            "Sinh tóm tắt 3 tầng theo role: "
            "(1) Cán bộ: 'Hồ sơ CPXD thiếu 1 tài liệu bắt buộc (PCCC), "
            "cần yêu cầu bổ sung trước khi trình ký.' "
            "(2) Lãnh đạo: 'Hồ sơ hợp lệ về thủ tục nhưng chưa đủ căn cứ "
            "pháp lý PCCC; đề nghị yêu cầu công dân bổ sung.' "
            "(3) Công dân: 'Hồ sơ của quý vị thiếu giấy chứng nhận PCCC — "
            "vui lòng bổ sung trong vòng 15 ngày.' "
            "Compliance score = 5/7 = 72%."
        ),
    },
    {
        "step_id": "STEP-HERO-09",
        "agent_name": "draft_agent",
        "action": "Sinh văn bản thông báo (NĐ 30/2020 thể thức)",
        "status": "completed",
        "input_tokens": 1320, "output_tokens": 680, "duration_ms": 3340,
        "output_summary": "Công văn 433/2026/QĐ-QLDT đúng thể thức NĐ 30/2020. PDF sẵn sàng ký số.",
        "reasoning_excerpt": (
            "Sinh Quyết định theo mẫu NĐ 30/2020 Điều 8: Quốc hiệu, tiêu "
            "ngữ, tên CQ ban hành, số/ký hiệu '433/2026/QĐ-QLDT', địa danh "
            "+ ngày, tên loại văn bản 'Quyết định', căn cứ pháp lý (3 căn "
            "cứ: Luật TCCQĐP, NĐ 30/2020, đề nghị), 3 điều khoản (chấp "
            "thuận, hiệu lực, trách nhiệm), nơi nhận, chữ ký số. "
            "Font Times New Roman 13, lề trái 3cm, phải 2cm. Đạt 10/10 "
            "quy tắc thể thức."
        ),
    },
    {
        "step_id": "STEP-HERO-10",
        "agent_name": "security_officer_agent",
        "action": "Phân loại bảo mật và kiểm tra permission",
        "status": "completed",
        "input_tokens": 540, "output_tokens": 90, "duration_ms": 840,
        "output_summary": "Classification = UNCLASSIFIED. Không có thông tin nhạy cảm. Cho phép public view.",
        "reasoning_excerpt": (
            "Quét metadata hồ sơ: không chứa CCCD đầy đủ trong payload "
            "public (đã mask 9 chữ số giữa), không có thông tin quân sự/"
            "tình báo/đối ngoại. Phân loại Unclassified. Property mask "
            "cấu hình: `national_id`/`phone` chỉ visible với clearance ≥ 1. "
            "Công dân tra cứu /public/cases/{code} được phép."
        ),
    },
]


def upsert_agent_step(case_id: str, step: dict) -> None:
    """Create AgentStep vertex + PROCESSED_BY edge from Case."""
    gremlin_submit(
        "g.V().has('AgentStep','step_id',sid).fold()"
        ".coalesce(unfold(),"
        " addV('AgentStep').property('step_id',sid)"
        ".property('agent_name',aname).property('action',act)"
        ".property('status',st).property('input_tokens',itok)"
        ".property('output_tokens',otok).property('duration_ms',dur)"
        ".property('output_summary',osum)"
        ".property('reasoning_excerpt',rthink)"
        ".property('created_at',now))",
        {
            "sid": step["step_id"], "aname": step["agent_name"],
            "act": step["action"], "st": step["status"],
            "itok": step["input_tokens"], "otok": step["output_tokens"],
            "dur": step["duration_ms"],
            "osum": step["output_summary"],
            "rthink": step["reasoning_excerpt"],
            "now": _iso(NOW),
        },
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('PROCESSED_BY').where(__.inV().has('AgentStep','step_id',sid)),"
        " __.addE('PROCESSED_BY').to(__.V().has('AgentStep','step_id',sid))"
        ")",
        {"cid": case_id, "sid": step["step_id"]},
    )


async def seed_audit_events(conn) -> None:
    """Seed a realistic audit trail for the Security Console demo."""
    events = [
        ("case.created", "staff_intake", "Case", "CASE-2026-0001",
         "CASE-2026-0001", "DEPT-QLDT", {"tthc_code": "1.004415"}),
        ("document.uploaded", "staff_intake", "Document", "DOC-001",
         "CASE-2026-0001", "DEPT-QLDT", {"filename": "don_cpxd.pdf"}),
        ("agent.completed", "doc_analyze_agent", "AgentStep", "STEP-HERO-02",
         "CASE-2026-0001", "DEPT-QLDT", {"duration_ms": 8420, "tokens": 3230}),
        ("permission.denied", "summary_agent", "Property", "national_id",
         "CASE-2026-0001", "DEPT-QLDT",
         {"tier": "SDK_GUARD", "reason": "Field không nằm trong allowlist"}),
        ("permission.denied", "legal_search_agent", "Vertex", "Gap",
         "CASE-2026-0001", "DEPT-QLDT",
         {"tier": "GDB_RBAC", "reason": "INSERT không được phép trên Gap"}),
        ("agent.completed", "compliance_agent", "AgentStep", "STEP-HERO-05",
         "CASE-2026-0001", "DEPT-QLDT", {"duration_ms": 4180, "gaps": 1}),
        ("clearance.elevated", "security_officer", "User", "ld_phong",
         None, "DEPT-ADMIN",
         {"from": "UNCLASSIFIED", "to": "CONFIDENTIAL", "fields": ["home_address"]}),
        ("case.approved", "ld_phong", "Case", "CASE-2026-0003",
         "CASE-2026-0003", "DEPT-QLDT", {"decision": "approve"}),
        ("case.rejected", "ld_phong", "Case", "CASE-2026-0107",
         "CASE-2026-0107", "DEPT-QLDT", {"decision": "reject", "reason": "Thiếu giấy tờ"}),
    ]
    import uuid as _uuid
    import json as _json
    for i, (evt_type, actor_name, tgt_type, tgt_id, cid, dept, details) in enumerate(events):
        await conn.execute(
            """
            INSERT INTO audit_events_flat (
                id, event_type, actor_name, target_type, target_id,
                case_id, department_id, details, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb,
                    NOW() - ($9 * INTERVAL '1 minute'))
            ON CONFLICT DO NOTHING
            """,
            _uuid.uuid4(), evt_type, actor_name, tgt_type, tgt_id,
            cid, dept, _json.dumps(details), (len(events) - i) * 3,
        )
    log.info(f"[audit] {len(events)} audit events seeded")


async def seed_hero_agent_trace(conn) -> None:
    """Wire a full 10-step AgentStep pipeline onto the hero case."""
    hero_case_id = "CASE-2026-0001"
    for step in HERO_STEPS:
        upsert_agent_step(hero_case_id, step)
        # Also mirror into analytics_agents so dashboard KPIs pick it up
        try:
            await conn.execute(
                """
                INSERT INTO analytics_agents (
                    case_id, agent_name, duration_ms,
                    input_tokens, output_tokens, tool_calls, status
                )
                SELECT $1::varchar, $2::varchar, $3::integer,
                       $4::integer, $5::integer, $6::integer, $7::varchar
                WHERE NOT EXISTS (
                    SELECT 1 FROM analytics_agents
                    WHERE case_id = $1::varchar AND agent_name = $2::varchar
                )
                """,
                hero_case_id, step["agent_name"], step["duration_ms"],
                step["input_tokens"], step["output_tokens"],
                1 if step["agent_name"] in ("doc_analyze_agent", "legal_search_agent", "compliance_agent") else 0,
                step["status"],
            )
        except Exception as exc:
            log.debug(f"analytics_agents insert skipped: {exc}")
    log.info(f"[hero-trace] {len(HERO_STEPS)} AgentStep vertices wired on {hero_case_id}")


async def main() -> None:
    create_gremlin_client()
    await create_pg_pool()
    try:
        pool = get_pg_pool()
        async with pool.acquire() as conn:
            await seed_users(conn)
            await seed_primary_cases(conn)
            await seed_analytics_only(conn)
            await seed_hero_agent_trace(conn)
            await seed_audit_events(conn)

        # Summary
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT count(*) FROM analytics_cases")
            log.info(f"[summary] analytics_cases total rows: {total}")
        vcount = gremlin_submit("g.V().count()")
        ecount = gremlin_submit("g.E().count()")
        log.info(f"[summary] GDB vertices={vcount[0] if vcount else 0}, "
                 f"edges={ecount[0] if ecount else 0}")
        log.info("[done] demo seed complete")
    finally:
        await close_pg_pool()
        close_gremlin_client()


if __name__ == "__main__":
    asyncio.run(main())
