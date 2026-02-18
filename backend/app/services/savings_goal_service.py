"""Service for managing savings goals."""

from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.savings_goal import SavingsGoal
from app.models.account import Account
from app.models.user import User
from app.utils.datetime_utils import utc_now


class SavingsGoalService:
    """Service for creating and managing savings goals."""

    @staticmethod
    async def create_goal(
        db: AsyncSession,
        user: User,
        name: str,
        target_amount: Decimal,
        start_date: date,
        description: Optional[str] = None,
        target_date: Optional[date] = None,
        account_id: Optional[UUID] = None,
        current_amount: Decimal = Decimal("0.00"),
    ) -> SavingsGoal:
        """Create a new savings goal."""
        goal = SavingsGoal(
            organization_id=user.organization_id,
            name=name,
            description=description,
            target_amount=target_amount,
            current_amount=current_amount,
            start_date=start_date,
            target_date=target_date,
            account_id=account_id,
        )

        db.add(goal)
        await db.commit()
        await db.refresh(goal)

        return goal

    @staticmethod
    async def get_goals(
        db: AsyncSession,
        user: User,
        is_completed: Optional[bool] = None,
    ) -> List[SavingsGoal]:
        """Get all savings goals for organization."""
        query = select(SavingsGoal).where(SavingsGoal.organization_id == user.organization_id)

        if is_completed is not None:
            query = query.where(SavingsGoal.is_completed == is_completed)

        query = query.order_by(SavingsGoal.target_date.asc().nullslast())

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_goal(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
    ) -> Optional[SavingsGoal]:
        """Get a specific savings goal."""
        result = await db.execute(
            select(SavingsGoal).where(
                and_(
                    SavingsGoal.id == goal_id,
                    SavingsGoal.organization_id == user.organization_id,
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_goal(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
        **kwargs,
    ) -> Optional[SavingsGoal]:
        """Update a savings goal."""
        goal = await SavingsGoalService.get_goal(db, goal_id, user)
        if not goal:
            return None

        # Track if amount changed to check for completion
        goal.current_amount

        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)

        # Auto-mark as completed if target reached
        if goal.current_amount >= goal.target_amount and not goal.is_completed:
            goal.is_completed = True
            goal.completed_at = utc_now()

        # Unmark completion if amount drops below target
        if goal.current_amount < goal.target_amount and goal.is_completed:
            goal.is_completed = False
            goal.completed_at = None

        goal.updated_at = utc_now()

        await db.commit()
        await db.refresh(goal)

        return goal

    @staticmethod
    async def delete_goal(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
    ) -> bool:
        """Delete a savings goal."""
        goal = await SavingsGoalService.get_goal(db, goal_id, user)
        if not goal:
            return False

        await db.delete(goal)
        await db.commit()

        return True

    @staticmethod
    async def sync_goal_from_account(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
    ) -> Optional[SavingsGoal]:
        """
        Sync goal's current_amount from linked account balance.

        Returns:
            Updated goal or None if not found or no account linked
        """
        goal = await SavingsGoalService.get_goal(db, goal_id, user)
        if not goal or not goal.account_id:
            return None

        # Get account balance
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.id == goal.account_id,
                    Account.organization_id == user.organization_id,
                )
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            return None

        # Update current amount
        goal.current_amount = account.current_balance

        # Check for completion
        if goal.current_amount >= goal.target_amount and not goal.is_completed:
            goal.is_completed = True
            goal.completed_at = utc_now()

        goal.updated_at = utc_now()

        await db.commit()
        await db.refresh(goal)

        return goal

    @staticmethod
    async def get_goal_progress(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
    ) -> Optional[Dict]:
        """
        Calculate progress metrics for a goal.

        Returns:
            Dict with progress percentage, remaining amount, days remaining, etc.
        """
        goal = await SavingsGoalService.get_goal(db, goal_id, user)
        if not goal:
            return None

        # Calculate progress percentage
        progress_pct = (
            (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        )

        # Calculate remaining amount
        remaining = goal.target_amount - goal.current_amount

        # Calculate days elapsed and remaining
        days_elapsed = (date.today() - goal.start_date).days
        days_remaining = (goal.target_date - date.today()).days if goal.target_date else None

        # Calculate required monthly savings
        monthly_required = None
        if goal.target_date and days_remaining and days_remaining > 0:
            months_remaining = days_remaining / 30.44  # Average days per month
            if months_remaining > 0:
                monthly_required = remaining / Decimal(str(months_remaining))

        # On track calculation
        on_track = None
        if goal.target_date and days_elapsed > 0:
            total_days = (goal.target_date - goal.start_date).days
            expected_progress = (days_elapsed / total_days) * 100
            actual_progress = float(progress_pct)
            on_track = actual_progress >= expected_progress * 0.9  # Within 10%

        return {
            "goal_id": goal.id,
            "name": goal.name,
            "current_amount": goal.current_amount,
            "target_amount": goal.target_amount,
            "progress_percentage": float(progress_pct),
            "remaining_amount": remaining,
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "monthly_required": monthly_required,
            "on_track": on_track,
            "is_completed": goal.is_completed,
        }


savings_goal_service = SavingsGoalService()
