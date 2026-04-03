"""Dashboard API endpoints."""

import calendar as cal_mod
import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, asc, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get as cache_get
from app.core.cache import setex as cache_setex
from app.core.database import get_db
from app.dependencies import (
    get_all_household_accounts,
    get_current_user,
    get_user_accounts,
    verify_household_member,
)
from app.models.account import Account
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.models.transaction import Transaction, TransactionSplit
from app.models.user import User
from app.schemas.transaction import CategorySummary, TransactionDetail
from app.services.dashboard_service import DashboardService
from app.services.deduplication_service import DeduplicationService
from app.services.financial_health_service import FinancialHealthService
from app.services.forecast_service import ForecastService
from app.services.insights_service import InsightsService
from app.services.milestone_service import get_milestone_summary
from app.services.net_worth_benchmark_service import compute_benchmark, get_all_age_group_medians
from app.services.trend_analysis_service import TrendAnalysisService
from app.constants.financial import NET_WORTH_MILESTONES
from app.utils.date_validation import validate_date_range

logger = logging.getLogger(__name__)


router = APIRouter()

# Cache TTLs (seconds) — centralised so they can be tuned in one place
_CACHE_TTL_SUMMARY = 300       # 5 min: dashboard summary stats
_CACHE_TTL_DASHBOARD = 60      # 60 s: full dashboard data (more volatile)
_CACHE_TTL_HEALTH = 3600       # 1 hr: financial health score (expensive, slow-changing)
_CACHE_TTL_INSIGHTS = 300      # 5 min: smart insights / spending analysis

# Initialize deduplication service
deduplication_service = DeduplicationService()


class MemberSpending(BaseModel):
    """Per-member spending breakdown for the summary period."""

    member_id: str
    member_name: str
    spending: float


class DashboardSummary(BaseModel):
    """Dashboard summary response."""

    net_worth: float
    total_assets: float
    total_debts: float
    monthly_spending: float
    monthly_income: float
    monthly_net: float
    spending_by_member: List[MemberSpending] = []


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


class ForecastTransaction(BaseModel):
    """Individual transaction within a forecast day."""

    merchant: Optional[str] = None
    amount: float
    category: Optional[str] = None
    label: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    event_type: str = "recurring"


class ForecastDataPoint(BaseModel):
    """Cash flow forecast data point."""

    date: str
    projected_balance: float
    day_change: float
    transaction_count: int
    income: float = 0.0
    expenses: float = 0.0
    transactions: list[ForecastTransaction] = []


class ForecastBreakdownItem(BaseModel):
    """Named amount for a forecast breakdown dimension."""

    name: str
    amount: float


class ForecastSummary(BaseModel):
    """Aggregated forecast summary over the full window."""

    total_income: float
    total_expenses: float
    net: float
    by_category: list[ForecastBreakdownItem]
    by_merchant: list[ForecastBreakdownItem]
    by_label: list[ForecastBreakdownItem]
    by_account: list[ForecastBreakdownItem]
    by_member: list[ForecastBreakdownItem] = []


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
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary metrics."""
    # Check cache (5 min TTL)
    cache_key = (
        f"dashboard:summary:{current_user.organization_id}"
        f":{user_id or 'household'}:{start_date}:{end_date}"
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return DashboardSummary(**cached)

    if start_date and end_date:
        validate_date_range(start_date, end_date)

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
    accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    service = DashboardService(db)

    # Reuse the already-fetched accounts instead of re-querying
    net_worth = service.compute_net_worth(accounts)
    total_assets = service.compute_total_assets(accounts)
    total_debts = service.compute_total_debts(accounts)

    # Single query for both spending and income (CASE WHEN)
    monthly_spending, monthly_income = await service.get_spending_and_income(
        current_user.organization_id, start_date, end_date, account_ids
    )

    # Per-member spending breakdown (only meaningful in combined household view)
    spending_by_member: List[MemberSpending] = []
    if not user_id:
        # Sum spending per account owner by joining accounts→transactions
        member_spending_rows = await db.execute(
            select(Account.user_id, func.sum(Transaction.amount).label("total"))
            .join(Transaction, Transaction.account_id == Account.id)
            .where(
                Account.organization_id == current_user.organization_id,
                Account.id.in_(account_ids),
                Transaction.is_transfer.is_(False),
                Transaction.is_pending.is_(False),
                Transaction.amount < 0,
                *(
                    [Transaction.date >= start_date] if start_date else []
                ),
                *(
                    [Transaction.date <= end_date] if end_date else []
                ),
            )
            .group_by(Account.user_id)
        )
        member_rows = member_spending_rows.all()
        if member_rows:
            member_user_ids = [r.user_id for r in member_rows]
            users_result = await db.execute(
                select(User.id, User.display_name, User.first_name, User.email).where(
                    User.id.in_(member_user_ids)
                )
            )
            users_map = {
                u.id: (u.display_name or u.first_name or u.email or str(u.id))
                for u in users_result.all()
            }
            spending_by_member = [
                MemberSpending(
                    member_id=str(r.user_id),
                    member_name=users_map.get(r.user_id, str(r.user_id)),
                    spending=abs(float(r.total)),
                )
                for r in member_rows
            ]

    summary = DashboardSummary(
        net_worth=float(net_worth),
        total_assets=float(total_assets),
        total_debts=float(total_debts),
        monthly_spending=float(monthly_spending),
        monthly_income=float(monthly_income),
        monthly_net=float(monthly_income - monthly_spending),
        spending_by_member=spending_by_member,
    )
    await cache_setex(cache_key, _CACHE_TTL_SUMMARY, summary.model_dump())
    return summary


@router.get("/", response_model=DashboardData)
async def get_dashboard_data(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete dashboard data."""
    if start_date and end_date:
        validate_date_range(start_date, end_date)

    # Check Redis cache first (60s TTL)
    cache_key = f"dashboard:{current_user.organization_id}:{user_id}:{start_date}:{end_date}"
    try:
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        logger.debug("Dashboard cache read failed for key %s", cache_key, exc_info=True)

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    service = DashboardService(db)

    # Fetch accounts once (eliminates 4 redundant identical queries)
    accounts = await service.get_active_accounts(current_user.organization_id, account_ids)

    # Compute account-based metrics synchronously from pre-fetched data
    net_worth = service.compute_net_worth(accounts)
    total_assets = service.compute_total_assets(accounts)
    total_debts = service.compute_total_debts(accounts)
    account_balances = service.compute_account_balances(accounts)

    # Single query for both spending and income (CASE WHEN)
    monthly_spending, monthly_income = await service.get_spending_and_income(
        current_user.organization_id, start_date, end_date, account_ids
    )

    recent_transactions = await service.get_recent_transactions(
        current_user.organization_id, limit=10, account_ids=account_ids
    )

    top_expenses = await service.get_expense_by_category(
        current_user.organization_id, start_date, end_date, limit=10, account_ids=account_ids
    )

    cash_flow_trend = await service.get_cash_flow_trend(
        current_user.organization_id, months=12, account_ids=account_ids
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
        category_summary = None
        if txn.category:
            category_summary = CategorySummary(
                id=txn.category.id,
                name=txn.category.name,
                color=txn.category.color,
                parent_id=txn.category.parent_category_id,
                parent_name=txn.category.parent.name if txn.category.parent else None,
            )

        transaction_details.append(
            TransactionDetail(
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
                labels=transaction_labels,
            )
        )

    response = DashboardData(
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
                month=cf["month"],
                income=cf["income"],
                expenses=cf["expenses"],
                net=cf["income"] - cf["expenses"],
            )
            for cf in cash_flow_trend
        ],
    )

    # Cache the response
    try:
        response_dict = response.model_dump(mode="json")
        await cache_setex(cache_key, _CACHE_TTL_DASHBOARD, response_dict)
    except Exception:
        logger.debug("Failed to write dashboard cache for key %s", cache_key)

    return response


# ── Net Worth Milestones ─────────────────────────────────────────────────────


class MilestoneItem(BaseModel):
    """A single achieved milestone."""

    threshold: int
    label: str


class AllTimeHighInfo(BaseModel):
    """All-time-high net worth info."""

    value: float
    date: Optional[str] = None
    is_current: bool


class MilestoneResponse(BaseModel):
    """Milestone summary response."""

    milestones_achieved: list[MilestoneItem]
    all_time_high: AllTimeHighInfo
    next_milestone: Optional[int] = None


@router.get("/milestones", response_model=MilestoneResponse)
async def get_milestones(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get net worth milestones and all-time-high status for the household."""
    summary = await get_milestone_summary(db, current_user.organization_id)

    return MilestoneResponse(
        milestones_achieved=[MilestoneItem(**m) for m in summary["milestones_achieved"]],
        all_time_high=AllTimeHighInfo(**summary["all_time_high"]),
        next_milestone=summary["next_milestone"],
    )


@router.get("/insights", response_model=list[SpendingInsight])
async def get_spending_insights(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
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
            type=insight["type"],
            title=insight["title"],
            message=insight["message"],
            category=insight.get("category"),
            amount=insight.get("amount"),
            percentage_change=insight.get("percentage_change"),
            priority=insight["priority"],
            icon=insight["icon"],
        )
        for insight in insights
    ]


@router.get("/forecast", response_model=list[ForecastDataPoint])
async def get_cash_flow_forecast(
    days_ahead: int = Query(90, ge=30, le=365, description="Number of days to forecast"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get projected cash flow forecast based on recurring transactions."""
    # Verify household member if user_id provided
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Generate forecast
    forecast = await ForecastService.generate_forecast(
        db, current_user.organization_id, user_id, days_ahead
    )

    return [ForecastDataPoint(**day) for day in forecast]


@router.get("/forecast/summary", response_model=ForecastSummary)
async def get_cash_flow_forecast_summary(
    days_ahead: int = Query(90, ge=30, le=365, description="Number of days to forecast"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated forecast summary: totals and breakdowns by category/merchant/label/account."""
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    summary = await ForecastService.generate_forecast_summary(
        db, current_user.organization_id, user_id, days_ahead
    )
    return ForecastSummary(**summary)


# ---------------------------------------------------------------------------
# Pydantic models for financial health score
# ---------------------------------------------------------------------------


class HealthComponent(BaseModel):
    """Individual component of the financial health score."""

    score: float
    value: float
    label: str
    detail: str


class HealthComponents(BaseModel):
    """All four scored components."""

    savings_rate: HealthComponent
    emergency_fund: HealthComponent
    debt_to_income: HealthComponent
    retirement_progress: HealthComponent


class FinancialHealthResponse(BaseModel):
    """Financial health score response."""

    overall_score: float
    grade: str
    components: HealthComponents
    recommendations: list[str]


@router.get("/financial-health", response_model=FinancialHealthResponse)
async def get_financial_health(
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get financial health score (0-100) with component breakdown."""
    # Check Redis cache first (1-hour TTL)
    cache_key = f"financial-health:{current_user.organization_id}:{user_id}"
    try:
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        logger.debug("Financial-health cache read failed for key %s", cache_key, exc_info=True)

    # Get accounts based on user filter
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = [acc.id for acc in accounts]

    service = FinancialHealthService(db)
    result = await service.calculate(
        organization_id=str(current_user.organization_id),
        user_id=user_id or current_user.id,
        account_ids=account_ids,
    )

    # Cache with health TTL (changes slowly — expensive to compute)
    try:
        await cache_setex(cache_key, _CACHE_TTL_HEALTH, result)
    except Exception:
        logger.debug("Failed to write financial-health cache for key %s", cache_key)

    return result


# ── Financial Calendar ─────────────────────────────────────────────────────────


class FinancialCalendarEvent(BaseModel):
    """A single financial event on the calendar."""

    date: str
    type: str  # "bill", "subscription", "income"
    name: str
    amount: float
    account: Optional[str] = None
    frequency: Optional[str] = None


class DailyProjectedBalance(BaseModel):
    """Projected balance for a single day."""

    date: str
    balance: float


class FinancialCalendarSummary(BaseModel):
    """Summary totals for the calendar month."""

    total_income: float
    total_bills: float
    total_subscriptions: float
    projected_end_balance: float


class FinancialCalendarResponse(BaseModel):
    """Full financial calendar response."""

    events: List[FinancialCalendarEvent]
    daily_projected_balance: List[DailyProjectedBalance]
    summary: FinancialCalendarSummary


def _expand_occurrences_for_range(
    pattern: RecurringTransaction,
    start: date,
    end: date,
) -> List[date]:
    """Generate all occurrence dates for a recurring pattern within [start, end]."""
    anchor = pattern.next_expected_date
    if not anchor:
        return []

    freq = pattern.frequency

    if freq == RecurringFrequency.ON_DEMAND:
        return []

    def _step(d: date, forward: bool = True) -> date:
        delta = 1 if forward else -1
        if freq == RecurringFrequency.WEEKLY:
            return d + timedelta(weeks=delta)
        if freq == RecurringFrequency.BIWEEKLY:
            return d + timedelta(weeks=2 * delta)
        if freq == RecurringFrequency.MONTHLY:
            return d + relativedelta(months=delta)
        if freq == RecurringFrequency.QUARTERLY:
            return d + relativedelta(months=3 * delta)
        return d + relativedelta(years=delta)

    first = anchor
    while first > start:
        first = _step(first, forward=False)
    while first < start:
        first = _step(first, forward=True)

    occurrences: List[date] = []
    current = first
    while current <= end:
        occurrences.append(current)
        current = _step(current, forward=True)

    return occurrences


@router.get("/financial-calendar", response_model=FinancialCalendarResponse)
async def get_financial_calendar(
    month: str = Query(
        ...,
        description="Month in YYYY-MM format",
        pattern=r"^\d{4}-\d{2}$",
    ),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all financial events for a calendar month.

    Aggregates recurring bills, subscriptions, and income patterns into a
    unified calendar view with projected daily balances.
    """
    # Parse month parameter
    year, month_num = int(month[:4]), int(month[5:7])
    month_start = date(year, month_num, 1)
    last_day = cal_mod.monthrange(year, month_num)[1]
    month_end = date(year, month_num, last_day)

    # Verify household member if user_id provided
    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Get accounts for filtering and name lookups
    if user_id:
        accounts = await get_user_accounts(db, user_id, current_user.organization_id)
    else:
        accounts = await get_all_household_accounts(db, current_user.organization_id)
        accounts = deduplication_service.deduplicate_accounts(accounts)

    account_ids = {acc.id for acc in accounts}
    account_name_map = {acc.id: acc.name for acc in accounts}

    # Fetch all active recurring transactions for the organization
    result = await db.execute(
        select(RecurringTransaction).where(
            and_(
                RecurringTransaction.organization_id == current_user.organization_id,
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_expected_date.isnot(None),
            )
        )
    )
    all_patterns = list(result.scalars().all())

    # Filter by user's accounts if user_id provided
    if user_id:
        all_patterns = [p for p in all_patterns if p.account_id in account_ids]

    # Classify patterns and build events
    events: List[FinancialCalendarEvent] = []

    # Subscription IDs — monthly/yearly with high confidence and negative amount
    subscription_ids: set = set()
    for p in all_patterns:
        if (
            p.frequency in (RecurringFrequency.MONTHLY, RecurringFrequency.YEARLY)
            and p.confidence_score is not None
            and p.confidence_score >= Decimal("0.70")
            and float(p.average_amount) < 0
        ):
            subscription_ids.add(p.id)

    for pattern in all_patterns:
        occurrences = _expand_occurrences_for_range(pattern, month_start, month_end)
        avg = float(pattern.average_amount)
        acct_name = account_name_map.get(pattern.account_id)

        # Classify: income (positive amount), subscription, or bill
        if avg > 0:
            event_type = "income"
        elif pattern.id in subscription_ids:
            event_type = "subscription"
        else:
            event_type = "bill"

        for occ_date in occurrences:
            events.append(
                FinancialCalendarEvent(
                    date=occ_date.isoformat(),
                    type=event_type,
                    name=pattern.merchant_name,
                    amount=round(avg, 2),
                    account=acct_name,
                    frequency=pattern.frequency.value if pattern.frequency else None,
                )
            )

    # Sort events by date
    events.sort(key=lambda e: e.date)

    # ── Compute daily projected balance ──────────────────────────────────────

    # Get current total balance across relevant accounts
    current_balance = await ForecastService._get_total_balance(
        db, current_user.organization_id, user_id
    )

    # Build a date->amount map from events
    daily_changes: dict[date, float] = defaultdict(float)
    for ev in events:
        ev_date = date.fromisoformat(ev.date)
        daily_changes[ev_date] += ev.amount

    # Account for events between today and month start that affect the balance
    today = date.today()
    if month_start > today:
        pre_month_start = today + timedelta(days=1)
        pre_month_end = month_start - timedelta(days=1)
        if pre_month_start <= pre_month_end:
            for pattern in all_patterns:
                pre_occurrences = _expand_occurrences_for_range(
                    pattern, pre_month_start, pre_month_end
                )
                for _occ_date in pre_occurrences:
                    current_balance += Decimal(str(float(pattern.average_amount)))

    # Build daily projected balance for the month
    daily_projected: List[DailyProjectedBalance] = []
    running = float(current_balance)
    for day_num in range(1, last_day + 1):
        d = date(year, month_num, day_num)
        if d >= today:
            running += daily_changes.get(d, 0.0)
        daily_projected.append(
            DailyProjectedBalance(
                date=d.isoformat(),
                balance=round(running, 2),
            )
        )

    # ── Compute summary ──────────────────────────────────────────────────────

    total_income = sum(ev.amount for ev in events if ev.type == "income")
    total_bills = sum(ev.amount for ev in events if ev.type == "bill")
    total_subscriptions = sum(ev.amount for ev in events if ev.type == "subscription")
    projected_end = daily_projected[-1].balance if daily_projected else float(current_balance)

    return FinancialCalendarResponse(
        events=events,
        daily_projected_balance=daily_projected,
        summary=FinancialCalendarSummary(
            total_income=round(total_income, 2),
            total_bills=round(total_bills, 2),
            total_subscriptions=round(total_subscriptions, 2),
            projected_end_balance=round(projected_end, 2),
        ),
    )


# ── Year-in-Review ────────────────────────────────────────────────────────────


class YearInReviewIncome(BaseModel):
    total: float
    avg_monthly: float
    best_month: Optional[str] = None
    best_amount: float = 0


class YearInReviewExpenses(BaseModel):
    total: float
    avg_monthly: float
    biggest_month: Optional[str] = None
    biggest_amount: float = 0


class YearInReviewNetWorth(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None
    change: Optional[float] = None
    change_pct: Optional[float] = None


class YearInReviewCategory(BaseModel):
    category: str
    total: float
    pct_of_total: float


class YearInReviewMerchant(BaseModel):
    merchant: str
    total: float
    count: int


class YearInReviewYoY(BaseModel):
    income_change_pct: Optional[float] = None
    expense_change_pct: Optional[float] = None
    savings_rate_change: Optional[float] = None


class YearInReviewResponse(BaseModel):
    year: int
    income: YearInReviewIncome
    expenses: YearInReviewExpenses
    net_income: float
    savings_rate: Optional[float] = None
    net_worth: YearInReviewNetWorth
    top_expense_categories: List[YearInReviewCategory]
    top_merchants: List[YearInReviewMerchant]
    milestones: List[str]
    yoy_comparison: YearInReviewYoY


@router.get("/year-in-review", response_model=YearInReviewResponse)
async def get_year_in_review(
    year: int = Query(..., ge=2000, le=2100, description="Year to review"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a comprehensive year-in-review summary."""
    org_id = current_user.organization_id

    # Resolve account IDs
    if user_id:
        await verify_household_member(db, user_id, org_id)
        raw_accounts = await get_user_accounts(db, user_id, org_id)
    else:
        raw_accounts = await get_all_household_accounts(db, org_id)
        raw_accounts = deduplication_service.deduplicate_accounts(raw_accounts)
    account_ids = [acc.id for acc in raw_accounts]

    # Check cache
    cache_key = f"year-in-review:{org_id}:{user_id}:{year}"
    try:
        cached = await cache_get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        logger.debug("Year-in-review cache read failed for key %s", cache_key, exc_info=True)

    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # --- 1. Annual income/expense summary ---
    annual = await TrendAnalysisService.get_annual_summary(
        db,
        org_id,
        year,
        user_id=user_id,
        account_ids=account_ids,
    )
    yr_total_income = annual["total_income"]
    yr_total_expenses = annual["total_expenses"]
    net_income = yr_total_income - yr_total_expenses
    savings_rate = (net_income / yr_total_income * 100) if yr_total_income > 0 else None

    # --- 2. Best income month ---
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    base_conditions = [
        Transaction.organization_id == org_id,
        Account.is_active.is_(True),
        Account.exclude_from_cash_flow.is_(False),
        Transaction.is_transfer.is_(False),
        Transaction.account_id.in_(account_ids),
        Transaction.date >= year_start,
        Transaction.date <= year_end,
    ]
    if user_id:
        base_conditions.append(Account.user_id == user_id)

    income_month_result = await db.execute(
        select(
            extract("month", Transaction.date).label("month"),
            func.sum(Transaction.amount).label("total"),
        )
        .select_from(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(and_(*base_conditions, Transaction.amount > 0))
        .group_by(extract("month", Transaction.date))
        .order_by(func.sum(Transaction.amount).desc())
        .limit(1)
    )
    best_income_row = income_month_result.one_or_none()
    best_month = month_names[int(best_income_row.month) - 1] if best_income_row else None
    best_amount = float(best_income_row.total) if best_income_row else 0

    # --- 3. Top expense categories ---
    cat_result = await db.execute(
        select(
            Transaction.category_primary,
            func.sum(func.abs(Transaction.amount)).label("total"),
        )
        .select_from(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            and_(
                *base_conditions,
                Transaction.amount < 0,
                Transaction.category_primary.isnot(None),
            )
        )
        .group_by(Transaction.category_primary)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .limit(10)
    )
    top_categories = []
    for row in cat_result.all():
        pct = (float(row.total) / yr_total_expenses * 100) if yr_total_expenses > 0 else 0
        top_categories.append(
            YearInReviewCategory(
                category=row.category_primary,
                total=float(row.total),
                pct_of_total=round(pct, 1),
            )
        )

    # --- 4. Top merchants ---
    merchant_result = await db.execute(
        select(
            Transaction.merchant_name,
            func.sum(func.abs(Transaction.amount)).label("total"),
            func.count(Transaction.id).label("cnt"),
        )
        .select_from(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            and_(
                *base_conditions,
                Transaction.amount < 0,
                Transaction.merchant_name.isnot(None),
            )
        )
        .group_by(Transaction.merchant_name)
        .order_by(func.sum(func.abs(Transaction.amount)).desc())
        .limit(10)
    )
    top_merchants = [
        YearInReviewMerchant(merchant=row.merchant_name, total=float(row.total), count=row.cnt)
        for row in merchant_result.all()
    ]

    # --- 5. Net worth start/end from snapshots ---
    nw_start_val: Optional[float] = None
    nw_end_val: Optional[float] = None

    nw_base = [NetWorthSnapshot.organization_id == org_id]
    if user_id:
        nw_base.append(NetWorthSnapshot.user_id == user_id)
    else:
        nw_base.append(NetWorthSnapshot.user_id.is_(None))

    start_snap = await db.execute(
        select(NetWorthSnapshot.total_net_worth)
        .where(and_(*nw_base, NetWorthSnapshot.snapshot_date <= year_start))
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    row = start_snap.one_or_none()
    if row:
        nw_start_val = float(row.total_net_worth)

    end_snap = await db.execute(
        select(NetWorthSnapshot.total_net_worth)
        .where(
            and_(
                *nw_base,
                NetWorthSnapshot.snapshot_date >= year_start,
                NetWorthSnapshot.snapshot_date <= year_end,
            )
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    row = end_snap.one_or_none()
    if row:
        nw_end_val = float(row.total_net_worth)

    nw_change: Optional[float] = None
    nw_change_pct: Optional[float] = None
    if nw_start_val is not None and nw_end_val is not None:
        nw_change = nw_end_val - nw_start_val
        if nw_start_val != 0:
            nw_change_pct = round(nw_change / abs(nw_start_val) * 100, 1)

    # --- 6. Year-over-year comparison ---
    prev_annual = await TrendAnalysisService.get_annual_summary(
        db,
        org_id,
        year - 1,
        user_id=user_id,
        account_ids=account_ids,
    )
    prev_income = prev_annual["total_income"]
    prev_expenses = prev_annual["total_expenses"]
    prev_net = prev_income - prev_expenses
    prev_savings_rate = (prev_net / prev_income * 100) if prev_income > 0 else None

    income_change_pct = (
        round((yr_total_income - prev_income) / prev_income * 100, 1) if prev_income > 0 else None
    )
    expense_change_pct = (
        round((yr_total_expenses - prev_expenses) / prev_expenses * 100, 1)
        if prev_expenses > 0
        else None
    )
    savings_rate_change = (
        round(savings_rate - prev_savings_rate, 1)
        if savings_rate is not None and prev_savings_rate is not None
        else None
    )

    # --- 7. Milestones ---
    milestones: List[str] = []
    if net_income > 0:
        milestones.append(f"Saved ${net_income:,.0f} this year")
    if savings_rate is not None and savings_rate >= 20:
        milestones.append(f"Achieved {savings_rate:.0f}% savings rate")
    if nw_end_val is not None:
        for t in NET_WORTH_MILESTONES.TIERS:
            if nw_start_val is not None and nw_start_val < t <= nw_end_val:
                milestones.append(f"Reached ${t:,.0f} net worth")
    if income_change_pct is not None and income_change_pct > 0:
        milestones.append(f"Grew income by {income_change_pct:.1f}% year-over-year")

    # Build response
    response = YearInReviewResponse(
        year=year,
        income=YearInReviewIncome(
            total=yr_total_income,
            avg_monthly=round(yr_total_income / 12, 2),
            best_month=best_month,
            best_amount=best_amount,
        ),
        expenses=YearInReviewExpenses(
            total=yr_total_expenses,
            avg_monthly=round(yr_total_expenses / 12, 2),
            biggest_month=annual.get("peak_expense_month"),
            biggest_amount=annual.get("peak_expense_amount", 0),
        ),
        net_income=net_income,
        savings_rate=round(savings_rate, 1) if savings_rate is not None else None,
        net_worth=YearInReviewNetWorth(
            start=nw_start_val,
            end=nw_end_val,
            change=nw_change,
            change_pct=nw_change_pct,
        ),
        top_expense_categories=top_categories,
        top_merchants=top_merchants,
        milestones=milestones,
        yoy_comparison=YearInReviewYoY(
            income_change_pct=income_change_pct,
            expense_change_pct=expense_change_pct,
            savings_rate_change=savings_rate_change,
        ),
    )

    # Cache with summary TTL (5 min)
    try:
        await cache_setex(cache_key, _CACHE_TTL_SUMMARY, response.model_dump(mode="json"))
    except Exception:
        logger.debug("Failed to cache year-in-review for key %s", cache_key)

    return response


# ── Net Worth History ─────────────────────────────────────────────────────────


class NetWorthHistoryPoint(BaseModel):
    """One data point in the net worth history timeline."""

    snapshot_date: str
    total_net_worth: float
    total_assets: float
    total_liabilities: float
    # Asset breakdown
    cash_and_checking: float
    savings: float
    investments: float
    retirement: float
    property: float
    vehicles: float
    other_assets: float
    # Liability breakdown
    credit_cards: float
    loans: float
    mortgages: float
    student_loans: float
    other_debts: float


@router.get("/net-worth-history", response_model=list[NetWorthHistoryPoint])
async def get_net_worth_history(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: Optional[UUID] = Query(
        None, description="Filter by user. None = combined household view"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily net worth snapshots with full asset/liability breakdown.

    Uses NetWorthSnapshot records (captured nightly by the snapshot task).
    When user_id is omitted, returns household-level snapshots (user_id IS NULL).
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=365)

    if start_date and end_date:
        validate_date_range(start_date, end_date)

    if user_id:
        await verify_household_member(db, user_id, current_user.organization_id)

    # Build query
    query = select(NetWorthSnapshot).where(
        NetWorthSnapshot.organization_id == current_user.organization_id,
        NetWorthSnapshot.snapshot_date >= start_date,
    )

    if end_date:
        query = query.where(NetWorthSnapshot.snapshot_date <= end_date)

    if user_id:
        query = query.where(NetWorthSnapshot.user_id == user_id)
    else:
        query = query.where(NetWorthSnapshot.user_id.is_(None))

    query = query.order_by(asc(NetWorthSnapshot.snapshot_date))

    result = await db.execute(query)
    snapshots = result.scalars().all()

    # Lazy bootstrap: if no snapshots exist yet, OR if only a stale $0 snapshot
    # exists (captured before accounts were added), re-capture today's snapshot.
    only_zero = snapshots and all(
        (s.total_net_worth is None or s.total_net_worth == 0) for s in snapshots
    )
    if not snapshots or only_zero:
        import logging as _logging
        from app.core.database import AsyncSessionLocal
        from app.services.net_worth_service import NetWorthService
        _logger = _logging.getLogger(__name__)
        try:
            # Use a separate session so the bootstrap commit never touches the
            # request-scoped session — mid-request commits corrupt the connection
            # and cause ConnectionDoesNotExistError on subsequent operations.
            async with AsyncSessionLocal() as bootstrap_db:
                svc = NetWorthService()
                snap = await svc.capture_snapshot(
                    bootstrap_db, current_user.organization_id, user_id or None
                )
            # Only use the bootstrapped snapshot if it has real data (non-zero net worth)
            # — avoids showing a $0 placeholder when the org has no accounts yet.
            if snap and snap.total_net_worth and snap.total_net_worth != 0:
                # Re-query on the original request session now that the snapshot is committed
                fresh_query = select(NetWorthSnapshot).where(
                    NetWorthSnapshot.organization_id == current_user.organization_id,
                    NetWorthSnapshot.snapshot_date >= start_date,
                )
                if end_date:
                    fresh_query = fresh_query.where(NetWorthSnapshot.snapshot_date <= end_date)
                if user_id:
                    fresh_query = fresh_query.where(NetWorthSnapshot.user_id == user_id)
                else:
                    fresh_query = fresh_query.where(NetWorthSnapshot.user_id.is_(None))
                fresh_query = fresh_query.order_by(asc(NetWorthSnapshot.snapshot_date))
                result2 = await db.execute(fresh_query)
                snapshots = result2.scalars().all()
        except Exception:
            _logger.exception("Net worth lazy bootstrap failed for org %s", current_user.organization_id)
            pass  # Non-fatal: return empty list if bootstrap fails

    def _float(v) -> float:
        return float(v) if v is not None else 0.0

    return [
        NetWorthHistoryPoint(
            snapshot_date=s.snapshot_date.isoformat(),
            total_net_worth=_float(s.total_net_worth),
            total_assets=_float(s.total_assets),
            total_liabilities=_float(s.total_liabilities),
            cash_and_checking=_float(s.cash_and_checking),
            savings=_float(s.savings),
            investments=_float(s.investments),
            retirement=_float(s.retirement),
            property=_float(s.property),
            vehicles=_float(s.vehicles),
            other_assets=_float(s.other_assets),
            credit_cards=_float(s.credit_cards),
            loans=_float(s.loans),
            mortgages=_float(s.mortgages),
            student_loans=_float(s.student_loans),
            other_debts=_float(s.other_debts),
        )
        for s in snapshots
    ]


# ---------------------------------------------------------------------------
# Net Worth Benchmarks
# ---------------------------------------------------------------------------


class NetWorthBenchmarkResponse(BaseModel):
    age_group: str
    age_group_label: str
    user_net_worth: float
    median_net_worth: int
    mean_net_worth: int
    percentile: int
    p25: int
    p50: int
    p75: int
    p90: int
    next_milestone_label: Optional[str]
    next_milestone_value: Optional[int]
    gap_to_next_milestone: Optional[float]
    all_age_groups: list[dict]


@router.get("/net-worth-benchmark", response_model=NetWorthBenchmarkResponse)
async def get_net_worth_benchmark(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compare the current user's net worth against SCF 2022 peers in their age group.

    Requires the user to have a birthdate set in their profile. Returns percentile
    rank, median/mean for their cohort, and the next milestone to reach.
    """
    # Resolve current net worth from latest snapshot or live accounts
    snapshot_query = (
        select(NetWorthSnapshot.total_net_worth)
        .where(
            NetWorthSnapshot.organization_id == current_user.organization_id,
            NetWorthSnapshot.user_id.is_(None),
        )
        .order_by(NetWorthSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot_result = await db.execute(snapshot_query)
    snapshot_row = snapshot_result.first()

    if snapshot_row:
        net_worth = float(snapshot_row[0])
    else:
        # Fall back to live account balances
        accounts_result = await db.execute(
            select(Account).where(
                Account.organization_id == current_user.organization_id,
                Account.is_active.is_(True),
            )
        )
        accounts = accounts_result.scalars().all()
        service = DashboardService()
        net_worth = float(service.compute_net_worth(accounts))

    # Determine age from birthdate
    if current_user.birthdate:
        age = date.today().year - current_user.birthdate.year
    else:
        # Default to 40 if no birthdate — still shows useful benchmarks
        age = 40

    benchmark = compute_benchmark(net_worth, age)
    all_groups = get_all_age_group_medians()

    return NetWorthBenchmarkResponse(
        age_group=benchmark.age_group,
        age_group_label=benchmark.age_group_label,
        user_net_worth=benchmark.user_net_worth,
        median_net_worth=benchmark.median_net_worth,
        mean_net_worth=benchmark.mean_net_worth,
        percentile=benchmark.percentile,
        p25=benchmark.p25,
        p50=benchmark.p50,
        p75=benchmark.p75,
        p90=benchmark.p90,
        next_milestone_label=benchmark.next_milestone_label,
        next_milestone_value=benchmark.next_milestone_value,
        gap_to_next_milestone=benchmark.gap_to_next_milestone,
        all_age_groups=all_groups,
    )
