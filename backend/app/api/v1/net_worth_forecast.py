"""Net Worth Forecast API — projects net worth trajectory to retirement."""

import datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import RETIREMENT, FIRE
from app.core.database import get_db
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.user import User



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(tags=["Net Worth Forecast"], dependencies=[Depends(_rate_limit)])


class ForecastPoint(BaseModel):
    year: int
    age: Optional[int]
    net_worth: float


class NetWorthForecastResponse(BaseModel):
    current_net_worth: float
    current_age: Optional[int]
    retirement_age: int
    years_to_retirement: int
    baseline: List[ForecastPoint]
    pessimistic: List[ForecastPoint]
    optimistic: List[ForecastPoint]
    retirement_target: float
    on_track: bool
    annual_contribution_used: float
    annual_return_used: float


def _project(
    current_nw: float,
    current_age: Optional[int],
    retirement_age: int,
    annual_contribution: float,
    annual_return: float,
    inflation_rate: float,
    years: int,
    start_year: int,
) -> List[ForecastPoint]:
    points = []
    nw = current_nw
    for i in range(years + 1):
        age = (current_age + i) if current_age is not None else None
        points.append(ForecastPoint(year=start_year + i, age=age, net_worth=round(nw, 2)))
        nw = nw * (1 + annual_return) + annual_contribution
    return points


@router.get("/net-worth-forecast", response_model=NetWorthForecastResponse)
async def get_net_worth_forecast(
    retirement_age: int = Query(default=RETIREMENT.DEFAULT_RETIREMENT_AGE, ge=40, le=90),
    annual_return: float = Query(default=FIRE.DEFAULT_EXPECTED_RETURN, ge=0.0, le=0.20),
    annual_contribution: Optional[float] = Query(default=None, ge=0),
    inflation_rate: float = Query(default=FIRE.DEFAULT_INFLATION, ge=0.0, le=0.15),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Project net worth from today to retirement under baseline / optimistic / pessimistic scenarios."""
    today = datetime.date.today()
    current_year = today.year

    # Derive current age from birthdate
    current_age: Optional[int] = None
    if current_user.birthdate:
        bd = current_user.birthdate
        current_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

    # Latest net worth snapshot
    snapshot_row = await db.execute(
        select(NetWorthSnapshot.total_net_worth)
        .where(NetWorthSnapshot.organization_id == current_user.organization_id)
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    row = snapshot_row.first()
    current_nw = float(row[0]) if row and row[0] is not None else 0.0

    # Annual contribution: use caller override or sensible default
    contrib = annual_contribution if annual_contribution is not None else float(FIRE.DEFAULT_ANNUAL_CONTRIBUTION)

    years_to_retirement = max(1, retirement_age - current_age) if current_age else 20

    baseline = _project(current_nw, current_age, retirement_age, contrib, annual_return, inflation_rate, years_to_retirement, current_year)
    pessimistic = _project(current_nw, current_age, retirement_age, contrib, max(0, annual_return - 0.02), inflation_rate, years_to_retirement, current_year)
    optimistic = _project(current_nw, current_age, retirement_age, contrib, annual_return + 0.02, inflation_rate, years_to_retirement, current_year)

    # 4% rule retirement target: 25× annual spending (estimate from FIRE defaults)
    retirement_target = FIRE.DEFAULT_ANNUAL_SPENDING * FIRE.FI_MULTIPLIER

    projected_at_retirement = baseline[-1].net_worth if baseline else current_nw
    on_track = projected_at_retirement >= retirement_target

    return NetWorthForecastResponse(
        current_net_worth=current_nw,
        current_age=current_age,
        retirement_age=retirement_age,
        years_to_retirement=years_to_retirement,
        baseline=baseline,
        pessimistic=pessimistic,
        optimistic=optimistic,
        retirement_target=retirement_target,
        on_track=on_track,
        annual_contribution_used=contrib,
        annual_return_used=annual_return,
    )
