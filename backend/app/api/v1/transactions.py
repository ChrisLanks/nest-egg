"""Transaction API endpoints."""

from typing import Optional
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction
from app.models.account import Account
from app.schemas.transaction import TransactionDetail, TransactionListResponse

router = APIRouter()


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    account_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with filtering and pagination."""
    # Build base query
    query = (
        select(Transaction)
        .options(joinedload(Transaction.account))
        .where(Transaction.organization_id == current_user.organization_id)
    )

    # Apply filters
    if account_id:
        query = query.where(Transaction.account_id == account_id)

    if start_date:
        query = query.where(Transaction.date >= start_date)

    if end_date:
        query = query.where(Transaction.date <= end_date)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            Transaction.merchant_name.ilike(search_pattern)
            | Transaction.description.ilike(search_pattern)
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(Transaction.date.desc(), Transaction.created_at.desc())
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    transactions = result.unique().scalars().all()

    # Transform to response format
    transaction_details = []
    for txn in transactions:
        detail = TransactionDetail(
            id=txn.id,
            organization_id=txn.organization_id,
            account_id=txn.account_id,
            external_transaction_id=txn.external_transaction_id,
            date=txn.date,
            amount=txn.amount,
            merchant_name=txn.merchant_name,
            description=txn.description,
            category_primary=txn.category_primary,
            category_detailed=txn.category_detailed,
            is_pending=txn.is_pending,
            created_at=txn.created_at,
            updated_at=txn.updated_at,
            account_name=txn.account.name if txn.account else None,
            account_mask=txn.account.mask if txn.account else None,
            labels=[],  # TODO: Add labels when we implement them
        )
        transaction_details.append(detail)

    has_more = (offset + page_size) < total

    return TransactionListResponse(
        transactions=transaction_details,
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )
