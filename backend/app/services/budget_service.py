"""Service for managing budgets and tracking spending."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction
from app.models.user import User
from app.models.notification import NotificationType, NotificationPriority
from app.services.notification_service import NotificationService
from app.utils.datetime_utils import utc_now


class BudgetService:
    """Service for creating and managing budgets."""

    @staticmethod
    def _get_period_dates(
        period: BudgetPeriod,
        reference_date: date = None,
    ) -> tuple[date, date]:
        """Get start and end dates for a budget period."""
        if reference_date is None:
            reference_date = date.today()

        if period == BudgetPeriod.MONTHLY:
            start = reference_date.replace(day=1)
            # Get last day of month
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)

        elif period == BudgetPeriod.QUARTERLY:
            # Get quarter (1-4)
            quarter = (reference_date.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start = reference_date.replace(month=start_month, day=1)

            # End of quarter
            end_month = start_month + 2
            if end_month > 12:
                end = start.replace(year=start.year + 1, month=end_month - 12, day=1)
            else:
                end = start.replace(month=end_month, day=1)

            # Get last day
            if end.month == 12:
                end = end.replace(year=end.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = end.replace(month=end.month + 1, day=1) - timedelta(days=1)

        elif period == BudgetPeriod.YEARLY:
            start = reference_date.replace(month=1, day=1)
            end = reference_date.replace(month=12, day=31)

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
            period_start, period_end = BudgetService._get_period_dates(budget.period)

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
            query = query.where(Transaction.category_id == budget.category_id)

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
