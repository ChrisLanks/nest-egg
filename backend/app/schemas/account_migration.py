"""Schemas for account provider migration."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.account import AccountSource
from app.models.account_migration import MigrationStatus


class MigrateAccountRequest(BaseModel):
    """Request to migrate an account to a different provider."""

    target_source: AccountSource = Field(
        ...,
        description="Target provider: plaid, teller, mx, or manual",
    )
    target_enrollment_id: Optional[UUID] = Field(
        None,
        description=(
            "ID of the target PlaidItem, TellerEnrollment, or MxMember. "
            "Required when target_source is not 'manual'."
        ),
    )
    target_external_account_id: Optional[str] = Field(
        None,
        description=(
            "The external account ID assigned by the target provider. "
            "Required when target_source is not 'manual'."
        ),
    )
    confirm: bool = Field(
        ...,
        description=(
            "Must be true. This operation changes the account's data source "
            "and provider-specific sync state will be lost."
        ),
    )


class MigrationLogResponse(BaseModel):
    """Response for a migration log entry."""

    id: UUID
    account_id: Optional[UUID] = None
    source_provider: str
    target_provider: str
    status: MigrationStatus
    pre_migration_snapshot: dict
    post_migration_snapshot: Optional[dict] = None
    error_message: Optional[str] = None
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    initiated_by_user_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


class MigrateAccountResponse(BaseModel):
    """Response after a successful account migration."""

    migration_log: MigrationLogResponse
    message: str
