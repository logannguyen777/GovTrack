"""Seed representative Gap vertices for demo cases."""
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, "/app")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

# Hero CPXD case: PCCC gap (classic example from spec)
GAPS = [
    (
        "CASE-2026-0001",
        [
            (
                "Thiếu văn bản thẩm duyệt PCCC",
                "critical",
                "Bổ sung Văn bản thẩm duyệt thiết kế về PCCC do Cảnh sát PCCC cấp trước khi xét duyệt cấp phép xây dựng.",
                "NĐ 136/2020/NĐ-CP Điều 13 Khoản 3 Điểm a",
                True,
            ),
            (
                "Bản vẽ thiết kế chưa có chữ ký chủ đầu tư",
                "high",
                "Yêu cầu chủ đầu tư ký xác nhận vào bản vẽ thiết kế kỹ thuật (6 bản).",
                "NĐ 15/2021/NĐ-CP Điều 12 Khoản 1",
                False,
            ),
            (
                "Giấy CN QSDĐ nộp dưới dạng bản chụp chưa công chứng",
                "medium",
                "Yêu cầu nộp bản sao công chứng giấy chứng nhận quyền sử dụng đất.",
                "NĐ 15/2021/NĐ-CP Điều 11 Khoản 2",
                False,
            ),
        ],
    ),
    (
        "CASE-2026-0003",
        [
            (
                "Chưa có điều lệ công ty",
                "critical",
                "Bổ sung bản điều lệ công ty có đầy đủ chữ ký của tất cả thành viên sáng lập.",
                "Luật Doanh nghiệp 2020 Điều 24",
                True,
            ),
            (
                "Danh sách thành viên thiếu CCCD",
                "medium",
                "Yêu cầu bổ sung bản sao CCCD của tất cả thành viên sáng lập.",
                "Luật Doanh nghiệp 2020 Điều 21",
                False,
            ),
        ],
    ),
]


def main() -> int:
    create_gremlin_client()
    now = datetime.now(timezone.utc).isoformat()
    # Clear previous gaps
    for case_id, _ in GAPS:
        gremlin_submit(
            "g.V().has('Case', 'case_id', cid).out('HAS_GAP').drop()",
            {"cid": case_id},
        )
    # Insert new gaps
    for case_id, gaps in GAPS:
        for description, severity, fix_sug, req_ref, blocking in gaps:
            gap_id = f"GAP-{uuid.uuid4().hex[:8].upper()}"
            gremlin_submit(
                "g.addV('Gap')"
                ".property('gap_id', gid).property('description', descr)"
                ".property('severity', sev).property('fix_suggestion', fix)"
                ".property('requirement_ref', req).property('is_blocking', blk)"
                ".property('case_id', cid).property('created_at', now)",
                {
                    "gid": gap_id,
                    "descr": description,
                    "sev": severity,
                    "fix": fix_sug,
                    "req": req_ref,
                    "blk": "true" if blocking else "false",
                    "cid": case_id,
                    "now": now,
                },
            )
            gremlin_submit(
                "g.V().has('Case', 'case_id', cid)"
                ".as('c').V().has('Gap', 'gap_id', gid)"
                ".addE('HAS_GAP').from('c')",
                {"cid": case_id, "gid": gap_id},
            )
            print(f"{case_id}: + {gap_id} · {severity} · {description[:50]}")

    close_gremlin_client()
    return 0


if __name__ == "__main__":
    sys.exit(main())
