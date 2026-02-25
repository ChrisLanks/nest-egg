"""
Teller API integration service.

Teller provides bank account linking with a generous free tier:
- 100 accounts/month FREE in production
- $1/account after that (half the price of Plaid!)
- Simple, clean API
"""

import hashlib
import httpx
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.account import Account, TellerEnrollment, AccountSource, AccountType, TaxTreatment
from app.models.transaction import Transaction
from app.services.encryption_service import get_encryption_service
from app.utils.datetime_utils import utc_now


class TellerService:
    """Service for Teller API integration."""

    def __init__(self):
        """Initialize Teller client."""
        self.base_url = "https://api.teller.io"
        self.app_id = settings.TELLER_APP_ID
        self.api_key = settings.TELLER_API_KEY
        self.encryption_service = get_encryption_service()

    async def _make_request(
        self, method: str, path: str, access_token: Optional[str] = None, **kwargs
    ) -> Dict:
        """Make authenticated request to Teller API.

        Teller requires mTLS (mutual TLS) — the client certificate authenticates
        the application, while the access token identifies the user's enrollment.
        """
        headers = {
            "Content-Type": "application/json",
        }

        # Access token as Basic Auth username (empty password), per Teller spec
        auth = (access_token or self.api_key, "")

        # mTLS client certificate — required by Teller for all API calls
        cert = settings.TELLER_CERT_PATH if settings.TELLER_CERT_PATH else None

        async with httpx.AsyncClient(cert=cert) as client:
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
        encrypted_token = self.encryption_service.encrypt_token(access_token)

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

    async def sync_accounts(self, db: AsyncSession, enrollment: TellerEnrollment) -> List[Account]:
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
                # Use ledger balance for accuracy (especially for credit cards/loans),
                # falling back to current, then available
                balance_data = account_data.get("balance", {})
                balance_value = (
                    balance_data.get("ledger")
                    or balance_data.get("current")
                    or balance_data.get("available", 0)
                )
                mapped_type, mapped_tax = self._map_account_type(
                    account_data.get("type"), account_data.get("subtype")
                )
                account = Account(
                    organization_id=enrollment.organization_id,
                    user_id=enrollment.user_id,
                    teller_enrollment_id=enrollment.id,
                    external_account_id=account_data["id"],
                    name=account_data.get("name", "Unknown Account"),
                    account_type=mapped_type,
                    tax_treatment=mapped_tax,
                    account_source=AccountSource.TELLER,
                    mask=account_data.get("last_four"),
                    institution_name=account_data.get("institution", {}).get("name"),
                    current_balance=Decimal(str(balance_value)),
                )
                db.add(account)
            else:
                # Update existing account balance
                # Use ledger balance for accuracy (especially for credit cards/loans),
                # falling back to current, then available
                balance = account_data.get("balance", {})
                balance_value = (
                    balance.get("ledger")
                    or balance.get("current")
                    or balance.get("available", 0)
                )
                account.current_balance = Decimal(str(balance_value))
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
        # Use explicit async query instead of lazy-loaded relationship
        # to avoid MissingGreenlet error in async context
        enrollment_result = await db.execute(
            select(TellerEnrollment).where(TellerEnrollment.id == account.teller_enrollment_id)
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Account does not have Teller enrollment")

        access_token = enrollment.get_decrypted_access_token()

        # Calculate date range
        from_date = (utc_now().date() - timedelta(days=days_back)).isoformat()

        # Get transactions from Teller
        transactions_data = await self._make_request(
            "GET",
            f"/accounts/{account.external_account_id}/transactions",
            access_token=access_token,
            params={"from_date": from_date},
        )

        synced_transactions = []

        # Pre-fetch existing external IDs for this account to avoid N+1 queries
        ext_result = await db.execute(
            select(Transaction.external_transaction_id).where(
                Transaction.account_id == account.id,
                Transaction.external_transaction_id.isnot(None),
            )
        )
        existing_ext_ids = {row[0] for row in ext_result.all()}

        for txn_data in transactions_data:
            # Check if transaction already exists using pre-fetched set
            if txn_data["id"] not in existing_ext_ids:
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

    def _map_account_type(
        self, teller_type: Optional[str], teller_subtype: Optional[str] = None
    ) -> tuple[AccountType, TaxTreatment | None]:
        """Map Teller account type + subtype to our AccountType enum and TaxTreatment.

        Teller types: depository, credit, loan, investment
        Teller subtypes: checking, savings, money_market, cd, brokerage, ira, etc.
        """
        if teller_type == "depository":
            if teller_subtype in ("savings", "money_market", "cd"):
                return AccountType.SAVINGS, None
            return AccountType.CHECKING, None
        elif teller_type == "credit":
            return AccountType.CREDIT_CARD, None
        elif teller_type == "loan":
            return AccountType.LOAN, None
        elif teller_type == "investment":
            if teller_subtype in ("ira", "traditional_ira"):
                return AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX
            elif teller_subtype == "sep_ira":
                return AccountType.RETIREMENT_SEP_IRA, TaxTreatment.PRE_TAX
            elif teller_subtype == "simple_ira":
                return AccountType.RETIREMENT_SIMPLE_IRA, TaxTreatment.PRE_TAX
            elif teller_subtype in ("roth", "roth_ira"):
                return AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH
            elif teller_subtype == "roth_401k":
                return AccountType.RETIREMENT_401K, TaxTreatment.ROTH
            elif teller_subtype == "roth_403b":
                return AccountType.RETIREMENT_403B, TaxTreatment.ROTH
            elif teller_subtype == "401k":
                return AccountType.RETIREMENT_401K, TaxTreatment.PRE_TAX
            elif teller_subtype == "403b":
                return AccountType.RETIREMENT_403B, TaxTreatment.PRE_TAX
            elif teller_subtype == "457b":
                return AccountType.RETIREMENT_457B, TaxTreatment.PRE_TAX
            elif teller_subtype == "hsa":
                return AccountType.HSA, TaxTreatment.TAX_FREE
            return AccountType.BROKERAGE, TaxTreatment.TAXABLE
        return AccountType.OTHER, None

    def _generate_dedup_hash(self, account_id: UUID, txn_data: Dict) -> str:
        """Generate deduplication hash for transaction."""
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
