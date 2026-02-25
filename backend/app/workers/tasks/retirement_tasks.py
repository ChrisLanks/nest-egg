"""
Celery tasks for retirement simulation background computation.

Allows large simulation runs (>1000 sims) to be processed in the background
without blocking the API request. The API endpoint dispatches the task and
returns immediately; the frontend polls for results.
"""

import asyncio
import logging

from sqlalchemy import select

from app.workers.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.models.retirement import RetirementScenario
from app.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(name="run_retirement_simulation")
def run_retirement_simulation(scenario_id: str, user_id: str):
    """
    Run Monte Carlo simulation for a retirement scenario in the background.

    Called from the API when the scenario requests more than the inline
    threshold (e.g., >2000 simulations).
    """
    async def _run():
        async with AsyncSessionLocal() as db:
            # Load scenario with life events
            result = await db.execute(
                select(RetirementScenario).where(
                    RetirementScenario.id == scenario_id,
                )
            )
            scenario = result.scalar_one_or_none()
            if not scenario:
                logger.warning(
                    "run_retirement_simulation: scenario %s not found, skipping",
                    scenario_id,
                )
                return

            # Load life events (may not be eagerly loaded)
            await db.refresh(scenario, ["life_events"])

            user_result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                logger.warning(
                    "run_retirement_simulation: user %s not found, skipping",
                    user_id,
                )
                return

            if not user.birthdate:
                logger.warning(
                    "run_retirement_simulation: user %s has no birthdate, skipping",
                    user_id,
                )
                return

            # Import here to avoid circular imports
            from app.services.retirement.monte_carlo_service import RetirementMonteCarloService

            sim_result = await RetirementMonteCarloService.run_simulation(
                db=db, scenario=scenario, user=user
            )
            await db.commit()
            logger.info(
                "run_retirement_simulation: completed for scenario=%s "
                "success_rate=%.1f%% compute_time=%dms",
                scenario_id,
                float(sim_result.success_rate),
                sim_result.compute_time_ms or 0,
            )

    asyncio.run(_run())
