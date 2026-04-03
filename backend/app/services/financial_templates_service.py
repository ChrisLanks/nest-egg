"""Orchestration service for financial templates.

Lists available templates and checks activation status.
"""

from typing import List

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget
from app.models.retirement import RetirementScenario
from app.models.rule import Rule
from app.models.savings_goal import SavingsGoal
from app.models.user import User

# Template definitions — static metadata that never hits the DB.
TEMPLATES = [
    {
        "id": "goal:emergency_fund",
        "category": "goal",
        "name": "Emergency Fund",
        "description": (
            "Save 3-6 months of expenses as a safety net. "
            "Auto-calculated from your recent spending."
        ),
    },
    {
        "id": "goal:vacation_fund",
        "category": "goal",
        "name": "Vacation Fund",
        "description": ("Set aside $4,000 over the next 12 months for travel."),
    },
    {
        "id": "goal:home_down_payment",
        "category": "goal",
        "name": "Home Down Payment",
        "description": (
            "Save $60,000 (20% of a $300K home) over 5 years. " "Adjust to your local market."
        ),
    },
    {
        "id": "goal:debt_payoff_reserve",
        "category": "goal",
        "name": "Debt Payoff Reserve",
        "description": (
            "Build a 10% reserve against your total debt to "
            "accelerate payoff on your highest-rate balances."
        ),
    },
    {
        "id": "rule:coffee_shops",
        "category": "rule",
        "name": "Coffee Shops",
        "description": "Auto-label Starbucks, Dunkin, and other coffee shop purchases.",
    },
    {
        "id": "rule:subscriptions",
        "category": "rule",
        "name": "Subscriptions",
        "description": "Auto-label Netflix, Spotify, and other recurring subscriptions.",
    },
    {
        "id": "rule:large_purchase_alert",
        "category": "rule",
        "name": "Large Purchases",
        "description": "Flag any transaction over $500 for review.",
    },
    {
        "id": "retirement:default",
        "category": "retirement",
        "name": "Retirement Scenario",
        "description": (
            "Generate a starter retirement plan with Monte Carlo "
            "simulation based on your current accounts and income."
        ),
    },
    {
        "id": "budget:suggestions",
        "category": "budget",
        "name": "Smart Budget Suggestions",
        "description": (
            "Analyze your spending history and suggest budgets "
            "for your top categories with smart period detection."
        ),
    },
]


class FinancialTemplatesService:
    """Lists templates and checks which ones are already activated."""

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        user: User,
    ) -> List[dict]:
        """Return all templates with their activation status."""
        org_id = user.organization_id

        # Batch all activation checks into a few queries
        # 1. Goal names
        goal_result = await db.execute(
            select(func.lower(SavingsGoal.name)).where(
                and_(
                    SavingsGoal.organization_id == org_id,
                    SavingsGoal.is_completed.is_(False),
                )
            )
        )
        active_goal_names = {row[0] for row in goal_result.all()}

        # 2. Rule names
        rule_result = await db.execute(
            select(func.lower(Rule.name)).where(
                and_(
                    Rule.organization_id == org_id,
                    Rule.is_active.is_(True),
                )
            )
        )
        active_rule_names = {row[0] for row in rule_result.all()}

        # 3. Retirement scenario count
        retirement_count_result = await db.execute(
            select(func.count(RetirementScenario.id)).where(
                RetirementScenario.organization_id == org_id,
            )
        )
        has_retirement = (retirement_count_result.scalar() or 0) > 0

        # 4. Budget count (for suggestions — if they have >3 budgets, suggestions are "done")
        budget_count_result = await db.execute(
            select(func.count(Budget.id)).where(
                and_(
                    Budget.organization_id == org_id,
                    Budget.is_active.is_(True),
                )
            )
        )
        budget_count = budget_count_result.scalar() or 0

        # Build response
        result = []
        for t in TEMPLATES:
            is_activated = False
            tid = t["id"]

            if tid.startswith("goal:"):
                is_activated = t["name"].lower() in active_goal_names
            elif tid.startswith("rule:"):
                is_activated = t["name"].lower() in active_rule_names
            elif tid == "retirement:default":
                is_activated = has_retirement
            elif tid == "budget:suggestions":
                is_activated = budget_count > 3

            result.append({**t, "is_activated": is_activated})

        return result


financial_templates_service = FinancialTemplatesService()
