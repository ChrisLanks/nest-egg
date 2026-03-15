"""
Teller API integration service.

Teller provides bank account linking with a generous free tier:
- 100 accounts/month FREE in production
- $1/account after that (half the price of Plaid!)
- Simple, clean API
"""

import hashlib
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import redis_client
from app.models.account import Account, AccountSource, AccountType, TaxTreatment, TellerEnrollment
from app.models.transaction import Transaction
from app.services.circuit_breaker import CircuitOpenError, get_circuit_breaker
from app.services.encryption_service import get_encryption_service
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# TTL for sync idempotency locks (seconds)
_SYNC_LOCK_TTL = 300


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

        Calls are wrapped with a circuit breaker so that sustained Teller outages
        fail fast instead of making every user wait for a timeout.
        """
        cb = get_circuit_breaker()
        try:
            return await cb.call("teller", self._do_request, method, path, access_token, **kwargs)
        except CircuitOpenError:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Teller API is temporarily unavailable"
                    " (circuit breaker open). Try again later."
                ),
            )

    async def _do_request(
        self, method: str, path: str, access_token: Optional[str] = None, **kwargs
    ) -> Dict:
        """Execute the actual HTTP request to Teller (called via circuit breaker)."""
        headers = {
            "Content-Type": "application/json",
        }

        # Access token as Basic Auth username (empty password), per Teller spec
        auth = (access_token or self.api_key, "")

        # mTLS client certificate — required by Teller for all API calls
        # Supports combined PEM (cert_path only) or separate cert+key files
        cert = None
        if settings.TELLER_CERT_PATH:
            if settings.TELLER_KEY_PATH:
                cert = (settings.TELLER_CERT_PATH, settings.TELLER_KEY_PATH)
            else:
                cert = settings.TELLER_CERT_PATH

        try:
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
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Teller API error %s %s: %d %s",
                method,
                path,
                exc.response.status_code,
                exc.response.text[:200],
            )
            raise HTTPException(
                status_code=502,
                detail=f"Teller API error: {exc.response.status_code}",
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Teller API request failed %s %s: %s", method, path, exc)
            raise HTTPException(status_code=502, detail="Teller API unavailable") from exc

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
        """Sync accounts from Teller.

        This operation is atomic (all-or-nothing) using a database savepoint
        and protected by a Redis idempotency lock to prevent concurrent syncs.
        """
        # Acquire Redis idempotency lock
        lock_key = f"sync:teller:accounts:{enrollment.enrollment_id}"
        lock_acquired = False
        if redis_client:
            try:
                lock_acquired = await redis_client.set(lock_key, "1", nx=True, ex=_SYNC_LOCK_TTL)
                if not lock_acquired:
                    logger.info(
                        f"Account sync already in progress for Teller enrollment "
                        f"{enrollment.enrollment_id}, skipping"
                    )
                    return []
            except Exception as e:
                logger.warning(f"Redis lock acquisition failed, proceeding without lock: {e}")

        try:
            access_token = enrollment.get_decrypted_access_token()

            # Get accounts from Teller
            accounts_data = await self._make_request("GET", "/accounts", access_token=access_token)

            synced_accounts = []

            # Use a savepoint so the entire batch is all-or-nothing
            async with db.begin_nested():
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

                # Update enrollment sync time within the same savepoint
                enrollment.last_synced_at = utc_now()

            await db.commit()

            return synced_accounts
        finally:
            # Release Redis lock on completion (success or failure)
            if redis_client and lock_acquired:
                try:
                    await redis_client.delete(lock_key)
                except Exception as e:
                    logger.warning(f"Failed to release Redis lock {lock_key}: {e}")

    async def sync_transactions(
        self, db: AsyncSession, account: Account, days_back: int = 90
    ) -> List[Transaction]:
        """Sync transactions from Teller.

        This operation is atomic (all-or-nothing) using a database savepoint
        and protected by a Redis idempotency lock to prevent concurrent syncs.
        """
        # Use explicit async query instead of lazy-loaded relationship
        # to avoid MissingGreenlet error in async context
        enrollment_result = await db.execute(
            select(TellerEnrollment).where(TellerEnrollment.id == account.teller_enrollment_id)
        )
        enrollment = enrollment_result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Account does not have Teller enrollment")

        # Acquire Redis idempotency lock
        lock_key = f"sync:teller:transactions:{enrollment.enrollment_id}:{account.id}"
        lock_acquired = False
        if redis_client:
            try:
                lock_acquired = await redis_client.set(lock_key, "1", nx=True, ex=_SYNC_LOCK_TTL)
                if not lock_acquired:
                    logger.info(
                        f"Transaction sync already in progress for Teller account "
                        f"{account.id}, skipping"
                    )
                    return []
            except Exception as e:
                logger.warning(f"Redis lock acquisition failed, proceeding without lock: {e}")

        try:
            access_token = enrollment.get_decrypted_access_token()

            # Teller uses cursor-based pagination (from_id), not
            # date-based filtering.  Fetch all pages then filter
            # client-side by the requested date window.
            cutoff_date = utc_now().date() - timedelta(days=days_back)
            transactions_data: list = []
            from_id: Optional[str] = None

            while True:
                params: Dict[str, str] = {"count": "250"}
                if from_id:
                    params["from_id"] = from_id

                page = await self._make_request(
                    "GET",
                    f"/accounts/{account.external_account_id}" f"/transactions",
                    access_token=access_token,
                    params=params,
                )

                if not page:
                    break

                reached_cutoff = False
                for txn in page:
                    txn_date = datetime.fromisoformat(txn["date"].replace("Z", "+00:00")).date()
                    if txn_date < cutoff_date:
                        reached_cutoff = True
                        break
                    transactions_data.append(txn)

                # Stop if we hit the cutoff or got fewer than
                # a full page (no more data).
                if reached_cutoff or len(page) < 250:
                    break

                # Use the last transaction ID as cursor
                from_id = page[-1]["id"]

            synced_transactions = []

            # Pre-fetch existing external IDs for this account to avoid N+1 queries
            ext_result = await db.execute(
                select(Transaction.external_transaction_id).where(
                    Transaction.account_id == account.id,
                    Transaction.external_transaction_id.isnot(None),
                )
            )
            existing_ext_ids = {row[0] for row in ext_result.all()}

            # Use a savepoint so the entire batch is all-or-nothing
            async with db.begin_nested():
                for txn_data in transactions_data:
                    # Check if transaction already exists using pre-fetched set
                    if txn_data["id"] not in existing_ext_ids:
                        # Extract category from Teller response (details.category)
                        details = txn_data.get("details", {})
                        teller_category = (
                            details.get("category") if isinstance(details, dict) else None
                        )

                        # Extract counterparty/merchant name
                        counterparty = (
                            details.get("counterparty", {}) if isinstance(details, dict) else {}
                        )
                        merchant = (
                            counterparty.get("name") if isinstance(counterparty, dict) else None
                        )

                        # Create transaction
                        transaction = Transaction(
                            organization_id=account.organization_id,
                            account_id=account.id,
                            external_transaction_id=txn_data["id"],
                            date=datetime.fromisoformat(
                                txn_data["date"].replace("Z", "+00:00")
                            ).date(),
                            amount=Decimal(str(txn_data["amount"])),
                            merchant_name=merchant or txn_data.get("description"),
                            description=txn_data.get("description"),
                            # Teller provides single-level category
                            category_primary=teller_category,
                            category_detailed=None,  # Teller doesn't have hierarchical categories
                            is_pending=txn_data.get("status") == "pending",
                            deduplication_hash=self._generate_dedup_hash(account.id, txn_data),
                        )
                        db.add(transaction)
                        synced_transactions.append(transaction)

            await db.commit()
            return synced_transactions
        finally:
            # Release Redis lock on completion (success or failure)
            if redis_client and lock_acquired:
                try:
                    await redis_client.delete(lock_key)
                except Exception as e:
                    logger.warning(f"Failed to release Redis lock {lock_key}: {e}")

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
