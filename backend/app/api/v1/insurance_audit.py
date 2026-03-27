"""Insurance audit API endpoint."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response schemas
# ---------------------------------------------------------------------------

class InsuranceCoverageItem(BaseModel):
    insurance_type: str  # "term_life", "disability", "umbrella", "ltc", "health"
    display_name: str
    description: str
    recommended_coverage: str  # human-readable, e.g. "10-12x gross income"
    existing_accounts: List[dict]  # LIFE_INSURANCE_CASH_VALUE accounts if any
    has_coverage: bool
    priority: str  # "critical", "important", "optional"
    tips: List[str]


class InsuranceAuditResponse(BaseModel):
    coverage_items: List[InsuranceCoverageItem]
    critical_gaps: int
    coverage_score: int  # 0-100
    net_worth: float


# ---------------------------------------------------------------------------
# Static coverage definitions
# ---------------------------------------------------------------------------

_STATIC_COVERAGE = [
    {
        "insurance_type": "term_life",
        "display_name": "Term Life Insurance",
        "description": (
            "Provides a death benefit to your dependents if you die during the policy term. "
            "Critical for anyone with dependents, a mortgage, or income others rely on."
        ),
        "recommended_coverage": "10–12× gross income",
        "priority": "critical",
        "tips": [
            "Use the DIME method: Debt + Income replacement + Mortgage + Education costs.",
            "Term policies (20–30 yr) are far cheaper than whole life for most families.",
            "Buy coverage before any health issues develop to lock in preferred rates.",
            "Review coverage after major life events: marriage, children, home purchase.",
        ],
    },
    {
        "insurance_type": "disability",
        "display_name": "Disability Insurance",
        "description": (
            "Replaces a portion of your income if illness or injury prevents you from working. "
            "Your biggest asset is your earning capacity — protect it."
        ),
        "recommended_coverage": "60–70% of gross income",
        "priority": "critical",
        "tips": [
            "Prefer 'own-occupation' definitions — you're covered if you can't do your specific job.",
            "Employer group plans often use 'any-occupation' definitions; supplement with individual coverage.",
            "Aim for a benefit period to age 65 with a 90-day elimination period.",
            "Social Security disability is very hard to qualify for — don't rely on it alone.",
        ],
    },
    {
        "insurance_type": "health",
        "display_name": "Health Insurance",
        "description": (
            "Covers medical expenses including doctor visits, hospital stays, and prescriptions. "
            "A medical emergency without coverage can be financially devastating."
        ),
        "recommended_coverage": "Adequate ACA/employer plan",
        "priority": "critical",
        "tips": [
            "Maximize HSA contributions if enrolled in a High-Deductible Health Plan (HDHP).",
            "Review your out-of-pocket maximum — this is your worst-case annual exposure.",
            "Check whether your preferred doctors are in-network before choosing a plan.",
            "Consider a supplemental accident policy to cover your deductible.",
        ],
    },
    {
        "insurance_type": "umbrella",
        "display_name": "Umbrella Liability Insurance",
        "description": (
            "Extends liability protection beyond your home and auto policy limits. "
            "Essential once your net worth or income could make you a lawsuit target."
        ),
        "recommended_coverage": "$1M+ liability umbrella",
        "priority": "important",
        "tips": [
            "A $1M umbrella policy typically costs $150–$300/yr — very cost-effective.",
            "Required triggers: net worth > $500k, rental property, teenage drivers, or pool.",
            "Coverage must exceed your underlying home/auto liability limits.",
            "Increase limits to $2M+ as net worth grows beyond $1M.",
        ],
    },
    {
        "insurance_type": "ltc",
        "display_name": "Long-Term Care (LTC) Insurance",
        "description": (
            "Covers costs for nursing home, assisted living, or in-home care when you can no "
            "longer perform basic activities of daily living. Medicare covers very little LTC."
        ),
        "recommended_coverage": "3+ years of coverage",
        "priority": "optional",  # upgraded to "important" if age >= 50 at runtime
        "tips": [
            "Hybrid life/LTC policies provide a death benefit if you never need care.",
            "Best time to buy is ages 55–65: premiums are still reasonable.",
            "Roughly 70% of people over 65 will need some form of long-term care.",
            "Shared-care riders allow spouses to pool benefit days.",
        ],
    },
]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/insurance-audit", response_model=InsuranceAuditResponse)
async def get_insurance_audit(
    user_id: Optional[str] = Query(default=None, description="Household member user ID; defaults to current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return an insurance coverage checklist with gap analysis.

    Surfaces any LIFE_INSURANCE_CASH_VALUE accounts from the database and
    combines them with a static checklist of recommended coverage types.
    """
    import uuid as _uuid

    # Resolve subject user
    subject_user_id = None
    if user_id:
        if user_id != str(current_user.id):
            member_result = await db.execute(
                select(User).where(
                    User.id == _uuid.UUID(user_id),
                    User.organization_id == current_user.organization_id,
                )
            )
            member = member_result.scalar_one_or_none()
            if member:
                subject_user_id = member.id
        else:
            subject_user_id = current_user.id

    # Fetch life insurance cash-value accounts for this org
    life_conditions = [
        Account.organization_id == current_user.organization_id,
        Account.account_type == AccountType.LIFE_INSURANCE_CASH_VALUE,
        Account.is_active == True,  # noqa: E712
    ]
    if subject_user_id:
        life_conditions.append(Account.user_id == subject_user_id)
    life_result = await db.execute(
        select(Account).where(and_(*life_conditions))
    )
    life_accounts = life_result.scalars().all()

    life_account_dicts = [
        {
            "id": str(acct.id),
            "name": acct.name,
            "balance": float(acct.current_balance or 0),
        }
        for acct in life_accounts
    ]

    # Latest household net-worth snapshot (user_id IS NULL = household rollup)
    snapshot_result = await db.execute(
        select(NetWorthSnapshot)
        .where(
            and_(
                NetWorthSnapshot.organization_id == current_user.organization_id,
                NetWorthSnapshot.user_id == None,  # noqa: E711
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()
    net_worth = float(snapshot.total_net_worth) if snapshot else 0.0

    # Determine user age for LTC priority (best effort — may be None)
    user_age: Optional[int] = None
    if hasattr(current_user, "date_of_birth") and current_user.date_of_birth:
        from datetime import date

        today = date.today()
        dob = current_user.date_of_birth
        user_age = (
            today.year
            - dob.year
            - ((today.month, today.day) < (dob.month, dob.day))
        )

    # Build coverage items
    coverage_items: List[InsuranceCoverageItem] = []
    critical_gap_count = 0

    for defn in _STATIC_COVERAGE:
        itype = defn["insurance_type"]
        priority = defn["priority"]

        # LTC priority upgrades when age >= 50
        if itype == "ltc" and user_age is not None and user_age >= 50:
            priority = "important"

        # Only life insurance maps to tracked accounts
        if itype == "term_life":
            existing = life_account_dicts
            has_coverage = len(existing) > 0
        else:
            existing = []
            has_coverage = False

        # Count critical gaps (critical items without coverage)
        if priority == "critical" and not has_coverage:
            critical_gap_count += 1

        coverage_items.append(
            InsuranceCoverageItem(
                insurance_type=itype,
                display_name=defn["display_name"],
                description=defn["description"],
                recommended_coverage=defn["recommended_coverage"],
                existing_accounts=existing,
                has_coverage=has_coverage,
                priority=priority,
                tips=defn["tips"],
            )
        )

    # Score based on critical items covered (3 critical types)
    critical_types = [item for item in coverage_items if item.priority == "critical"]
    critical_covered = sum(1 for item in critical_types if item.has_coverage)
    critical_total = len(critical_types)
    coverage_score = int((critical_covered / critical_total * 100)) if critical_total > 0 else 0

    return InsuranceAuditResponse(
        coverage_items=coverage_items,
        critical_gaps=critical_gap_count,
        coverage_score=coverage_score,
        net_worth=net_worth,
    )
