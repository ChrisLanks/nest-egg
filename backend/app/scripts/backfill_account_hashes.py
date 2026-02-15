"""Backfill script to populate plaid_item_hash for existing accounts.

This script:
1. Calculates SHA256 hash from plaid_item_id + external_account_id
2. Updates accounts table with the hash
3. Sets is_primary_household_member TRUE for oldest user in each organization
"""

import asyncio
import hashlib
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models.account import Account
from app.models.user import User


def calculate_account_hash(plaid_item_id: str, external_account_id: str) -> str:
    """Generate deterministic hash for account identification.

    Args:
        plaid_item_id: Plaid item identifier
        external_account_id: Plaid account identifier

    Returns:
        SHA256 hash as hex string
    """
    content = f"{plaid_item_id}:{external_account_id}"
    return hashlib.sha256(content.encode()).hexdigest()


async def backfill_account_hashes(db: AsyncSession):
    """Backfill plaid_item_hash for all accounts that have Plaid data."""
    print("Backfilling account hashes...")

    # Get all accounts with Plaid data but no hash
    result = await db.execute(
        select(Account)
        .options(joinedload(Account.plaid_item))
        .where(
            Account.plaid_item_id.isnot(None),
            Account.external_account_id.isnot(None),
            Account.plaid_item_hash.is_(None)
        )
    )
    accounts = result.unique().scalars().all()

    if not accounts:
        print("No accounts need hash backfill.")
        return

    print(f"Found {len(accounts)} accounts to backfill")

    updated_count = 0
    for account in accounts:
        # Get the plaid item_id
        if not account.plaid_item or not account.plaid_item.item_id:
            print(f"⚠️  Skipping account {account.id} - no plaid item_id")
            continue

        # Calculate hash
        hash_value = calculate_account_hash(
            account.plaid_item.item_id,
            account.external_account_id
        )

        # Update account
        account.plaid_item_hash = hash_value
        updated_count += 1

        print(f"✓ Updated account {account.name} ({str(account.id)[:8]}...): {hash_value[:16]}...")

    await db.commit()
    print(f"\n✅ Successfully backfilled {updated_count} account hashes")


async def set_primary_household_members(db: AsyncSession):
    """Set is_primary_household_member TRUE for the oldest user in each organization."""
    print("\nSetting primary household members...")

    # Get all organizations
    result = await db.execute(
        select(User.organization_id, func.min(User.created_at).label('oldest_created_at'))
        .where(User.is_active == True)
        .group_by(User.organization_id)
    )
    org_oldest = result.all()

    if not org_oldest:
        print("No organizations found.")
        return

    print(f"Found {len(org_oldest)} organizations")

    updated_count = 0
    for org_id, oldest_created_at in org_oldest:
        # Find the oldest user in this org
        result = await db.execute(
            select(User).where(
                User.organization_id == org_id,
                User.created_at == oldest_created_at,
                User.is_active == True
            )
        )
        oldest_user = result.scalars().first()

        if oldest_user:
            oldest_user.is_primary_household_member = True
            updated_count += 1
            print(f"✓ Set {oldest_user.email} as primary for org {str(org_id)[:8]}...")

    await db.commit()
    print(f"\n✅ Set {updated_count} primary household members")


async def main():
    """Run backfill operations."""
    print("=" * 60)
    print("Account Hash & Primary Member Backfill Script")
    print("=" * 60)
    print()

    async for db in get_db():
        try:
            await backfill_account_hashes(db)
            await set_primary_household_members(db)
            print()
            print("=" * 60)
            print("✅ Backfill complete!")
            print("=" * 60)
        except Exception as e:
            print(f"\n❌ Error during backfill: {e}")
            raise
        finally:
            await db.close()
        break  # Only use first session


if __name__ == "__main__":
    asyncio.run(main())
