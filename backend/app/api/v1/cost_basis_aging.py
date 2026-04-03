"""Cost basis aging API endpoint — open lot analysis with holding-period buckets."""

import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.constants.financial import SMART_INSIGHTS
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.holding import Holding
from app.models.tax_lot import TaxLot
from app.models.user import User
from app.services.rate_limit_service import rate_limit_service

logger = logging.getLogger(__name__)


async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for cost basis aging endpoints."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=20, window_seconds=60, identifier=str(current_user.id)
    )


router = APIRouter(tags=["Cost Basis Aging"], dependencies=[Depends(_rate_limit)])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TaxLotItem(BaseModel):
    lot_id: str
    account_id: str
    account_name: str
    ticker: Optional[str]
    quantity: float
    cost_basis_per_share: float
    cost_basis_total: float
    current_value: Optional[float]
    unrealized_gain: Optional[float]
    unrealized_gain_pct: Optional[float]
    acquisition_date: str
    days_held: int
    holding_period: str
    days_to_long_term: int
    bucket: str


class CostBasisAgingResponse(BaseModel):
    lots: List[TaxLotItem]
    approaching_count: int
    approaching_value: float
    short_term_gain: float
    long_term_gain: float
    short_term_loss: float
    long_term_loss: float
    total_open_lots: int
    summary_tip: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/cost-basis-aging", response_model=CostBasisAgingResponse)
async def get_cost_basis_aging(
    account_id: Optional[str] = Query(None, description="Filter to a specific account"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all open tax lots grouped into holding-period buckets.

    Buckets:
    - ``approaching``: short-term lots within 30 days of the 1-year mark
    - ``short_term``:  short-term lots with > 30 days remaining
    - ``long_term``:   lots held >= 365 days
    """
    today = datetime.date.today()

    # Fetch all accounts for this organisation (for name lookup)
    acct_result = await db.execute(
        select(Account).where(
            Account.organization_id == current_user.organization_id,
        )
    )
    accounts = {str(a.id): a for a in acct_result.scalars().all()}

    # Fetch open lots for this organisation
    lot_query = (
        select(TaxLot)
        .where(
            TaxLot.organization_id == current_user.organization_id,
            TaxLot.is_closed.is_(False),
        )
        .options(selectinload(TaxLot.holding))
    )
    if account_id:
        import uuid as _uuid
        lot_query = lot_query.where(TaxLot.account_id == _uuid.UUID(account_id))

    lot_result = await db.execute(lot_query)
    open_lots = lot_result.scalars().all()

    lots: List[TaxLotItem] = []
    approaching_count = 0
    approaching_value = 0.0
    st_gain = 0.0
    lt_gain = 0.0
    st_loss = 0.0
    lt_loss = 0.0

    for lot in open_lots:
        acq_date = lot.acquisition_date
        days_held = (today - acq_date).days
        is_long_term = days_held >= 365
        holding_period = "long_term" if is_long_term else "short_term"
        days_to_long_term = 0 if is_long_term else max(0, 365 - days_held)

        # Bucket assignment
        if is_long_term:
            bucket = "long_term"
        elif days_to_long_term <= SMART_INSIGHTS.DAYS_TO_LONG_TERM_WARNING:
            bucket = "approaching"
        else:
            bucket = "short_term"

        quantity = float(lot.remaining_quantity)
        cbps = float(lot.cost_basis_per_share)
        cost_total = float(lot.total_cost_basis)

        # Current value from associated holding if available
        current_value: Optional[float] = None
        unrealized_gain: Optional[float] = None
        unrealized_gain_pct: Optional[float] = None

        holding: Optional[Holding] = lot.holding
        if holding and holding.current_price_per_share is not None:
            current_price = float(holding.current_price_per_share)
            current_value = round(current_price * quantity, 2)
            unrealized_gain = round(current_value - cost_total, 2)
            unrealized_gain_pct = (
                round((unrealized_gain / cost_total) * 100, 2) if cost_total != 0 else 0.0
            )

        account = accounts.get(str(lot.account_id))
        account_name = account.name if account else str(lot.account_id)
        ticker = holding.ticker if holding else None

        # Accumulate summary stats
        if bucket == "approaching":
            approaching_count += 1
            if current_value is not None:
                approaching_value += current_value

        if unrealized_gain is not None:
            if holding_period == "short_term":
                if unrealized_gain >= 0:
                    st_gain += unrealized_gain
                else:
                    st_loss += unrealized_gain
            else:
                if unrealized_gain >= 0:
                    lt_gain += unrealized_gain
                else:
                    lt_loss += unrealized_gain

        lots.append(
            TaxLotItem(
                lot_id=str(lot.id),
                account_id=str(lot.account_id),
                account_name=account_name,
                ticker=ticker,
                quantity=quantity,
                cost_basis_per_share=cbps,
                cost_basis_total=round(cost_total, 2),
                current_value=current_value,
                unrealized_gain=unrealized_gain,
                unrealized_gain_pct=unrealized_gain_pct,
                acquisition_date=acq_date.isoformat(),
                days_held=days_held,
                holding_period=holding_period,
                days_to_long_term=days_to_long_term,
                bucket=bucket,
            )
        )

    # Sort: approaching first, then short-term, then long-term; within each sort by days_held asc
    _bucket_order = {"approaching": 0, "short_term": 1, "long_term": 2}
    lots.sort(key=lambda l: (_bucket_order[l.bucket], l.days_held))

    # Summary tip
    if approaching_count > 0:
        summary_tip = (
            f"{approaching_count} lot(s) become long-term within 30 days — "
            "consider holding to avoid short-term tax rates."
        )
    elif st_loss < -SMART_INSIGHTS.TAX_LOSS_HARVEST_MIN_USD:
        summary_tip = (
            f"${abs(st_loss):,.0f} in short-term losses available for tax-loss harvesting."
        )
    else:
        summary_tip = "No urgent cost basis actions needed."

    return CostBasisAgingResponse(
        lots=lots,
        approaching_count=approaching_count,
        approaching_value=round(approaching_value, 2),
        short_term_gain=round(st_gain, 2),
        long_term_gain=round(lt_gain, 2),
        short_term_loss=round(st_loss, 2),
        long_term_loss=round(lt_loss, 2),
        total_open_lots=len(lots),
        summary_tip=summary_tip,
    )
