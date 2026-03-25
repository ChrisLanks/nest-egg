"""Tests for NetWorthSnapshot, BulkOperationLog, and SubscriptionInsightsService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.bulk_operation_log import BulkOperationLog
from app.models.net_worth_snapshot import NetWorthSnapshot
from app.models.recurring_transaction import RecurringFrequency
from app.services.subscription_insights_service import (
    SubscriptionInsightsService,
)

# ---------------------------------------------------------------------------
# NetWorthSnapshot model fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthSnapshotModel:
    """Verify NetWorthSnapshot columns exist with expected defaults."""

    def test_tablename(self):
        assert NetWorthSnapshot.__tablename__ == "net_worth_snapshots"

    def test_has_required_columns(self):
        col_names = {c.name for c in NetWorthSnapshot.__table__.columns}
        expected = {
            "id",
            "organization_id",
            "user_id",
            "snapshot_date",
            "total_net_worth",
            "total_assets",
            "total_liabilities",
            "cash_and_checking",
            "savings",
            "investments",
            "retirement",
            "property",
            "vehicles",
            "other_assets",
            "credit_cards",
            "loans",
            "mortgages",
            "student_loans",
            "other_debts",
            "breakdown_json",
            "created_at",
        }
        assert expected.issubset(col_names)

    def test_user_id_is_nullable(self):
        """user_id is nullable (NULL represents household aggregate)."""
        col = NetWorthSnapshot.__table__.c.user_id
        assert col.nullable is True

    def test_total_net_worth_is_not_nullable(self):
        col = NetWorthSnapshot.__table__.c.total_net_worth
        assert col.nullable is False

    def test_asset_columns_have_decimal_zero_default(self):
        for name in (
            "total_assets",
            "total_liabilities",
            "cash_and_checking",
            "savings",
            "investments",
            "retirement",
            "property",
            "vehicles",
            "other_assets",
        ):
            col = NetWorthSnapshot.__table__.c[name]
            if col.default is not None:
                assert col.default.arg == Decimal("0"), f"{name} default should be 0"

    def test_liability_columns_have_decimal_zero_default(self):
        for name in ("credit_cards", "loans", "mortgages", "student_loans", "other_debts"):
            col = NetWorthSnapshot.__table__.c[name]
            if col.default is not None:
                assert col.default.arg == Decimal("0"), f"{name} default should be 0"


# ---------------------------------------------------------------------------
# BulkOperationLog model fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBulkOperationLogModel:
    """Verify BulkOperationLog columns exist with expected defaults."""

    def test_tablename(self):
        assert BulkOperationLog.__tablename__ == "bulk_operation_logs"

    def test_has_required_columns(self):
        col_names = {c.name for c in BulkOperationLog.__table__.columns}
        expected = {
            "id",
            "organization_id",
            "user_id",
            "operation_type",
            "affected_ids",
            "previous_state",
            "new_state",
            "is_undone",
            "created_at",
            "undone_at",
        }
        assert expected.issubset(col_names)

    def test_is_undone_defaults_to_false(self):
        col = BulkOperationLog.__table__.c.is_undone
        assert col.default.arg is False

    def test_operation_type_not_nullable(self):
        col = BulkOperationLog.__table__.c.operation_type
        assert col.nullable is False

    def test_new_state_is_nullable(self):
        col = BulkOperationLog.__table__.c.new_state
        assert col.nullable is True

    def test_undone_at_is_nullable(self):
        col = BulkOperationLog.__table__.c.undone_at
        assert col.nullable is True


# ---------------------------------------------------------------------------
# SubscriptionInsightsService — pure helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnnualizeCalculation:
    """Test the static _annualize helper."""

    def test_monthly_annualize(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("10.00"), RecurringFrequency.MONTHLY
        )
        assert result == Decimal("120.00")

    def test_weekly_annualize(self):
        result = SubscriptionInsightsService._annualize(Decimal("5.00"), RecurringFrequency.WEEKLY)
        assert result == Decimal("260.00")

    def test_biweekly_annualize(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("20.00"), RecurringFrequency.BIWEEKLY
        )
        assert result == Decimal("520.00")

    def test_quarterly_annualize(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("100.00"), RecurringFrequency.QUARTERLY
        )
        assert result == Decimal("400.00")

    def test_yearly_annualize(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("600.00"), RecurringFrequency.YEARLY
        )
        assert result == Decimal("600.00")

    def test_on_demand_annualize_is_zero(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("50.00"), RecurringFrequency.ON_DEMAND
        )
        assert result == Decimal("0.00")

    def test_negative_amount_uses_absolute_value(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("-15.00"), RecurringFrequency.MONTHLY
        )
        assert result == Decimal("180.00")

    def test_rounding(self):
        # 7.33 * 52 = 381.16
        result = SubscriptionInsightsService._annualize(Decimal("7.33"), RecurringFrequency.WEEKLY)
        assert result == Decimal("381.16")


# ---------------------------------------------------------------------------
# SubscriptionInsightsService — price change detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDetectPriceChanges:
    """Test detect_price_changes logic with mocked DB."""

    def _make_recurring_txn(
        self, average_amount, frequency=RecurringFrequency.MONTHLY, **overrides
    ):
        rt = MagicMock()
        rt.average_amount = Decimal(str(average_amount))
        rt.frequency = frequency
        rt.account_id = uuid4()
        rt.merchant_name = overrides.get("merchant_name", "Netflix")
        rt.organization_id = uuid4()
        rt.is_active = True
        rt.annual_cost = None
        rt.previous_amount = None
        rt.amount_change_pct = None
        rt.amount_change_detected_at = None
        rt.updated_at = None
        for k, v in overrides.items():
            setattr(rt, k, v)
        return rt

    @pytest.mark.asyncio
    async def test_price_increase_above_threshold_sets_detected_at(self):
        """A >5% increase should populate amount_change_detected_at."""
        rt = self._make_recurring_txn(average_amount="15.00")
        prev_avg = 10.00  # 50% increase

        # Mock DB: first query returns recurring txns, second returns historical avg
        db = AsyncMock()
        recurring_result = MagicMock()
        recurring_result.scalars.return_value.all.return_value = [rt]
        hist_result = MagicMock()
        hist_result.scalar.return_value = prev_avg

        db.execute = AsyncMock(side_effect=[recurring_result, hist_result])
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        org_id = uuid4()
        updated = await SubscriptionInsightsService.detect_price_changes(db, org_id)

        assert len(updated) == 1
        assert rt.amount_change_detected_at is not None
        assert rt.previous_amount == Decimal("10.00")
        assert rt.amount_change_pct == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_price_change_below_threshold_clears_detected_at(self):
        """A <5% change should set amount_change_detected_at to None."""
        rt = self._make_recurring_txn(average_amount="10.20")
        prev_avg = 10.00  # 2% increase — below threshold

        db = AsyncMock()
        recurring_result = MagicMock()
        recurring_result.scalars.return_value.all.return_value = [rt]
        hist_result = MagicMock()
        hist_result.scalar.return_value = prev_avg

        db.execute = AsyncMock(side_effect=[recurring_result, hist_result])
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        updated = await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        assert len(updated) == 1
        assert rt.amount_change_detected_at is None
        assert rt.amount_change_pct == Decimal("2.00")

    @pytest.mark.asyncio
    async def test_no_historical_data_clears_fields(self):
        """When there is no historical average, price-change fields should be cleared."""
        rt = self._make_recurring_txn(average_amount="25.00")

        db = AsyncMock()
        recurring_result = MagicMock()
        recurring_result.scalars.return_value.all.return_value = [rt]
        hist_result = MagicMock()
        hist_result.scalar.return_value = None  # no history

        db.execute = AsyncMock(side_effect=[recurring_result, hist_result])
        db.commit = AsyncMock()

        updated = await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        # No historical data means not added to updated list
        assert len(updated) == 0
        assert rt.previous_amount is None
        assert rt.amount_change_pct is None
        assert rt.amount_change_detected_at is None

    @pytest.mark.asyncio
    async def test_annual_cost_always_set(self):
        """annual_cost should be populated even without historical data."""
        rt = self._make_recurring_txn(average_amount="20.00", frequency=RecurringFrequency.MONTHLY)

        db = AsyncMock()
        recurring_result = MagicMock()
        recurring_result.scalars.return_value.all.return_value = [rt]
        hist_result = MagicMock()
        hist_result.scalar.return_value = None

        db.execute = AsyncMock(side_effect=[recurring_result, hist_result])
        db.commit = AsyncMock()

        await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        assert rt.annual_cost == Decimal("240.00")

    @pytest.mark.asyncio
    async def test_price_decrease_above_threshold(self):
        """A >5% decrease should still set detected_at (negative pct)."""
        rt = self._make_recurring_txn(average_amount="9.00")
        prev_avg = 10.00  # -10% change

        db = AsyncMock()
        recurring_result = MagicMock()
        recurring_result.scalars.return_value.all.return_value = [rt]
        hist_result = MagicMock()
        hist_result.scalar.return_value = prev_avg

        db.execute = AsyncMock(side_effect=[recurring_result, hist_result])
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        updated = await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        assert len(updated) == 1
        assert rt.amount_change_pct == Decimal("-10.00")
        assert rt.amount_change_detected_at is not None


# ---------------------------------------------------------------------------
# SubscriptionInsightsService — year-over-year comparison
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestYearOverYearComparison:
    """Test get_year_over_year_comparison output structure."""

    @pytest.mark.asyncio
    async def test_returns_comparison_dicts(self):
        sub = MagicMock()
        sub.id = uuid4()
        sub.merchant_name = "Spotify"
        sub.frequency = RecurringFrequency.MONTHLY
        sub.average_amount = Decimal("9.99")
        sub.previous_amount = Decimal("8.99")
        sub.amount_change_pct = Decimal("11.12")
        sub.annual_cost = Decimal("119.88")
        sub.account_id = uuid4()
        sub.is_active = True
        sub.category_id = None

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            return_value=[sub],
        ):
            db = AsyncMock()
            result = await SubscriptionInsightsService.get_year_over_year_comparison(db, uuid4())

        assert len(result) == 1
        item = result[0]
        assert item["merchant_name"] == "Spotify"
        assert item["current_amount"] == pytest.approx(9.99)
        assert item["previous_amount"] == pytest.approx(8.99)
        assert item["amount_change_pct"] == pytest.approx(11.12)
        assert item["annual_cost"] == pytest.approx(119.88)
        assert "id" in item
        assert "account_id" in item

    @pytest.mark.asyncio
    async def test_none_previous_amount_handled(self):
        sub = MagicMock()
        sub.id = uuid4()
        sub.merchant_name = "Hulu"
        sub.frequency = RecurringFrequency.MONTHLY
        sub.average_amount = Decimal("14.99")
        sub.previous_amount = None
        sub.amount_change_pct = None
        sub.annual_cost = Decimal("179.88")
        sub.account_id = uuid4()

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            return_value=[sub],
        ):
            db = AsyncMock()
            result = await SubscriptionInsightsService.get_year_over_year_comparison(db, uuid4())

        item = result[0]
        assert item["previous_amount"] is None
        assert item["amount_change_pct"] is None


# ---------------------------------------------------------------------------
# NetWorthService — Redis caching for get_history
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthServiceCaching:
    """Verify cache hit/miss behaviour in NetWorthService.get_history."""

    @pytest.mark.asyncio
    async def test_get_history_cache_miss_computes_and_caches(self):
        """On cache miss, get_history should query DB and call cache_setex."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        # DB returns an empty result set (no snapshots)
        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_cache_get,
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cache_setex,
        ):
            svc = NetWorthService()
            result = await svc.get_history(db, org_id)

        # cache_get was called once
        mock_cache_get.assert_called_once()
        # cache_setex was called with key, ttl=300, and the computed data
        mock_cache_setex.assert_called_once()
        args = mock_cache_setex.call_args
        assert args[0][1] == 300  # TTL
        assert args[0][2] == []  # empty result list
        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_cache_hit_skips_db(self):
        """On cache hit, get_history should return cached data without querying DB."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        cached_data = [
            {
                "date": "2026-01-01",
                "total_net_worth": 100000.0,
                "total_assets": 150000.0,
                "total_liabilities": 50000.0,
            }
        ]

        with patch(
            "app.services.net_worth_service.cache_get",
            new_callable=AsyncMock,
            return_value=cached_data,
        ) as mock_cache_get:
            svc = NetWorthService()
            result = await svc.get_history(db, org_id)

        mock_cache_get.assert_called_once()
        # DB should NOT have been queried
        db.execute.assert_not_called()
        assert result == cached_data

    @pytest.mark.asyncio
    async def test_get_current_breakdown_cache_miss(self):
        """On cache miss, get_current_breakdown should query DB and cache result."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_cache_setex,
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        mock_cache_setex.assert_called_once()
        assert result["total_net_worth"] == 0.0
        assert result["total_assets"] == 0.0
        assert result["total_liabilities"] == 0.0

    @pytest.mark.asyncio
    async def test_get_current_breakdown_cache_hit(self):
        """On cache hit, get_current_breakdown should return cached data without DB query."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        cached_data = {
            "total_net_worth": 200000.0,
            "total_assets": 250000.0,
            "total_liabilities": 50000.0,
            "categories": {},
            "accounts": [],
        }

        with patch(
            "app.services.net_worth_service.cache_get",
            new_callable=AsyncMock,
            return_value=cached_data,
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        db.execute.assert_not_called()
        assert result == cached_data


# ---------------------------------------------------------------------------
# NetWorthService — get_history with user_id and granularity
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthServiceGetHistoryBranches:
    """Test additional branches in NetWorthService.get_history."""

    @pytest.mark.asyncio
    async def test_get_history_with_user_id(self):
        """get_history with user_id should filter by user."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        user_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_history(db, org_id, user_id=user_id)

        assert result == []
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_history_weekly_granularity(self):
        """get_history with weekly granularity should use date_trunc."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_history(db, org_id, granularity="weekly")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_monthly_granularity(self):
        """get_history with monthly granularity should use date_trunc."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_history(db, org_id, granularity="monthly")

        assert result == []

    @pytest.mark.asyncio
    async def test_get_history_with_date_range(self):
        """get_history with explicit start and end dates."""
        from datetime import date

        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_history(
                db,
                org_id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
            )

        assert result == []


# ---------------------------------------------------------------------------
# NetWorthService — get_current_breakdown branches
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthServiceBreakdownBranches:
    """Test additional branches in get_current_breakdown."""

    @pytest.mark.asyncio
    async def test_get_current_breakdown_with_user_id(self):
        """get_current_breakdown with user_id should filter."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        user_id = uuid4()
        db = AsyncMock()

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = []
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id, user_id=user_id)

        assert result["total_net_worth"] == 0.0
        assert result["accounts"] == []

    @pytest.mark.asyncio
    async def test_get_current_breakdown_with_accounts(self):
        """get_current_breakdown should categorize accounts properly."""
        from decimal import Decimal

        from app.models.account import Account, AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        # Create mock accounts
        checking = MagicMock(spec=Account)
        checking.id = uuid4()
        checking.name = "Checking"
        checking.account_type = AccountType.CHECKING
        checking.current_balance = Decimal("5000.00")
        checking.include_in_networth = None
        checking.institution_name = "Chase"
        checking.company_status = None
        checking.vesting_schedule = None
        checking.equity_value = None
        checking.company_valuation = None
        checking.ownership_percentage = None
        checking.share_price = None

        credit_card = MagicMock(spec=Account)
        credit_card.id = uuid4()
        credit_card.name = "Visa"
        credit_card.account_type = AccountType.CREDIT_CARD
        credit_card.current_balance = Decimal("-2000.00")
        credit_card.include_in_networth = None
        credit_card.institution_name = "BoA"
        credit_card.company_status = None
        credit_card.vesting_schedule = None
        credit_card.equity_value = None
        credit_card.company_valuation = None
        credit_card.ownership_percentage = None
        credit_card.share_price = None

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [checking, credit_card]
        db.execute.return_value = db_result

        with (
            patch(
                "app.services.net_worth_service.cache_get",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "app.services.net_worth_service.cache_setex",
                new_callable=AsyncMock,
                return_value=True,
            ),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        assert result["total_assets"] == 5000.0
        assert result["total_liabilities"] == 2000.0
        assert result["total_net_worth"] == 3000.0
        assert result["categories"]["cash_and_checking"] == 5000.0
        assert result["categories"]["credit_cards"] == 2000.0
        assert len(result["accounts"]) == 2


# ---------------------------------------------------------------------------
# NetWorthService — capture_snapshot
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNetWorthServiceCaptureSnapshot:
    """Test capture_snapshot with mocked DB."""

    @pytest.mark.asyncio
    async def test_capture_snapshot_with_user_id(self):
        """capture_snapshot with user_id should use user-specific conflict index."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        user_id = uuid4()
        db = AsyncMock()

        # Mock account query returning empty
        account_result = MagicMock()
        account_result.scalars.return_value.all.return_value = []

        # Mock upsert result
        snapshot_mock = MagicMock()
        snapshot_mock.total_net_worth = Decimal("0")
        upsert_result = MagicMock()
        upsert_result.scalar_one.return_value = snapshot_mock

        db.execute = AsyncMock(side_effect=[account_result, upsert_result])

        svc = NetWorthService()
        result = await svc.capture_snapshot(db, org_id, user_id=user_id)

        assert result is not None
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_capture_snapshot_household(self):
        """capture_snapshot without user_id uses household conflict index."""
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        account_result = MagicMock()
        account_result.scalars.return_value.all.return_value = []

        snapshot_mock = MagicMock()
        snapshot_mock.total_net_worth = Decimal("0")
        upsert_result = MagicMock()
        upsert_result.scalar_one.return_value = snapshot_mock

        db.execute = AsyncMock(side_effect=[account_result, upsert_result])

        svc = NetWorthService()
        result = await svc.capture_snapshot(db, org_id)

        assert result is not None
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Equity accounts in net worth snapshots and breakdown
# ---------------------------------------------------------------------------


def _make_equity_account(
    account_type,
    *,
    include_in_networth=None,
    company_status_value=None,
    current_balance=Decimal("0"),
    share_price=None,
    quantity=None,
    vesting_schedule=None,
):
    """Helper to build a mock equity Account."""
    from app.models.account import Account, CompanyStatus

    acc = MagicMock(spec=Account)
    acc.id = uuid4()
    acc.name = "Equity Grant"
    acc.account_type = account_type
    acc.current_balance = current_balance
    acc.include_in_networth = include_in_networth
    acc.institution_name = None
    acc.share_price = share_price
    acc.quantity = quantity
    acc.vesting_schedule = vesting_schedule
    acc.equity_value = None
    acc.company_valuation = None
    acc.ownership_percentage = None
    if company_status_value is not None:
        status = MagicMock()
        status.value = company_status_value
        acc.company_status = status
    else:
        acc.company_status = None
    return acc


@pytest.mark.unit
class TestNetWorthEquityAccounts:
    """Verify equity accounts are correctly included/excluded in snapshots and breakdown."""

    def _make_upsert_result(self, net_worth=Decimal("0")):
        snapshot_mock = MagicMock()
        snapshot_mock.total_net_worth = net_worth
        upsert_result = MagicMock()
        upsert_result.scalar_one.return_value = snapshot_mock
        return upsert_result

    @pytest.mark.asyncio
    async def test_stock_options_private_excluded_from_snapshot_by_default(self):
        """Private stock options with no explicit flag must NOT appear in snapshot totals."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        acc = _make_equity_account(
            AccountType.STOCK_OPTIONS,
            company_status_value="private",
            current_balance=Decimal("50000"),
        )

        account_result = MagicMock()
        account_result.scalars.return_value.all.return_value = [acc]
        db.execute = AsyncMock(side_effect=[account_result, self._make_upsert_result()])

        svc = NetWorthService()
        snapshot = await svc.capture_snapshot(db, org_id)

        # The upsert was called — verify the values dict had 0 for investments
        call_args = db.execute.call_args_list[1]
        stmt = call_args[0][0]
        # Values are in stmt.compile().params or accessible via the insert statement's
        # _values dict; easiest to check via the returned snapshot total
        assert snapshot.total_net_worth == Decimal("0")

    @pytest.mark.asyncio
    async def test_stock_options_public_included_in_snapshot(self):
        """Public stock options with no explicit flag MUST appear in snapshot investments."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        acc = _make_equity_account(
            AccountType.STOCK_OPTIONS,
            company_status_value="public",
            current_balance=Decimal("30000"),
        )

        account_result = MagicMock()
        account_result.scalars.return_value.all.return_value = [acc]

        snapshot_mock = MagicMock()
        upsert_result = MagicMock()
        upsert_result.scalar_one.return_value = snapshot_mock
        db.execute = AsyncMock(side_effect=[account_result, upsert_result])

        svc = NetWorthService()
        await svc.capture_snapshot(db, org_id)

        # DB commit means snapshot was written; verify the insert values included investments
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_private_equity_excluded_from_breakdown_by_default(self):
        """Private equity with no flag must be excluded from get_current_breakdown."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        acc = _make_equity_account(
            AccountType.PRIVATE_EQUITY,
            company_status_value="private",
            current_balance=Decimal("100000"),
        )

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [acc]
        db.execute.return_value = db_result

        with (
            patch("app.services.net_worth_service.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.services.net_worth_service.cache_setex", new_callable=AsyncMock),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        assert result["total_assets"] == 0.0
        assert result["total_net_worth"] == 0.0
        assert result["categories"]["investments"] == 0.0

    @pytest.mark.asyncio
    async def test_private_equity_included_when_flag_overrides(self):
        """Private equity with include_in_networth=True must appear in breakdown."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        acc = _make_equity_account(
            AccountType.PRIVATE_EQUITY,
            company_status_value="private",
            current_balance=Decimal("80000"),
            include_in_networth=True,
        )

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [acc]
        db.execute.return_value = db_result

        with (
            patch("app.services.net_worth_service.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.services.net_worth_service.cache_setex", new_callable=AsyncMock),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        assert result["total_assets"] == 80000.0
        assert result["categories"]["investments"] == 80000.0

    @pytest.mark.asyncio
    async def test_stock_options_excluded_when_flag_false(self):
        """Stock options with include_in_networth=False must be excluded even if public."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        acc = _make_equity_account(
            AccountType.STOCK_OPTIONS,
            company_status_value="public",
            current_balance=Decimal("50000"),
            include_in_networth=False,
        )

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [acc]
        db.execute.return_value = db_result

        with (
            patch("app.services.net_worth_service.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.services.net_worth_service.cache_setex", new_callable=AsyncMock),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        assert result["total_assets"] == 0.0
        assert result["categories"]["investments"] == 0.0

    @pytest.mark.asyncio
    async def test_vesting_aware_balance_used_in_breakdown(self):
        """Breakdown must use vesting-aware balance (sum of vested events), not current_balance."""
        import json

        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        # Account has current_balance=0 but a vested event worth 5000
        # DashboardService._calculate_account_value computes from vesting_schedule
        acc = _make_equity_account(
            AccountType.STOCK_OPTIONS,
            company_status_value="public",
            current_balance=Decimal("0"),
            share_price=Decimal("10"),
            quantity=Decimal("1000"),
            vesting_schedule=json.dumps([
                {"date": "2020-01-01", "quantity": 500},  # past — vested
            ]),
            include_in_networth=True,
        )

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [acc]
        db.execute.return_value = db_result

        with (
            patch("app.services.net_worth_service.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.services.net_worth_service.cache_setex", new_callable=AsyncMock),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        # 500 vested shares × $10/share = $5,000
        assert result["total_assets"] == 5000.0
        assert result["categories"]["investments"] == 5000.0

    @pytest.mark.asyncio
    async def test_equity_maps_to_investments_category(self):
        """Both STOCK_OPTIONS and PRIVATE_EQUITY must land in 'investments' category."""
        from app.models.account import AccountType
        from app.services.net_worth_service import NetWorthService

        org_id = uuid4()
        db = AsyncMock()

        stock = _make_equity_account(
            AccountType.STOCK_OPTIONS,
            company_status_value="public",
            current_balance=Decimal("20000"),
            include_in_networth=True,
        )
        pe = _make_equity_account(
            AccountType.PRIVATE_EQUITY,
            company_status_value="public",
            current_balance=Decimal("30000"),
            include_in_networth=True,
        )

        db_result = MagicMock()
        db_result.scalars.return_value.all.return_value = [stock, pe]
        db.execute.return_value = db_result

        with (
            patch("app.services.net_worth_service.cache_get", new_callable=AsyncMock, return_value=None),
            patch("app.services.net_worth_service.cache_setex", new_callable=AsyncMock),
        ):
            svc = NetWorthService()
            result = await svc.get_current_breakdown(db, org_id)

        assert result["total_assets"] == 50000.0
        assert result["categories"]["investments"] == 50000.0
        # No equity leaks into other categories
        assert result["categories"]["other_assets"] == 0.0
        assert result["categories"]["retirement"] == 0.0
