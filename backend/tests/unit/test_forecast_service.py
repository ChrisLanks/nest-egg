"""Unit tests for forecast service."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.services.forecast_service import ForecastService
from app.utils.datetime_utils import utc_now


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
            pattern,
            days_ahead=21,  # 3 weeks
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
            pattern,
            days_ahead=93,  # >3 months to guarantee 4 occurrences regardless of start date
        )

        # Should have 4 occurrences (today + 3 monthly intervals)
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
            pattern,
            days_ahead=56,  # 4 biweekly periods
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
            pattern,
            days_ahead=45,  # 1.5 months
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
class TestPrivateDebtProjections:
    """Test Private Debt cash flow projections."""

    def test_monthly_interest_income_calculation(self):
        """Test monthly interest income is calculated correctly."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events([account], days_ahead=90)

        # Monthly interest = 10,000 * (6 / 100) / 12 = $50.00
        expected_monthly_interest = Decimal("50.00")

        # Should have ~3 monthly interest payments
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]
        assert len(interest_events) >= 3
        assert all(e["amount"] == expected_monthly_interest for e in interest_events)

    def test_principal_repayment_on_maturity(self):
        """Test principal repayment event on maturity date."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events([account], days_ahead=90)

        # Find principal repayment event
        principal_events = [e for e in events if "Principal Repayment" in e["merchant"]]
        assert len(principal_events) == 1
        assert principal_events[0]["amount"] == Decimal("25000.00")
        assert principal_events[0]["date"] == maturity_date

    def test_no_interest_rate_only_principal(self):
        """Test projection with no interest rate (only principal repayment)."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events([account], days_ahead=90)

        # Should only have principal repayment, no interest events
        assert len(events) == 1
        assert "Principal Repayment" in events[0]["merchant"]
        assert events[0]["amount"] == Decimal("5000.00")

    def test_maturity_outside_forecast_window(self):
        """Test that maturity date outside window is not included."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events for 90 days
        events = ForecastService._get_future_private_debt_events([account], days_ahead=90)

        # Should have interest payments but no principal repayment
        principal_events = [e for e in events if "Principal Repayment" in e["merchant"]]
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]

        assert len(principal_events) == 0  # Maturity outside window
        assert len(interest_events) >= 3  # Still get interest payments

    def test_skip_zero_principal_accounts(self):
        """Test that accounts with zero principal are skipped."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events([account], days_ahead=90)

        # Should have no events
        assert len(events) == 0

    def test_multiple_private_debt_accounts(self):
        """Test projection with multiple private debt accounts."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events(
            [account1, account2], days_ahead=90
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

    def test_year_rollover_for_interest_payments(self):
        """Test that interest payments handle year rollover correctly."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_private_debt_events(
            [account],
            days_ahead=120,  # 4 months
        )

        # Should have interest events spanning months
        interest_events = [e for e in events if "Interest Income" in e["merchant"]]
        assert len(interest_events) >= 4

        # Check that dates are in chronological order
        dates = [e["date"] for e in interest_events]
        assert dates == sorted(dates)


@pytest.mark.unit
class TestCDMaturityProjections:
    """Test CD maturity cash flow projections."""

    def test_cd_maturity_with_simple_interest(self):
        """Test CD maturity with simple interest (at_maturity compounding)."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

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

        # Generate events
        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=400)

        # Should have 1 maturity event
        assert len(events) == 1
        assert events[0]["date"] == maturity_date
        assert "CD Maturity" in events[0]["merchant"]

        # Simple interest: 10,000 * (1 + 0.05 * 2) = 11,000
        expected_value = Decimal("11000.00")
        assert abs(events[0]["amount"] - expected_value) < Decimal("1.00")

    def test_cd_maturity_with_monthly_compounding(self):
        """Test CD maturity with monthly compounding."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

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

        # Generate events
        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=90)

        # Should have 1 maturity event
        assert len(events) == 1
        assert events[0]["date"] == maturity_date

        # Monthly compounding: 10,000 * (1 + 0.05/12)^12 ≈ 10,511.62
        expected_value = Decimal("10511.62")
        assert abs(events[0]["amount"] - expected_value) < Decimal("5.00")

    def test_cd_maturity_outside_forecast_window(self):
        """Test that CD maturity outside forecast window is not included."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

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

        # Generate events for 90 days
        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=90)

        # Should have no events (maturity outside window)
        assert len(events) == 0

    def test_cd_without_interest_rate(self):
        """Test CD without interest rate uses principal only."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        # Generate events
        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=90)

        # Should have maturity event with principal only
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("5000.00")

    def test_multiple_cd_accounts(self):
        """Test projection with multiple CD accounts."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

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

        # Generate events
        events = ForecastService._get_future_cd_maturity_events([cd1, cd2], days_ahead=90)

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

    def test_mortgage_payment_uses_amortization_formula(self):
        """Monthly payment calculated via standard amortization: M = P*r(1+r)^n / [(1+r)^n - 1]."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)

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

    def test_loan_payment_uses_remaining_term_from_origination(self):
        """Remaining term is calculated from origination date when available."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)

        # Should have payments projected
        assert len(events) >= 3
        assert all(e["amount"] < 0 for e in events)

    def test_accounts_without_interest_rate_are_skipped(self):
        """Accounts with no interest_rate should not generate payment events."""
        # Pass empty list to simulate pre-filtered accounts without interest_rate
        events = ForecastService._get_mortgage_payment_events([], days_ahead=90)

        assert events == []

    def test_accounts_excluded_from_cash_flow_are_skipped(self):
        """Accounts with exclude_from_cash_flow=True should not generate payment events."""
        # Pass empty list to simulate pre-filtered accounts with exclude_from_cash_flow
        events = ForecastService._get_mortgage_payment_events([], days_ahead=90)

        assert events == []

    def test_payment_uses_default_term_when_no_term_data(self):
        """Mortgage without term data defaults to 360 months; loan defaults to 120 months."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        events = ForecastService._get_mortgage_payment_events([mortgage], days_ahead=90)

        # Should still generate payments using 360-month default
        assert len(events) >= 3
        assert all(e["amount"] < 0 for e in events)

    def test_payment_events_on_correct_due_day(self):
        """Payments are scheduled on payment_due_day when set."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

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

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)

        # All payment dates should be on the 15th (or last day of month if shorter)
        for event in events:
            assert event["date"].day == 15


@pytest.mark.unit
class TestBondCouponEvents:
    """Test bond coupon cash flow projections."""

    def test_bond_coupon_semi_annual_default(self):
        """Bonds with no compounding_frequency default to semi-annual coupons."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Treasury Bond",
            account_type=AccountType.BOND,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("4.00"),
            compounding_frequency=None,  # defaults to semi-annual
            origination_date=date.today() - timedelta(days=30),
            maturity_date=date.today() + timedelta(days=400),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=365)

        coupon_events = [e for e in events if "Coupon" in e["merchant"]]
        # Semi-annual = 2/year, so expect ~2 coupon events in 365 days
        assert len(coupon_events) >= 1
        # Coupon amount: 10,000 * 0.04 / 2 = 200
        expected_coupon = Decimal("10000.00") * Decimal("0.04") / Decimal("2")
        for e in coupon_events:
            assert e["amount"] == expected_coupon

    def test_bond_maturity_repayment(self):
        """Should include principal repayment on maturity date."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        maturity_date = date.today() + timedelta(days=60)

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Corporate Bond",
            account_type=AccountType.BOND,
            original_amount=Decimal("25000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=None,
            origination_date=date.today() - timedelta(days=100),
            maturity_date=maturity_date,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=90)

        maturity_events = [e for e in events if "Maturity" in e["merchant"]]
        assert len(maturity_events) == 1
        assert maturity_events[0]["amount"] == Decimal("25000.00")
        assert maturity_events[0]["date"] == maturity_date

    def test_bond_already_matured_skipped(self):
        """Bonds past maturity should be skipped entirely."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Expired Bond",
            account_type=AccountType.BOND,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("3.00"),
            maturity_date=date.today() - timedelta(days=30),  # Already matured
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=90)
        assert len(events) == 0

    def test_bond_excluded_from_cash_flow_skipped(self):
        """Bonds with exclude_from_cash_flow should be skipped."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Excluded Bond",
            account_type=AccountType.BOND,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("4.00"),
            exclude_from_cash_flow=True,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=90)
        assert len(events) == 0

    def test_bond_with_quarterly_coupons(self):
        """Bond with quarterly compounding frequency."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Quarterly Bond",
            account_type=AccountType.BOND,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("4.00"),
            compounding_frequency=CompoundingFrequency.QUARTERLY,
            origination_date=date.today() - timedelta(days=10),
            maturity_date=date.today() + timedelta(days=400),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=365)
        coupon_events = [e for e in events if "Coupon" in e["merchant"]]
        # Quarterly = 4/year, expect ~4 in 365 days
        assert len(coupon_events) >= 3
        # Coupon amount: 10,000 * 0.04 / 4 = 100
        expected_coupon = Decimal("10000.00") * Decimal("0.04") / Decimal("4")
        for e in coupon_events:
            assert e["amount"] == expected_coupon

    def test_bond_zero_principal_skipped(self):
        """Bond with zero or None principal should be skipped."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Zero Bond",
            account_type=AccountType.BOND,
            original_amount=None,
            current_balance=Decimal("0"),
            interest_rate=Decimal("4.00"),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_bond_coupon_events([account], days_ahead=90)
        assert len(events) == 0


@pytest.mark.unit
class TestPensionAnnuityIncomeEvents:
    """Test pension/annuity income projections."""

    def test_pension_monthly_income(self):
        """Should project monthly pension payments."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="State Pension",
            account_type=AccountType.PENSION,
            monthly_benefit=Decimal("2500.00"),
            benefit_start_date=date.today() - timedelta(days=30),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) >= 2
        for e in events:
            assert e["amount"] == Decimal("2500.00")
            assert "Income" in e["merchant"]

    def test_annuity_income_events(self):
        """Should project annuity income payments."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Life Annuity",
            account_type=AccountType.ANNUITY,
            monthly_benefit=Decimal("1500.00"),
            benefit_start_date=date.today() - timedelta(days=15),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) >= 2

    def test_pension_not_started_yet(self):
        """Pension starting beyond forecast window should produce no events."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Future Pension",
            account_type=AccountType.PENSION,
            monthly_benefit=Decimal("3000.00"),
            benefit_start_date=date.today() + timedelta(days=365),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) == 0

    def test_pension_excluded_from_cash_flow(self):
        """Pensions excluded from cash flow should produce no events."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Excluded Pension",
            account_type=AccountType.PENSION,
            monthly_benefit=Decimal("2000.00"),
            benefit_start_date=date.today() - timedelta(days=30),
            exclude_from_cash_flow=True,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) == 0

    def test_pension_no_benefit_start_date(self):
        """Pension with no benefit_start_date should default to today."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Active Pension",
            account_type=AccountType.PENSION,
            monthly_benefit=Decimal("1800.00"),
            benefit_start_date=None,  # Defaults to today
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) >= 2

    def test_zero_benefit_skipped(self):
        """Pensions with zero monthly_benefit should produce no events."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Empty Pension",
            account_type=AccountType.PENSION,
            monthly_benefit=None,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_pension_annuity_income_events([account], days_ahead=90)
        assert len(events) == 0


@pytest.mark.unit
class TestVestingEvents:
    """Test private equity vesting event projections."""

    def test_future_vesting_events(self):
        """Should project future vesting events within forecast window."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        vest_date = (date.today() + timedelta(days=30)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Startup Equity",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("25.00"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("2500.00")

    def test_past_vesting_events_excluded(self):
        """Vesting events in the past should not be included."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        vest_date = (date.today() - timedelta(days=30)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Vested Equity",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("25.00"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0

    def test_vesting_no_share_price_skipped(self):
        """Accounts with zero share price produce no events."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        vest_date = (date.today() + timedelta(days=30)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="No Price Equity",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("0"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0

    def test_vesting_excluded_from_networth_skipped(self):
        """Accounts not included in networth should be skipped."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        vest_date = (date.today() + timedelta(days=30)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Excluded Equity",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("25.00"),
            include_in_networth=False,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0

    def test_malformed_vesting_schedule_skipped(self):
        """Malformed JSON vesting schedule should be skipped gracefully."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Bad Schedule",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule="not-valid-json",
            share_price=Decimal("25.00"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0


@pytest.mark.unit
class TestForecastOccurrenceEdgeCases:
    """Additional edge cases for occurrence calculation."""

    def test_quarterly_occurrences(self):
        """Test quarterly recurring transactions."""
        pattern = RecurringTransaction(
            merchant_name="Quarterly Bill",
            average_amount=Decimal("-500.00"),
            frequency=RecurringFrequency.QUARTERLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(pattern, days_ahead=365)
        # Quarterly = 4/year + today = 5 occurrences
        assert len(occurrences) == 5

    def test_yearly_occurrences(self):
        """Test yearly recurring transactions."""
        pattern = RecurringTransaction(
            merchant_name="Annual Subscription",
            average_amount=Decimal("-120.00"),
            frequency=RecurringFrequency.YEARLY,
            next_expected_date=date.today(),
        )

        occurrences = ForecastService._calculate_future_occurrences(pattern, days_ahead=365)
        # Should have 2 occurrences (today + 1 year)
        assert len(occurrences) == 2

    def test_no_next_expected_date_uses_today(self):
        """When next_expected_date is None, should use today."""
        pattern = RecurringTransaction(
            merchant_name="Unknown Date",
            average_amount=Decimal("-50.00"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=None,
        )

        occurrences = ForecastService._calculate_future_occurrences(pattern, days_ahead=30)
        assert len(occurrences) >= 1
        assert occurrences[0]["date"] == date.today()


@pytest.mark.unit
class TestMortgagePaymentEdgeCases:
    """Additional mortgage payment edge cases."""

    def test_loan_with_maturity_date_no_term(self):
        """Loan with maturity_date but no loan_term_months should use maturity for remaining."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Maturity Loan",
            account_type=AccountType.LOAN,
            current_balance=Decimal("50000.00"),
            interest_rate=Decimal("5.00"),
            loan_term_months=None,
            origination_date=None,
            maturity_date=date.today() + timedelta(days=365 * 5),
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)
        assert len(events) >= 3
        assert all(e["amount"] < 0 for e in events)

    def test_zero_balance_loan_skipped(self):
        """Loan with zero balance should produce no events."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Paid Off Loan",
            account_type=AccountType.LOAN,
            current_balance=Decimal("0.00"),
            interest_rate=Decimal("5.00"),
            loan_term_months=120,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)
        assert len(events) == 0

    def test_student_loan_default_term(self):
        """Student loan with no term data defaults to 120 months (not 360)."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        loan = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Student Loan No Term",
            account_type=AccountType.STUDENT_LOAN,
            current_balance=Decimal("30000.00"),
            interest_rate=Decimal("4.5"),
            loan_term_months=None,
            origination_date=None,
            maturity_date=None,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_mortgage_payment_events([loan], days_ahead=90)
        # Should have events using 120-month default
        assert len(events) >= 3


# ---------------------------------------------------------------------------
# Tests for generate_forecast (async, requires mocked DB)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateForecast:
    """Test the main generate_forecast entry point."""

    @pytest.mark.asyncio
    async def test_generate_forecast_basic(self):
        """Should produce daily forecast data points."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        # Mock account query result
        checking = MagicMock(spec=Account)
        checking.id = uuid4()
        checking.account_type = AccountType.CHECKING
        checking.is_active = True
        checking.vesting_schedule = None
        checking.include_in_networth = True
        checking.company_status = None

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [checking]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        with (
            patch.object(
                ForecastService,
                "_get_total_balance",
                new_callable=AsyncMock,
                return_value=Decimal("5000"),
            ),
            patch(
                "app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            forecast = await ForecastService.generate_forecast(db, org_id, days_ahead=5)

        assert len(forecast) == 6  # today + 5 days
        assert forecast[0]["projected_balance"] == 5000.0
        assert forecast[0]["date"] == date.today().isoformat()

    @pytest.mark.asyncio
    async def test_generate_forecast_with_user_filter(self):
        """Should filter recurring transactions by user account IDs."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        user_id = uuid4()
        db = AsyncMock()

        acct = MagicMock(spec=Account)
        acct.id = uuid4()
        acct.account_type = AccountType.CHECKING
        acct.is_active = True
        acct.vesting_schedule = None

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [acct]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        # Create a recurring txn for a different account
        rt = RecurringTransaction(
            merchant_name="Other",
            average_amount=Decimal("-50"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
            account_id=uuid4(),  # different from acct.id
        )

        with (
            patch.object(
                ForecastService,
                "_get_total_balance",
                new_callable=AsyncMock,
                return_value=Decimal("1000"),
            ),
            patch(
                "app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                new_callable=AsyncMock,
                return_value=[rt],
            ),
        ):
            forecast = await ForecastService.generate_forecast(
                db, org_id, user_id=user_id, days_ahead=3
            )

        # The recurring txn is for a different account, so it should be filtered out
        assert all(f["day_change"] == 0.0 for f in forecast)

    @pytest.mark.asyncio
    async def test_generate_forecast_includes_recurring(self):
        """Should include recurring transaction amounts in forecast."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        acct = MagicMock(spec=Account)
        acct.id = uuid4()
        acct.account_type = AccountType.CHECKING
        acct.is_active = True
        acct.vesting_schedule = None

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [acct]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        # Create a recurring txn for today
        rt = RecurringTransaction(
            merchant_name="Netflix",
            average_amount=Decimal("-15.99"),
            frequency=RecurringFrequency.MONTHLY,
            next_expected_date=date.today(),
        )

        with (
            patch.object(
                ForecastService,
                "_get_total_balance",
                new_callable=AsyncMock,
                return_value=Decimal("1000"),
            ),
            patch(
                "app.services.forecast_service.RecurringDetectionService.get_recurring_transactions",
                new_callable=AsyncMock,
                return_value=[rt],
            ),
        ):
            forecast = await ForecastService.generate_forecast(db, org_id, days_ahead=3)

        # First day should include the recurring transaction
        assert forecast[0]["day_change"] == float(Decimal("-15.99"))
        assert forecast[0]["transaction_count"] >= 1


# ---------------------------------------------------------------------------
# Tests for _get_total_balance (async, mocked DB)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTotalBalance:
    """Test _get_total_balance with various account types."""

    @pytest.mark.asyncio
    async def test_basic_balance(self):
        """Should sum balances of regular accounts."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        checking = MagicMock(spec=Account)
        checking.include_in_networth = True
        checking.account_type = AccountType.CHECKING
        checking.current_balance = Decimal("5000")
        checking.exclude_from_cash_flow = False
        checking.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [checking]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("5000")

    @pytest.mark.asyncio
    async def test_debt_account_subtracted(self):
        """Debt accounts should be subtracted from total."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        cc = MagicMock(spec=Account)
        cc.include_in_networth = True
        cc.account_type = AccountType.CREDIT_CARD
        cc.current_balance = Decimal("500")
        cc.exclude_from_cash_flow = False
        cc.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [cc]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("-500")

    @pytest.mark.asyncio
    async def test_vehicle_excluded_by_default(self):
        """Vehicle accounts with include_in_networth=None should be excluded."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        vehicle = MagicMock(spec=Account)
        vehicle.include_in_networth = None
        vehicle.account_type = AccountType.VEHICLE
        vehicle.current_balance = Decimal("25000")
        vehicle.exclude_from_cash_flow = False
        vehicle.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [vehicle]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("0")

    @pytest.mark.asyncio
    async def test_private_equity_public_auto_included(self):
        """Private equity with company_status=public and
        include_in_networth=None should be included."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompanyStatus

        org_id = uuid4()
        db = AsyncMock()

        pe = MagicMock(spec=Account)
        pe.include_in_networth = None
        pe.account_type = AccountType.PRIVATE_EQUITY
        pe.company_status = CompanyStatus.PUBLIC
        pe.vesting_schedule = None
        pe.current_balance = Decimal("10000")
        pe.exclude_from_cash_flow = False
        pe.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pe]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("10000")

    @pytest.mark.asyncio
    async def test_private_equity_private_auto_excluded(self):
        """Private equity with company_status=private and
        include_in_networth=None should be excluded."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompanyStatus

        org_id = uuid4()
        db = AsyncMock()

        pe = MagicMock(spec=Account)
        pe.include_in_networth = None
        pe.account_type = AccountType.PRIVATE_EQUITY
        pe.company_status = CompanyStatus.PRIVATE
        pe.vesting_schedule = None
        pe.current_balance = Decimal("10000")
        pe.exclude_from_cash_flow = False
        pe.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pe]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("0")

    @pytest.mark.asyncio
    async def test_business_equity_with_equity_value(self):
        """Business equity should use equity_value when set."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        biz = MagicMock(spec=Account)
        biz.include_in_networth = True
        biz.account_type = AccountType.BUSINESS_EQUITY
        biz.equity_value = Decimal("500000")
        biz.company_valuation = None
        biz.ownership_percentage = None
        biz.current_balance = Decimal("0")
        biz.exclude_from_cash_flow = False
        biz.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [biz]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("500000")

    @pytest.mark.asyncio
    async def test_business_equity_with_valuation_and_percentage(self):
        """Business equity should calculate value from valuation * ownership_percentage."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        biz = MagicMock(spec=Account)
        biz.include_in_networth = True
        biz.account_type = AccountType.BUSINESS_EQUITY
        biz.equity_value = None
        biz.company_valuation = Decimal("1000000")
        biz.ownership_percentage = Decimal("25")
        biz.current_balance = Decimal("0")
        biz.exclude_from_cash_flow = False
        biz.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [biz]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("250000")

    @pytest.mark.asyncio
    async def test_business_equity_valuation_no_percentage(self):
        """Business equity with valuation but no percentage assumes 100%."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        biz = MagicMock(spec=Account)
        biz.include_in_networth = True
        biz.account_type = AccountType.BUSINESS_EQUITY
        biz.equity_value = None
        biz.company_valuation = Decimal("750000")
        biz.ownership_percentage = None
        biz.current_balance = Decimal("100")
        biz.exclude_from_cash_flow = False
        biz.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [biz]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("750000")

    @pytest.mark.asyncio
    async def test_private_equity_with_vesting_schedule(self):
        """Private equity with vesting schedule should calculate vested value."""
        import json
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        utc_today = utc_now().date()
        yesterday = (utc_today - timedelta(days=1)).isoformat()
        tomorrow = (utc_today + timedelta(days=1)).isoformat()
        schedule = json.dumps(
            [
                {"date": yesterday, "quantity": 100},
                {"date": tomorrow, "quantity": 200},
            ]
        )

        pe = MagicMock(spec=Account)
        pe.include_in_networth = True
        pe.account_type = AccountType.PRIVATE_EQUITY
        pe.vesting_schedule = schedule
        pe.share_price = Decimal("50")
        pe.current_balance = Decimal("0")
        pe.exclude_from_cash_flow = False
        pe.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pe]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        # Only past/today vesting entries count: 100 shares * $50 = $5000
        # (tomorrow's 200 shares are not yet vested)
        assert total == Decimal("5000")

    @pytest.mark.asyncio
    async def test_private_equity_malformed_vesting_fallback(self):
        """Private equity with malformed JSON should fall back to current_balance."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        pe = MagicMock(spec=Account)
        pe.include_in_networth = True
        pe.account_type = AccountType.PRIVATE_EQUITY
        pe.vesting_schedule = "not-valid-json"
        pe.current_balance = Decimal("3000")
        pe.exclude_from_cash_flow = False
        pe.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pe]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("3000")

    @pytest.mark.asyncio
    async def test_private_equity_non_list_vesting_fallback(self):
        """Private equity with non-list vesting schedule should fall back to balance."""
        import json
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        pe = MagicMock(spec=Account)
        pe.include_in_networth = True
        pe.account_type = AccountType.PRIVATE_EQUITY
        pe.vesting_schedule = json.dumps({"not": "a list"})
        pe.current_balance = Decimal("7000")
        pe.exclude_from_cash_flow = False
        pe.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [pe]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("7000")

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self):
        """Should add user_id condition when provided."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        org_id = uuid4()
        user_id = uuid4()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id, user_id=user_id)
        assert total == Decimal("0")
        db.execute.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests for check_negative_balance_alert
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCheckNegativeBalanceAlert:
    """Test negative balance alert logic."""

    @pytest.mark.asyncio
    async def test_creates_alert_on_negative_balance(self):
        """Should create notification when negative balance is projected."""
        from unittest.mock import AsyncMock, patch

        org_id = __import__("uuid").uuid4()
        db = AsyncMock()

        mock_forecast = [
            {
                "date": "2025-01-01",
                "projected_balance": 500.0,
                "day_change": 0,
                "transaction_count": 0,
            },
            {
                "date": "2025-01-02",
                "projected_balance": -100.0,
                "day_change": -600,
                "transaction_count": 1,
            },
        ]

        with (
            patch.object(
                ForecastService,
                "generate_forecast",
                new_callable=AsyncMock,
                return_value=mock_forecast,
            ),
            patch(
                "app.services.forecast_service.NotificationService.create_notification",
                new_callable=AsyncMock,
            ) as mock_notify,
        ):
            result = await ForecastService.check_negative_balance_alert(db, org_id)

        assert result is not None
        assert result["projected_balance"] == -100.0
        mock_notify.assert_awaited_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_negative(self):
        """Should return None when forecast stays positive."""
        from unittest.mock import AsyncMock, patch

        org_id = __import__("uuid").uuid4()
        db = AsyncMock()

        mock_forecast = [
            {
                "date": "2025-01-01",
                "projected_balance": 500.0,
                "day_change": 0,
                "transaction_count": 0,
            },
            {
                "date": "2025-01-02",
                "projected_balance": 400.0,
                "day_change": -100,
                "transaction_count": 1,
            },
        ]

        with patch.object(
            ForecastService, "generate_forecast", new_callable=AsyncMock, return_value=mock_forecast
        ):
            result = await ForecastService.check_negative_balance_alert(db, org_id)

        assert result is None


# ---------------------------------------------------------------------------
# CD maturity edge cases (compound interest)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCDMaturityCompounding:
    """CD maturity with various compounding frequencies."""

    def test_cd_daily_compounding(self):
        """CD with daily compounding should calculate compound interest."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Daily CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.DAILY,
            origination_date=date.today() - timedelta(days=180),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 1
        assert events[0]["amount"] > Decimal("10000.00")  # Principal + interest

    def test_cd_quarterly_compounding(self):
        """CD with quarterly compounding should calculate compound interest."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Quarterly CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.QUARTERLY,
            origination_date=date.today() - timedelta(days=180),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 1
        assert events[0]["amount"] > Decimal("10000.00")

    def test_cd_at_maturity_simple_interest(self):
        """CD with at_maturity compounding uses simple interest."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Simple CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.AT_MATURITY,
            origination_date=date.today() - timedelta(days=365),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 1
        # Simple interest: P * (1 + r * t)
        assert events[0]["amount"] > Decimal("10000.00")

    def test_cd_no_original_amount_uses_balance(self):
        """CD with no original_amount should use current_balance."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Balance CD",
            account_type=AccountType.CD,
            original_amount=None,
            current_balance=Decimal("5000.00"),
            interest_rate=Decimal("0"),
            compounding_frequency=None,
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("5000.00")

    def test_cd_zero_principal_skipped(self):
        """CD with zero principal should be skipped."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Empty CD",
            account_type=AccountType.CD,
            original_amount=Decimal("0"),
            current_balance=Decimal("0"),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 0

    def test_cd_no_origination_date_uses_today(self):
        """CD with no origination_date should default to today."""
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompoundingFrequency

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="No Origin CD",
            account_type=AccountType.CD,
            original_amount=Decimal("10000.00"),
            interest_rate=Decimal("5.00"),
            compounding_frequency=CompoundingFrequency.MONTHLY,
            origination_date=None,
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_cd_maturity_events([account], days_ahead=60)
        assert len(events) == 1


# ---------------------------------------------------------------------------
# Vesting events edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVestingEdgeCases:
    """Additional edge cases for vesting events."""

    def test_vesting_auto_include_public_company(self):
        """Private equity with company_status=public and
        include_in_networth=None should be included."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompanyStatus

        vest_date = (date.today() + timedelta(days=15)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 50}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Public PE",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("100"),
            include_in_networth=None,
            company_status=CompanyStatus.PUBLIC,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=30)
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("5000")

    def test_vesting_non_list_schedule_skipped(self):
        """Vesting schedule that is valid JSON but not a list should be skipped."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Dict Schedule",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=json.dumps({"date": "2025-01-01", "quantity": 100}),
            share_price=Decimal("50"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0

    def test_vesting_milestone_missing_date(self):
        """Milestone with no date should be skipped."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        schedule = json.dumps([{"quantity": 100}])  # no date

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="No Date Milestone",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("50"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0

    def test_vesting_milestone_invalid_date(self):
        """Milestone with invalid date format should be skipped."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        schedule = json.dumps([{"date": "not-a-date", "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Bad Date Milestone",
            account_type=AccountType.PRIVATE_EQUITY,
            vesting_schedule=schedule,
            share_price=Decimal("50"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=90)
        assert len(events) == 0


# ---------------------------------------------------------------------------
# Private debt events edge case
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrivateDebtEdgeCases:
    """Additional private debt event edge cases."""

    def test_private_debt_no_interest_but_maturity(self):
        """Private debt with zero interest but maturity should only show principal."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Zero Rate Debt",
            account_type=AccountType.PRIVATE_DEBT,
            principal_amount=Decimal("50000"),
            interest_rate=Decimal("0"),
            maturity_date=date.today() + timedelta(days=30),
            is_active=True,
        )

        events = ForecastService._get_future_private_debt_events([account], days_ahead=60)
        # Should have only the principal repayment, no interest
        assert len(events) == 1
        assert "Principal Repayment" in events[0]["merchant"]

    def test_mortgage_default_term_360_months(self):
        """Mortgage with no term data defaults to 360 months."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Mortgage No Term",
            account_type=AccountType.MORTGAGE,
            current_balance=Decimal("300000"),
            interest_rate=Decimal("6.5"),
            loan_term_months=None,
            origination_date=None,
            maturity_date=None,
            payment_due_day=15,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        # Use 120 days to guarantee >= 3 payment dates regardless of current day-of-month
        events = ForecastService._get_mortgage_payment_events([account], days_ahead=120)
        assert len(events) >= 3
        # Payment should be based on 360-month term
        for e in events:
            assert e["amount"] < 0

    def test_mortgage_loan_term_only(self):
        """Loan with loan_term_months but no origination or maturity should use full term."""
        from uuid import uuid4

        from app.models.account import Account, AccountType

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Term Only Loan",
            account_type=AccountType.LOAN,
            current_balance=Decimal("20000"),
            interest_rate=Decimal("5.0"),
            loan_term_months=60,
            origination_date=None,
            maturity_date=None,
            exclude_from_cash_flow=False,
            is_active=True,
        )

        events = ForecastService._get_mortgage_payment_events([account], days_ahead=90)
        assert len(events) >= 3


# ---------------------------------------------------------------------------
# STOCK_OPTIONS vesting in forecast service
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStockOptionsForecast:
    """STOCK_OPTIONS accounts use the same vesting logic as PRIVATE_EQUITY in forecast."""

    def test_future_vesting_events_stock_options(self):
        """_get_future_vesting_events includes STOCK_OPTIONS accounts."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        vest_date = (date.today() + timedelta(days=10)).isoformat()
        schedule = json.dumps([{"date": vest_date, "quantity": 100}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="RSU Grant",
            account_type=AccountType.STOCK_OPTIONS,
            vesting_schedule=schedule,
            share_price=Decimal("20"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=30)
        assert len(events) == 1
        assert events[0]["amount"] == Decimal("2000")  # 100 * 20

    def test_future_vesting_events_stock_options_past_excluded(self):
        """Past vesting events for STOCK_OPTIONS are not included in future events."""
        import json
        from uuid import uuid4

        from app.models.account import Account, AccountType

        past_date = (date.today() - timedelta(days=10)).isoformat()
        schedule = json.dumps([{"date": past_date, "quantity": 500}])

        account = Account(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uuid4(),
            name="Past Vested RSUs",
            account_type=AccountType.STOCK_OPTIONS,
            vesting_schedule=schedule,
            share_price=Decimal("10"),
            include_in_networth=True,
            is_active=True,
        )

        events = ForecastService._get_future_vesting_events([account], days_ahead=30)
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_get_total_balance_stock_options_public_auto_included(self):
        """STOCK_OPTIONS at a public company auto-include in _get_total_balance."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompanyStatus

        org_id = uuid4()
        db = AsyncMock()

        so = MagicMock(spec=Account)
        so.include_in_networth = None
        so.account_type = AccountType.STOCK_OPTIONS
        so.company_status = CompanyStatus.PUBLIC
        so.vesting_schedule = None
        so.current_balance = Decimal("15000")
        so.exclude_from_cash_flow = False
        so.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [so]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("15000")

    @pytest.mark.asyncio
    async def test_get_total_balance_stock_options_private_auto_excluded(self):
        """STOCK_OPTIONS at a private company are excluded from _get_total_balance by default."""
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType, CompanyStatus

        org_id = uuid4()
        db = AsyncMock()

        so = MagicMock(spec=Account)
        so.include_in_networth = None
        so.account_type = AccountType.STOCK_OPTIONS
        so.company_status = CompanyStatus.PRIVATE
        so.vesting_schedule = None
        so.current_balance = Decimal("15000")
        so.exclude_from_cash_flow = False
        so.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [so]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        assert total == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_total_balance_stock_options_with_vesting(self):
        """_get_total_balance applies vesting math for STOCK_OPTIONS."""
        import json
        from unittest.mock import AsyncMock, MagicMock
        from uuid import uuid4

        from app.models.account import Account, AccountType

        org_id = uuid4()
        db = AsyncMock()

        so = MagicMock(spec=Account)
        so.include_in_networth = True
        so.account_type = AccountType.STOCK_OPTIONS
        so.vesting_schedule = json.dumps(
            [
                {"date": "2020-01-01", "quantity": 300},  # vested
                {"date": "2099-01-01", "quantity": 700},  # not vested
            ]
        )
        so.share_price = Decimal("10")
        so.current_balance = Decimal("10000")
        so.exclude_from_cash_flow = False
        so.is_active = True

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [so]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        total = await ForecastService._get_total_balance(db, org_id)
        # 300 vested * $10 = $3000
        assert total == Decimal("3000")
