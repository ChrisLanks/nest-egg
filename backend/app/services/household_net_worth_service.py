"""Per-member net worth breakdown for household views.

Returns net worth attributed to each household member (and joint/unattributed
accounts) so couples and families can see "his / hers / joint" views.

Accounts are attributed to members via the ``user_id`` foreign key on the
Account model.  Accounts with ``user_id=NULL`` are treated as joint/shared.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountCategory, AccountType


@dataclass
class MemberNetWorth:
    """Net worth attributed to a single household member."""

    user_id: Optional[UUID]
    display_name: str  # "Member" or first name if available
    total_assets: float
    total_debts: float
    net_worth: float
    account_count: int
    accounts_by_type: dict[str, float] = field(default_factory=dict)


@dataclass
class HouseholdNetWorthBreakdown:
    """Full household net worth broken down by member."""

    organization_id: UUID
    total_net_worth: float
    total_assets: float
    total_debts: float
    members: list[MemberNetWorth]  # one entry per user_id + one "joint" entry
    member_count: int  # excludes the joint bucket


async def get_household_net_worth_breakdown(
    db: AsyncSession,
    organization_id: UUID,
    member_display_names: Optional[dict[UUID, str]] = None,
) -> HouseholdNetWorthBreakdown:
    """Aggregate net worth per household member.

    Parameters
    ----------
    db:
        Async SQLAlchemy session.
    organization_id:
        The household organisation UUID.
    member_display_names:
        Optional mapping of user_id → display name (e.g. first name).
        Falls back to "Member 1", "Member 2", … if not provided.
    """
    result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == organization_id,
                Account.is_active.is_(True),
            )
        )
    )
    accounts = result.scalars().all()

    # Group accounts by user_id (None = joint/shared)
    buckets: dict[Optional[UUID], list[Account]] = {}
    for acct in accounts:
        uid = acct.user_id
        buckets.setdefault(uid, []).append(acct)

    names = member_display_names or {}
    member_num = 1
    members: list[MemberNetWorth] = []
    total_assets = 0.0
    total_debts = 0.0

    # Produce per-member entries first (user_id != None), joint last
    for uid in sorted(buckets.keys(), key=lambda x: (x is None, str(x or ""))):
        accts = buckets[uid]

        if uid is None:
            display = "Joint / Unattributed"
        elif uid in names:
            display = names[uid]
        else:
            display = f"Member {member_num}"
            member_num += 1

        assets = sum(
            float(a.current_balance or 0)
            for a in accts
            if a.account_type.category == AccountCategory.ASSET
        )
        debts = sum(
            float(a.current_balance or 0)
            for a in accts
            if a.account_type.category == AccountCategory.DEBT
        )
        nw = assets - debts
        total_assets += assets
        total_debts += debts

        # Group by account type for breakdown
        by_type: dict[str, float] = {}
        for a in accts:
            key = a.account_type.value
            by_type[key] = by_type.get(key, 0.0) + float(a.current_balance or 0)

        members.append(
            MemberNetWorth(
                user_id=uid,
                display_name=display,
                total_assets=round(assets, 2),
                total_debts=round(debts, 2),
                net_worth=round(nw, 2),
                account_count=len(accts),
                accounts_by_type={k: round(v, 2) for k, v in by_type.items()},
            )
        )

    real_members = [m for m in members if m.user_id is not None]

    return HouseholdNetWorthBreakdown(
        organization_id=organization_id,
        total_net_worth=round(total_assets - total_debts, 2),
        total_assets=round(total_assets, 2),
        total_debts=round(total_debts, 2),
        members=members,
        member_count=len(real_members),
    )
