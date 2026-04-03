"""Tax-loss harvest ledger API — track harvests and wash sale windows."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.services.rate_limit_service import rate_limit_service
from app.models.tax_loss_harvest import HarvestStatus, TaxLossHarvestRecord
from app.models.user import User



async def _rate_limit(http_request: Request, current_user: User = Depends(get_current_user)):
    """Shared rate-limit dependency for all endpoints in this module."""
    await rate_limit_service.check_rate_limit(
        request=http_request, max_requests=30, window_seconds=60, identifier=str(current_user.id)
    )

router = APIRouter(dependencies=[Depends(_rate_limit)])

WASH_SALE_WINDOW_DAYS = 30


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HarvestRecordCreate(BaseModel):
    date_harvested: date
    ticker_sold: str
    lot_acquisition_date: Optional[date] = None
    loss_amount: Decimal
    replacement_ticker: Optional[str] = None


class HarvestRecordResponse(BaseModel):
    id: UUID
    date_harvested: date
    ticker_sold: str
    lot_acquisition_date: Optional[date] = None
    loss_amount: float
    replacement_ticker: Optional[str] = None
    wash_sale_window_end: date
    status: str
    days_remaining: int

    class Config:
        from_attributes = True


class WashSaleCheckResponse(BaseModel):
    ticker: str
    is_risky: bool
    window_end: Optional[date] = None
    days_remaining: Optional[int] = None


class HarvestSummaryResponse(BaseModel):
    ytd_harvested_losses: float
    active_windows: int
    records: List[HarvestRecordResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/harvest-ledger", response_model=HarvestSummaryResponse)
async def get_harvest_ledger(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the tax-loss harvest ledger with all records for this year."""
    today = date.today()
    year_start = date(today.year, 1, 1)

    result = await db.execute(
        select(TaxLossHarvestRecord)
        .where(
            and_(
                TaxLossHarvestRecord.organization_id == current_user.organization_id,
                TaxLossHarvestRecord.date_harvested >= year_start,
            )
        )
        .order_by(TaxLossHarvestRecord.date_harvested.desc())
    )
    records = list(result.scalars().all())

    # Auto-update statuses
    for r in records:
        if r.status == HarvestStatus.ACTIVE_WINDOW and today > r.wash_sale_window_end:
            r.status = HarvestStatus.WINDOW_CLOSED
    await db.commit()

    ytd_losses = sum(float(r.loss_amount) for r in records)
    active_windows = sum(1 for r in records if r.status == HarvestStatus.ACTIVE_WINDOW)

    return HarvestSummaryResponse(
        ytd_harvested_losses=ytd_losses,
        active_windows=active_windows,
        records=[
            HarvestRecordResponse(
                id=r.id,
                date_harvested=r.date_harvested,
                ticker_sold=r.ticker_sold,
                lot_acquisition_date=r.lot_acquisition_date,
                loss_amount=float(r.loss_amount),
                replacement_ticker=r.replacement_ticker,
                wash_sale_window_end=r.wash_sale_window_end,
                status=r.status.value,
                days_remaining=max(0, (r.wash_sale_window_end - today).days),
            )
            for r in records
        ],
    )


@router.post("/harvest-ledger", response_model=HarvestRecordResponse, status_code=201)
async def record_harvest(
    body: HarvestRecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a new tax-loss harvest event."""
    window_end = body.date_harvested + timedelta(days=WASH_SALE_WINDOW_DAYS)
    today = date.today()
    status = HarvestStatus.ACTIVE_WINDOW if today <= window_end else HarvestStatus.WINDOW_CLOSED

    record = TaxLossHarvestRecord(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        date_harvested=body.date_harvested,
        ticker_sold=body.ticker_sold,
        lot_acquisition_date=body.lot_acquisition_date,
        loss_amount=body.loss_amount,
        replacement_ticker=body.replacement_ticker,
        wash_sale_window_end=window_end,
        status=status,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return HarvestRecordResponse(
        id=record.id,
        date_harvested=record.date_harvested,
        ticker_sold=record.ticker_sold,
        lot_acquisition_date=record.lot_acquisition_date,
        loss_amount=float(record.loss_amount),
        replacement_ticker=record.replacement_ticker,
        wash_sale_window_end=record.wash_sale_window_end,
        status=record.status.value,
        days_remaining=max(0, (record.wash_sale_window_end - today).days),
    )


@router.get("/wash-sale-check/{ticker}", response_model=WashSaleCheckResponse)
async def check_wash_sale_risk(
    ticker: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if purchasing a ticker would trigger a wash sale."""
    today = date.today()
    result = await db.execute(
        select(TaxLossHarvestRecord).where(
            and_(
                TaxLossHarvestRecord.organization_id == current_user.organization_id,
                TaxLossHarvestRecord.ticker_sold == ticker.upper(),
                TaxLossHarvestRecord.status == HarvestStatus.ACTIVE_WINDOW,
                TaxLossHarvestRecord.wash_sale_window_end >= today,
            )
        )
    )
    active = result.scalars().first()

    if active:
        return WashSaleCheckResponse(
            ticker=ticker.upper(),
            is_risky=True,
            window_end=active.wash_sale_window_end,
            days_remaining=(active.wash_sale_window_end - today).days,
        )
    return WashSaleCheckResponse(ticker=ticker.upper(), is_risky=False)
