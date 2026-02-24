"""Service for managing savings goals."""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType
from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
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
        auto_sync: bool = False,
        is_shared: bool = False,
        shared_user_ids: Optional[list] = None,
    ) -> SavingsGoal:
        """Create a new savings goal, assigning it the lowest priority."""
        # Assign priority = number of existing active goals + 1
        count_result = await db.execute(
            select(func.count(SavingsGoal.id)).where(
                and_(
                    SavingsGoal.organization_id == user.organization_id,
                    SavingsGoal.is_completed == False,  # noqa: E712
                    SavingsGoal.is_funded == False,  # noqa: E712
                )
            )
        )
        active_count = count_result.scalar() or 0
        priority = active_count + 1

        goal = SavingsGoal(
            organization_id=user.organization_id,
            name=name,
            description=description,
            target_amount=target_amount,
            current_amount=current_amount,
            start_date=start_date,
            target_date=target_date,
            account_id=account_id,
            auto_sync=auto_sync,
            priority=priority,
            is_shared=is_shared,
            shared_user_ids=shared_user_ids,
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
        """Get all savings goals for organization, ordered by priority."""
        query = select(SavingsGoal).where(SavingsGoal.organization_id == user.organization_id)

        if is_completed is not None:
            if is_completed:
                # Completed = reached target OR funded
                query = query.where(
                    or_(SavingsGoal.is_completed == True, SavingsGoal.is_funded == True)  # noqa: E712
                )
            else:
                # Active = not completed AND not funded
                query = query.where(
                    and_(
                        SavingsGoal.is_completed == False,  # noqa: E712
                        SavingsGoal.is_funded == False,  # noqa: E712
                    )
                )

        query = query.order_by(SavingsGoal.priority.asc().nullslast(), SavingsGoal.target_date.asc().nullslast())

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

        for key, value in kwargs.items():
            if hasattr(goal, key):
                setattr(goal, key, value)

        # If account_id is cleared, disable auto_sync
        if goal.account_id is None:
            goal.auto_sync = False

        # Sync completed_at when is_completed is explicitly changed
        if "is_completed" in kwargs:
            if goal.is_completed and goal.completed_at is None:
                goal.completed_at = utc_now()
            elif not goal.is_completed:
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

        goal.current_amount = account.current_balance
        goal.updated_at = utc_now()

        await db.commit()
        await db.refresh(goal)

        return goal

    @staticmethod
    async def fund_goal(
        db: AsyncSession,
        goal_id: UUID,
        user: User,
        method: str = "waterfall",
    ) -> Optional[SavingsGoal]:
        """
        Mark a goal as funded (money has been spent on the goal).

        After funding, auto-sync remaining goals so their allocations are updated.
        """
        goal = await SavingsGoalService.get_goal(db, goal_id, user)
        if not goal:
            return None

        goal.is_funded = True
        goal.funded_at = utc_now()
        goal.updated_at = utc_now()

        await db.commit()
        await db.refresh(goal)

        # Recalculate remaining auto-sync goals now that this one is excluded
        await SavingsGoalService.auto_sync_goals(db, user, method)

        return goal

    @staticmethod
    async def auto_sync_goals(
        db: AsyncSession,
        user: User,
        method: str = "waterfall",
    ) -> List[SavingsGoal]:
        """
        Sync all active auto-sync goals from their linked accounts.

        When multiple goals share an account, balance is allocated according to method:
        - waterfall: goals in priority order each claim up to their target
        - proportional: balance split proportionally by target amounts
        """
        # Get all active auto-sync goals with an account linked, ordered by priority
        result = await db.execute(
            select(SavingsGoal).where(
                and_(
                    SavingsGoal.organization_id == user.organization_id,
                    SavingsGoal.is_completed == False,  # noqa: E712
                    SavingsGoal.is_funded == False,  # noqa: E712
                    SavingsGoal.auto_sync == True,  # noqa: E712
                    SavingsGoal.account_id.is_not(None),
                )
            ).order_by(SavingsGoal.priority.asc().nullslast())
        )
        goals = list(result.scalars().all())

        if not goals:
            return []

        # Collect unique account IDs and fetch balances in one query
        account_ids = list({g.account_id for g in goals})
        acc_result = await db.execute(
            select(Account).where(
                and_(
                    Account.id.in_(account_ids),
                    Account.organization_id == user.organization_id,
                )
            )
        )
        accounts = {acc.id: acc for acc in acc_result.scalars().all()}

        # Group goals by account_id (preserving priority order)
        goals_by_account: Dict[UUID, List[SavingsGoal]] = defaultdict(list)
        for goal in goals:
            goals_by_account[goal.account_id].append(goal)

        # Allocate balance per account
        updated_goals: List[SavingsGoal] = []
        for account_id, account_goals in goals_by_account.items():
            account = accounts.get(account_id)
            if not account:
                continue

            balance = account.current_balance

            if method == "waterfall":
                remaining = balance
                for goal in account_goals:  # already sorted by priority
                    allocated = min(remaining, goal.target_amount)
                    goal.current_amount = max(Decimal("0"), allocated)
                    remaining = max(Decimal("0"), remaining - allocated)
                    updated_goals.append(goal)
            else:  # proportional
                total_target = sum(g.target_amount for g in account_goals)
                for goal in account_goals:
                    if total_target > 0:
                        share = goal.target_amount / total_target
                        allocated = min(balance * share, goal.target_amount)
                    else:
                        allocated = Decimal("0")
                    goal.current_amount = max(Decimal("0"), allocated)
                    updated_goals.append(goal)

        now = utc_now()
        for goal in updated_goals:
            goal.updated_at = now

        await db.commit()
        for goal in updated_goals:
            await db.refresh(goal)

        return updated_goals

    @staticmethod
    async def reorder_goals(
        db: AsyncSession,
        user: User,
        goal_ids: List[UUID],
    ) -> bool:
        """
        Update priority for goals based on the provided order.

        goal_ids is the desired order (first = highest priority = 1).
        Only goals belonging to the org are updated.
        """
        if not goal_ids:
            return True

        # Fetch all matching goals in one query
        result = await db.execute(
            select(SavingsGoal).where(
                and_(
                    SavingsGoal.id.in_(goal_ids),
                    SavingsGoal.organization_id == user.organization_id,
                )
            )
        )
        goals = {g.id: g for g in result.scalars().all()}

        now = utc_now()
        for position, goal_id in enumerate(goal_ids, start=1):
            goal = goals.get(goal_id)
            if goal:
                goal.priority = position
                goal.updated_at = now

        await db.commit()
        return True

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

    @staticmethod
    async def create_emergency_fund_goal(
        db: AsyncSession,
        user: User,
    ) -> SavingsGoal:
        """
        Create an Emergency Fund goal pre-configured from spending history.

        Target = average monthly expenses (last 6 months) × 6.
        Auto-links to the liquid account (checking/savings) with the highest balance
        and enables auto_sync if one is found.
        """
        # --- Calculate average monthly expenses over last 6 months ---
        six_months_ago = date.today() - timedelta(days=182)

        # Negative amounts = expenses (per transaction model convention)
        expense_result = await db.execute(
            select(func.sum(Transaction.amount)).where(
                and_(
                    Transaction.organization_id == user.organization_id,
                    Transaction.amount < 0,
                    Transaction.date >= six_months_ago,
                )
            )
        )
        total_expenses = expense_result.scalar() or Decimal("0")
        avg_monthly_expenses = abs(total_expenses) / 6  # always positive

        # Default to $3,000/month if no transaction history
        if avg_monthly_expenses < Decimal("1"):
            avg_monthly_expenses = Decimal("3000")

        target = (avg_monthly_expenses * 6).quantize(Decimal("0.01"))

        # --- Find best liquid account to link ---
        liquid_result = await db.execute(
            select(Account).where(
                and_(
                    Account.organization_id == user.organization_id,
                    Account.account_type.in_([AccountType.CHECKING, AccountType.SAVINGS]),
                    Account.is_active == True,  # noqa: E712
                )
            ).order_by(Account.current_balance.desc())
        )
        liquid_account = liquid_result.scalars().first()

        description = (
            f"6 months of expenses (~${avg_monthly_expenses:,.0f}/month average)"
        )

        return await SavingsGoalService.create_goal(
            db=db,
            user=user,
            name="Emergency Fund",
            description=description,
            target_amount=target,
            start_date=date.today(),
            account_id=liquid_account.id if liquid_account else None,
            auto_sync=bool(liquid_account),
            current_amount=Decimal(liquid_account.current_balance) if liquid_account else Decimal("0"),
        )


savings_goal_service = SavingsGoalService()
