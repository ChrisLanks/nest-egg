"""Dashboard API endpoints."""

from datetime import date, datetime
from typing import Optional
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import (
    get_current_user,
    verify_household_member,
    get_user_accounts,
    get_all_household_accounts
)
from app.models.user import User
from app.services.dashboard_service import DashboardService
from app.services.deduplication_service import DeduplicationService
from app.services.insights_service import InsightsService
from app.schemas.transaction import TransactionDetail


router = APIRouter()

# Initialize deduplication service
deduplication_service = DeduplicationService()


class DashboardSummary(BaseModel):
    """Dashboard summary response."""
    net_worth: float
    total_assets: float
    total_debts: float
    monthly_spending: float
    monthly_income: float
    monthly_net: float


class ExpenseCategory(BaseModel):
    """Expense category breakdown."""
    category: str
    total: float
    count: int


class AccountBalance(BaseModel):
    """Account balance info."""
    id: str
    name: str
    type: str
    balance: float
    institution: Optional[str] = None


class CashFlowMonth(BaseModel):
    """Cash flow for a month."""
    month: str
    income: float
    expenses: float
    net: float


class SpendingInsight(BaseModel):
    """Spending insight item."""
    type: str
    title: str
    message: str
    category: Optional[str] = None
    amount: Optional[float] = None
    percentage_change: Optional[float] = None
    priority: str
    icon: str


class DashboardData(BaseModel):
    """Complete dashboard data."""
    summary: DashboardSummary
    recent_transactions: list[TransactionDetail]
    top_expenses: list[ExpenseCategory]
    account_balances: list[AccountBalance]
    cash_flow_trend: list[CashFlowMonth]


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = combined household view"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary metrics."""
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    service = DashboardService(db)

    # Calculate metrics
    net_worth = await service.get_net_worth(current_user.organization_id, account_ids)
    total_assets = await service.get_total_assets(current_user.organization_id, account_ids)
    total_debts = await service.get_total_debts(current_user.organization_id, account_ids)
    monthly_spending = await service.get_monthly_spending(
        current_user.organization_id, start_date, end_date, account_ids
    )
    monthly_income = await service.get_monthly_income(
        current_user.organization_id, start_date, end_date, account_ids
    )

    return DashboardSummary(
        net_worth=float(net_worth),
        total_assets=float(total_assets),
        total_debts=float(total_debts),
        monthly_spending=float(monthly_spending),
        monthly_income=float(monthly_income),
        monthly_net=float(monthly_income - monthly_spending),
    )


@router.get("/", response_model=DashboardData)
async def get_dashboard_data(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = combined household view"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete dashboard data."""
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    service = DashboardService(db)

    # Get all dashboard data
    net_worth = await service.get_net_worth(current_user.organization_id, account_ids)
    total_assets = await service.get_total_assets(current_user.organization_id, account_ids)
    total_debts = await service.get_total_debts(current_user.organization_id, account_ids)
    monthly_spending = await service.get_monthly_spending(
        current_user.organization_id, start_date, end_date, account_ids
    )
    monthly_income = await service.get_monthly_income(
        current_user.organization_id, start_date, end_date, account_ids
    )

    recent_transactions = await service.get_recent_transactions(
        current_user.organization_id, limit=10, account_ids=account_ids
    )

    top_expenses = await service.get_expense_by_category(
        current_user.organization_id, start_date, end_date, limit=10, account_ids=account_ids
    )

    account_balances = await service.get_account_balances(current_user.organization_id, account_ids)

    cash_flow_trend = await service.get_cash_flow_trend(
        current_user.organization_id, months=6, account_ids=account_ids
    )

    # Convert transactions to TransactionDetail format
    transaction_details = []
    for txn in recent_transactions:
        # Extract labels from the many-to-many relationship
        transaction_labels = [tl.label for tl in txn.labels if tl.label]

        # Get account info
        account_name = txn.account.name if txn.account else None
        account_mask = txn.account.mask if txn.account else None

        # Extract category information
        from app.schemas.transaction import CategorySummary
        category_summary = None
        if txn.category:
            category_summary = CategorySummary(
                id=txn.category.id,
                name=txn.category.name,
                color=txn.category.color,
                parent_id=txn.category.parent_category_id,
                parent_name=txn.category.parent.name if txn.category.parent else None,
            )

        transaction_details.append(TransactionDetail(
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
            is_transfer=txn.is_transfer,
            created_at=txn.created_at,
            updated_at=txn.updated_at,
            account_name=account_name,
            account_mask=account_mask,
            category=category_summary,
            labels=transaction_labels
        ))

    return DashboardData(
        summary=DashboardSummary(
            net_worth=float(net_worth),
            total_assets=float(total_assets),
            total_debts=float(total_debts),
            monthly_spending=float(monthly_spending),
            monthly_income=float(monthly_income),
            monthly_net=float(monthly_income - monthly_spending),
        ),
        recent_transactions=transaction_details,
        top_expenses=[ExpenseCategory(**cat) for cat in top_expenses],
        account_balances=[AccountBalance(**bal) for bal in account_balances],
        cash_flow_trend=[
            CashFlowMonth(
                month=cf['month'],
                income=cf['income'],
                expenses=cf['expenses'],
                net=cf['income'] - cf['expenses']
            )
            for cf in cash_flow_trend
        ],
    )


@router.get("/insights", response_model=list[SpendingInsight])
async def get_spending_insights(
    user_id: Optional[UUID] = Query(None, description="Filter by user. None = combined household view"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get smart spending insights for dashboard."""
    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    # Generate insights
    insights = await InsightsService.generate_insights(
        db, current_user.organization_id, account_ids, max_insights=5
    )

    # Convert to SpendingInsight models
    return [
        SpendingInsight(
            type=insight['type'],
            title=insight['title'],
            message=insight['message'],
            category=insight.get('category'),
            amount=insight.get('amount'),
            percentage_change=insight.get('percentage_change'),
            priority=insight['priority'],
            icon=insight['icon']
        )
        for insight in insights
    ]
