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

        # Add future private debt events (interest income and principal repayment)
        private_debt_events = await ForecastService._get_future_private_debt_events(
            db, organization_id, user_id, days_ahead
        )
        future_transactions.extend(private_debt_events)

        # Add future CD maturity events
        cd_maturity_events = await ForecastService._get_future_cd_maturity_events(
            db, organization_id, user_id, days_ahead
        )
        future_transactions.extend(cd_maturity_events)

        # Add future mortgage/loan payment events
        mortgage_events = await ForecastService._get_mortgage_payment_events(
            db, organization_id, user_id, days_ahead
        )
        future_transactions.extend(mortgage_events)

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

        # Account types that default to excluded from net worth when include_in_networth is None
        EXCLUDED_BY_DEFAULT = {
            AccountType.VEHICLE,
            AccountType.COLLECTIBLES,
            AccountType.OTHER,
            AccountType.MANUAL,
        }

        for account in accounts:
            # Check if account should be included
            include = account.include_in_networth
            if include is None:
                # Auto-determine
                if account.account_type in EXCLUDED_BY_DEFAULT:
                    include = False
                elif account.account_type == AccountType.PRIVATE_EQUITY:
                    include = bool(account.company_status and account.company_status.value == 'public')
                else:
                    include = True

            if not include:
                continue

            # Calculate account value
            # Handle Business Equity accounts
            if account.account_type == AccountType.BUSINESS_EQUITY:
                # If direct equity value is provided, use it
                if account.equity_value:
                    total += account.equity_value
                # If company valuation is provided
                elif account.company_valuation:
                    # If ownership percentage is also provided, calculate proportional value
                    if account.ownership_percentage:
                        total += (account.company_valuation * account.ownership_percentage) / Decimal(100)
                    # If no percentage provided, assume 100% ownership (use full valuation)
                    else:
                        total += account.company_valuation
                # Fallback to current_balance
                else:
                    total += account.current_balance or Decimal(0)
            # Handle Private Equity with vesting schedule
            elif account.account_type == AccountType.PRIVATE_EQUITY and account.vesting_schedule:
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
    async def _get_future_private_debt_events(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID], days_ahead: int
    ) -> List[Dict]:
        """
        Extract future cash flow events from Private Debt accounts.

        Projects:
        1. Monthly interest income (based on interest_rate and principal_amount)
        2. Principal repayment on maturity_date

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering
            days_ahead: Number of days to forecast

        Returns:
            List of future private debt events as transaction-like dictionaries
        """
        from datetime import datetime
        from app.models.account import AccountType

        # Query Private Debt accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type == AccountType.PRIVATE_DEBT,
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        debt_events = []
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        for account in accounts:
            principal_amount = account.principal_amount or Decimal(0)
            interest_rate = account.interest_rate or Decimal(0)

            # Skip if no principal amount
            if principal_amount <= 0:
                continue

            # Calculate monthly interest income (if interest rate is provided)
            if interest_rate > 0:
                # Monthly interest = principal * (annual_rate / 100) / 12
                monthly_interest = principal_amount * (interest_rate / Decimal(100)) / Decimal(12)

                # Generate monthly interest payments within forecast window
                current_month = today.replace(day=1)  # Start of current month
                if current_month < today:
                    # Move to next month if we're past the 1st
                    if current_month.month == 12:
                        current_month = current_month.replace(year=current_month.year + 1, month=1)
                    else:
                        current_month = current_month.replace(month=current_month.month + 1)

                while current_month <= end_date:
                    debt_events.append({
                        'date': current_month,
                        'amount': monthly_interest,  # Positive since it's income
                        'merchant': f"{account.name} - Interest Income",
                    })

                    # Move to next month
                    if current_month.month == 12:
                        current_month = current_month.replace(year=current_month.year + 1, month=1)
                    else:
                        current_month = current_month.replace(month=current_month.month + 1)

            # Add principal repayment on maturity date (if within forecast window)
            if account.maturity_date:
                maturity_date = account.maturity_date
                if today < maturity_date <= end_date:
                    debt_events.append({
                        'date': maturity_date,
                        'amount': principal_amount,  # Positive since you're receiving repayment
                        'merchant': f"{account.name} - Principal Repayment",
                    })

        return debt_events

    @staticmethod
    async def _get_future_cd_maturity_events(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID], days_ahead: int
    ) -> List[Dict]:
        """
        Extract future CD maturity events.

        When a CD matures, the full value (principal + accrued interest) becomes liquid.
        Projects the maturity value based on interest rate and compounding frequency.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering
            days_ahead: Number of days to forecast

        Returns:
            List of future CD maturity events as transaction-like dictionaries
        """
        from datetime import datetime
        from app.models.account import AccountType
        from decimal import Decimal as D
        from math import pow

        # Query CD accounts
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type == AccountType.CD,
            Account.maturity_date.isnot(None),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        cd_events = []
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        for account in accounts:
            maturity_date = account.maturity_date
            if not maturity_date or not (today < maturity_date <= end_date):
                continue

            # Calculate maturity value
            principal = account.original_amount or account.current_balance or D(0)
            if principal <= 0:
                continue

            interest_rate = account.interest_rate or D(0)

            # If no interest rate or compounding, use current balance
            if interest_rate == 0 or not account.compounding_frequency:
                maturity_value = principal
            else:
                # Calculate accrued interest based on compounding frequency
                origination_date = account.origination_date or today
                days_held = (maturity_date - origination_date).days
                years_held = D(days_held) / D(365)

                rate_decimal = interest_rate / D(100)

                # Determine compounding periods per year
                if account.compounding_frequency.value == 'daily':
                    n = D(365)
                elif account.compounding_frequency.value == 'monthly':
                    n = D(12)
                elif account.compounding_frequency.value == 'quarterly':
                    n = D(4)
                else:  # at_maturity (simple interest)
                    maturity_value = principal * (D(1) + rate_decimal * years_held)
                    cd_events.append({
                        'date': maturity_date,
                        'amount': maturity_value,
                        'merchant': f"{account.name} - CD Maturity",
                    })
                    continue

                # Compound interest formula: A = P(1 + r/n)^(nt)
                try:
                    compounding_factor = float((D(1) + rate_decimal / n) ** (n * years_held))
                    maturity_value = principal * D(str(compounding_factor))
                except (ValueError, OverflowError):
                    # Fallback to simple interest if calculation fails
                    maturity_value = principal * (D(1) + rate_decimal * years_held)

            cd_events.append({
                'date': maturity_date,
                'amount': maturity_value,
                'merchant': f"{account.name} - CD Maturity",
            })

        return cd_events

    @staticmethod
    async def _get_mortgage_payment_events(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID], days_ahead: int
    ) -> List[Dict]:
        """
        Calculate monthly mortgage/loan payments and project as cash outflows.

        Uses standard amortization formula: M = P[r(1+r)^n] / [(1+r)^n - 1]
        where P = current balance, r = monthly rate, n = remaining months.

        Only runs for accounts with interest_rate set and exclude_from_cash_flow = False.
        """
        import calendar
        from app.models.account import AccountType

        loan_types = [AccountType.MORTGAGE, AccountType.LOAN, AccountType.STUDENT_LOAN]

        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type.in_(loan_types),
            Account.interest_rate.isnot(None),
            Account.interest_rate > 0,
            Account.exclude_from_cash_flow.is_(False),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))
        accounts = result.scalars().all()

        payment_events = []
        today = date.today()
        end_date = today + timedelta(days=days_ahead)

        for account in accounts:
            balance = account.current_balance or Decimal(0)
            if balance <= 0:
                continue

            monthly_rate = account.interest_rate / Decimal(100) / Decimal(12)

            # Determine remaining months
            if account.loan_term_months and account.origination_date:
                months_elapsed = (
                    (today.year - account.origination_date.year) * 12
                    + (today.month - account.origination_date.month)
                )
                remaining_months = max(1, account.loan_term_months - months_elapsed)
            elif account.maturity_date:
                remaining_months = max(
                    1,
                    (account.maturity_date.year - today.year) * 12
                    + (account.maturity_date.month - today.month),
                )
            elif account.loan_term_months:
                remaining_months = account.loan_term_months
            else:
                # No term data — use conservative defaults
                remaining_months = 360 if account.account_type == AccountType.MORTGAGE else 120

            # Amortization formula: M = P * r(1+r)^n / [(1+r)^n - 1]
            factor = (Decimal(1) + monthly_rate) ** remaining_months
            monthly_payment = balance * (monthly_rate * factor) / (factor - Decimal(1))

            payment_day = account.payment_due_day or 1

            # Generate one payment per month within the forecast window
            current_month = today.replace(day=1)
            while current_month <= end_date:
                last_day = calendar.monthrange(current_month.year, current_month.month)[1]
                pay_day = min(payment_day, last_day)
                payment_date = current_month.replace(day=pay_day)

                if today <= payment_date <= end_date:
                    payment_events.append(
                        {
                            "date": payment_date,
                            "amount": -monthly_payment,  # Negative = cash outflow
                            "merchant": f"{account.name} - Loan Payment",
                        }
                    )

                # Advance to next month
                if current_month.month == 12:
                    current_month = current_month.replace(year=current_month.year + 1, month=1)
                else:
                    current_month = current_month.replace(month=current_month.month + 1)

        return payment_events

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
