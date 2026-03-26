"""Contribution Headroom API — annual tax-advantaged contribution room per member."""

import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, extract, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import RETIREMENT
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.contribution import AccountContribution, ContributionFrequency
from app.models.user import User

router = APIRouter(tags=["Contribution Headroom"])

# Account types that have IRS contribution limits
_LIMIT_TYPES = {
    AccountType.RETIREMENT_401K,
    AccountType.RETIREMENT_403B,
    AccountType.RETIREMENT_457B,
    AccountType.RETIREMENT_IRA,
    AccountType.RETIREMENT_ROTH,
    AccountType.RETIREMENT_SEP_IRA,
    AccountType.RETIREMENT_SIMPLE_IRA,
    AccountType.HSA,
    AccountType.RETIREMENT_529,
}


def _annual_limit(account_type: AccountType, age: Optional[int], limits: dict, hsa_family: bool = False) -> tuple[float, bool, float]:
    """Return (base_limit, catch_up_eligible, total_limit_with_catchup)."""
    catchup_age_401k = RETIREMENT.CATCH_UP_AGE_401K
    catchup_age_hsa = RETIREMENT.CATCH_UP_AGE_HSA

    if account_type in (AccountType.RETIREMENT_401K, AccountType.RETIREMENT_403B, AccountType.RETIREMENT_457B):
        base = float(limits["LIMIT_401K"])
        catchup = float(limits["LIMIT_401K_CATCH_UP"])
        eligible = age is not None and age >= catchup_age_401k
        return base, eligible, base + (catchup if eligible else 0)
    if account_type in (AccountType.RETIREMENT_IRA, AccountType.RETIREMENT_ROTH):
        base = float(limits["LIMIT_IRA"])
        catchup = float(limits["LIMIT_IRA_CATCH_UP"])
        eligible = age is not None and age >= catchup_age_401k
        return base, eligible, base + (catchup if eligible else 0)
    if account_type == AccountType.RETIREMENT_SEP_IRA:
        base = float(limits["LIMIT_SEP_IRA"])
        return base, False, base
    if account_type == AccountType.RETIREMENT_SIMPLE_IRA:
        base = float(limits["LIMIT_SIMPLE_IRA"])
        catchup = float(limits["LIMIT_SIMPLE_IRA_CATCH_UP"])
        eligible = age is not None and age >= catchup_age_401k
        return base, eligible, base + (catchup if eligible else 0)
    if account_type == AccountType.HSA:
        base = float(limits["LIMIT_HSA_FAMILY"]) if hsa_family else float(limits["LIMIT_HSA_INDIVIDUAL"])
        catchup = float(limits["LIMIT_HSA_CATCH_UP"])
        eligible = age is not None and age >= catchup_age_hsa
        return base, eligible, base + (catchup if eligible else 0)
    if account_type == AccountType.RETIREMENT_529:
        base = float(limits["LIMIT_529_ANNUAL_GIFT_EXCLUSION"])
        return base, False, base
    return 0.0, False, 0.0


def _annualize(amount: float, frequency: ContributionFrequency) -> float:
    """Convert a recurring contribution amount to annual."""
    mapping = {
        ContributionFrequency.WEEKLY: 52,
        ContributionFrequency.BIWEEKLY: 26,
        ContributionFrequency.MONTHLY: 12,
        ContributionFrequency.QUARTERLY: 4,
        ContributionFrequency.ANNUALLY: 1,
    }
    return amount * mapping.get(frequency, 12)


class AccountHeadroom(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    limit: float
    catch_up_limit: float
    catch_up_eligible: bool
    contributed_ytd: float
    remaining_headroom: float
    pct_used: float


class MemberHeadroom(BaseModel):
    user_id: str
    name: str
    age: Optional[int]
    accounts: List[AccountHeadroom]
    total_limit: float
    total_contributed_ytd: float
    total_remaining_headroom: float


class ContributionHeadroomResponse(BaseModel):
    tax_year: int
    members: List[MemberHeadroom]


@router.get("/contribution-headroom", response_model=ContributionHeadroomResponse)
async def get_contribution_headroom(
    tax_year: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Show remaining IRS contribution room per tax-advantaged account for all household members."""
    today = datetime.date.today()
    year = tax_year or today.year
    limits = RETIREMENT.for_year(year)

    # Fetch all users in org
    user_result = await db.execute(
        select(User).where(
            User.organization_id == current_user.organization_id,
            User.is_active == True,
        )
    )
    members = user_result.scalars().all()

    member_responses: List[MemberHeadroom] = []

    for member in members:
        age: Optional[int] = None
        if member.birthdate:
            bd = member.birthdate
            age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

        # Fetch limited accounts for this member
        acct_result = await db.execute(
            select(Account).where(
                Account.organization_id == current_user.organization_id,
                Account.user_id == member.id,
                Account.account_type.in_(list(_LIMIT_TYPES)),
                Account.is_active == True,
            )
        )
        accts = acct_result.scalars().all()

        account_rows: List[AccountHeadroom] = []
        total_limit = 0.0
        total_ytd = 0.0

        for acct in accts:
            # Sum active annual contributions
            contrib_result = await db.execute(
                select(AccountContribution).where(
                    AccountContribution.account_id == acct.id,
                    AccountContribution.is_active == True,
                )
            )
            contribs = contrib_result.scalars().all()
            ytd = sum(_annualize(float(c.amount), c.frequency) / (12 / today.month) for c in contribs)

            hsa_family = len(members) >= 2
            base_limit, catchup_elig, full_limit = _annual_limit(acct.account_type, age, limits, hsa_family)
            if full_limit == 0:
                continue

            remaining = max(0.0, full_limit - ytd)
            pct = min(100.0, round((ytd / full_limit * 100) if full_limit > 0 else 0, 1))
            total_limit += full_limit
            total_ytd += ytd

            account_rows.append(AccountHeadroom(
                account_id=str(acct.id),
                account_name=acct.account_name or str(acct.account_type),
                account_type=str(acct.account_type),
                limit=base_limit,
                catch_up_limit=full_limit,
                catch_up_eligible=catchup_elig,
                contributed_ytd=round(ytd, 2),
                remaining_headroom=round(remaining, 2),
                pct_used=pct,
            ))

        member_responses.append(MemberHeadroom(
            user_id=str(member.id),
            name=member.display_name or member.email or "Member",
            age=age,
            accounts=account_rows,
            total_limit=round(total_limit, 2),
            total_contributed_ytd=round(total_ytd, 2),
            total_remaining_headroom=round(max(0, total_limit - total_ytd), 2),
        ))

    return ContributionHeadroomResponse(tax_year=year, members=member_responses)
