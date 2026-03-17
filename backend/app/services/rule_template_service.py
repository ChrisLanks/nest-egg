"""Pre-built rule templates for common transaction categorization patterns."""

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rule import (
    ActionType,
    ConditionField,
    ConditionOperator,
    Rule,
    RuleAction,
    RuleApplyTo,
    RuleCondition,
    RuleMatchType,
)
from app.models.user import User


class RuleTemplateService:
    """Creates pre-configured rules from templates."""

    @staticmethod
    async def create_coffee_shops_rule(
        db: AsyncSession,
        user: User,
    ) -> Rule:
        """Label coffee shop transactions automatically."""
        merchants = [
            "starbucks",
            "dunkin",
            "peets",
            "dutch bros",
            "caribou",
            "tim hortons",
            "philz",
            "blue bottle",
        ]
        return await RuleTemplateService._create_merchant_label_rule(
            db=db,
            user=user,
            name="Coffee Shops",
            description="Auto-label coffee shop purchases.",
            merchants=merchants,
            label="Coffee",
        )

    @staticmethod
    async def create_subscriptions_rule(
        db: AsyncSession,
        user: User,
    ) -> Rule:
        """Label recurring subscription transactions."""
        merchants = [
            "netflix",
            "spotify",
            "hulu",
            "disney+",
            "apple.com/bill",
            "youtube premium",
            "amazon prime",
            "hbo max",
            "paramount+",
            "peacock",
        ]
        return await RuleTemplateService._create_merchant_label_rule(
            db=db,
            user=user,
            name="Subscriptions",
            description="Auto-label streaming and subscription services.",
            merchants=merchants,
            label="Subscription",
        )

    @staticmethod
    async def create_large_purchase_alert_rule(
        db: AsyncSession,
        user: User,
    ) -> Rule:
        """Label transactions over $500 as large purchases."""
        rule = Rule(
            organization_id=user.organization_id,
            name="Large Purchases",
            description="Flag transactions over $500 for review.",
            match_type=RuleMatchType.ALL,
            apply_to=RuleApplyTo.BOTH,
            is_active=True,
            priority=0,
        )
        rule.conditions = [
            RuleCondition(
                field=ConditionField.AMOUNT,
                operator=ConditionOperator.LESS_THAN,
                value="-500",
            ),
        ]
        rule.actions = [
            RuleAction(
                action_type=ActionType.ADD_LABEL,
                action_value="Large Purchase",
            ),
        ]

        db.add(rule)
        await db.flush()
        await db.refresh(rule, attribute_names=["conditions", "actions"])
        return rule

    @staticmethod
    async def _create_merchant_label_rule(
        db: AsyncSession,
        user: User,
        name: str,
        description: str,
        merchants: List[str],
        label: str,
    ) -> Rule:
        """Helper: create an ANY-match rule that labels transactions by merchant name."""
        rule = Rule(
            organization_id=user.organization_id,
            name=name,
            description=description,
            match_type=RuleMatchType.ANY,
            apply_to=RuleApplyTo.BOTH,
            is_active=True,
            priority=0,
        )

        rule.conditions = [
            RuleCondition(
                field=ConditionField.MERCHANT_NAME,
                operator=ConditionOperator.CONTAINS,
                value=merchant,
            )
            for merchant in merchants
        ]

        rule.actions = [
            RuleAction(
                action_type=ActionType.ADD_LABEL,
                action_value=label,
            ),
        ]

        db.add(rule)
        await db.flush()
        await db.refresh(rule, attribute_names=["conditions", "actions"])
        return rule


rule_template_service = RuleTemplateService()
