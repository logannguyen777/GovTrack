"""
scripts/create_gdb_schema.py
Create GDB vertex label schema and TinkerGraph index.
Run once before data ingestion.
"""
import sys

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

# All vertex labels (doc 30 + data-specific extras)
VERTEX_LABELS = [
    # Legal hierarchy (from actual corpus data)
    "Law", "Decree", "Circular", "Decision", "Resolution", "Ordinance", "Other",
    "Article", "Clause", "Point",
    # TTHC
    "TTHCSpec", "RequiredComponent", "ProcedureCategory",
    # Organization
    "Organization", "Position",
    # Templates
    "Template", "ClassificationLevel",
    # Case processing
    "Case", "Applicant", "Bundle", "Document", "ExtractedEntity",
    "Task", "Gap", "Citation",
    # Agent outputs
    "Opinion", "Summary", "Classification",
    "Draft", "PublishedDoc",
    # Audit
    "AuditEvent", "AgentStep",
    # Consultation
    "ConsultRequest",
]


def main():
    create_gremlin_client()

    # Create TinkerGraph index on _kg_id for O(1) vertex lookups during edge creation
    try:
        gremlin_submit("graph.createIndex('_kg_id', Vertex.class)")
        print("Created TinkerGraph index on _kg_id")
    except Exception as e:
        print(f"Index creation note: {e}")

    # Create sentinel vertices to register each label
    for label in VERTEX_LABELS:
        gremlin_submit(f"g.addV('{label}').property('_schema_sentinel', true)")

    print(f"Created {len(VERTEX_LABELS)} vertex labels")

    # Verify
    result = gremlin_submit("g.V().label().dedup()")
    print(f"Labels in graph: {sorted(result)}")

    # Clean up sentinels
    gremlin_submit("g.V().has('_schema_sentinel', true).drop()")
    print("Sentinel vertices removed")

    # Verify clean
    count = gremlin_submit("g.V().count()")
    print(f"Vertex count after cleanup: {count}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
