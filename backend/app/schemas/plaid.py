"""Plaid API schemas."""

from typing import Optional, List
from pydantic import BaseModel


class LinkTokenCreateRequest(BaseModel):
    """Request schema for creating a Plaid Link token."""

    pass  # No parameters needed for now


class LinkTokenCreateResponse(BaseModel):
    """Response schema for Plaid Link token creation."""

    link_token: str
    expiration: str


class PublicTokenExchangeRequest(BaseModel):
    """Request schema for exchanging Plaid public token."""

    public_token: str
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    accounts: List[dict] = []


class PlaidAccount(BaseModel):
    """Plaid account information."""

    account_id: str
    name: str
    mask: Optional[str] = None
    official_name: Optional[str] = None
    type: str
    subtype: Optional[str] = None
    current_balance: float
    available_balance: Optional[float] = None
    limit: Optional[float] = None


class PublicTokenExchangeResponse(BaseModel):
    """Response schema for public token exchange."""

    item_id: str
    accounts: List[PlaidAccount]
