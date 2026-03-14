"""Unit tests for SubscriptionInsightsService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.recurring_transaction import RecurringFrequency
from app.services.subscription_insights_service import (
    SubscriptionInsightsService,
)


def _make_recurring(
    frequency=RecurringFrequency.MONTHLY,
    average_amount=Decimal("15.99"),
    previous_amount=None,
    amount_change_pct=None,
    amount_change_detected_at=None,
    annual_cost=None,
    category_id=None,
    account_id=None,
):
    rt = MagicMock()
    rt.id = uuid4()
    rt.organization_id = uuid4()
    rt.account_id = account_id or uuid4()
    rt.merchant_name = "Netflix"
    rt.frequency = frequency
    rt.average_amount = average_amount
    rt.previous_amount = previous_amount
    rt.amount_change_pct = amount_change_pct
    rt.amount_change_detected_at = amount_change_detected_at
    rt.annual_cost = annual_cost
    rt.category_id = category_id
    rt.is_active = True
    return rt


class TestAnnualize:
    """Tests for _annualize static method."""

    def test_monthly(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("10.00"), RecurringFrequency.MONTHLY
        )
        assert result == Decimal("120.00")

    def test_weekly(self):
        result = SubscriptionInsightsService._annualize(Decimal("5.00"), RecurringFrequency.WEEKLY)
        assert result == Decimal("260.00")

    def test_biweekly(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("100.00"), RecurringFrequency.BIWEEKLY
        )
        assert result == Decimal("2600.00")

    def test_quarterly(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("30.00"), RecurringFrequency.QUARTERLY
        )
        assert result == Decimal("120.00")

    def test_yearly(self):
        result = SubscriptionInsightsService._annualize(Decimal("99.00"), RecurringFrequency.YEARLY)
        assert result == Decimal("99.00")

    def test_on_demand(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("10.00"), RecurringFrequency.ON_DEMAND
        )
        assert result == Decimal("0.00")

    def test_negative_amount_uses_abs(self):
        result = SubscriptionInsightsService._annualize(
            Decimal("-15.99"), RecurringFrequency.MONTHLY
        )
        assert result == Decimal("191.88")


class TestMonthlyize:
    """Tests for _monthlyize static method."""

    def test_monthly(self):
        result = SubscriptionInsightsService._monthlyize(
            Decimal("10.00"), RecurringFrequency.MONTHLY
        )
        assert result == Decimal("10.00")

    def test_yearly(self):
        result = SubscriptionInsightsService._monthlyize(
            Decimal("120.00"), RecurringFrequency.YEARLY
        )
        assert result == Decimal("10.00")

    def test_on_demand(self):
        result = SubscriptionInsightsService._monthlyize(
            Decimal("50.00"), RecurringFrequency.ON_DEMAND
        )
        assert result == Decimal("0.00")


class TestDetectPriceChanges:
    """Tests for detect_price_changes."""

    @pytest.mark.asyncio
    async def test_no_recurring_transactions(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)
        db.commit = AsyncMock()

        result = await SubscriptionInsightsService.detect_price_changes(db, uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_price_increase_above_threshold(self):
        db = AsyncMock()
        rt = _make_recurring(average_amount=Decimal("20.00"))

        mock_rt_result = MagicMock()
        mock_rt_result.scalars.return_value.all.return_value = [rt]

        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = 15.00  # prev avg was 15, now 20 = 33%

        db.execute = AsyncMock(side_effect=[mock_rt_result, mock_hist_result])
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        assert len(result) == 1
        assert rt.amount_change_detected_at is not None

    @pytest.mark.asyncio
    async def test_price_change_below_threshold(self):
        db = AsyncMock()
        rt = _make_recurring(average_amount=Decimal("15.50"))  # 15.50 vs 15.00 = ~3.3%

        mock_rt_result = MagicMock()
        mock_rt_result.scalars.return_value.all.return_value = [rt]

        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = 15.00

        db.execute = AsyncMock(side_effect=[mock_rt_result, mock_hist_result])
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        result = await SubscriptionInsightsService.detect_price_changes(db, uuid4())

        assert len(result) == 1
        # Below threshold: cleared detection
        assert rt.amount_change_detected_at is None

    @pytest.mark.asyncio
    async def test_no_historical_data(self):
        db = AsyncMock()
        rt = _make_recurring(average_amount=Decimal("15.99"))

        mock_rt_result = MagicMock()
        mock_rt_result.scalars.return_value.all.return_value = [rt]

        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = None

        db.execute = AsyncMock(side_effect=[mock_rt_result, mock_hist_result])
        db.commit = AsyncMock()

        result = await SubscriptionInsightsService.detect_price_changes(db, uuid4())
        assert result == []
        assert rt.previous_amount is None

    @pytest.mark.asyncio
    async def test_zero_previous_avg_clears_fields(self):
        db = AsyncMock()
        rt = _make_recurring(average_amount=Decimal("10.00"))

        mock_rt_result = MagicMock()
        mock_rt_result.scalars.return_value.all.return_value = [rt]

        mock_hist_result = MagicMock()
        mock_hist_result.scalar.return_value = 0.0  # previous avg is 0

        db.execute = AsyncMock(side_effect=[mock_rt_result, mock_hist_result])
        db.commit = AsyncMock()

        result = await SubscriptionInsightsService.detect_price_changes(db, uuid4())
        # 0 avg => no meaningful comparison
        assert result == []


class TestGetAnnualSubscriptionTotal:
    """Tests for get_annual_subscription_total."""

    @pytest.mark.asyncio
    async def test_totals_subscriptions(self):
        db = AsyncMock()
        subs = [
            _make_recurring(frequency=RecurringFrequency.MONTHLY, average_amount=Decimal("10.00")),
            _make_recurring(frequency=RecurringFrequency.YEARLY, average_amount=Decimal("120.00")),
        ]

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            new=AsyncMock(return_value=subs),
        ):
            total = await SubscriptionInsightsService.get_annual_subscription_total(db, uuid4())

        assert total == Decimal("240.00")  # 10*12 + 120*1


class TestGetYearOverYearComparison:
    """Tests for get_year_over_year_comparison."""

    @pytest.mark.asyncio
    async def test_returns_comparison_data(self):
        db = AsyncMock()
        sub = _make_recurring(
            average_amount=Decimal("15.99"),
            previous_amount=Decimal("12.99"),
            amount_change_pct=Decimal("23.09"),
            annual_cost=Decimal("191.88"),
        )

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            new=AsyncMock(return_value=[sub]),
        ):
            result = await SubscriptionInsightsService.get_year_over_year_comparison(db, uuid4())

        assert len(result) == 1
        assert result[0]["merchant_name"] == "Netflix"
        assert result[0]["current_amount"] == 15.99
        assert result[0]["previous_amount"] == 12.99
        assert result[0]["annual_cost"] == 191.88

    @pytest.mark.asyncio
    async def test_no_annual_cost_calculates_it(self):
        db = AsyncMock()
        sub = _make_recurring(
            average_amount=Decimal("10.00"),
            annual_cost=None,
        )

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            new=AsyncMock(return_value=[sub]),
        ):
            result = await SubscriptionInsightsService.get_year_over_year_comparison(db, uuid4())

        assert result[0]["annual_cost"] == 120.0


class TestGetPriceIncreases:
    """Tests for get_price_increases."""

    @pytest.mark.asyncio
    async def test_returns_price_increases(self):
        db = AsyncMock()
        from app.utils.datetime_utils import utc_now

        sub = _make_recurring(
            average_amount=Decimal("20.00"),
            previous_amount=Decimal("15.00"),
            amount_change_pct=Decimal("33.33"),
            amount_change_detected_at=utc_now(),
            annual_cost=Decimal("240.00"),
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sub]
        db.execute = AsyncMock(return_value=mock_result)

        result = await SubscriptionInsightsService.get_price_increases(db, uuid4())

        assert len(result) == 1
        assert result[0]["amount_change_pct"] == 33.33
        assert result[0]["annual_increase"] is not None


class TestGetSubscriptionSummary:
    """Tests for get_subscription_summary."""

    @pytest.mark.asyncio
    async def test_empty_subscriptions(self):
        db = AsyncMock()

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            new=AsyncMock(return_value=[]),
        ):
            result = await SubscriptionInsightsService.get_subscription_summary(db, uuid4())

        assert result["total_count"] == 0
        assert result["monthly_cost"] == 0.0
        assert result["annual_cost"] == 0.0
        assert result["price_increases_count"] == 0
        assert result["price_decreases_count"] == 0

    @pytest.mark.asyncio
    async def test_summary_with_subscriptions(self):
        db = AsyncMock()
        from app.utils.datetime_utils import utc_now

        sub1 = _make_recurring(
            average_amount=Decimal("10.00"),
            amount_change_pct=Decimal("10.00"),
            amount_change_detected_at=utc_now(),
            previous_amount=Decimal("9.00"),
            category_id=uuid4(),
        )
        sub2 = _make_recurring(
            average_amount=Decimal("5.00"),
            amount_change_pct=Decimal("-6.00"),
            amount_change_detected_at=utc_now(),
            category_id=None,
        )

        # Mock category fetch
        mock_cat_result = MagicMock()
        mock_cat_result.all.return_value = [(sub1.category_id, "Entertainment")]
        db.execute = AsyncMock(return_value=mock_cat_result)

        with patch.object(
            SubscriptionInsightsService,
            "_get_active_subscriptions",
            new=AsyncMock(return_value=[sub1, sub2]),
        ):
            result = await SubscriptionInsightsService.get_subscription_summary(db, uuid4())

        assert result["total_count"] == 2
        assert result["price_increases_count"] == 1
        assert result["price_decreases_count"] == 1
        assert len(result["top_categories"]) >= 1
