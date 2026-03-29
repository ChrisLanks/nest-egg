"""
Tests for dynamic data services:
  - FX rates (Frankfurter API)
  - Mortgage rates including 5/1 ARM (FRED)
  - CD rates (FRED)
  - Student loan rates (studentaid.gov / FRED derivation)
"""

import inspect


# ── FX Service ────────────────────────────────────────────────────────────────


class TestFxService:
    """fx_service.py: Frankfurter live FX rate integration."""

    def test_supported_currencies_list(self):
        from app.services.fx_service import SUPPORTED_CURRENCIES
        assert "USD" in SUPPORTED_CURRENCIES
        assert "EUR" in SUPPORTED_CURRENCIES
        assert "GBP" in SUPPORTED_CURRENCIES
        assert "JPY" in SUPPORTED_CURRENCIES
        assert len(SUPPORTED_CURRENCIES) >= 5

    def test_supported_currencies_function(self):
        from app.services.fx_service import supported_currencies
        result = supported_currencies()
        assert isinstance(result, list)
        assert "USD" in result

    def test_fallback_rates_from_usd_complete(self):
        from app.services.fx_service import _FALLBACK_RATES_FROM_USD, SUPPORTED_CURRENCIES
        for currency in SUPPORTED_CURRENCIES:
            assert currency in _FALLBACK_RATES_FROM_USD, f"Missing fallback rate for {currency}"

    def test_fallback_usd_is_one(self):
        from app.services.fx_service import _FALLBACK_RATES_FROM_USD
        assert _FALLBACK_RATES_FROM_USD["USD"] == 1.0

    def test_fallback_rates_are_positive(self):
        from app.services.fx_service import _FALLBACK_RATES_FROM_USD
        for currency, rate in _FALLBACK_RATES_FROM_USD.items():
            assert rate > 0, f"Non-positive fallback rate for {currency}: {rate}"

    def test_frankfurter_url_configured(self):
        from app.services.fx_service import _FRANKFURTER_URL
        assert "frankfurter" in _FRANKFURTER_URL
        assert _FRANKFURTER_URL.startswith("https://")

    def test_cache_ttl_is_one_hour(self):
        from app.services.fx_service import _CACHE_TTL
        assert _CACHE_TTL == 3600

    def test_get_rate_function_exists(self):
        from app.services.fx_service import get_rate
        import asyncio
        # Same currency → always 1.0 (no network needed)
        result = asyncio.get_event_loop().run_until_complete(get_rate("USD", "USD"))
        assert result == 1.0

    def test_get_all_rates_returns_base_as_one(self):
        """Fallback path: USD base → USD must be 1.0."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from app.services.fx_service import get_all_rates

        with patch("app.services.fx_service.cache_get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.fx_service.cache_setex", new_callable=AsyncMock), \
             patch("httpx.AsyncClient") as mock_client:
            mock_get.return_value = None
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("network error")
            rates = asyncio.get_event_loop().run_until_complete(get_all_rates("USD"))

        assert rates["USD"] == 1.0

    def test_get_all_rates_non_usd_fallback_base(self):
        """Fallback path: EUR base → EUR must be 1.0."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from app.services.fx_service import get_all_rates

        with patch("app.services.fx_service.cache_get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.fx_service.cache_setex", new_callable=AsyncMock), \
             patch("httpx.AsyncClient") as mock_client:
            mock_get.return_value = None
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("network error")
            rates = asyncio.get_event_loop().run_until_complete(get_all_rates("EUR"))

        assert rates["EUR"] == pytest.approx(1.0)

    def test_get_all_rates_uses_cache(self):
        """If cache returns data, httpx should not be called."""
        import asyncio
        from unittest.mock import AsyncMock, patch
        from app.services.fx_service import get_all_rates

        cached = {"USD": 1.0, "EUR": 0.93}
        with patch("app.services.fx_service.cache_get", new_callable=AsyncMock) as mock_get, \
             patch("httpx.AsyncClient") as mock_client:
            mock_get.return_value = cached
            rates = asyncio.get_event_loop().run_until_complete(get_all_rates("USD"))

        mock_client.assert_not_called()
        assert rates == cached


import pytest


# ── Mortgage Rate Service ────────────────────────────────────────────────────


class TestMortgageRateService:
    """mortgage_rate_service.py: ARM rate added."""

    def test_snapshot_has_arm_field(self):
        from app.services.mortgage_rate_service import MortgageRateSnapshot
        snap = MortgageRateSnapshot(
            rate_30yr=0.065,
            rate_15yr=0.060,
            rate_5_1_arm=0.058,
            as_of_date="2025-05-01",
        )
        assert snap.rate_5_1_arm == 0.058

    def test_snapshot_arm_can_be_none(self):
        from app.services.mortgage_rate_service import MortgageRateSnapshot
        snap = MortgageRateSnapshot(
            rate_30yr=0.065,
            rate_15yr=0.060,
            rate_5_1_arm=None,
            as_of_date="2025-05-01",
        )
        assert snap.rate_5_1_arm is None

    def test_fred_5arm_url_configured(self):
        from app.services.mortgage_rate_service import FRED_5ARM_URL
        assert "MORTGAGE5US" in FRED_5ARM_URL
        assert FRED_5ARM_URL.startswith("https://fred.stlouisfed.org")

    def test_get_current_mortgage_rates_returns_snapshot(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.mortgage_rate_service import get_current_mortgage_rates, MortgageRateSnapshot

        async def mock_fetch(url):
            return (0.065, "2025-04-01")

        with patch("app.services.mortgage_rate_service._fetch_latest_fred_rate", side_effect=mock_fetch):
            snap = asyncio.get_event_loop().run_until_complete(get_current_mortgage_rates())

        assert isinstance(snap, MortgageRateSnapshot)
        assert snap.rate_30yr == 0.065
        assert snap.rate_15yr == 0.065
        assert snap.rate_5_1_arm == 0.065

    def test_financial_planning_response_has_arm_field(self):
        """MortgageRateResponse Pydantic model includes rate_5_1_arm."""
        from app.api.v1.financial_planning import MortgageRateResponse
        resp = MortgageRateResponse(
            rate_30yr=0.065,
            rate_15yr=0.060,
            rate_5_1_arm=0.058,
            as_of_date="2025-05-01",
            source="FRED / Freddie Mac",
            your_rate=None,
            rate_comparison=None,
        )
        assert resp.rate_5_1_arm == 0.058


# ── Bond Ladder / CD Rate Service ────────────────────────────────────────────


class TestCdRateService:
    """bond_ladder_service.py: live CD rates from FRED."""

    def test_get_live_cd_rates_function_exists(self):
        from app.services.bond_ladder_service import get_live_cd_rates
        assert callable(get_live_cd_rates)

    def test_fred_cd_urls_configured(self):
        from app.services.bond_ladder_service import FRED_CD_6MO_URL, FRED_CD_1YR_URL
        assert "CD6NRNJ" in FRED_CD_6MO_URL
        assert "CD1YEAR" in FRED_CD_1YR_URL

    def test_get_live_cd_rates_returns_dict(self):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from app.services.bond_ladder_service import get_live_cd_rates

        with patch("app.services.bond_ladder_service._fetch_fred_rate", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None
            rates = asyncio.get_event_loop().run_until_complete(get_live_cd_rates())

        assert "6_month" in rates
        assert "1_year" in rates

    def test_get_live_cd_rates_uses_fred_values(self):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from app.services.bond_ladder_service import get_live_cd_rates

        call_count = 0

        async def mock_fetch(url):
            nonlocal call_count
            call_count += 1
            return 0.045

        with patch("app.services.bond_ladder_service._fetch_fred_rate", side_effect=mock_fetch):
            rates = asyncio.get_event_loop().run_until_complete(get_live_cd_rates())

        assert rates["6_month"] == 0.045
        assert rates["1_year"] == 0.045

    def test_estimate_cd_rates_accepts_live_cd_rates(self):
        from app.services.bond_ladder_service import estimate_cd_rates
        treasury = {"1_year": 0.045, "2_year": 0.044, "5_year": 0.043, "10_year": 0.042}
        live = {"6_month": 0.046, "1_year": 0.047}
        result = estimate_cd_rates(treasury, live_cd_rates=live)
        assert result["6_month"] == 0.046
        assert result["1_year"] == 0.047

    def test_estimate_cd_rates_live_overrides_spread(self):
        """Live FRED rate should override the spread-based estimate for 1-year."""
        from app.services.bond_ladder_service import estimate_cd_rates
        treasury = {"1_year": 0.040, "2_year": 0.039, "5_year": 0.038, "10_year": 0.037}
        # Spread-based 1yr would be 0.040 + 0.0010 = 0.041
        live = {"6_month": None, "1_year": 0.0500}
        result = estimate_cd_rates(treasury, live_cd_rates=live)
        assert result["1_year"] == pytest.approx(0.0500)


# ── Student Loan Rate Service ────────────────────────────────────────────────


class TestStudentLoanRateService:
    """student_loan_rate_service.py: federal student loan rates."""

    def test_get_student_loan_rates_function_exists(self):
        from app.services.student_loan_rate_service import get_student_loan_rates
        assert callable(get_student_loan_rates)

    def test_student_loan_rates_model(self):
        from app.services.student_loan_rate_service import StudentLoanRates
        rates = StudentLoanRates(
            academic_year="2025-26",
            undergrad_subsidized=6.53,
            undergrad_unsubsidized=6.53,
            grad_unsubsidized=8.08,
            parent_plus=9.08,
            grad_plus=9.08,
            derived=False,
        )
        assert rates.undergrad_subsidized == 6.53
        assert rates.grad_unsubsidized == 8.08

    def test_confirmed_rates_exist_for_recent_years(self):
        from app.services.student_loan_rate_service import _CONFIRMED_RATES
        assert 2024 in _CONFIRMED_RATES
        assert "undergrad_subsidized" in _CONFIRMED_RATES[2024]
        assert "grad_unsubsidized" in _CONFIRMED_RATES[2024]
        assert "parent_plus" in _CONFIRMED_RATES[2024]

    def test_confirmed_rates_within_valid_range(self):
        """All confirmed rates should be between 2% and 14% (statutory caps apply)."""
        from app.services.student_loan_rate_service import _CONFIRMED_RATES
        for year, rates in _CONFIRMED_RATES.items():
            for loan_type, rate in rates.items():
                assert 2.0 <= rate <= 14.0, f"Rate {rate} for {loan_type} ({year}) out of range"

    def test_formula_caps_undergrad_at_8_25(self):
        from app.services.student_loan_rate_service import _apply_formula
        # Very high T-note rate → should cap
        result = _apply_formula(10.0)
        assert result["undergrad_subsidized"] == 8.25
        assert result["undergrad_unsubsidized"] == 8.25

    def test_formula_caps_grad_at_9_50(self):
        from app.services.student_loan_rate_service import _apply_formula
        result = _apply_formula(10.0)
        assert result["grad_unsubsidized"] == 9.50

    def test_formula_caps_plus_at_10_50(self):
        from app.services.student_loan_rate_service import _apply_formula
        result = _apply_formula(10.0)
        assert result["parent_plus"] == 10.50

    def test_formula_normal_case(self):
        from app.services.student_loan_rate_service import _apply_formula
        result = _apply_formula(4.484)
        assert result["undergrad_subsidized"] == pytest.approx(6.53, abs=0.01)

    def test_returns_confirmed_rates_for_known_year(self):
        import asyncio
        from unittest.mock import patch
        import datetime
        from app.services.student_loan_rate_service import get_student_loan_rates

        # Force academic year to 2024
        with patch("app.services.student_loan_rate_service._current_academic_year", return_value=2024):
            rates = asyncio.get_event_loop().run_until_complete(get_student_loan_rates())

        assert not rates.derived
        assert rates.undergrad_subsidized == 6.53

    def test_academic_year_format(self):
        import asyncio
        from unittest.mock import patch
        from app.services.student_loan_rate_service import get_student_loan_rates

        with patch("app.services.student_loan_rate_service._current_academic_year", return_value=2024):
            rates = asyncio.get_event_loop().run_until_complete(get_student_loan_rates())

        assert rates.academic_year == "2024-25"

    def test_endpoint_registered(self):
        import inspect
        from app.api.v1 import financial_planning
        src = inspect.getsource(financial_planning)
        assert "/student-loan-rates" in src
        assert "StudentLoanRatesResponse" in src
