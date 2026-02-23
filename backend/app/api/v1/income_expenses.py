"""Income vs Expenses API endpoints."""

import logging
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts,
)
from app.models.user import User
from app.models.transaction import Transaction, Category, transaction_labels, Label
from app.models.account import Account
from app.services.deduplication_service import DeduplicationService
from app.services.trend_analysis_service import TrendAnalysisService
from app.utils.date_validation import validate_date_range


router = APIRouter()

# Initialize logger and services
logger = logging.getLogger(__name__)
deduplication_service = DeduplicationService()

# Cap on merchant GROUP BY results to prevent unbounded memory use
MAX_MERCHANT_RESULTS = 500


class CategoryBreakdown(BaseModel):
    """Category breakdown item."""

    category: str
    amount: float
    count: int
    percentage: float
    has_children: bool = False  # Whether this category has child categories
    id: Optional[str] = None  # For account grouping: account UUID


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
    # Use hierarchical categories: show root category for child categories, otherwise show the category itself
    # Aliases for category matching
    ParentCategory = aliased(Category)
    CategoryByName = aliased(Category)  # Match provider category by name
    ParentByName = aliased(Category)     # Parent of matched category

    # Build category name expression:
    # Priority:
    # 1. If transaction has custom category_id with parent → use parent name
    # 2. If transaction has custom category_id without parent → use category name
    # 3. If provider category matches a category name with parent → use parent name
    # 4. Otherwise → use provider category as-is
    category_name_expr = func.coalesce(
        ParentCategory.name,  # Parent of custom category
        Category.name,        # Custom category name
        ParentByName.name,    # Parent of matched provider category
        Transaction.category_primary  # Fallback to provider category
    ).label("category_name")

    logger.info(f"[CATEGORY GROUPING] Querying income categories - org: {current_user.organization_id}, accounts: {len(account_ids)}, date range: {start_date} to {end_date}")

    # Debug: Check what categories exist
    debug_cats = await db.execute(
        select(Category.name, Category.parent_category_id, ParentCategory.name.label("parent_name"))
        .outerjoin(ParentCategory, Category.parent_category_id == ParentCategory.id)
        .where(Category.organization_id == current_user.organization_id)
    )
    logger.info(f"[CATEGORY GROUPING] Available categories: {[(r.name, r.parent_name) for r in debug_cats.all()]}")

    income_categories_result = await db.execute(
        select(
            category_name_expr,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(ParentCategory, Category.parent_category_id == ParentCategory.id)
        .outerjoin(
            CategoryByName,
            and_(
                Transaction.category_primary == CategoryByName.name,
                CategoryByName.organization_id == current_user.organization_id
            )
        )
        .outerjoin(ParentByName, CategoryByName.parent_category_id == ParentByName.id)
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
            # Include transactions with either custom category or provider category
            (Transaction.category_id.isnot(None)) | (Transaction.category_primary.isnot(None)),
        )
        .group_by(category_name_expr)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    for row in income_categories_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.category_name, amount=amount, count=row.count, percentage=percentage
            )
        )

    logger.info(f"[CATEGORY GROUPING] Found {len(income_categories)} income categories: {[c.category for c in income_categories]}")

    # Get expenses by category - only from active accounts
    # Use hierarchical categories: show root category for child categories
    expense_categories_result = await db.execute(
        select(
            category_name_expr,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .select_from(Transaction)
        .join(Account)
        .outerjoin(Category, Transaction.category_id == Category.id)
        .outerjoin(ParentCategory, Category.parent_category_id == ParentCategory.id)
        .outerjoin(
            CategoryByName,
            and_(
                Transaction.category_primary == CategoryByName.name,
                CategoryByName.organization_id == current_user.organization_id
            )
        )
        .outerjoin(ParentByName, CategoryByName.parent_category_id == ParentByName.id)
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
            # Include transactions with either custom category or provider category
            (Transaction.category_id.isnot(None)) | (Transaction.category_primary.isnot(None)),
        )
        .group_by(category_name_expr)
        .order_by(func.sum(Transaction.amount).asc())  # Most negative first
    )

    expense_categories = []
    for row in expense_categories_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.category_name, amount=amount, count=row.count, percentage=percentage
            )
        )

    logger.info(f"[CATEGORY GROUPING] Found {len(expense_categories)} expense categories: {[c.category for c in expense_categories]}")

    # Check which categories have children (for hierarchical drill-down)
    all_category_names = set(c.category for c in income_categories + expense_categories)
    categories_with_children = set()

    for cat_name in all_category_names:
        # Check if this category exists in our database and has children
        cat_result = await db.execute(
            select(Category.id)
            .where(
                Category.organization_id == current_user.organization_id,
                Category.name == cat_name
            )
        )
        cat = cat_result.scalar_one_or_none()

        if cat:
            # Check if it has children
            children_result = await db.execute(
                select(func.count(Category.id))
                .where(
                    Category.organization_id == current_user.organization_id,
                    Category.parent_category_id == cat
                )
            )
            child_count = children_result.scalar()
            if child_count > 0:
                categories_with_children.add(cat_name)

    # Update has_children flag
    for cat in income_categories:
        cat.has_children = cat.category in categories_with_children
    for cat in expense_categories:
        cat.has_children = cat.category in categories_with_children

    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories,
    )


@router.get("/category-drill-down", response_model=IncomeExpenseSummary)
async def get_category_drill_down(
    start_date: date = Query(...),
    end_date: date = Query(...),
    parent_category: str = Query(..., description="Parent category name to drill down into"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get child categories for a specific parent category (drill-down)."""
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

    # Find the parent category
    parent_cat_result = await db.execute(
        select(Category).where(
            Category.organization_id == current_user.organization_id,
            Category.name == parent_category
        )
    )
    parent_cat = parent_cat_result.scalar_one_or_none()

    if not parent_cat:
        # If no custom category found, treat as provider category (leaf node with no children)
        income_result = await db.execute(
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                Transaction.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
                Account.exclude_from_cash_flow.is_(False),
                Transaction.is_transfer.is_(False),
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount > 0,
                Transaction.category_primary == parent_category
            )
        )
        income_row = income_result.one_or_none()
        total_income = float(income_row.total) if income_row and income_row.total else 0
        income_count = income_row.count if income_row else 0

        expense_result = await db.execute(
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                Transaction.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
                Account.exclude_from_cash_flow.is_(False),
                Transaction.is_transfer.is_(False),
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount < 0,
                Transaction.category_primary == parent_category
            )
        )
        expense_row = expense_result.one_or_none()
        total_expenses = abs(float(expense_row.total)) if expense_row and expense_row.total else 0
        expense_count = expense_row.count if expense_row else 0

        # For provider categories (leaf nodes), return single category
        return IncomeExpenseSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net=total_income - total_expenses,
            income_categories=[CategoryBreakdown(
                category=parent_category,
                amount=total_income,
                count=income_count,
                percentage=100.0
            )] if total_income > 0 else [],
            expense_categories=[CategoryBreakdown(
                category=parent_category,
                amount=total_expenses,
                count=expense_count,
                percentage=100.0
            )] if total_expenses > 0 else [],
        )

    # Check if this category has children
    child_cats_result = await db.execute(
        select(Category).where(
            Category.organization_id == current_user.organization_id,
            Category.parent_category_id == parent_cat.id
        )
    )
    child_cats = child_cats_result.scalars().all()

    if not child_cats:
        # Leaf category - return single breakdown
        income_result = await db.execute(
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                Transaction.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
                Account.exclude_from_cash_flow.is_(False),
                Transaction.is_transfer.is_(False),
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount > 0,
                Transaction.category_id == parent_cat.id
            )
        )
        income_row = income_result.one_or_none()
        total_income = float(income_row.total) if income_row and income_row.total else 0
        income_count = income_row.count if income_row else 0

        expense_result = await db.execute(
            select(
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count")
            )
            .select_from(Transaction)
            .join(Account)
            .where(
                Transaction.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
                Account.exclude_from_cash_flow.is_(False),
                Transaction.is_transfer.is_(False),
                Transaction.account_id.in_(account_ids),
                Transaction.date >= start_date,
                Transaction.date <= end_date,
                Transaction.amount < 0,
                Transaction.category_id == parent_cat.id
            )
        )
        expense_row = expense_result.one_or_none()
        total_expenses = abs(float(expense_row.total)) if expense_row and expense_row.total else 0
        expense_count = expense_row.count if expense_row else 0

        return IncomeExpenseSummary(
            total_income=total_income,
            total_expenses=total_expenses,
            net=total_income - total_expenses,
            income_categories=[CategoryBreakdown(
                category=parent_category,
                amount=total_income,
                count=income_count,
                percentage=100.0
            )] if total_income > 0 else [],
            expense_categories=[CategoryBreakdown(
                category=parent_category,
                amount=total_expenses,
                count=expense_count,
                percentage=100.0
            )] if total_expenses > 0 else [],
        )

    # Has children - return child breakdown
    child_names = [cat.name for cat in child_cats]

    # Get totals for parent (including children)
    # Match by category_primary to get accurate totals
    parent_income_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
            Transaction.category_primary.in_(child_names)
        )
    )
    total_income = float(parent_income_result.scalar() or 0)

    parent_expense_result = await db.execute(
        select(func.sum(Transaction.amount))
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.category_primary.in_(child_names)
        )
    )
    total_expenses = abs(float(parent_expense_result.scalar() or 0))

    # Get child category breakdown
    income_children_result = await db.execute(
        select(
            Transaction.category_primary.label("name"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count")
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
            Transaction.category_primary.in_(child_names)
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).desc())
    )

    income_categories = []
    for row in income_children_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(
            CategoryBreakdown(
                category=row.name,
                amount=amount,
                count=row.count,
                percentage=percentage
            )
        )

    expense_children_result = await db.execute(
        select(
            Transaction.category_primary.label("name"),
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count")
        )
        .select_from(Transaction)
        .join(Account)
        .where(
            Transaction.organization_id == current_user.organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.category_primary.in_(child_names)
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).asc())
    )

    expense_categories = []
    for row in expense_children_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(
            CategoryBreakdown(
                category=row.name,
                amount=amount,
                count=row.count,
                percentage=percentage
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
        .limit(MAX_MERCHANT_RESULTS)
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
            .limit(MAX_MERCHANT_RESULTS)
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
            .limit(MAX_MERCHANT_RESULTS)
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
        .limit(MAX_MERCHANT_RESULTS)
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
        .limit(MAX_MERCHANT_RESULTS)
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
                category=row.name, amount=amount, count=row.count, percentage=percentage, id=str(row.id)
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
                category=row.name, amount=amount, count=row.count, percentage=percentage, id=str(row.id)
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
        .limit(MAX_MERCHANT_RESULTS)
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
