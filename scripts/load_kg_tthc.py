"""
scripts/load_kg_tthc.py
Load TTHC procedure specs into GDB from pre-processed JSONL.
Reads: data/tthc_specs/kg_vertices.jsonl, data/tthc_specs/kg_edges.jsonl

Small dataset (~37 vertices, ~84 edges), so individual submits are fine.
Must run AFTER load_kg_legal.py (GOVERNED_BY edges target Article vertices).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

VERTEX_FILE = Path("data/tthc_specs/kg_vertices.jsonl")
EDGE_FILE = Path("data/tthc_specs/kg_edges.jsonl")


def escape_groovy(s: str) -> str:
    if not isinstance(s, str):
        return str(s)
    return (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def groovy_literal(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, list):
        return f"'{escape_groovy(json.dumps(val, ensure_ascii=False))}'"
    return f"'{escape_groovy(str(val))}'"


def main():
    create_gremlin_client()

    # Check if TTHC data already loaded
    existing = gremlin_submit("g.V().hasLabel('TTHCSpec').count()")[0]
    if existing > 0:
        print(f"Already {existing} TTHCSpec vertices in GDB. Skipping.")
        close_gremlin_client()
        return

    # --- Load vertices ---
    print(f"Loading TTHC vertices from {VERTEX_FILE}...")
    v_count = 0
    for line in open(VERTEX_FILE):
        v = json.loads(line.strip())
        label = v["label"]
        bindings = {"b0": v["id"]}
        prop_chain = ".property('_kg_id', b0)"
        # TTHC-related vertices are public information — classification=0
        # so PUBLIC_SESSION (PermittedGremlinClient) can read them.
        if label in ("TTHCSpec", "RequiredComponent", "ProcedureCategory", "Organization"):
            prop_chain += ".property('classification', 0)"
        idx = 1
        for k, val in v.get("properties", {}).items():
            if val is None:
                continue
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            elif isinstance(val, bool):
                val = str(val).lower()
            bname = f"b{idx}"
            bindings[bname] = val
            prop_chain += f".property('{k}', {bname})"
            idx += 1
        gremlin_submit(f"g.addV('{label}'){prop_chain}", bindings)
        v_count += 1
    print(f"  Loaded {v_count} TTHC vertices")

    # --- Load edges ---
    print(f"Loading TTHC edges from {EDGE_FILE}...")
    e_count = 0
    e_skip = 0
    for line in open(EDGE_FILE):
        e = json.loads(line.strip())
        from_id = escape_groovy(e["from"])
        to_id = escape_groovy(e["to"])
        label = escape_groovy(e["label"])

        # Check that both endpoints exist (GOVERNED_BY targets may be missing)
        try:
            from_exists = gremlin_submit("g.V().has('_kg_id', fid).count()", {"fid": from_id})[0]
            to_exists = gremlin_submit("g.V().has('_kg_id', tid).count()", {"tid": to_id})[0]
            if from_exists == 0 or to_exists == 0:
                e_skip += 1
                continue

            gremlin_submit(
                f"g.V().has('_kg_id', from_id)"
                f".addE('{label}')"
                f".to(__.V().has('_kg_id', to_id))",
                {"from_id": from_id, "to_id": to_id},
            )
            e_count += 1
        except Exception as ex:
            print(f"  Edge {from_id} -[{label}]-> {to_id} failed: {ex}")
            e_skip += 1

    print(f"  Loaded {e_count} edges, skipped {e_skip}")

    # --- Verify ---
    print("\nTTHC Verification:")
    for label in ["TTHCSpec", "RequiredComponent", "ProcedureCategory"]:
        count = gremlin_submit(f"g.V().hasLabel('{label}').count()")[0]
        print(f"  {label}: {count}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
