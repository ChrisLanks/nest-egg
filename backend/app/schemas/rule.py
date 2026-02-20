"""Rule schemas."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.rule import (
    RuleMatchType,
    RuleApplyTo,
    ConditionField,
    ConditionOperator,
    ActionType,
)


class RuleConditionCreate(BaseModel):
    """Rule condition creation schema."""

    field: ConditionField
    operator: ConditionOperator
    value: str
    value_max: Optional[str] = None


class RuleActionCreate(BaseModel):
    """Rule action creation schema."""

    action_type: ActionType
    action_value: str

    @field_validator('action_value')
    @classmethod
    def action_value_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Action value cannot be empty')
        return v


class RuleCreate(BaseModel):
    """Rule creation schema."""

    name: str
    description: Optional[str] = None
    match_type: RuleMatchType = RuleMatchType.ALL
    apply_to: RuleApplyTo = RuleApplyTo.NEW_ONLY
    priority: int = 0
    is_active: bool = True
    conditions: List[RuleConditionCreate]
    actions: List[RuleActionCreate]


class RuleConditionResponse(RuleConditionCreate):
    """Rule condition response schema."""

    id: UUID
    rule_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleActionResponse(BaseModel):
    """Rule action response schema."""

    action_type: ActionType
    action_value: str
    id: UUID
    rule_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class RuleResponse(BaseModel):
    """Rule response schema."""

    id: UUID
    organization_id: UUID
    name: str
    description: Optional[str] = None
    match_type: RuleMatchType
    apply_to: RuleApplyTo
    priority: int
    is_active: bool
    times_applied: int
    last_applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    conditions: List[RuleConditionResponse] = []
    actions: List[RuleActionResponse] = []

    model_config = {"from_attributes": True}


class RuleUpdate(BaseModel):
    """Rule update schema."""

    name: Optional[str] = None
    description: Optional[str] = None
    match_type: Optional[RuleMatchType] = None
    apply_to: Optional[RuleApplyTo] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    conditions: Optional[List[RuleConditionCreate]] = None
    actions: Optional[List[RuleActionCreate]] = None
