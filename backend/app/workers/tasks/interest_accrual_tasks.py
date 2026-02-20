"""Celery task for auto-accruing interest on CD and savings accounts."""

import hashlib
import logging
from calendar import monthrange
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, select

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.account import Account, AccountType, CompoundingFrequency
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

# Account types eligible for interest accrual
INTEREST_ACCOUNT_TYPES = {
    AccountType.CD,
    AccountType.SAVINGS,
    AccountType.MONEY_MARKET,
    AccountType.CHECKING,
}


@celery_app.task(name="accrue_account_interest")
def accrue_account_interest_task():
    """
    Auto-accrue interest for accounts with interest_rate and compounding_frequency set.
    Runs on the 1st of each month at 1am UTC.
    """
    import asyncio

    asyncio.run(_accrue_interest_async())


async def _accrue_interest_async():
    """Async implementation of monthly interest accrual."""
    today = date.today()
    first_of_month = today.replace(day=1)

    async with AsyncSessionLocal() as db:
        try:
            # Find all accounts that need interest accrual
            result = await db.execute(
                select(Account).where(
                    and_(
                        Account.account_type.in_(list(INTEREST_ACCOUNT_TYPES)),
                        Account.interest_rate.isnot(None),
                        Account.interest_rate > 0,
                        Account.compounding_frequency.isnot(None),
                        Account.is_active.is_(True),
                        Account.current_balance.isnot(None),
                        Account.current_balance > 0,
                    )
                )
            )
            accounts = list(result.scalars().all())

            logger.info(f"Interest accrual: checking {len(accounts)} eligible accounts")
            accrued_count = 0

            for account in accounts:
                # Skip if already accrued this month
                if account.last_interest_accrued_at is not None:
                    if account.last_interest_accrued_at >= first_of_month:
                        continue

                # Skip CDs that have matured
                if account.maturity_date and account.maturity_date < today:
                    if account.compounding_frequency != CompoundingFrequency.at_maturity:
                        continue

                # Calculate interest for this period
                interest = _calculate_interest(account, today)
                if interest <= Decimal("0.01"):
                    continue

                # Generate stable deduplication hash (account + year-month)
                period_key = f"interest:{account.id}:{today.year}-{today.month:02d}"
                dedup_hash = hashlib.sha256(period_key.encode()).hexdigest()[:64]

                # Check if transaction already exists (idempotency)
                existing = await db.execute(
                    select(Transaction).where(
                        and_(
                            Transaction.account_id == account.id,
                            Transaction.deduplication_hash == dedup_hash,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Create interest income transaction
                txn = Transaction(
                    organization_id=account.organization_id,
                    account_id=account.id,
                    date=first_of_month,
                    amount=interest,          # Positive = income
                    merchant_name=f"Interest — {account.name}",
                    category_primary="Interest Income",
                    is_pending=False,
                    is_transfer=False,
                    is_split=False,
                    description=(
                        f"Auto-accrued: {account.interest_rate}% APY "
                        f"({account.compounding_frequency.value})"
                    ),
                    deduplication_hash=dedup_hash,
                )
                db.add(txn)

                # Update account balance and last accrual date
                account.current_balance = (account.current_balance or Decimal("0")) + interest
                account.last_interest_accrued_at = first_of_month
                accrued_count += 1

            await db.commit()
            logger.info(f"Interest accrual complete: accrued interest for {accrued_count} accounts")

        except Exception:
            logger.exception("Interest accrual task failed")
            await db.rollback()
            raise


def _calculate_interest(account: Account, today: date) -> Decimal:
    """Calculate the interest amount for the current period."""
    balance = Decimal(str(account.current_balance))
    rate = Decimal(str(account.interest_rate)) / 100  # annual rate as decimal
    freq = account.compounding_frequency

    if freq == CompoundingFrequency.DAILY:
        days_in_month = monthrange(today.year, today.month)[1]
        return balance * rate / 365 * days_in_month

    if freq == CompoundingFrequency.MONTHLY:
        return balance * rate / 12

    if freq == CompoundingFrequency.QUARTERLY:
        # Only accrue in Mar, Jun, Sep, Dec (quarters)
        if today.month not in (3, 6, 9, 12):
            return Decimal("0")
        return balance * rate / 4

    if freq == CompoundingFrequency.AT_MATURITY:
        # Only accrue on maturity date's month
        if account.maturity_date is None:
            return Decimal("0")
        if today.month != account.maturity_date.month or today.year != account.maturity_date.year:
            return Decimal("0")
        # Calculate total interest from origination to maturity
        if account.origination_date:
            days = (account.maturity_date - account.origination_date).days
            return balance * rate * days / 365
        return balance * rate  # fallback: 1 year

    # Default: monthly
    return balance * rate / 12
