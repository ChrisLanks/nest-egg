"""Retirement planner orchestration service."""

import copy
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.retirement import (
    LifeEvent,
    RetirementScenario,
    RetirementSimulationResult,
)
from app.models.user import User
from app.services.retirement.monte_carlo_service import (
    RetirementMonteCarloService,
    _compute_scenario_hash,
)
from app.utils.datetime_utils import utc_now
from app.utils.rmd_calculator import calculate_age


class RetirementPlannerService:
    """Core orchestration service for retirement planning."""

    @staticmethod
    async def list_scenarios(
        db: AsyncSession,
        organization_id: str,
        user_id: Optional[str] = None,
    ) -> List[RetirementScenario]:
        """List all scenarios for an organization, optionally filtered by user."""
        conditions = [RetirementScenario.organization_id == organization_id]
        if user_id:
            conditions.append(RetirementScenario.user_id == user_id)

        result = await db.execute(
            select(RetirementScenario)
            .where(and_(*conditions))
            .order_by(RetirementScenario.is_default.desc(), RetirementScenario.updated_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_scenario(
        db: AsyncSession,
        scenario_id: UUID,
        organization_id: str,
    ) -> Optional[RetirementScenario]:
        """Get a scenario by ID with life events eagerly loaded."""
        result = await db.execute(
            select(RetirementScenario)
            .options(joinedload(RetirementScenario.life_events))
            .where(
                and_(
                    RetirementScenario.id == scenario_id,
                    RetirementScenario.organization_id == organization_id,
                )
            )
        )
        return result.unique().scalars().first()

    @staticmethod
    async def create_scenario(
        db: AsyncSession,
        organization_id: str,
        user_id: str,
        **kwargs,
    ) -> RetirementScenario:
        """Create a new retirement scenario."""
        scenario = RetirementScenario(
            organization_id=organization_id,
            user_id=user_id,
            **kwargs,
        )
        db.add(scenario)
        await db.flush()

        # Eagerly load life_events for response serialization
        await db.refresh(scenario, ["life_events"])
        return scenario

    @staticmethod
    async def create_default_scenario(
        db: AsyncSession,
        user: User,
    ) -> RetirementScenario:
        """Auto-generate a starter scenario from existing user data."""
        current_age = calculate_age(user.birthdate) if user.birthdate else 35

        # Gather portfolio data for smart defaults
        account_data = await RetirementMonteCarloService._gather_account_data(
            db, str(user.organization_id), str(user.id)
        )

        # Try to get income from 401k salary fields
        annual_income = None
        if account_data.get("annual_income"):
            annual_income = account_data["annual_income"]

        # Default retirement spending: 80% of income or $60K
        default_spending = Decimal("60000")
        if annual_income:
            default_spending = Decimal(str(annual_income)) * Decimal("0.80")

        scenario = RetirementScenario(
            organization_id=user.organization_id,
            user_id=user.id,
            name="My Retirement Plan",
            is_default=True,
            retirement_age=67,
            life_expectancy=95,
            current_annual_income=annual_income,
            annual_spending_retirement=default_spending,
        )
        db.add(scenario)
        await db.flush()
        await db.refresh(scenario, ["life_events"])
        return scenario

    @staticmethod
    async def update_scenario(
        db: AsyncSession,
        scenario: RetirementScenario,
        updates: dict,
    ) -> RetirementScenario:
        """Update a scenario with partial data."""
        for key, value in updates.items():
            if value is not None and hasattr(scenario, key):
                setattr(scenario, key, value)
        scenario.updated_at = utc_now()
        await db.flush()
        return scenario

    @staticmethod
    async def delete_scenario(
        db: AsyncSession,
        scenario: RetirementScenario,
    ) -> None:
        """Delete a scenario and all its life events + results (cascade)."""
        await db.delete(scenario)
        await db.flush()

    @staticmethod
    async def duplicate_scenario(
        db: AsyncSession,
        scenario: RetirementScenario,
        new_name: Optional[str] = None,
    ) -> RetirementScenario:
        """Deep clone a scenario including life events."""
        new_scenario = RetirementScenario(
            organization_id=scenario.organization_id,
            user_id=scenario.user_id,
            name=new_name or f"{scenario.name} (Copy)",
            description=scenario.description,
            is_default=False,
            retirement_age=scenario.retirement_age,
            life_expectancy=scenario.life_expectancy,
            current_annual_income=scenario.current_annual_income,
            annual_spending_retirement=scenario.annual_spending_retirement,
            pre_retirement_return=scenario.pre_retirement_return,
            post_retirement_return=scenario.post_retirement_return,
            volatility=scenario.volatility,
            inflation_rate=scenario.inflation_rate,
            medical_inflation_rate=scenario.medical_inflation_rate,
            social_security_monthly=scenario.social_security_monthly,
            social_security_start_age=scenario.social_security_start_age,
            use_estimated_pia=scenario.use_estimated_pia,
            spouse_social_security_monthly=scenario.spouse_social_security_monthly,
            spouse_social_security_start_age=scenario.spouse_social_security_start_age,
            withdrawal_strategy=scenario.withdrawal_strategy,
            withdrawal_rate=scenario.withdrawal_rate,
            federal_tax_rate=scenario.federal_tax_rate,
            state_tax_rate=scenario.state_tax_rate,
            capital_gains_rate=scenario.capital_gains_rate,
            num_simulations=scenario.num_simulations,
            is_shared=scenario.is_shared,
        )
        db.add(new_scenario)
        await db.flush()

        # Clone life events
        for event in scenario.life_events:
            new_event = LifeEvent(
                scenario_id=new_scenario.id,
                name=event.name,
                category=event.category,
                start_age=event.start_age,
                end_age=event.end_age,
                annual_cost=event.annual_cost,
                one_time_cost=event.one_time_cost,
                income_change=event.income_change,
                use_medical_inflation=event.use_medical_inflation,
                custom_inflation_rate=event.custom_inflation_rate,
                is_preset=event.is_preset,
                preset_key=event.preset_key,
                sort_order=event.sort_order,
            )
            db.add(new_event)

        await db.flush()
        await db.refresh(new_scenario, ["life_events"])
        return new_scenario

    @staticmethod
    async def run_or_get_cached_simulation(
        db: AsyncSession,
        scenario: RetirementScenario,
        user: User,
    ) -> RetirementSimulationResult:
        """Run simulation if inputs changed, else return cached result."""
        current_hash = _compute_scenario_hash(scenario)

        # Check for cached result
        result = await db.execute(
            select(RetirementSimulationResult)
            .where(
                and_(
                    RetirementSimulationResult.scenario_id == scenario.id,
                    RetirementSimulationResult.scenario_hash == current_hash,
                )
            )
            .order_by(RetirementSimulationResult.computed_at.desc())
            .limit(1)
        )
        cached = result.scalars().first()
        if cached:
            return cached

        # Run new simulation
        return await RetirementMonteCarloService.run_simulation(db, scenario, user)

    @staticmethod
    async def get_latest_result(
        db: AsyncSession,
        scenario_id: UUID,
    ) -> Optional[RetirementSimulationResult]:
        """Get the most recent simulation result for a scenario."""
        result = await db.execute(
            select(RetirementSimulationResult)
            .where(RetirementSimulationResult.scenario_id == scenario_id)
            .order_by(RetirementSimulationResult.computed_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    @staticmethod
    async def get_scenario_summary_with_scores(
        db: AsyncSession,
        scenarios: List[RetirementScenario],
    ) -> list[dict]:
        """Enrich scenarios with latest readiness scores for list view."""
        summaries = []
        for scenario in scenarios:
            latest = await RetirementPlannerService.get_latest_result(db, scenario.id)
            summaries.append({
                "id": scenario.id,
                "name": scenario.name,
                "retirement_age": scenario.retirement_age,
                "is_default": scenario.is_default,
                "readiness_score": latest.readiness_score if latest else None,
                "success_rate": float(latest.success_rate) if latest else None,
                "updated_at": scenario.updated_at,
            })
        return summaries
