"""Tests for the pluggable state tax rate provider system.

Covers:
- StaticStateTaxProvider.get_rate() for CA, TX (0.0), NY
- StaticStateTaxProvider.get_brackets() single-bracket structure
- TaxGraphsProvider graceful fallback when network unavailable
- TaxGraphsProvider graceful fallback when Redis unavailable
- TaxGraphsProvider.get_rate() with mocked taxgraphs JSON
- set_provider() / get_provider() registry behaviour
- Provider registry reset between tests
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.services.tax_rate_providers as registry
from app.services.tax_rate_providers import (
    StateTaxBracket,
    StaticStateTaxProvider,
    TaxGraphsProvider,
    get_provider,
    set_provider,
)


# ── helpers ────────────────────────────────────────────────────────────────────


def _reset_registry():
    """Reset the module-level provider singleton between tests."""
    registry._provider = None


# Sample taxgraphs-style JSON for CA (simplified)
_SAMPLE_TAXGRAPHS_JSON = {
    "CA": {
        "income": {
            "single": {
                "brackets": [
                    [0, 0.01, 0],
                    [10099, 0.02, 100.99],
                    [23942, 0.04, 377.85],
                    [37788, 0.06, 931.69],
                    [52455, 0.08, 1812.01],
                    [66295, 0.093, 2919.21],
                    [338639, 0.103, 28248.30],
                    [406364, 0.113, 35226.51],
                    [677275, 0.123, 65834.94],
                ]
            },
            "married": {
                "brackets": [
                    [0, 0.01, 0],
                    [20198, 0.02, 201.98],
                ]
            },
        }
    },
    "TX": {},  # No income data → 0 rate
    "NY": {
        "income": {
            "single": {
                "brackets": [
                    [0, 0.04, 0],
                    [17150, 0.045, 686.0],
                    [23600, 0.0525, 976.25],
                    [27900, 0.055, 1202.0],
                    [161550, 0.06, 8551.5],
                    [323200, 0.0685, 18245.1],
                    [2155350, 0.0965, 143556.96],
                    [5000000, 0.103, 418062.39],
                    [25000000, 0.109, 2477562.39],
                ]
            }
        }
    },
}


# ── StaticStateTaxProvider tests ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestStaticStateTaxProvider:
    async def test_get_rate_california(self):
        provider = StaticStateTaxProvider()
        rate = await provider.get_rate("CA", "single", 75000)
        assert rate == pytest.approx(0.093)

    async def test_get_rate_texas_is_zero(self):
        provider = StaticStateTaxProvider()
        rate = await provider.get_rate("TX", "single", 75000)
        assert rate == 0.0

    async def test_get_rate_new_york(self):
        provider = StaticStateTaxProvider()
        rate = await provider.get_rate("NY", "single", 75000)
        assert rate == pytest.approx(0.0685)

    async def test_get_rate_unknown_state_returns_zero(self):
        provider = StaticStateTaxProvider()
        rate = await provider.get_rate("ZZ", "single", 50000)
        assert rate == 0.0

    async def test_get_rate_case_insensitive(self):
        provider = StaticStateTaxProvider()
        rate_upper = await provider.get_rate("CA", "single", 75000)
        rate_lower = await provider.get_rate("ca", "single", 75000)
        assert rate_upper == rate_lower

    async def test_get_brackets_returns_single_bracket(self):
        provider = StaticStateTaxProvider()
        brackets = await provider.get_brackets("CA", "single")
        assert len(brackets) == 1
        bracket = brackets[0]
        assert bracket.min_income == 0
        assert bracket.max_income == float("inf")
        assert bracket.rate == pytest.approx(0.093)

    async def test_get_brackets_zero_rate_state(self):
        provider = StaticStateTaxProvider()
        brackets = await provider.get_brackets("TX", "single")
        assert len(brackets) == 1
        assert brackets[0].rate == 0.0

    def test_source_name(self):
        provider = StaticStateTaxProvider()
        assert provider.source_name() == "static_bundled_rates_2026"

    def test_tax_year(self):
        provider = StaticStateTaxProvider()
        assert provider.tax_year() == 2026


# ── TaxGraphsProvider: fallback when network is unavailable ───────────────────


@pytest.mark.asyncio
class TestTaxGraphsProviderNetworkFallback:
    async def test_falls_back_to_static_on_connect_error(self):
        """When httpx raises ConnectError, provider returns static rate."""
        provider = TaxGraphsProvider()
        # Prevent Redis from being used
        provider._redis_available = False

        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("no network")):
            rate = await provider.get_rate("CA", "single", 75000)

        # Static fallback for CA is 0.093
        assert rate == pytest.approx(0.093)

    async def test_falls_back_to_static_on_http_error(self):
        """Any httpx exception triggers fallback to static provider."""
        provider = TaxGraphsProvider()
        provider._redis_available = False

        with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("timeout")):
            rate = await provider.get_rate("TX", "single", 50000)

        assert rate == 0.0  # TX has no income tax


# ── TaxGraphsProvider: fallback when Redis is unavailable ─────────────────────


@pytest.mark.asyncio
class TestTaxGraphsProviderRedisFallback:
    async def test_falls_back_gracefully_when_redis_raises(self):
        """When redis.from_url raises, provider still returns correct rate via HTTP."""
        provider = TaxGraphsProvider()

        # Make Redis init raise
        with patch(
            "redis.asyncio.from_url",
            side_effect=Exception("Redis connection refused"),
        ):
            # Patch the HTTP call to return our sample data
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = _SAMPLE_TAXGRAPHS_JSON

            async_get_mock = AsyncMock(return_value=mock_response)
            with patch("httpx.AsyncClient.get", async_get_mock):
                rate = await provider.get_rate("CA", "single", 80000)

        # At $80k, CA single should be in the 9.3% bracket
        assert rate == pytest.approx(0.093)

    async def test_redis_unavailable_flag_is_set_on_failure(self):
        """After Redis fails to connect, _redis_available is set to False."""
        provider = TaxGraphsProvider()

        with patch(
            "redis.asyncio.from_url",
            side_effect=Exception("Connection refused"),
        ):
            result = await provider._get_redis()

        assert result is None
        assert provider._redis_available is False


# ── TaxGraphsProvider: correct rate from mocked JSON ─────────────────────────


@pytest.mark.asyncio
class TestTaxGraphsProviderWithMockedJSON:
    def _make_provider_with_data(self, data: dict) -> TaxGraphsProvider:
        """Return a TaxGraphsProvider that immediately returns data from _load_data."""
        provider = TaxGraphsProvider()
        provider._load_data = AsyncMock(return_value=data)
        return provider

    async def test_ca_single_rate_at_75k(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        # $75k falls in the 9.3% bracket (starts at $66,295)
        rate = await provider.get_rate("CA", "single", 75000)
        assert rate == pytest.approx(0.093)

    async def test_ca_single_rate_at_low_income(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        # $5k falls in first bracket: 1%
        rate = await provider.get_rate("CA", "single", 5000)
        assert rate == pytest.approx(0.01)

    async def test_tx_no_income_data_returns_zero(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        rate = await provider.get_rate("TX", "single", 75000)
        assert rate == 0.0

    async def test_ny_single_rate_at_300k(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        # In the sample JSON, the bracket starting at $161,550 has rate 0.06;
        # the 6.85% bracket starts at $323,200.  $300k falls in the 6% bracket.
        rate = await provider.get_rate("NY", "single", 300000)
        assert rate == pytest.approx(0.06)

    async def test_unknown_state_falls_back_to_static(self):
        """State not in taxgraphs JSON falls back to STATE_TAX_RATES dict."""
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        # OR is not in our sample JSON but is in STATE_TAX_RATES (0.099)
        brackets = await provider.get_brackets("OR", "single")
        assert len(brackets) == 1
        assert brackets[0].rate == pytest.approx(0.099)

    async def test_married_status_mapping(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        # "married_jointly" should map to taxgraphs "married"
        rate_married = await provider.get_rate("CA", "married", 30000)
        rate_jointly = await provider.get_rate("CA", "married_jointly", 30000)
        assert rate_married == rate_jointly

    async def test_get_brackets_returns_multiple_brackets(self):
        provider = self._make_provider_with_data(_SAMPLE_TAXGRAPHS_JSON)
        brackets = await provider.get_brackets("CA", "single")
        assert len(brackets) == 9
        # First bracket
        assert brackets[0].min_income == 0
        assert brackets[0].max_income == pytest.approx(10099)
        assert brackets[0].rate == pytest.approx(0.01)
        # Last bracket has infinite ceiling
        assert brackets[-1].max_income == float("inf")

    async def test_falls_back_to_static_when_load_data_returns_none(self):
        """If _load_data returns None, get_rate uses static fallback."""
        provider = TaxGraphsProvider()
        provider._load_data = AsyncMock(return_value=None)
        rate = await provider.get_rate("CA", "single", 75000)
        assert rate == pytest.approx(0.093)

    def test_source_name(self):
        provider = TaxGraphsProvider()
        assert provider.source_name() == "taxgraphs_github"


# ── Provider registry tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestProviderRegistry:
    def setup_method(self):
        _reset_registry()

    def teardown_method(self):
        _reset_registry()

    async def test_get_provider_returns_taxgraphs_by_default(self):
        provider = await get_provider()
        assert isinstance(provider, TaxGraphsProvider)

    async def test_get_provider_returns_same_instance_on_second_call(self):
        p1 = await get_provider()
        p2 = await get_provider()
        assert p1 is p2

    async def test_set_provider_overrides_default(self):
        static = StaticStateTaxProvider()
        set_provider(static)
        result = await get_provider()
        assert result is static

    async def test_set_provider_then_reset_restores_none(self):
        set_provider(StaticStateTaxProvider())
        _reset_registry()
        provider = await get_provider()
        # After reset, a fresh TaxGraphsProvider should be created
        assert isinstance(provider, TaxGraphsProvider)

    async def test_custom_provider_can_be_set(self):
        """Any StateTaxProvider subclass can be injected."""

        class MyProvider(registry.StateTaxProvider):
            def source_name(self):
                return "my_custom_provider"

            def tax_year(self):
                return 2025

            async def get_rate(self, state, filing_status, income):
                return 0.05

            async def get_brackets(self, state, filing_status):
                return [StateTaxBracket(0, float("inf"), 0.05)]

        set_provider(MyProvider())
        p = await get_provider()
        assert p.source_name() == "my_custom_provider"
        rate = await p.get_rate("CA", "single", 100000)
        assert rate == pytest.approx(0.05)
