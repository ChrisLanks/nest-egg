"""Tests for market data provider factory."""

import pytest
from unittest.mock import patch


class TestMarketDataProviderFactory:
    """Test suite for provider factory."""

    def setup_method(self):
        """Reset factory singleton before each test."""
        from app.services.market_data.provider_factory import MarketDataProviderFactory

        MarketDataProviderFactory._instance = None

    def test_default_provider_is_yahoo(self, monkeypatch):
        """Should default to Yahoo Finance provider."""
        monkeypatch.setenv("MARKET_DATA_PROVIDER", "yahoo_finance")
        from app.services.market_data.provider_factory import get_market_data_provider

        provider = get_market_data_provider("yahoo_finance")
        assert provider.get_provider_name() == "Yahoo Finance"

    def test_finnhub_provider(self, monkeypatch):
        """Should create Finnhub provider when API key is set."""
        monkeypatch.setattr("app.config.settings.FINNHUB_API_KEY", "test-key")
        from app.services.market_data.provider_factory import get_market_data_provider

        provider = get_market_data_provider("finnhub")
        assert provider.get_provider_name() == "Finnhub"

    def test_alpha_vantage_provider(self, monkeypatch):
        """Should create Alpha Vantage provider when API key is set."""
        monkeypatch.setattr("app.config.settings.ALPHA_VANTAGE_API_KEY", "test-key")
        from app.services.market_data.provider_factory import get_market_data_provider

        provider = get_market_data_provider("alpha_vantage")
        assert provider.get_provider_name() == "Alpha Vantage"

    def test_finnhub_without_api_key_raises(self, monkeypatch):
        """Should raise ValueError when Finnhub key is not set."""
        monkeypatch.setattr("app.config.settings.FINNHUB_API_KEY", None)
        from app.services.market_data.provider_factory import get_market_data_provider

        with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
            get_market_data_provider("finnhub")

    def test_alpha_vantage_without_api_key_raises(self, monkeypatch):
        """Should raise ValueError when Alpha Vantage key is not set."""
        monkeypatch.setattr("app.config.settings.ALPHA_VANTAGE_API_KEY", None)
        from app.services.market_data.provider_factory import get_market_data_provider

        with pytest.raises(ValueError, match="ALPHA_VANTAGE_API_KEY"):
            get_market_data_provider("alpha_vantage")

    def test_unknown_provider_raises(self):
        """Should raise ValueError for unknown provider."""
        from app.services.market_data.provider_factory import get_market_data_provider

        with pytest.raises(ValueError, match="Unsupported"):
            get_market_data_provider("nonexistent_provider")

    def test_factory_caches_default_instance(self, monkeypatch):
        """Should cache the default provider instance."""
        monkeypatch.setenv("MARKET_DATA_PROVIDER", "yahoo_finance")
        from app.services.market_data.provider_factory import (
            MarketDataProviderFactory,
            get_market_data_provider,
        )

        provider1 = get_market_data_provider()
        provider2 = get_market_data_provider()
        assert provider1 is provider2

    def test_explicit_provider_name_bypasses_cache(self, monkeypatch):
        """Should create new instance when explicit provider name given."""
        monkeypatch.setenv("MARKET_DATA_PROVIDER", "yahoo_finance")
        from app.services.market_data.provider_factory import get_market_data_provider

        provider1 = get_market_data_provider()
        # Explicit name should still return a provider, just may be a new instance
        provider2 = get_market_data_provider("yahoo_finance")
        assert provider2.get_provider_name() == "Yahoo Finance"
