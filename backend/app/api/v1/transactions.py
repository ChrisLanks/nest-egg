"""Transaction API endpoints."""

from typing import Optional
from uuid import UUID
from datetime import date, datetime
import base64
import json
import csv
from io import StringIO

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction, Label, TransactionLabel, Category
from app.models.account import Account
from app.schemas.transaction import TransactionDetail, TransactionListResponse, TransactionUpdate, CategorySummary

router = APIRouter()


def encode_cursor(txn_date: date, created_at: datetime, txn_id: UUID) -> str:
    """Encode transaction cursor for pagination."""
    cursor_data = {
        'date': txn_date.isoformat(),
        'created_at': created_at.isoformat(),
        'id': str(txn_id)
    }
    json_str = json.dumps(cursor_data)
    return base64.b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> tuple:
    """Decode transaction cursor."""
    try:
        json_str = base64.b64decode(cursor.encode()).decode()
        cursor_data = json.loads(json_str)
        return (
            datetime.fromisoformat(cursor_data['date']).date(),
            datetime.fromisoformat(cursor_data['created_at']),
            UUID(cursor_data['id'])
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid cursor: {str(e)}")


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    page_size: int = Query(50, ge=1, le=1000),
    cursor: Optional[str] = None,
    account_id: Optional[UUID] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List transactions with filtering and cursor-based pagination."""
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

    # Build base query - only include transactions from active accounts
    query = (
        select(Transaction)
        .join(Account)
        .options(joinedload(Transaction.account))
        .options(joinedload(Transaction.category).joinedload(Category.parent))
        .options(joinedload(Transaction.labels).joinedload(TransactionLabel.label))
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active == True
        )
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

    # Apply cursor pagination
    if cursor:
        cursor_date, cursor_created_at, cursor_id = decode_cursor(cursor)
        # Use tuple comparison for stable ordering
        query = query.where(
            tuple_(Transaction.date, Transaction.created_at, Transaction.id) <
            tuple_(cursor_date, cursor_created_at, cursor_id)
        )

    # Order by date DESC, created_at DESC, id DESC for consistent ordering
    query = query.order_by(
        Transaction.date.desc(),
        Transaction.created_at.desc(),
        Transaction.id.desc()
    )

    # Fetch one extra to determine if there are more results
    query = query.limit(page_size + 1)

    result = await db.execute(query)
    transactions = result.unique().scalars().all()

    # Check if there are more results
    has_more = len(transactions) > page_size
    if has_more:
        transactions = transactions[:page_size]

    # Generate next cursor from last transaction
    next_cursor = None
    if has_more and transactions:
        last_txn = transactions[-1]
        next_cursor = encode_cursor(last_txn.date, last_txn.created_at, last_txn.id)

    # Get total count (only when no cursor, for first page)
    total = 0
    if not cursor:
        # Build count query with same filters - only count transactions from active accounts
        count_query = (
            select(func.count())
            .select_from(Transaction)
            .join(Account)
            .where(
                Transaction.organization_id == current_user.organization_id,
                Account.is_active == True
            )
        )
        if account_id:
            count_query = count_query.where(Transaction.account_id == account_id)
        if start_date_obj:
            count_query = count_query.where(Transaction.date >= start_date_obj)
        if end_date_obj:
            count_query = count_query.where(Transaction.date <= end_date_obj)
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                Transaction.merchant_name.ilike(search_pattern)
                | Transaction.description.ilike(search_pattern)
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar()

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

    return TransactionListResponse(
        transactions=transaction_details,
        total=total,
        page=1,  # Always return 1 for cursor-based pagination
        page_size=page_size,
        has_more=has_more,
        next_cursor=next_cursor,
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
    if update_data.is_transfer is not None:
        txn.is_transfer = update_data.is_transfer

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


@router.get("/export/csv")
async def export_transactions_csv(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    account_id: Optional[UUID] = Query(None, description="Filter by account"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export transactions as CSV file.

    Returns all transactions matching the filters in CSV format suitable for
    spreadsheet applications, tax software, or archival purposes.
    """
    # Build query
    query = select(Transaction).options(
        joinedload(Transaction.account),
        joinedload(Transaction.category),
        joinedload(Transaction.labels).joinedload(TransactionLabel.label),
    ).where(
        Transaction.organization_id == current_user.organization_id
    ).order_by(Transaction.date.desc(), Transaction.created_at.desc())

    # Apply filters
    if start_date:
        query = query.where(Transaction.date >= datetime.fromisoformat(start_date).date())
    if end_date:
        query = query.where(Transaction.date <= datetime.fromisoformat(end_date).date())
    if account_id:
        query = query.where(Transaction.account_id == account_id)

    # Execute query
    result = await db.execute(query)
    transactions = result.unique().scalars().all()

    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow([
        'Date',
        'Merchant',
        'Description',
        'Category',
        'Labels',
        'Amount',
        'Account',
        'Account Number',
        'Is Pending',
        'Is Transfer',
        'Transaction ID',
    ])

    # Write data rows
    for txn in transactions:
        # Format labels as comma-separated list
        labels_str = ', '.join([label.label.name for label in txn.labels]) if txn.labels else ''

        # Format category (use custom category if available, otherwise Plaid category)
        category_str = txn.category.name if txn.category else (txn.category_primary or '')

        writer.writerow([
            txn.date.isoformat(),
            txn.merchant_name or '',
            txn.description or '',
            category_str,
            labels_str,
            float(txn.amount),
            txn.account.name if txn.account else '',
            f"****{txn.account.mask}" if txn.account and txn.account.mask else '',
            'Yes' if txn.is_pending else 'No',
            'Yes' if txn.is_transfer else 'No',
            str(txn.id),
        ])

    # Prepare response
    output.seek(0)

    # Generate filename with date range
    filename = 'transactions'
    if start_date and end_date:
        filename = f'transactions_{start_date}_to_{end_date}'
    elif start_date:
        filename = f'transactions_from_{start_date}'
    elif end_date:
        filename = f'transactions_until_{end_date}'
    filename += '.csv'

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
