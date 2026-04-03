"""Calculator Prefill API — auto-populates calculator inputs from account data."""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.contribution import AccountContribution
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service

logger = logging.getLogger(__name__)


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for calculator prefill endpoint."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(dependencies=[Depends(_rate_limit)])


class PrefillResponse(BaseModel):
    calculator: str
    prefilled: bool
    values: Dict[str, Any]
    note: str

_IRA_TYPES = [AccountType.RETIREMENT_IRA, AccountType.RETIREMENT_SEP_IRA, AccountType.RETIREMENT_SIMPLE_IRA]
_401K_TYPES = [AccountType.RETIREMENT_401K, AccountType.RETIREMENT_403B, AccountType.RETIREMENT_457B]
_ROTH_TYPES = [AccountType.RETIREMENT_ROTH]
_TAXABLE_TYPES = [AccountType.BROKERAGE]


async def _sum_balances(db: AsyncSession, org_id, account_types: list) -> float:
    """Sum current balances for given account types."""
    result = await db.execute(
        select(func.coalesce(func.sum(Account.current_balance), 0)).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(account_types),
                Account.is_active == True,  # noqa: E712
            )
        )
    )
    return float(result.scalar() or 0)


@router.get("/prefill", response_model=PrefillResponse)
async def calculator_prefill(
    calculator: str = Query(..., description="roth_conversion, capital_gains, or contribution_headroom"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return pre-filled calculator values from user's actual accounts."""
    org_id = current_user.organization_id

    if calculator == "roth_conversion":
        traditional_balance = await _sum_balances(db, org_id, _IRA_TYPES + _401K_TYPES)
        roth_balance = await _sum_balances(db, org_id, _ROTH_TYPES)

        return {
            "calculator": "roth_conversion",
            "prefilled": True,
            "values": {
                "traditional_ira_balance": round(traditional_balance, 2),
                "roth_balance": round(roth_balance, 2),
                "current_income": float(current_user.annual_income) if hasattr(current_user, 'annual_income') and current_user.annual_income else 0,
                "filing_status": getattr(current_user, 'filing_status', 'single') or 'single',
                "state": getattr(current_user, 'state', '') or '',
            },
            "note": "Pre-filled from your accounts — edit as needed.",
        }

    elif calculator == "capital_gains":
        taxable_balance = await _sum_balances(db, org_id, _TAXABLE_TYPES)

        return {
            "calculator": "capital_gains",
            "prefilled": True,
            "values": {
                "taxable_portfolio_value": round(taxable_balance, 2),
                "realized_gains_ytd": 0,  # Would need transaction analysis
                "unrealized_gains": 0,  # Would need cost basis data
                "estimated_income": float(current_user.annual_income) if hasattr(current_user, 'annual_income') and current_user.annual_income else 0,
            },
            "note": "Pre-filled from your accounts — edit as needed.",
        }

    elif calculator == "contribution_headroom":
        # Sum existing contributions YTD
        from datetime import date
        year_start = date(date.today().year, 1, 1)

        ira_contrib_result = await db.execute(
            select(func.coalesce(func.sum(AccountContribution.amount), 0)).where(
                and_(
                    AccountContribution.organization_id == org_id,
                    AccountContribution.is_active == True,  # noqa: E712
                )
            )
        )
        total_contrib = float(ira_contrib_result.scalar() or 0)

        # Get employer match from 401k accounts
        employer_match = 0
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.organization_id == org_id,
                    Account.account_type.in_(_401K_TYPES),
                    Account.is_active == True,  # noqa: E712
                )
            )
        )
        for acct in result.scalars().all():
            if acct.employer_match_percent:
                employer_match += float(acct.employer_match_percent)

        return {
            "calculator": "contribution_headroom",
            "prefilled": True,
            "values": {
                "existing_contributions_ytd": round(total_contrib, 2),
                "employer_match_pct": round(employer_match, 2),
                "num_401k_accounts": 0,
                "num_ira_accounts": 0,
            },
            "note": "Pre-filled from your accounts — edit as needed.",
        }

    else:
        return {
            "calculator": calculator,
            "prefilled": False,
            "values": {},
            "note": f"Unknown calculator type: {calculator}",
        }
