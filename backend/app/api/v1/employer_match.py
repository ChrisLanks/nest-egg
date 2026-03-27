"""Employer 401k/403b/457b match optimization API endpoint."""

from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.contribution import AccountContribution, ContributionFrequency, ContributionType
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class EmployerMatchItem(BaseModel):
    account_id: str
    account_name: str
    account_type: str
    user_name: str
    employer_match_percent: Optional[float]  # e.g. 50 (= 50% match)
    employer_match_limit_percent: Optional[float]  # e.g. 6 (= up to 6% of salary)
    annual_salary: Optional[float]
    annual_match_value: Optional[float]  # max $ employer will contribute
    required_employee_pct: Optional[float]  # minimum % you must contribute
    is_capturing_full_match: Optional[bool]  # None if cannot determine
    estimated_left_on_table: Optional[float]  # $/yr forfeited
    action: str


class EmployerMatchResponse(BaseModel):
    accounts: List[EmployerMatchItem]
    total_potential_match: float
    total_captured_match: float
    total_left_on_table: float
    fully_optimized: bool
    summary: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMPLOYER_PLAN_TYPES = [
    AccountType.RETIREMENT_401K.value,
    AccountType.RETIREMENT_403B.value,
    AccountType.RETIREMENT_457B.value,
]

# Approximate multiplier to annualise a contribution amount by frequency
_FREQUENCY_ANNUAL_MULTIPLIER = {
    ContributionFrequency.WEEKLY: 52,
    ContributionFrequency.BIWEEKLY: 26,
    ContributionFrequency.MONTHLY: 12,
    ContributionFrequency.QUARTERLY: 4,
    ContributionFrequency.ANNUALLY: 1,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _annual_contribution_amount(contrib: AccountContribution, annual_salary: Optional[float]) -> Optional[float]:
    """Estimate annual dollar contribution from an AccountContribution record."""
    multiplier = _FREQUENCY_ANNUAL_MULTIPLIER.get(contrib.frequency, 12)
    amount = float(contrib.amount)

    if contrib.contribution_type == ContributionType.FIXED_AMOUNT:
        return amount * multiplier

    if contrib.contribution_type == ContributionType.PERCENTAGE_GROWTH:
        # amount is a percentage of salary
        if annual_salary and annual_salary > 0:
            return (amount / 100.0) * annual_salary
        return None  # can't compute without salary

    # SHARES — not meaningful for match capture; skip
    return None


def _employee_contribution_pct(
    contrib: AccountContribution,
    annual_salary: Optional[float],
) -> Optional[float]:
    """Estimate the employee's contribution as % of salary."""
    if contrib.contribution_type == ContributionType.PERCENTAGE_GROWTH:
        return float(contrib.amount)  # already a percentage

    if contrib.contribution_type == ContributionType.FIXED_AMOUNT and annual_salary and annual_salary > 0:
        multiplier = _FREQUENCY_ANNUAL_MULTIPLIER.get(contrib.frequency, 12)
        annual_amount = float(contrib.amount) * multiplier
        return (annual_amount / annual_salary) * 100.0

    return None


def _build_item(
    account: Account,
    contrib: Optional[AccountContribution],
) -> EmployerMatchItem:
    """Build an EmployerMatchItem for a single account."""

    match_pct = float(account.employer_match_percent) if account.employer_match_percent else None
    match_limit_pct = (
        float(account.employer_match_limit_percent)
        if account.employer_match_limit_percent
        else None
    )

    # Salary — stored as EncryptedString, reads back as str; convert to float
    annual_salary: Optional[float] = None
    if account.annual_salary:
        try:
            annual_salary = float(account.annual_salary)
        except (ValueError, TypeError):
            annual_salary = None

    # Maximum annual employer match value
    annual_match_value: Optional[float] = None
    if annual_salary and match_pct is not None and match_limit_pct is not None:
        annual_match_value = annual_salary * (match_limit_pct / 100.0) * (match_pct / 100.0)

    required_employee_pct = match_limit_pct  # must contribute this % to get full match

    # Determine capture status from AccountContribution
    is_capturing_full_match: Optional[bool] = None
    estimated_left_on_table: Optional[float] = None

    if contrib is not None and contrib.is_active:
        employee_pct = _employee_contribution_pct(contrib, annual_salary)

        if employee_pct is not None and required_employee_pct is not None:
            is_capturing_full_match = employee_pct >= required_employee_pct
            if not is_capturing_full_match and annual_match_value is not None:
                # Fraction of match being captured
                captured_fraction = min(employee_pct / required_employee_pct, 1.0)
                estimated_left_on_table = annual_match_value * (1.0 - captured_fraction)
        elif annual_match_value is not None:
            # Contribution exists but we can't determine percentage — unknown
            is_capturing_full_match = None
    # If no contribution record, is_capturing_full_match remains None

    if not is_capturing_full_match and annual_match_value and estimated_left_on_table is None and contrib is None:
        estimated_left_on_table = annual_match_value  # assume zero captured

    # User name (account owner)
    user_name = getattr(account, "_user_name", None) or "Unknown"

    # Action string
    if is_capturing_full_match is True:
        action = "Full match captured \u2713"
    elif is_capturing_full_match is False and required_employee_pct is not None:
        action = f"Increase contributions to {required_employee_pct:.0f}% to capture full match"
    elif is_capturing_full_match is None and annual_match_value is not None and required_employee_pct is not None:
        action = (
            f"Verify you're contributing at least {required_employee_pct:.0f}% "
            f"to capture ${annual_match_value:,.0f}/yr match"
        )
    else:
        action = "No employer match configured — update account details"

    return EmployerMatchItem(
        account_id=str(account.id),
        account_name=account.name,
        account_type=account.account_type.value,
        user_name=user_name,
        employer_match_percent=match_pct,
        employer_match_limit_percent=match_limit_pct,
        annual_salary=annual_salary,
        annual_match_value=annual_match_value,
        required_employee_pct=required_employee_pct,
        is_capturing_full_match=is_capturing_full_match,
        estimated_left_on_table=estimated_left_on_table,
        action=action,
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/employer-match", response_model=EmployerMatchResponse)
async def get_employer_match(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Surface whether household members are fully capturing their employer 401k/403b/457b match.

    Queries all employer-plan accounts and their associated contribution records,
    then estimates how much match is being left on the table.
    """
    org_id = current_user.organization_id

    # Fetch all employer retirement plan accounts (org-scoped, no user filter)
    acct_result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == org_id,
                Account.account_type.in_(_EMPLOYER_PLAN_TYPES),
                Account.is_active == True,  # noqa: E712
            )
        )
        .order_by(Account.name)
    )
    accounts = acct_result.scalars().all()

    if not accounts:
        return EmployerMatchResponse(
            accounts=[],
            total_potential_match=0.0,
            total_captured_match=0.0,
            total_left_on_table=0.0,
            fully_optimized=True,
            summary="No 401k/403b/457b accounts found. Add employer retirement accounts to use this feature.",
        )

    account_ids = [acct.id for acct in accounts]

    # Fetch active contributions for those accounts
    contrib_result = await db.execute(
        select(AccountContribution).where(
            and_(
                AccountContribution.account_id.in_(account_ids),
                AccountContribution.is_active == True,  # noqa: E712
            )
        )
    )
    contributions = contrib_result.scalars().all()

    # Build lookup: account_id -> most recent active contribution
    contrib_by_account: dict = {}
    for c in contributions:
        existing = contrib_by_account.get(c.account_id)
        if existing is None or c.created_at > existing.created_at:
            contrib_by_account[c.account_id] = c

    # Fetch user names for accounts (best-effort join)
    from app.models.user import User as UserModel

    user_ids = list({acct.user_id for acct in accounts if acct.user_id})
    user_map: dict = {}
    if user_ids:
        user_result = await db.execute(
            select(UserModel).where(UserModel.id.in_(user_ids))
        )
        for u in user_result.scalars().all():
            name = u.display_name or f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email or str(u.id)
            user_map[u.id] = name

    # Attach user names temporarily to avoid model mutation
    for acct in accounts:
        acct._user_name = user_map.get(acct.user_id, "Unknown")  # type: ignore[attr-defined]

    # Build items
    items = [_build_item(acct, contrib_by_account.get(acct.id)) for acct in accounts]

    total_potential_match = sum(
        item.annual_match_value for item in items if item.annual_match_value is not None
    )
    total_left_on_table = sum(
        item.estimated_left_on_table
        for item in items
        if item.estimated_left_on_table is not None
    )
    total_captured_match = max(0.0, total_potential_match - total_left_on_table)
    fully_optimized = total_left_on_table == 0 and all(
        item.is_capturing_full_match is not False for item in items
    )

    if fully_optimized and total_potential_match > 0:
        summary = (
            f"All employer matches are fully captured — ${total_potential_match:,.0f}/yr "
            "in employer contributions."
        )
    elif total_left_on_table > 0:
        summary = (
            f"${total_left_on_table:,.0f}/yr in employer match is being forfeited. "
            "Increase contributions to the accounts marked below."
        )
    else:
        summary = (
            "Add salary and match details to your retirement accounts to see if you're "
            "capturing the full employer match."
        )

    return EmployerMatchResponse(
        accounts=items,
        total_potential_match=total_potential_match,
        total_captured_match=total_captured_match,
        total_left_on_table=total_left_on_table,
        fully_optimized=fully_optimized,
        summary=summary,
    )
