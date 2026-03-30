"""Unit tests for dashboard API endpoints — covers get_dashboard_summary,
get_dashboard_data, get_spending_insights, and get_cash_flow_forecast."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.api.v1.dashboard import (
    DashboardData,
    DashboardSummary,
    ForecastDataPoint,
    ForecastSummary,
    SpendingInsight,
    get_cash_flow_forecast,
    get_cash_flow_forecast_summary,
    get_dashboard_data,
    get_dashboard_summary,
    get_spending_insights,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(org_id=None, user_id=None):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id or uuid4()
    user.organization_id = org_id or uuid4()
    return user


def _make_account(acc_id=None):
    """Create a mock account."""
    account = MagicMock()
    account.id = acc_id or uuid4()
    return account


def _make_mock_dashboard_service():
    """Create a mock DashboardService with common methods."""
    service = MagicMock()
    service.get_active_accounts = AsyncMock(return_value=[])
    service.compute_net_worth = MagicMock(return_value=Decimal("10000"))
    service.compute_total_assets = MagicMock(return_value=Decimal("15000"))
    service.compute_total_debts = MagicMock(return_value=Decimal("5000"))
    service.compute_account_balances = MagicMock(return_value=[])
    service.get_spending_and_income = AsyncMock(return_value=(Decimal("2000"), Decimal("5000")))
    service.get_recent_transactions = AsyncMock(return_value=[])
    service.get_expense_by_category = AsyncMock(return_value=[])
    service.get_cash_flow_trend = AsyncMock(return_value=[])
    return service


# ---------------------------------------------------------------------------
# get_dashboard_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDashboardSummary:
    @pytest.mark.asyncio
    async def test_basic_summary(self):
        """Should return dashboard summary with financial metrics."""
        user = _make_user()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]

                    result = await get_dashboard_summary(
                        start_date=None,
                        end_date=None,
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert isinstance(result, DashboardSummary)
        assert result.net_worth == 10000.0
        assert result.total_assets == 15000.0
        assert result.total_debts == 5000.0
        assert result.monthly_spending == 2000.0
        assert result.monthly_income == 5000.0
        assert result.monthly_net == 3000.0

    @pytest.mark.asyncio
    async def test_summary_with_date_range(self):
        """Should pass date range to service."""
        user = _make_user()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                    with patch("app.api.v1.dashboard.validate_date_range"):
                        result = await get_dashboard_summary(
                            start_date=date(2024, 1, 1),
                            end_date=date(2024, 12, 31),
                            user_id=None,
                            current_user=user,
                            db=db,
                        )

        assert result.monthly_spending == 2000.0

    @pytest.mark.asyncio
    async def test_summary_with_user_id_filter(self):
        """Should filter by user_id when provided."""
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch("app.api.v1.dashboard.verify_household_member", new_callable=AsyncMock):
                with patch(
                    "app.api.v1.dashboard.get_user_accounts", new_callable=AsyncMock
                ) as mock_ua:
                    mock_ua.return_value = [_make_account()]

                    result = await get_dashboard_summary(
                        start_date=None,
                        end_date=None,
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

        mock_ua.assert_awaited_once()
        assert isinstance(result, DashboardSummary)


# ---------------------------------------------------------------------------
# get_dashboard_data
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetDashboardData:
    @pytest.mark.asyncio
    async def test_returns_complete_dashboard(self):
        """Should return complete dashboard data with all sections."""
        user = _make_user()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                    with patch(
                        "app.api.v1.dashboard.cache_get", new_callable=AsyncMock
                    ) as mock_cache:
                        mock_cache.return_value = None  # Cache miss
                        with patch("app.api.v1.dashboard.cache_setex", new_callable=AsyncMock):
                            result = await get_dashboard_data(
                                start_date=None,
                                end_date=None,
                                user_id=None,
                                current_user=user,
                                db=db,
                            )

        assert isinstance(result, DashboardData)
        assert result.summary.net_worth == 10000.0
        assert result.recent_transactions == []
        assert result.top_expenses == []
        assert result.account_balances == []
        assert result.cash_flow_trend == []

    @pytest.mark.asyncio
    async def test_returns_cached_data(self):
        """Should return cached data when available."""
        user = _make_user()
        db = AsyncMock()

        cached_data = {
            "summary": {
                "net_worth": 99999.0,
                "total_assets": 100000.0,
                "total_debts": 1.0,
                "monthly_spending": 100.0,
                "monthly_income": 200.0,
                "monthly_net": 100.0,
            },
            "recent_transactions": [],
            "top_expenses": [],
            "account_balances": [],
            "cash_flow_trend": [],
        }

        with patch("app.api.v1.dashboard.cache_get", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = cached_data

            result = await get_dashboard_data(
                start_date=None,
                end_date=None,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_handles_cache_failure_gracefully(self):
        """Should continue when cache read fails."""
        user = _make_user()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                    with patch(
                        "app.api.v1.dashboard.cache_get", new_callable=AsyncMock
                    ) as mock_cache:
                        mock_cache.side_effect = Exception("Redis down")
                        with patch("app.api.v1.dashboard.cache_setex", new_callable=AsyncMock):
                            result = await get_dashboard_data(
                                start_date=None,
                                end_date=None,
                                user_id=None,
                                current_user=user,
                                db=db,
                            )

        assert isinstance(result, DashboardData)

    @pytest.mark.asyncio
    async def test_with_user_id_filter(self):
        """Should filter by user_id and verify household member."""
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.verify_household_member", new_callable=AsyncMock
            ) as mock_verify:
                with patch(
                    "app.api.v1.dashboard.get_user_accounts", new_callable=AsyncMock
                ) as mock_ua:
                    mock_ua.return_value = [_make_account()]
                    with patch(
                        "app.api.v1.dashboard.cache_get", new_callable=AsyncMock
                    ) as mock_cache:
                        mock_cache.return_value = None
                        with patch("app.api.v1.dashboard.cache_setex", new_callable=AsyncMock):
                            await get_dashboard_data(
                                start_date=None,
                                end_date=None,
                                user_id=target_user_id,
                                current_user=user,
                                db=db,
                            )

        mock_verify.assert_awaited_once()
        mock_ua.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_with_transactions_and_categories(self):
        """Should process transactions with categories and labels."""
        from datetime import datetime

        user = _make_user()
        db = AsyncMock()

        # Create a mock label with required fields
        mock_label = MagicMock()
        mock_label.id = uuid4()
        mock_label.name = "TestLabel"
        mock_label.color = "#FF0000"

        mock_label_obj = MagicMock()
        mock_label_obj.label = mock_label

        mock_category = MagicMock()
        mock_category.id = uuid4()
        mock_category.name = "Groceries"
        mock_category.color = "#00FF00"
        mock_category.parent_category_id = None
        mock_category.parent = None

        mock_txn = MagicMock()
        mock_txn.id = uuid4()
        mock_txn.organization_id = user.organization_id
        mock_txn.account_id = uuid4()
        mock_txn.external_transaction_id = None
        mock_txn.date = date(2024, 6, 15)
        mock_txn.amount = Decimal("-50.00")
        mock_txn.merchant_name = "Store"
        mock_txn.description = "Grocery shopping"
        mock_txn.category_primary = "Groceries"
        mock_txn.category_detailed = "Supermarkets"
        mock_txn.is_pending = False
        mock_txn.is_transfer = False
        mock_txn.created_at = datetime(2024, 6, 15, 12, 0, 0)
        mock_txn.updated_at = datetime(2024, 6, 15, 12, 0, 0)
        mock_txn.labels = [mock_label_obj]
        mock_txn.category = mock_category
        mock_txn.account = MagicMock()
        mock_txn.account.name = "Checking"
        mock_txn.account.mask = "1234"

        mock_service = _make_mock_dashboard_service()
        mock_service.get_recent_transactions = AsyncMock(return_value=[mock_txn])
        mock_service.get_expense_by_category = AsyncMock(
            return_value=[{"category": "Groceries", "total": 50.0, "count": 1}]
        )
        mock_service.compute_account_balances = MagicMock(
            return_value=[
                {"id": str(uuid4()), "name": "Checking", "type": "checking", "balance": 5000.0}
            ]
        )
        mock_service.get_cash_flow_trend = AsyncMock(
            return_value=[{"month": "2024-06", "income": 5000.0, "expenses": 2000.0}]
        )

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                    with patch(
                        "app.api.v1.dashboard.cache_get", new_callable=AsyncMock
                    ) as mock_cache:
                        mock_cache.return_value = None
                        with patch("app.api.v1.dashboard.cache_setex", new_callable=AsyncMock):
                            result = await get_dashboard_data(
                                start_date=None,
                                end_date=None,
                                user_id=None,
                                current_user=user,
                                db=db,
                            )

        assert len(result.recent_transactions) == 1
        assert result.recent_transactions[0].merchant_name == "Store"
        assert result.recent_transactions[0].category.name == "Groceries"
        assert len(result.top_expenses) == 1
        assert len(result.cash_flow_trend) == 1

    @pytest.mark.asyncio
    async def test_cache_write_failure_doesnt_break_response(self):
        """Should return response even if cache write fails."""
        user = _make_user()
        db = AsyncMock()

        mock_service = _make_mock_dashboard_service()

        with patch("app.api.v1.dashboard.DashboardService", return_value=mock_service):
            with patch(
                "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
            ) as mock_hh:
                mock_hh.return_value = [_make_account()]
                with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                    mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                    with patch(
                        "app.api.v1.dashboard.cache_get", new_callable=AsyncMock
                    ) as mock_cache_get:
                        mock_cache_get.return_value = None
                        with patch(
                            "app.api.v1.dashboard.cache_setex", new_callable=AsyncMock
                        ) as mock_cache_set:
                            mock_cache_set.side_effect = Exception("Redis write fail")

                            result = await get_dashboard_data(
                                start_date=None,
                                end_date=None,
                                user_id=None,
                                current_user=user,
                                db=db,
                            )

        assert isinstance(result, DashboardData)


# ---------------------------------------------------------------------------
# get_spending_insights
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSpendingInsights:
    @pytest.mark.asyncio
    async def test_returns_insights(self):
        """Should return spending insights from InsightsService."""
        user = _make_user()
        db = AsyncMock()

        mock_insights = [
            {
                "type": "spending_increase",
                "title": "Groceries Up",
                "message": "Your grocery spending increased 20%",
                "category": "Groceries",
                "amount": 150.0,
                "percentage_change": 20.0,
                "priority": "medium",
                "icon": "trending-up",
            }
        ]

        with patch(
            "app.api.v1.dashboard.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            mock_hh.return_value = [_make_account()]
            with patch("app.api.v1.dashboard.deduplication_service") as mock_dedup:
                mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                with patch(
                    "app.api.v1.dashboard.InsightsService.generate_insights", new_callable=AsyncMock
                ) as mock_gen:
                    mock_gen.return_value = mock_insights

                    result = await get_spending_insights(
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert len(result) == 1
        assert isinstance(result[0], SpendingInsight)
        assert result[0].type == "spending_increase"
        assert result[0].category == "Groceries"

    @pytest.mark.asyncio
    async def test_insights_with_user_id(self):
        """Should filter by user_id when provided."""
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        with patch(
            "app.api.v1.dashboard.verify_household_member", new_callable=AsyncMock
        ) as mock_verify:
            with patch("app.api.v1.dashboard.get_user_accounts", new_callable=AsyncMock) as mock_ua:
                mock_ua.return_value = [_make_account()]
                with patch(
                    "app.api.v1.dashboard.InsightsService.generate_insights", new_callable=AsyncMock
                ) as mock_gen:
                    mock_gen.return_value = []

                    result = await get_spending_insights(
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

        mock_verify.assert_awaited_once()
        assert result == []


# ---------------------------------------------------------------------------
# get_cash_flow_forecast
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCashFlowForecast:
    @pytest.mark.asyncio
    async def test_returns_forecast(self):
        """Should return forecast data points."""
        user = _make_user()
        db = AsyncMock()

        mock_forecast = [
            {
                "date": "2024-07-01",
                "projected_balance": 5000.0,
                "day_change": -50.0,
                "transaction_count": 3,
                "income": 0.0,
                "expenses": -50.0,
                "transactions": [
                    {"merchant": "Netflix", "amount": -50.0, "category": "Subscriptions",
                     "label": None, "account_id": None, "account_name": None, "event_type": "recurring"}
                ],
            }
        ]

        with patch(
            "app.api.v1.dashboard.ForecastService.generate_forecast", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = mock_forecast

            result = await get_cash_flow_forecast(
                days_ahead=90,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert len(result) == 1
        assert isinstance(result[0], ForecastDataPoint)
        assert result[0].projected_balance == 5000.0
        assert result[0].income == 0.0
        assert result[0].expenses == -50.0
        assert len(result[0].transactions) == 1
        assert result[0].transactions[0].merchant == "Netflix"
        assert result[0].transactions[0].event_type == "recurring"

    @pytest.mark.asyncio
    async def test_forecast_with_user_id(self):
        """Should verify household member when user_id provided."""
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        with patch(
            "app.api.v1.dashboard.verify_household_member", new_callable=AsyncMock
        ) as mock_verify:
            with patch(
                "app.api.v1.dashboard.ForecastService.generate_forecast", new_callable=AsyncMock
            ) as mock_gen:
                mock_gen.return_value = []

                result = await get_cash_flow_forecast(
                    days_ahead=90,
                    user_id=target_user_id,
                    current_user=user,
                    db=db,
                )

        mock_verify.assert_awaited_once()
        assert result == []


# ---------------------------------------------------------------------------
# get_cash_flow_forecast_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCashFlowForecastSummary:
    @pytest.mark.asyncio
    async def test_returns_summary(self):
        """Should return ForecastSummary with totals and breakdowns."""
        user = _make_user()
        db = AsyncMock()

        mock_summary = {
            "total_income": 5500.0,
            "total_expenses": -2200.0,
            "net": 3300.0,
            "by_category": [{"name": "Uncategorized", "amount": 3300.0}],
            "by_merchant": [
                {"name": "Direct Deposit", "amount": 5500.0},
                {"name": "Rent", "amount": -2200.0},
            ],
            "by_label": [],
            "by_account": [{"name": "Checking", "amount": 3300.0}],
        }

        with patch(
            "app.api.v1.dashboard.ForecastService.generate_forecast_summary",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = mock_summary

            result = await get_cash_flow_forecast_summary(
                days_ahead=90,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert isinstance(result, ForecastSummary)
        assert result.total_income == 5500.0
        assert result.total_expenses == -2200.0
        assert result.net == 3300.0
        assert len(result.by_merchant) == 2
        assert result.by_merchant[0].name == "Direct Deposit"
        assert result.by_label == []

    @pytest.mark.asyncio
    async def test_summary_verifies_household_member(self):
        """Should verify household member when user_id provided."""
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        mock_summary = {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net": 0.0,
            "by_category": [],
            "by_merchant": [],
            "by_label": [],
            "by_account": [],
        }

        with patch(
            "app.api.v1.dashboard.verify_household_member", new_callable=AsyncMock
        ) as mock_verify:
            with patch(
                "app.api.v1.dashboard.ForecastService.generate_forecast_summary",
                new_callable=AsyncMock,
                return_value=mock_summary,
            ):
                await get_cash_flow_forecast_summary(
                    days_ahead=90,
                    user_id=target_user_id,
                    current_user=user,
                    db=db,
                )

        mock_verify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_summary_passes_days_ahead(self):
        """Should forward days_ahead parameter to the service."""
        user = _make_user()
        db = AsyncMock()

        empty_summary = {
            "total_income": 0.0, "total_expenses": 0.0, "net": 0.0,
            "by_category": [], "by_merchant": [], "by_label": [], "by_account": [],
        }

        with patch(
            "app.api.v1.dashboard.ForecastService.generate_forecast_summary",
            new_callable=AsyncMock,
            return_value=empty_summary,
        ) as mock_gen:
            await get_cash_flow_forecast_summary(
                days_ahead=30,
                user_id=None,
                current_user=user,
                db=db,
            )

        mock_gen.assert_awaited_once()
        args = mock_gen.call_args.args
        assert args[3] == 30  # days_ahead is 4th positional arg (db, org_id, user_id, days_ahead)

    @pytest.mark.asyncio
    async def test_summary_breakdown_items_are_typed(self):
        """ForecastSummary breakdown items must be ForecastBreakdownItem instances."""
        from app.api.v1.dashboard import ForecastBreakdownItem

        user = _make_user()
        db = AsyncMock()

        mock_summary = {
            "total_income": 1200.0,
            "total_expenses": -500.0,
            "net": 700.0,
            "by_category": [{"name": "Income", "amount": 1200.0}, {"name": "Bills", "amount": -500.0}],
            "by_merchant": [{"name": "Employer", "amount": 1200.0}],
            "by_label": [{"name": "Work", "amount": 1200.0}],
            "by_account": [{"name": "Checking", "amount": 700.0}],
        }

        with patch(
            "app.api.v1.dashboard.ForecastService.generate_forecast_summary",
            new_callable=AsyncMock,
            return_value=mock_summary,
        ):
            result = await get_cash_flow_forecast_summary(
                days_ahead=90,
                user_id=None,
                current_user=user,
                db=db,
            )

        assert all(isinstance(item, ForecastBreakdownItem) for item in result.by_category)
        assert all(isinstance(item, ForecastBreakdownItem) for item in result.by_merchant)
        assert all(isinstance(item, ForecastBreakdownItem) for item in result.by_label)
        assert all(isinstance(item, ForecastBreakdownItem) for item in result.by_account)
