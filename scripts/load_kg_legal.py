"""
scripts/load_kg_legal.py
Load pre-processed legal KG data from JSONL into TinkerGraph via Gremlin.
Reads: data/legal/processed/vertices.jsonl, data/legal/processed/edges.jsonl

Uses parameterized bindings for safety (no Groovy string escaping needed).
Uses __.V() for anonymous traversals in edge creation.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

VERTEX_FILE = Path("data/legal/processed/vertices.jsonl")
EDGE_FILE = Path("data/legal/processed/edges.jsonl")


def add_vertex(v: dict) -> None:
    """Add a single vertex using parameterized bindings."""
    label = v["label"]
    kg_id = v["id"]
    props = v.get("properties", {})

    # Build property chain dynamically with indexed binding names
    prop_chain = ".property('_kg_id', b0)"
    bindings = {"b0": kg_id}

    idx = 1
    for k, val in props.items():
        if val is None:
            continue
        # Convert non-string types to strings for TinkerGraph compatibility
        if isinstance(val, bool):
            val = str(val).lower()
        elif isinstance(val, (list, dict)):
            val = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, (int, float)):
            # Keep numeric types as-is
            pass
        else:
            val = str(val)
        bname = f"b{idx}"
        bindings[bname] = val
        prop_chain += f".property('{k}', {bname})"
        idx += 1

    query = f"g.addV('{label}'){prop_chain}"
    gremlin_submit(query, bindings)


def add_edge(e: dict) -> None:
    """Add a single edge using parameterized bindings and __.V() anonymous traversal."""
    label = e["label"]
    # Use __.V() for the anonymous traversal in .to()
    query = f"g.V().has('_kg_id', from_id).addE('{label}').to(__.V().has('_kg_id', to_id))"
    bindings = {"from_id": e["from"], "to_id": e["to"]}
    gremlin_submit(query, bindings)


def main():
    create_gremlin_client()

    # Create TinkerGraph index for fast lookups
    try:
        gremlin_submit("graph.createIndex('_kg_id', Vertex.class)")
        print("Created TinkerGraph index on _kg_id")
    except Exception as ex:
        print(f"Index note: {ex}")

    # Check if already loaded
    count = gremlin_submit("g.V().count()")[0]
    if count > 100:
        print(f"GDB already has {count} vertices. Skipping ingestion.")
        print("To reload, restart gremlin-server first.")
        close_gremlin_client()
        return

    # --- Load vertices ---
    print(f"Loading vertices from {VERTEX_FILE}...")
    vertices = [json.loads(line) for line in open(VERTEX_FILE)]
    total_v = len(vertices)
    t0 = time.time()
    failed_v = 0

    for i, v in enumerate(vertices):
        try:
            add_vertex(v)
        except Exception as ex:
            failed_v += 1
            if failed_v <= 10:
                print(f"\n  Vertex {v['id'][:60]} failed: {str(ex)[:100]}")
        if (i + 1) % 500 == 0 or i == total_v - 1:
            pct = (i + 1) * 100 // total_v
            print(f"\r  Vertices: {i + 1}/{total_v} ({pct}%)", end="", flush=True)

    v_time = time.time() - t0
    print(f"\n  Vertices done: {total_v - failed_v} loaded, {failed_v} failed in {v_time:.1f}s")

    # --- Load edges ---
    print(f"Loading edges from {EDGE_FILE}...")
    edges = [json.loads(line) for line in open(EDGE_FILE)]
    total_e = len(edges)
    t0 = time.time()
    failed_e = 0

    for i, e in enumerate(edges):
        try:
            add_edge(e)
        except Exception as ex:
            failed_e += 1
            if failed_e <= 10:
                print(f"\n  Edge {e['from'][:40]} -[{e['label']}]-> {e['to'][:40]} failed: {str(ex)[:80]}")
        if (i + 1) % 2000 == 0 or i == total_e - 1:
            pct = (i + 1) * 100 // total_e
            print(f"\r  Edges: {i + 1}/{total_e} ({pct}%)", end="", flush=True)

    e_time = time.time() - t0
    print(f"\n  Edges done: {total_e - failed_e} loaded, {failed_e} failed in {e_time:.1f}s")

    # --- Verify ---
    print("\nVerification:")
    result = gremlin_submit("g.V().groupCount().by(label)")
    print(f"  Vertex counts: {result}")
    total = gremlin_submit("g.V().count()")
    print(f"  Total vertices: {total}")
    edge_total = gremlin_submit("g.E().count()")
    print(f"  Total edges: {edge_total}")
    edge_labels = gremlin_submit("g.E().groupCount().by(label)")
    print(f"  Edge counts: {edge_labels}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
