"""Service for cash flow forecasting."""

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from uuid import UUID

from app.models.user import User
from app.models.account import Account
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency
from app.services.recurring_detection_service import RecurringDetectionService
from app.services.notification_service import NotificationService
from app.models.notification import NotificationType, NotificationPriority


class ForecastService:
    """Service for forecasting future cash flow."""

    @staticmethod
    async def generate_forecast(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        days_ahead: int = 90,
    ) -> List[Dict]:
        """
        Generate daily cash flow forecast.

        Uses recurring transactions to project future balance.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering
            days_ahead: Number of days to forecast

        Returns:
            List of daily forecast data points
        """
        # Get current account balances (exclude cash flow exclusions)
        current_balance = await ForecastService._get_total_balance(db, organization_id, user_id)

        # Get recurring transactions
        user = User(organization_id=organization_id)
        recurring = await RecurringDetectionService.get_recurring_transactions(
            db, user, is_active=True
        )

        # Filter by user_id if provided
        if user_id:
            # Need to join with accounts to filter by user
            user_accounts_result = await db.execute(
                select(Account.id).where(
                    and_(Account.organization_id == organization_id, Account.user_id == user_id)
                )
            )
            user_account_ids = [row[0] for row in user_accounts_result.all()]
            recurring = [r for r in recurring if r.account_id in user_account_ids]

        # Project future occurrences from recurring transactions
        future_transactions = []
        for pattern in recurring:
            occurrences = ForecastService._calculate_future_occurrences(pattern, days_ahead)
            future_transactions.extend(occurrences)

        # Add future vesting events for private equity accounts
        vesting_events = await ForecastService._get_future_vesting_events(
            db, organization_id, user_id, days_ahead
        )
        future_transactions.extend(vesting_events)

        # Calculate daily running balance
        forecast = []
        running_balance = current_balance

        start_date = date.today()
        for day_offset in range(days_ahead + 1):  # Include today
            forecast_date = start_date + timedelta(days=day_offset)

            # Sum transactions for this day
            day_transactions = [t for t in future_transactions if t["date"] == forecast_date]
            day_change = sum(t["amount"] for t in day_transactions)
            running_balance += day_change

            forecast.append(
                {
                    "date": forecast_date.isoformat(),
                    "projected_balance": float(running_balance),
                    "day_change": float(day_change),
                    "transaction_count": len(day_transactions),
                }
            )

        return forecast

    @staticmethod
    async def _get_total_balance(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> Decimal:
        """
        Get total current balance across all accounts.

        Excludes accounts with exclude_from_cash_flow = True.
        For Private Equity accounts, calculates vested value based on vesting schedule.
        Respects include_in_networth flag.
        """
        import json
        from datetime import datetime
        from app.models.account import AccountType

        # Query all accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.exclude_from_cash_flow.is_(False),
            Account.is_active.is_(True),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        total = Decimal(0)
        today = date.today()

        for account in accounts:
            # Check if account should be included
            include = account.include_in_networth
            if include is None:
                # Auto-determine
                if account.account_type == AccountType.PRIVATE_EQUITY:
                    include = account.company_status and account.company_status.value == 'public'
                else:
                    include = True

            if not include:
                continue

            # Calculate account value
            if account.account_type == AccountType.PRIVATE_EQUITY and account.vesting_schedule:
                # Calculate vested value
                try:
                    milestones = json.loads(account.vesting_schedule)
                    if isinstance(milestones, list):
                        vested_quantity = Decimal(0)
                        for milestone in milestones:
                            vest_date_str = milestone.get('date')
                            quantity = milestone.get('quantity', 0)
                            if vest_date_str:
                                try:
                                    vest_date = datetime.strptime(vest_date_str, '%Y-%m-%d').date()
                                    if vest_date <= today:
                                        vested_quantity += Decimal(str(quantity))
                                except (ValueError, TypeError):
                                    continue

                        share_price = account.share_price or Decimal(0)
                        total += vested_quantity * share_price
                    else:
                        total += account.current_balance or Decimal(0)
                except (json.JSONDecodeError, TypeError):
                    total += account.current_balance or Decimal(0)
            else:
                # Regular account
                balance = account.current_balance or Decimal(0)
                # Handle debt accounts (negative contribution)
                if account.account_type.is_debt:
                    total -= abs(balance)
                else:
                    total += balance

        return total

    @staticmethod
    def _calculate_future_occurrences(pattern: RecurringTransaction, days_ahead: int) -> List[Dict]:
        """
        Generate future transaction occurrences based on frequency.

        Args:
            pattern: Recurring transaction pattern
            days_ahead: Number of days to project

        Returns:
            List of projected transactions
        """
        occurrences = []
        current_date = pattern.next_expected_date or date.today()
        end_date = date.today() + timedelta(days=days_ahead)

        # Frequency to days mapping
        frequency_days = {
            RecurringFrequency.WEEKLY: 7,
            RecurringFrequency.BIWEEKLY: 14,
            RecurringFrequency.MONTHLY: 30,
            RecurringFrequency.QUARTERLY: 90,
            RecurringFrequency.YEARLY: 365,
        }

        interval_days = frequency_days.get(pattern.frequency, 30)

        # Generate occurrences until end_date
        while current_date <= end_date:
            occurrences.append(
                {
                    "date": current_date,
                    "amount": pattern.average_amount,
                    "merchant": pattern.merchant_name,
                }
            )
            current_date += timedelta(days=interval_days)

        return occurrences

    @staticmethod
    async def _get_future_vesting_events(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID], days_ahead: int
    ) -> List[Dict]:
        """
        Extract future vesting events from Private Equity accounts.

        Only includes vesting events for accounts with include_in_networth = True
        (or None with company_status = public).

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering
            days_ahead: Number of days to forecast

        Returns:
            List of future vesting events as transaction-like dictionaries
        """
        import json
        from datetime import datetime
        from app.models.account import AccountType

        # Query Private Equity accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type == AccountType.PRIVATE_EQUITY,
            Account.vesting_schedule.isnot(None),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        vesting_events = []
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        for account in accounts:
            # Check if account should be included in cash flow
            include = account.include_in_networth
            if include is None:
                # Auto-determine: include if public
                include = account.company_status and account.company_status.value == 'public'

            if not include:
                continue

            # Parse vesting schedule
            try:
                milestones = json.loads(account.vesting_schedule)
                if not isinstance(milestones, list):
                    continue

                share_price = account.share_price or Decimal(0)
                if share_price == 0:
                    continue  # Can't calculate value without share price

                for milestone in milestones:
                    vest_date_str = milestone.get('date')
                    quantity = milestone.get('quantity', 0)

                    if not vest_date_str or not quantity:
                        continue

                    try:
                        vest_date = datetime.strptime(vest_date_str, '%Y-%m-%d').date()

                        # Only include future vesting events within forecast window
                        if today < vest_date <= end_date:
                            vest_value = Decimal(str(quantity)) * share_price

                            vesting_events.append({
                                'date': vest_date,
                                'amount': vest_value,  # Positive since it's an asset increase
                                'merchant': f"{account.name} - Vesting",
                            })

                    except (ValueError, TypeError):
                        continue

            except (json.JSONDecodeError, TypeError):
                continue

        return vesting_events

    @staticmethod
    async def check_negative_balance_alert(
        db: AsyncSession,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Dict]:
        """
        Check if forecast shows negative balance, create alert if so.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering

        Returns:
            Day with negative balance if found, None otherwise
        """
        # Generate 30-day forecast
        forecast = await ForecastService.generate_forecast(
            db, organization_id, user_id, days_ahead=30
        )

        # Check for negative balance
        for day in forecast:
            if day["projected_balance"] < 0:
                # Create high-priority notification
                await NotificationService.create_notification(
                    db=db,
                    organization_id=organization_id,
                    user_id=user_id,
                    type=NotificationType.LARGE_TRANSACTION,
                    title="⚠️ Cash Flow Alert",
                    message=f"Your balance is projected to go negative on {day['date']} (${day['projected_balance']:.2f})",
                    priority=NotificationPriority.HIGH,
                    expires_in_days=7,
                )

                await db.commit()
                return day

        return None
