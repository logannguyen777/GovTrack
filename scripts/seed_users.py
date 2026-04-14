"""
scripts/seed_users.py
Create 6 test users with varying roles and clearance levels.
Requires PostgreSQL tables to exist (run init.sql first).
"""
import asyncio
import hashlib
import sys
import uuid

sys.path.insert(0, "backend")
from src.database import create_pg_pool, get_pg_pool, close_pg_pool

USERS = [
    # (username, full_name, role, clearance, departments[])
    ("admin",   "Quan Tri Vien",        "admin",         4, ["ubnd_bd"]),
    ("gd_xd",   "Nguyen Van Giam Doc",  "leader",        3, ["so_xd_bd"]),
    ("tp_qldt",  "Tran Thi Truong Phong","leader",        2, ["phong_qldt_xd"]),
    ("cv_qldt",  "Le Van Chuyen Vien",   "officer",       1, ["phong_qldt_xd"]),
    ("cv_tnmt",  "Pham Thi Moi Truong",  "officer",       1, ["phong_qldd"]),
    ("public",   "Cong Dan Thu Nghiem",   "public_viewer", 0, []),
]


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


async def main():
    await create_pg_pool()
    pool = get_pg_pool()

    async with pool.acquire() as conn:
        for username, full_name, role, clearance, depts in USERS:
            await conn.execute(
                """
                INSERT INTO users (id, username, full_name, email, password_hash,
                    role, clearance_level, departments)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (username) DO NOTHING
                """,
                uuid.uuid4(),
                username,
                full_name,
                f"{username}@govflow.test",
                hash_password(f"{username}123"),
                role,
                clearance,
                depts,
            )
            print(f"  Created user: {username} (role={role}, clearance={clearance})")

    # Verify
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT username, role, clearance_level FROM users ORDER BY clearance_level DESC"
        )
        print(f"\nVerification ({len(rows)} users):")
        for r in rows:
            print(f"  {r['username']:12s} role={r['role']:15s} clearance={r['clearance_level']}")

    await close_pg_pool()


if __name__ == "__main__":
    asyncio.run(main())
