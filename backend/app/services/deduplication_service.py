"""Account deduplication service for multi-user households."""

import hashlib
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType, AccountSource


class DeduplicationService:
    """Service for detecting and handling duplicate accounts across household members."""

    @staticmethod
    def calculate_plaid_hash(plaid_item_id: str, external_account_id: str) -> str:
        """Generate deterministic hash for Plaid account identification.

        Args:
            plaid_item_id: Plaid item identifier
            external_account_id: Plaid account identifier

        Returns:
            SHA256 hash as hex string
        """
        content = f"plaid:{plaid_item_id}:{external_account_id}"
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def calculate_manual_account_hash(
        account_type: AccountType, institution_name: Optional[str], mask: Optional[str], name: str
    ) -> str:
        """Generate deterministic hash for manual account identification.

        Manual accounts are matched by:
        - Account type (e.g., checking, mortgage, property)
        - Institution name (normalized)
        - Mask (last 4 digits) if available
        - Account name (for properties, mortgages, etc.)

        Args:
            account_type: Type of account
            institution_name: Financial institution name
            mask: Last 4 digits of account
            name: Account name

        Returns:
            SHA256 hash as hex string
        """
        # Normalize strings for matching
        institution = (institution_name or "").lower().strip()
        account_mask = (mask or "").strip()
        account_name = name.lower().strip()

        # For accounts with mask (bank accounts, credit cards), use institution + type + mask
        if account_mask and institution:
            content = f"manual:{account_type.value}:{institution}:{account_mask}"
        # For properties and other unique assets, use type + name
        elif account_type in [AccountType.PROPERTY, AccountType.VEHICLE]:
            content = f"manual:{account_type.value}:{account_name}"
        # For loans/mortgages, use institution + type + name
        elif account_type in [AccountType.MORTGAGE, AccountType.LOAN, AccountType.STUDENT_LOAN]:
            content = f"manual:{account_type.value}:{institution}:{account_name}"
        else:
            # For other accounts, use type + institution + name
            content = f"manual:{account_type.value}:{institution}:{account_name}"

        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def calculate_account_hash_from_account(account: Account) -> Optional[str]:
        """Calculate appropriate hash for any account type.

        Args:
            account: Account object

        Returns:
            SHA256 hash or None if account cannot be hashed
        """
        # Plaid accounts
        if account.account_source == AccountSource.PLAID and account.external_account_id:
            # Use plaid_item.item_id if available, otherwise use plaid_item_id
            if account.plaid_item and hasattr(account.plaid_item, "item_id"):
                return DeduplicationService.calculate_plaid_hash(
                    account.plaid_item.item_id, account.external_account_id
                )
            # Fallback: use existing plaid_item_hash if set
            return account.plaid_item_hash

        # Manual accounts
        elif account.is_manual:
            return DeduplicationService.calculate_manual_account_hash(
                account.account_type, account.institution_name, account.mask, account.name
            )

        return None

    async def find_duplicate_accounts(self, db: AsyncSession, organization_id: UUID) -> dict:
        """Find accounts with same hash (same underlying account added by multiple users).

        Args:
            db: Database session
            organization_id: Organization ID to search within

        Returns:
            Dictionary mapping hash to list of account IDs
        """
        result = await db.execute(
            select(Account.plaid_item_hash, func.array_agg(Account.id))
            .where(Account.organization_id == organization_id, Account.plaid_item_hash.isnot(None))
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

    async def get_duplicate_groups(self, db: AsyncSession, organization_id: UUID) -> List[dict]:
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
            result = await db.execute(select(Account).where(Account.id.in_(account_ids)))
            accounts = result.scalars().all()

            groups.append(
                {
                    "hash": hash_value,
                    "count": len(accounts),
                    "accounts": [
                        {
                            "id": acc.id,
                            "name": acc.name,
                            "user_id": acc.user_id,
                            "institution_name": acc.institution_name,
                            "mask": acc.mask,
                        }
                        for acc in accounts
                    ],
                }
            )

        return groups


# Singleton instance
deduplication_service = DeduplicationService()
