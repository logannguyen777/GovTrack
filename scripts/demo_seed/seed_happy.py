"""Seed happy-path demo cases: every required document present + rich metadata.

Intentionally leaves CASE-2026-0001 (CPXD) missing 1 document (Văn bản thẩm
duyệt PCCC) so judges see the "hero gap" demo scenario.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "/app")
from src.database import (
    create_gremlin_client,
    gremlin_submit,
    close_gremlin_client,
)

# Map: case_id → (tthc_code, rich_metadata, status, submitted_days_ago, skip_components)
CASE_PLAN = {
    "CASE-2026-0001": {  # CPXD — hero gap case
        "tthc_code": "1.004415",
        "status": "consultation",
        "submitted_days_ago": 5,
        "applicant_name": "Nguyễn Văn Bình",
        "applicant_id_number": "001085012345",
        "applicant_phone": "0912345678",
        "applicant_address": "Số 18 Nguyễn Trãi, Thượng Đình, Thanh Xuân, Hà Nội",
        "project_name": "Nhà ở riêng lẻ 3 tầng",
        "project_address": "Lô đất A12, Khu đô thị Văn Phú, phường Phú La, Hà Đông, Hà Nội",
        "construction_area": "82m² (3 tầng)",
        "notes": "Xin cấp phép xây dựng nhà ở riêng lẻ tại Khu đô thị Văn Phú",
        "skip_components": ["Văn bản thẩm duyệt PCCC"],  # demo gap
    },
    "CASE-2026-0002": {  # QSDĐ — happy
        "tthc_code": "1.000046",
        "status": "classifying",
        "submitted_days_ago": 3,
        "applicant_name": "Trần Thị Hoa",
        "applicant_id_number": "052075067890",
        "applicant_phone": "0987654321",
        "applicant_address": "Số 45 Lê Hồng Phong, phường Trần Phú, TP Quy Nhơn, Bình Định",
        "land_parcel": "Thửa 285, tờ 12",
        "land_area": "120 m²",
        "notes": "Cấp GCN quyền sử dụng đất lần đầu — nguồn gốc đất: chuyển nhượng hợp pháp 2018",
        "skip_components": [],
    },
    "CASE-2026-0003": {  # DN — happy
        "tthc_code": "1.001757",
        "status": "drafting",
        "submitted_days_ago": 8,
        "applicant_name": "Lê Minh Tuấn",
        "applicant_id_number": "079082034567",
        "applicant_phone": "0903456789",
        "applicant_address": "Số 7 Đinh Tiên Hoàng, phường Đa Kao, Quận 1, TP HCM",
        "company_name": "Công ty TNHH Tư vấn Quản lý Tuấn Minh",
        "company_capital": "500.000.000 VND",
        "business_address": "Số 7 Đinh Tiên Hoàng, phường Đa Kao, Quận 1, TP HCM",
        "notes": "Đăng ký thành lập công ty TNHH một thành viên — lĩnh vực tư vấn quản lý",
        "skip_components": [],
    },
    "CASE-2026-0004": {  # LLTP — already published happy case
        "tthc_code": "1.000122",
        "status": "published",
        "submitted_days_ago": 12,
        "applicant_name": "Phạm Thị Lan",
        "applicant_id_number": "036095089012",
        "applicant_phone": "0978901234",
        "applicant_address": "Số 22 Bà Triệu, phường Lê Đại Hành, Hai Bà Trưng, Hà Nội",
        "purpose": "Nộp hồ sơ du học",
        "certificate_type": "Phiếu LLTP số 1 (cá nhân)",
        "notes": "Xin cấp phiếu lý lịch tư pháp số 1 phục vụ hồ sơ du học",
        "skip_components": [],
    },
    "CASE-2026-0005": {  # Env — happy (submitted stage)
        "tthc_code": "2.002154",
        "status": "leader_review",
        "submitted_days_ago": 10,
        "applicant_name": "Công ty TNHH Xanh Việt",
        "applicant_id_number": "0106789012",
        "applicant_phone": "02438765432",
        "applicant_address": "Lô B12 KCN Thăng Long, Đông Anh, Hà Nội",
        "project_name": "Nhà máy chế biến nông sản",
        "project_capacity": "200 tấn/tháng",
        "notes": "Cấp giấy phép môi trường cho dự án nhà máy chế biến công suất vừa",
        "skip_components": [],
    },
}

# Filename template per component name
def _filename(component_name: str, idx: int) -> str:
    slug = (
        component_name.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace(":", "")
    )[:60]
    return f"{idx:02d}_{slug}.pdf"


def _oss_key_for(component_name: str) -> str:
    """Best-fit mapping: reuse 5 sample files for all components."""
    n = component_name.lower()
    if "cccd" in n or "cmnd" in n or "căn cước" in n or "chứng minh" in n:
        return "demo-seed/sample_cccd.jpg"
    if "đất" in n or "qsdd" in n or "gcn" in n or "địa chính" in n or "thửa" in n:
        return "demo-seed/sample_gcn_qsdd.pdf"
    if "kinh doanh" in n or "doanh nghi" in n or "điều lệ" in n or "gpkd" in n:
        return "demo-seed/sample_giay_phep_kd.pdf"
    if "điều lệ" in n:
        return "demo-seed/sample_dieu_le_cong_ty.pdf"
    # default to CPXD đơn xin
    return "demo-seed/sample_don_xin_cpxd.pdf"


def _content_type(oss_key: str) -> str:
    if oss_key.endswith(".pdf"):
        return "application/pdf"
    if oss_key.endswith(".jpg") or oss_key.endswith(".jpeg"):
        return "image/jpeg"
    if oss_key.endswith(".png"):
        return "image/png"
    return "application/octet-stream"


def main() -> int:
    create_gremlin_client()

    for case_id, plan in CASE_PLAN.items():
        now = datetime.now(timezone.utc)
        submitted_at = (now - timedelta(days=plan["submitted_days_ago"])).isoformat()

        print(f"\n=== {case_id} · TTHC {plan['tthc_code']} · {plan['status']} ===")

        # 1. Update case properties (rich metadata + proper submitted_at)
        form_data = {
            k: plan[k]
            for k in (
                "applicant_name",
                "applicant_id_number",
                "applicant_phone",
                "applicant_address",
                "notes",
            )
        }
        # Include TTHC-specific extras
        for extra in (
            "project_name", "project_address", "construction_area",
            "land_parcel", "land_area",
            "company_name", "company_capital", "business_address",
            "purpose", "certificate_type",
            "project_capacity",
        ):
            if extra in plan:
                form_data[extra] = plan[extra]

        form_data_json = json.dumps(form_data, ensure_ascii=False)

        gremlin_submit(
            "g.V().has('Case', 'case_id', cid)"
            ".property('status', st)"
            ".property('submitted_at', sub)"
            ".property('tthc_code', tc)"
            ".property('form_data', fd)"
            ".property('notes', nt)",
            {
                "cid": case_id,
                "st": plan["status"],
                "sub": submitted_at,
                "tc": plan["tthc_code"],
                "fd": form_data_json,
                "nt": plan["notes"],
            },
        )

        # 2. Drop only the HAS_DOCUMENT edges (keep Document vertices so other cases
        # / stable IDs like DOC-001..DOC-041 are preserved).
        gremlin_submit(
            "g.V().has('Case', 'case_id', cid).outE('HAS_DOCUMENT').drop()",
            {"cid": case_id},
        )

        # 3. Fetch RequiredComponents for this TTHC
        reqs = gremlin_submit(
            "g.V().has('TTHCSpec', 'code', tc)"
            ".out('REQUIRES').valueMap(true)",
            {"tc": plan["tthc_code"]},
        )
        skip = set(plan["skip_components"])

        created = 0
        for idx, r in enumerate(reqs, start=1):
            name = (r.get("name") or r.get("component_name") or [""])
            comp_name = name[0] if isinstance(name, list) else str(name)
            if comp_name in skip:
                print(f"  SKIP (demo gap): {comp_name}")
                continue
            doc_id = f"DOC-{uuid.uuid4().hex[:10].upper()}"
            fname = _filename(comp_name, idx)
            oss_key = _oss_key_for(comp_name)
            ctype = _content_type(oss_key)

            gremlin_submit(
                "g.addV('Document')"
                ".property('document_id', did).property('doc_id', did)"
                ".property('case_id', cid)"
                ".property('filename', fn).property('content_type', ct)"
                ".property('oss_key', ok)"
                ".property('component_name', comp)"
                ".property('ocr_status', 'completed')"
                ".property('uploaded_at', up)"
                ".property('size_bytes', sz)",
                {
                    "did": doc_id,
                    "cid": case_id,
                    "fn": fname,
                    "ct": ctype,
                    "ok": oss_key,
                    "comp": comp_name,
                    "up": submitted_at,
                    "sz": 48000,
                },
            )
            gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".as('c').V().has('Document', 'document_id', did)"
                ".addE('HAS_DOCUMENT').from('c')",
                {"cid": case_id, "did": doc_id},
            )
            # SATISFIES edge: Document satisfies RequiredComponent
            kg_id = (r.get("_kg_id") or [""])[0]
            if kg_id:
                try:
                    gremlin_submit(
                        "g.V().has('Document', 'document_id', did)"
                        ".as('d').V().has('RequiredComponent', '_kg_id', k)"
                        ".addE('SATISFIES').from('d')",
                        {"did": doc_id, "k": kg_id},
                    )
                except Exception:
                    pass
            created += 1
            print(f"  + {doc_id} · {fname}")

        print(f"  {created} documents linked")

    close_gremlin_client()
    return 0


if __name__ == "__main__":
    sys.exit(main())
