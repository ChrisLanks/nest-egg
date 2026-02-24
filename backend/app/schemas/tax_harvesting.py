"""Tax-loss harvesting schemas."""

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TaxLossOpportunityResponse(BaseModel):
    holding_id: UUID
    ticker: str
    name: Optional[str]
    shares: Decimal
    cost_basis: Decimal
    current_value: Decimal
    unrealized_loss: Decimal
    loss_percentage: Decimal
    estimated_tax_savings: Decimal
    wash_sale_risk: bool
    wash_sale_reason: Optional[str]
    sector: Optional[str]
    suggested_replacements: List[str]


class TaxLossHarvestingSummaryResponse(BaseModel):
    opportunities: List[TaxLossOpportunityResponse]
    total_harvestable_losses: Decimal
    total_estimated_tax_savings: Decimal
