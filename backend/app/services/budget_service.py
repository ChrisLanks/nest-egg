"""Service for managing budgets and tracking spending."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction, Category, TransactionLabel
from app.models.user import Organization, User
from app.models.notification import NotificationType, NotificationPriority
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
                    start = reference_date.replace(year=reference_date.year - 1, month=12, day=start_day)
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
    ) -> Budget:
        """Create a new budget."""
        budget = Budget(
            organization_id=user.organization_id,
            name=name,
            amount=amount,
            period=period,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            label_id=label_id,
            rollover_unused=rollover_unused,
            alert_threshold=alert_threshold,
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
    ) -> List[Budget]:
        """Get all budgets for organization."""
        query = select(Budget).where(Budget.organization_id == user.organization_id)

        if is_active is not None:
            query = query.where(Budget.is_active == is_active)

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
        if period_start is None or period_end is None:
            org_result = await db.execute(
                select(Organization).where(Organization.id == user.organization_id)
            )
            org = org_result.scalar_one_or_none()
            monthly_start_day = org.monthly_start_day if org else 1
            period_start, period_end = BudgetService._get_period_dates(
                budget.period, monthly_start_day=monthly_start_day
            )

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
            cat_result = await db.execute(
                select(Category).where(Category.id == budget.category_id)
            )
            category = cat_result.scalar_one_or_none()

            if category:
                children_result = await db.execute(
                    select(Category).where(Category.parent_category_id == budget.category_id)
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

        remaining = budget.amount - spent
        percentage = (spent / budget.amount * 100) if budget.amount > 0 else Decimal("0.00")

        return {
            "budget_amount": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": percentage,
            "period_start": period_start,
            "period_end": period_end,
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

        for budget in budgets:
            spending = await BudgetService.get_budget_spending(db, budget.id, user)

            if not spending:
                continue

            percentage = spending["percentage"]

            # Check if over alert threshold
            if percentage >= (budget.alert_threshold * 100):
                # Create notification
                priority = (
                    NotificationPriority.HIGH if percentage >= 100 else NotificationPriority.MEDIUM
                )

                title = f"Budget Alert: {budget.name}"
                message = (
                    f"You've spent ${spending['spent']:.2f} of ${budget.amount:.2f} "
                    f"({percentage:.1f}%) in the current {budget.period.value} period."
                )

                await NotificationService.create_notification(
                    db=db,
                    organization_id=user.organization_id,
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


budget_service = BudgetService()
