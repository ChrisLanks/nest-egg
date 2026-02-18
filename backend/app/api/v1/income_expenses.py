"""Income vs Expenses API endpoints."""

from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts,
)
from app.models.user import User
from app.models.transaction import Transaction
from app.models.account import Account
from app.services.deduplication_service import DeduplicationService
from app.services.trend_analysis_service import TrendAnalysisService


router = APIRouter()

# Initialize deduplication service
deduplication_service = DeduplicationService()


def validate_date_range(start_date: date, end_date: date) -> None:
    """Validate date range parameters."""
    # Check date range bounds (prevent unrealistic queries)
    min_date = date(1900, 1, 1)
    max_date = date(2100, 12, 31)

    if start_date < min_date:
        raise HTTPException(
            status_code=400, detail=f"start_date cannot be before {min_date.isoformat()}"
        )

    if end_date > max_date:
        raise HTTPException(
            status_code=400, detail=f"end_date cannot be after {max_date.isoformat()}"
        )

    # Check start is before end
    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be before or equal to end_date"
        )

    # Check date range is not too large (prevent DoS via huge queries)
    max_range_days = 3650  # ~10 years
    date_diff = (end_date - start_date).days

    if date_diff > max_range_days:
        raise HTTPException(
            status_code=400, detail=f"Date range cannot exceed {max_range_days} days (~10 years)"
        )


class CategoryBreakdown(BaseModel):
    """Category breakdown item."""

    category: str
    amount: float
    count: int
    percentage: float


class IncomeExpenseSummary(BaseModel):
    """Income vs expense summary."""

    total_income: float
    total_expenses: float
    net: float
    income_categories: List[CategoryBreakdown]
    expense_categories: List[CategoryBreakdown]


class MonthlyTrend(BaseModel):
    """Monthly income/expense trend."""

    month: str
    income: float
    expenses: float
    net: float


@router.get("/summary", response_model=IncomeExpenseSummary)
async def get_income_expense_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get income vs expense summary for date range."""
    # Validate date range
    validate_date_range(start_date, end_date)

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Get total income - only from active accounts
    income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
    )
    total_income = float(income_result.scalar() or 0)

    # Get total expenses - only from active accounts
    expense_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
    )
    total_expenses = abs(float(expense_result.scalar() or 0))

    # Get income by category - only from active accounts
    income_categories_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
            Transaction.category_primary.isnot(None),
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    for row in income_categories_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.category_primary, amount=amount, count=row.count, percentage=percentage
            )
        )

    # Get expenses by category - only from active accounts
    expense_categories_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.category_primary.isnot(None),
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).asc())  # Most negative first
    )

    expense_categories = []
    for row in expense_categories_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.category_primary, amount=amount, count=row.count, percentage=percentage
            )
        )

    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
    )


@router.get("/trend", response_model=List[MonthlyTrend])
async def get_income_expense_trend(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly income vs expense trend."""

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Create the date_trunc expression once to reuse
    month_expr = func.date_trunc("month", Transaction.date)

    result = await db.execute(
        select(
            month_expr.label("month"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label("expenses"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        )
        .group_by(month_expr)
        .order_by(month_expr)
    )

    trend = []
    for row in result:
        income = float(row.income or 0)
        expenses = abs(float(row.expenses or 0))
        trend.append(
            MonthlyTrend(
                month=row.month.strftime("%Y-%m") if row.month else "",
                income=income,
                expenses=expenses,
                net=income - expenses,
            )
        )

    return trend


@router.get("/merchants", response_model=List[CategoryBreakdown])
async def get_merchant_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    category: Optional[str] = Query(None),
    transaction_type: str = Query(..., description="income or expense"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get merchant breakdown for a category."""

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Build base conditions - only include transactions from active accounts
    conditions = [
        Transaction.organization_id == current_user.organization_id,
        Account.is_active.is_(True),
        Transaction.account_id.in_(account_ids),
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.merchant_name.isnot(None),
    ]

    # Add transaction type filter
    if transaction_type == "income":
        conditions.append(Transaction.amount > 0)
    else:
        conditions.append(Transaction.amount < 0)

    # Add category filter if provided
    if category:
        conditions.append(Transaction.category_primary == category)

    # Get merchant breakdown
    result = await db.execute(
        select(
            Transaction.merchant_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(and_(*conditions))
        .group_by(Transaction.merchant_name)
        .order_by(
            func.sum(Transaction.amount).desc()
            if transaction_type == "income"
            else func.sum(Transaction.amount).asc()
        )
    )

    # Calculate total for percentage
    total_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(and_(*conditions))
    )
    total = abs(float(total_result.scalar() or 0))

    merchants = []
    for row in result:
        amount = abs(float(row.total))
        percentage = (amount / total * 100) if total > 0 else 0
        merchants.append(
            CategoryBreakdown(
                category=row.merchant_name,  # Using category field to store merchant name
                amount=amount,
                count=row.count,
                percentage=percentage,
            )
        )

    return merchants


@router.get("/label-summary", response_model=IncomeExpenseSummary)
async def get_label_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get income vs expense summary grouped by labels."""
    from app.models.transaction import transaction_labels, Label

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Get total income - only from active accounts
    income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
    )
    total_income = float(income_result.scalar() or 0)

    # Get total expenses - only from active accounts
    expense_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
    )
    total_expenses = abs(float(expense_result.scalar() or 0))

    # Get income by label
    income_labels_result = await db.execute(
        select(
            Label.name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(transaction_labels, Transaction.id == transaction_labels.c.transaction_id)
        .join(Label, Label.id == transaction_labels.c.label_id)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
        .group_by(Label.name)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    labeled_income_total = 0
    for row in income_labels_result:
        amount = float(row.total)
        labeled_income_total += amount
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.name, amount=amount, count=row.count, percentage=percentage
            )
        )

    # Add "Unlabeled" category for income transactions without labels
    if labeled_income_total < total_income:
        unlabeled_income = total_income - labeled_income_total
        unlabeled_income_count_result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.organization_id == current_user.organization_id,
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount > 0,
                ~Transaction.id.in_(
                    select(transaction_labels.c.transaction_id).select_from(transaction_labels)
                ),
            )
        )
        unlabeled_count = unlabeled_income_count_result.scalar() or 0
        percentage = (unlabeled_income / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category="Unlabeled",
                amount=unlabeled_income,
                count=unlabeled_count,
                percentage=percentage,
            )
        )

    # Get expenses by label
    expense_labels_result = await db.execute(
        select(
            Label.name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(transaction_labels, Transaction.id == transaction_labels.c.transaction_id)
        .join(Label, Label.id == transaction_labels.c.label_id)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
        .group_by(Label.name)
        .order_by(func.sum(Transaction.amount).asc())
    )

    expense_categories = []
    labeled_expense_total = 0
    for row in expense_labels_result:
        amount = abs(float(row.total))
        labeled_expense_total += amount
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.name, amount=amount, count=row.count, percentage=percentage
            )
        )

    # Add "Unlabeled" category for expense transactions without labels
    if labeled_expense_total < total_expenses:
        unlabeled_expense = total_expenses - labeled_expense_total
        unlabeled_expense_count_result = await db.execute(
            select(func.count(Transaction.id)).where(
                Transaction.organization_id == current_user.organization_id,
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount < 0,
                ~Transaction.id.in_(
                    select(transaction_labels.c.transaction_id).select_from(transaction_labels)
                ),
            )
        )
        unlabeled_count = unlabeled_expense_count_result.scalar() or 0
        percentage = (unlabeled_expense / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category="Unlabeled",
                amount=unlabeled_expense,
                count=unlabeled_count,
                percentage=percentage,
            )
        )

    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
    )


@router.get("/label-merchants", response_model=List[CategoryBreakdown])
async def get_label_merchant_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    label: Optional[str] = Query(None),
    transaction_type: str = Query(..., description="income or expense"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get merchant breakdown for a label."""
    from app.models.transaction import transaction_labels, Label

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Build base conditions
    conditions = [
        Transaction.organization_id == current_user.organization_id,
        Transaction.account_id.in_(account_ids),
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.merchant_name.isnot(None),
    ]

    # Add transaction type filter
    if transaction_type == "income":
        conditions.append(Transaction.amount > 0)
    else:
        conditions.append(Transaction.amount < 0)

    # Handle "Unlabeled" special case
    if label == "Unlabeled":
        # Get transactions without any labels
        result = await db.execute(
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(
                and_(*conditions),
                ~Transaction.id.in_(
                    select(transaction_labels.c.transaction_id).select_from(transaction_labels)
                ),
            )
            .group_by(Transaction.merchant_name)
            .order_by(
                func.sum(Transaction.amount).desc()
                if transaction_type == "income"
                else func.sum(Transaction.amount).asc()
            )
        )

        # Calculate total for percentage
        total_result = await db.execute(
            select(func.sum(Transaction.amount)).where(
                and_(*conditions),
                ~Transaction.id.in_(
                    select(transaction_labels.c.transaction_id).select_from(transaction_labels)
                ),
            )
        )
    elif label:
        # Get transactions with specific label
        result = await db.execute(
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(transaction_labels, Transaction.id == transaction_labels.c.transaction_id)
            .join(Label, Label.id == transaction_labels.c.label_id)
            .where(and_(*conditions), Label.name == label)
            .group_by(Transaction.merchant_name)
            .order_by(
                func.sum(Transaction.amount).desc()
                if transaction_type == "income"
                else func.sum(Transaction.amount).asc()
            )
        )

        # Calculate total for percentage
        total_result = await db.execute(
            select(func.sum(Transaction.amount))
            .select_from(Transaction)
            .join(transaction_labels, Transaction.id == transaction_labels.c.transaction_id)
            .join(Label, Label.id == transaction_labels.c.label_id)
            .where(and_(*conditions), Label.name == label)
        )
    else:
        # No label filter - return all merchants
        result = await db.execute(
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(and_(*conditions))
            .group_by(Transaction.merchant_name)
            .order_by(
                func.sum(Transaction.amount).desc()
                if transaction_type == "income"
                else func.sum(Transaction.amount).asc()
            )
        )

        total_result = await db.execute(
            select(func.sum(Transaction.amount)).where(and_(*conditions))
        )

    total = abs(float(total_result.scalar() or 0))

    merchants = []
    for row in result:
        amount = abs(float(row.total))
        percentage = (amount / total * 100) if total > 0 else 0
        merchants.append(
            CategoryBreakdown(
                category=row.merchant_name, amount=amount, count=row.count, percentage=percentage
            )
        )

    return merchants


@router.get("/merchant-summary", response_model=IncomeExpenseSummary)
async def get_merchant_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get income vs expense summary grouped by merchant."""

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Get total income - only from active accounts
    income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
    )
    total_income = float(income_result.scalar() or 0)

    # Get total expenses - only from active accounts
    expense_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
    )
    total_expenses = abs(float(expense_result.scalar() or 0))

    # Get income by merchant - only from active accounts
    income_merchants_result = await db.execute(
        select(
            Transaction.merchant_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
            Transaction.merchant_name.isnot(None),
        )
        .group_by(Transaction.merchant_name)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    for row in income_merchants_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.merchant_name or "Unknown",
                amount=amount,
                count=row.count,
                percentage=percentage,
            )
        )

    # Get expenses by merchant - only from active accounts
    expense_merchants_result = await db.execute(
        select(
            Transaction.merchant_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.merchant_name.isnot(None),
        )
        .group_by(Transaction.merchant_name)
        .order_by(func.sum(Transaction.amount).asc())  # Most negative first
    )

    expense_categories = []
    for row in expense_merchants_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.merchant_name or "Unknown",
                amount=amount,
                count=row.count,
                percentage=percentage,
            )
        )

    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
    )


@router.get("/account-summary", response_model=IncomeExpenseSummary)
async def get_account_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get income vs expense summary grouped by account."""

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Get total income - only from active accounts
    income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
    )
    total_income = float(income_result.scalar() or 0)

    # Get total expenses - only from active accounts
    expense_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
    )
    total_expenses = abs(float(expense_result.scalar() or 0))

    # Get income by account - only from active accounts
    income_accounts_result = await db.execute(
        select(
            Account.id,
            Account.name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
        )
        .group_by(Account.id, Account.name)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    for row in income_accounts_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.name, amount=amount, count=row.count, percentage=percentage
            )
        )

    # Get expenses by account - only from active accounts
    expense_accounts_result = await db.execute(
        select(
            Account.id,
            Account.name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(
                False
            ),  # Exclude loans/mortgages to prevent double-counting
            Transaction.is_transfer.is_(False),  # Exclude transfers to prevent double-counting
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
        )
        .group_by(Account.id, Account.name)
        .order_by(func.sum(Transaction.amount).asc())  # Most negative first
    )

    expense_categories = []
    for row in expense_accounts_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.name, amount=amount, count=row.count, percentage=percentage
            )
        )

    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
    )


@router.get("/account-merchants", response_model=List[CategoryBreakdown])
async def get_account_merchant_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    account_id: Optional[str] = Query(None),
    transaction_type: str = Query(..., description="income or expense"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get merchant breakdown for a specific account."""

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Build base conditions - only include transactions from active accounts
    conditions = [
        Transaction.organization_id == current_user.organization_id,
        Account.is_active.is_(True),
        Transaction.account_id.in_(account_ids),
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.merchant_name.isnot(None),
    ]

    # Add transaction type filter
    if transaction_type == "income":
        conditions.append(Transaction.amount > 0)
    else:
        conditions.append(Transaction.amount < 0)

    # Add account filter if provided
    if account_id:
        conditions.append(Transaction.account_id == account_id)

    # Get merchant breakdown
    result = await db.execute(
        select(
            Transaction.merchant_name,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .where(and_(*conditions))
        .group_by(Transaction.merchant_name)
        .order_by(
            func.sum(Transaction.amount).desc()
            if transaction_type == "income"
            else func.sum(Transaction.amount).asc()
        )
    )

    # Calculate total for percentage
    total_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(and_(*conditions))
    )
    total = abs(float(total_result.scalar() or 0))

    merchants = []
    for row in result:
        amount = abs(float(row.total))
        percentage = (amount / total * 100) if total > 0 else 0
        merchants.append(
            CategoryBreakdown(
                category=row.merchant_name, amount=amount, count=row.count, percentage=percentage
            )
        )

    return merchants


# Trend Analysis Endpoints


@router.get("/year-over-year")
async def get_year_over_year_comparison(
    years: List[int] = Query(..., description="Years to compare (e.g., [2024, 2023, 2022])"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get side-by-side monthly comparison across multiple years.

    Returns monthly data with income/expenses/net for each year, enabling:
    - Year-over-year trend visualization
    - Seasonality analysis
    - Multi-year performance comparison
    """
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    comparison = await TrendAnalysisService.get_year_over_year_comparison(
        db,
        current_user.organization_id,
        years,
        user_id,
        account_ids,
    )

    return comparison


@router.get("/quarterly-summary")
async def get_quarterly_summary(
    years: List[int] = Query(..., description="Years to compare (e.g., [2024, 2023])"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get quarterly summary across multiple years.

    Returns quarterly aggregations (Q1, Q2, Q3, Q4) for each year with:
    - Total income per quarter
    - Total expenses per quarter
    - Net income per quarter
    """
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    summary = await TrendAnalysisService.get_quarterly_summary(
        db,
        current_user.organization_id,
        years,
        user_id,
        account_ids,
    )

    return summary


@router.get("/category-trends")
async def get_category_trends(
    category: str = Query(..., description="Category name to analyze"),
    start_date: date = Query(...),
    end_date: date = Query(...),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get time-series trend for a specific category.

    Returns monthly data points showing:
    - Total spending per month
    - Transaction count per month

    Useful for identifying spending patterns and anomalies within a category.
    """
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    trends = await TrendAnalysisService.get_category_trends(
        db,
        current_user.organization_id,
        category,
        start_date,
        end_date,
        user_id,
        account_ids,
    )

    return trends


@router.get("/annual-summary")
async def get_annual_summary(
    year: int = Query(..., description="Year to summarize"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive annual summary for a single year.

    Returns:
    - Total income and expenses
    - Net income
    - Average monthly values
    - Peak expense month
    """
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    summary = await TrendAnalysisService.get_annual_summary(
        db,
        current_user.organization_id,
        year,
        user_id,
        account_ids,
    )

    return summary
