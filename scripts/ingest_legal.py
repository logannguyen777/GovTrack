"""
Ingest legal corpus from HuggingFace th1nhng0/vietnamese-legal-documents
into GovFlow Knowledge Graph format.

Dataset structure (3 parquet files):
  - metadata.parquet: 153k rows (id, title, so_ky_hieu, loai_van_ban, tinh_trang_hieu_luc, ...)
  - content.parquet: 178k rows (id, content_html)
  - relationships.parquet: 897k rows (doc_id, other_doc_id, relationship)

Output:
  - data/legal/processed/vertices.jsonl  (Law, Decree, Circular, Article, Clause, Point)
  - data/legal/processed/edges.jsonl     (CONTAINS, AMENDED_BY, SUPERSEDED_BY, REFERENCES, etc.)
  - data/legal/processed/law_chunks.jsonl (for Hologres law_chunks table)
  - data/legal/processed/stats.json
"""

import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass

import pyarrow.parquet as pq
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "legal" / "raw" / "vietnamese-legal-documents" / "data"
PROCESSED_DIR = PROJECT_ROOT / "data" / "legal" / "processed"

CORE_LAW_CODES = {
    "50/2014/QH13", "62/2020/QH14", "15/2021/NĐ-CP", "136/2020/NĐ-CP",
    "31/2024/QH15", "101/2024/NĐ-CP", "59/2020/QH14", "01/2021/NĐ-CP",
    "28/2009/QH12", "72/2020/QH14", "08/2022/NĐ-CP", "61/2018/NĐ-CP",
    "107/2021/NĐ-CP", "45/2020/NĐ-CP", "30/2020/NĐ-CP",
}

CORE_LAW_NAMES = {
    "50/2014/QH13": "Luật Xây dựng 2014",
    "62/2020/QH14": "Luật sửa đổi Luật XD 2020",
    "15/2021/NĐ-CP": "NĐ 15/2021 cấp phép XD",
    "136/2020/NĐ-CP": "NĐ 136/2020 PCCC",
    "31/2024/QH15": "Luật Đất đai 2024",
    "101/2024/NĐ-CP": "NĐ 101/2024 hướng dẫn Luật Đất đai",
    "59/2020/QH14": "Luật Doanh nghiệp 2020",
    "01/2021/NĐ-CP": "NĐ 01/2021 ĐKKD",
    "28/2009/QH12": "Luật Lý lịch tư pháp 2009",
    "72/2020/QH14": "Luật BVMT 2020",
    "08/2022/NĐ-CP": "NĐ 08/2022 BVMT",
    "61/2018/NĐ-CP": "NĐ 61/2018 một cửa",
    "107/2021/NĐ-CP": "NĐ 107/2021 sửa đổi NĐ 61",
    "45/2020/NĐ-CP": "NĐ 45/2020 TTHC điện tử",
    "30/2020/NĐ-CP": "NĐ 30/2020 công tác văn thư",
}

REL_TYPE_MAP = {
    "Văn bản sửa đổi": "AMENDED_BY",
    "Văn bản được sửa đổi": "AMENDED_BY",
    "Văn bản hết hiệu lực": "SUPERSEDED_BY",
    "Văn bản quy định hết hiệu lực": "REPEALED_BY",
    "Văn bản quy định hết hiệu lực 1 phần": "PARTIALLY_REPEALED_BY",
    "Văn bản bị hết hiệu lực 1 phần": "PARTIALLY_REPEALED_BY",
    "Văn bản bổ sung": "AMENDED_BY",
    "Văn bản được bổ sung": "AMENDED_BY",
    "Văn bản căn cứ": "BASED_ON",
    "Văn bản dẫn chiếu": "REFERENCES",
    "Văn bản HD, QĐ chi tiết": "DETAILS",
    "Văn bản được HD, QĐ chi tiết": "DETAILED_BY",
    "Văn bản đình chỉ": "SUSPENDED_BY",
    "Văn bản bị đình chỉ": "SUSPENDED_BY",
    "Văn bản đình chỉ 1 phần": "PARTIALLY_SUSPENDED_BY",
    "Văn bản bị đình chỉ 1 phần": "PARTIALLY_SUSPENDED_BY",
    "Văn bản liên quan khác": "RELATED",
}


@dataclass
class Vertex:
    label: str
    id: str
    properties: dict


@dataclass
class Edge:
    label: str
    from_id: str
    to_id: str
    properties: dict = None


def classify_doc_type(loai_van_ban: str) -> str:
    loai = loai_van_ban.lower().strip()
    if "luật" in loai or "bộ luật" in loai:
        return "Law"
    if "nghị định" in loai:
        return "Decree"
    if "thông tư" in loai:
        return "Circular"
    if "quyết định" in loai:
        return "Decision"
    if "nghị quyết" in loai:
        return "Resolution"
    if "pháp lệnh" in loai:
        return "Ordinance"
    if "sắc lệnh" in loai:
        return "Decree"
    return "Other"


def html_to_text(html: str) -> str:
    if not html or not isinstance(html, str):
        return ""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n", strip=True)


def parse_articles(text: str):
    articles = []
    current = None
    current_clause = None

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue

        m = re.match(r"Điều\s+(\d+)\s*[.:]?\s*(.*)", line)
        if m:
            if current:
                articles.append(current)
            current = {
                "num": int(m.group(1)),
                "title": m.group(2).strip(),
                "text": line,
                "clauses": [],
            }
            current_clause = None
            continue

        cm = re.match(r"(\d+)\.\s+(.*)", line)
        if cm and current:
            current_clause = {"num": int(cm.group(1)), "text": line, "points": []}
            current["clauses"].append(current_clause)
            continue

        pm = re.match(r"([a-zđ])\)\s+(.*)", line)
        if pm and current_clause:
            current_clause["points"].append({"label": pm.group(1), "text": line})
            continue

        if current_clause:
            current_clause["text"] += "\n" + line
        elif current:
            current["text"] += "\n" + line

    if current:
        articles.append(current)
    return articles


def chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks, buf = [], ""
    for sent in re.split(r"(?<=[.;:])\s+", text):
        if len(buf) + len(sent) > max_chars and buf:
            chunks.append(buf.strip())
            buf = sent
        else:
            buf = buf + " " + sent if buf else sent
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def main():
    print("=" * 60)
    print("GovFlow Legal Corpus Ingest")
    print("=" * 60)

    if not RAW_DIR.exists():
        print(f"ERROR: {RAW_DIR} not found")
        sys.exit(1)

    print("\n[1/4] Loading metadata...")
    meta_df = pq.read_table(RAW_DIR / "metadata.parquet").to_pandas()
    print(f"  {len(meta_df)} documents")

    print("[2/4] Loading relationships...")
    rels_df = pq.read_table(RAW_DIR / "relationships.parquet").to_pandas()
    print(f"  {len(rels_df)} relationships")

    # Build id→so_ky_hieu lookup
    id_to_code = dict(zip(meta_df["id"], meta_df["so_ky_hieu"]))
    id_to_type = dict(zip(meta_df["id"], meta_df["loai_van_ban"]))
    code_to_id = {}
    for _, row in meta_df.iterrows():
        code_to_id[row["so_ky_hieu"]] = row["id"]

    # Find core law IDs
    core_ids = set()
    for _, row in meta_df.iterrows():
        if row["so_ky_hieu"] in CORE_LAW_CODES:
            core_ids.add(row["id"])

    # Also include docs directly related to core laws (1-hop)
    related_ids = set()
    for _, row in rels_df.iterrows():
        if row["doc_id"] in core_ids:
            related_ids.add(row["other_doc_id"])
        if row["other_doc_id"] in core_ids:
            related_ids.add(row["doc_id"])

    target_ids = core_ids | related_ids
    print(f"\n  Core laws: {len(core_ids)}")
    print(f"  1-hop related docs: {len(related_ids)}")
    print(f"  Total target docs: {len(target_ids)}")

    # Load content for target docs only
    print("\n[3/4] Loading content for target docs...")
    content_df = pq.read_table(RAW_DIR / "content.parquet").to_pandas()
    content_df["id"] = content_df["id"].astype(str)
    content_map = dict(zip(content_df["id"], content_df["content_html"]))
    del content_df
    print(f"  Content loaded ({len(content_map)} docs)")

    # Build vertices
    print("\n[4/4] Building graph...")
    vertices = []
    edges = []
    law_chunks = []
    seen = set()

    target_meta = meta_df[meta_df["id"].isin(target_ids)]
    for _, row in target_meta.iterrows():
        doc_id = row["id"]
        code = row["so_ky_hieu"]
        if not code or code in seen:
            continue
        seen.add(code)

        label = classify_doc_type(str(row["loai_van_ban"]))
        status_raw = str(row.get("tinh_trang_hieu_luc", ""))
        if "còn hiệu lực" in status_raw.lower():
            status = "effective"
        elif "hết hiệu lực toàn bộ" in status_raw.lower():
            status = "repealed"
        elif "hết hiệu lực một phần" in status_raw.lower():
            status = "amended"
        else:
            status = "unknown"

        is_core = code in CORE_LAW_CODES

        vertex_id = f"KG:{label}:{code}"
        vertices.append(Vertex(
            label=label,
            id=vertex_id,
            properties={
                "code": code,
                "name": str(row["title"]),
                "issued_date": str(row.get("ngay_ban_hanh", "")),
                "effective_date": str(row.get("ngay_co_hieu_luc", "")),
                "classification": "Unclassified",
                "status": status,
                "is_core": is_core,
                "co_quan_ban_hanh": str(row.get("co_quan_ban_hanh", "")),
                "nguoi_ky": str(row.get("nguoi_ky", "")),
            },
        ))

        # Parse content for core laws only (full-text article extraction is expensive)
        if is_core and str(doc_id) in content_map:
            html = content_map[str(doc_id)]
            text = html_to_text(html)

            if len(text) > 200:
                articles = parse_articles(text)
                for art in articles:
                    art_id = f"KG:Article:{code}:D{art['num']}"
                    vertices.append(Vertex(
                        label="Article",
                        id=art_id,
                        properties={
                            "law_code": code,
                            "num": art["num"],
                            "title": art.get("title", ""),
                            "text": art["text"][:10000],
                            "classification": "Unclassified",
                            "effective_date": str(row.get("ngay_co_hieu_luc", "")),
                        },
                    ))
                    edges.append(Edge("CONTAINS", vertex_id, art_id))

                    for clause in art.get("clauses", []):
                        clause_id = f"KG:Clause:{code}:D{art['num']}:K{clause['num']}"
                        vertices.append(Vertex(
                            label="Clause",
                            id=clause_id,
                            properties={
                                "law_code": code,
                                "article_num": art["num"],
                                "num": clause["num"],
                                "text": clause["text"][:5000],
                            },
                        ))
                        edges.append(Edge("HAS_CLAUSE", art_id, clause_id))

                        for pt in clause.get("points", []):
                            pt_id = f"KG:Point:{code}:D{art['num']}:K{clause['num']}:{pt['label']}"
                            vertices.append(Vertex(
                                label="Point",
                                id=pt_id,
                                properties={
                                    "law_code": code,
                                    "article_num": art["num"],
                                    "clause_num": clause["num"],
                                    "label": pt["label"],
                                    "text": pt["text"][:3000],
                                },
                            ))
                            edges.append(Edge("HAS_POINT", clause_id, pt_id))

                    for seq, chunk in enumerate(chunk_text(art["text"])):
                        law_chunks.append({
                            "law_code": code,
                            "article_num": art["num"],
                            "chunk_seq": seq,
                            "text": chunk,
                            "classification": "Unclassified",
                            "effective_date": str(row.get("ngay_co_hieu_luc", "")),
                            "status": status,
                        })

    # Build relationship edges
    code_to_vertex_id = {}
    for v in vertices:
        if v.label in ("Law", "Decree", "Circular", "Decision", "Resolution", "Ordinance", "Other"):
            code_to_vertex_id[v.properties["code"]] = v.id

    for _, row in rels_df.iterrows():
        src_id = row["doc_id"]
        tgt_id = row["other_doc_id"]
        rel = row["relationship"]

        if src_id not in target_ids and tgt_id not in target_ids:
            continue

        src_code = id_to_code.get(src_id)
        tgt_code = id_to_code.get(tgt_id)
        if not src_code or not tgt_code:
            continue

        src_vid = code_to_vertex_id.get(src_code)
        tgt_vid = code_to_vertex_id.get(tgt_code)

        edge_label = REL_TYPE_MAP.get(rel)
        if not edge_label or not src_vid or not tgt_vid:
            continue

        edges.append(Edge(edge_label, src_vid, tgt_vid, {"original_rel": rel}))

    # Write output
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    with open(PROCESSED_DIR / "vertices.jsonl", "w") as f:
        for v in vertices:
            f.write(json.dumps({"label": v.label, "id": v.id, "properties": v.properties}, ensure_ascii=False) + "\n")

    with open(PROCESSED_DIR / "edges.jsonl", "w") as f:
        for e in edges:
            f.write(json.dumps({"label": e.label, "from": e.from_id, "to": e.to_id, "properties": e.properties or {}}, ensure_ascii=False) + "\n")

    with open(PROCESSED_DIR / "law_chunks.jsonl", "w") as f:
        for c in law_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Stats
    label_counts = {}
    for v in vertices:
        label_counts[v.label] = label_counts.get(v.label, 0) + 1
    edge_counts = {}
    for e in edges:
        edge_counts[e.label] = edge_counts.get(e.label, 0) + 1

    core_found = [v.properties["code"] for v in vertices if v.properties.get("is_core")]

    stats = {
        "total_vertices": len(vertices),
        "total_edges": len(edges),
        "total_chunks": len(law_chunks),
        "vertex_labels": label_counts,
        "edge_labels": edge_counts,
        "core_laws_found": core_found,
        "core_laws_missing": list(CORE_LAW_CODES - set(core_found)),
    }
    with open(PROCESSED_DIR / "stats.json", "w") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print("RESULTS")
    print(f"{'=' * 60}")
    print(f"  Vertices: {len(vertices)}")
    for lbl, cnt in sorted(label_counts.items()):
        print(f"    {lbl}: {cnt}")
    print(f"  Edges: {len(edges)}")
    for lbl, cnt in sorted(edge_counts.items()):
        print(f"    {lbl}: {cnt}")
    print(f"  Law chunks (for Hologres): {len(law_chunks)}")
    print(f"\n  Core laws found: {len(core_found)}/{len(CORE_LAW_CODES)}")
    for c in sorted(core_found):
        print(f"    ✓ {c}: {CORE_LAW_NAMES.get(c, '')}")
    missing = CORE_LAW_CODES - set(core_found)
    if missing:
        print(f"  Missing ({len(missing)}):")
        for c in sorted(missing):
            print(f"    ✗ {c}: {CORE_LAW_NAMES.get(c, '')}")

    print(f"\n  Output:")
    print(f"    {PROCESSED_DIR / 'vertices.jsonl'}")
    print(f"    {PROCESSED_DIR / 'edges.jsonl'}")
    print(f"    {PROCESSED_DIR / 'law_chunks.jsonl'}")
    print(f"    {PROCESSED_DIR / 'stats.json'}")


if __name__ == "__main__":
    main()
