"""Rule API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.rule import Rule, RuleCondition, RuleAction
from app.models.transaction import Transaction
from app.schemas.rule import RuleCreate, RuleResponse, RuleUpdate
from app.services.rule_engine import RuleEngine

router = APIRouter()


class ApplyRuleRequest(BaseModel):
    """Request to apply a rule to transactions."""
    transaction_ids: Optional[List[str]] = None  # If None, applies to all transactions


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new rule."""
    # Create rule
    rule = Rule(
        organization_id=current_user.organization_id,
        name=rule_data.name,
        description=rule_data.description,
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
        action = RuleAction(
            rule_id=rule.id,
            action_type=action_data.action_type,
            action_value=action_data.action_value,
        )
        db.add(action)

    await db.commit()
    await db.refresh(rule)

    # Load relationships
    result = await db.execute(
        select(Rule)
        .options(joinedload(Rule.conditions), joinedload(Rule.actions))
        .where(Rule.id == rule.id)
    )
    rule = result.unique().scalar_one()
    return rule


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a rule."""
    result = await db.execute(
        select(Rule).where(
            Rule.id == rule_id,
            Rule.organization_id == current_user.organization_id,
        )
    )
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update fields
    if rule_data.name is not None:
        rule.name = rule_data.name
    if rule_data.description is not None:
        rule.description = rule_data.description
    if rule_data.is_active is not None:
        rule.is_active = rule_data.is_active
    if rule_data.priority is not None:
        rule.priority = rule_data.priority

    await db.commit()
    await db.refresh(rule)

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a rule."""
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


@router.post("/{rule_id}/apply")
async def apply_rule(
    rule_id: UUID,
    request: ApplyRuleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a rule to transactions."""
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
    count = await engine.apply_rule_to_transactions(rule, request.transaction_ids)

    return {"applied_count": count, "message": f"Applied rule to {count} transaction(s)"}


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

    # Get all transactions for this organization
    result = await db.execute(
        select(Transaction).where(
            Transaction.organization_id == current_user.organization_id
        )
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
    }
