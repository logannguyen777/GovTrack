"""
scripts/create_gdb_edges.py
Document canonical GDB edge types.
TinkerGraph creates edges implicitly on first use -- this script is for reference.
"""

EDGE_TYPES = [
    # Legal hierarchy
    ("CONTAINS",              "Hierarchical containment (Law->Article, Article->Clause, Bundle->Document)"),
    ("HAS_CLAUSE",            "Article contains Clause (from legal corpus)"),
    ("HAS_POINT",             "Clause contains Point (from legal corpus)"),
    # Legal relationships
    ("AMENDED_BY",            "Legal amendment (Law->Law, newer amends older)"),
    ("SUPERSEDED_BY",         "Legal supersession (Law->Law)"),
    ("REPEALED_BY",           "Legal repeal (Law->Law)"),
    ("PARTIALLY_REPEALED_BY", "Partial repeal (Law->Law)"),
    ("SUSPENDED_BY",          "Legal suspension (Law->Law)"),
    ("PARTIALLY_SUSPENDED_BY","Partial suspension (Law->Law)"),
    ("REFERENCES",            "Cross-reference between legal articles (Article->Article)"),
    ("BASED_ON",              "Document based on legal basis (from corpus)"),
    ("DETAILED_BY",           "Law detailed by implementing decree/circular"),
    ("DETAILS",               "Implementing doc details a law"),
    ("RELATED",               "General relationship between legal documents"),
    # TTHC
    ("REQUIRES",              "TTHC requires a component (TTHCSpec->RequiredComponent)"),
    ("GOVERNED_BY",           "TTHC governed by legal article (TTHCSpec->Article)"),
    ("AUTHORIZED_FOR",        "Position authorized for TTHC (Position->TTHCSpec)"),
    # Organization
    ("PARENT_OF",             "Hierarchical parent (Org->Org, Category->Category)"),
    ("REPORTS_TO",            "Reporting line (Position->Position)"),
    ("BELONGS_TO",            "Membership (Position->Org, Case->Category)"),
    # Case processing
    ("SUBMITTED_BY",          "Case submitted by applicant"),
    ("HAS_BUNDLE",            "Case has document bundle"),
    ("EXTRACTED",             "Document has extracted entity"),
    ("MATCHES_TTHC",          "Case matched to TTHC spec"),
    ("HAS_GAP",               "Case has identified gap"),
    ("GAP_FOR",               "Gap relates to required component"),
    ("CITES",                 "Output cites a legal reference"),
    ("SATISFIES",             "Document satisfies requirement"),
    ("DEPENDS_ON",            "Task depends on another task (DAG)"),
    ("ASSIGNED_TO",           "Task assigned to agent step"),
    ("CONSULTED",             "Case has consultation request"),
    ("HAS_OPINION",           "Case has agent opinion"),
    ("HAS_DECISION",          "Case has decision"),
    ("PUBLISHED_AS",          "Case published as official document"),
    ("AUDITS",                "Audit event targets entity"),
    ("PROCESSED_BY",          "Case processed by agent step"),
    ("CLASSIFIED_AS",         "Case classified at security level"),
    ("HAS_DRAFT",             "Case has draft document"),
    ("RESULT_TEMPLATE",       "Draft uses ND30 template"),
]


def main():
    print(f"GovFlow Canonical Edge Types ({len(EDGE_TYPES)} total)")
    print("=" * 70)
    for label, desc in EDGE_TYPES:
        print(f"  {label:25s} -- {desc}")


if __name__ == "__main__":
    main()
