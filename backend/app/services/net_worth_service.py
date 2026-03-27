"""Net worth history service for tracking and querying net worth over time."""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get as cache_get
from app.core.cache import setex as cache_setex
from app.models.account import Account, AccountType
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.services.dashboard_service import DashboardService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Account type -> snapshot category mapping for assets
_ASSET_CATEGORY_MAP: Dict[AccountType, str] = {
    AccountType.CHECKING: "cash_and_checking",
    AccountType.MONEY_MARKET: "cash_and_checking",
    AccountType.CASH: "cash_and_checking",
    AccountType.SAVINGS: "savings",
    AccountType.CD: "savings",
    AccountType.BROKERAGE: "investments",
    AccountType.CRYPTO: "investments",
    AccountType.PRIVATE_EQUITY: "investments",
    AccountType.PRIVATE_DEBT: "investments",
    AccountType.PRECIOUS_METALS: "investments",
    AccountType.BOND: "investments",
    AccountType.STOCK_OPTIONS: "investments",
    AccountType.ESPP: "investments",
    AccountType.COLLECTIBLES: "investments",
    AccountType.BUSINESS_EQUITY: "investments",
    AccountType.LIFE_INSURANCE_CASH_VALUE: "investments",
    AccountType.ANNUITY: "investments",
    AccountType.RETIREMENT_401K: "retirement",
    AccountType.RETIREMENT_403B: "retirement",
    AccountType.RETIREMENT_457B: "retirement",
    AccountType.RETIREMENT_IRA: "retirement",
    AccountType.RETIREMENT_ROTH: "retirement",
    AccountType.RETIREMENT_SEP_IRA: "retirement",
    AccountType.RETIREMENT_SIMPLE_IRA: "retirement",
    AccountType.RETIREMENT_529: "retirement",
    AccountType.HSA: "retirement",
    AccountType.PENSION: "retirement",
    AccountType.PROPERTY: "property",
    AccountType.VEHICLE: "vehicles",
    AccountType.MANUAL: "other_assets",
    AccountType.OTHER: "other_assets",
}

# Account type -> snapshot category mapping for debts
_DEBT_CATEGORY_MAP: Dict[AccountType, str] = {
    AccountType.CREDIT_CARD: "credit_cards",
    AccountType.LOAN: "loans",
    AccountType.MORTGAGE: "mortgages",
    AccountType.STUDENT_LOAN: "student_loans",
}


class NetWorthService:
    """Service for capturing and querying net worth history."""

    async def capture_snapshot(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        snapshot_date: Optional[date] = None,
    ) -> NetWorthSnapshot:
        """
        Capture a net worth snapshot for an organization (combined or per-user).

        Uses upsert (INSERT ... ON CONFLICT UPDATE) to ensure one snapshot per day.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            snapshot_date: Date for snapshot (defaults to today)

        Returns:
            Created or updated NetWorthSnapshot
        """
        if snapshot_date is None:
            snapshot_date = utc_now().date()

        # Fetch active accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        # Use DashboardService for consistent net worth calculation logic
        dashboard_svc = DashboardService(db)

        # Categorize accounts and compute breakdown
        category_totals = {
            "cash_and_checking": Decimal("0"),
            "savings": Decimal("0"),
            "investments": Decimal("0"),
            "retirement": Decimal("0"),
            "property": Decimal("0"),
            "vehicles": Decimal("0"),
            "other_assets": Decimal("0"),
            "credit_cards": Decimal("0"),
            "loans": Decimal("0"),
            "mortgages": Decimal("0"),
            "student_loans": Decimal("0"),
            "other_debts": Decimal("0"),
        }

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        per_account_breakdown = []

        for account in accounts:
            if not dashboard_svc._should_include_in_networth(account):
                continue

            balance = dashboard_svc._calculate_account_value(account)

            if account.account_type.is_asset:
                total_assets += balance
                category = _ASSET_CATEGORY_MAP.get(account.account_type, "other_assets")
                category_totals[category] += balance
            elif account.account_type.is_debt:
                abs_balance = abs(balance)
                total_liabilities += abs_balance
                category = _DEBT_CATEGORY_MAP.get(account.account_type, "other_debts")
                category_totals[category] += abs_balance

            per_account_breakdown.append(
                {
                    "account_id": str(account.id),
                    "name": account.name,
                    "type": account.account_type.value,
                    "balance": float(balance),
                    "institution": account.institution_name,
                }
            )

        total_net_worth = total_assets - total_liabilities

        values = {
            "organization_id": organization_id,
            "user_id": user_id,
            "snapshot_date": snapshot_date,
            "total_net_worth": total_net_worth,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "cash_and_checking": category_totals["cash_and_checking"],
            "savings": category_totals["savings"],
            "investments": category_totals["investments"],
            "retirement": category_totals["retirement"],
            "property": category_totals["property"],
            "vehicles": category_totals["vehicles"],
            "other_assets": category_totals["other_assets"],
            "credit_cards": category_totals["credit_cards"],
            "loans": category_totals["loans"],
            "mortgages": category_totals["mortgages"],
            "student_loans": category_totals["student_loans"],
            "other_debts": category_totals["other_debts"],
            "breakdown_json": per_account_breakdown,
        }

        # Upsert: insert or update if exists for this org/user/date.
        # Use the appropriate partial unique index depending on whether user_id is NULL.
        stmt = pg_insert(NetWorthSnapshot).values(**values)

        update_set = {
            "total_net_worth": stmt.excluded.total_net_worth,
            "total_assets": stmt.excluded.total_assets,
            "total_liabilities": stmt.excluded.total_liabilities,
            "cash_and_checking": stmt.excluded.cash_and_checking,
            "savings": stmt.excluded.savings,
            "investments": stmt.excluded.investments,
            "retirement": stmt.excluded.retirement,
            "property": stmt.excluded.property,
            "vehicles": stmt.excluded.vehicles,
            "other_assets": stmt.excluded.other_assets,
            "credit_cards": stmt.excluded.credit_cards,
            "loans": stmt.excluded.loans,
            "mortgages": stmt.excluded.mortgages,
            "student_loans": stmt.excluded.student_loans,
            "other_debts": stmt.excluded.other_debts,
            "breakdown_json": stmt.excluded.breakdown_json,
        }

        if user_id is not None:
            stmt = stmt.on_conflict_do_update(
                index_elements=["organization_id", "user_id", "snapshot_date"],
                index_where=text("user_id IS NOT NULL"),
                set_=update_set,
            )
        else:
            stmt = stmt.on_conflict_do_update(
                index_elements=["organization_id", "snapshot_date"],
                index_where=text("user_id IS NULL"),
                set_=update_set,
            )
        stmt = stmt.returning(NetWorthSnapshot)

        result = await db.execute(stmt)
        await db.commit()
        snapshot = result.scalar_one()

        user_label = user_id or "household"
        logger.info(
            "Captured net worth snapshot for org %s user %s on %s: $%s",
            organization_id,
            user_label,
            snapshot_date,
            total_net_worth,
        )
        return snapshot

    async def get_history(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        granularity: str = "daily",
    ) -> List[Dict]:
        """
        Get net worth history as a time series.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            start_date: Start date (inclusive)
            end_date: End date (inclusive, defaults to today)
            granularity: "daily", "weekly", or "monthly"

        Returns:
            List of dicts with date and net worth data
        """
        if end_date is None:
            end_date = utc_now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)

        # Check cache
        cache_key = (
            f"nw:history:{organization_id}:{user_id or 'household'}"
            f":{start_date}:{end_date}:{granularity}"
        )
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        conditions = [
            NetWorthSnapshot.organization_id == organization_id,
            NetWorthSnapshot.snapshot_date >= start_date,
            NetWorthSnapshot.snapshot_date <= end_date,
        ]

        if user_id is not None:
            conditions.append(NetWorthSnapshot.user_id == user_id)
        else:
            conditions.append(NetWorthSnapshot.user_id.is_(None))

        if granularity == "daily":
            query = (
                select(NetWorthSnapshot)
                .where(and_(*conditions))
                .order_by(NetWorthSnapshot.snapshot_date.asc())
            )
            result = await db.execute(query)
            snapshots = result.scalars().all()

            data = [
                {
                    "date": s.snapshot_date.isoformat(),
                    "total_net_worth": float(s.total_net_worth),
                    "total_assets": float(s.total_assets),
                    "total_liabilities": float(s.total_liabilities),
                    "cash_and_checking": float(s.cash_and_checking or 0),
                    "savings": float(s.savings or 0),
                    "investments": float(s.investments or 0),
                    "retirement": float(s.retirement or 0),
                    "property": float(s.property or 0),
                    "vehicles": float(s.vehicles or 0),
                    "other_assets": float(s.other_assets or 0),
                    "credit_cards": float(s.credit_cards or 0),
                    "loans": float(s.loans or 0),
                    "mortgages": float(s.mortgages or 0),
                    "student_loans": float(s.student_loans or 0),
                    "other_debts": float(s.other_debts or 0),
                }
                for s in snapshots
            ]
            await cache_setex(cache_key, 300, data)
            return data

        # For weekly/monthly, group by truncated date and take the last snapshot per period
        if granularity == "weekly":
            trunc_expr = func.date_trunc("week", NetWorthSnapshot.snapshot_date)
        else:  # monthly
            trunc_expr = func.date_trunc("month", NetWorthSnapshot.snapshot_date)

        # Subquery: get max snapshot_date per period
        subq = (
            select(
                func.max(NetWorthSnapshot.snapshot_date).label("max_date"),
                trunc_expr.label("period"),
            )
            .where(and_(*conditions))
            .group_by(trunc_expr)
            .subquery()
        )

        query = (
            select(NetWorthSnapshot)
            .join(
                subq,
                and_(
                    NetWorthSnapshot.snapshot_date == subq.c.max_date,
                    NetWorthSnapshot.organization_id == organization_id,
                    NetWorthSnapshot.user_id == user_id
                    if user_id
                    else NetWorthSnapshot.user_id.is_(None),
                ),
            )
            .order_by(NetWorthSnapshot.snapshot_date.asc())
        )

        result = await db.execute(query)
        snapshots = result.scalars().all()

        data = [
            {
                "date": s.snapshot_date.isoformat(),
                "total_net_worth": float(s.total_net_worth),
                "total_assets": float(s.total_assets),
                "total_liabilities": float(s.total_liabilities),
                "cash_and_checking": float(s.cash_and_checking or 0),
                "savings": float(s.savings or 0),
                "investments": float(s.investments or 0),
                "retirement": float(s.retirement or 0),
                "property": float(s.property or 0),
                "vehicles": float(s.vehicles or 0),
                "other_assets": float(s.other_assets or 0),
                "credit_cards": float(s.credit_cards or 0),
                "loans": float(s.loans or 0),
                "mortgages": float(s.mortgages or 0),
                "student_loans": float(s.student_loans or 0),
                "other_debts": float(s.other_debts or 0),
            }
            for s in snapshots
        ]
        await cache_setex(cache_key, 300, data)
        return data

    async def get_current_breakdown(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Dict:
        """
        Get the current net worth with full category breakdown.

        Computes live from accounts (not from snapshots) for real-time accuracy.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: User ID (None = combined household)

        Returns:
            Dict with net worth breakdown by category
        """
        # Check cache
        cache_key = f"nw:breakdown:{organization_id}:{user_id or 'household'}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached

        # Fetch active accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        dashboard_svc = DashboardService(db)

        category_totals = {
            "cash_and_checking": Decimal("0"),
            "savings": Decimal("0"),
            "investments": Decimal("0"),
            "retirement": Decimal("0"),
            "property": Decimal("0"),
            "vehicles": Decimal("0"),
            "other_assets": Decimal("0"),
            "credit_cards": Decimal("0"),
            "loans": Decimal("0"),
            "mortgages": Decimal("0"),
            "student_loans": Decimal("0"),
            "other_debts": Decimal("0"),
        }

        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        per_account = []

        for account in accounts:
            if not dashboard_svc._should_include_in_networth(account):
                continue

            balance = dashboard_svc._calculate_account_value(account)

            if account.account_type.is_asset:
                total_assets += balance
                category = _ASSET_CATEGORY_MAP.get(account.account_type, "other_assets")
                category_totals[category] += balance
            elif account.account_type.is_debt:
                abs_balance = abs(balance)
                total_liabilities += abs_balance
                category = _DEBT_CATEGORY_MAP.get(account.account_type, "other_debts")
                category_totals[category] += abs_balance

            per_account.append(
                {
                    "account_id": str(account.id),
                    "name": account.name,
                    "type": account.account_type.value,
                    "balance": float(balance),
                    "institution": account.institution_name,
                }
            )

        # Multi-currency: identify foreign currency accounts and convert to USD
        foreign_currency_accounts: Dict[str, Dict] = {}
        multi_currency = False
        for account in accounts:
            currency = getattr(account, "currency", "USD") or "USD"
            if currency.upper() != "USD":
                multi_currency = True
                from app.services.fx_service import get_rate
                rate = await get_rate(currency.upper(), "USD")
                balance_local = float(account.current_balance or 0)
                balance_usd = balance_local * rate
                if currency.upper() not in foreign_currency_accounts:
                    foreign_currency_accounts[currency.upper()] = {
                        "balance_local": 0.0,
                        "balance_usd": 0.0,
                        "rate": rate,
                    }
                foreign_currency_accounts[currency.upper()]["balance_local"] += balance_local
                foreign_currency_accounts[currency.upper()]["balance_usd"] += round(balance_usd, 2)

        result = {
            "total_net_worth": float(total_assets - total_liabilities),
            "total_assets": float(total_assets),
            "total_liabilities": float(total_liabilities),
            "categories": {k: float(v) for k, v in category_totals.items()},
            "accounts": per_account,
            "multi_currency": multi_currency,
            "foreign_currency_accounts": foreign_currency_accounts,
        }
        await cache_setex(cache_key, 300, result)
        return result


# Singleton instance
net_worth_service = NetWorthService()
