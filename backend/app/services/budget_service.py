"""Service for managing budgets and tracking spending."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetPeriod
from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.transaction import Category, Transaction, TransactionLabel
from app.models.user import Organization, User
from app.services.notification_service import NotificationService
from app.utils.datetime_utils import utc_now


class BudgetService:
    """Service for creating and managing budgets."""

    @staticmethod
    def _get_period_dates(
        period: BudgetPeriod,
        reference_date: date = None,
        monthly_start_day: int = 1,
    ) -> tuple[date, date]:
        """Get start and end dates for a budget period.

        monthly_start_day (1-28) is the household setting for when periods begin.
        For example, start_day=15 means monthly periods run from the 15th of one
        month through the 14th of the next.
        """
        if reference_date is None:
            reference_date = date.today()

        # Clamp to safe range (schema enforces 1-28; guard here too)
        start_day = max(1, min(monthly_start_day, 28))

        if period == BudgetPeriod.MONTHLY:
            # Determine whether today is before or after the start_day this month
            if reference_date.day >= start_day:
                start = reference_date.replace(day=start_day)
            else:
                # Start is in the previous month
                if reference_date.month == 1:
                    start = reference_date.replace(
                        year=reference_date.year - 1, month=12, day=start_day
                    )
                else:
                    start = reference_date.replace(month=reference_date.month - 1, day=start_day)

            # End is one day before the next start_day
            if start.month == 12:
                end = date(start.year + 1, 1, start_day) - timedelta(days=1)
            else:
                end = date(start.year, start.month + 1, start_day) - timedelta(days=1)

        elif period == BudgetPeriod.QUARTERLY:
            # Quarter boundaries are the start_day of months 1, 4, 7, 10
            quarter_start_months = [1, 4, 7, 10]
            current_period = None

            for i, month in enumerate(quarter_start_months):
                try:
                    q_start = date(reference_date.year, month, start_day)
                except ValueError:
                    q_start = date(reference_date.year, month, 28)

                if i < 3:
                    next_month = quarter_start_months[i + 1]
                    try:
                        next_q_start = date(reference_date.year, next_month, start_day)
                    except ValueError:
                        next_q_start = date(reference_date.year, next_month, 28)
                else:
                    try:
                        next_q_start = date(reference_date.year + 1, 1, start_day)
                    except ValueError:
                        next_q_start = date(reference_date.year + 1, 1, 28)

                if q_start <= reference_date < next_q_start:
                    current_period = (q_start, next_q_start - timedelta(days=1))
                    break

            if current_period is None:
                # reference_date falls before Q1 start (e.g. Jan 1-14 when start_day=15)
                # → belongs to Q4 of the previous year
                try:
                    q_start = date(reference_date.year - 1, 10, start_day)
                    next_q_start = date(reference_date.year, 1, start_day)
                except ValueError:
                    q_start = date(reference_date.year - 1, 10, 28)
                    next_q_start = date(reference_date.year, 1, 28)
                current_period = (q_start, next_q_start - timedelta(days=1))

            start, end = current_period

        elif period == BudgetPeriod.SEMI_ANNUAL:
            # Half-year boundaries: start_day of months 1 and 7
            half_start_months = [1, 7]
            current_period = None

            for i, month in enumerate(half_start_months):
                try:
                    h_start = date(reference_date.year, month, start_day)
                except ValueError:
                    h_start = date(reference_date.year, month, 28)

                if i < 1:
                    next_month = half_start_months[i + 1]
                    try:
                        next_h_start = date(reference_date.year, next_month, start_day)
                    except ValueError:
                        next_h_start = date(reference_date.year, next_month, 28)
                else:
                    try:
                        next_h_start = date(reference_date.year + 1, 1, start_day)
                    except ValueError:
                        next_h_start = date(reference_date.year + 1, 1, 28)

                if h_start <= reference_date < next_h_start:
                    current_period = (h_start, next_h_start - timedelta(days=1))
                    break

            if current_period is None:
                # reference_date falls before H1 start (e.g. Jan 1-14 when start_day=15)
                # → belongs to H2 of the previous year
                try:
                    h_start = date(reference_date.year - 1, 7, start_day)
                    next_h_start = date(reference_date.year, 1, start_day)
                except ValueError:
                    h_start = date(reference_date.year - 1, 7, 28)
                    next_h_start = date(reference_date.year, 1, 28)
                current_period = (h_start, next_h_start - timedelta(days=1))

            start, end = current_period

        elif period == BudgetPeriod.YEARLY:
            # Year runs from start_day of January to one day before the following year's start
            try:
                year_start = date(reference_date.year, 1, start_day)
            except ValueError:
                year_start = date(reference_date.year, 1, 28)

            if reference_date < year_start:
                start = date(reference_date.year - 1, 1, start_day)
                end = year_start - timedelta(days=1)
            else:
                start = year_start
                try:
                    end = date(reference_date.year + 1, 1, start_day) - timedelta(days=1)
                except ValueError:
                    end = date(reference_date.year + 1, 1, 28) - timedelta(days=1)

        return start, end

    @staticmethod
    async def create_budget(
        db: AsyncSession,
        user: User,
        name: str,
        amount: Decimal,
        period: BudgetPeriod,
        start_date: date,
        category_id: Optional[UUID] = None,
        label_id: Optional[UUID] = None,
        end_date: Optional[date] = None,
        rollover_unused: bool = False,
        alert_threshold: Decimal = Decimal("0.80"),
        is_shared: bool = False,
        shared_user_ids: Optional[list] = None,
    ) -> Budget:
        """Create a new budget."""
        # Enforce unique name per owner
        existing = await db.execute(
            select(Budget.id).where(
                Budget.user_id == user.id,
                func.lower(Budget.name) == name.strip().lower(),
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a budget named '{name.strip()}'",
            )

        budget = Budget(
            organization_id=user.organization_id,
            user_id=user.id,
            name=name,
            amount=amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            label_id=label_id,
            rollover_unused=rollover_unused,
            alert_threshold=alert_threshold,
            is_shared=is_shared,
            shared_user_ids=shared_user_ids,
        )

        db.add(budget)
        await db.commit()
        await db.refresh(budget)

        return budget

    @staticmethod
    async def get_budgets(
        db: AsyncSession,
        user: User,
        is_active: Optional[bool] = None,
        user_id: Optional[UUID] = None,
    ) -> List[Budget]:
        """Get all budgets for organization."""
        query = select(Budget).where(Budget.organization_id == user.organization_id)

        if is_active is not None:
            query = query.where(Budget.is_active == is_active)

        if user_id is not None:
            query = query.where(Budget.user_id == user_id)

        query = query.order_by(Budget.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_budget(
        db: AsyncSession,
        budget_id: UUID,
        user: User,
    ) -> Optional[Budget]:
        """Get a specific budget."""
        result = await db.execute(
            select(Budget).where(
                and_(
                    Budget.id == budget_id,
                    Budget.organization_id == user.organization_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_budget(
        db: AsyncSession,
        budget_id: UUID,
        user: User,
        **kwargs,
    ) -> Optional[Budget]:
        """Update a budget."""
        budget = await BudgetService.get_budget(db, budget_id, user)
        if not budget:
            return None

        # If name is being changed, enforce uniqueness per owner
        new_name = kwargs.get("name")
        if new_name and new_name.strip().lower() != (budget.name or "").strip().lower():
            existing = await db.execute(
                select(Budget.id).where(
                    Budget.user_id == budget.user_id,
                    func.lower(Budget.name) == new_name.strip().lower(),
                    Budget.id != budget_id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You already have a budget named '{new_name.strip()}'",
                )

        for key, value in kwargs.items():
            if hasattr(budget, key):
                setattr(budget, key, value)

        budget.updated_at = utc_now()

        await db.commit()
        await db.refresh(budget)

        return budget

    @staticmethod
    async def delete_budget(
        db: AsyncSession,
        budget_id: UUID,
        user: User,
    ) -> bool:
        """Delete a budget."""
        budget = await BudgetService.get_budget(db, budget_id, user)
        if not budget:
            return False

        await db.delete(budget)
        await db.commit()

        return True

    @staticmethod
    async def get_budget_spending(
        db: AsyncSession,
        budget_id: UUID,
        user: User,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> Dict[str, Decimal]:
        """
        Calculate spending for a budget in a given period.

        Returns:
            Dict with spent, remaining, and percentage
        """
        budget = await BudgetService.get_budget(db, budget_id, user)
        if not budget:
            return {}

        # Determine period dates
        monthly_start_day = 1
        if period_start is None or period_end is None:
            org_result = await db.execute(
                select(Organization).where(Organization.id == user.organization_id)
            )
            org = org_result.scalar_one_or_none()
            monthly_start_day = org.monthly_start_day if org else 1
            period_start, period_end = BudgetService._get_period_dates(
                budget.period, monthly_start_day=monthly_start_day
            )

        # Calculate rollover from previous period
        rollover_amount = Decimal("0.00")
        if budget.rollover_unused:
            prev_end = period_start - timedelta(days=1)
            prev_start, _ = BudgetService._get_period_dates(
                budget.period,
                reference_date=prev_end,
                monthly_start_day=monthly_start_day,
            )
            prev_query = select(func.sum(Transaction.amount)).where(
                and_(
                    Transaction.organization_id == user.organization_id,
                    Transaction.date >= prev_start,
                    Transaction.date <= prev_end,
                    Transaction.amount < 0,
                )
            )
            if budget.category_id:
                prev_query = prev_query.where(Transaction.category_id == budget.category_id)
            if budget.label_id:
                prev_query = prev_query.join(
                    TransactionLabel,
                    and_(
                        TransactionLabel.transaction_id == Transaction.id,
                        TransactionLabel.label_id == budget.label_id,
                    ),
                )
            prev_result = await db.execute(prev_query)
            prev_spent = abs(prev_result.scalar() or Decimal("0.00"))
            rollover_amount = max(Decimal("0.00"), budget.amount - prev_spent)

        effective_budget = budget.amount + rollover_amount

        # Build query for transactions
        query = select(func.sum(Transaction.amount)).where(
            and_(
                Transaction.organization_id == user.organization_id,
                Transaction.date >= period_start,
                Transaction.date <= period_end,
                Transaction.amount < 0,  # Expenses only
            )
        )

        # Filter by category if budget is category-specific
        if budget.category_id:
            # Load the category and all its children so that transactions assigned
            # to a sub-category roll up into the parent budget.
            # Always scope to the user's org — defense-in-depth against IDOR.
            cat_result = await db.execute(
                select(Category).where(
                    Category.id == budget.category_id,
                    Category.organization_id == user.organization_id,
                )
            )
            category = cat_result.scalar_one_or_none()

            if category:
                children_result = await db.execute(
                    select(Category).where(
                        Category.parent_category_id == budget.category_id,
                        Category.organization_id == user.organization_id,
                    )
                )
                children = list(children_result.scalars().all())

                # All category IDs in scope: parent + children
                all_category_ids = [budget.category_id] + [c.id for c in children]

                # Names to match against category_primary for provider-categorized
                # transactions that have no category_id assigned yet.
                all_names = set()
                for cat in [category] + children:
                    all_names.add((cat.plaid_category_name or cat.name).lower())

                conditions = [Transaction.category_id.in_(all_category_ids)]
                if all_names:
                    conditions.append(func.lower(Transaction.category_primary).in_(all_names))

                query = query.where(or_(*conditions))
            else:
                query = query.where(Transaction.category_id == budget.category_id)

        # Filter by label if budget is label-specific
        if budget.label_id:
            query = query.join(
                TransactionLabel,
                and_(
                    TransactionLabel.transaction_id == Transaction.id,
                    TransactionLabel.label_id == budget.label_id,
                ),
            )

        result = await db.execute(query)
        spent = abs(result.scalar() or Decimal("0.00"))

        remaining = effective_budget - spent
        percentage = (spent / effective_budget * 100) if effective_budget > 0 else Decimal("0.00")

        return {
            "budget_amount": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "period_start": period_start,
            "period_end": period_end,
            "rollover_amount": rollover_amount,
            "effective_budget": effective_budget,
        }

    @staticmethod
    async def check_budget_alerts(
        db: AsyncSession,
        user: User,
    ) -> List[Dict]:
        """
        Check all budgets and create notifications for those exceeding alert threshold.

        Returns:
            List of budgets that triggered alerts
        """
        budgets = await BudgetService.get_budgets(db, user, is_active=True)
        alerts = []

        # Fetch org members once so we can attach a real user_id to alerts
        members_result = await db.execute(
            select(User).where(
                User.organization_id == user.organization_id,
                User.is_active.is_(True),
            )
        )
        org_members = members_result.scalars().all()
        # Prefer the org admin; fall back to any member; last resort: the caller
        alert_user = next(
            (m for m in org_members if m.is_org_admin), org_members[0] if org_members else user
        )

        for budget in budgets:
            spending = await BudgetService.get_budget_spending(db, budget.id, user)

            if not spending:
                continue

            percentage = spending["percentage"]

            # Check if over alert threshold
            if percentage >= (budget.alert_threshold * 100):
                # Deduplication: skip if an unread BUDGET_ALERT for this budget already
                # exists today for this org (prevents duplicate alerts from repeated runs)
                today_str = utc_now().date().isoformat()
                existing_result = await db.execute(
                    select(Notification.id)
                    .where(
                        and_(
                            Notification.organization_id == user.organization_id,
                            Notification.type == NotificationType.BUDGET_ALERT,
                            Notification.related_entity_id == budget.id,
                            Notification.is_read.is_(False),
                            func.date(Notification.created_at) == today_str,
                        )
                    )
                    .limit(1)
                )
                if existing_result.scalar_one_or_none() is not None:
                    continue

                # Create notification
                priority = (
                    NotificationPriority.HIGH if percentage >= 100 else NotificationPriority.MEDIUM
                )

                title = f"Budget Alert: {budget.name}"
                period_labels = {
                    "monthly": "monthly",
                    "quarterly": "quarterly",
                    "semi_annual": "6-month",
                    "yearly": "yearly",
                }
                period_label = period_labels.get(budget.period.value, budget.period.value)
                message = (
                    f"You've spent ${spending['spent']:.2f} of ${budget.amount:.2f} "
                    f"({percentage:.1f}%) in the current {period_label} period."
                )

                await NotificationService.create_notification(
                    db=db,
                    organization_id=user.organization_id,
                    user_id=alert_user.id,
                    type=NotificationType.BUDGET_ALERT,
                    title=title,
                    message=message,
                    priority=priority,
                    related_entity_type="budget",
                    related_entity_id=budget.id,
                    action_url=f"/budgets/{budget.id}",
                    action_label="View Budget",
                    expires_in_days=7,
                )

                alerts.append(
                    {
                        "budget": budget,
                        "spending": spending,
                    }
                )

        return alerts


    @staticmethod
    async def get_budget_variance_breakdown(
        db: AsyncSession,
        budget_id: UUID,
        user: User,
    ) -> Optional[dict]:
        """Return per-merchant spending breakdown for the current budget period."""
        budget = await BudgetService.get_budget(db, budget_id, user)
        if not budget:
            return None

        org_result = await db.execute(
            select(Organization).where(Organization.id == user.organization_id)
        )
        org = org_result.scalar_one_or_none()
        monthly_start_day = org.monthly_start_day if org else 1
        period_start, period_end = BudgetService._get_period_dates(
            budget.period, monthly_start_day=monthly_start_day
        )

        # Base conditions
        base_conditions = [
            Transaction.organization_id == user.organization_id,
            Transaction.date >= period_start,
            Transaction.date <= period_end,
            Transaction.amount < 0,
        ]

        # Build merchant breakdown query
        merchant_query = (
            select(
                Transaction.merchant_name,
                func.sum(Transaction.amount).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .where(and_(*base_conditions))
            .group_by(Transaction.merchant_name)
            .order_by(func.sum(Transaction.amount).asc())  # Most negative = biggest spend
            .limit(10)
        )

        if budget.category_id:
            merchant_query = merchant_query.where(Transaction.category_id == budget.category_id)
        if budget.label_id:
            merchant_query = merchant_query.join(
                TransactionLabel,
                and_(
                    TransactionLabel.transaction_id == Transaction.id,
                    TransactionLabel.label_id == budget.label_id,
                ),
            )

        merchant_result = await db.execute(merchant_query)
        merchant_rows = merchant_result.all()

        # Top 3 largest transactions
        top_query = (
            select(Transaction.id, Transaction.date, Transaction.merchant_name, Transaction.amount)
            .where(and_(*base_conditions))
            .order_by(Transaction.amount.asc())
            .limit(3)
        )
        if budget.category_id:
            top_query = top_query.where(Transaction.category_id == budget.category_id)
        if budget.label_id:
            top_query = top_query.join(
                TransactionLabel,
                and_(TransactionLabel.transaction_id == Transaction.id,
                     TransactionLabel.label_id == budget.label_id),
            )

        top_result = await db.execute(top_query)
        top_rows = top_result.all()

        total_spent_result = await db.execute(
            select(func.sum(Transaction.amount)).where(and_(*base_conditions))
        )
        total_spent = abs(total_spent_result.scalar() or Decimal("0.00"))

        return {
            "merchant_breakdown": [
                {
                    "merchant_name": row.merchant_name or "Unknown",
                    "amount": abs(float(row.total)),
                    "transaction_count": row.count,
                }
                for row in merchant_rows
            ],
            "largest_transactions": [
                {
                    "id": str(row.id),
                    "date": row.date.isoformat() if row.date else None,
                    "merchant_name": row.merchant_name or "Unknown",
                    "amount": abs(float(row.amount)),
                }
                for row in top_rows
            ],
            "total_spent": float(total_spent),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }


budget_service = BudgetService()
