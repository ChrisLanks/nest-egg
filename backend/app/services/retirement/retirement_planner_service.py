"""Retirement planner orchestration service."""

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
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


class RetirementPlannerService:
    """Core orchestration service for retirement planning."""

    @staticmethod
    async def compute_household_member_hash(
        db: AsyncSession, organization_id: str
    ) -> tuple[str, list[str]]:
        """Return (hash, sorted_member_id_list) for active org members."""
        from app.models.user import User

        result = await db.execute(
            select(User.id)
            .where(
                User.organization_id == organization_id,
                User.is_active == True,  # noqa: E712
            )
            .order_by(User.id)
        )
        member_ids = [str(row[0]) for row in result.all()]
        hash_str = hashlib.sha256(",".join(member_ids).encode()).hexdigest()
        return hash_str, member_ids

    @staticmethod
    def compute_selective_member_hash(member_ids: list[str]) -> str:
        """Compute hash for an explicit subset of members (no DB query)."""
        sorted_ids = sorted(member_ids)
        return hashlib.sha256(",".join(sorted_ids).encode()).hexdigest()

    @staticmethod
    async def list_scenarios(
        db: AsyncSession,
        organization_id: str,
        user_id: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[RetirementScenario]:
        """List scenarios for an organization, optionally filtered by user."""
        conditions = [RetirementScenario.organization_id == organization_id]
        if user_id:
            conditions.append(RetirementScenario.user_id == user_id)
        if not include_archived:
            conditions.append(RetirementScenario.is_archived.is_(False))

        result = await db.execute(
            select(RetirementScenario)
            .where(and_(*conditions))
            .order_by(
                RetirementScenario.is_archived.asc(),
                RetirementScenario.is_default.desc(),
                RetirementScenario.updated_at.desc(),
            )
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
        member_ids: Optional[list[str]] = None,
        **kwargs,
    ) -> RetirementScenario:
        """Create a new retirement scenario.

        member_ids: explicit list of member UUIDs for selective multi-user.
        If provided with 2+ entries, overrides include_all_members.
        """
        scenario = RetirementScenario(
            organization_id=organization_id,
            user_id=user_id,
            **kwargs,
        )
        db.add(scenario)
        await db.flush()

        if member_ids and len(member_ids) >= 2:
            # Selective multi-user scenario
            sorted_ids = sorted(member_ids)
            scenario.household_member_ids = json.dumps(sorted_ids)
            scenario.household_member_hash = RetirementPlannerService.compute_selective_member_hash(
                sorted_ids
            )
            scenario.include_all_members = False
            await db.flush()
        elif scenario.include_all_members:
            # Dynamic all-members scenario
            hash_str, all_ids = await RetirementPlannerService.compute_household_member_hash(
                db, organization_id
            )
            scenario.household_member_hash = hash_str
            scenario.household_member_ids = json.dumps(all_ids)
            await db.flush()

        # Eagerly load life_events for response serialization
        await db.refresh(scenario, ["life_events"])
        return scenario

    @staticmethod
    async def create_default_scenario(
        db: AsyncSession,
        user: User,
    ) -> RetirementScenario:
        """Auto-generate a starter scenario from existing user data.

        Household-aware: checks org member count to set married/couple defaults
        for healthcare (ACA couple rates, married IRMAA thresholds) and higher
        default spending. Single users get single-person defaults.
        """
        # Gather portfolio data for smart defaults
        account_data = await RetirementMonteCarloService._gather_account_data(
            db, str(user.organization_id), str(user.id)
        )

        # Check household size (>1 user in org = household/couple)
        member_count_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.organization_id == user.organization_id,
                    User.is_active.is_(True),
                )
            )
        )
        household_size = member_count_result.scalar() or 1
        is_household = household_size > 1

        # Try to get income from 401k salary fields
        annual_income = None
        if account_data.get("annual_income"):
            annual_income = account_data["annual_income"]

        # Default retirement spending: couples spend more
        if annual_income:
            spend_ratio = Decimal("0.85") if is_household else Decimal("0.80")
            default_spending = Decimal(str(annual_income)) * spend_ratio
        else:
            default_spending = Decimal("80000") if is_household else Decimal("60000")

        # Household/couple defaults
        scenario_kwargs = dict(
            organization_id=user.organization_id,
            user_id=user.id,
            name="Our Retirement Plan" if is_household else "My Retirement Plan",
            is_default=True,
            retirement_age=67,
            life_expectancy=95,
            current_annual_income=annual_income,
            annual_spending_retirement=default_spending,
            is_shared=is_household,
        )

        # If household, also set spouse SS defaults and include all members
        if is_household:
            scenario_kwargs["spouse_social_security_monthly"] = None  # Will be estimated
            scenario_kwargs["spouse_social_security_start_age"] = 67
            scenario_kwargs["include_all_members"] = True

        scenario = RetirementScenario(**scenario_kwargs)
        db.add(scenario)
        await db.flush()

        # If household-wide, compute and store member hash
        if is_household:
            hash_str, member_ids = await RetirementPlannerService.compute_household_member_hash(
                db, str(user.organization_id)
            )
            scenario.household_member_hash = hash_str
            scenario.household_member_ids = json.dumps(member_ids)
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
            if not hasattr(scenario, key):
                continue
            # Allow explicit null for nullable fields (e.g. healthcare overrides,
            # household member fields when reverting to personal plan);
            # skip null for non-nullable fields to avoid DB integrity errors.
            NULLABLE_FIELDS = {
                "household_member_ids",
                "household_member_hash",
                "spending_phases",
            }
            if value is None and not key.endswith("_override") and key not in NULLABLE_FIELDS:
                continue
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
            include_all_members=scenario.include_all_members,
            household_member_hash=scenario.household_member_hash,
            household_member_ids=scenario.household_member_ids,
            spending_phases=scenario.spending_phases,
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
        """Run simulation if inputs changed, else return cached result.

        The hash includes scenario parameters AND account data so that
        balance/contribution changes also invalidate the cache.
        """
        import hashlib as _hashlib

        # Resolve household user IDs (same logic as run_simulation)
        household_user_ids = None
        if getattr(scenario, "include_all_members", False) is True:
            _, member_ids = await RetirementPlannerService.compute_household_member_hash(
                db, str(scenario.organization_id)
            )
            if len(member_ids) > 1:
                household_user_ids = member_ids
        elif getattr(scenario, "household_member_ids", None) and isinstance(
            scenario.household_member_ids, str
        ):
            import json as _json

            stored_ids = _json.loads(scenario.household_member_ids)
            if len(stored_ids) > 1:
                household_user_ids = stored_ids

        # Gather account data for hash (lightweight — same query as simulation)
        account_data = await RetirementMonteCarloService._gather_account_data(
            db,
            str(scenario.organization_id),
            str(scenario.user_id),
            user_ids=household_user_ids,
        )
        account_hash = _hashlib.sha256(
            "|".join(
                str(account_data[k]) for k in sorted(account_data.keys()) if k != "accounts"
            ).encode()
        ).hexdigest()

        scenario_hash = _compute_scenario_hash(scenario)
        current_hash = _hashlib.sha256(f"{scenario_hash}|{account_hash}".encode()).hexdigest()

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

        # Run new simulation (pass pre-fetched data to avoid re-querying)
        return await RetirementMonteCarloService.run_simulation(
            db,
            scenario,
            user,
            account_data=account_data,
            household_user_ids=household_user_ids,
            scenario_hash=current_hash,
        )

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
            summaries.append(
                {
                    "id": scenario.id,
                    "user_id": scenario.user_id,
                    "name": scenario.name,
                    "retirement_age": scenario.retirement_age,
                    "is_default": scenario.is_default,
                    "readiness_score": latest.readiness_score if latest else None,
                    "success_rate": float(latest.success_rate) if latest else None,
                    "updated_at": scenario.updated_at,
                }
            )
        return summaries

    # --- Archival lifecycle ---

    @staticmethod
    async def archive_scenarios_for_departed_member(
        db: AsyncSession,
        organization_id: str,
        departed_user_id: str,
        departed_user_name: str = "a member",
    ) -> int:
        """Archive selective-member scenarios that include the departed user.

        Does NOT archive include_all_members=True scenarios (those use
        the staleness mechanism instead).
        Returns the number of archived scenarios.
        """
        result = await db.execute(
            select(RetirementScenario).where(
                and_(
                    RetirementScenario.organization_id == organization_id,
                    RetirementScenario.is_archived.is_(False),
                    RetirementScenario.include_all_members.is_(False),
                    RetirementScenario.household_member_ids.isnot(None),
                )
            )
        )
        scenarios = result.scalars().all()
        archived_count = 0

        for scenario in scenarios:
            stored_ids = json.loads(scenario.household_member_ids)
            if departed_user_id in stored_ids:
                scenario.is_archived = True
                scenario.archived_at = utc_now()
                scenario.archived_reason = f"Member {departed_user_name} left the household"
                archived_count += 1

        if archived_count:
            await db.flush()
        return archived_count

    @staticmethod
    async def unarchive_scenario(
        db: AsyncSession,
        scenario: RetirementScenario,
    ) -> RetirementScenario:
        """Reactivate an archived scenario.

        Validates that at least one member is still active.
        Recomputes the household member hash.
        """
        if not scenario.household_member_ids:
            # Single-user scenario — just clear archive fields
            scenario.is_archived = False
            scenario.archived_at = None
            scenario.archived_reason = None
            await db.flush()
            return scenario

        stored_ids = json.loads(scenario.household_member_ids)

        # Check how many stored members are still active
        active_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.id.in_(stored_ids),
                    User.is_active.is_(True),
                )
            )
        )
        active_count = active_result.scalar() or 0
        if active_count == 0:
            raise ValueError("Cannot unarchive: no members in this scenario are active")

        # Recompute hash for the stored member list
        scenario.household_member_hash = RetirementPlannerService.compute_selective_member_hash(
            stored_ids
        )
        scenario.is_archived = False
        scenario.archived_at = None
        scenario.archived_reason = None
        await db.flush()
        return scenario

    @staticmethod
    async def cleanup_orphaned_archived_scenarios(
        db: AsyncSession,
    ) -> int:
        """Delete archived scenarios with no active members after 30 days.

        Returns the number of deleted scenarios.
        """
        cutoff = utc_now() - timedelta(days=30)

        result = await db.execute(
            select(RetirementScenario).where(
                and_(
                    RetirementScenario.is_archived.is_(True),
                    RetirementScenario.archived_at.isnot(None),
                    RetirementScenario.archived_at < cutoff,
                )
            )
        )
        candidates = result.scalars().all()
        deleted_count = 0

        for scenario in candidates:
            if not scenario.household_member_ids:
                # Single-user archived scenario past cutoff — delete
                await db.delete(scenario)
                deleted_count += 1
                continue

            stored_ids = json.loads(scenario.household_member_ids)
            active_result = await db.execute(
                select(func.count(User.id)).where(
                    and_(
                        User.id.in_(stored_ids),
                        User.is_active.is_(True),
                    )
                )
            )
            active_count = active_result.scalar() or 0
            if active_count == 0:
                await db.delete(scenario)
                deleted_count += 1

        if deleted_count:
            await db.flush()
        return deleted_count
