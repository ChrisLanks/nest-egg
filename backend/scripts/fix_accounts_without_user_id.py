"""
Fix accounts that don't have user_id set.

This script identifies accounts without user_id and either:
1. Assigns them to the organization's primary user (oldest user)
2. Or allows manual review before deletion
"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.account import Account
from app.models.user import User


async def find_accounts_without_user_id(db: AsyncSession):
    """Find all accounts that don't have user_id set."""
    result = await db.execute(
        select(Account)
        .where(Account.user_id.is_(None))
    )
    return result.scalars().all()


async def get_oldest_user_in_org(db: AsyncSession, org_id):
    """Get the oldest (first created) user in an organization."""
    result = await db.execute(
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.created_at.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def fix_accounts():
    """Main function to fix accounts without user_id."""
    async with AsyncSessionLocal() as db:
        # Find accounts without user_id
        accounts = await find_accounts_without_user_id(db)

        if not accounts:
            print("✓ No accounts found without user_id. Database is clean!")
            return

        print(f"\nFound {len(accounts)} accounts without user_id:")
        print("-" * 80)

        # Group by organization
        org_accounts = {}
        for account in accounts:
            if account.organization_id not in org_accounts:
                org_accounts[account.organization_id] = []
            org_accounts[account.organization_id].append(account)

        # Process each organization
        for org_id, org_accounts_list in org_accounts.items():
            print(f"\nOrganization: {org_id}")
            print(f"  Accounts without user_id: {len(org_accounts_list)}")

            # Get oldest user in this org
            oldest_user = await get_oldest_user_in_org(db, org_id)

            if not oldest_user:
                print(f"  ⚠️  No users found in this organization - cannot assign accounts")
                print(f"     You should delete these accounts manually")
                for acc in org_accounts_list:
                    print(f"     - {acc.name} (ID: {acc.id})")
                continue

            print(f"  Will assign to: {oldest_user.email} (ID: {oldest_user.id})")

            # List the accounts
            for acc in org_accounts_list:
                print(f"    - {acc.name} ({acc.account_type}) - Balance: {acc.current_balance}")

            # Ask for confirmation
            response = input("\n  Assign these accounts to this user? (y/n): ")

            if response.lower() == 'y':
                for acc in org_accounts_list:
                    acc.user_id = oldest_user.id
                await db.commit()
                print(f"  ✓ Assigned {len(org_accounts_list)} accounts to {oldest_user.email}")
            else:
                print(f"  Skipped {len(org_accounts_list)} accounts")

        print("\n" + "=" * 80)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(fix_accounts())
