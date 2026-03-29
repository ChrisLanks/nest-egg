"""Tax lot API endpoints for per-lot cost basis tracking."""

import csv
import io
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, extract, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.holding import Holding
from app.models.tax_lot import CostBasisMethod, TaxLot
from app.models.user import User
from app.schemas.tax_lot import (
    CostBasisMethodUpdate,
    RealizedGainsSummary,
    SaleRequest,
    SaleResult,
    TaxLotCreate,
    TaxLotResponse,
    UnrealizedGainsSummary,
)
from app.services.tax_lot_service import tax_lot_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_verified_holding(
    holding_id: UUID,
    current_user: User,
    db: AsyncSession,
) -> Holding:
    """Verify holding belongs to user's organization."""
    result = await db.execute(
        select(Holding).where(
            Holding.id == holding_id,
            Holding.organization_id == current_user.organization_id,
        )
    )
    holding = result.scalar_one_or_none()
    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")
    return holding


# --- Holding-scoped endpoints ---


@router.get(
    "/holdings/{holding_id}/tax-lots",
    response_model=List[TaxLotResponse],
)
async def list_tax_lots(
    holding_id: UUID = Path(..., description="Holding ID"),
    include_closed: bool = Query(False, description="Include closed (fully sold) lots"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List tax lots for a holding."""
    await _get_verified_holding(holding_id, current_user, db)
    lots = await tax_lot_service.get_lots(db, holding_id, include_closed=include_closed)
    return lots


@router.post(
    "/holdings/{holding_id}/tax-lots",
    response_model=TaxLotResponse,
    status_code=201,
)
async def create_tax_lot(
    body: TaxLotCreate,
    holding_id: UUID = Path(..., description="Holding ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually record a purchase lot for a holding."""
    holding = await _get_verified_holding(holding_id, current_user, db)

    lot = await tax_lot_service.record_purchase(
        db=db,
        org_id=current_user.organization_id,
        holding_id=holding.id,
        account_id=holding.account_id,
        quantity=body.quantity,
        price_per_share=body.cost_basis_per_share,
        acquisition_date=body.acquisition_date,
    )
    await db.commit()
    await db.refresh(lot)
    return lot


@router.post(
    "/holdings/{holding_id}/sell",
    response_model=SaleResult,
)
async def record_sale(
    body: SaleRequest,
    holding_id: UUID = Path(..., description="Holding ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a sale and select lots per cost basis method.

    Uses the account's default cost basis method unless overridden in the request.
    """
    holding = await _get_verified_holding(holding_id, current_user, db)

    # Determine method
    method = None
    if body.cost_basis_method:
        try:
            method = CostBasisMethod(body.cost_basis_method)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid cost basis method: {body.cost_basis_method}. "
                f"Must be one of: fifo, lifo, hifo, specific_id",
            )

    if method == CostBasisMethod.SPECIFIC_ID and not body.specific_lot_ids:
        raise HTTPException(
            status_code=400,
            detail="specific_lot_ids required when using specific_id method",
        )

    try:
        result = await tax_lot_service.record_sale(
            db=db,
            org_id=current_user.organization_id,
            holding_id=holding.id,
            account_id=holding.account_id,
            quantity=body.quantity,
            sale_price_per_share=body.sale_price_per_share,
            sale_date=body.sale_date,
            method=method,
            specific_lot_ids=body.specific_lot_ids,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Insufficient shares or invalid sale parameters")

    await db.commit()
    # Refresh lot details after commit
    for lot in result["lot_details"]:
        await db.refresh(lot)

    return result


@router.post(
    "/holdings/{holding_id}/import-lots",
    response_model=Optional[TaxLotResponse],
)
async def import_lots_from_holding(
    holding_id: UUID = Path(..., description="Holding ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-create a tax lot from existing holding cost basis data (migration helper)."""
    await _get_verified_holding(holding_id, current_user, db)

    lot = await tax_lot_service.import_lots_from_holding(
        db, holding_id, org_id=current_user.organization_id
    )
    if lot is None:
        raise HTTPException(
            status_code=409,
            detail="Cannot import: lots already exist, or holding lacks cost basis data",
        )
    await db.commit()
    await db.refresh(lot)
    return lot


# --- Account-scoped endpoints ---


@router.get(
    "/accounts/{account_id}/unrealized-gains",
    response_model=UnrealizedGainsSummary,
)
async def get_unrealized_gains(
    account_id: UUID = Path(..., description="Account ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get per-lot unrealized gains for an account using current holding prices."""
    # Verify account ownership
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    summary = await tax_lot_service.get_unrealized_gains(
        db, account_id, org_id=current_user.organization_id
    )
    return summary


@router.get(
    "/accounts/{account_id}/realized-gains",
    response_model=RealizedGainsSummary,
)
async def get_realized_gains(
    account_id: UUID = Path(..., description="Account ID"),
    year: int = Query(..., description="Tax year"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get realized gains summary for a tax year."""
    # Verify account ownership
    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    summary = await tax_lot_service.get_realized_gains_summary(
        db, current_user.organization_id, year, account_id=account_id
    )
    return summary


@router.put(
    "/accounts/{account_id}/cost-basis-method",
    response_model=dict,
)
async def update_cost_basis_method(
    body: CostBasisMethodUpdate,
    account_id: UUID = Path(..., description="Account ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the default cost basis method for an account."""
    # Validate method value
    try:
        CostBasisMethod(body.cost_basis_method)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cost basis method: {body.cost_basis_method}. "
            f"Must be one of: fifo, lifo, hifo, specific_id",
        )

    result = await db.execute(
        select(Account).where(
            Account.id == account_id,
            Account.organization_id == current_user.organization_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.cost_basis_method = body.cost_basis_method
    await db.commit()

    return {
        "account_id": str(account_id),
        "cost_basis_method": body.cost_basis_method,
    }


@router.get("/tax-lots/export/8949")
async def export_form_8949(
    year: int = Query(..., description="Tax year to export (e.g. 2025)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export closed tax lots in IRS Form 8949 format as a CSV.

    Returns two sections: short-term lots (Box A/B) and long-term lots (Box D/E/F).
    Columns match the IRS Form 8949 layout:
      Description | Date Acquired | Date Sold | Proceeds | Cost Basis | Adjustment Code | Adjustment Amount | Gain or Loss
    """
    # Fetch all closed lots for this org/year with their associated holding
    result = await db.execute(
        select(TaxLot)
        .options(selectinload(TaxLot.holding))
        .where(
            and_(
                TaxLot.organization_id == current_user.organization_id,
                TaxLot.is_closed == True,  # noqa: E712
                extract("year", TaxLot.closed_at) == year,
            )
        )
        .order_by(TaxLot.holding_period, TaxLot.closed_at)
    )
    lots = result.scalars().all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header comment
    writer.writerow([f"IRS Form 8949 — Tax Year {year}", "", "", "", "", "", "", ""])
    writer.writerow([
        "Description of Property",
        "Date Acquired",
        "Date Sold",
        "Proceeds",
        "Cost or Other Basis",
        "Adjustment Code(s)",
        "Amount of Adjustment",
        "Gain or (Loss)",
    ])

    short_term = [l for l in lots if l.holding_period == "SHORT_TERM"]
    long_term = [l for l in lots if l.holding_period == "LONG_TERM"]
    other = [l for l in lots if l.holding_period not in ("SHORT_TERM", "LONG_TERM")]

    def _write_section(header: str, section_lots: list) -> None:
        if not section_lots:
            return
        writer.writerow([header, "", "", "", "", "", "", ""])
        for lot in section_lots:
            ticker = lot.holding.ticker if lot.holding and lot.holding.ticker else "UNKNOWN"
            qty = float(lot.quantity)
            description = f"{qty:g} shares of {ticker}"
            date_acquired = lot.acquisition_date.strftime("%m/%d/%Y") if lot.acquisition_date else ""
            date_sold = lot.closed_at.date().strftime("%m/%d/%Y") if lot.closed_at else ""
            proceeds = float(lot.sale_proceeds) if lot.sale_proceeds is not None else 0.0
            cost_basis = float(lot.total_cost_basis) if lot.total_cost_basis is not None else 0.0
            gain_loss = float(lot.realized_gain_loss) if lot.realized_gain_loss is not None else proceeds - cost_basis
            writer.writerow([
                description,
                date_acquired,
                date_sold,
                f"{proceeds:.2f}",
                f"{cost_basis:.2f}",
                "",  # No adjustments tracked
                "0.00",
                f"{gain_loss:.2f}",
            ])

    _write_section("--- SHORT-TERM (held 1 year or less) ---", short_term)
    _write_section("--- LONG-TERM (held more than 1 year) ---", long_term)
    if other:
        _write_section("--- OTHER (holding period unknown) ---", other)

    if not lots:
        writer.writerow(["No closed lots found for this tax year", "", "", "", "", "", "", ""])

    csv_content = output.getvalue()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="form_8949_{year}.csv"'},
    )
