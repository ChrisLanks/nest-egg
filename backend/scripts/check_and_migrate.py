"""Check database state and run missing migrations."""
import asyncio
import subprocess
import sys

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

# Read DATABASE_URL from env file
import os
from pathlib import Path

env_file = Path(__file__).parent.parent / ".env"
db_url = None
for line in env_file.read_text().splitlines():
    if line.startswith("DATABASE_URL="):
        db_url = line.split("=", 1)[1].strip()
        break

if not db_url:
    print("ERROR: DATABASE_URL not found in .env")
    sys.exit(1)

print(f"Using DB: {db_url.split('@')[-1]}")

COLUMNS_TO_CHECK = [
    ("accounts", "iso_exercise_basis"),
    ("accounts", "form_8606_basis"),
    ("accounts", "after_tax_401k_balance"),
    ("accounts", "mega_backdoor_eligible"),
    ("accounts", "pension_cola_rate"),
    ("accounts", "pension_type"),
    ("users", "paycheck_frequency"),
    ("users", "state_of_residence"),
    ("users", "target_retirement_state"),
    ("users", "minimum_monthly_budget"),
]


async def check_db():
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        # Check alembic_version table
        r = await conn.execute(sa.text(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version')"
        ))
        has_alembic = r.scalar()
        print(f"alembic_version table exists: {has_alembic}")

        if has_alembic:
            r2 = await conn.execute(sa.text("SELECT version_num FROM alembic_version"))
            rows = r2.fetchall()
            print(f"Current versions: {[r[0] for r in rows]}")

        print("\nColumn check:")
        missing = []
        for table, col in COLUMNS_TO_CHECK:
            r3 = await conn.execute(sa.text(
                f"SELECT EXISTS(SELECT 1 FROM information_schema.columns "
                f"WHERE table_name='{table}' AND column_name='{col}')"
            ))
            exists = r3.scalar()
            status = "✓" if exists else "✗ MISSING"
            print(f"  {table}.{col}: {status}")
            if not exists:
                missing.append((table, col))

        return has_alembic, missing


async def main():
    has_alembic, missing = await check_db()

    if not missing:
        print("\n✓ All columns present — no migration needed.")
        return

    print(f"\n{len(missing)} columns missing. Need to run migrations.")

    if not has_alembic:
        print("\nNo alembic_version table — need to stamp the DB first.")
        print("The DB was created without going through Alembic.")
        print("\nStrategy: stamp at parents of missing migrations, then upgrade.")
        print("Parents: 3f8a1b2c9d4e (pre-iso_exercise_basis), c3d4e5f6a8b9 (pre-user-profile)")
        print("\nRunning: alembic stamp 3f8a1b2c9d4e c3d4e5f6a8b9")

        result = subprocess.run(
            ["alembic", "stamp", "3f8a1b2c9d4e", "c3d4e5f6a8b9"],
            capture_output=True, text=True
        )
        print(result.stdout)
        if result.returncode != 0:
            print("STDERR:", result.stderr)
            sys.exit(1)
        print("Stamp complete.")

    print("\nRunning: alembic upgrade heads")
    result = subprocess.run(
        ["alembic", "upgrade", "heads"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr)
        sys.exit(1)
    print("\n✓ Migration complete.")


asyncio.run(main())
