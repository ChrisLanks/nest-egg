"""Private Equity Performance API endpoints."""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account, AccountType
from app.models.pe_transaction import PETransaction, PETransactionType
from app.models.user import User
from app.services.pe_performance_service import compute_pe_metrics

logger = logging.getLogger(__name__)
router = APIRouter()


class PETransactionCreate(BaseModel):
    transaction_type: str = Field(..., description="capital_call, distribution, or nav_update")
    amount: float = Field(..., gt=0)
    date: date
    nav_after: Optional[float] = None
    notes: Optional[str] = None


class PETransactionResponse(BaseModel):
    id: str
    transaction_type: str
    amount: float
    date: date
    nav_after: Optional[float]
    notes: Optional[str]


class PEMetricsResponse(BaseModel):
    account_id: str
    account_name: str
    irr: Optional[float]
    irr_pct: Optional[float]
    tvpi: float
    dpi: float
    moic: float
    total_called: float
    total_distributions: float
    current_nav: float
    net_profit: float
    transactions: List[PETransactionResponse]


@router.get("/portfolio", summary="Aggregate PE metrics across all PE accounts")
async def get_pe_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate PE performance across all PE/PD accounts."""
    result = await db.execute(
        select(Account).where(
            and_(
                Account.organization_id == current_user.organization_id,
                Account.account_type.in_([AccountType.PRIVATE_EQUITY, AccountType.PRIVATE_DEBT]),
                Account.is_active == True,  # noqa: E712
            )
        )
    )
    accounts = result.scalars().all()

    if not accounts:
        return {"accounts": [], "portfolio_metrics": None}

    all_txn_dicts = []
    total_nav = Decimal("0")
    account_summaries = []

    for account in accounts:
        txn_result = await db.execute(
            select(PETransaction)
            .where(PETransaction.account_id == account.id)
            .order_by(PETransaction.date.asc())
        )
        transactions = txn_result.scalars().all()

        txn_dicts = [
            {"type": t.transaction_type.value, "amount": t.amount, "date": t.date}
            for t in transactions
        ]

        nav = account.current_balance or Decimal("0")
        total_nav += nav

        metrics = compute_pe_metrics(txn_dicts, nav)
        all_txn_dicts.extend(txn_dicts)

        account_summaries.append({
            "account_id": str(account.id),
            "name": account.name,
            **metrics,
        })

    # Portfolio-level metrics
    portfolio_metrics = compute_pe_metrics(all_txn_dicts, total_nav)

    return {
        "accounts": account_summaries,
        "portfolio_metrics": portfolio_metrics,
    }


@router.get("/{account_id}", response_model=PEMetricsResponse)
async def get_pe_performance(
    account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get PE performance metrics for a specific account."""
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.organization_id == current_user.organization_id,
                Account.account_type.in_([AccountType.PRIVATE_EQUITY, AccountType.PRIVATE_DEBT]),
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="PE/PD account not found")

    txn_result = await db.execute(
        select(PETransaction)
        .where(PETransaction.account_id == account_id)
        .order_by(PETransaction.date.asc())
    )
    transactions = txn_result.scalars().all()

    txn_dicts = [
        {"type": t.transaction_type.value, "amount": t.amount, "date": t.date}
        for t in transactions
    ]

    current_nav = account.current_balance or Decimal("0")
    metrics = compute_pe_metrics(txn_dicts, current_nav)

    txn_responses = [
        PETransactionResponse(
            id=str(t.id),
            transaction_type=t.transaction_type.value,
            amount=float(t.amount),
            date=t.date,
            nav_after=float(t.nav_after) if t.nav_after else None,
            notes=t.notes,
        )
        for t in transactions
    ]

    return PEMetricsResponse(
        account_id=str(account_id),
        account_name=account.name,
        irr=metrics["irr"],
        irr_pct=metrics["irr_pct"],
        tvpi=metrics["tvpi"],
        dpi=metrics["dpi"],
        moic=metrics["moic"],
        total_called=metrics["total_called"],
        total_distributions=metrics["total_distributions"],
        current_nav=metrics["current_nav"],
        net_profit=metrics["net_profit"],
        transactions=txn_responses,
    )


@router.post("/{account_id}/transactions", status_code=201)
async def add_pe_transaction(
    account_id: UUID,
    txn_data: PETransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a capital call, distribution, or NAV update to a PE account."""
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.organization_id == current_user.organization_id,
                Account.account_type.in_([AccountType.PRIVATE_EQUITY, AccountType.PRIVATE_DEBT]),
            )
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="PE/PD account not found")

    try:
        txn_type = PETransactionType(txn_data.transaction_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid transaction_type. Must be one of: {[t.value for t in PETransactionType]}"
        )

    txn = PETransaction(
        account_id=account_id,
        transaction_type=txn_type,
        amount=Decimal(str(txn_data.amount)),
        date=txn_data.date,
        nav_after=Decimal(str(txn_data.nav_after)) if txn_data.nav_after else None,
        notes=txn_data.notes,
    )
    db.add(txn)

    if txn_data.nav_after is not None:
        account.current_balance = Decimal(str(txn_data.nav_after))

    await db.commit()
    await db.refresh(txn)

    return {
        "id": str(txn.id),
        "transaction_type": txn.transaction_type.value,
        "amount": float(txn.amount),
        "date": txn.date.isoformat(),
    }
