"""Unit tests for the inflation tracking service (I-Bonds, TIPS, real vs nominal)."""

from datetime import date
from unittest.mock import patch

import pytest

from app.services.inflation_tracking_service import (
    _IBOND_FIXED_RATE_HISTORY,
    _STATIC_CPI_FALLBACK,
    analyze_inflation_linked_accounts,
    calculate_ibond_composite_rate,
    get_current_ibond_fixed_rate,
    nominal_to_real,
    real_to_nominal,
)


@pytest.mark.unit
class TestNominalToReal:
    def test_fisher_equation_basic(self):
        # 7% nominal, 3% inflation → (1.07/1.03) - 1 ≈ 3.88%
        result = nominal_to_real(0.07, 0.03)
        assert result == pytest.approx(0.0388, abs=0.001)

    def test_zero_inflation_returns_nominal(self):
        assert nominal_to_real(0.07, 0.0) == pytest.approx(0.07)

    def test_negative_inflation_deflation(self):
        result = nominal_to_real(0.07, -0.02)
        assert result > 0.07  # real return exceeds nominal under deflation

    def test_round_trip_nominal_real_nominal(self):
        nominal = 0.07
        real = nominal_to_real(nominal, 0.03)
        back = real_to_nominal(real, 0.03)
        assert back == pytest.approx(nominal, abs=1e-6)


@pytest.mark.unit
class TestRealToNominal:
    def test_basic(self):
        # 3.88% real, 3% inflation → ~7% nominal
        result = real_to_nominal(0.0388, 0.03)
        assert result == pytest.approx(0.07, abs=0.001)


@pytest.mark.unit
class TestIBondCompositeRate:
    def test_zero_cpi_only_fixed_rate(self):
        rate = calculate_ibond_composite_rate(0.0, fixed_rate=0.012)
        assert rate == pytest.approx(0.012)

    def test_composite_formula(self):
        # fixed=1.2%, semiannual_cpi=1.5%
        # composite = 0.012 + 2*0.015 + 0.012*0.015 = 0.012 + 0.03 + 0.00018 = 0.04218
        rate = calculate_ibond_composite_rate(0.015, fixed_rate=0.012)
        assert rate == pytest.approx(0.04218, abs=0.0001)

    def test_uses_current_fixed_rate_when_none(self):
        rate = calculate_ibond_composite_rate(0.01, fixed_rate=None)
        assert 0 <= rate <= 0.20  # sanity range


@pytest.mark.unit
class TestGetCurrentIBondFixedRate:
    def test_returns_a_rate_in_valid_range(self):
        rate, is_stale, as_of = get_current_ibond_fixed_rate()
        assert 0.0 <= rate <= 0.10
        assert isinstance(is_stale, bool)
        assert isinstance(as_of, str)

    def test_as_of_is_yyyy_mm_format(self):
        _, _, as_of = get_current_ibond_fixed_rate()
        parts = as_of.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1].isdigit()

    def test_ibond_fixed_rate_history_has_entries(self):
        assert len(_IBOND_FIXED_RATE_HISTORY) >= 5

    def test_all_rates_non_negative(self):
        for key, rate in _IBOND_FIXED_RATE_HISTORY.items():
            assert rate >= 0, f"Negative rate at {key}"


@pytest.mark.unit
class TestStaticCPIFallback:
    def test_has_recent_years(self):
        assert max(_STATIC_CPI_FALLBACK.keys()) >= date.today().year - 1

    def test_all_rates_positive(self):
        for yr, rate in _STATIC_CPI_FALLBACK.items():
            assert rate > 0, f"Non-positive CPI at {yr}"


@pytest.mark.unit
class TestAnalyzeInflationLinkedAccounts:
    def _ibond_acct(self, balance=10_000):
        return {
            "id": "abc",
            "name": "I-Bond Series I",
            "account_type": "i_bond",
            "current_balance": balance,
            "nominal_return": None,
        }

    def _tips_acct(self, balance=20_000, nominal_return=0.05):
        return {
            "id": "def",
            "name": "TIPS ETF",
            "account_type": "tips",
            "current_balance": balance,
            "nominal_return": nominal_return,
        }

    def test_empty_accounts_returns_zero_linked(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([], 100_000)
        assert result.total_inflation_linked == 0.0
        assert result.inflation_linked_pct == 0.0

    def test_ibond_account_included(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([self._ibond_acct(10_000)], 100_000)
        assert result.total_inflation_linked == 10_000
        assert len(result.holdings) == 1
        assert result.holdings[0].account_type == "i_bond"
        assert result.holdings[0].ibond_composite_rate is not None

    def test_tips_account_real_return_computed(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([self._tips_acct(20_000, 0.05)], 100_000)
        holding = result.holdings[0]
        assert holding.real_return is not None
        assert holding.real_return == pytest.approx(nominal_to_real(0.05, 0.03), abs=0.001)

    def test_non_inflation_accounts_excluded(self):
        acct = {"id": "x", "name": "Checking", "account_type": "checking", "current_balance": 5_000, "nominal_return": None}
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([acct], 100_000)
        assert result.total_inflation_linked == 0.0
        assert len(result.holdings) == 0

    def test_estimated_cpi_flag_propagates(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, True)):
            result = analyze_inflation_linked_accounts([self._ibond_acct()], 100_000)
        assert result.cpi_is_estimated is True
        assert result.holdings[0].cpi_is_estimated is True

    def test_data_note_present(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([], 100_000)
        assert len(result.data_note) > 10

    def test_inflation_linked_pct_correct(self):
        with patch("app.services.inflation_tracking_service.get_current_cpi_rate", return_value=(0.03, False)):
            result = analyze_inflation_linked_accounts([self._ibond_acct(10_000)], 100_000)
        assert result.inflation_linked_pct == pytest.approx(10.0)
