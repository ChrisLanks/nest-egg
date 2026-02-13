"""Rule engine for evaluating and applying rules to transactions."""

import re
from decimal import Decimal
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.rule import (
    Rule,
    RuleCondition,
    RuleAction,
    ConditionField,
    ConditionOperator,
    ActionType,
    RuleMatchType,
)
from app.models.transaction import Transaction, Label, TransactionLabel


class RuleEngine:
    """Engine for evaluating and applying transaction rules."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def evaluate_condition(self, transaction: Transaction, condition: RuleCondition) -> bool:
        """Evaluate a single condition against a transaction."""
        # Get the field value from transaction
        if condition.field == ConditionField.MERCHANT_NAME:
            field_value = (transaction.merchant_name or "").lower()
        elif condition.field == ConditionField.AMOUNT:
            field_value = abs(float(transaction.amount))
        elif condition.field == ConditionField.AMOUNT_EXACT:
            field_value = float(transaction.amount)
        elif condition.field == ConditionField.CATEGORY:
            field_value = (transaction.category_primary or "").lower()
        elif condition.field == ConditionField.DESCRIPTION:
            field_value = (transaction.description or "").lower()
        else:
            return False

        # Handle amount comparisons
        if condition.field in [ConditionField.AMOUNT, ConditionField.AMOUNT_EXACT]:
            try:
                condition_value = float(condition.value)
            except (ValueError, TypeError):
                return False

            if condition.operator == ConditionOperator.EQUALS:
                return abs(field_value - condition_value) < 0.01
            elif condition.operator == ConditionOperator.GREATER_THAN:
                return field_value > condition_value
            elif condition.operator == ConditionOperator.LESS_THAN:
                return field_value < condition_value
            elif condition.operator == ConditionOperator.BETWEEN:
                if not condition.value_max:
                    return False
                try:
                    max_value = float(condition.value_max)
                    return condition_value <= field_value <= max_value
                except (ValueError, TypeError):
                    return False
            else:
                return False

        # Handle string comparisons
        condition_value = condition.value.lower()

        if condition.operator == ConditionOperator.EQUALS:
            return field_value == condition_value
        elif condition.operator == ConditionOperator.CONTAINS:
            return condition_value in field_value
        elif condition.operator == ConditionOperator.STARTS_WITH:
            return field_value.startswith(condition_value)
        elif condition.operator == ConditionOperator.ENDS_WITH:
            return field_value.endswith(condition_value)
        elif condition.operator == ConditionOperator.REGEX:
            try:
                return bool(re.search(condition_value, field_value, re.IGNORECASE))
            except re.error:
                return False

        return False

    def matches_rule(self, transaction: Transaction, rule: Rule) -> bool:
        """Check if a transaction matches a rule's conditions."""
        if not rule.conditions:
            return False

        if rule.match_type == RuleMatchType.ALL:
            # All conditions must match (AND)
            return all(
                self.evaluate_condition(transaction, condition)
                for condition in rule.conditions
            )
        else:
            # Any condition can match (OR)
            return any(
                self.evaluate_condition(transaction, condition)
                for condition in rule.conditions
            )

    async def apply_action(
        self, transaction: Transaction, action: RuleAction, rule_id: str
    ) -> bool:
        """Apply a single action to a transaction."""
        try:
            if action.action_type == ActionType.SET_CATEGORY:
                transaction.category_primary = action.action_value
                return True

            elif action.action_type == ActionType.SET_MERCHANT:
                transaction.merchant_name = action.action_value
                return True

            elif action.action_type == ActionType.ADD_LABEL:
                # Check if label exists
                result = await self.db.execute(
                    select(Label).where(Label.id == action.action_value)
                )
                label = result.scalar_one_or_none()
                if not label:
                    return False

                # Check if label already applied
                result = await self.db.execute(
                    select(TransactionLabel).where(
                        TransactionLabel.transaction_id == transaction.id,
                        TransactionLabel.label_id == action.action_value,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return False  # Already has this label

                # Add label
                txn_label = TransactionLabel(
                    transaction_id=transaction.id,
                    label_id=action.action_value,
                    applied_by_rule_id=rule_id,
                )
                self.db.add(txn_label)
                return True

            elif action.action_type == ActionType.REMOVE_LABEL:
                # Remove label
                result = await self.db.execute(
                    select(TransactionLabel).where(
                        TransactionLabel.transaction_id == transaction.id,
                        TransactionLabel.label_id == action.action_value,
                    )
                )
                txn_label = result.scalar_one_or_none()
                if txn_label:
                    await self.db.delete(txn_label)
                    return True
                return False

        except Exception as e:
            print(f"Error applying action: {e}")
            return False

        return False

    async def apply_rule_to_transaction(
        self, transaction: Transaction, rule: Rule
    ) -> bool:
        """Apply a rule to a single transaction if it matches."""
        if not rule.is_active:
            return False

        if not self.matches_rule(transaction, rule):
            return False

        # Apply all actions
        applied = False
        for action in rule.actions:
            if await self.apply_action(transaction, action, str(rule.id)):
                applied = True

        return applied

    async def apply_rule_to_transactions(
        self, rule: Rule, transaction_ids: List[str] = None
    ) -> int:
        """Apply a rule to multiple transactions. Returns count of affected transactions."""
        # Build query for transactions
        query = select(Transaction).where(
            Transaction.organization_id == rule.organization_id
        )

        # Filter by transaction IDs if provided
        if transaction_ids:
            query = query.where(Transaction.id.in_(transaction_ids))

        result = await self.db.execute(query)
        transactions = result.scalars().all()

        # Apply rule to each transaction
        count = 0
        for transaction in transactions:
            if await self.apply_rule_to_transaction(transaction, rule):
                count += 1

        # Update rule statistics
        if count > 0:
            rule.times_applied += count
            from datetime import datetime
            rule.last_applied_at = datetime.utcnow()

        await self.db.commit()
        return count

    async def apply_all_rules_to_transaction(
        self, transaction: Transaction
    ) -> List[str]:
        """Apply all active rules to a transaction. Returns list of rule IDs that were applied."""
        # Get all active rules for this organization, ordered by priority
        result = await self.db.execute(
            select(Rule)
            .options(joinedload(Rule.conditions), joinedload(Rule.actions))
            .where(
                Rule.organization_id == transaction.organization_id,
                Rule.is_active == True,
            )
            .order_by(Rule.priority.desc(), Rule.created_at)
        )
        rules = result.unique().scalars().all()

        applied_rule_ids = []
        for rule in rules:
            if await self.apply_rule_to_transaction(transaction, rule):
                applied_rule_ids.append(str(rule.id))

        await self.db.commit()
        return applied_rule_ids
