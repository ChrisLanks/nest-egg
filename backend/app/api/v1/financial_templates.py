"""Financial templates API — list and activate pre-built financial setups."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.user import User
from app.services.financial_templates_service import financial_templates_service
from app.services.rule_template_service import rule_template_service
from app.services.savings_goal_service import savings_goal_service



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])


class TemplateInfo(BaseModel):
    id: str
    category: str
    name: str
    description: str
    is_activated: bool


@router.get("/", response_model=List[TemplateInfo])
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available financial templates with activation status."""
    return await financial_templates_service.list_templates(db=db, user=current_user)


@router.post("/{template_id}/activate", response_model=dict)
async def activate_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activate a financial template by creating the corresponding resource.

    template_id format: "category:name" — e.g. "goal:emergency_fund", "rule:coffee_shops"
    """
    # Goal templates
    goal_methods = {
        "goal:emergency_fund": savings_goal_service.create_emergency_fund_goal,
        "goal:vacation_fund": savings_goal_service.create_vacation_fund_goal,
        "goal:home_down_payment": savings_goal_service.create_home_down_payment_goal,
        "goal:debt_payoff_reserve": savings_goal_service.create_debt_payoff_reserve_goal,
    }

    # Rule templates
    rule_methods = {
        "rule:coffee_shops": rule_template_service.create_coffee_shops_rule,
        "rule:subscriptions": rule_template_service.create_subscriptions_rule,
        "rule:large_purchase_alert": rule_template_service.create_large_purchase_alert_rule,
    }

    if template_id in goal_methods:
        await goal_methods[template_id](db=db, user=current_user)
        await db.commit()
        return {"status": "activated", "template_id": template_id}

    if template_id in rule_methods:
        await rule_methods[template_id](db=db, user=current_user)
        await db.commit()
        return {"status": "activated", "template_id": template_id}

    if template_id == "retirement:default":
        # Import here to avoid circular imports
        from app.services.retirement.retirement_planner_service import (
            retirement_planner_service,
        )

        await retirement_planner_service.create_default_scenario(db=db, user=current_user)
        await db.commit()
        return {"status": "activated", "template_id": template_id}

    if template_id == "budget:suggestions":
        # Budget suggestions are read-only — nothing to "activate".
        # The frontend handles showing suggestions automatically.
        return {
            "status": "info",
            "template_id": template_id,
            "message": "Budget suggestions appear automatically on the Budgets page.",
        }

    raise HTTPException(status_code=404, detail=f"Unknown template: {template_id}")
