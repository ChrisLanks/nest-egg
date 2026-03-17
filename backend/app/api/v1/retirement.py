"""Retirement planning API endpoints."""

import csv
import io
import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, verify_household_member
from app.models.retirement import LifeEvent
from app.models.user import User
from app.schemas.retirement import (
    HealthcareCostBreakdown,
    HealthcareCostEstimateResponse,
    LifeEventCreate,
    LifeEventPreset,
    LifeEventPresetRequest,
    LifeEventResponse,
    LifeEventUpdate,
    ProjectionDataPoint,
    QuickSimulationRequest,
    QuickSimulationResponse,
    RetirementAccountDataResponse,
    RetirementScenarioCreate,
    RetirementScenarioResponse,
    RetirementScenarioSummary,
    RetirementScenarioUpdate,
    ScenarioComparisonItem,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    SimulationResultResponse,
    SocialSecurityEstimateResponse,
)
from app.services.input_sanitization_service import input_sanitization_service
from app.services.retirement.healthcare_cost_estimator import (
    estimate_annual_healthcare_cost,
)
from app.services.retirement.life_event_presets import (
    create_life_event_from_preset,
    get_all_presets,
)
from app.services.retirement.monte_carlo_service import RetirementMonteCarloService
from app.services.retirement.retirement_planner_service import RetirementPlannerService
from app.services.retirement.social_security_estimator import estimate_social_security
from app.utils.rmd_calculator import calculate_age

router = APIRouter()


# --- Scenario CRUD ---


@router.post("/scenarios", response_model=RetirementScenarioResponse, status_code=201)
async def create_scenario(
    data: RetirementScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new retirement scenario."""
    # Sanitize user text input
    sanitized = data.model_dump()
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    if sanitized.get("description"):
        sanitized["description"] = input_sanitization_service.sanitize_html(
            sanitized["description"]
        )
    scenario = await RetirementPlannerService.create_scenario(
        db=db,
        organization_id=str(current_user.organization_id),
        user_id=str(current_user.id),
        **sanitized,
    )
    await db.commit()
    return scenario


@router.get("/scenarios", response_model=List[RetirementScenarioSummary])
async def list_scenarios(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List retirement scenarios for a specific user in the organization."""
    target_user = user_id or str(current_user.id)
    # Verify target user belongs to the same organization
    if user_id and user_id != str(current_user.id):
        from app.models.user import User as UserModel

        target = await db.get(UserModel, user_id)
        if not target or str(target.organization_id) != str(current_user.organization_id):
            raise HTTPException(status_code=403, detail="Cannot access another organization's data")
    scenarios = await RetirementPlannerService.list_scenarios(
        db=db,
        organization_id=str(current_user.organization_id),
        user_id=target_user,
    )
    summaries = await RetirementPlannerService.get_scenario_summary_with_scores(db, scenarios)

    # Compute staleness for household-wide scenarios
    has_household = any(s.include_all_members for s in scenarios)
    current_hash = None
    if has_household:
        current_hash, _ = await RetirementPlannerService.compute_household_member_hash(
            db, str(current_user.organization_id)
        )

    for summary, scenario in zip(summaries, scenarios):
        summary["include_all_members"] = scenario.include_all_members
        if scenario.include_all_members and scenario.household_member_hash and current_hash:
            summary["is_stale"] = current_hash != scenario.household_member_hash
        else:
            summary["is_stale"] = False

    return summaries


# Static paths MUST come before parameterized {scenario_id} routes
# to prevent FastAPI from matching "default" as a UUID parameter.
@router.post("/scenarios/default", response_model=RetirementScenarioResponse, status_code=201)
async def create_default_scenario(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-generate a default scenario from user profile and accounts."""
    if not current_user.birthdate:
        raise HTTPException(
            status_code=400, detail="Please set your birthdate in preferences first"
        )

    scenario = await RetirementPlannerService.create_default_scenario(db=db, user=current_user)
    await db.commit()
    return scenario


@router.get("/scenarios/{scenario_id}", response_model=RetirementScenarioResponse)
async def get_scenario(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a scenario with all life events."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Compute staleness for household-wide scenarios
    is_stale = False
    if scenario.include_all_members and scenario.household_member_hash:
        current_hash, _ = await RetirementPlannerService.compute_household_member_hash(
            db, str(current_user.organization_id)
        )
        is_stale = current_hash != scenario.household_member_hash

    # Parse household_member_ids from JSON
    household_member_ids = None
    if scenario.household_member_ids:
        import json

        household_member_ids = json.loads(scenario.household_member_ids)

    response = RetirementScenarioResponse.model_validate(scenario)
    response.is_stale = is_stale
    response.household_member_ids = household_member_ids
    return response


@router.patch("/scenarios/{scenario_id}", response_model=RetirementScenarioResponse)
async def update_scenario(
    scenario_id: UUID,
    data: RetirementScenarioUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a retirement scenario."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot edit another user's scenario")

    # Sanitize user text input
    updates = data.model_dump(exclude_unset=True)
    if updates.get("name"):
        updates["name"] = input_sanitization_service.sanitize_html(updates["name"])
    if updates.get("description"):
        updates["description"] = input_sanitization_service.sanitize_html(updates["description"])
    updated = await RetirementPlannerService.update_scenario(
        db=db, scenario=scenario, updates=updates
    )
    await db.commit()
    return updated


@router.delete("/scenarios/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a retirement scenario."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot delete another user's scenario")

    await RetirementPlannerService.delete_scenario(db=db, scenario=scenario)
    await db.commit()


@router.post(
    "/scenarios/{scenario_id}/duplicate", response_model=RetirementScenarioResponse, status_code=201
)
async def duplicate_scenario(
    scenario_id: UUID,
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a scenario for what-if exploration."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Sanitize user text input
    sanitized_name = input_sanitization_service.sanitize_html(name) if name else name
    dup = await RetirementPlannerService.duplicate_scenario(
        db=db, scenario=scenario, new_name=sanitized_name
    )
    await db.commit()
    return dup


@router.post(
    "/scenarios/{scenario_id}/refresh-household",
    response_model=RetirementScenarioResponse,
)
async def refresh_household(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recompute the household member hash for a household-wide scenario."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if not scenario.include_all_members:
        raise HTTPException(status_code=400, detail="Scenario is not household-wide")

    hash_str, member_ids = await RetirementPlannerService.compute_household_member_hash(
        db, str(current_user.organization_id)
    )
    scenario.household_member_hash = hash_str
    scenario.household_member_ids = json.dumps(member_ids)
    await db.flush()
    await db.commit()

    # Re-fetch to get fresh life_events
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )

    response = RetirementScenarioResponse.model_validate(scenario)
    response.is_stale = False
    response.household_member_ids = member_ids
    return response


# --- Life Events ---


@router.post(
    "/scenarios/{scenario_id}/life-events", response_model=LifeEventResponse, status_code=201
)
async def add_life_event(
    scenario_id: UUID,
    data: LifeEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a life event to a scenario."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot modify another user's scenario")

    # Sanitize user text input
    sanitized = data.model_dump()
    if sanitized.get("name"):
        sanitized["name"] = input_sanitization_service.sanitize_html(sanitized["name"])
    event = LifeEvent(scenario_id=scenario.id, **sanitized)
    db.add(event)
    await db.flush()
    await db.commit()
    return event


@router.patch("/life-events/{event_id}", response_model=LifeEventResponse)
async def update_life_event(
    event_id: UUID,
    data: LifeEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a life event."""
    event = await db.get(LifeEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Life event not found")

    # Verify ownership through scenario
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=event.scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot modify another user's scenario")

    for key, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            # Sanitize text fields
            if key == "name":
                value = input_sanitization_service.sanitize_html(value)
            setattr(event, key, value)
    await db.flush()
    await db.commit()
    return event


@router.post(
    "/scenarios/{scenario_id}/life-events/from-preset",
    response_model=LifeEventResponse,
    status_code=201,
)
async def add_life_event_from_preset(
    scenario_id: UUID,
    data: LifeEventPresetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a life event from a preset template."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot modify another user's scenario")

    start_age = data.start_age or scenario.retirement_age
    event_data = create_life_event_from_preset(data.preset_key, start_age)
    if not event_data:
        raise HTTPException(status_code=400, detail=f"Unknown preset: {data.preset_key}")

    event = LifeEvent(scenario_id=scenario.id, **event_data)
    db.add(event)
    await db.flush()
    await db.commit()
    return event


@router.delete("/life-events/{event_id}", status_code=204)
async def delete_life_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a life event."""
    event = await db.get(LifeEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Life event not found")

    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=event.scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if str(scenario.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Cannot modify another user's scenario")

    await db.delete(event)
    await db.flush()
    await db.commit()


# --- Life Event Presets ---


@router.get("/life-event-presets", response_model=List[LifeEventPreset])
async def list_life_event_presets(
    current_user: User = Depends(get_current_user),
):
    """List all available life event preset templates."""
    presets = get_all_presets()
    return [LifeEventPreset(**p) for p in presets]


# --- Social Security ---


@router.get("/social-security-estimate", response_model=SocialSecurityEstimateResponse)
async def get_social_security_estimate(
    claiming_age: int = Query(default=67, ge=62, le=70),
    override_salary: Optional[float] = Query(default=None, ge=0),
    override_pia: Optional[float] = Query(default=None, ge=0),
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Estimate Social Security benefits based on user profile or overrides."""
    target_user = current_user
    if user_id and user_id != current_user.id:
        target_user = await verify_household_member(db, user_id, current_user.organization_id)

    if not target_user.birthdate:
        raise HTTPException(
            status_code=400, detail="Please set your birthdate in preferences first"
        )

    current_age = calculate_age(target_user.birthdate)
    birth_year = target_user.birthdate.year

    # Determine salary for estimation
    salary = override_salary or 0
    if salary == 0:
        # TODO: Could pull from scenario or account data
        salary = 75000  # Reasonable default

    result = estimate_social_security(
        current_salary=salary,
        current_age=current_age,
        birth_year=birth_year,
        claiming_age=claiming_age,
        manual_pia_override=override_pia,
    )

    return SocialSecurityEstimateResponse(**result)


# --- Healthcare Cost Estimate ---


@router.get("/healthcare-estimate", response_model=HealthcareCostEstimateResponse)
async def get_healthcare_estimate(
    retirement_income: float = Query(default=50000, ge=0),
    medical_inflation_rate: float = Query(default=6.0, ge=0, le=20),
    include_ltc: bool = Query(default=True),
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = current user"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Estimate healthcare costs across retirement phases."""
    target_user = current_user
    if user_id and user_id != current_user.id:
        target_user = await verify_household_member(db, user_id, current_user.organization_id)

    if not target_user.birthdate:
        raise HTTPException(
            status_code=400, detail="Please set your birthdate in preferences first"
        )

    current_age = calculate_age(target_user.birthdate)

    # Sample ages for the response
    sample_ages_list = [55, 60, 65, 70, 75, 80, 85, 90, 95]
    sample_ages_list = [a for a in sample_ages_list if a >= current_age]

    samples = []
    pre_65_total = 0.0
    medicare_total = 0.0
    ltc_total = 0.0

    for age in sample_ages_list:
        costs = estimate_annual_healthcare_cost(
            age=age,
            retirement_income=retirement_income,
            current_age=current_age,
            medical_inflation_rate=medical_inflation_rate,
            include_ltc=include_ltc,
        )
        samples.append(HealthcareCostBreakdown(age=age, **costs))

        if age < 65:
            pre_65_total += costs["total"]
        elif age < 85:
            medicare_total += costs["total"]
        else:
            ltc_total += costs["total"]

    # Rough lifetime total (sample * gap years)
    total_lifetime = pre_65_total + medicare_total + ltc_total

    return HealthcareCostEstimateResponse(
        pre_65_annual=samples[0].total if samples and samples[0].age < 65 else 0,
        medicare_annual=next((s.total for s in samples if 65 <= s.age < 85), 0),
        ltc_annual=next((s.total for s in samples if s.age >= 85), 0),
        total_lifetime=round(total_lifetime, 2),
        sample_ages=samples,
    )


# --- Account Data ---


@router.get("/account-data", response_model=RetirementAccountDataResponse)
async def get_account_data(
    user_id: Optional[str] = None,
    include_all_members: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current account balances and contributions for the retirement planner."""
    target_user = user_id or str(current_user.id)
    # Verify target user belongs to the same organization
    if user_id and user_id != str(current_user.id):
        from app.models.user import User as UserModel

        target = await db.get(UserModel, user_id)
        if not target or str(target.organization_id) != str(current_user.organization_id):
            raise HTTPException(status_code=403, detail="Cannot access another organization's data")

    # Gather household-wide data when requested
    household_user_ids = None
    if include_all_members:
        _, household_user_ids = await RetirementPlannerService.compute_household_member_hash(
            db, str(current_user.organization_id)
        )

    data = await RetirementMonteCarloService._gather_account_data(
        db,
        str(current_user.organization_id),
        target_user,
        user_ids=household_user_ids,
    )
    return RetirementAccountDataResponse(
        total_portfolio=float(data["total_portfolio"]),
        taxable_balance=float(data["taxable_balance"]),
        pre_tax_balance=float(data["pre_tax_balance"]),
        roth_balance=float(data["roth_balance"]),
        hsa_balance=float(data["hsa_balance"]),
        cash_balance=float(data.get("cash_balance", 0)),
        pension_monthly=float(data["pension_monthly"]),
        annual_contributions=float(data["annual_contributions"]),
        employer_match_annual=float(data["employer_match_annual"]),
        annual_income=float(data["annual_income"]),
        accounts=data.get("accounts", []),
    )


# --- Simulation ---


@router.post("/scenarios/{scenario_id}/simulate", response_model=SimulationResultResponse)
async def run_simulation(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run Monte Carlo simulation for a scenario (or return cached if unchanged)."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if not current_user.birthdate:
        raise HTTPException(
            status_code=400, detail="Please set your birthdate in preferences first"
        )

    result = await RetirementPlannerService.run_or_get_cached_simulation(
        db=db, scenario=scenario, user=current_user
    )
    await db.commit()
    return _format_simulation_result(result)


@router.get("/scenarios/{scenario_id}/results", response_model=SimulationResultResponse)
async def get_latest_results(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the latest simulation results for a scenario."""
    # Verify access
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = await RetirementPlannerService.get_latest_result(db=db, scenario_id=scenario_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="No simulation results yet. Run a simulation first."
        )

    return _format_simulation_result(result)


# --- Quick Simulate (no DB save) ---


@router.post("/quick-simulate", response_model=QuickSimulationResponse)
async def quick_simulate(
    data: QuickSimulationRequest,
    current_user: User = Depends(get_current_user),
):
    """Lightweight simulation for real-time slider exploration. No DB persistence."""
    result = RetirementMonteCarloService.run_quick_simulation(
        current_portfolio=float(data.current_portfolio),
        annual_contributions=float(data.annual_contributions),
        current_age=data.current_age,
        retirement_age=data.retirement_age,
        life_expectancy=data.life_expectancy,
        annual_spending=float(data.annual_spending),
        pre_retirement_return=data.pre_retirement_return,
        post_retirement_return=data.post_retirement_return,
        volatility=data.volatility,
        inflation_rate=data.inflation_rate,
        social_security_monthly=data.social_security_monthly or 0,
        social_security_start_age=data.social_security_start_age,
    )

    return QuickSimulationResponse(
        success_rate=result["success_rate"],
        readiness_score=result["readiness_score"],
        projections=[ProjectionDataPoint(**p) for p in result["projections"]],
        median_depletion_age=result["median_depletion_age"],
    )


# --- Scenario Comparison ---


@router.post("/compare", response_model=ScenarioComparisonResponse)
async def compare_scenarios(
    data: ScenarioComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compare multiple scenarios side-by-side."""
    items = []
    for scenario_id in data.scenario_ids:
        scenario = await RetirementPlannerService.get_scenario(
            db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
        )
        if not scenario:
            raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found")

        result = await RetirementPlannerService.get_latest_result(db=db, scenario_id=scenario_id)
        if not result:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"No simulation results for scenario"
                    f" '{scenario.name}'. Run simulation first."
                ),
            )

        projections = json.loads(result.projections_json)
        items.append(
            ScenarioComparisonItem(
                scenario_id=scenario.id,
                scenario_name=scenario.name,
                retirement_age=scenario.retirement_age,
                readiness_score=result.readiness_score,
                success_rate=float(result.success_rate),
                median_portfolio_at_end=float(result.median_portfolio_at_end)
                if result.median_portfolio_at_end
                else None,
                projections=[ProjectionDataPoint(**p) for p in projections],
            )
        )

    return ScenarioComparisonResponse(scenarios=items)


# --- CSV Export ---


@router.get("/scenarios/{scenario_id}/export-csv")
async def export_projections_csv(
    scenario_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export year-by-year projections as CSV."""
    scenario = await RetirementPlannerService.get_scenario(
        db=db, scenario_id=scenario_id, organization_id=str(current_user.organization_id)
    )
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = await RetirementPlannerService.get_latest_result(db=db, scenario_id=scenario_id)
    if not result:
        raise HTTPException(
            status_code=404, detail="No simulation results yet. Run a simulation first."
        )

    projections = json.loads(result.projections_json)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Age",
            "10th Percentile",
            "25th Percentile",
            "Median (50th)",
            "75th Percentile",
            "90th Percentile",
            "Depletion Probability %",
        ]
    )
    for p in projections:
        writer.writerow(
            [
                p["age"],
                round(p["p10"], 2),
                round(p["p25"], 2),
                round(p["p50"], 2),
                round(p["p75"], 2),
                round(p["p90"], 2),
                round(p["depletion_pct"], 1),
            ]
        )

    output.seek(0)
    safe_name = scenario.name.replace(" ", "_").replace("/", "_")[:50]
    filename = f"retirement_{safe_name}_projections.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- Helpers ---


def _format_simulation_result(result) -> SimulationResultResponse:
    """Format a DB result into the API response."""
    projections = json.loads(result.projections_json)
    withdrawal_comparison = (
        json.loads(result.withdrawal_comparison_json) if result.withdrawal_comparison_json else None
    )

    return SimulationResultResponse(
        id=result.id,
        scenario_id=result.scenario_id,
        computed_at=result.computed_at,
        num_simulations=result.num_simulations,
        compute_time_ms=result.compute_time_ms,
        success_rate=float(result.success_rate),
        readiness_score=result.readiness_score,
        median_portfolio_at_retirement=(
            float(result.median_portfolio_at_retirement)
            if result.median_portfolio_at_retirement
            else None
        ),
        median_portfolio_at_end=float(result.median_portfolio_at_end)
        if result.median_portfolio_at_end
        else None,
        median_depletion_age=result.median_depletion_age,
        estimated_pia=float(result.estimated_pia) if result.estimated_pia else None,
        projections=[ProjectionDataPoint(**p) for p in projections],
        withdrawal_comparison=withdrawal_comparison,
    )
