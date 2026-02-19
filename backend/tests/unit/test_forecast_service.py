"""Unit tests for forecast service."""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from app.services.forecast_service import ForecastService
from app.models.recurring_transaction import RecurringTransaction, RecurringFrequency


@pytest.mark.unit
class TestForecastService:
    """Test cash flow forecast service."""

    def test_calculate_future_occurrences_weekly(self):
        """Test weekly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Grocery Store",
            average_amount=Decimal("-100.00"),
            frequency=RecurringFrequency.WEEKLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern, days_ahead=21  # 3 weeks
        )

        # Should have 4 occurrences (weekly for 3 weeks, inclusive)
        assert len(occurrences) == 4
        assert all(occ["amount"] == Decimal("-100.00") for occ in occurrences)

    def test_calculate_future_occurrences_monthly(self):
        """Test monthly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Rent",
            average_amount=Decimal("-2000.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern, days_ahead=90  # ~3 months
        )

        # Should have 4 occurrences (monthly recurring within 90 days, inclusive)
        assert len(occurrences) == 4
        assert all(occ["amount"] == Decimal("-2000.00") for occ in occurrences)
        assert all(occ["merchant"] == "Rent" for occ in occurrences)

    def test_calculate_future_occurrences_biweekly(self):
        """Test biweekly recurring transaction projection."""
        pattern = RecurringTransaction(
            merchant_name="Paycheck",
            average_amount=Decimal("3000.00"),
            frequency=RecurringFrequency.BIWEEKLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern, days_ahead=56  # 4 biweekly periods
        )

        # Should have 5 occurrences (biweekly for 56 days, inclusive)
        assert len(occurrences) == 5
        assert all(occ["amount"] == Decimal("3000.00") for occ in occurrences)

    def test_calculate_future_occurrences_stops_at_end_date(self):
        """Test that projections stop at specified end date."""
        pattern = RecurringTransaction(
            merchant_name="Monthly Bill",
            average_amount=Decimal("-50.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(
            pattern, days_ahead=45  # 1.5 months
        )

        # Should have 2 occurrences (monthly within 45 days, inclusive)
        assert len(occurrences) == 2

    def test_negative_balance_detection(self):
        """Test detection of projected negative balance."""
        forecast_data = [
            {"date": date.today(), "projected_balance": 500.0},
            {"date": date.today() + timedelta(days=5), "projected_balance": -100.0},
            {"date": date.today() + timedelta(days=10), "projected_balance": 200.0},
        ]

        # Find first negative balance
        negative_day = next((day for day in forecast_data if day["projected_balance"] < 0), None)

        assert negative_day is not None
        assert negative_day["projected_balance"] == -100.0

    def test_running_balance_calculation(self):
        """Test running balance calculation over time."""
        starting_balance = Decimal("1000.00")
        transactions = [
            {"date": date.today(), "amount": Decimal("-100.00")},
            {"date": date.today() + timedelta(days=1), "amount": Decimal("500.00")},
            {"date": date.today() + timedelta(days=2), "amount": Decimal("-200.00")},
        ]

        # Calculate running balance
        balance = starting_balance
        balances = []

        for txn in transactions:
            balance += txn["amount"]
            balances.append(balance)

        assert balances[0] == Decimal("900.00")  # 1000 - 100
        assert balances[1] == Decimal("1400.00")  # 900 + 500
        assert balances[2] == Decimal("1200.00")  # 1400 - 200


@pytest.mark.unit
@pytest.mark.asyncio
class TestPrivateDebtProjections:
    """Test Private Debt cash flow projections."""

    async def test_monthly_interest_income_calculation(self):
        """Test monthly interest income is calculated correctly."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # Create mock account with 6% annual interest on $10,000 principal
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Loan to Friend",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("10000.00"),
            interest_rate=Decimal("6.00"),  # 6% annual
            maturity_date=date.today() + timedelta(days=365),
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=90
        )

        # Monthly interest = 10,000 * (6 / 100) / 12 = $50.00
        expected_monthly_interest = Decimal("50.00")

        # Should have ~3 monthly interest payments
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]
        assert len(interest_events) >= 3
        assert all(e["amount"] == expected_monthly_interest for e in interest_events)

    async def test_principal_repayment_on_maturity(self):
        """Test principal repayment event on maturity date."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        maturity_date = date.today() + timedelta(days=60)

        # Create mock account
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Private Loan",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("25000.00"),
            interest_rate=Decimal("5.00"),
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=90
        )

        # Find principal repayment event
        principal_events = [e for e in events if "Principal Repayment" in e["merchant"]]
        assert len(principal_events) == 1
        assert principal_events[0]["amount"] == Decimal("25000.00")
        assert principal_events[0]["date"] == maturity_date

    async def test_no_interest_rate_only_principal(self):
        """Test projection with no interest rate (only principal repayment)."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        maturity_date = date.today() + timedelta(days=30)

        # Create account with no interest rate
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Zero Interest Loan",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("5000.00"),
            interest_rate=None,  # No interest
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should only have principal repayment, no interest events
        assert len(events) == 1
        assert "Principal Repayment" in events[0]["merchant"]
        assert events[0]["amount"] == Decimal("5000.00")

    async def test_maturity_outside_forecast_window(self):
        """Test that maturity date outside window is not included."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # Maturity date beyond forecast window
        maturity_date = date.today() + timedelta(days=180)

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Long-term Loan",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("10000.00"),
            interest_rate=Decimal("4.00"),
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events for 90 days
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have interest payments but no principal repayment
        principal_events = [e for e in events if "Principal Repayment" in e["merchant"]]
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]

        assert len(principal_events) == 0  # Maturity outside window
        assert len(interest_events) >= 3  # Still get interest payments

    async def test_skip_zero_principal_accounts(self):
        """Test that accounts with zero principal are skipped."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Empty Loan",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("0.00"),  # No principal
            interest_rate=Decimal("5.00"),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have no events
        assert len(events) == 0

    async def test_multiple_private_debt_accounts(self):
        """Test projection with multiple private debt accounts."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        org_id = uuid4()
        user_id = uuid4()

        # Create two accounts
        account1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user_id,
            name="Loan A",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            maturity_date=date.today() + timedelta(days=60),
            is_active=True,
        )

        account2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user_id,
            name="Loan B",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("15000.00"),
            interest_rate=Decimal("6.00"),
            maturity_date=date.today() + timedelta(days=90),
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account1, account2]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, org_id, user_id, days_ahead=90
        )

        # Should have events from both accounts
        loan_a_events = [e for e in events if "Loan A" in e["merchant"]]
        loan_b_events = [e for e in events if "Loan B" in e["merchant"]]

        assert len(loan_a_events) > 0
        assert len(loan_b_events) > 0

        # Check interest amounts
        loan_a_interest = [e for e in loan_a_events if "Interest" in e["merchant"]]
        loan_b_interest = [e for e in loan_b_events if "Interest" in e["merchant"]]

        # Loan A: 10,000 * 5% / 12 = $41.67
        assert all(abs(e["amount"] - Decimal("41.67")) < Decimal("0.01") for e in loan_a_interest)

        # Loan B: 15,000 * 6% / 12 = $75.00
        assert all(e["amount"] == Decimal("75.00") for e in loan_b_interest)

    async def test_year_rollover_for_interest_payments(self):
        """Test that interest payments handle year rollover correctly."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # Create account
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Year-End Loan",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("12000.00"),
            interest_rate=Decimal("5.00"),
            maturity_date=date.today() + timedelta(days=365),
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_private_debt_events(
            db, uuid4(), None, days_ahead=120  # 4 months
        )

        # Should have interest events spanning months
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]
        assert len(interest_events) >= 4

        # Check that dates are in chronological order
        dates = [e["date"] for e in interest_events]
        assert dates == sorted(dates)


@pytest.mark.unit
@pytest.mark.asyncio
class TestCDMaturityProjections:
    """Test CD maturity cash flow projections."""

    async def test_cd_maturity_with_simple_interest(self):
        """Test CD maturity with simple interest (at_maturity compounding)."""
        from app.models.account import Account, AccountType, CompoundingFrequency
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        maturity_date = date.today() + timedelta(days=365)
        origination_date = date.today() - timedelta(days=365)

        # $10,000 CD at 5% APY for 2 years (simple interest)
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="2-Year CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.AT_MATURITY,
            origination_date=origination_date,
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_cd_maturity_events(
            db, uuid4(), None, days_ahead=400
        )

        # Should have 1 maturity event
        assert len(events) == 1
        assert events[0]["date"] == maturity_date
        assert "CD Maturity" in events[0]["merchant"]

        # Simple interest: 10,000 * (1 + 0.05 * 2) = 11,000
        expected_value = Decimal("11000.00")
        assert abs(events[0]["amount"] - expected_value) < Decimal("1.00")

    async def test_cd_maturity_with_monthly_compounding(self):
        """Test CD maturity with monthly compounding."""
        from app.models.account import Account, AccountType, CompoundingFrequency
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        maturity_date = date.today() + timedelta(days=60)
        origination_date = date.today() - timedelta(days=305)  # ~10 months ago

        # $10,000 CD at 5% APY, monthly compounding, for 1 year
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="1-Year CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.MONTHLY,
            origination_date=origination_date,
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_cd_maturity_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have 1 maturity event
        assert len(events) == 1
        assert events[0]["date"] == maturity_date

        # Monthly compounding: 10,000 * (1 + 0.05/12)^12 ≈ 10,511.62
        expected_value = Decimal("10511.62")
        assert abs(events[0]["amount"] - expected_value) < Decimal("5.00")

    async def test_cd_maturity_outside_forecast_window(self):
        """Test that CD maturity outside forecast window is not included."""
        from app.models.account import Account, AccountType, CompoundingFrequency
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # Maturity date beyond forecast window
        maturity_date = date.today() + timedelta(days=365)

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Long-term CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.MONTHLY,
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events for 90 days
        events = await ForecastService._get_future_cd_maturity_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have no events (maturity outside window)
        assert len(events) == 0

    async def test_cd_without_interest_rate(self):
        """Test CD without interest rate uses principal only."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        maturity_date = date.today() + timedelta(days=30)

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="No Interest CD",
            account_type=AccountType.CD,
            original_amount=Decimal("5000.00"),
            interest_rate=None,  # No interest
            maturity_date=maturity_date,
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_cd_maturity_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have maturity event with principal only
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("5000.00")

    async def test_multiple_cd_accounts(self):
        """Test projection with multiple CD accounts."""
        from app.models.account import Account, AccountType, CompoundingFrequency
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        org_id = uuid4()
        user_id = uuid4()

        # Create two CDs
        cd1 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user_id,
            name="CD A",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.MONTHLY,
            origination_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        cd2 = Account(
            id=uuid4(),
            organization_id=org_id,
            user_id=user_id,
            name="CD B",
            account_type=AccountType.CD,
            original_amount=Decimal("15000.00"),
            interest_rate=Decimal("4.00"),
            compounding_frequency=CompoundingFrequency.QUARTERLY,
            origination_date=date.today() - timedelta(days=180),
            maturity_date=date.today() + timedelta(days=60),
            is_active=True,
        )

        # Mock database
        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [cd1, cd2]
        db.execute = AsyncMock(return_value=result_mock)

        # Generate events
        events = await ForecastService._get_future_cd_maturity_events(
            db, org_id, user_id, days_ahead=90
        )

        # Should have events from both CDs
        assert len(events) == 2
        cd_a_event = [e for e in events if "CD A" in e["merchant"]]
        cd_b_event = [e for e in events if "CD B" in e["merchant"]]

        assert len(cd_a_event) == 1
        assert len(cd_b_event) == 1

        # CD A matures first
        assert cd_a_event[0]["date"] < cd_b_event[0]["date"]


@pytest.mark.unit
class TestMortgagePaymentProjections:
    """Test mortgage/loan payment cash flow projections."""

    async def test_mortgage_payment_uses_amortization_formula(self):
        """Monthly payment calculated via standard amortization: M = P*r(1+r)^n / [(1+r)^n - 1]."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # $400,000 mortgage at 7% APR, 30-year term (360 months)
        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Home Mortgage",
            account_type=AccountType.MORTGAGE,
            current_balance=Decimal("400000.00"),
            interest_rate=Decimal("7.00"),
            loan_term_months=360,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have ~3 monthly payments
        assert len(events) >= 3

        # All amounts should be negative (cash outflow)
        assert all(e["amount"] < 0 for e in events)

        # Expected payment: $400,000 at 7%/12 monthly rate, 360 months
        # M ≈ $2,661.21
        monthly_rate = Decimal("7.00") / 100 / 12
        factor = (Decimal(1) + monthly_rate) ** 360
        expected_payment = Decimal("400000.00") * (monthly_rate * factor) / (factor - 1)

        for event in events:
            assert float(abs(event["amount"])) == pytest.approx(float(expected_payment), rel=0.001)
            assert "Loan Payment" in event["merchant"]

    async def test_loan_payment_uses_remaining_term_from_origination(self):
        """Remaining term is calculated from origination date when available."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        # Loan taken out 60 months ago on a 120-month term → 60 months remaining
        origination_date = date.today().replace(day=1) - timedelta(days=60 * 30)

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Car Loan",
            account_type=AccountType.LOAN,
            current_balance=Decimal("15000.00"),
            interest_rate=Decimal("5.00"),
            loan_term_months=120,
            origination_date=origination_date,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should have payments projected
        assert len(events) >= 3
        assert all(e["amount"] < 0 for e in events)

    async def test_accounts_without_interest_rate_are_skipped(self):
        """Accounts with no interest_rate should not generate payment events."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="No-Rate Mortgage",
            account_type=AccountType.MORTGAGE,
            current_balance=Decimal("300000.00"),
            interest_rate=None,  # No rate — skip
            exclude_from_cash_flow=False,
            is_active=True,
        )

        db = MagicMock()
        result_mock = MagicMock()
        # Query filters out accounts without interest_rate, so empty result
        result_mock.scalars().all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        assert events == []

    async def test_accounts_excluded_from_cash_flow_are_skipped(self):
        """Accounts with exclude_from_cash_flow=True should not generate payment events."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        db = MagicMock()
        result_mock = MagicMock()
        # exclude_from_cash_flow filter in query returns nothing
        result_mock.scalars().all.return_value = []
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        assert events == []

    async def test_payment_uses_default_term_when_no_term_data(self):
        """Mortgage without term data defaults to 360 months; loan defaults to 120 months."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        mortgage = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Unknown Term Mortgage",
            account_type=AccountType.MORTGAGE,
            current_balance=Decimal("250000.00"),
            interest_rate=Decimal("6.5"),
            loan_term_months=None,  # No term — use 360 default
            origination_date=None,
            maturity_date=None,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [mortgage]
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        # Should still generate payments using 360-month default
        assert len(events) >= 3
        assert all(e["amount"] < 0 for e in events)

    async def test_payment_events_on_correct_due_day(self):
        """Payments are scheduled on payment_due_day when set."""
        from app.models.account import Account, AccountType
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Student Loan",
            account_type=AccountType.STUDENT_LOAN,
            current_balance=Decimal("30000.00"),
            interest_rate=Decimal("4.5"),
            loan_term_months=120,
            payment_due_day=15,  # Due on the 15th
            exclude_from_cash_flow=False,
            is_active=True,
        )

        db = MagicMock()
        result_mock = MagicMock()
        result_mock.scalars().all.return_value = [account]
        db.execute = AsyncMock(return_value=result_mock)

        events = await ForecastService._get_mortgage_payment_events(
            db, uuid4(), None, days_ahead=90
        )

        # All payment dates should be on the 15th (or last day of month if shorter)
        for event in events:
            assert event["date"].day == 15
