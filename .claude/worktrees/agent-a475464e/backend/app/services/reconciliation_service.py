"""Balance reconciliation service.

Compares bank-reported balances (from Plaid/Teller/MX sync) against
locally computed balances (sum of transactions) and reports discrepancies.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)


class ReconciliationResult:
    """Result of a balance reconciliation for a single account."""

    def __init__(
        self,
        account_id: UUID,
        account_name: str,
        bank_balance: Decimal,
        computed_balance: Decimal,
        discrepancy: Decimal,
        last_synced_at: Optional[datetime],
        transaction_count: int,
    ):
        self.account_id = account_id
        self.account_name = account_name
        self.bank_balance = bank_balance
        self.computed_balance = computed_balance
        self.discrepancy = discrepancy
        self.last_synced_at = last_synced_at
        self.transaction_count = transaction_count

    def to_dict(self) -> dict:
        return {
            "account_id": str(self.account_id),
            "account_name": self.account_name,
            "bank_balance": float(self.bank_balance),
            "computed_balance": float(self.computed_balance),
            "discrepancy": float(self.discrepancy),
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "transaction_count": self.transaction_count,
        }


class ReconciliationService:
    """Service for reconciling bank-reported vs locally computed balances."""

    async def reconcile_account(
        self,
        db: AsyncSession,
        account: Account,
    ) -> ReconciliationResult:
        """
        Reconcile a single account by comparing its bank-reported balance
        against the sum of its transactions.

        Args:
            db: Database session
            account: The account to reconcile (already verified)

        Returns:
            ReconciliationResult with balance comparison details
        """
        bank_balance = account.current_balance or Decimal("0")

        # Compute balance from sum of all transactions for this account.
        # Transaction.amount is positive for income, negative for expenses.
        result = await db.execute(
            select(
                func.coalesce(func.sum(Transaction.amount), Decimal("0")),
                func.count(Transaction.id),
            ).where(Transaction.account_id == account.id)
        )
        row = result.one()
        computed_balance = row[0]
        transaction_count = row[1]

        discrepancy = bank_balance - computed_balance

        # Use balance_as_of as the last sync timestamp, fall back to updated_at
        last_synced_at = account.balance_as_of or account.updated_at

        logger.info(
            "Reconciled account %s (%s): bank=$%s computed=$%s discrepancy=$%s txns=%d",
            account.id,
            account.name,
            bank_balance,
            computed_balance,
            discrepancy,
            transaction_count,
        )

        return ReconciliationResult(
            account_id=account.id,
            account_name=account.name,
            bank_balance=bank_balance,
            computed_balance=computed_balance,
            discrepancy=discrepancy,
            last_synced_at=last_synced_at,
            transaction_count=transaction_count,
        )


# Singleton instance
reconciliation_service = ReconciliationService()
