"""Expanded unit tests for ReportService — covers execute_report, all query types,
generate_export_csv, and filter branches.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.services.report_service import ReportService

# ── helpers ──────────────────────────────────────────────────────────────────


def _mock_time_row(period, income=100, expenses=-50, count=5):
    row = Mock()
    row.period = period
    row.income = Decimal(str(income))
    row.expenses = Decimal(str(expenses))
    row.count = count
    return row


def _mock_category_row(category="Food", total=100, count=5):
    row = Mock()
    row.category_primary = category
    row.total = Decimal(str(total))
    row.count = count
    return row


def _mock_merchant_row(merchant="Walmart", total=200, count=10):
    row = Mock()
    row.merchant_name = merchant
    row.total = Decimal(str(total))
    row.count = count
    return row


def _mock_account_row(name="Chase Checking", total=500, count=20):
    row = Mock()
    row.name = name
    row.total = Decimal(str(total))
    row.count = count
    return row


# ── _parse_date_range (additional branches) ──────────────────────────────────


@pytest.mark.unit
class TestParseDateRangeAdditional:
    """Cover additional parse branches not in existing tests."""

    def test_custom_range_missing_start(self):
        """Custom range with missing startDate defaults to 30 days ago."""
        start, end = ReportService._parse_date_range(
            {
                "type": "custom",
                "endDate": "2024-06-30",
            }
        )
        assert start == date.today() - timedelta(days=30)
        assert end == date(2024, 6, 30)

    def test_custom_range_missing_end(self):
        """Custom range with missing endDate defaults to today."""
        start, end = ReportService._parse_date_range(
            {
                "type": "custom",
                "startDate": "2024-01-01",
            }
        )
        assert start == date(2024, 1, 1)
        assert end == date.today()

    def test_custom_range_no_dates(self):
        """Custom range with no dates uses defaults."""
        start, end = ReportService._parse_date_range({"type": "custom"})
        assert start == date.today() - timedelta(days=30)
        assert end == date.today()


# ── _execute_time_grouped_query ──────────────────────────────────────────────


@pytest.mark.unit
class TestExecuteTimeGroupedQuery:
    """Test time-grouped query execution."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_monthly_grouping(self, mock_db):
        """Monthly grouping returns formatted results."""
        row = _mock_time_row(period=date(2024, 1, 1), income=200, expenses=-100, count=10)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "monthly")

        assert len(data) == 1
        assert data[0]["name"] == "2024-01-01"
        assert data[0]["income"] == 200.0
        assert data[0]["expenses"] == 100.0
        assert data[0]["net"] == 100.0
        assert data[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_daily_grouping(self, mock_db):
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "daily")
        assert data == []

    @pytest.mark.asyncio
    async def test_weekly_grouping(self, mock_db):
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "weekly")
        assert data == []

    @pytest.mark.asyncio
    async def test_quarterly_grouping(self, mock_db):
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "quarterly")
        assert data == []

    @pytest.mark.asyncio
    async def test_yearly_grouping(self, mock_db):
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "yearly")
        assert data == []

    @pytest.mark.asyncio
    async def test_none_period(self, mock_db):
        """Handle None period gracefully."""
        row = _mock_time_row(period=None, income=0, expenses=0, count=0)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "monthly")

        assert data[0]["name"] == ""

    @pytest.mark.asyncio
    async def test_none_income_expenses(self, mock_db):
        """None income/expenses default to 0."""
        row = Mock()
        row.period = date(2024, 1, 1)
        row.income = None
        row.expenses = None
        row.count = 0
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_time_grouped_query(mock_db, [], "monthly")

        assert data[0]["income"] == 0.0
        assert data[0]["expenses"] == 0.0


# ── _execute_category_query ──────────────────────────────────────────────────


@pytest.mark.unit
class TestExecuteCategoryQuery:
    """Test category-grouped query execution."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_formatted_categories(self, mock_db):
        row = _mock_category_row("Food", 100, 5)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_category_query(mock_db, [], {})

        assert len(data) == 1
        assert data[0]["name"] == "Food"
        assert data[0]["amount"] == 100.0
        assert data[0]["count"] == 5
        assert data[0]["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_percentage_calculation(self, mock_db):
        rows = [
            _mock_category_row("Food", 300, 3),
            _mock_category_row("Travel", 100, 1),
        ]
        result_mock = Mock()
        result_mock.all.return_value = rows
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_category_query(mock_db, [], {})

        assert data[0]["percentage"] == 75.0
        assert data[1]["percentage"] == 25.0

    @pytest.mark.asyncio
    async def test_none_category_becomes_uncategorized(self, mock_db):
        row = _mock_category_row(None, 50, 1)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_category_query(mock_db, [], {})

        assert data[0]["name"] == "Uncategorized"

    @pytest.mark.asyncio
    async def test_sort_by_count(self, mock_db):
        """config sortBy=count triggers count-based sort."""
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        await ReportService._execute_category_query(mock_db, [], {"sortBy": "count"})
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sort_direction_asc(self, mock_db):
        result_mock = Mock()
        result_mock.all.return_value = []
        mock_db.execute.return_value = result_mock

        await ReportService._execute_category_query(mock_db, [], {"sortDirection": "asc"})
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_zero_total_sum_percentage(self, mock_db):
        """When total_sum is 0, percentage should be 0."""
        row = Mock()
        row.category_primary = "Test"
        row.total = Decimal("0")
        row.count = 1
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_category_query(mock_db, [], {})
        assert data[0]["percentage"] == 0

    @pytest.mark.asyncio
    async def test_none_total(self, mock_db):
        row = Mock()
        row.category_primary = "Test"
        row.total = None
        row.count = 1
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_category_query(mock_db, [], {})
        assert data[0]["amount"] == 0


# ── _execute_merchant_query ──────────────────────────────────────────────────


@pytest.mark.unit
class TestExecuteMerchantQuery:
    """Test merchant-grouped query."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_formatted_merchants(self, mock_db):
        row = _mock_merchant_row("Walmart", 200, 10)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_merchant_query(mock_db, [], {})
        assert data[0]["name"] == "Walmart"
        assert data[0]["amount"] == 200.0

    @pytest.mark.asyncio
    async def test_none_merchant_name(self, mock_db):
        row = _mock_merchant_row(None, 50, 1)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_merchant_query(mock_db, [], {})
        assert data[0]["name"] == "Unknown"


# ── _execute_account_query ───────────────────────────────────────────────────


@pytest.mark.unit
class TestExecuteAccountQuery:
    """Test account-grouped query."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_returns_formatted_accounts(self, mock_db):
        row = _mock_account_row("Chase Checking", 500, 20)
        result_mock = Mock()
        result_mock.all.return_value = [row]
        mock_db.execute.return_value = result_mock

        data = await ReportService._execute_account_query(mock_db, [], {})
        assert data[0]["name"] == "Chase Checking"
        assert data[0]["amount"] == 500.0
        assert data[0]["count"] == 20


# ── execute_report ───────────────────────────────────────────────────────────


@pytest.mark.unit
class TestExecuteReport:
    """Test the main execute_report method."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_category_group_by_default(self, mock_db):
        """Default groupBy is category."""
        with patch.object(
            ReportService,
            "_execute_category_query",
            new_callable=AsyncMock,
            return_value=[{"amount": 100, "count": 5, "name": "Food"}],
        ) as mock_cat:
            result = await ReportService.execute_report(
                mock_db, uuid4(), {"dateRange": {"type": "preset", "preset": "last_30_days"}}
            )
        mock_cat.assert_awaited_once()
        assert "data" in result
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_time_group_by(self, mock_db):
        with patch.object(
            ReportService, "_execute_time_grouped_query", new_callable=AsyncMock, return_value=[]
        ) as mock_time:
            await ReportService.execute_report(mock_db, uuid4(), {"groupBy": "time"})
        mock_time.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_merchant_group_by(self, mock_db):
        with patch.object(
            ReportService, "_execute_merchant_query", new_callable=AsyncMock, return_value=[]
        ) as mock_merchant:
            await ReportService.execute_report(mock_db, uuid4(), {"groupBy": "merchant"})
        mock_merchant.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_account_group_by(self, mock_db):
        with patch.object(
            ReportService, "_execute_account_query", new_callable=AsyncMock, return_value=[]
        ) as mock_acct:
            await ReportService.execute_report(mock_db, uuid4(), {"groupBy": "account"})
        mock_acct.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_group_by_returns_empty(self, mock_db):
        result = await ReportService.execute_report(mock_db, uuid4(), {"groupBy": "unknown"})
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_income_filter(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(
                mock_db, uuid4(), {"filters": {"transactionType": "income"}}
            )
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_expense_filter(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(
                mock_db, uuid4(), {"filters": {"transactionType": "expense"}}
            )
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_amount_filters(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(
                mock_db, uuid4(), {"filters": {"minAmount": 10, "maxAmount": 500}}
            )
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_user_id_filter(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(mock_db, uuid4(), {}, user_id=uuid4())
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_account_ids_filter(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(mock_db, uuid4(), {}, account_ids=[uuid4()])
        assert result["data"] == []

    @pytest.mark.asyncio
    async def test_result_contains_date_range(self, mock_db):
        with patch.object(
            ReportService, "_execute_category_query", new_callable=AsyncMock, return_value=[]
        ):
            result = await ReportService.execute_report(
                mock_db, uuid4(), {"dateRange": {"type": "preset", "preset": "this_year"}}
            )
        assert "startDate" in result["dateRange"]
        assert "endDate" in result["dateRange"]


# ── generate_export_csv ──────────────────────────────────────────────────────


@pytest.mark.unit
class TestGenerateExportCSV:
    """Test CSV export from report templates."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_template_not_found_raises(self, mock_db):
        """Missing template raises ValueError."""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(ValueError, match="not found"):
            await ReportService.generate_export_csv(mock_db, uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_csv_output_with_data(self, mock_db):
        """CSV output contains headers and data from executed report."""
        template = Mock()
        template.config = {"groupBy": "category"}

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = template
        mock_db.execute.return_value = result_mock

        report_data = {
            "data": [
                {"name": "Food", "amount": 100.0, "count": 5},
                {"name": "Travel", "amount": 200.0, "count": 3},
            ],
            "metrics": {},
            "config": {},
            "dateRange": {},
        }

        with patch.object(
            ReportService,
            "execute_report",
            new_callable=AsyncMock,
            return_value=report_data,
        ):
            csv_str = await ReportService.generate_export_csv(mock_db, uuid4(), uuid4())

        assert "name" in csv_str
        assert "Food" in csv_str
        assert "Travel" in csv_str
        lines = csv_str.strip().split("\n")
        assert len(lines) == 3  # 1 header + 2 data

    @pytest.mark.asyncio
    async def test_csv_empty_data(self, mock_db):
        """Empty data produces empty CSV."""
        template = Mock()
        template.config = {}
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = template
        mock_db.execute.return_value = result_mock

        with patch.object(
            ReportService,
            "execute_report",
            new_callable=AsyncMock,
            return_value={"data": [], "metrics": {}, "config": {}, "dateRange": {}},
        ):
            csv_str = await ReportService.generate_export_csv(mock_db, uuid4(), uuid4())

        assert csv_str == ""
