"""Portfolio stress testing API endpoints."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import STRESS_TEST
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.stress_test_service import StressTestService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/scenarios",
    summary="List available stress test scenarios",
    description="Returns all hardcoded stress scenario keys and labels. No DB required.",
)
async def list_scenarios(
    current_user: User = Depends(get_current_user),
):
    """Returns available scenario keys and human-readable labels."""
    return [
        {"scenario_key": key, "label": scenario.get("label", key)}
        for key, scenario in STRESS_TEST.SCENARIOS.items()
    ]


@router.get(
    "/run",
    summary="Run a single stress test scenario",
    description=(
        "Applies a named historical or hypothetical stress scenario to the user's "
        "current portfolio composition. Returns pre/post values by asset class."
    ),
)
async def run_scenario(
    scenario_key: str = Query(..., description="Scenario key (e.g. gfc_2008, dot_com_2000)"),
    user_id: Optional[UUID] = Query(None, description="Filter to a specific user (household member)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Runs a single stress scenario against the portfolio."""
    portfolio = await StressTestService.get_portfolio_composition(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
    )
    try:
        return StressTestService.run_scenario(portfolio, scenario_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get(
    "/run-all",
    summary="Run all stress test scenarios",
    description=(
        "Applies every hardcoded stress scenario to the current portfolio and returns "
        "results sorted from worst to best outcome."
    ),
)
async def run_all_scenarios(
    user_id: Optional[UUID] = Query(None, description="Filter to a specific user (household member)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Runs all stress scenarios against the portfolio, sorted worst to best."""
    return await StressTestService.run_all_scenarios(
        db=db,
        organization_id=current_user.organization_id,
        user_id=user_id,
    )
