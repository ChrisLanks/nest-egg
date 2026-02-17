"""
Teller API integration service.

Teller provides bank account linking with a generous free tier:
- 100 accounts/month FREE in production
- $1/account after that (half the price of Plaid!)
- Simple, clean API
"""

import httpx
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.account import Account, TellerEnrollment, AccountSource, AccountType
from app.models.transaction import Transaction
from app.services.encryption_service import get_encryption_service
from app.utils.datetime_utils import utc_now


class TellerService:
    """Service for Teller API integration."""

    def __init__(self):
        """Initialize Teller client."""
        self.base_url = "https://api.teller.io" if settings.TELLER_ENV == "production" else "https://api.teller.io"
        self.app_id = settings.TELLER_APP_ID
        self.api_key = settings.TELLER_API_KEY
        self.encryption_service = get_encryption_service()

    async def _make_request(
        self, method: str, path: str, access_token: Optional[str] = None, **kwargs
    ) -> Dict:
        """Make authenticated request to Teller API."""
        headers = {
            "Content-Type": "application/json",
        }

        # Use access_token if provided, otherwise use app credentials
        auth = (access_token or self.api_key, "")

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                auth=auth,
                headers=headers,
                timeout=30.0,
                **kwargs,
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    async def get_enrollment_url(self, user_id: str) -> str:
        """
        Get Teller Connect URL for account linking.

        Returns URL that user should visit to connect their bank.
        """
        # In Teller, you generate application access tokens
        # For simplicity, return the Teller Connect URL
        return f"https://teller.io/connect/app/{self.app_id}"

    async def exchange_token(self, enrollment_id: str) -> Dict:
        """
        Exchange enrollment ID for access token.

        In Teller, the enrollment process returns an access_token directly.
        """
        # Get enrollment details
        enrollment = await self._make_request("GET", f"/enrollments/{enrollment_id}")
        return enrollment

    async def create_enrollment(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: UUID,
        enrollment_id: str,
        access_token: str,
        institution_name: Optional[str] = None,
    ) -> TellerEnrollment:
        """Create Teller enrollment record."""
        encrypted_token = self.encryption_service.encrypt(access_token)

        enrollment = TellerEnrollment(
            organization_id=organization_id,
            user_id=user_id,
            enrollment_id=enrollment_id,
            access_token=encrypted_token,
            institution_name=institution_name,
        )

        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)

        return enrollment

    async def sync_accounts(
        self, db: AsyncSession, enrollment: TellerEnrollment
    ) -> List[Account]:
        """Sync accounts from Teller."""
        access_token = enrollment.get_decrypted_access_token()

        # Get accounts from Teller
        accounts_data = await self._make_request("GET", "/accounts", access_token=access_token)

        synced_accounts = []

        for account_data in accounts_data:
            # Check if account already exists
            result = await db.execute(
                select(Account).where(
                    Account.teller_enrollment_id == enrollment.id,
                    Account.external_account_id == account_data["id"],
                )
            )
            account = result.scalar_one_or_none()

            if not account:
                # Create new account
                account = Account(
                    organization_id=enrollment.organization_id,
                    user_id=enrollment.user_id,
                    teller_enrollment_id=enrollment.id,
                    external_account_id=account_data["id"],
                    name=account_data.get("name", "Unknown Account"),
                    account_type=self._map_account_type(account_data.get("type")),
                    account_source=AccountSource.TELLER,
                    mask=account_data.get("last_four"),
                    institution_name=account_data.get("institution", {}).get("name"),
                    current_balance=Decimal(str(account_data.get("balance", {}).get("available", 0))),
                )
                db.add(account)
            else:
                # Update existing account balance
                balance = account_data.get("balance", {})
                account.current_balance = Decimal(str(balance.get("available", 0)))
                account.updated_at = utc_now()

            synced_accounts.append(account)

        await db.commit()

        # Update enrollment sync time
        enrollment.last_synced_at = utc_now()
        await db.commit()

        return synced_accounts

    async def sync_transactions(
        self, db: AsyncSession, account: Account, days_back: int = 90
    ) -> List[Transaction]:
        """Sync transactions from Teller."""
        enrollment = account.teller_enrollment
        if not enrollment:
            raise ValueError("Account does not have Teller enrollment")

        access_token = enrollment.get_decrypted_access_token()

        # Calculate date range
        from_date = (datetime.now().date() - timedelta(days=days_back)).isoformat()

        # Get transactions from Teller
        transactions_data = await self._make_request(
            "GET",
            f"/accounts/{account.external_account_id}/transactions",
            access_token=access_token,
            params={"from_date": from_date},
        )

        synced_transactions = []

        for txn_data in transactions_data:
            # Check if transaction already exists
            result = await db.execute(
                select(Transaction).where(
                    Transaction.account_id == account.id,
                    Transaction.external_transaction_id == txn_data["id"],
                )
            )
            existing_txn = result.scalar_one_or_none()

            if not existing_txn:
                # Extract category from Teller response (details.category)
                details = txn_data.get("details", {})
                teller_category = details.get("category") if isinstance(details, dict) else None

                # Extract counterparty/merchant name
                counterparty = details.get("counterparty", {}) if isinstance(details, dict) else {}
                merchant = counterparty.get("name") if isinstance(counterparty, dict) else None

                # Create transaction
                transaction = Transaction(
                    organization_id=account.organization_id,
                    account_id=account.id,
                    external_transaction_id=txn_data["id"],
                    date=datetime.fromisoformat(txn_data["date"].replace("Z", "+00:00")).date(),
                    amount=Decimal(str(txn_data["amount"])),
                    merchant_name=merchant or txn_data.get("description"),
                    description=txn_data.get("description"),
                    category_primary=teller_category,  # Teller provides single-level category
                    category_detailed=None,  # Teller doesn't have hierarchical categories
                    is_pending=txn_data.get("status") == "pending",
                    deduplication_hash=self._generate_dedup_hash(account.id, txn_data),
                )
                db.add(transaction)
                synced_transactions.append(transaction)

        await db.commit()
        return synced_transactions

    def _map_account_type(self, teller_type: Optional[str]) -> AccountType:
        """Map Teller account type to our AccountType enum."""
        mapping = {
            "depository": AccountType.CHECKING,
            "credit": AccountType.CREDIT_CARD,
            "loan": AccountType.LOAN,
            "investment": AccountType.BROKERAGE,
        }
        return mapping.get(teller_type, AccountType.OTHER)

    def _generate_dedup_hash(self, account_id: UUID, txn_data: Dict) -> str:
        """Generate deduplication hash for transaction."""
        import hashlib

        # Use same approach as Plaid for consistency
        components = [
            str(account_id),
            txn_data["date"],
            str(txn_data["amount"]),
            txn_data.get("description", ""),
        ]
        hash_input = "|".join(components)
        return hashlib.sha256(hash_input.encode()).hexdigest()


def get_teller_service() -> TellerService:
    """Get Teller service instance."""
    return TellerService()
