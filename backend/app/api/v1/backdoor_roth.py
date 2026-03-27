"""Backdoor Roth & Mega Backdoor Roth analysis API."""

import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import RETIREMENT, TAX
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.user import User
from app.utils.account_type_groups import TRADITIONAL_IRA_TYPES, EMPLOYER_PLAN_TYPES

router = APIRouter(tags=["Backdoor Roth"])

# Roth IRA income phase-out ranges — sourced from financial.py TAX class
def _roth_phaseout(filing_status: str, year: int) -> tuple:
    return TAX.roth_phaseout(filing_status, year)


class IraAccountDetail(BaseModel):
    account_id: str
    name: str
    balance: float
    form_8606_basis: float
    pre_tax_portion: float
    pro_rata_ratio: float  # 0.0–1.0  (fraction that is pre-tax)


class BackdoorRothDetail(BaseModel):
    eligible: bool
    pro_rata_warning: bool
    total_ira_balance: float
    total_form_8606_basis: float
    accounts: List[IraAccountDetail]
    steps: List[str]


class K401AccountDetail(BaseModel):
    account_id: str
    name: str
    after_tax_balance: float
    mega_backdoor_eligible: bool


class MegaBackdoorDetail(BaseModel):
    eligible: bool
    available_amount: float
    accounts: List[K401AccountDetail]
    steps: List[str]


class BackdoorRothResponse(BaseModel):
    backdoor_roth: BackdoorRothDetail
    mega_backdoor: MegaBackdoorDetail
    ira_contribution_headroom: float
    direct_roth_eligible: Optional[bool]
    user_magi_estimate: Optional[float]
    tax_year: int
    data_source: Optional[dict] = None  # DataSourceMeta — static/cached/live indicator


@router.get("/backdoor-roth-analysis", response_model=BackdoorRothResponse)
async def get_backdoor_roth_analysis(
    filing_status: str = Query(default="single"),
    estimated_magi: Optional[float] = Query(default=None),
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze backdoor Roth and mega backdoor Roth opportunities for this user."""
    import uuid as _uuid
    today = datetime.date.today()
    tax_year = today.year

    # Resolve subject user (supports household member switching)
    subject_user = current_user
    if user_id and user_id != str(current_user.id):
        member_result = await db.execute(
            select(User).where(
                User.id == _uuid.UUID(user_id),
                User.organization_id == current_user.organization_id,
            )
        )
        member = member_result.scalar_one_or_none()
        if member:
            subject_user = member

    current_age: Optional[int] = None
    if subject_user.birthdate:
        bd = subject_user.birthdate
        current_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    # Fetch IRA accounts
    ira_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.user_id == subject_user.id,
            Account.account_type.in_(list(TRADITIONAL_IRA_TYPES)),
            Account.is_active == True,
        )
    )
    ira_accounts = ira_result.scalars().all()

    # Fetch 401k-type accounts
    k401_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
            Account.user_id == subject_user.id,
            Account.account_type.in_(list(EMPLOYER_PLAN_TYPES)),
            Account.is_active == True,
        )
    )
    k401_accounts = k401_result.scalars().all()

    # --- Backdoor Roth analysis ---
    total_ira_balance = sum(float(a.current_balance or 0) for a in ira_accounts)
    total_basis = sum(float(a.form_8606_basis or 0) for a in ira_accounts)
    pro_rata_warning = total_ira_balance > 0 and (total_ira_balance - total_basis) > 0

    ira_details = []
    for a in ira_accounts:
        bal = float(a.current_balance or 0)
        basis = float(a.form_8606_basis or 0)
        pre_tax = max(0.0, bal - basis)
        ratio = (pre_tax / bal) if bal > 0 else 0.0
        ira_details.append(IraAccountDetail(
            account_id=str(a.id),
            name=a.account_name or a.account_type,
            balance=bal,
            form_8606_basis=basis,
            pre_tax_portion=pre_tax,
            pro_rata_ratio=round(ratio, 4),
        ))

    bd_steps: List[str] = []
    if pro_rata_warning:
        bd_steps.append(
            "⚠️ Pro-rata rule: You have pre-tax IRA funds. Consider rolling them into your 401(k) first to eliminate the pro-rata tax issue."
        )
    bd_steps.append("Contribute $0 (non-deductible) to a Traditional IRA — file Form 8606 to record your basis.")
    limits = RETIREMENT.for_year(tax_year)
    ira_limit = limits["LIMIT_IRA"] + (limits["LIMIT_IRA_CATCH_UP"] if current_age and current_age >= 50 else 0)
    bd_steps.append(f"Immediately convert the Traditional IRA to Roth IRA (the 'backdoor'). Annual limit: ${ira_limit:,.0f}.")
    bd_steps.append("File Form 8606 Part II to report the conversion and avoid double taxation.")

    # --- Mega Backdoor analysis ---
    k401_details = []
    total_mega = 0.0
    any_mega_eligible = False
    for a in k401_accounts:
        after_tax = float(a.after_tax_401k_balance or 0)
        eligible = bool(a.mega_backdoor_eligible)
        if eligible:
            any_mega_eligible = True
            total_mega += after_tax
        k401_details.append(K401AccountDetail(
            account_id=str(a.id),
            name=a.account_name or a.account_type,
            after_tax_balance=after_tax,
            mega_backdoor_eligible=eligible,
        ))

    mega_steps: List[str] = []
    if not k401_accounts:
        mega_steps.append("No 401(k) accounts found. A mega backdoor requires a 401(k) plan.")
    elif not any_mega_eligible:
        mega_steps.append("Your 401(k) plan does not appear to allow in-service withdrawals or after-tax contributions. Check with your plan administrator.")
    else:
        mega_steps.append(f"Confirm your plan allows after-tax contributions (beyond the ${limits['LIMIT_401K']:,.0f} pre-tax limit).")
        mega_steps.append(f"Contribute after-tax to your 401(k) up to the total ${limits['LIMIT_401K_TOTAL']:,.0f} combined limit.")
        mega_steps.append("Immediately convert the after-tax balance to Roth (in-plan Roth rollover) or withdraw and roll to a Roth IRA.")
        if total_mega > 0:
            mega_steps.append(f"You currently have ${total_mega:,.0f} in after-tax 401(k) funds available to convert.")

    # Direct Roth eligibility
    direct_roth_eligible = None
    if estimated_magi is not None:
        lo, hi = _roth_phaseout(filing_status, tax_year)
        direct_roth_eligible = estimated_magi < lo

    return BackdoorRothResponse(
        backdoor_roth=BackdoorRothDetail(
            eligible=True,  # Always an option (with pro-rata caveat)
            pro_rata_warning=pro_rata_warning,
            total_ira_balance=total_ira_balance,
            total_form_8606_basis=total_basis,
            accounts=ira_details,
            steps=bd_steps,
        ),
        mega_backdoor=MegaBackdoorDetail(
            eligible=any_mega_eligible,
            available_amount=total_mega,
            accounts=k401_details,
            steps=mega_steps,
        ),
        ira_contribution_headroom=float(ira_limit),
        direct_roth_eligible=direct_roth_eligible,
        user_magi_estimate=estimated_magi,
        tax_year=tax_year,
    )
