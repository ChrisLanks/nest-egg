"""Transaction API endpoints."""

from typing import Optional
from uuid import UUID
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction, Label, TransactionLabel, Category
from app.models.account import Account
from app.schemas.transaction import TransactionDetail, TransactionListResponse, TransactionUpdate, CategorySummary

router = APIRouter()


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),  # Increased limit for displaying all transactions
    account_id: Optional[UUID] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with filtering and pagination."""
    # Parse date strings if provided
    start_date_obj = None
    end_date_obj = None

    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    # Build base query
    query = (
        select(Transaction)
        .options(joinedload(Transaction.account))
        .options(joinedload(Transaction.category).joinedload(Category.parent))
        .options(joinedload(Transaction.labels).joinedload(TransactionLabel.label))
        .where(Transaction.organization_id == current_user.organization_id)
    )

    # Apply filters
    if account_id:
        query = query.where(Transaction.account_id == account_id)

    if start_date_obj:
        query = query.where(Transaction.date >= start_date_obj)

    if end_date_obj:
        query = query.where(Transaction.date <= end_date_obj)

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
        # Extract labels from the many-to-many relationship
        transaction_labels = [tl.label for tl in txn.labels if tl.label]

        # Extract category information
        category_summary = None
        if txn.category:
            category_summary = CategorySummary(
                id=txn.category.id,
                name=txn.category.name,
                color=txn.category.color,
                parent_id=txn.category.parent_category_id,
                parent_name=txn.category.parent.name if txn.category.parent else None,
            )

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
            category=category_summary,
            labels=transaction_labels,
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


@router.get("/{transaction_id}", response_model=TransactionDetail)
async def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific transaction with details."""
    result = await db.execute(
        select(Transaction)
        .options(joinedload(Transaction.account))
        .options(joinedload(Transaction.category).joinedload(Category.parent))
        .options(joinedload(Transaction.labels).joinedload(TransactionLabel.label))
        .where(
            Transaction.id == transaction_id,
            Transaction.organization_id == current_user.organization_id,
        )
    )
    txn = result.unique().scalar_one_or_none()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Extract labels from the many-to-many relationship
    transaction_labels = [tl.label for tl in txn.labels if tl.label]

    # Extract category information
    category_summary = None
    if txn.category:
        category_summary = CategorySummary(
            id=txn.category.id,
            name=txn.category.name,
            color=txn.category.color,
            parent_id=txn.category.parent_category_id,
            parent_name=txn.category.parent.name if txn.category.parent else None,
        )

    return TransactionDetail(
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
        category=category_summary,
        labels=transaction_labels,
    )


@router.patch("/{transaction_id}", response_model=TransactionDetail)
async def update_transaction(
    transaction_id: UUID,
    update_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction."""
    result = await db.execute(
        select(Transaction)
        .options(joinedload(Transaction.account))
        .where(
            Transaction.id == transaction_id,
            Transaction.organization_id == current_user.organization_id,
        )
    )
    txn = result.unique().scalar_one_or_none()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update fields
    if update_data.merchant_name is not None:
        txn.merchant_name = update_data.merchant_name
    if update_data.description is not None:
        txn.description = update_data.description
    if update_data.category_primary is not None:
        txn.category_primary = update_data.category_primary

    txn.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(txn)

    return TransactionDetail(
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
        labels=[],
    )


@router.post("/{transaction_id}/labels/{label_id}", status_code=201)
async def add_label_to_transaction(
    transaction_id: UUID,
    label_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a label to a transaction."""
    # Verify transaction exists and belongs to organization
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.organization_id == current_user.organization_id,
        )
    )
    txn = txn_result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify label exists and belongs to organization
    label_result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.organization_id == current_user.organization_id,
        )
    )
    label = label_result.scalar_one_or_none()
    if not label:
        raise HTTPException(status_code=404, detail="Label not found")

    # Check if already labeled
    existing = await db.execute(
        select(TransactionLabel).where(
            TransactionLabel.transaction_id == transaction_id,
            TransactionLabel.label_id == label_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"message": "Label already applied"}

    # Add label
    txn_label = TransactionLabel(
        transaction_id=transaction_id,
        label_id=label_id,
    )
    db.add(txn_label)
    await db.commit()

    return {"message": "Label added successfully"}


@router.delete("/{transaction_id}/labels/{label_id}", status_code=204)
async def remove_label_from_transaction(
    transaction_id: UUID,
    label_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a label from a transaction."""
    # Verify transaction belongs to organization
    txn_result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.organization_id == current_user.organization_id,
        )
    )
    if not txn_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Remove label
    result = await db.execute(
        select(TransactionLabel).where(
            TransactionLabel.transaction_id == transaction_id,
            TransactionLabel.label_id == label_id,
        )
    )
    txn_label = result.scalar_one_or_none()

    if txn_label:
        await db.delete(txn_label)
        await db.commit()
