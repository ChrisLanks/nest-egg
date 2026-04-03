"""Net worth percentile API endpoint — SCF benchmark comparison."""

import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.user import User
from app.services.scf_benchmark_service import age_bucket as _age_bucket
from app.services.scf_benchmark_service import fidelity_target, get_benchmarks

logger = logging.getLogger(__name__)



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(tags=["Net Worth Percentile"], dependencies=[Depends(_rate_limit)])

_DATA_SOURCE = "Federal Reserve Survey of Consumer Finances (2022)"

# Approximate 25th and 75th / 90th percentile multipliers relative to median.
# The SCF publishes median and mean; we derive the spread from historical SCF
# distributions (the distribution is right-skewed, so these are conservative).
#
# Multipliers applied to the median for each synthetic percentile:
#   p25 ≈ 0.20 × median  (bottom quartile — very little savings)
#   p50 = 1.00 × median  (by definition)
#   p75 ≈ 2.80 × median  (rough upper-quartile estimate)
#   p90 ≈ 5.50 × median  (rough top-decile estimate)
#
# These are intentionally rough — real SCF microdata would give exact values.
_P25_FACTOR = 0.20
_P75_FACTOR = 2.80
_P90_FACTOR = 5.50


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PercentileBenchmark(BaseModel):
    label: str
    value: float
    is_above: bool


class NetWorthPercentileResponse(BaseModel):
    current_net_worth: float
    age: Optional[int]
    age_bucket: str
    estimated_percentile: float
    percentile_label: str
    benchmarks: List[PercentileBenchmark]
    fidelity_target_multiplier: float
    fidelity_target_amount: Optional[float]
    median_for_age: float
    data_source: str
    encouragement: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _interpolate_percentile(net_worth: float, p25: float, p50: float, p75: float, p90: float) -> float:
    """Linearly interpolate net worth to an estimated percentile (0-100)."""
    if net_worth >= p90:
        # Above 90th — interpolate between 90 and 100 using the p90→mean gap as proxy
        excess_factor = min((net_worth - p90) / max(p90, 1), 1.0)
        return round(90 + 10 * excess_factor, 1)
    if net_worth >= p75:
        t = (net_worth - p75) / max(p90 - p75, 1)
        return round(75 + 15 * t, 1)
    if net_worth >= p50:
        t = (net_worth - p50) / max(p75 - p50, 1)
        return round(50 + 25 * t, 1)
    if net_worth >= p25:
        t = (net_worth - p25) / max(p50 - p25, 1)
        return round(25 + 25 * t, 1)
    if p25 > 0:
        t = max(net_worth / p25, 0)
        return round(25 * t, 1)
    return 0.0


def _percentile_label(pct: float) -> str:
    if pct >= 90:
        return "Top 10%"
    if pct >= 75:
        return "Top 25%"
    if pct >= 50:
        return "Top 50%"
    if pct >= 25:
        return "Second quartile"
    return "Bottom 25%"


def _encouragement(pct: float) -> str:
    if pct >= 90:
        return "Outstanding — you're in the top 10% for your age group."
    if pct >= 75:
        return "Excellent financial position — top quartile for your age."
    if pct >= 50:
        return "Above median — you're ahead of most peers your age."
    if pct >= 25:
        return "Building momentum — you're in the second quartile."
    return "Early stage — focus on increasing savings rate and reducing debt."


def _fidelity_multiplier(age: int) -> float:
    """Return the closest applicable Fidelity salary-multiple for the given age."""
    from app.constants.financial import NET_WORTH_BENCHMARKS

    milestones = NET_WORTH_BENCHMARKS.FIDELITY_MILESTONES
    applicable = sorted(a for a in milestones if a <= age)
    if not applicable:
        return 1.0
    return milestones[applicable[-1]]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/net-worth-percentile", response_model=NetWorthPercentileResponse)
async def get_net_worth_percentile(
    age: Optional[int] = Query(
        None, ge=18, le=100, description="Age override (default: derived from user birthdate)"
    ),
    annual_income: Optional[float] = Query(
        None, ge=0, description="Gross annual income for Fidelity target calculation (USD)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare the user's net worth against SCF age-group benchmarks.

    Returns estimated percentile, benchmark reference points, and a
    Fidelity salary-multiple target for retirement preparedness.
    """
    # Resolve age
    effective_age: Optional[int] = age
    if effective_age is None and current_user.birthdate is not None:
        today = datetime.date.today()
        bd = current_user.birthdate
        effective_age = (
            today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        )

    # Latest net worth snapshot (household-level: user_id IS NULL preferred)
    snap_result = await db.execute(
        select(NetWorthSnapshot)
        .where(
            NetWorthSnapshot.organization_id == current_user.organization_id,
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = snap_result.scalars().first()
    current_net_worth = float(snapshot.total_net_worth) if snapshot else 0.0

    # SCF benchmark data
    benchmarks_data = get_benchmarks()
    median_by_age: dict = benchmarks_data.get("median", {})

    # Age bucket
    resolved_bucket = _age_bucket(effective_age) if effective_age is not None else "35-44"
    median_for_age = float(median_by_age.get(resolved_bucket, 135_600))

    # Synthetic percentile reference points
    p25 = median_for_age * _P25_FACTOR
    p50 = median_for_age
    p75 = median_for_age * _P75_FACTOR
    p90 = median_for_age * _P90_FACTOR

    estimated_pct = _interpolate_percentile(current_net_worth, p25, p50, p75, p90)

    # Benchmarks list
    benchmark_entries: List[PercentileBenchmark] = [
        PercentileBenchmark(
            label="25th percentile",
            value=round(p25, 0),
            is_above=current_net_worth >= p25,
        ),
        PercentileBenchmark(
            label="Median (50th percentile)",
            value=round(p50, 0),
            is_above=current_net_worth >= p50,
        ),
        PercentileBenchmark(
            label="75th percentile",
            value=round(p75, 0),
            is_above=current_net_worth >= p75,
        ),
        PercentileBenchmark(
            label="90th percentile",
            value=round(p90, 0),
            is_above=current_net_worth >= p90,
        ),
    ]

    # Fidelity target
    fidelity_mult = _fidelity_multiplier(effective_age) if effective_age is not None else 1.0
    fidelity_amount: Optional[float] = None
    if annual_income and annual_income > 0:
        fidelity_amount = round(fidelity_mult * annual_income, 2)

    return NetWorthPercentileResponse(
        current_net_worth=round(current_net_worth, 2),
        age=effective_age,
        age_bucket=resolved_bucket,
        estimated_percentile=estimated_pct,
        percentile_label=_percentile_label(estimated_pct),
        benchmarks=benchmark_entries,
        fidelity_target_multiplier=fidelity_mult,
        fidelity_target_amount=fidelity_amount,
        median_for_age=round(median_for_age, 0),
        data_source=_DATA_SOURCE,
        encouragement=_encouragement(estimated_pct),
    )
