"""Unit tests for fee analysis and fund overlap endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.api.v1.holdings import (
    _compute_fee_drag_projection,
    get_fee_analysis,
    get_fund_overlap,
)
from app.models.holding import Holding
from app.models.user import User


def _make_user(org_id=None):
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = org_id or uuid4()
    return user


def _make_holding(ticker, value, expense_ratio=0.0, name=None):
    h = Mock(spec=Holding)
    h.ticker = ticker
    h.name = name or ticker
    h.current_total_value = Decimal(str(value))
    h.expense_ratio = Decimal(str(expense_ratio))
    h.account_id = uuid4()
    return h


@pytest.mark.unit
class TestComputeFeeDragProjection:
    """Test _compute_fee_drag_projection helper."""

    def test_basic_projection(self):
        """Fee drag grows with time as compounding takes effect."""
        result = _compute_fee_drag_projection(100000, 0.01, [5, 10, 20, 30])

        assert result.years == [5, 10, 20, 30]
        assert len(result.with_fees) == 4
        assert len(result.without_fees) == 4
        assert len(result.fee_cost) == 4

        # Without fees should always be >= with fees
        for wf, nf in zip(result.with_fees, result.without_fees):
            assert nf >= wf

        # Fee cost should increase over time
        for i in range(len(result.fee_cost) - 1):
            assert result.fee_cost[i + 1] > result.fee_cost[i]

    def test_zero_expense_ratio(self):
        """Zero expense ratio means no fee cost."""
        result = _compute_fee_drag_projection(50000, 0.0, [10])

        assert result.fee_cost[0] == 0.0
        assert result.with_fees[0] == result.without_fees[0]

    def test_zero_portfolio_value(self):
        """Zero portfolio should produce all zeros."""
        result = _compute_fee_drag_projection(0, 0.01, [5, 10])

        assert result.with_fees == [0.0, 0.0]
        assert result.without_fees == [0.0, 0.0]
        assert result.fee_cost == [0.0, 0.0]

    def test_projection_math_at_5_years(self):
        """Verify exact math: 7% return, 1% ER, $100k, 5 years."""
        pv = 100000
        er = 0.01
        result = _compute_fee_drag_projection(pv, er, [5])

        expected_no_fees = round(pv * (1.07**5), 2)
        expected_with_fees = round(pv * (1.06**5), 2)

        assert result.without_fees[0] == expected_no_fees
        assert result.with_fees[0] == expected_with_fees
        assert result.fee_cost[0] == round(expected_no_fees - expected_with_fees, 2)


@pytest.mark.unit
class TestGetFeeAnalysis:
    """Test get_fee_analysis endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_empty_portfolio(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Empty portfolio returns zero values."""
        mock_get_holdings.return_value = []

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert result.current_portfolio_value == 0
        assert result.weighted_avg_expense_ratio == 0
        assert result.total_annual_fees == 0
        assert result.fee_drag_projection.years == [5, 10, 20, 30]
        assert result.high_fee_holdings == []

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_weighted_expense_ratio(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Weighted ER calculated correctly across holdings."""
        mock_get_holdings.return_value = [
            _make_holding("VTI", 80000, 0.0003),
            _make_holding("ARKK", 20000, 0.0075),
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        # Weighted ER: (80000 * 0.0003 + 20000 * 0.0075) / 100000 = (24 + 150) / 100000 = 0.00174
        assert result.current_portfolio_value == 100000.0
        assert abs(result.weighted_avg_expense_ratio - 0.00174) < 0.0001
        # Total annual fees = 80000*0.0003 + 20000*0.0075 = 24 + 150 = 174
        assert abs(result.total_annual_fees - 174.0) < 1.0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_high_fee_detection(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Holdings with ER > 0.5% are flagged as high-fee."""
        mock_get_holdings.return_value = [
            _make_holding("VTI", 50000, 0.0003),  # Low fee, should not be flagged
            _make_holding("ARKK", 30000, 0.0075),  # High fee
            _make_holding("ARKW", 20000, 0.0068),  # High fee
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.high_fee_holdings) == 2
        tickers = {h.ticker for h in result.high_fee_holdings}
        assert tickers == {"ARKK", "ARKW"}
        # Sorted by ER desc
        assert (
            result.high_fee_holdings[0].expense_ratio >= result.high_fee_holdings[1].expense_ratio
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_low_cost_alternatives(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Low-cost alternatives suggested for known high-fee funds."""
        mock_get_holdings.return_value = [
            _make_holding("ARKK", 50000, 0.0075),
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.low_cost_alternatives) >= 1
        alt = result.low_cost_alternatives[0]
        assert alt.original == "ARKK"
        assert alt.alternative == "VTI"
        assert alt.annual_savings > 0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_no_alternatives_for_already_low_cost(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """No alternatives suggested for already-low-cost funds."""
        mock_get_holdings.return_value = [
            _make_holding("VTI", 100000, 0.0003),
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.low_cost_alternatives) == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_fee_drag_projection_present(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Fee drag projection is computed for non-empty portfolio."""
        mock_get_holdings.return_value = [
            _make_holding("VTI", 100000, 0.001),
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert result.fee_drag_projection.years == [5, 10, 20, 30]
        assert all(fc > 0 for fc in result.fee_drag_projection.fee_cost)

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_duplicate_tickers_aggregated(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Same ticker in multiple accounts is aggregated."""
        mock_get_holdings.return_value = [
            _make_holding("VTI", 50000, 0.0003),
            _make_holding("VTI", 30000, 0.0003),
        ]

        result = await get_fee_analysis(user_id=None, current_user=mock_user, db=mock_db)

        assert result.current_portfolio_value == 80000.0


@pytest.mark.unit
class TestGetFundOverlap:
    """Test get_fund_overlap endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        return _make_user()

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_detects_sp500_overlap(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Two S&P 500 funds should be detected as overlap."""
        mock_get_holdings.return_value = [
            _make_holding("SPY", 50000, 0.0009),
            _make_holding("VOO", 30000, 0.0003),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 1
        overlap = result.overlaps[0]
        assert overlap.category == "S&P 500"
        assert set(overlap.holdings) == {"SPY", "VOO"}
        assert overlap.total_value == 80000.0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_no_overlap_with_single_per_category(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Single fund per category means no overlap detected."""
        mock_get_holdings.return_value = [
            _make_holding("SPY", 50000, 0.0009),
            _make_holding("BND", 30000, 0.0003),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 0
        assert result.total_overlap_value == 0.0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_empty_portfolio_no_overlap(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Empty portfolio returns no overlaps."""
        mock_get_holdings.return_value = []

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 0
        assert result.total_overlap_value == 0.0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_multiple_overlap_groups(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Multiple categories can each have overlapping holdings."""
        mock_get_holdings.return_value = [
            _make_holding("SPY", 40000, 0.0009),
            _make_holding("VOO", 20000, 0.0003),
            _make_holding("BND", 15000, 0.0003),
            _make_holding("AGG", 10000, 0.0003),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 2
        categories = {g.category for g in result.overlaps}
        assert "S&P 500" in categories
        assert "Total US Bond Market" in categories
        assert result.total_overlap_value == 85000.0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_overlaps_sorted_by_value_desc(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Overlap groups sorted by total value descending."""
        mock_get_holdings.return_value = [
            _make_holding("BND", 10000, 0.0003),
            _make_holding("AGG", 5000, 0.0003),
            _make_holding("SPY", 50000, 0.0009),
            _make_holding("VOO", 40000, 0.0003),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 2
        assert result.overlaps[0].total_value >= result.overlaps[1].total_value

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_unknown_tickers_ignored(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Tickers not in FUND_INDEX_MAP are excluded from overlap detection."""
        mock_get_holdings.return_value = [
            _make_holding("AAPL", 50000, 0.0),
            _make_holding("MSFT", 30000, 0.0),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock)
    @patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None)
    @patch("app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock)
    async def test_case_insensitive_ticker_matching(
        self, mock_get_holdings, mock_cache_get, mock_cache_setex, mock_db, mock_user
    ):
        """Tickers are matched case-insensitively."""
        mock_get_holdings.return_value = [
            _make_holding("spy", 50000, 0.0009),
            _make_holding("voo", 30000, 0.0003),
        ]

        result = await get_fund_overlap(user_id=None, current_user=mock_user, db=mock_db)

        assert len(result.overlaps) == 1
        assert result.overlaps[0].category == "S&P 500"
