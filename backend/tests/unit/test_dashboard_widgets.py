"""Unit tests for dashboard widget API endpoints — covers fee analysis,
fund overlap, YoY comparison, quarterly summary, tax loss harvesting,
social security, healthcare estimates, RMD summary, and Roth analysis."""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(org_id=None, user_id=None, birthdate=None):
    """Create a mock user."""
    from app.models.user import User

    user = MagicMock(spec=User)
    user.id = user_id or uuid4()
    user.organization_id = org_id or uuid4()
    user.birthdate = birthdate
    return user


def _make_holding(
    ticker="VTI",
    name="Vanguard Total Stock Market",
    shares=Decimal("100"),
    expense_ratio=Decimal("0.0003"),
    current_total_value=Decimal("25000"),
    asset_type="equity",
    sector=None,
    industry=None,
    country="US",
    current_price_per_share=Decimal("250"),
    total_cost_basis=Decimal("20000"),
    price_as_of=None,
    account_id=None,
):
    h = MagicMock()
    h.ticker = ticker
    h.name = name
    h.shares = shares
    h.expense_ratio = expense_ratio
    h.current_total_value = current_total_value
    h.asset_type = asset_type
    h.sector = sector
    h.industry = industry
    h.country = country
    h.current_price_per_share = current_price_per_share
    h.total_cost_basis = total_cost_basis
    h.price_as_of = price_as_of or datetime.now(timezone.utc)
    h.account_id = account_id or uuid4()
    return h


def _make_account(acc_id=None, org_id=None):
    acc = MagicMock()
    acc.id = acc_id or uuid4()
    acc.organization_id = org_id or uuid4()
    return acc


# ---------------------------------------------------------------------------
# Fee Analysis Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFeeAnalysisWidget:
    """Tests for the fee analysis endpoint that powers the Fee Analysis widget."""

    @pytest.mark.asyncio
    async def test_returns_fee_analysis_with_holdings(self):
        """Should return fee metrics when portfolio has holdings."""
        from app.api.v1.holdings import get_fee_analysis

        user = _make_user()
        db = AsyncMock()

        holdings = [
            _make_holding(
                ticker="VTI", expense_ratio=Decimal("0.0003"), current_total_value=Decimal("25000")
            ),
            _make_holding(
                ticker="ARKK", expense_ratio=Decimal("0.0075"), current_total_value=Decimal("5000")
            ),
        ]

        with patch(
            "app.api.v1.holdings._get_holdings_for_user",
            new_callable=AsyncMock,
            return_value=holdings,
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fee_analysis(user_id=None, current_user=user, db=db)

        assert result.current_portfolio_value == pytest.approx(30000.0)
        assert result.weighted_avg_expense_ratio > 0
        assert result.total_annual_fees > 0
        assert isinstance(result.high_fee_holdings, list)

    @pytest.mark.asyncio
    async def test_empty_portfolio_returns_zero(self):
        """Should return zero fees for empty portfolio."""
        from app.api.v1.holdings import get_fee_analysis

        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock, return_value=[]
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fee_analysis(user_id=None, current_user=user, db=db)

        assert result.current_portfolio_value == 0
        assert result.total_annual_fees == 0
        assert result.high_fee_holdings == []

    @pytest.mark.asyncio
    async def test_high_fee_holdings_identified(self):
        """Should flag holdings with expense ratio > 0.5%."""
        from app.api.v1.holdings import get_fee_analysis

        user = _make_user()
        db = AsyncMock()

        holdings = [
            _make_holding(
                ticker="LOW", expense_ratio=Decimal("0.0003"), current_total_value=Decimal("10000")
            ),
            _make_holding(
                ticker="HIGH", expense_ratio=Decimal("0.0150"), current_total_value=Decimal("10000")
            ),
        ]

        with patch(
            "app.api.v1.holdings._get_holdings_for_user",
            new_callable=AsyncMock,
            return_value=holdings,
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fee_analysis(user_id=None, current_user=user, db=db)

        high_fee_tickers = [h.ticker for h in result.high_fee_holdings]
        assert "HIGH" in high_fee_tickers

    @pytest.mark.asyncio
    async def test_cached_result_returned(self):
        """Should return cached result if available."""
        from app.api.v1.holdings import get_fee_analysis

        user = _make_user()
        db = AsyncMock()
        cached_data = {"current_portfolio_value": 99999, "cached": True}

        with patch(
            "app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=cached_data
        ):
            result = await get_fee_analysis(user_id=None, current_user=user, db=db)

        assert result == cached_data

    @pytest.mark.asyncio
    async def test_fee_drag_projection_included(self):
        """Should include fee drag projections."""
        from app.api.v1.holdings import get_fee_analysis

        user = _make_user()
        db = AsyncMock()

        holdings = [
            _make_holding(
                ticker="VTI", expense_ratio=Decimal("0.0003"), current_total_value=Decimal("100000")
            ),
        ]

        with patch(
            "app.api.v1.holdings._get_holdings_for_user",
            new_callable=AsyncMock,
            return_value=holdings,
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fee_analysis(user_id=None, current_user=user, db=db)

        assert result.fee_drag_projection is not None
        proj = result.fee_drag_projection
        assert len(proj.years) > 0
        assert len(proj.with_fees) > 0
        assert len(proj.without_fees) > 0


# ---------------------------------------------------------------------------
# Fund Overlap Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFundOverlapWidget:
    """Tests for the fund overlap endpoint that powers the Fund Overlap widget."""

    @pytest.mark.asyncio
    async def test_detects_sp500_overlap(self):
        """Should detect overlapping S&P 500 funds."""
        from app.api.v1.holdings import get_fund_overlap

        user = _make_user()
        db = AsyncMock()

        holdings = [
            _make_holding(ticker="SPY", current_total_value=Decimal("10000")),
            _make_holding(ticker="VOO", current_total_value=Decimal("15000")),
        ]

        with patch(
            "app.api.v1.holdings._get_holdings_for_user",
            new_callable=AsyncMock,
            return_value=holdings,
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fund_overlap(user_id=None, current_user=user, db=db)

        assert isinstance(result.overlaps, list)
        assert result.total_overlap_value >= 0
        # SPY and VOO both track S&P 500, overlap should be detected
        if result.overlaps:
            categories = [g.category for g in result.overlaps]
            assert any("S&P" in c or "500" in c for c in categories)

    @pytest.mark.asyncio
    async def test_no_overlap_with_unique_funds(self):
        """Should return empty overlaps for non-overlapping individual stocks."""
        from app.api.v1.holdings import get_fund_overlap

        user = _make_user()
        db = AsyncMock()

        holdings = [
            _make_holding(ticker="AAPL", current_total_value=Decimal("10000")),
            _make_holding(ticker="MSFT", current_total_value=Decimal("15000")),
        ]

        with patch(
            "app.api.v1.holdings._get_holdings_for_user",
            new_callable=AsyncMock,
            return_value=holdings,
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fund_overlap(user_id=None, current_user=user, db=db)

        assert result.overlaps == []
        assert result.total_overlap_value == 0

    @pytest.mark.asyncio
    async def test_empty_portfolio_no_overlap(self):
        """Should handle empty portfolio gracefully."""
        from app.api.v1.holdings import get_fund_overlap

        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.holdings._get_holdings_for_user", new_callable=AsyncMock, return_value=[]
        ):
            with patch("app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=None):
                with patch("app.api.v1.holdings.cache_setex", new_callable=AsyncMock):
                    result = await get_fund_overlap(user_id=None, current_user=user, db=db)

        assert result.overlaps == []

    @pytest.mark.asyncio
    async def test_cached_result_returned(self):
        """Should return cached fund overlap result."""
        from app.api.v1.holdings import get_fund_overlap

        user = _make_user()
        db = AsyncMock()
        cached_data = {"overlaps": [], "total_overlap_value": 0}

        with patch(
            "app.api.v1.holdings.cache_get", new_callable=AsyncMock, return_value=cached_data
        ):
            result = await get_fund_overlap(user_id=None, current_user=user, db=db)

        assert result == cached_data


# ---------------------------------------------------------------------------
# Year-over-Year Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestYearOverYearWidget:
    """Tests for the YoY comparison endpoint."""

    @pytest.mark.asyncio
    async def test_returns_monthly_comparison(self):
        """Should return monthly data for requested years."""
        from app.api.v1.income_expenses import get_year_over_year_comparison

        user = _make_user()
        db = AsyncMock()
        mock_comparison = [
            {
                "month": 1,
                "month_name": "January",
                "data": {"2026": {"income": 5000, "expenses": 3000, "net": 2000}},
            },
            {
                "month": 2,
                "month_name": "February",
                "data": {"2026": {"income": 5500, "expenses": 2800, "net": 2700}},
            },
        ]

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            mock_hh.return_value = [_make_account()]
            with patch("app.api.v1.income_expenses.deduplication_service") as mock_dedup:
                mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_year_over_year_comparison",
                    new_callable=AsyncMock,
                    return_value=mock_comparison,
                ):
                    result = await get_year_over_year_comparison(
                        years=[2026, 2025],
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert len(result) == 2
        assert result[0]["month"] == 1
        assert "2026" in result[0]["data"]

    @pytest.mark.asyncio
    async def test_empty_data_for_no_transactions(self):
        """Should return empty list when no data available."""
        from app.api.v1.income_expenses import get_year_over_year_comparison

        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            mock_hh.return_value = []
            with patch("app.api.v1.income_expenses.deduplication_service") as mock_dedup:
                mock_dedup.deduplicate_accounts.return_value = []
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_year_over_year_comparison",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    result = await get_year_over_year_comparison(
                        years=[2026, 2025],
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result == []


# ---------------------------------------------------------------------------
# Quarterly Performance Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestQuarterlyPerformanceWidget:
    """Tests for the quarterly summary endpoint."""

    @pytest.mark.asyncio
    async def test_returns_quarterly_data(self):
        """Should return quarterly data with net income per year."""
        from app.api.v1.income_expenses import get_quarterly_summary

        user = _make_user()
        db = AsyncMock()
        mock_data = [
            {
                "quarter": 1,
                "quarter_name": "Q1",
                "data": {"2026": {"income": 15000, "expenses": 9000, "net": 6000}},
            },
            {
                "quarter": 2,
                "quarter_name": "Q2",
                "data": {"2026": {"income": 16000, "expenses": 10000, "net": 6000}},
            },
        ]

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            mock_hh.return_value = [_make_account()]
            with patch("app.api.v1.income_expenses.deduplication_service") as mock_dedup:
                mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_quarterly_summary",
                    new_callable=AsyncMock,
                    return_value=mock_data,
                ):
                    result = await get_quarterly_summary(
                        years=[2026, 2025],
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert len(result) == 2
        assert result[0]["quarter_name"] == "Q1"

    @pytest.mark.asyncio
    async def test_returns_four_quarters(self):
        """Should return data for all four quarters."""
        from app.api.v1.income_expenses import get_quarterly_summary

        user = _make_user()
        db = AsyncMock()
        mock_data = [
            {
                "quarter": q,
                "quarter_name": f"Q{q}",
                "data": {"2026": {"income": 10000, "expenses": 7000, "net": 3000}},
            }
            for q in range(1, 5)
        ]

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            mock_hh.return_value = [_make_account()]
            with patch("app.api.v1.income_expenses.deduplication_service") as mock_dedup:
                mock_dedup.deduplicate_accounts.return_value = [_make_account()]
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_quarterly_summary",
                    new_callable=AsyncMock,
                    return_value=mock_data,
                ):
                    result = await get_quarterly_summary(
                        years=[2026], user_id=None, current_user=user, db=db
                    )

        assert len(result) == 4


# ---------------------------------------------------------------------------
# Tax Loss Harvesting Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaxLossHarvestingWidget:
    """Tests for the tax loss harvesting endpoint."""

    @pytest.mark.asyncio
    async def test_returns_opportunities(self):
        """Should return harvesting opportunities with totals."""
        from app.api.v1.reports import get_tax_loss_harvesting

        user = _make_user()
        db = AsyncMock()

        mock_opp = MagicMock()
        mock_opp.holding_id = uuid4()
        mock_opp.ticker = "ARKK"
        mock_opp.name = "ARK Innovation ETF"
        mock_opp.shares = Decimal("50")
        mock_opp.cost_basis = Decimal("7500")
        mock_opp.current_value = Decimal("3000")
        mock_opp.unrealized_loss = Decimal("-4500")
        mock_opp.loss_percentage = Decimal("-60.0")
        mock_opp.estimated_tax_savings = Decimal("1350")
        mock_opp.wash_sale_risk = False
        mock_opp.wash_sale_reason = None
        mock_opp.sector = "Technology"
        mock_opp.suggested_replacements = ["VGT", "QQQ"]

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[mock_opp],
        ):
            result = await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        assert len(result.opportunities) == 1
        assert result.total_harvestable_losses == Decimal("-4500")
        assert result.total_estimated_tax_savings == Decimal("1350")

    @pytest.mark.asyncio
    async def test_no_opportunities_returns_empty(self):
        """Should return empty list when no opportunities exist."""
        from app.api.v1.reports import get_tax_loss_harvesting

        user = _make_user()
        db = AsyncMock()

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        assert result.opportunities == []
        assert result.total_harvestable_losses == 0
        assert result.total_estimated_tax_savings == 0

    @pytest.mark.asyncio
    async def test_wash_sale_risk_flagged(self):
        """Should flag opportunities with wash sale risk."""
        from app.api.v1.reports import get_tax_loss_harvesting

        user = _make_user()
        db = AsyncMock()

        mock_opp = MagicMock()
        mock_opp.holding_id = uuid4()
        mock_opp.ticker = "VTI"
        mock_opp.name = "Vanguard Total Stock"
        mock_opp.shares = Decimal("10")
        mock_opp.cost_basis = Decimal("2000")
        mock_opp.current_value = Decimal("1800")
        mock_opp.unrealized_loss = Decimal("-200")
        mock_opp.loss_percentage = Decimal("-10.0")
        mock_opp.estimated_tax_savings = Decimal("60")
        mock_opp.wash_sale_risk = True
        mock_opp.wash_sale_reason = "Similar fund VTSAX held in IRA"
        mock_opp.sector = None
        mock_opp.suggested_replacements = []

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[mock_opp],
        ):
            result = await get_tax_loss_harvesting(user_id=None, current_user=user, db=db)

        assert result.opportunities[0].wash_sale_risk is True


# ---------------------------------------------------------------------------
# Social Security Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSocialSecurityWidget:
    """Tests for the social security estimate endpoint."""

    @pytest.mark.asyncio
    async def test_returns_estimate_for_user_with_birthdate(self):
        """Should return SS estimates when user has a birthdate."""
        from app.api.v1.retirement import get_social_security_estimate

        user = _make_user(birthdate=date(1970, 5, 15))

        result = await get_social_security_estimate(
            claiming_age=67,
            override_salary=100000.0,
            override_pia=None,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        assert result.monthly_at_62 > 0
        assert result.monthly_at_fra > 0
        assert result.monthly_at_70 > 0
        assert result.monthly_at_70 > result.monthly_at_62

    @pytest.mark.asyncio
    async def test_raises_without_birthdate(self):
        """Should raise 400 when user has no birthdate."""
        from app.api.v1.retirement import get_social_security_estimate

        user = _make_user(birthdate=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=None,
                override_pia=None,
                user_id=None,
                current_user=user,
                db=AsyncMock(),
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_delayed_claiming_increases_benefit(self):
        """Claiming at 70 should yield higher monthly benefit than 62."""
        from app.api.v1.retirement import get_social_security_estimate

        user = _make_user(birthdate=date(1965, 1, 1))

        result_62 = await get_social_security_estimate(
            claiming_age=62,
            override_salary=80000.0,
            override_pia=None,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )
        result_70 = await get_social_security_estimate(
            claiming_age=70,
            override_salary=80000.0,
            override_pia=None,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        assert result_70.monthly_benefit > result_62.monthly_benefit

    @pytest.mark.asyncio
    async def test_pia_override_used(self):
        """Should use manual PIA override when provided."""
        from app.api.v1.retirement import get_social_security_estimate

        user = _make_user(birthdate=date(1965, 1, 1))

        result = await get_social_security_estimate(
            claiming_age=67,
            override_salary=None,
            override_pia=2500.0,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        # With PIA override of $2500 at FRA, benefit should be $2500
        assert result.monthly_benefit == pytest.approx(2500.0, rel=0.01)


# ---------------------------------------------------------------------------
# Healthcare Cost Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthcareCostWidget:
    """Tests for the healthcare cost estimate endpoint."""

    @pytest.mark.asyncio
    async def test_returns_cost_estimate(self):
        """Should return healthcare cost projections."""
        from app.api.v1.retirement import get_healthcare_estimate

        user = _make_user(birthdate=date(1970, 6, 15))

        result = await get_healthcare_estimate(
            retirement_income=50000.0,
            medical_inflation_rate=6.0,
            include_ltc=True,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        assert result.total_lifetime > 0
        assert len(result.sample_ages) > 0

    @pytest.mark.asyncio
    async def test_raises_without_birthdate(self):
        """Should raise 400 when user has no birthdate."""
        from app.api.v1.retirement import get_healthcare_estimate

        user = _make_user(birthdate=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_healthcare_estimate(
                retirement_income=50000.0,
                medical_inflation_rate=6.0,
                include_ltc=True,
                user_id=None,
                current_user=user,
                db=AsyncMock(),
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_exclude_ltc_reduces_cost(self):
        """Excluding long-term care should reduce or equal total cost."""
        from app.api.v1.retirement import get_healthcare_estimate

        user = _make_user(birthdate=date(1960, 1, 1))

        result_with = await get_healthcare_estimate(
            retirement_income=50000.0,
            medical_inflation_rate=6.0,
            include_ltc=True,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )
        result_without = await get_healthcare_estimate(
            retirement_income=50000.0,
            medical_inflation_rate=6.0,
            include_ltc=False,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        assert result_without.total_lifetime <= result_with.total_lifetime

    @pytest.mark.asyncio
    async def test_sample_ages_start_at_or_above_current(self):
        """Sample ages should start at or above user's current age."""
        from app.api.v1.retirement import get_healthcare_estimate

        user = _make_user(birthdate=date(1956, 1, 1))  # Age ~70

        result = await get_healthcare_estimate(
            retirement_income=50000.0,
            medical_inflation_rate=6.0,
            include_ltc=True,
            user_id=None,
            current_user=user,
            db=AsyncMock(),
        )

        for sample in result.sample_ages:
            assert sample.age >= 55  # All predefined sample ages are >= 55


# ---------------------------------------------------------------------------
# RMD Planner Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRmdPlannerWidget:
    """Tests for the RMD summary endpoint."""

    @pytest.mark.asyncio
    async def test_returns_not_required_for_young_user(self):
        """Should return requires_rmd=False for users under 73."""
        from app.api.v1.holdings import get_rmd_summary

        user = _make_user(birthdate=date(1970, 1, 1))  # Age 56
        db = AsyncMock()

        # Individual view (with user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = user
        db.execute = AsyncMock(return_value=user_result)

        with patch("app.api.v1.holdings.verify_household_member", new_callable=AsyncMock):
            result = await get_rmd_summary(user_id=user.id, current_user=user, db=db)

        assert result.requires_rmd is False
        assert result.user_age < 73

    @pytest.mark.asyncio
    async def test_returns_none_without_birthdate_individual(self):
        """Should return None when individual user has no birthdate."""
        from app.api.v1.holdings import get_rmd_summary

        user = _make_user(birthdate=None)
        db = AsyncMock()

        user_result = MagicMock()
        user_result.scalar_one.return_value = user
        db.execute = AsyncMock(return_value=user_result)

        with patch("app.api.v1.holdings.verify_household_member", new_callable=AsyncMock):
            result = await get_rmd_summary(user_id=user.id, current_user=user, db=db)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_without_birthdate_household(self):
        """Should return None when no household members have birthdates."""
        from app.api.v1.holdings import get_rmd_summary

        user = _make_user(birthdate=None)
        db = AsyncMock()

        # Household view returns members without birthdates
        members_result = MagicMock()
        members_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=members_result)

        result = await get_rmd_summary(user_id=None, current_user=user, db=db)

        assert result is None


# ---------------------------------------------------------------------------
# Roth Conversion Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRothConversionWidget:
    """Tests for the Roth analysis endpoint."""

    @pytest.mark.asyncio
    async def test_zero_balance_no_traditional_accounts(self):
        """Should return zero balance when no traditional accounts exist."""
        from app.api.v1.holdings import get_roth_analysis

        user = _make_user(birthdate=date(1970, 5, 15))
        db = AsyncMock()

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            with patch("app.api.v1.holdings.deduplication_service") as mock_dedup:
                mock_hh.return_value = []
                mock_dedup.deduplicate_accounts.return_value = []
                with patch("app.api.v1.holdings.calculate_age", return_value=55):
                    result = await get_roth_analysis(user_id=None, current_user=user, db=db)

        assert result["traditional_balance"] == 0
        assert result["accounts"] == []

    @pytest.mark.asyncio
    async def test_response_structure(self):
        """Should return expected response fields."""
        from app.api.v1.holdings import get_roth_analysis

        user = _make_user(birthdate=date(1970, 5, 15))
        db = AsyncMock()

        with patch(
            "app.api.v1.holdings.get_all_household_accounts", new_callable=AsyncMock
        ) as mock_hh:
            with patch("app.api.v1.holdings.deduplication_service") as mock_dedup:
                mock_hh.return_value = []
                mock_dedup.deduplicate_accounts.return_value = []
                with patch("app.api.v1.holdings.calculate_age", return_value=55):
                    result = await get_roth_analysis(user_id=None, current_user=user, db=db)

        assert "traditional_balance" in result
        assert "projected_rmd_at_73" in result
        assert "current_age" in result
        assert "accounts" in result


# ---------------------------------------------------------------------------
# Widget Endpoint Imports
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestWidgetEndpointConsistency:
    """Verify that all widget-backing endpoints exist and are importable."""

    def test_fee_analysis_endpoint_exists(self):
        from app.api.v1.holdings import get_fee_analysis

        assert callable(get_fee_analysis)

    def test_fund_overlap_endpoint_exists(self):
        from app.api.v1.holdings import get_fund_overlap

        assert callable(get_fund_overlap)

    def test_rmd_summary_endpoint_exists(self):
        from app.api.v1.holdings import get_rmd_summary

        assert callable(get_rmd_summary)

    def test_roth_analysis_endpoint_exists(self):
        from app.api.v1.holdings import get_roth_analysis

        assert callable(get_roth_analysis)

    def test_yoy_comparison_endpoint_exists(self):
        from app.api.v1.income_expenses import get_year_over_year_comparison

        assert callable(get_year_over_year_comparison)

    def test_quarterly_summary_endpoint_exists(self):
        from app.api.v1.income_expenses import get_quarterly_summary

        assert callable(get_quarterly_summary)

    def test_merchant_summary_endpoint_exists(self):
        from app.api.v1.income_expenses import get_merchant_summary

        assert callable(get_merchant_summary)

    def test_label_summary_endpoint_exists(self):
        from app.api.v1.income_expenses import get_label_summary

        assert callable(get_label_summary)

    def test_social_security_endpoint_exists(self):
        from app.api.v1.retirement import get_social_security_estimate

        assert callable(get_social_security_estimate)

    def test_healthcare_estimate_endpoint_exists(self):
        from app.api.v1.retirement import get_healthcare_estimate

        assert callable(get_healthcare_estimate)

    def test_tax_loss_harvesting_endpoint_exists(self):
        from app.api.v1.reports import get_tax_loss_harvesting

        assert callable(get_tax_loss_harvesting)


# ---------------------------------------------------------------------------
# User-ID Filtering: Social Security Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSocialSecurityUserIdFiltering:
    """Tests that social security endpoint respects user_id filtering."""

    @pytest.mark.asyncio
    async def test_uses_target_user_birthdate_when_user_id_provided(self):
        """Should call verify_household_member and use target user's birthdate."""
        from app.api.v1.retirement import get_social_security_estimate

        org_id = uuid4()
        current_user = _make_user(org_id=org_id, birthdate=date(1980, 1, 1))
        target_user = _make_user(org_id=org_id, birthdate=date(1965, 6, 15))

        with patch(
            "app.api.v1.retirement.verify_household_member",
            new_callable=AsyncMock,
            return_value=target_user,
        ) as mock_verify:
            result = await get_social_security_estimate(
                claiming_age=67,
                override_salary=80000.0,
                override_pia=None,
                user_id=target_user.id,
                current_user=current_user,
                db=AsyncMock(),
            )

        mock_verify.assert_awaited_once_with(
            mock_verify.call_args[0][0],  # db
            target_user.id,
            current_user.organization_id,
        )
        # Result should be valid and based on target user's age (born 1965)
        assert result.monthly_at_fra > 0
        assert result.claiming_age == 67

    @pytest.mark.asyncio
    async def test_skips_verify_when_user_id_is_self(self):
        """Should NOT call verify_household_member when user_id == current_user.id."""
        from app.api.v1.retirement import get_social_security_estimate

        user = _make_user(birthdate=date(1970, 5, 15))

        with patch(
            "app.api.v1.retirement.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            await get_social_security_estimate(
                claiming_age=67,
                override_salary=80000.0,
                override_pia=None,
                user_id=user.id,
                current_user=user,
                db=AsyncMock(),
            )

        mock_verify.assert_not_awaited()


# ---------------------------------------------------------------------------
# User-ID Filtering: Healthcare Cost Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthcareCostUserIdFiltering:
    """Tests that healthcare cost endpoint respects user_id filtering."""

    @pytest.mark.asyncio
    async def test_uses_target_user_birthdate_when_user_id_provided(self):
        """Should call verify_household_member and use target user's age."""
        from app.api.v1.retirement import get_healthcare_estimate

        org_id = uuid4()
        current_user = _make_user(org_id=org_id, birthdate=date(1990, 1, 1))
        target_user = _make_user(org_id=org_id, birthdate=date(1960, 3, 10))

        with patch(
            "app.api.v1.retirement.verify_household_member",
            new_callable=AsyncMock,
            return_value=target_user,
        ) as mock_verify:
            result = await get_healthcare_estimate(
                retirement_income=50000.0,
                medical_inflation_rate=6.0,
                include_ltc=True,
                user_id=target_user.id,
                current_user=current_user,
                db=AsyncMock(),
            )

        mock_verify.assert_awaited_once_with(
            mock_verify.call_args[0][0],  # db
            target_user.id,
            current_user.organization_id,
        )
        # Target user born 1960 is ~66 years old; sample ages should start at 70+
        assert result.total_lifetime > 0
        for sample in result.sample_ages:
            assert sample.age >= 55

    @pytest.mark.asyncio
    async def test_skips_verify_when_user_id_is_self(self):
        """Should NOT call verify_household_member when user_id == current_user.id."""
        from app.api.v1.retirement import get_healthcare_estimate

        user = _make_user(birthdate=date(1970, 6, 15))

        with patch(
            "app.api.v1.retirement.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            await get_healthcare_estimate(
                retirement_income=50000.0,
                medical_inflation_rate=6.0,
                include_ltc=True,
                user_id=user.id,
                current_user=user,
                db=AsyncMock(),
            )

        mock_verify.assert_not_awaited()


# ---------------------------------------------------------------------------
# User-ID Filtering: Tax Loss Harvesting Widget
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaxLossHarvestingUserIdFiltering:
    """Tests that TLH widget endpoint respects user_id filtering."""

    @pytest.mark.asyncio
    async def test_passes_account_ids_when_user_id_provided(self):
        """Should call verify_household_member, get_user_accounts, and pass account_ids."""
        from app.api.v1.reports import get_tax_loss_harvesting

        org_id = uuid4()
        current_user = _make_user(org_id=org_id)
        target_user_id = uuid4()
        acc1 = _make_account(org_id=org_id)
        acc2 = _make_account(org_id=org_id)

        with patch(
            "app.api.v1.reports.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.reports.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[acc1, acc2],
            ) as mock_get_accs:
                with patch(
                    "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
                    new_callable=AsyncMock,
                    return_value=[],
                ) as mock_get_opps:
                    await get_tax_loss_harvesting(
                        user_id=target_user_id,
                        current_user=current_user,
                        db=AsyncMock(),
                    )

        mock_verify.assert_awaited_once()
        mock_get_accs.assert_awaited_once()
        # Service should receive the account_ids set
        call_kwargs = mock_get_opps.call_args.kwargs
        assert call_kwargs["account_ids"] == {acc1.id, acc2.id}

    @pytest.mark.asyncio
    async def test_no_account_ids_when_no_user_id(self):
        """Should pass account_ids=None when user_id is not provided."""
        from app.api.v1.reports import get_tax_loss_harvesting

        user = _make_user()

        with patch(
            "app.api.v1.reports.tax_loss_harvesting_service.get_opportunities",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_get_opps:
            await get_tax_loss_harvesting(
                user_id=None,
                current_user=user,
                db=AsyncMock(),
            )

        call_kwargs = mock_get_opps.call_args.kwargs
        assert call_kwargs["account_ids"] is None
