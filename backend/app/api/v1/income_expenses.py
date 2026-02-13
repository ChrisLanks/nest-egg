"""Income vs Expenses API endpoints."""

from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.transaction import Transaction


router = APIRouter()


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get income vs expense summary for date range."""
    
    # Get total income
    income_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0
        )
    )
    total_income = float(income_result.scalar() or 0)
    
    # Get total expenses
    expense_result = await db.execute(
        select(func.sum(Transaction.amount)).where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0
        )
    )
    total_expenses = abs(float(expense_result.scalar() or 0))
    
    # Get income by category
    income_categories_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount > 0,
            Transaction.category_primary.isnot(None)
        ).group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).desc())
    )
    
    income_categories = []
    for row in income_categories_result:
        amount = float(row.total)
        percentage = (amount / total_income * 100) if total_income > 0 else 0
        income_categories.append(CategoryBreakdown(
            category=row.category_primary,
            amount=amount,
            count=row.count,
            percentage=percentage
        ))
    
    # Get expenses by category
    expense_categories_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.amount < 0,
            Transaction.category_primary.isnot(None)
        ).group_by(Transaction.category_primary)
        .order_by(func.sum(Transaction.amount).asc())  # Most negative first
    )
    
    expense_categories = []
    for row in expense_categories_result:
        amount = abs(float(row.total))
        percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
        expense_categories.append(CategoryBreakdown(
            category=row.category_primary,
            amount=amount,
            count=row.count,
            percentage=percentage
        ))
    
    return IncomeExpenseSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        income_categories=income_categories,
        expense_categories=expense_categories
    )


@router.get("/trend", response_model=List[MonthlyTrend])
async def get_income_expense_trend(
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get monthly income vs expense trend."""

    result = await db.execute(
        select(
            func.date_trunc('month', Transaction.date).label('month'),
            func.sum(
                func.case((Transaction.amount > 0, Transaction.amount), else_=0)
            ).label('income'),
            func.sum(
                func.case((Transaction.amount < 0, Transaction.amount), else_=0)
            ).label('expenses')
        ).where(
            Transaction.organization_id == current_user.organization_id,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        ).group_by(func.date_trunc('month', Transaction.date))
        .order_by(func.date_trunc('month', Transaction.date))
    )

    trend = []
    for row in result:
        income = float(row.income or 0)
        expenses = abs(float(row.expenses or 0))
        trend.append(MonthlyTrend(
            month=row.month.strftime('%Y-%m') if row.month else '',
            income=income,
            expenses=expenses,
            net=income - expenses
        ))

    return trend


@router.get("/merchants", response_model=List[CategoryBreakdown])
async def get_merchant_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    category: Optional[str] = Query(None),
    transaction_type: str = Query(..., description="income or expense"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get merchant breakdown for a category."""

    # Build base conditions
    conditions = [
        Transaction.organization_id == current_user.organization_id,
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Transaction.merchant_name.isnot(None),
    ]

    # Add transaction type filter
    if transaction_type == 'income':
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
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count')
        ).where(and_(*conditions))
        .group_by(Transaction.merchant_name)
        .order_by(func.sum(Transaction.amount).desc() if transaction_type == 'income' else func.sum(Transaction.amount).asc())
    )

    # Calculate total for percentage
    total_result = await db.execute(
        select(func.sum(Transaction.amount)).where(and_(*conditions))
    )
    total = abs(float(total_result.scalar() or 0))

    merchants = []
    for row in result:
        amount = abs(float(row.total))
        percentage = (amount / total * 100) if total > 0 else 0
        merchants.append(CategoryBreakdown(
            category=row.merchant_name,  # Using category field to store merchant name
            amount=amount,
            count=row.count,
            percentage=percentage
        ))

    return merchants
