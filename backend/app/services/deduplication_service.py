"""Account deduplication service for multi-user households."""

import hashlib
from typing import List
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class DeduplicationService:
    """Service for detecting and handling duplicate accounts across household members."""

    @staticmethod
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

    async def find_duplicate_accounts(
        self,
        db: AsyncSession,
        organization_id: UUID
    ) -> dict:
        """Find accounts with same hash (same underlying account added by multiple users).

        Args:
            db: Database session
            organization_id: Organization ID to search within

        Returns:
            Dictionary mapping hash to list of account IDs
        """
        result = await db.execute(
            select(Account.plaid_item_hash, func.array_agg(Account.id))
            .where(
                Account.organization_id == organization_id,
                Account.plaid_item_hash.isnot(None)
            )
            .group_by(Account.plaid_item_hash)
            .having(func.count(Account.id) > 1)
        )

        duplicates = {}
        for row in result:
            hash_value, account_ids = row
            duplicates[hash_value] = account_ids

        return duplicates

    def deduplicate_accounts(self, accounts: List[Account]) -> List[Account]:
        """Remove duplicate accounts, keeping first occurrence.

        Used for combined household views to show each real-world account only once,
        even if multiple household members have linked it.

        Args:
            accounts: List of accounts potentially containing duplicates

        Returns:
            Deduplicated list of accounts
        """
        seen_hashes = set()
        unique_accounts = []

        for account in accounts:
            # If account has no hash or hash not seen yet, include it
            if not account.plaid_item_hash or account.plaid_item_hash not in seen_hashes:
                unique_accounts.append(account)

                # Mark hash as seen
                if account.plaid_item_hash:
                    seen_hashes.add(account.plaid_item_hash)

        return unique_accounts

    async def get_duplicate_groups(
        self,
        db: AsyncSession,
        organization_id: UUID
    ) -> List[dict]:
        """Get detailed information about duplicate account groups.

        Args:
            db: Database session
            organization_id: Organization ID

        Returns:
            List of duplicate groups with account details
        """
        duplicates = await self.find_duplicate_accounts(db, organization_id)

        groups = []
        for hash_value, account_ids in duplicates.items():
            # Fetch full account objects
            result = await db.execute(
                select(Account).where(Account.id.in_(account_ids))
            )
            accounts = result.scalars().all()

            groups.append({
                'hash': hash_value,
                'count': len(accounts),
                'accounts': [
                    {
                        'id': acc.id,
                        'name': acc.name,
                        'user_id': acc.user_id,
                        'institution_name': acc.institution_name,
                        'mask': acc.mask,
                    }
                    for acc in accounts
                ]
            })

        return groups


# Singleton instance
deduplication_service = DeduplicationService()
