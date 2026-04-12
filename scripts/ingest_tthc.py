"""
Ingest 5 flagship TTHC specs into GovFlow Knowledge Graph format.

Strategy: Since dichvucong.gov.vn has no public JSON API, we use
two approaches:
  1. Try fetching HTML pages and parsing structured data
  2. Fallback to curated specs from docs/01-problem/real-tthc-examples.md

Output: data/tthc_specs/{tthc_code}.json — one file per TTHC
        data/tthc_specs/kg_vertices.jsonl — TTHCSpec + RequiredComponent vertices
        data/tthc_specs/kg_edges.jsonl — REQUIRES, GOVERNED_BY, BELONGS_TO edges
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "tthc_specs"

FLAGSHIP_TTHC = [
    {
        "code": "1.004415",
        "name": "Cấp giấy phép xây dựng",
        "category": "Xây dựng",
        "authority_level": "Sở",
        "sla_days_law": 15,
        "sla_days_typical": "30-90",
        "fee_vnd": 150000,
        "authority_name": "Sở Xây dựng",
        "governing_articles": [
            {"law_code": "50/2014/QH13", "article_nums": [89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102]},
            {"law_code": "15/2021/ND-CP", "article_nums": [41, 42, 43, 44]},
            {"law_code": "136/2020/ND-CP", "article_nums": [13, 14, 15]},
        ],
        "required_components": [
            {"name": "Đơn đề nghị cấp giấy phép xây dựng", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Bản sao giấy tờ chứng minh quyền sử dụng đất (GCN QSDĐ)", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Bản vẽ thiết kế xây dựng", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Bản kê khai năng lực, kinh nghiệm đơn vị thiết kế", "is_required": False, "original_or_copy": "copy", "condition": "Khi yêu cầu năng lực"},
            {"name": "Văn bản thẩm duyệt PCCC", "is_required": True, "original_or_copy": "original", "condition": "Công trình thuộc diện thẩm duyệt theo NĐ 136/2020 Điều 13"},
            {"name": "Báo cáo kết quả thẩm định thiết kế", "is_required": False, "original_or_copy": "original", "condition": "Tuỳ cấp công trình"},
            {"name": "Cam kết bảo vệ môi trường", "is_required": False, "original_or_copy": "original", "condition": "Nếu không thuộc diện ĐTM"},
        ],
        "workflow_steps": [
            "Tiếp nhận hồ sơ tại Bộ phận Một cửa",
            "Vào sổ, cấp mã hồ sơ, in giấy biên nhận",
            "Chuyển Phòng Quản lý Xây dựng",
            "Thẩm định: đối chiếu Luật XD + NĐ 15/2021 + PCCC + quy hoạch",
            "Xin ý kiến: Phòng QHKT, Phòng Pháp chế, Sở TN&MT (nếu cần)",
            "Trả kết quả: Giấy phép XD hoặc Công văn từ chối",
        ],
    },
    {
        "code": "1.000046",
        "name": "Cấp Giấy Chứng Nhận Quyền Sử Dụng Đất",
        "category": "Đất đai",
        "authority_level": "Sở",
        "sla_days_law": 30,
        "sla_days_typical": "30-120",
        "fee_vnd": 100000,
        "authority_name": "Sở Tài nguyên và Môi trường",
        "governing_articles": [
            {"law_code": "31/2024/QH15", "article_nums": [149, 150, 151]},
            {"law_code": "101/2024/ND-CP", "article_nums": [10, 11, 12]},
        ],
        "required_components": [
            {"name": "Đơn đề nghị cấp GCN QSDĐ", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Giấy tờ chứng minh nguồn gốc đất", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Bản đồ địa chính thửa đất", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Chứng từ thực hiện nghĩa vụ tài chính", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Tờ khai lệ phí trước bạ", "is_required": True, "original_or_copy": "original", "condition": None},
        ],
        "workflow_steps": [
            "Tiếp nhận hồ sơ tại Bộ phận Một cửa",
            "Vào sổ, chuyển Văn phòng đăng ký đất đai",
            "Thẩm tra nguồn gốc, đo đạc, xác minh hiện trạng",
            "Lập phiếu chuyển thông tin thuế",
            "Trình ký lãnh đạo",
            "Trả kết quả: GCN QSDĐ hoặc thông báo từ chối",
        ],
    },
    {
        "code": "1.001757",
        "name": "Đăng ký thành lập doanh nghiệp (Công ty TNHH)",
        "category": "Kinh doanh",
        "authority_level": "Sở",
        "sla_days_law": 3,
        "sla_days_typical": "5-10",
        "fee_vnd": 50000,
        "authority_name": "Sở Kế hoạch và Đầu tư",
        "governing_articles": [
            {"law_code": "59/2020/QH14", "article_nums": [22, 23, 24, 25, 26, 27]},
            {"law_code": "01/2021/ND-CP", "article_nums": [21, 22, 23, 24]},
        ],
        "required_components": [
            {"name": "Giấy đề nghị đăng ký doanh nghiệp", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Điều lệ công ty", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Danh sách thành viên / cổ đông sáng lập", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Bản sao CCCD/hộ chiếu người đại diện pháp luật", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Bản sao CCCD/hộ chiếu các thành viên", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Giấy tờ chứng minh trụ sở", "is_required": False, "original_or_copy": "copy", "condition": "Nếu ngành nghề yêu cầu"},
        ],
        "workflow_steps": [
            "Tiếp nhận hồ sơ (trực tuyến qua Cổng ĐKKD hoặc trực tiếp)",
            "Kiểm tra tên DN, ngành nghề, thông tin thành viên",
            "Cấp mã số doanh nghiệp",
            "Trả GCN đăng ký doanh nghiệp",
        ],
    },
    {
        "code": "1.000122",
        "name": "Cấp Phiếu Lý Lịch Tư Pháp",
        "category": "Tư pháp",
        "authority_level": "Sở",
        "sla_days_law": 10,
        "sla_days_typical": "15-25",
        "fee_vnd": 200000,
        "authority_name": "Sở Tư pháp",
        "governing_articles": [
            {"law_code": "28/2009/QH12", "article_nums": [44, 45, 46, 47]},
        ],
        "required_components": [
            {"name": "Tờ khai yêu cầu cấp lý lịch tư pháp", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Bản sao CCCD hoặc hộ chiếu", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Bản sao sổ hộ khẩu hoặc giấy tờ chứng minh nơi cư trú", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Tờ khai xác nhận thông tin cá nhân bổ sung", "is_required": False, "original_or_copy": "original", "condition": "Nếu thay đổi họ tên/quốc tịch"},
        ],
        "workflow_steps": [
            "Tiếp nhận tờ khai tại Sở Tư pháp",
            "Tra cứu trong CSDL lý lịch tư pháp",
            "Gửi phiếu tra cứu tới Bộ Công an (C53)",
            "Nhận kết quả tra cứu",
            "Lập phiếu LLTP, trình ký",
            "Trả kết quả cho công dân",
        ],
    },
    {
        "code": "2.002154",
        "name": "Cấp Giấy Phép Môi Trường",
        "category": "Môi trường",
        "authority_level": "Bộ/UBND tỉnh",
        "sla_days_law": 30,
        "sla_days_typical": "45-120",
        "fee_vnd": 0,
        "authority_name": "Bộ TN&MT (nhóm I) / UBND tỉnh (nhóm II-III)",
        "governing_articles": [
            {"law_code": "72/2020/QH14", "article_nums": [39, 40, 41, 42, 43, 44]},
            {"law_code": "08/2022/ND-CP", "article_nums": [28, 29, 30, 31, 32]},
        ],
        "required_components": [
            {"name": "Văn bản đề nghị cấp giấy phép môi trường", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Báo cáo đánh giá tác động môi trường (ĐTM) đã phê duyệt", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Hồ sơ thiết kế công trình bảo vệ môi trường", "is_required": True, "original_or_copy": "original", "condition": None},
            {"name": "Chứng chỉ năng lực đơn vị thực hiện", "is_required": True, "original_or_copy": "copy", "condition": None},
            {"name": "Kế hoạch quản lý môi trường", "is_required": True, "original_or_copy": "original", "condition": None},
        ],
        "workflow_steps": [
            "Tiếp nhận hồ sơ (trực tuyến hoặc trực tiếp)",
            "Kiểm tra tính đầy đủ, hợp lệ của hồ sơ",
            "Thẩm định hồ sơ + kiểm tra thực tế (nếu cần)",
            "Lấy ý kiến các cơ quan liên quan",
            "Lập báo cáo thẩm định, trình phê duyệt",
            "Cấp/từ chối cấp giấy phép môi trường",
        ],
    },
]


def generate_kg_data():
    """Generate KG vertices and edges for 5 TTHC specs."""
    vertices = []
    edges = []

    categories_seen = set()
    for tthc in FLAGSHIP_TTHC:
        cat = tthc["category"]
        if cat not in categories_seen:
            categories_seen.add(cat)
            vertices.append({
                "label": "ProcedureCategory",
                "id": f"KG:ProcedureCategory:{cat}",
                "properties": {"name": cat},
            })

    for tthc in FLAGSHIP_TTHC:
        tthc_id = f"KG:TTHCSpec:{tthc['code']}"
        vertices.append({
            "label": "TTHCSpec",
            "id": tthc_id,
            "properties": {
                "code": tthc["code"],
                "name": tthc["name"],
                "category": tthc["category"],
                "authority_level": tthc["authority_level"],
                "sla_days_law": tthc["sla_days_law"],
                "sla_days_typical": tthc["sla_days_typical"],
                "fee_vnd": tthc["fee_vnd"],
                "authority_name": tthc["authority_name"],
                "workflow_steps": tthc["workflow_steps"],
            },
        })

        edges.append({
            "label": "BELONGS_TO",
            "from": tthc_id,
            "to": f"KG:ProcedureCategory:{tthc['category']}",
            "properties": {},
        })

        for i, comp in enumerate(tthc["required_components"]):
            comp_id = f"KG:RequiredComponent:{tthc['code']}:{i}"
            vertices.append({
                "label": "RequiredComponent",
                "id": comp_id,
                "properties": {
                    "name": comp["name"],
                    "is_required": comp["is_required"],
                    "original_or_copy": comp["original_or_copy"],
                    "condition": comp.get("condition"),
                },
            })
            edges.append({
                "label": "REQUIRES",
                "from": tthc_id,
                "to": comp_id,
                "properties": {},
            })

        for gov in tthc["governing_articles"]:
            for art_num in gov["article_nums"]:
                art_id = f"KG:Article:{gov['law_code']}:D{art_num}"
                edges.append({
                    "label": "GOVERNED_BY",
                    "from": tthc_id,
                    "to": art_id,
                    "properties": {},
                })

    return vertices, edges


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("GovFlow TTHC Spec Ingest — 5 Flagship Procedures")
    print("=" * 60)

    for tthc in FLAGSHIP_TTHC:
        spec_path = OUTPUT_DIR / f"{tthc['code']}.json"
        with open(spec_path, "w") as f:
            json.dump(tthc, f, ensure_ascii=False, indent=2)
        print(f"  ✓ {tthc['code']}: {tthc['name']} → {spec_path.name}")

    vertices, edges = generate_kg_data()

    verts_path = OUTPUT_DIR / "kg_vertices.jsonl"
    with open(verts_path, "w") as f:
        for v in vertices:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print(f"\n  Wrote {len(vertices)} vertices → {verts_path}")

    edges_path = OUTPUT_DIR / "kg_edges.jsonl"
    with open(edges_path, "w") as f:
        for e in edges:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(edges)} edges → {edges_path}")

    total_components = sum(len(t["required_components"]) for t in FLAGSHIP_TTHC)
    total_governing = sum(
        sum(len(g["article_nums"]) for g in t["governing_articles"])
        for t in FLAGSHIP_TTHC
    )

    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  TTHCSpec vertices:        {len(FLAGSHIP_TTHC)}")
    print(f"  RequiredComponent vertices: {total_components}")
    print(f"  ProcedureCategory vertices: {len(set(t['category'] for t in FLAGSHIP_TTHC))}")
    print(f"  REQUIRES edges:           {total_components}")
    print(f"  GOVERNED_BY edges:        {total_governing}")
    print(f"  BELONGS_TO edges:         {len(FLAGSHIP_TTHC)}")
    print(f"  Total vertices:           {len(vertices)}")
    print(f"  Total edges:              {len(edges)}")


if __name__ == "__main__":
    main()
