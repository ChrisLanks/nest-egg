"""Service for 529 education planning projections."""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import EDUCATION
from app.models.account import Account, AccountType
from app.models.contribution import AccountContribution

logger = logging.getLogger(__name__)


class EducationPlanningService:
    """Project 529 savings against estimated college costs."""

    # Re-export from centralized constants
    COLLEGE_COSTS = EDUCATION.COLLEGE_COSTS
    COLLEGE_INFLATION_RATE = EDUCATION.COLLEGE_INFLATION_RATE
    DEFAULT_ANNUAL_RETURN = EDUCATION.DEFAULT_ANNUAL_RETURN
    COLLEGE_YEARS = EDUCATION.COLLEGE_YEARS

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_education_plans(
        self,
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Return an education-planning summary for every 529 account in the org."""
        query = select(Account).where(
            and_(
                Account.organization_id == organization_id,
                Account.account_type == AccountType.RETIREMENT_529,
                Account.is_active == True,  # noqa: E712
            )
        )
        if user_id:
            query = query.where(Account.user_id == user_id)

        result = await db.execute(query.order_by(Account.name))
        accounts = list(result.scalars().all())

        plans: List[Dict] = []
        for acct in accounts:
            # Try to find a recurring contribution for this account
            contrib_result = await db.execute(
                select(AccountContribution)
                .where(
                    and_(
                        AccountContribution.account_id == acct.id,
                        AccountContribution.organization_id == organization_id,
                        AccountContribution.is_active == True,  # noqa: E712
                    )
                )
                .order_by(AccountContribution.created_at.desc())
            )
            contribution = contrib_result.scalars().first()
            monthly_contribution = float(contribution.amount) if contribution else 0.0

            plans.append(
                {
                    "account_id": str(acct.id),
                    "account_name": acct.name,
                    "current_balance": float(acct.current_balance or 0),
                    "monthly_contribution": monthly_contribution,
                    "user_id": str(acct.user_id),
                }
            )

        return plans

    async def project_529(
        self,
        current_balance: float,
        monthly_contribution: float,
        years_until_college: int,
        college_type: str = "public_in_state",
        annual_return: float = 0.06,
    ) -> Dict:
        """
        Project 529 growth vs projected college costs.

        Returns year-by-year projections plus summary metrics.
        """
        annual_cost_today = self.COLLEGE_COSTS.get(
            college_type, self.COLLEGE_COSTS["public_in_state"]
        )

        monthly_rate = annual_return / 12

        # Year-by-year savings projection
        projections: List[Dict] = []
        balance = current_balance

        for year in range(1, years_until_college + 1):
            # Compound monthly contributions for one year
            for _ in range(12):
                balance = balance * (1 + monthly_rate) + monthly_contribution
            projections.append(
                {
                    "year": year,
                    "projected_savings": round(balance, 2),
                }
            )

        projected_balance = round(balance, 2)

        # Estimated total college cost (4 years, inflated to the start year)
        total_college_cost = 0.0
        for y in range(self.COLLEGE_YEARS):
            inflated_year = years_until_college + y
            annual_inflated = annual_cost_today * (
                (1 + self.COLLEGE_INFLATION_RATE) ** inflated_year
            )
            total_college_cost += annual_inflated
        total_college_cost = round(total_college_cost, 2)

        funding_percentage = (
            round((projected_balance / total_college_cost) * 100, 1)
            if total_college_cost > 0
            else 0.0
        )
        gap = round(total_college_cost - projected_balance, 2)

        # Recommend monthly contribution to close the gap
        recommended_monthly = 0.0
        if gap > 0 and years_until_college > 0:
            # Future value of annuity formula: FV = PMT * [((1+r)^n - 1) / r]
            n = years_until_college * 12
            if monthly_rate > 0:
                fv_factor = ((1 + monthly_rate) ** n - 1) / monthly_rate
                recommended_monthly = round(gap / fv_factor, 2) if fv_factor > 0 else 0.0
            else:
                recommended_monthly = round(gap / n, 2)

        return {
            "current_balance": current_balance,
            "monthly_contribution": monthly_contribution,
            "years_until_college": years_until_college,
            "college_type": college_type,
            "annual_return": annual_return,
            "projected_balance": projected_balance,
            "total_college_cost": total_college_cost,
            "funding_percentage": funding_percentage,
            "funding_gap": gap if gap > 0 else 0.0,
            "funding_surplus": abs(gap) if gap < 0 else 0.0,
            "recommended_monthly_to_close_gap": recommended_monthly,
            "projections": projections,
        }


education_planning_service = EducationPlanningService()
