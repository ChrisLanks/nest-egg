"""Rule API endpoints."""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
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
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from app.services.dividend_detection_service import DividendDetectionService
from app.services.input_sanitization_service import input_sanitization_service
from app.services.rate_limit_service import get_rate_limit_service
from app.services.rule_engine import RuleEngine
from app.services.rule_template_service import rule_template_service

router = APIRouter()
rate_limit_service = get_rate_limit_service()


class ApplyRuleRequest(BaseModel):
    """Request to apply a rule to transactions."""

    transaction_ids: Optional[List[str]] = Field(default=None, max_length=500)  # If None, applies to all transactions


class RuleTemplate(str, Enum):
    coffee_shops = "coffee_shops"
    subscriptions = "subscriptions"
    large_purchase_alert = "large_purchase_alert"


class RuleFromTemplateRequest(BaseModel):
    template: RuleTemplate


class ApplyRuleResponse(BaseModel):
    applied_count: int
    message: str


@router.get("/", response_model=List[RuleResponse])
async def list_rules(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all rules for the current user's organization."""
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.organization_id == current_user.organization_id)
        .order_by(Rule.priority.desc(), Rule.name)
    )
    rules = result.unique().scalars().all()
    return rules


@router.post("/", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule_data: RuleCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new rule.
    Rate limited to 20 rule creations per hour to prevent abuse.
    """
    # Rate limit: 20 rule creations per hour per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=20,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    # Sanitize user text input
    sanitized_name = (
        input_sanitization_service.sanitize_html(rule_data.name)
        if rule_data.name
        else rule_data.name
    )
    sanitized_description = (
        input_sanitization_service.sanitize_html(rule_data.description)
        if rule_data.description
        else rule_data.description
    )

    # Create rule
    rule = Rule(
        organization_id=current_user.organization_id,
        name=sanitized_name,
        description=sanitized_description,
        match_type=rule_data.match_type,
        apply_to=rule_data.apply_to,
        priority=rule_data.priority,
        is_active=rule_data.is_active,
    )
    db.add(rule)
    await db.flush()

    # Create conditions
    for condition_data in rule_data.conditions:
        condition = RuleCondition(
            rule_id=rule.id,
            field=condition_data.field,
            operator=condition_data.operator,
            value=condition_data.value,
            value_max=condition_data.value_max,
        )
        db.add(condition)

    # Create actions
    for action_data in rule_data.actions:
        sanitized_action_value = (
            input_sanitization_service.sanitize_html(action_data.action_value)
            if action_data.action_value
            else action_data.action_value
        )
        action = RuleAction(
            rule_id=rule.id,
            action_type=action_data.action_type,
            action_value=sanitized_action_value,
        )
        db.add(action)

    await db.commit()

    # Reload with fresh relationships
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.id == rule.id)
    )
    rule = result.unique().scalar_one()
    return rule


@router.post("/from-template", response_model=RuleResponse, status_code=201)
async def create_rule_from_template(
    body: RuleFromTemplateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a rule from a built-in template.

    Templates:
    - **coffee_shops**: Label coffee shop purchases
    - **subscriptions**: Label streaming and subscription services
    - **large_purchase_alert**: Flag transactions over $500
    """
    template_methods = {
        RuleTemplate.coffee_shops: rule_template_service.create_coffee_shops_rule,
        RuleTemplate.subscriptions: rule_template_service.create_subscriptions_rule,
        RuleTemplate.large_purchase_alert: rule_template_service.create_large_purchase_alert_rule,
    }
    method = template_methods.get(body.template)
    if not method:
        raise HTTPException(status_code=400, detail=f"Unknown template: {body.template}")

    rule = await method(db=db, user=current_user)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.id == rule.id)
    )
    return result.unique().scalar_one()


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific rule."""
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.unique().scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    return rule


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a rule.
    Rate limited to 30 rule updates per hour to prevent abuse.
    """
    # Rate limit: 30 rule updates per hour per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=30,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.unique().scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update scalar fields (sanitize text inputs)
    if rule_data.name is not None:
        rule.name = input_sanitization_service.sanitize_html(rule_data.name)
    if rule_data.description is not None:
        rule.description = input_sanitization_service.sanitize_html(rule_data.description)
    if rule_data.match_type is not None:
        rule.match_type = rule_data.match_type
    if rule_data.apply_to is not None:
        rule.apply_to = rule_data.apply_to
    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active
    if rule_data.priority is not None:
        rule.priority = rule_data.priority

    # Replace conditions if provided
    if rule_data.conditions is not None:
        for condition in list(rule.conditions):
            await db.delete(condition)
        await db.flush()
        for c in rule_data.conditions:
            db.add(
                RuleCondition(
                    rule_id=rule.id,
                    field=c.field,
                    operator=c.operator,
                    value=c.value,
                    value_max=c.value_max,
                )
            )

    # Replace actions if provided
    if rule_data.actions is not None:
        for action in list(rule.actions):
            await db.delete(action)
        await db.flush()
        for a in rule_data.actions:
            sanitized_action_value = (
                input_sanitization_service.sanitize_html(a.action_value)
                if a.action_value
                else a.action_value
            )
            db.add(
                RuleAction(
                    rule_id=rule.id,
                    action_type=a.action_type,
                    action_value=sanitized_action_value,
                )
            )

    await db.commit()

    # Load relationships
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.id == rule.id)
    )
    rule = result.unique().scalar_one()
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a rule.
    Rate limited to 20 rule deletions per hour to prevent abuse.
    """
    # Rate limit: 20 rule deletions per hour per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=20,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/apply", response_model=ApplyRuleResponse)
async def apply_rule(
    rule_id: UUID,
    request_data: ApplyRuleRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Apply a rule to transactions.
    Rate limited to 10 rule applications per hour to prevent abuse.
    """
    # Rate limit: 10 rule applications per hour per user
    await rate_limit_service.check_rate_limit(
        request=http_request,
        max_requests=10,
        window_seconds=3600,  # 1 hour
        identifier=str(current_user.id),
    )

    # Get the rule with conditions and actions
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.unique().scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Apply the rule
    engine = RuleEngine(db)
    count = await engine.apply_rule_to_transactions(rule, request_data.transaction_ids)

    return ApplyRuleResponse(applied_count=count, message=f"Applied rule to {count} transaction(s)")


@router.get("/{rule_id}/preview")
async def preview_rule(
    rule_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview which transactions would match this rule."""
    # Get the rule with conditions and actions
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.unique().scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Get transactions for this organization (capped to prevent OOM on large datasets)
    MAX_PREVIEW = 10_000
    result = await db.execute(
        select(Transaction)
        .where(Transaction.organization_id == current_user.organization_id)
        .order_by(Transaction.date.desc())
        .limit(MAX_PREVIEW)
    )
    transactions = result.scalars().all()

    # Check which transactions match
    engine = RuleEngine(db)
    matching_ids = []
    for transaction in transactions:
        if engine.matches_rule(transaction, rule):
            matching_ids.append(str(transaction.id))

    return {
        "matching_transaction_ids": matching_ids,
        "count": len(matching_ids),
        "truncated": len(transactions) >= MAX_PREVIEW,
    }


@router.post("/test", response_model=Dict[str, Any])
async def test_rule(
    rule_data: RuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Test a rule configuration without saving it.

    Returns matching transactions with previews of what would change.
    Useful for validating rule logic before creating/updating.
    """
    # Create temporary rule object (not saved to database)
    temp_rule = Rule(
        organization_id=current_user.organization_id,
        name=input_sanitization_service.sanitize_html(rule_data.name)
        if rule_data.name
        else rule_data.name,
        description=input_sanitization_service.sanitize_html(rule_data.description)
        if rule_data.description
        else rule_data.description,
        match_type=rule_data.match_type,
        apply_to=rule_data.apply_to,
        priority=rule_data.priority or 0,
        is_active=True,
    )

    # Create temporary conditions
    temp_rule.conditions = [
        RuleCondition(
            field=c.field,
            operator=c.operator,
            value=c.value,
            value_max=c.value_max,
        )
        for c in rule_data.conditions
    ]

    # Create temporary actions
    temp_rule.actions = [
        RuleAction(
            action_type=a.action_type,
            action_value=a.action_value,
        )
        for a in rule_data.actions
    ]

    # Get sample transactions (limit to recent 1000 for performance)
    result = await db.execute(
        select(Transaction)
        .where(Transaction.organization_id == current_user.organization_id)
        .order_by(Transaction.date.desc())
        .limit(1000)
    )
    transactions = result.scalars().all()

    # Test rule against transactions
    engine = RuleEngine(db)
    matching_transactions = []

    for transaction in transactions:
        if engine.matches_rule(transaction, temp_rule):
            # Build preview of what would change
            changes = []
            for action in temp_rule.actions:
                if action.action_type.value == "set_category":
                    changes.append(
                        {
                            "field": "category",
                            "from": transaction.category_primary,
                            "to": action.action_value,
                        }
                    )
                elif action.action_type.value == "set_merchant":
                    changes.append(
                        {
                            "field": "merchant",
                            "from": transaction.merchant_name,
                            "to": action.action_value,
                        }
                    )
                elif action.action_type.value == "add_label":
                    changes.append(
                        {"field": "label", "action": "add", "label_id": action.action_value}
                    )
                elif action.action_type.value == "remove_label":
                    changes.append(
                        {"field": "label", "action": "remove", "label_id": action.action_value}
                    )

            matching_transactions.append(
                {
                    "id": str(transaction.id),
                    "date": transaction.date.isoformat() if transaction.date else None,
                    "merchant": transaction.merchant_name,
                    "amount": float(transaction.amount),
                    "category": transaction.category_primary,
                    "changes": changes,
                }
            )

    return {
        "matching_count": len(matching_transactions),
        "matching_transactions": matching_transactions[:50],  # Limit to 50 for response size
        "total_tested": len(transactions),
        "message": (
            f"Rule would match {len(matching_transactions)}"
            f" of {len(transactions)} tested transactions"
        ),
    }


# ── Default rule templates ────────────────────────────────────────────────

# Two regex patterns (each ≤200 chars) covering dividend/income keywords.
# Split to stay within the rule engine's per-pattern length limit.
_DIVIDEND_REGEX_1 = (
    r"\b(dividend|div (payment|reinv)|reinvest div|drip"
    r"|cash div|ord div|qual div|non-?qual div"
    r"|cap ?gain dist|capital gain dist"
    r"|[ls]t cap gain|return of cap)"
)
_DIVIDEND_REGEX_2 = (
    r"\b(bond int(erest)?|interest payment" r"|int income|money market (int|income))"
)

_DIVIDEND_RULE_NAME = "Dividend Income Detection"


@router.post("/seed-dividend-detection", response_model=RuleResponse)
async def seed_dividend_detection_rule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create the default Dividend Income Detection rule.

    Idempotent — returns the existing rule if one with this name exists.
    The rule uses regex matching on transaction descriptions and category
    keywords to auto-apply the system "Dividend Income" label.
    Users can edit or disable it like any other rule.
    """
    org_id = current_user.organization_id

    # Check if rule already exists
    existing = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.organization_id == org_id, Rule.name == _DIVIDEND_RULE_NAME)
    )
    existing_rule = existing.unique().scalar_one_or_none()
    if existing_rule:
        return existing_rule

    # Ensure the system label exists and get its ID
    detector = DividendDetectionService(db)
    label = await detector.ensure_system_label(org_id)

    # Create the rule
    rule = Rule(
        organization_id=org_id,
        name=_DIVIDEND_RULE_NAME,
        description=(
            "Auto-labels dividend, interest, and capital gain "
            "transactions. Edit the patterns below to customize."
        ),
        match_type=RuleMatchType.ANY,
        apply_to=RuleApplyTo.BOTH,
        priority=10,
        is_active=True,
    )
    db.add(rule)
    await db.flush()

    # Conditions — ANY match triggers the rule
    conditions = [
        RuleCondition(
            rule_id=rule.id,
            field=ConditionField.DESCRIPTION,
            operator=ConditionOperator.REGEX,
            value=_DIVIDEND_REGEX_1,
        ),
        RuleCondition(
            rule_id=rule.id,
            field=ConditionField.DESCRIPTION,
            operator=ConditionOperator.REGEX,
            value=_DIVIDEND_REGEX_2,
        ),
        RuleCondition(
            rule_id=rule.id,
            field=ConditionField.CATEGORY,
            operator=ConditionOperator.CONTAINS,
            value="dividend",
        ),
        RuleCondition(
            rule_id=rule.id,
            field=ConditionField.CATEGORY,
            operator=ConditionOperator.CONTAINS,
            value="interest",
        ),
    ]
    for c in conditions:
        db.add(c)

    # Action — add the system "Dividend Income" label
    action = RuleAction(
        rule_id=rule.id,
        action_type=ActionType.ADD_LABEL,
        action_value=str(label.id),
    )
    db.add(action)

    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.id == rule.id)
    )
    return result.unique().scalar_one()
