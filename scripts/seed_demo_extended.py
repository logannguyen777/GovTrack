"""
scripts/seed_demo_extended.py
=============================================================================
Extended demo seed: 60 cases, 150 documents, 30 gaps, 20 citations,
10 consult requests, 40 dispatch logs, 200+ audit events, 60 agent steps,
10 notifications, 20 users.

Idempotent — safe to re-run.

Usage (from GovTrack/ root):
    cd /home/logan/GovTrack/backend
    ../backend/.venv/bin/python ../scripts/seed_demo_extended.py
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Bootstrap path ──────────────────────────────────────────────────────────
sys.path.insert(0, "/home/logan/GovTrack/backend")

from src.database import (  # noqa: E402
    close_gremlin_client,
    close_pg_pool,
    create_gremlin_client,
    create_oss_client,
    create_pg_pool,
    get_pg_pool,
    gremlin_submit,
    oss_get_signed_url,
    oss_put_object,
)
from src.config import settings  # noqa: E402

try:
    from argon2 import PasswordHasher as _PH
    PW_HASH = _PH().hash("demo")
except ImportError:
    import hashlib
    PW_HASH = hashlib.sha256(b"demo").hexdigest()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("seed_extended")

NOW = datetime.now(timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _days_ago(n: float) -> datetime:
    return NOW - timedelta(days=n)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DEPTS = ["DEPT-QLDT", "DEPT-TNMT", "DEPT-PHAPCHE", "DEPT-TEST", "DEPT-ADMIN"]
TTHC_CODES = ["1.004415", "1.000046", "1.001757", "1.000122", "2.002154"]

ALL_STATUSES = [
    "submitted", "classifying", "extracting",
    "gap_checking", "pending_supplement",
    "legal_review", "drafting",
    "leader_review", "consultation",
    "approved", "published",
    "rejected", "failed",
]

CLEARANCE_MAP = {
    0: "Unclassified",
    1: "Confidential",
    2: "Secret",
    3: "Top Secret",
}

# ─────────────────────────────────────────────────────────────────────────────
# 20 users (keep 7 existing, add 13 more)
# ─────────────────────────────────────────────────────────────────────────────

EXTRA_USERS: list[tuple] = [
    # (username, full_name, email, role, clearance_level, departments)
    ("nguyen_van_a",   "Nguyễn Văn A",       "nva@govflow.vn",   "staff_intake",    0, ["DEPT-QLDT"]),
    ("tran_thi_b",     "Trần Thị B",          "ttb@govflow.vn",   "staff_processor", 1, ["DEPT-TNMT"]),
    ("le_van_c",       "Lê Văn C",            "lvc@govflow.vn",   "staff_processor", 1, ["DEPT-PHAPCHE"]),
    ("pham_minh_d",    "Phạm Minh D",         "pmd@govflow.vn",   "leader",          2, ["DEPT-TEST"]),
    ("hoang_thi_e",    "Hoàng Thị E",         "hte@govflow.vn",   "legal",           2, ["DEPT-PHAPCHE"]),
    ("vu_quoc_f",      "Vũ Quốc F",           "vqf@govflow.vn",   "staff_intake",    0, ["DEPT-ADMIN"]),
    ("dinh_van_g",     "Đinh Văn G",          "dvg@govflow.vn",   "staff_processor", 1, ["DEPT-QLDT", "DEPT-TEST"]),
    ("bui_thi_h",      "Bùi Thị H",           "bth@govflow.vn",   "leader",          2, ["DEPT-TNMT"]),
    ("ngo_van_i",      "Ngô Văn I",           "nvi@govflow.vn",   "legal",           2, ["DEPT-PHAPCHE"]),
    ("ly_thi_j",       "Lý Thị J",            "ltj@govflow.vn",   "staff_intake",    0, ["DEPT-TEST"]),
    ("cao_van_k",      "Cao Văn K",           "cvk@govflow.vn",   "staff_processor", 1, ["DEPT-ADMIN"]),
    ("do_thi_l",       "Đỗ Thị L",            "dtl@govflow.vn",   "security",        3, ["DEPT-ADMIN"]),
    ("mai_van_m",      "Mai Văn M",           "mvm@govflow.vn",   "staff_processor", 1, ["DEPT-QLDT"]),
]

# ─────────────────────────────────────────────────────────────────────────────
# Helper: make a tiny placeholder PDF/JPG/PNG for MinIO
# ─────────────────────────────────────────────────────────────────────────────

_TINY_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f\n"
    b"0000000009 00000 n\n0000000058 00000 n\n"
    b"0000000115 00000 n\n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
)

_TINY_JPG = bytes([
    0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
    0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,
    0xFF,0xDB,0x00,0x43,0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,
    0x07,0x07,0x09,0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,
    0x19,0x12,0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,
    0x20,0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
    0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,0x3C,
    0x2E,0x33,0x34,0x32,
    0xFF,0xD9,
])

_TINY_PNG = bytes([
    0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,  # PNG signature
    0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,  # IHDR chunk length + type
    0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,  # 1x1 pixels
    0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,  # 8-bit RGB, CRC
    0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,  # IDAT chunk
    0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
    0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,
    0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,  # IEND
    0x44,0xAE,0x42,0x60,0x82,
])


def _doc_payload(content_type: str) -> tuple[bytes, str]:
    """Return (bytes, mime_type) for placeholder object."""
    if "pdf" in content_type or content_type.endswith(".pdf"):
        return _TINY_PDF, "application/pdf"
    if "jpg" in content_type or "jpeg" in content_type:
        return _TINY_JPG, "image/jpeg"
    if "png" in content_type:
        return _TINY_PNG, "image/png"
    return _TINY_PDF, "application/pdf"


# ─────────────────────────────────────────────────────────────────────────────
# Document library — 150 docs across 60 cases
# ─────────────────────────────────────────────────────────────────────────────

# Vietnamese filename templates by doc type
_DOC_NAMES = {
    "don_de_nghi":      ("Don-de-nghi-{}.pdf",         "application/pdf"),
    "ban_ve_thiet_ke":  ("Ban-ve-thiet-ke-{}.pdf",      "application/pdf"),
    "gcn_qsdd":         ("GCN-quyen-su-dung-dat-{}.pdf","application/pdf"),
    "cccd_mat_truoc":   ("CCCD-mat-truoc-{}.jpg",       "image/jpeg"),
    "cccd_mat_sau":     ("CCCD-mat-sau-{}.jpg",         "image/jpeg"),
    "so_do_mat_bang":   ("So-do-mat-bang-{}.pdf",       "application/pdf"),
    "bao_cao_dtm":      ("Bao-cao-danh-gia-tac-dong-moi-truong-{}.pdf", "application/pdf"),
    "hop_dong_xd":      ("Hop-dong-xay-dung-{}.pdf",    "application/pdf"),
    "giay_phep_kd":     ("Giay-phep-kinh-doanh-{}.pdf", "application/pdf"),
    "dieu_le_cty":      ("Dieu-le-cong-ty-{}.pdf",      "application/pdf"),
    "ly_lich_tu_phap":  ("Ly-lich-tu-phap-{}.pdf",      "application/pdf"),
    "anh_chan_dung":    ("Anh-chan-dung-{}.jpg",         "image/jpeg"),
    "phieu_thu":        ("Phieu-thu-le-phi-{}.pdf",     "application/pdf"),
    "bao_cao_kt":       ("Bao-cao-ket-qua-kiem-tra-{}.pdf","application/pdf"),
    "to_khai_hai_quan": ("To-khai-hai-quan-{}.pdf",     "application/pdf"),
    "bien_ban_hop":     ("Bien-ban-hop-dong-y-{}.pdf",  "application/pdf"),
    "qd_phe_duyet":     ("Quyet-dinh-phe-duyet-{}.pdf", "application/pdf"),
    "bang_chuyen_nhuong":("Bang-chuyen-nhuong-tai-san-{}.pdf","application/pdf"),
    "phieu_xin_nghi":   ("Phieu-xin-nghi-phep-{}.pdf",  "application/pdf"),
    "so_ho_khau":       ("So-ho-khau-{}.png",            "image/png"),
}

_DOC_TYPE_LIST = list(_DOC_NAMES.keys())

# ─────────────────────────────────────────────────────────────────────────────
# Build case + doc data
# ─────────────────────────────────────────────────────────────────────────────

def _build_cases_and_docs() -> tuple[list[dict], list[dict]]:
    """Return (cases, docs) lists.

    Cases 1-5: hero cases (kept from original seed, just enriched with docs).
    Cases 6-60: generated.
    Docs 1-150: 3-5 per case.
    """
    cases: list[dict] = []
    docs: list[dict] = []
    doc_counter = 0

    # ── Hero cases 1-5 (from original seed, add oss_key to existing docs) ──
    hero_doc_mapping = {
        "CASE-2026-0001": [
            ("DOC-001", "don_de_nghi",    "Don-de-nghi-cap-GPXD-001.pdf",   "application/pdf"),
            ("DOC-002", "ban_ve_thiet_ke","Ban-ve-thiet-ke-001.pdf",          "application/pdf"),
            ("DOC-003", "gcn_qsdd",       "GCN-quyen-su-dung-dat-001.pdf",    "application/pdf"),
            ("DOC-004", "hop_dong_xd",    "Hop-dong-xay-dung-001.pdf",        "application/pdf"),
        ],
        "CASE-2026-0002": [
            ("DOC-010", "don_de_nghi",    "Don-dang-ky-GCN-010.pdf",          "application/pdf"),
            ("DOC-011", "so_do_mat_bang", "Ho-so-dia-chinh-011.pdf",           "application/pdf"),
            ("DOC-012", "gcn_qsdd",       "Ban-do-dia-chinh-012.pdf",          "application/pdf"),
        ],
        "CASE-2026-0003": [
            ("DOC-020", "don_de_nghi",    "Don-dang-ky-KD-020.pdf",            "application/pdf"),
            ("DOC-021", "dieu_le_cty",    "Dieu-le-cong-ty-021.pdf",           "application/pdf"),
        ],
        "CASE-2026-0004": [
            ("DOC-030", "don_de_nghi",    "Don-yeu-cau-LLTP-030.pdf",          "application/pdf"),
            ("DOC-031", "cccd_mat_truoc", "CCCD-mat-truoc-031.jpg",            "image/jpeg"),
        ],
        "CASE-2026-0005": [
            ("DOC-040", "bao_cao_dtm",    "Bao-cao-DTM-040.pdf",               "application/pdf"),
            ("DOC-041", "giay_phep_kd",   "Giay-phep-KD-041.pdf",              "application/pdf"),
        ],
    }

    # Collect hero docs (will update existing vertices in GDB)
    for case_id, hero_docs in hero_doc_mapping.items():
        for doc_id, dtype, filename, ct in hero_docs:
            docs.append({
                "doc_id": doc_id,
                "case_id": case_id,
                "doc_type": dtype,
                "filename": filename,
                "content_type": ct,
                "oss_key": f"documents/{case_id}/{doc_id}/{filename}",
                "ocr_status": "completed",
                "page_count": 2,
                "classification_level": 0,
                "is_hero": True,
            })

    doc_counter = 41  # start new sequential docs at DOC-042 (hero docs go up to DOC-041)

    # ── Status distribution ──
    status_buckets = {
        "submitted":         5,
        "classifying":       2,
        "extracting":        3,
        "gap_checking":      3,
        "pending_supplement":2,
        "legal_review":      3,
        "drafting":          3,
        "leader_review":     3,
        "consultation":      3,
        "approved":          3,
        "published":         5,  # historical
        "rejected":          3,  # historical
        "failed":            2,  # historical
    }
    # internal_dispatch (15 cases)

    case_counter = 6
    dept_cycle = DEPTS * 20
    tthc_cycle = TTHC_CODES * 20

    # Clearance distribution: 30 UNCLASSIFIED, 20 CONFIDENTIAL, 8 SECRET, 2 TOP_SECRET
    clearance_seq = [0]*30 + [1]*20 + [2]*8 + [3]*2

    case_list_generated: list[dict] = []

    # ── Regular cases by status ──
    for status, count in status_buckets.items():
        for _ in range(count):
            idx = case_counter - 1
            days_since = idx % 30 + 1
            dept = dept_cycle[idx % len(dept_cycle)]
            tthc = tthc_cycle[idx % len(tthc_cycle)]
            clearance = clearance_seq[idx % len(clearance_seq)]
            sla = [15, 20, 10, 15, 30][idx % 5]
            submitted = _days_ago(days_since)
            is_overdue = (days_since > sla)
            processing_days = days_since if status in ("published", "approved", "rejected", "failed") else None
            completed_at = (_days_ago(days_since - sla) if processing_days else None)

            case_list_generated.append({
                "case_id": f"CASE-2026-{case_counter:04d}",
                "code": f"HS-2026{case_counter:04d}-EXT{case_counter:04d}",
                "tthc_code": tthc,
                "department_id": dept,
                "status": status,
                "case_type": "citizen_tthc",
                "classification": clearance,
                "submitted_at": _iso(submitted),
                "completed_at": _iso(completed_at) if completed_at else None,
                "sla_days": sla,
                "processing_days": processing_days,
                "is_overdue": is_overdue,
                "applicant": {
                    "name": f"Công Dân Demo {case_counter:04d}",
                    "id_number": f"0{case_counter:011d}",
                    "phone": f"09{case_counter % 100000000:08d}",
                    "address": f"Số {case_counter}, Đường Demo, TP Bình Định",
                },
            })
            case_counter += 1

    # ── Internal dispatch cases (15) ──
    for i in range(15):
        idx = case_counter - 1
        days_since = (i + 1) * 2
        dept_from = DEPTS[i % len(DEPTS)]
        dept_to = DEPTS[(i + 1) % len(DEPTS)]
        submitted = _days_ago(days_since)
        case_list_generated.append({
            "case_id": f"CASE-2026-{case_counter:04d}",
            "code": f"HS-2026{case_counter:04d}-INT{i:04d}",
            "tthc_code": TTHC_CODES[i % len(TTHC_CODES)],
            "department_id": dept_from,
            "status": "legal_review" if i % 3 == 0 else "drafting",
            "case_type": "internal_dispatch",
            "classification": clearance_seq[i % len(clearance_seq)],
            "submitted_at": _iso(submitted),
            "completed_at": None,
            "sla_days": 20,
            "processing_days": None,
            "is_overdue": (days_since > 20),
            "applicant": {
                "name": f"Phòng Ban Nội Bộ {i+1:03d}",
                "id_number": f"1{i:011d}",
                "phone": f"028{i:08d}",
                "address": f"Trụ sở UBND, Số {i+1}",
            },
            "_dispatch_to": dept_to,
        })
        case_counter += 1

    cases.extend(case_list_generated)

    # ── Generate docs for generated cases ──
    doc_types_cycle = _DOC_TYPE_LIST

    for c in case_list_generated:
        cid = c["case_id"]
        num_docs = (int(cid[-4:]) % 3) + 3  # 3-5 docs per case
        for d_idx in range(num_docs):
            doc_counter += 1
            dtype = doc_types_cycle[doc_counter % len(doc_types_cycle)]
            fname_template, ct = _DOC_NAMES[dtype]
            fname = fname_template.format(f"{doc_counter:03d}")
            did = f"DOC-{doc_counter:03d}"

            docs.append({
                "doc_id": did,
                "case_id": cid,
                "doc_type": dtype,
                "filename": fname,
                "content_type": ct,
                "oss_key": f"documents/{cid}/{did}/{fname}",
                "ocr_status": "completed" if d_idx == 0 else "pending",
                "page_count": (d_idx + 1),
                "classification_level": c["classification"],
                "is_hero": False,
            })

    return cases, docs


# ─────────────────────────────────────────────────────────────────────────────
# Gap / Citation / Consult / Dispatch data
# ─────────────────────────────────────────────────────────────────────────────

_GAP_TEMPLATES = [
    ("Thiếu giấy chứng nhận PCCC", "high",   "NĐ 136/2020/NĐ-CP Điều 9 khoản 2",
     "Bổ sung văn bản thẩm duyệt PCCC từ cơ quan PCCC địa phương"),
    ("Thiếu bản sao công chứng CCCD", "medium", "Thông tư 25/2021/TT-BCA Điều 5",
     "Nộp bản sao có công chứng CCCD còn hiệu lực"),
    ("Giấy tờ đất đai hết hiệu lực", "high",   "Luật Đất đai 2013 Điều 106",
     "Cập nhật GCN QSDĐ theo quy định hiện hành"),
    ("Bản vẽ thiết kế chưa đóng dấu thẩm duyệt", "medium", "NĐ 15/2021/NĐ-CP Điều 32",
     "Bổ sung bản vẽ có dấu thẩm duyệt của cơ quan có thẩm quyền"),
    ("Hồ sơ địa chính không khớp hiện trạng", "high", "Thông tư 25/2014/TT-BTNMT Điều 8",
     "Cập nhật hồ sơ địa chính theo hiện trạng thực tế"),
    ("Thiếu báo cáo đánh giá tác động môi trường", "medium", "Luật BVMT 2020 Điều 30",
     "Lập báo cáo ĐTM theo hướng dẫn của Bộ TN&MT"),
    ("Chứng chỉ hành nghề xây dựng hết hạn", "high", "Luật Xây dựng 2014 Điều 152",
     "Gia hạn hoặc cấp mới chứng chỉ hành nghề"),
    ("Sơ đồ mặt bằng thiếu tọa độ", "warning", "NĐ 43/2014/NĐ-CP Điều 20",
     "Bổ sung tọa độ địa lý vào sơ đồ mặt bằng"),
    ("Thiếu xác nhận của chính quyền địa phương", "medium", "NĐ 148/2020/NĐ-CP Điều 14",
     "Bổ sung xác nhận của UBND phường/xã nơi thực hiện dự án"),
    ("Hợp đồng xây dựng chưa công chứng", "warning", "Luật Kinh doanh BĐS 2014 Điều 17",
     "Công chứng hợp đồng xây dựng tại văn phòng công chứng"),
]

_CITATION_TEMPLATES = [
    ("Luật Xây dựng 2014",          "Điều 89",           0.91),
    ("NĐ 136/2020/NĐ-CP",           "Điều 9 khoản 2",    0.95),
    ("Luật Đất đai 2013",            "Điều 106",          0.88),
    ("NĐ 43/2014/NĐ-CP",             "Điều 20",           0.82),
    ("Thông tư 25/2014/TT-BTNMT",    "Điều 8",            0.79),
    ("Luật BVMT 2020",               "Điều 30",           0.84),
    ("NĐ 15/2021/NĐ-CP",             "Điều 32",           0.87),
    ("Luật Doanh nghiệp 2020",       "Điều 26",           0.93),
    ("Luật Kinh doanh BĐS 2014",     "Điều 17",           0.76),
    ("Thông tư 25/2021/TT-BCA",      "Điều 5",            0.81),
    ("NĐ 148/2020/NĐ-CP",            "Điều 14",           0.78),
    ("NĐ 30/2020/NĐ-CP",             "Điều 8",            0.90),
    ("Luật TCCQĐP 2015",             "Điều 22",           0.85),
    ("Luật Thủy lợi 2017",           "Điều 42",           0.72),
    ("Luật Hải quan 2014",           "Điều 18",           0.69),
    ("NĐ 08/2018/NĐ-CP",             "Điều 3",            0.74),
    ("NĐ 47/2014/NĐ-CP",             "Điều 12",           0.77),
    ("Thông tư 11/2022/TT-BXD",      "Điều 6",            0.83),
    ("NĐ 82/2017/NĐ-CP",             "Điều 9",            0.80),
    ("Luật Phòng cháy chữa cháy 2001","Điều 15",           0.94),
]


# ─────────────────────────────────────────────────────────────────────────────
# Audit event types
# ─────────────────────────────────────────────────────────────────────────────

_AUDIT_EVENT_TYPES = [
    "PROPERTY_MASK.APPLIED", "SDK_GUARD.ALLOW", "SDK_GUARD.DENY",
    "GDB_RBAC.ALLOW", "GDB_RBAC.DENY",
    "AUTH.LOGIN", "AUTH.LOGOUT",
    "CASE.CREATE", "CASE.DECISION", "CASE.STATUS_CHANGE",
    "DOC.UPLOAD", "DOC.VIEW",
    "AGENT.RUN", "AGENT.COMPLETED", "AGENT.FAILED",
    "CLEARANCE.ELEVATED", "CLEARANCE.REVOKED",
    "PERMISSION.DENIED", "PERMISSION.GRANTED",
    "SEARCH.LAW", "SEARCH.TTHC",
    "audit.created", "case.created", "case.approved", "case.rejected",
    "document.uploaded", "agent.completed", "permission.denied",
    "clearance.elevated", "data_subject.access",
]

_ACTORS = [
    "admin", "cv_qldt", "staff_intake", "security_officer",
    "ld_phong", "legal_expert", "nguyen_van_a", "tran_thi_b",
    "doc_analyze_agent", "compliance_agent", "legal_search_agent",
    "system",
]

# ─────────────────────────────────────────────────────────────────────────────
# GDB upsert helpers
# ─────────────────────────────────────────────────────────────────────────────

def _gdb_upsert_case(c: dict) -> None:
    gremlin_submit(
        "g.V().has('Case','case_id',cid).fold()"
        ".coalesce(unfold(),"
        " addV('Case').property('case_id',cid).property('code',code)"
        ".property('tthc_code',tthc).property('department_id',dept)"
        ".property('status',status).property('submitted_at',sub)"
        ".property('classification',classif)"
        ".property('case_type',ctype).property('sla_days',sla))",
        {
            "cid": c["case_id"], "code": c["code"], "tthc": c["tthc_code"],
            "dept": c["department_id"], "status": c["status"],
            "sub": c["submitted_at"], "classif": c.get("classification", 0),
            "ctype": c.get("case_type", "citizen_tthc"),
            "sla": c.get("sla_days", 15),
        },
    )


def _gdb_upsert_applicant(case_id: str, app: dict) -> None:
    aid = f"APP-{case_id}"
    gremlin_submit(
        "g.V().has('Applicant','applicant_id',aid).fold()"
        ".coalesce(unfold(),"
        " addV('Applicant').property('applicant_id',aid)"
        ".property('full_name',name).property('id_number',idn)"
        ".property('phone',phone).property('address',addr))",
        {"aid": aid, "name": app["name"], "idn": app["id_number"],
         "phone": app["phone"], "addr": app["address"]},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('SUBMITTED_BY').where(__.inV().has('Applicant','applicant_id',aid)),"
        " __.addE('SUBMITTED_BY').to(__.V().has('Applicant','applicant_id',aid))"
        ")",
        {"cid": case_id, "aid": aid},
    )


def _gdb_upsert_doc(d: dict) -> None:
    """Upsert Document vertex — works for both new and existing (hero) docs."""
    # Try doc_id first, then document_id
    # For hero docs (is_hero=True) the vertex already exists with document_id prop
    # We update ALL properties so signed-url works
    if d.get("is_hero"):
        # Hero docs: vertex exists with document_id=DOC-XXX
        # Add oss_key / content_type / doc_id / page_count if missing
        for prop_name in ("doc_id",):
            gremlin_submit(
                "g.V().has('Document','document_id',did)"
                ".property('doc_id',did)"
                ".property('oss_key',okey)"
                ".property('content_type',ct)"
                ".property('ocr_status',ostat)"
                ".property('page_count',pc)"
                ".property('classification_level',cl)",
                {
                    "did": d["doc_id"],
                    "okey": d["oss_key"],
                    "ct": d["content_type"],
                    "ostat": d["ocr_status"],
                    "pc": d["page_count"],
                    "cl": d["classification_level"],
                },
            )
    else:
        gremlin_submit(
            "g.V().has('Document','doc_id',did).fold()"
            ".coalesce(unfold(),"
            " addV('Document').property('doc_id',did)"
            ".property('document_id',did))"  # keep compat
            ".property('filename',fn)"
            ".property('content_type',ct)"
            ".property('doc_type',dtype)"
            ".property('oss_key',okey)"
            ".property('ocr_status',ostat)"
            ".property('page_count',pc)"
            ".property('classification_level',cl)",
            {
                "did": d["doc_id"],
                "fn": d["filename"],
                "ct": d["content_type"],
                "dtype": d["doc_type"],
                "okey": d["oss_key"],
                "ostat": d["ocr_status"],
                "pc": d["page_count"],
                "cl": d["classification_level"],
            },
        )
        # Edge: Case → Document
        gremlin_submit(
            "g.V().has('Case','case_id',cid)"
            ".coalesce("
            " __.outE('HAS_DOCUMENT').where(__.inV().has('Document','doc_id',did)),"
            " __.addE('HAS_DOCUMENT').to(__.V().has('Document','doc_id',did))"
            ")",
            {"cid": d["case_id"], "did": d["doc_id"]},
        )


def _gdb_upsert_gap(case_id: str, gap_id: str, desc: str, sev: str, ref: str, fix: str) -> None:
    gremlin_submit(
        "g.V().has('Gap','gap_id',gid).fold()"
        ".coalesce(unfold(),"
        " addV('Gap').property('gap_id',gid).property('description',d)"
        ".property('severity',s).property('requirement_ref',rr)"
        ".property('fix_suggestion',fx))",
        {"gid": gap_id, "d": desc, "s": sev, "rr": ref, "fx": fix},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('HAS_GAP').where(__.inV().has('Gap','gap_id',gid)),"
        " __.addE('HAS_GAP').to(__.V().has('Gap','gap_id',gid))"
        ")",
        {"cid": case_id, "gid": gap_id},
    )


def _gdb_upsert_citation(case_id: str, cit_id: str, law: str, article: str, rel: float) -> None:
    gremlin_submit(
        "g.V().has('Citation','citation_id',cit).fold()"
        ".coalesce(unfold(),"
        " addV('Citation').property('citation_id',cit)"
        ".property('law_name',l).property('article',a).property('relevance',r))",
        {"cit": cit_id, "l": law, "a": article, "r": rel},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('CITES').where(__.inV().has('Citation','citation_id',cit)),"
        " __.addE('CITES').to(__.V().has('Citation','citation_id',cit))"
        ")",
        {"cid": case_id, "cit": cit_id},
    )


def _gdb_upsert_consult(req_id: str, case_id: str, from_dept: str, to_dept: str,
                         question: str, status: str, created_at: str) -> None:
    gremlin_submit(
        "g.V().has('ConsultRequest','request_id',rid).fold()"
        ".coalesce(unfold(),"
        " addV('ConsultRequest').property('request_id',rid)"
        ".property('case_id',cid).property('from_dept',fdept)"
        ".property('to_dept',tdept).property('question',q)"
        ".property('status',st).property('created_at',cat))",
        {"rid": req_id, "cid": case_id, "fdept": from_dept, "tdept": to_dept,
         "q": question, "st": status, "cat": created_at},
    )
    gremlin_submit(
        "g.V().has('Case','case_id',cid)"
        ".coalesce("
        " __.outE('HAS_CONSULT').where(__.inV().has('ConsultRequest','request_id',rid)),"
        " __.addE('HAS_CONSULT').to(__.V().has('ConsultRequest','request_id',rid))"
        ")",
        {"cid": case_id, "rid": req_id},
    )


def _gdb_upsert_agent_step(case_id: str, step: dict) -> None:
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
            "rthink": step.get("reasoning_excerpt", ""),
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


# ─────────────────────────────────────────────────────────────────────────────
# PostgreSQL seeders
# ─────────────────────────────────────────────────────────────────────────────

async def seed_extra_users(conn) -> None:
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
    log.info(f"[users] +{created} new / {len(EXTRA_USERS)} attempted")


async def seed_analytics(conn, cases: list[dict]) -> None:
    inserted = 0
    for c in cases:
        try:
            result = await conn.execute(
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
                c["case_id"], c.get("department_id", "DEPT-ADMIN"),
                c.get("tthc_code", "1.004415"), c.get("status", "submitted"),
                _parse_dt(c.get("submitted_at")),
                _parse_dt(c.get("completed_at")),
                c.get("processing_days"),
                c.get("sla_days", 15),
                c.get("is_overdue", False),
            )
            if result.endswith(" 1"):
                inserted += 1
        except Exception as e:
            log.debug(f"analytics insert skip for {c['case_id']}: {e}")
    log.info(f"[analytics] +{inserted} new rows (attempted {len(cases)})")


async def seed_dispatch_logs(conn, cases: list[dict]) -> None:
    """40 dispatch log entries for internal_dispatch cases."""
    dispatch_cases = [c for c in cases if c.get("case_type") == "internal_dispatch"]
    inserted = 0
    for i, c in enumerate(dispatch_cases[:40]):
        cid = c["case_id"]
        to_dept = c.get("_dispatch_to", DEPTS[(i + 1) % len(DEPTS)])
        dispatched_at = _days_ago(i * 0.5 + 0.1)
        try:
            result = await conn.execute(
                """
                INSERT INTO dispatch_log (
                    id, case_id, from_dept_id, to_dept_id,
                    dispatch_type, reason, dispatched_by, dispatched_at, metadata
                )
                SELECT $1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb
                WHERE NOT EXISTS (
                    SELECT 1 FROM dispatch_log WHERE case_id=$2 AND from_dept_id=$3
                )
                """,
                uuid.uuid4(), cid, c["department_id"], to_dept,
                "consult" if i % 2 == 0 else "transfer",
                f"Chuyển hồ sơ {cid} để xử lý tiếp theo quy trình",
                _ACTORS[i % len(_ACTORS)],
                dispatched_at,
                json.dumps({"priority": "normal", "note": f"dispatch {i+1}"}),
            )
            if result.endswith(" 1"):
                inserted += 1
        except Exception as e:
            log.debug(f"dispatch insert skip: {e}")
    log.info(f"[dispatch] +{inserted} rows")


async def seed_consult_requests(conn, cases: list[dict]) -> None:
    """10 consult requests (5 pending, 5 completed)."""
    target_cases = cases[:10]
    inserted = 0
    for i, c in enumerate(target_cases):
        cid = c["case_id"]
        status = "pending" if i < 5 else "completed"
        dept_from = c.get("department_id", DEPTS[0])
        dept_to = DEPTS[(DEPTS.index(dept_from) + 1) % len(DEPTS)]
        req_id = f"CONSULT-EXT-{i+1:03d}"
        question = (
            f"Xin ý kiến về hồ sơ {cid}: "
            f"Trường hợp này có cần bổ sung tài liệu {'PCCC' if i%2==0 else 'môi trường'} không?"
        )
        _gdb_upsert_consult(
            req_id, cid, dept_from, dept_to, question, status,
            _iso(_days_ago(i + 1))
        )
        inserted += 1
    log.info(f"[consult] {inserted} consult requests in GDB")


async def seed_audit_events(conn, cases: list[dict]) -> None:
    """200+ audit events spanning 30 days."""
    admin_id_row = await conn.fetchrow("SELECT id FROM users WHERE username='admin'")
    admin_id = admin_id_row["id"] if admin_id_row else uuid.uuid4()

    events: list[dict] = []

    # Spread over 30 days, ~7 events per day
    for day_offset in range(30):
        base_dt = _days_ago(day_offset)
        for hour_offset in range(7):
            idx = day_offset * 7 + hour_offset
            evt_type = _AUDIT_EVENT_TYPES[idx % len(_AUDIT_EVENT_TYPES)]
            actor = _ACTORS[idx % len(_ACTORS)]
            case = cases[idx % len(cases)] if cases else {}
            cid = case.get("case_id")
            dept = case.get("department_id", "DEPT-ADMIN")
            target_type = ["Case", "Document", "AgentStep", "Property", "User"][idx % 5]
            target_id = cid or f"TGT-{idx}"

            events.append({
                "id": uuid.uuid4(),
                "event_type": evt_type,
                "actor_id": admin_id,
                "actor_name": actor,
                "target_type": target_type,
                "target_id": target_id,
                "case_id": cid,
                "department_id": dept,
                "details": json.dumps({
                    "action": evt_type,
                    "day": day_offset,
                    "hour": hour_offset,
                    "idx": idx,
                }),
                "ip_address": f"10.0.{day_offset % 256}.{hour_offset + 1}",
                "created_at": base_dt - timedelta(hours=hour_offset),
            })

    inserted = 0
    for evt in events:
        try:
            result = await conn.execute(
                """
                INSERT INTO audit_events_flat (
                    id, event_type, actor_id, actor_name, target_type, target_id,
                    case_id, department_id, details, ip_address, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10,$11)
                ON CONFLICT DO NOTHING
                """,
                evt["id"], evt["event_type"], evt["actor_id"], evt["actor_name"],
                evt["target_type"], evt["target_id"],
                evt["case_id"], evt["department_id"],
                evt["details"], evt["ip_address"], evt["created_at"],
            )
            if result.endswith(" 1"):
                inserted += 1
        except Exception as e:
            log.debug(f"audit insert skip: {e}")
    log.info(f"[audit] +{inserted} new rows (attempted {len(events)})")


async def seed_notifications(conn) -> None:
    """10 notifications for admin and staff users."""
    admin_row = await conn.fetchrow("SELECT id FROM users WHERE username='admin'")
    ld_row = await conn.fetchrow("SELECT id FROM users WHERE username='ld_phong'")
    staff_row = await conn.fetchrow("SELECT id FROM users WHERE username='staff_intake'")

    notifs = [
        (admin_row["id"] if admin_row else None, "Hồ sơ mới CASE-2026-0001",
         "Hồ sơ cấp phép xây dựng vừa được nộp, cần xử lý trong 15 ngày.",
         "action_required", "/cases/CASE-2026-0001"),
        (admin_row["id"] if admin_row else None, "Phát hiện gap PCCC nghiêm trọng",
         "Compliance Agent phát hiện thiếu văn bản thẩm duyệt PCCC tại CASE-2026-0001.",
         "alert", "/cases/CASE-2026-0001"),
        (ld_row["id"] if ld_row else None, "Hồ sơ chờ phê duyệt",
         "CASE-2026-0003 đang chờ quyết định phê duyệt từ lãnh đạo.",
         "action_required", "/cases/CASE-2026-0003"),
        (ld_row["id"] if ld_row else None, "Tóm tắt tuần",
         "Tuần này: 8 hồ sơ mới, 3 hoàn thành, 2 quá hạn.",
         "system", "/leadership/dashboard"),
        (staff_row["id"] if staff_row else None, "Yêu cầu tham vấn mới",
         "Phòng QLĐT yêu cầu ý kiến về hồ sơ môi trường CASE-2026-0005.",
         "action_required", "/agents/consult/inbox"),
        (admin_row["id"] if admin_row else None, "Cảnh báo bảo mật",
         "Phát hiện yêu cầu truy cập trái phép vào tài liệu MẬT.",
         "alert", "/audit/events"),
        (admin_row["id"] if admin_row else None, "Hệ thống hoạt động bình thường",
         "Tất cả các dịch vụ đang hoạt động. GDB: OK, PG: OK, OSS: OK.",
         "system", "/healthz"),
        (ld_row["id"] if ld_row else None, "Hồ sơ quá hạn SLA",
         "5 hồ sơ đã vượt quá thời hạn SLA. Cần xem xét khẩn.",
         "alert", "/leadership/inbox"),
        (staff_row["id"] if staff_row else None, "Tài liệu đã được OCR",
         "DOC-001 đã được phân tích bằng Qwen3-VL. Kết quả sẵn sàng.",
         "info", "/documents/DOC-001"),
        (admin_row["id"] if admin_row else None, "Báo cáo hàng tuần",
         "Báo cáo tuần 15/2026 đã được tổng hợp và sẵn sàng xem xét.",
         "info", "/leadership/weekly-brief"),
    ]

    # Clear old notifs from seed runs to keep idempotent
    await conn.execute("DELETE FROM notifications WHERE body LIKE '%(Seed)%'")

    inserted = 0
    for i, (user_id, title, body, category, link) in enumerate(notifs):
        if user_id is None:
            continue
        try:
            # Tag body so we can idempotently delete-and-reinsert
            tagged_body = body + " (Seed)"
            already = await conn.fetchval(
                "SELECT COUNT(*) FROM notifications WHERE user_id=$1 AND title=$2",
                user_id, title,
            )
            if already > 0:
                continue
            result = await conn.execute(
                """
                INSERT INTO notifications (id, user_id, title, body, category, link, is_read, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                uuid.uuid4(), user_id, title, tagged_body, category, link,
                (i % 3 == 0),  # some pre-read
                _days_ago(i * 0.5),
            )
            if result.endswith(" 1"):
                inserted += 1
        except Exception as e:
            log.debug(f"notification insert skip: {e}")
    log.info(f"[notifications] +{inserted} new rows")


async def seed_analytics_agents(conn, cases: list[dict]) -> None:
    """60 agent_steps in analytics_agents (10 hero + scattered for others)."""
    agent_names = [
        "intake_agent", "doc_analyze_agent", "classifier_agent",
        "legal_search_agent", "compliance_agent", "router_agent",
        "consult_agent", "summary_agent", "draft_agent", "security_officer_agent",
    ]
    inserted = 0
    # Sample from first 6 generated cases: 10 steps each = 60 rows
    for case_idx, c in enumerate(cases[:6]):
        cid = c["case_id"]
        for step_idx, agent in enumerate(agent_names):
            try:
                result = await conn.execute(
                    """
                    INSERT INTO analytics_agents (
                        case_id, agent_name, duration_ms,
                        input_tokens, output_tokens, tool_calls, status
                    )
                    SELECT $1::varchar, $2::varchar, $3::integer,
                           $4::integer, $5::integer, $6::integer, $7::varchar
                    WHERE NOT EXISTS (
                        SELECT 1 FROM analytics_agents
                        WHERE case_id=$1::varchar AND agent_name=$2::varchar
                    )
                    """,
                    cid, agent,
                    500 + (step_idx * 300) + (case_idx * 100),
                    100 + step_idx * 50,
                    50 + step_idx * 30,
                    1 if agent in ("doc_analyze_agent", "legal_search_agent", "compliance_agent") else 0,
                    "completed",
                )
                if result.endswith(" 1"):
                    inserted += 1
            except Exception as e:
                log.debug(f"analytics_agents insert skip: {e}")
    log.info(f"[analytics_agents] +{inserted} rows")


# ─────────────────────────────────────────────────────────────────────────────
# MinIO placeholder objects
# ─────────────────────────────────────────────────────────────────────────────

def upload_doc_placeholder(doc: dict) -> bool:
    """Upload a tiny placeholder file to MinIO for the document's oss_key."""
    try:
        data, mime = _doc_payload(doc["content_type"])
        oss_put_object(doc["oss_key"], data, mime)
        return True
    except Exception as e:
        log.warning(f"MinIO upload failed for {doc['oss_key']}: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Misc
# ─────────────────────────────────────────────────────────────────────────────

def _parse_dt(v):
    if v is None or isinstance(v, datetime):
        return v
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    log.info("=== GovFlow Extended Seed starting ===")
    create_gremlin_client()
    create_oss_client()
    await create_pg_pool()

    try:
        pool = get_pg_pool()

        # ── Build data ──────────────────────────────────────────────────────
        cases_generated, docs = _build_cases_and_docs()
        log.info(f"Built {len(cases_generated)} generated cases, {len(docs)} docs")

        # ── PostgreSQL: users ────────────────────────────────────────────────
        async with pool.acquire() as conn:
            await seed_extra_users(conn)

        # ── GDB: cases ──────────────────────────────────────────────────────
        log.info("Seeding case vertices in GDB...")
        for c in cases_generated:
            _gdb_upsert_case(c)
            _gdb_upsert_applicant(c["case_id"], c["applicant"])

        log.info(f"  done: {len(cases_generated)} cases")

        # ── GDB: docs (upsert all 150) ──────────────────────────────────────
        log.info("Seeding document vertices in GDB...")
        minio_ok = 0
        for d in docs:
            _gdb_upsert_doc(d)
            if upload_doc_placeholder(d):
                minio_ok += 1

        log.info(f"  done: {len(docs)} docs, {minio_ok} MinIO uploads OK")

        # ── GDB: gaps (30 across 15 cases) ──────────────────────────────────
        log.info("Seeding gap vertices...")
        gap_counter = 100
        gap_cases = cases_generated[:15]
        for i, c in enumerate(gap_cases):
            for j in range(2):  # 2 gaps per case = 30 total
                gap_tmpl = _GAP_TEMPLATES[(i * 2 + j) % len(_GAP_TEMPLATES)]
                gap_id = f"GAP-EXT-{gap_counter:03d}"
                _gdb_upsert_gap(
                    c["case_id"], gap_id,
                    gap_tmpl[0], gap_tmpl[1], gap_tmpl[2], gap_tmpl[3],
                )
                gap_counter += 1
        log.info(f"  done: {gap_counter - 100} gaps")

        # ── GDB: citations (20 across 10 cases) ─────────────────────────────
        log.info("Seeding citation vertices...")
        cit_counter = 100
        cit_cases = cases_generated[:10]
        for i, c in enumerate(cit_cases):
            for j in range(2):  # 2 citations per case = 20 total
                tmpl = _CITATION_TEMPLATES[(i * 2 + j) % len(_CITATION_TEMPLATES)]
                cit_id = f"CIT-EXT-{cit_counter:03d}"
                _gdb_upsert_citation(c["case_id"], cit_id, tmpl[0], tmpl[1], tmpl[2])
                cit_counter += 1
        log.info(f"  done: {cit_counter - 100} citations")

        # ── GDB: agent steps (6 cases × 10 steps = 60) ──────────────────────
        log.info("Seeding agent step vertices...")
        step_counter = 0
        agent_seq = [
            "intake_agent", "doc_analyze_agent", "classifier_agent",
            "legal_search_agent", "compliance_agent", "router_agent",
            "consult_agent", "summary_agent", "draft_agent", "security_officer_agent",
        ]
        for case_idx, c in enumerate(cases_generated[:6]):
            cid = c["case_id"]
            for step_idx, agent in enumerate(agent_seq):
                step_id = f"STEP-EXT-{case_idx:02d}-{step_idx:02d}"
                step_counter += 1
                _gdb_upsert_agent_step(cid, {
                    "step_id": step_id,
                    "agent_name": agent,
                    "action": f"Xử lý {agent.replace('_', ' ')} cho {cid}",
                    "status": "completed",
                    "input_tokens": 200 + step_idx * 50,
                    "output_tokens": 100 + step_idx * 30,
                    "duration_ms": 800 + step_idx * 200,
                    "output_summary": f"[{agent}] Hoàn thành bước {step_idx+1}/10 cho {cid}",
                    "reasoning_excerpt": (
                        f"Agent {agent} xử lý hồ sơ {cid}. "
                        f"Bước {step_idx+1}: phân tích đầu vào và tạo kết quả đầu ra."
                    ),
                })
        log.info(f"  done: {step_counter} agent steps")

        # ── PostgreSQL: analytics, dispatch, consult, audit, notifications ──
        async with pool.acquire() as conn:
            await seed_analytics(conn, cases_generated)
            await seed_dispatch_logs(conn, cases_generated)
            await seed_consult_requests(conn, cases_generated)
            await seed_audit_events(conn, cases_generated)
            await seed_notifications(conn)
            await seed_analytics_agents(conn, cases_generated)

        # ── Summary ─────────────────────────────────────────────────────────
        log.info("=== SEED SUMMARY ===")
        async with pool.acquire() as conn:
            users_count = await conn.fetchval("SELECT COUNT(*) FROM users")
            cases_count = await conn.fetchval("SELECT COUNT(*) FROM analytics_cases")
            audit_count = await conn.fetchval("SELECT COUNT(*) FROM audit_events_flat")
            notif_count = await conn.fetchval("SELECT COUNT(*) FROM notifications")
            dispatch_count = await conn.fetchval("SELECT COUNT(*) FROM dispatch_log")
            agent_count = await conn.fetchval("SELECT COUNT(*) FROM analytics_agents")

        v_count = gremlin_submit("g.V().count()")
        e_count = gremlin_submit("g.E().count()")
        doc_gdb = gremlin_submit("g.V().hasLabel('Document').count()")
        gap_gdb = gremlin_submit("g.V().hasLabel('Gap').count()")
        step_gdb = gremlin_submit("g.V().hasLabel('AgentStep').count()")
        consult_gdb = gremlin_submit("g.V().hasLabel('ConsultRequest').count()")
        case_gdb = gremlin_submit("g.V().hasLabel('Case').count()")

        print("")
        print("╔══════════════════════════════════╦═══════╗")
        print("║ Table                            ║ Rows  ║")
        print("╠══════════════════════════════════╬═══════╣")
        print(f"║ users (PG)                       ║ {users_count:5d} ║")
        print(f"║ analytics_cases (PG)             ║ {cases_count:5d} ║")
        print(f"║ audit_events_flat (PG)           ║ {audit_count:5d} ║")
        print(f"║ notifications (PG)               ║ {notif_count:5d} ║")
        print(f"║ dispatch_log (PG)                ║ {dispatch_count:5d} ║")
        print(f"║ analytics_agents (PG)            ║ {agent_count:5d} ║")
        print(f"║ Case vertices (GDB)              ║ {(case_gdb[0] if case_gdb else 0):5d} ║")
        print(f"║ Document vertices (GDB)          ║ {(doc_gdb[0] if doc_gdb else 0):5d} ║")
        print(f"║ Gap vertices (GDB)               ║ {(gap_gdb[0] if gap_gdb else 0):5d} ║")
        print(f"║ AgentStep vertices (GDB)         ║ {(step_gdb[0] if step_gdb else 0):5d} ║")
        print(f"║ ConsultRequest vertices (GDB)    ║ {(consult_gdb[0] if consult_gdb else 0):5d} ║")
        print(f"║ Total GDB vertices               ║ {(v_count[0] if v_count else 0):5d} ║")
        print(f"║ Total GDB edges                  ║ {(e_count[0] if e_count else 0):5d} ║")
        print("╚══════════════════════════════════╩═══════╝")
        print("")
        log.info("=== Extended seed complete ===")

    finally:
        await close_pg_pool()
        close_gremlin_client()


if __name__ == "__main__":
    asyncio.run(main())
