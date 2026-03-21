"""Unit tests for rental property service."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.services.rental_property_service import RentalPropertyService


def _make_account(
    name="123 Main St",
    balance=300000,
    is_rental=True,
    rental_income=2000,
    address="123 Main St, Anytown",
    org_id=None,
    user_id=None,
    property_type=None,
):
    acct = Mock()
    acct.id = uuid4()
    acct.name = name
    acct.current_balance = Decimal(str(balance))
    acct.is_rental_property = is_rental
    acct.rental_monthly_income = Decimal(str(rental_income))
    acct.rental_address = address
    acct.organization_id = org_id or uuid4()
    acct.user_id = user_id or uuid4()
    acct.is_active = True
    acct.property_type = property_type
    return acct


def _make_transaction(txn_date, amount, category_name=None):
    txn = Mock()
    txn.date = txn_date
    txn.amount = Decimal(str(amount))
    txn.is_pending = False
    return txn, category_name


@pytest.mark.unit
class TestGetRentalProperties:
    """Test listing rental properties."""

    @pytest.mark.asyncio
    async def test_returns_property_list(self):
        """Returns all rental properties for the org."""
        mock_db = AsyncMock()
        acct = _make_account()

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [acct]
        mock_db.execute.return_value = mock_result

        service = RentalPropertyService(mock_db)
        org_id = acct.organization_id

        result = await service.get_rental_properties(org_id)

        assert len(result) == 1
        assert result[0]["name"] == "123 Main St"
        assert result[0]["rental_monthly_income"] == 2000.0
        assert result[0]["rental_address"] == "123 Main St, Anytown"

    @pytest.mark.asyncio
    async def test_empty_when_no_rentals(self):
        """Returns empty list when no rental properties exist."""
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        service = RentalPropertyService(mock_db)
        result = await service.get_rental_properties(uuid4())

        assert result == []


@pytest.mark.unit
class TestGetPropertyPnl:
    """Test P&L calculation for a rental property."""

    @pytest.fixture
    def org_id(self):
        return uuid4()

    @pytest.fixture
    def account(self, org_id):
        acct = _make_account(balance=300000, org_id=org_id)
        return acct

    @pytest.mark.asyncio
    async def test_pnl_income_and_expenses(self, org_id, account):
        """P&L correctly sums income and expenses."""
        mock_db = AsyncMock()

        # First call: account lookup
        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        # Second call: transactions
        txns = [
            _make_transaction(date(2024, 1, 15), 2000, "Rent"),  # income
            _make_transaction(date(2024, 1, 20), 2000, "Rent"),  # income
            _make_transaction(date(2024, 2, 1), -500, "Repairs"),  # expense
            _make_transaction(date(2024, 3, 1), -200, "Insurance"),  # expense
            _make_transaction(date(2024, 6, 1), -1000, "Mortgage Interest"),  # expense
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        assert result["gross_income"] == 4000.0
        assert result["total_expenses"] == 1700.0
        assert result["net_income"] == 2300.0

    @pytest.mark.asyncio
    async def test_cap_rate_calculation(self, org_id, account):
        """Cap rate = net_income / property_value * 100."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txns = [
            _make_transaction(date(2024, 1, 15), 24000, "Rent"),
            _make_transaction(date(2024, 6, 1), -6000, "Expenses"),
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        # Net income: 24000 - 6000 = 18000; Cap rate: 18000 / 300000 * 100 = 6.0
        assert abs(result["cap_rate"] - 6.0) < 0.1

    @pytest.mark.asyncio
    async def test_cap_rate_zero_value_property(self, org_id):
        """Cap rate is 0 when property value is 0."""
        mock_db = AsyncMock()
        account = _make_account(balance=0, org_id=org_id)

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txn_result = Mock()
        txn_result.all.return_value = []

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        assert result["cap_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_schedule_e_category_breakdown(self, org_id, account):
        """Expenses are broken down by category (Schedule E style)."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txns = [
            _make_transaction(date(2024, 2, 1), -800, "Repairs"),
            _make_transaction(date(2024, 3, 1), -300, "Insurance"),
            _make_transaction(date(2024, 4, 1), -200, "Repairs"),
            _make_transaction(date(2024, 5, 1), -500, "Utilities"),
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        breakdown = {item["category"]: item["amount"] for item in result["expense_breakdown"]}
        assert breakdown["Repairs"] == 1000.0
        assert breakdown["Insurance"] == 300.0
        assert breakdown["Utilities"] == 500.0

    @pytest.mark.asyncio
    async def test_expense_breakdown_sorted_by_amount_desc(self, org_id, account):
        """Expense breakdown is sorted by amount descending."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txns = [
            _make_transaction(date(2024, 1, 1), -100, "Supplies"),
            _make_transaction(date(2024, 2, 1), -500, "Repairs"),
            _make_transaction(date(2024, 3, 1), -300, "Insurance"),
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        amounts = [item["amount"] for item in result["expense_breakdown"]]
        assert amounts == sorted(amounts, reverse=True)

    @pytest.mark.asyncio
    async def test_monthly_breakdown_all_12_months(self, org_id, account):
        """Monthly breakdown always contains all 12 months."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txns = [
            _make_transaction(date(2024, 3, 1), 2000, "Rent"),
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        assert len(result["monthly"]) == 12
        months = [m["month"] for m in result["monthly"]]
        assert months == list(range(1, 13))

        # March should have income
        march = result["monthly"][2]
        assert march["income"] == 2000.0
        assert march["net"] == 2000.0

        # January should be zero
        jan = result["monthly"][0]
        assert jan["income"] == 0.0
        assert jan["expenses"] == 0.0

    @pytest.mark.asyncio
    async def test_account_not_found(self, org_id):
        """Returns error when account not found."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = None

        mock_db.execute.return_value = acct_result

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, uuid4(), 2024)

        assert "error" in result
        assert result["error"] == "Account not found"

    @pytest.mark.asyncio
    async def test_no_transactions_yields_zero_pnl(self, org_id, account):
        """No transactions means zero income and expenses."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txn_result = Mock()
        txn_result.all.return_value = []

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        assert result["gross_income"] == 0.0
        assert result["total_expenses"] == 0.0
        assert result["net_income"] == 0.0

    @pytest.mark.asyncio
    async def test_uncategorized_expenses_labeled_other(self, org_id, account):
        """Expenses without a category are labeled 'Other'."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = account

        txns = [
            _make_transaction(date(2024, 1, 1), -250, None),  # No category
        ]
        txn_result = Mock()
        txn_result.all.return_value = txns

        mock_db.execute.side_effect = [acct_result, txn_result]

        service = RentalPropertyService(mock_db)
        result = await service.get_property_pnl(org_id, account.id, 2024)

        assert len(result["expense_breakdown"]) == 1
        assert result["expense_breakdown"][0]["category"] == "Other"


@pytest.mark.unit
class TestGetAllPropertiesSummary:
    """Test summary aggregation across all properties."""

    @pytest.mark.asyncio
    async def test_summary_aggregation(self):
        """Summary correctly sums income/expenses across properties."""
        mock_db = AsyncMock()
        org_id = uuid4()

        acct1 = _make_account(name="Prop A", balance=200000, rental_income=1500, org_id=org_id)
        acct2 = _make_account(name="Prop B", balance=300000, rental_income=2500, org_id=org_id)

        # get_rental_properties call
        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [acct1, acct2]

        # Property A PnL: account lookup then transactions
        acct1_result = Mock()
        acct1_result.scalar_one_or_none.return_value = acct1
        acct1_txns = Mock()
        acct1_txns.all.return_value = [
            _make_transaction(date(2024, 1, 15), 12000, "Rent"),
            _make_transaction(date(2024, 6, 1), -3000, "Repairs"),
        ]

        # Property B PnL: account lookup then transactions
        acct2_result = Mock()
        acct2_result.scalar_one_or_none.return_value = acct2
        acct2_txns = Mock()
        acct2_txns.all.return_value = [
            _make_transaction(date(2024, 1, 15), 24000, "Rent"),
            _make_transaction(date(2024, 6, 1), -5000, "Repairs"),
        ]

        mock_db.execute.side_effect = [
            list_result,
            acct1_result,
            acct1_txns,
            acct2_result,
            acct2_txns,
        ]

        service = RentalPropertyService(mock_db)
        result = await service.get_all_properties_summary(org_id, 2024)

        assert result["property_count"] == 2
        assert result["total_income"] == 36000.0
        assert result["total_expenses"] == 8000.0
        assert result["total_net_income"] == 28000.0
        assert result["year"] == 2024

    @pytest.mark.asyncio
    async def test_avg_cap_rate(self):
        """Average cap rate is computed across all properties."""
        mock_db = AsyncMock()
        org_id = uuid4()

        acct = _make_account(balance=200000, org_id=org_id)

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = [acct]

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = acct
        txns = Mock()
        txns.all.return_value = [
            _make_transaction(date(2024, 1, 1), 20000, "Rent"),
            _make_transaction(date(2024, 6, 1), -10000, "Expenses"),
        ]

        mock_db.execute.side_effect = [list_result, acct_result, txns]

        service = RentalPropertyService(mock_db)
        result = await service.get_all_properties_summary(org_id, 2024)

        # net=10000, value=200000 => cap_rate = 5.0
        assert abs(result["average_cap_rate"] - 5.0) < 0.1

    @pytest.mark.asyncio
    async def test_no_properties_summary(self):
        """Summary with no properties returns zeros."""
        mock_db = AsyncMock()

        list_result = Mock()
        list_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = list_result

        service = RentalPropertyService(mock_db)
        result = await service.get_all_properties_summary(uuid4(), 2024)

        assert result["property_count"] == 0
        assert result["total_income"] == 0.0
        assert result["total_expenses"] == 0.0
        assert result["average_cap_rate"] == 0.0


@pytest.mark.unit
class TestUpdateRentalFields:
    """Test updating rental-specific fields."""

    @pytest.mark.asyncio
    async def test_update_fields(self):
        """Can update rental fields on an account."""
        mock_db = AsyncMock()
        org_id = uuid4()
        acct = _make_account(org_id=org_id)

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = acct
        mock_db.execute.return_value = acct_result

        service = RentalPropertyService(mock_db)
        result = await service.update_rental_fields(
            organization_id=org_id,
            account_id=acct.id,
            is_rental_property=True,
            rental_monthly_income=Decimal("2500"),
            rental_address="456 Oak Ave",
        )

        assert result["is_rental_property"] is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Returns error when account not found."""
        mock_db = AsyncMock()

        acct_result = Mock()
        acct_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = acct_result

        service = RentalPropertyService(mock_db)
        result = await service.update_rental_fields(
            organization_id=uuid4(),
            account_id=uuid4(),
        )

        assert "error" in result
