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
