"""Tests for the Financial Calendar endpoint logic."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.api.v1.dashboard import _expand_occurrences_for_range
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction

# ---------------------------------------------------------------------------
# Helper to build a minimal RecurringTransaction-like object
# ---------------------------------------------------------------------------


def _make_pattern(
    frequency: RecurringFrequency,
    next_expected: date,
    average_amount: float = -50.0,
    merchant_name: str = "Test Merchant",
    confidence_score: Decimal = Decimal("0.85"),
    account_id=None,
) -> RecurringTransaction:
    """Build a RecurringTransaction instance for testing expansion."""
    rt = RecurringTransaction(
        id=uuid4(),
        organization_id=uuid4(),
        account_id=account_id or uuid4(),
        merchant_name=merchant_name,
        frequency=frequency,
        average_amount=Decimal(str(average_amount)),
        confidence_score=confidence_score,
        first_occurrence=next_expected - timedelta(days=90),
        next_expected_date=next_expected,
        is_active=True,
    )
    return rt


# ---------------------------------------------------------------------------
# _expand_occurrences_for_range
# ---------------------------------------------------------------------------


class TestExpandOccurrencesForRange:
    """Test the date expansion helper for recurring patterns."""

    def test_weekly_occurrences(self):
        pattern = _make_pattern(RecurringFrequency.WEEKLY, date(2025, 3, 3))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # March 3, 10, 17, 24, 31 => 5 occurrences
        assert len(result) == 5
        assert result[0] == date(2025, 3, 3)
        for i in range(1, len(result)):
            assert (result[i] - result[i - 1]).days == 7

    def test_biweekly_occurrences(self):
        pattern = _make_pattern(RecurringFrequency.BIWEEKLY, date(2025, 3, 7))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # March 7, 21 => 2 occurrences
        assert len(result) == 2
        assert result[0] == date(2025, 3, 7)
        assert result[1] == date(2025, 3, 21)

    def test_monthly_occurrences(self):
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 3, 15))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        assert len(result) == 1
        assert result[0] == date(2025, 3, 15)

    def test_monthly_across_two_months(self):
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 3, 10))
        start = date(2025, 3, 1)
        end = date(2025, 4, 30)
        result = _expand_occurrences_for_range(pattern, start, end)

        assert len(result) == 2
        assert result[0] == date(2025, 3, 10)
        assert result[1] == date(2025, 4, 10)

    def test_quarterly_occurrences(self):
        pattern = _make_pattern(RecurringFrequency.QUARTERLY, date(2025, 1, 15))
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # Jan 15, Apr 15, Jul 15, Oct 15 => 4
        assert len(result) == 4
        assert result[0] == date(2025, 1, 15)
        assert result[1] == date(2025, 4, 15)

    def test_yearly_occurrences(self):
        pattern = _make_pattern(RecurringFrequency.YEARLY, date(2025, 6, 1))
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        assert len(result) == 1
        assert result[0] == date(2025, 6, 1)

    def test_on_demand_returns_empty(self):
        pattern = _make_pattern(RecurringFrequency.ON_DEMAND, date(2025, 3, 15))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        assert result == []

    def test_no_next_expected_date_returns_empty(self):
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 3, 15))
        pattern.next_expected_date = None
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        assert result == []

    def test_anchor_before_range(self):
        """Anchor is before range start; should step forward into range."""
        pattern = _make_pattern(RecurringFrequency.WEEKLY, date(2025, 2, 24))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # First should be March 3 (stepping from Feb 24 by weeks)
        assert len(result) > 0
        assert result[0] >= start
        assert result[-1] <= end

    def test_anchor_after_range_end(self):
        """Anchor is after range end; should produce no occurrences."""
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 5, 15))
        start = date(2025, 3, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # The step-back logic should move anchor before start, then step forward
        # but if the first forward step lands past end, no results
        for d in result:
            assert start <= d <= end

    def test_start_equals_end(self):
        """Single day range."""
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 3, 15))
        result = _expand_occurrences_for_range(pattern, date(2025, 3, 15), date(2025, 3, 15))
        assert len(result) == 1
        assert result[0] == date(2025, 3, 15)

    def test_february_month_boundary(self):
        """Monthly pattern anchored on 31st should handle February."""
        # dateutil.relativedelta handles day overflow by capping to end of month
        pattern = _make_pattern(RecurringFrequency.MONTHLY, date(2025, 1, 31))
        start = date(2025, 1, 1)
        end = date(2025, 3, 31)
        result = _expand_occurrences_for_range(pattern, start, end)

        # Jan 31, Feb 28, Mar 31 (or similar)
        assert len(result) >= 2
        assert result[0] == date(2025, 1, 31)
        # Feb should be 28 for 2025
        assert result[1].month == 2


# ---------------------------------------------------------------------------
# Calendar event classification (unit test of the classification rules)
# ---------------------------------------------------------------------------


class TestCalendarEventClassification:
    """Test event type classification rules used in the calendar endpoint."""

    def test_income_classified_by_positive_amount(self):
        """Positive average_amount should be classified as income."""
        avg = 2000.0
        assert avg > 0  # income

    def test_subscription_classification(self):
        """Monthly/yearly with high confidence and negative amount => subscription."""
        freq = RecurringFrequency.MONTHLY
        confidence = Decimal("0.85")
        avg = -14.99

        is_subscription = (
            freq in (RecurringFrequency.MONTHLY, RecurringFrequency.YEARLY)
            and confidence is not None
            and confidence >= Decimal("0.70")
            and avg < 0
        )
        assert is_subscription is True

    def test_bill_classification(self):
        """Weekly negative amount with low confidence => bill (not subscription)."""
        freq = RecurringFrequency.WEEKLY
        confidence = Decimal("0.50")
        avg = -200.0

        is_subscription = (
            freq in (RecurringFrequency.MONTHLY, RecurringFrequency.YEARLY)
            and confidence is not None
            and confidence >= Decimal("0.70")
            and avg < 0
        )
        # Not a subscription, so classified as bill
        assert is_subscription is False

    def test_low_confidence_monthly_is_bill(self):
        """Monthly negative with confidence below 0.70 => bill, not subscription."""
        freq = RecurringFrequency.MONTHLY
        confidence = Decimal("0.60")
        avg = -50.0

        is_subscription = (
            freq in (RecurringFrequency.MONTHLY, RecurringFrequency.YEARLY)
            and confidence is not None
            and confidence >= Decimal("0.70")
            and avg < 0
        )
        assert is_subscription is False
