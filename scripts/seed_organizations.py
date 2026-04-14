"""
scripts/seed_organizations.py
Seed the Binh Duong province organizational hierarchy into GDB.
8 organizations + 8 positions with clearance levels.
Uses __.V() for anonymous traversals in .to() clauses.
"""
import sys

sys.path.insert(0, "backend")
from src.database import create_gremlin_client, gremlin_submit, close_gremlin_client

ORGS = [
    # (org_id, name, level, parent_org_id, province, district)
    ("ubnd_bd",       "UBND tinh Binh Duong",             "tinh",   None,        "Binh Duong", None),
    ("so_xd_bd",      "So Xay dung tinh Binh Duong",     "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_tnmt_bd",    "So TN&MT tinh Binh Duong",        "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_tp_bd",      "So Tu phap tinh Binh Duong",      "so",     "ubnd_bd",   "Binh Duong", None),
    ("so_nv_bd",      "So Noi vu tinh Binh Duong",       "so",     "ubnd_bd",   "Binh Duong", None),
    ("ubnd_tdi",      "UBND TP Thu Dau Mot",             "huyen",  "ubnd_bd",   "Binh Duong", "Thu Dau Mot"),
    ("phong_qldt_xd", "Phong QLDT - So Xay dung",       "phong",  "so_xd_bd",  "Binh Duong", None),
    ("phong_qldd",    "Phong QLDD - So TN&MT",           "phong",  "so_tnmt_bd","Binh Duong", None),
]

POSITIONS = [
    # (position_id, title, org_id, clearance_level)
    ("gd_so_xd",      "Giam doc So Xay dung",        "so_xd_bd",      3),
    ("pgd_so_xd",     "Pho Giam doc So Xay dung",    "so_xd_bd",      2),
    ("tp_qldt",       "Truong phong QLDT",            "phong_qldt_xd", 2),
    ("cv_qldt_1",     "Chuyen vien QLDT 1",           "phong_qldt_xd", 1),
    ("cv_qldt_2",     "Chuyen vien QLDT 2",           "phong_qldt_xd", 1),
    ("gd_so_tnmt",    "Giam doc So TN&MT",            "so_tnmt_bd",    3),
    ("tp_qldd",       "Truong phong QLDD",            "phong_qldd",    2),
    ("cv_qldd_1",     "Chuyen vien QLDD 1",           "phong_qldd",    1),
]


def main():
    create_gremlin_client()

    # Check if fully seeded
    org_count = gremlin_submit("g.V().hasLabel('Organization').count()")[0]
    pos_count = gremlin_submit("g.V().hasLabel('Position').count()")[0]
    if org_count >= len(ORGS) and pos_count >= len(POSITIONS):
        print(f"Already seeded: {org_count} orgs, {pos_count} positions. Skipping.")
        close_gremlin_client()
        return

    # Create organizations
    for org_id, name, level, parent_id, province, district in ORGS:
        bindings = {"oid": org_id, "n": name, "l": level, "p": province}
        prop_chain = ".property('org_id', oid).property('name', n).property('level', l).property('province', p)"
        if parent_id:
            bindings["pid"] = parent_id
            prop_chain += ".property('parent_org_id', pid)"
        if district:
            bindings["d"] = district
            prop_chain += ".property('district', d)"
        gremlin_submit(f"g.addV('Organization'){prop_chain}", bindings)

    print(f"Created {len(ORGS)} organizations")

    # Create PARENT_OF edges
    for org_id, _, _, parent_id, _, _ in ORGS:
        if parent_id:
            gremlin_submit(
                "g.V().has('Organization', 'org_id', pid)"
                ".addE('PARENT_OF')"
                ".to(__.V().has('Organization', 'org_id', cid))",
                {"pid": parent_id, "cid": org_id},
            )

    print("Created PARENT_OF edges")

    # Create positions + BELONGS_TO edges
    for pos_id, title, org_id, clearance in POSITIONS:
        gremlin_submit(
            "g.addV('Position')"
            ".property('position_id', pid)"
            ".property('title', t)"
            ".property('org_id', oid)"
            ".property('clearance_level', cl)",
            {"pid": pos_id, "t": title, "oid": org_id, "cl": clearance},
        )
        gremlin_submit(
            "g.V().has('Position', 'position_id', pid)"
            ".addE('BELONGS_TO')"
            ".to(__.V().has('Organization', 'org_id', oid))",
            {"pid": pos_id, "oid": org_id},
        )

    print(f"Created {len(POSITIONS)} positions with BELONGS_TO edges")

    # Verify
    result = gremlin_submit(
        "g.V().has(label, within('Organization','Position')).groupCount().by(label)"
    )
    print(f"Org/Position counts: {result}")

    close_gremlin_client()


if __name__ == "__main__":
    main()
