"""Pydantic schemas for permission grants."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.permission import GRANT_ACTIONS, RESOURCE_TYPES

ActionLiteral = Literal["read", "create", "update", "delete"]


class GrantCreate(BaseModel):
    grantee_id: UUID
    resource_type: str
    resource_id: Optional[UUID] = None
    actions: list[ActionLiteral]
    expires_at: Optional[datetime] = None

    @field_validator("resource_type")
    @classmethod
    def validate_resource_type(cls, v: str) -> str:
        if v not in RESOURCE_TYPES:
            raise ValueError(
                f"Invalid resource_type '{v}'. Must be one of: {', '.join(RESOURCE_TYPES)}"
            )
        return v

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("actions must not be empty")
        invalid = [a for a in v if a not in GRANT_ACTIONS]
        if invalid:
            raise ValueError(f"Invalid actions: {invalid}")
        return v


class GrantUpdate(BaseModel):
    actions: list[ActionLiteral]
    expires_at: Optional[datetime] = None

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("actions must not be empty")
        return v


class GrantResponse(BaseModel):
    id: UUID
    organization_id: UUID
    grantor_id: UUID
    grantee_id: UUID
    resource_type: str
    resource_id: Optional[UUID]
    actions: list[str]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    # Denormalized display helpers (populated in endpoint layer)
    grantee_display_name: Optional[str] = None
    grantor_display_name: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditResponse(BaseModel):
    id: UUID
    grant_id: Optional[UUID]
    action: str
    actor_id: Optional[UUID]
    grantor_id: Optional[UUID]
    grantee_id: Optional[UUID]
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    actions_before: Optional[list[str]]
    actions_after: Optional[list[str]]
    ip_address: Optional[str]
    occurred_at: datetime

    model_config = {"from_attributes": True}


class HouseholdMemberResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    model_config = {"from_attributes": True}
