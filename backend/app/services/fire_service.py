"""FIRE (Financial Independence, Retire Early) metrics service."""

import logging
import math
from datetime import timedelta
from decimal import Decimal
from typing import Dict, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import FIRE
from app.models.account import Account, AccountType
from app.services.dashboard_service import DashboardService
from app.utils.account_type_groups import ALL_RETIREMENT_TYPES
from app.utils.datetime_utils import utc_now

logger = logging.getLogger(__name__)

# Account types considered "investable" for FIRE calculations:
# brokerage + all retirement account types
INVESTABLE_ACCOUNT_TYPES: frozenset[AccountType] = (
    frozenset({AccountType.BROKERAGE}) | ALL_RETIREMENT_TYPES
)


class FireService:
    """Service for calculating FIRE (Financial Independence) metrics."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._dashboard_svc = DashboardService(db)

    async def _get_investable_assets(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Decimal:
        """
        Calculate total investable assets (brokerage + retirement accounts).

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)

        Returns:
            Total investable asset value
        """
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type.in_(INVESTABLE_ACCOUNT_TYPES),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await self.db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        total = Decimal("0")
        for account in accounts:
            if self._dashboard_svc._should_include_in_networth(account):
                total += self._dashboard_svc._calculate_account_value(account)

        return total

    async def _get_trailing_annual_spending(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Decimal:
        """
        Calculate trailing 12-month spending.

        Uses DashboardService pattern for querying expense transactions.

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)

        Returns:
            Total spending over trailing 12 months (positive number)
        """
        end_date = utc_now().date()
        start_date = end_date - timedelta(days=365)

        # Get account IDs if filtering by user
        account_ids = None
        if user_id is not None:
            conditions = [
                Account.organization_id == organization_id,
                Account.user_id == user_id,
                Account.is_active.is_(True),
            ]
            result = await self.db.execute(select(Account.id).where(and_(*conditions)))
            account_ids = [row[0] for row in result.all()]

        spending = await self._dashboard_svc.get_monthly_spending(
            str(organization_id), start_date, end_date, account_ids
        )
        return spending

    async def _get_trailing_annual_income(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Decimal:
        """
        Calculate trailing 12-month income.

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)

        Returns:
            Total income over trailing 12 months
        """
        end_date = utc_now().date()
        start_date = end_date - timedelta(days=365)

        account_ids = None
        if user_id is not None:
            conditions = [
                Account.organization_id == organization_id,
                Account.user_id == user_id,
                Account.is_active.is_(True),
            ]
            result = await self.db.execute(select(Account.id).where(and_(*conditions)))
            account_ids = [row[0] for row in result.all()]

        income = await self._dashboard_svc.get_monthly_income(
            str(organization_id), start_date, end_date, account_ids
        )
        return income

    async def calculate_fi_ratio(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        withdrawal_rate: float = 0.04,
    ) -> Dict:
        """
        Calculate Financial Independence ratio.

        FI Ratio = investable_assets / (annual_expenses / withdrawal_rate)
        A ratio of 1.0 means you are financially independent.

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            withdrawal_rate: Safe withdrawal rate (default 4%)

        Returns:
            Dict with fi_ratio, investable_assets, annual_expenses, fi_number
        """
        investable = await self._get_investable_assets(organization_id, user_id)
        annual_expenses = await self._get_trailing_annual_spending(organization_id, user_id)

        fi_number = float(annual_expenses) / withdrawal_rate
        fi_ratio = float(investable) / fi_number if fi_number > 0 else 0.0

        return {
            "fi_ratio": round(fi_ratio, 4),
            "investable_assets": float(investable),
            "annual_expenses": float(annual_expenses),
            "fi_number": float(fi_number),
        }

    async def calculate_savings_rate(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        months: int = 12,
    ) -> Dict:
        """
        Calculate savings rate over the specified period.

        Savings Rate = (income - spending) / income

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            months: Number of trailing months (default 12)

        Returns:
            Dict with savings_rate, income, spending, savings
        """
        end_date = utc_now().date()
        start_date = end_date - relativedelta(months=months)

        account_ids = None
        if user_id is not None:
            conditions = [
                Account.organization_id == organization_id,
                Account.user_id == user_id,
                Account.is_active.is_(True),
            ]
            result = await self.db.execute(select(Account.id).where(and_(*conditions)))
            account_ids = [row[0] for row in result.all()]

        spending, income = await self._dashboard_svc.get_spending_and_income(
            str(organization_id), start_date, end_date, account_ids
        )

        savings = income - spending
        savings_rate = float(savings / income) if income > 0 else 0.0

        return {
            "savings_rate": round(savings_rate, 4),
            "income": float(income),
            "spending": float(spending),
            "savings": float(savings),
            "months": months,
        }

    async def calculate_years_to_fi(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        withdrawal_rate: float = 0.04,
        expected_return: float = 0.07,
    ) -> Dict:
        """
        Calculate estimated years to financial independence.

        Uses the compound growth formula:
        years = ln(
            (FI_number * r + annual_savings)
            / (current_portfolio * r + annual_savings)
        ) / ln(1 + r)

        Where r = expected_return - inflation (assume 3% inflation).

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            withdrawal_rate: Safe withdrawal rate (default 4%)
            expected_return: Expected annual return (default 7%)

        Returns:
            Dict with years_to_fi and supporting metrics
        """
        investable = await self._get_investable_assets(organization_id, user_id)
        annual_expenses = await self._get_trailing_annual_spending(organization_id, user_id)
        annual_income = await self._get_trailing_annual_income(organization_id, user_id)

        annual_savings = float(annual_income - annual_expenses)
        if withdrawal_rate <= 0:
            return {
                "years_to_fi": None,
                "fi_number": None,
                "investable_assets": float(investable),
                "annual_savings": annual_savings,
                "withdrawal_rate": withdrawal_rate,
                "expected_return": expected_return,
                "already_fi": False,
            }
        fi_number = float(annual_expenses) / withdrawal_rate
        current = float(investable)

        # Already FI
        if current >= fi_number:
            return {
                "years_to_fi": 0.0,
                "fi_number": fi_number,
                "investable_assets": current,
                "annual_savings": annual_savings,
                "withdrawal_rate": withdrawal_rate,
                "expected_return": expected_return,
                "already_fi": True,
            }

        # Cannot reach FI with negative savings and no portfolio
        real_return = expected_return - FIRE.DEFAULT_INFLATION  # Assume 3% inflation
        if real_return <= 0 or (annual_savings <= 0 and current <= 0):
            return {
                "years_to_fi": None,
                "fi_number": fi_number,
                "investable_assets": current,
                "annual_savings": annual_savings,
                "withdrawal_rate": withdrawal_rate,
                "expected_return": expected_return,
                "already_fi": False,
            }

        # Compound growth formula with regular contributions
        # FV = PV * (1+r)^n + PMT * ((1+r)^n - 1) / r
        # Solve for n: iterative approach for accuracy
        r = real_return
        target = fi_number

        if annual_savings <= 0:
            # Only portfolio growth, no contributions
            if current <= 0 or target <= 0:
                years = None
            else:
                years = math.log(target / current) / math.log(1 + r)
        else:
            # With contributions: solve FV = PV*(1+r)^n + C*((1+r)^n - 1)/r = target
            # (PV*r + C) * (1+r)^n = target*r + C
            numerator = target * r + annual_savings
            denominator = current * r + annual_savings
            if denominator <= 0 or numerator <= 0:
                years = None
            else:
                years = math.log(numerator / denominator) / math.log(1 + r)

        return {
            "years_to_fi": round(years, 1) if years is not None else None,
            "fi_number": round(fi_number, 2),
            "investable_assets": current,
            "annual_savings": annual_savings,
            "withdrawal_rate": withdrawal_rate,
            "expected_return": expected_return,
            "already_fi": False,
        }

    async def calculate_coast_fi(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        retirement_age: int = 65,
        expected_return: float = 0.07,
        withdrawal_rate: float = 0.04,
    ) -> Dict:
        """
        Calculate Coast FI number.

        Coast FI = the portfolio value needed today such that, with zero additional
        contributions, investment growth alone reaches your FI number by retirement age.

        Coast FI = FI_number / (1 + real_return) ^ years_until_retirement

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            retirement_age: Target retirement age (default 65)
            expected_return: Expected annual return (default 7%)
            withdrawal_rate: Safe withdrawal rate (default 4%)

        Returns:
            Dict with coast_fi_number and supporting metrics
        """
        investable = await self._get_investable_assets(organization_id, user_id)
        annual_expenses = await self._get_trailing_annual_spending(organization_id, user_id)

        fi_number = float(annual_expenses) / withdrawal_rate

        # Estimate years until retirement (assume user is ~30 if we can't determine age)
        # In a production system, this would come from the user's profile/birth date
        years_until_retirement = max(retirement_age - 30, 1)

        real_return = expected_return - FIRE.DEFAULT_INFLATION  # Assume 3% inflation

        # Coast FI = FI number discounted back to present
        coast_fi = fi_number / ((1 + real_return) ** years_until_retirement)

        # Are they already past Coast FI?
        is_coast_fi = float(investable) >= coast_fi

        return {
            "coast_fi_number": round(coast_fi, 2),
            "fi_number": fi_number,
            "investable_assets": float(investable),
            "is_coast_fi": is_coast_fi,
            "retirement_age": retirement_age,
            "years_until_retirement": years_until_retirement,
            "expected_return": expected_return,
        }

    async def get_fire_dashboard(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        withdrawal_rate: float = 0.04,
        expected_return: float = 0.07,
        retirement_age: int = 65,
    ) -> Dict:
        """
        Aggregate all FIRE metrics into a single dashboard response.

        Args:
            organization_id: Organization ID
            user_id: User ID (None = combined household)
            withdrawal_rate: Safe withdrawal rate (default 4%)
            expected_return: Expected annual return (default 7%)
            retirement_age: Target retirement age (default 65)

        Returns:
            Dict with all FIRE metrics
        """
        fi_ratio = await self.calculate_fi_ratio(organization_id, user_id, withdrawal_rate)
        savings_rate = await self.calculate_savings_rate(organization_id, user_id)
        years_to_fi = await self.calculate_years_to_fi(
            organization_id, user_id, withdrawal_rate, expected_return
        )
        coast_fi = await self.calculate_coast_fi(
            organization_id, user_id, retirement_age, expected_return, withdrawal_rate
        )

        return {
            "fi_ratio": fi_ratio,
            "savings_rate": savings_rate,
            "years_to_fi": years_to_fi,
            "coast_fi": coast_fi,
        }
