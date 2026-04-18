"""Ensure stable DOC-001..DOC-041 IDs exist for predictable URL testing."""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")
from src.database import (
    create_gremlin_client,
    gremlin_submit,
    close_gremlin_client,
)

STABLE_DOCS = {
    "DOC-001": ("don_cpxd.pdf", "don_xin_cap_phep", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-002": ("banve.pdf", "ban_ve_thiet_ke", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-003": ("qsdd.pdf", "giay_cn_qsdd", "demo-seed/sample_gcn_qsdd.pdf", "application/pdf"),
    "DOC-004": ("hopdong.pdf", "hop_dong", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-010": ("don_dk.pdf", "don_dang_ky", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-011": ("diachinh.pdf", "ban_do_dia_chinh", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-012": ("bando.pdf", "ban_do", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-020": ("denghi.pdf", "giay_de_nghi", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-021": ("dieule.pdf", "dieu_le", "demo-seed/sample_dieu_le_cong_ty.pdf", "application/pdf"),
    "DOC-030": ("yeucau.pdf", "yeu_cau", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-031": ("cccd.pdf", "cccd", "demo-seed/sample_cccd.jpg", "image/jpeg"),
    "DOC-040": ("dtm.pdf", "dtm", "demo-seed/sample_don_xin_cpxd.pdf", "application/pdf"),
    "DOC-041": ("gpkd.pdf", "giay_phep_kd", "demo-seed/sample_giay_phep_kd.pdf", "application/pdf"),
}


def main() -> int:
    create_gremlin_client()
    now = datetime.now(timezone.utc).isoformat()
    created = 0
    for did, (fn, dt, ok, ct) in STABLE_DOCS.items():
        exists = gremlin_submit(
            "g.V().has('Document', 'document_id', did).count()",
            {"did": did},
        )
        count = exists[0] if exists else 0
        if count and (int(count) if not isinstance(count, dict) else count.get("value", 0)):
            continue
        gremlin_submit(
            "g.addV('Document')"
            ".property('document_id', did).property('doc_id', did)"
            ".property('filename', fn).property('doc_type', dt)"
            ".property('oss_key', ok).property('content_type', ct)"
            ".property('ocr_status', 'completed')"
            ".property('uploaded_at', up)"
            ".property('size_bytes', 48000)",
            {"did": did, "fn": fn, "dt": dt, "ok": ok, "ct": ct, "up": now},
        )
        created += 1
        print(f"  + created stable doc: {did} ({fn})")
    print(f"{created} stable docs created, total stable set: {len(STABLE_DOCS)}")
    close_gremlin_client()
    return 0


if __name__ == "__main__":
    sys.exit(main())
