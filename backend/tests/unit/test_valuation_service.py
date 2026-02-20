"""Unit tests for the auto-valuation service."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.valuation_service import (
    ValuationResult,
    get_available_property_providers,
    get_available_vehicle_providers,
    get_property_value,
    get_vehicle_value,
    decode_vin_nhtsa,
    _get_property_value_rentcast,
    _get_property_value_attom,
    _get_property_value_zillow,
    _get_vehicle_value_marketcheck,
    _is_provider_configured,
)


# ── provider discovery ────────────────────────────────────────────────────────


class TestGetAvailablePropertyProviders:
    def test_returns_empty_when_no_keys(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = None
            mock_settings.ATTOM_API_KEY = None
            mock_settings.ZILLOW_RAPIDAPI_KEY = None
            assert get_available_property_providers() == []

    def test_returns_rentcast_when_configured(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = "rc_key"
            mock_settings.ATTOM_API_KEY = None
            mock_settings.ZILLOW_RAPIDAPI_KEY = None
            assert get_available_property_providers() == ["rentcast"]

    def test_returns_attom_when_configured(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = None
            mock_settings.ATTOM_API_KEY = "attom_key"
            mock_settings.ZILLOW_RAPIDAPI_KEY = None
            assert get_available_property_providers() == ["attom"]

    def test_returns_zillow_when_configured(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = None
            mock_settings.ATTOM_API_KEY = None
            mock_settings.ZILLOW_RAPIDAPI_KEY = "zil_key"
            assert get_available_property_providers() == ["zillow"]

    def test_returns_all_when_all_configured(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = "rc_key"
            mock_settings.ATTOM_API_KEY = "attom_key"
            mock_settings.ZILLOW_RAPIDAPI_KEY = "zil_key"
            providers = get_available_property_providers()
            assert "rentcast" in providers
            assert "attom" in providers
            assert "zillow" in providers

    def test_rentcast_before_attom_before_zillow(self):
        """Preferred order: rentcast → attom → zillow."""
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.RENTCAST_API_KEY = "rc"
            mock_settings.ATTOM_API_KEY = "at"
            mock_settings.ZILLOW_RAPIDAPI_KEY = "zil"
            providers = get_available_property_providers()
            assert providers.index("rentcast") < providers.index("attom")
            assert providers.index("attom") < providers.index("zillow")


class TestGetAvailableVehicleProviders:
    def test_returns_empty_when_no_key(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.MARKETCHECK_API_KEY = None
            assert get_available_vehicle_providers() == []

    def test_returns_marketcheck_when_configured(self):
        with patch("app.services.valuation_service.settings") as mock_settings:
            mock_settings.MARKETCHECK_API_KEY = "mc_key"
            assert get_available_vehicle_providers() == ["marketcheck"]


# ── _is_provider_configured ───────────────────────────────────────────────────


class TestIsProviderConfigured:
    def test_rentcast_configured(self):
        with patch("app.services.valuation_service.settings") as s:
            s.RENTCAST_API_KEY = "key"
            s.ATTOM_API_KEY = None
            s.ZILLOW_RAPIDAPI_KEY = None
            s.MARKETCHECK_API_KEY = None
            assert _is_provider_configured("rentcast") is True

    def test_rentcast_not_configured(self):
        with patch("app.services.valuation_service.settings") as s:
            s.RENTCAST_API_KEY = None
            s.ATTOM_API_KEY = None
            s.ZILLOW_RAPIDAPI_KEY = None
            s.MARKETCHECK_API_KEY = None
            assert _is_provider_configured("rentcast") is False

    def test_zillow_configured(self):
        with patch("app.services.valuation_service.settings") as s:
            s.RENTCAST_API_KEY = None
            s.ATTOM_API_KEY = None
            s.ZILLOW_RAPIDAPI_KEY = "rapidapi_key"
            s.MARKETCHECK_API_KEY = None
            assert _is_provider_configured("zillow") is True

    def test_unknown_provider_returns_false(self):
        with patch("app.services.valuation_service.settings") as s:
            s.RENTCAST_API_KEY = "key"
            assert _is_provider_configured("nonexistent") is False


# ── RentCast provider ─────────────────────────────────────────────────────────


class TestGetPropertyValueRentcast:
    @pytest.mark.asyncio
    async def test_returns_valuation_result_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "price": 500000,
            "priceRangeLow": 475000,
            "priceRangeHigh": 525000,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.RENTCAST_API_KEY = "test_key"
                result = await _get_property_value_rentcast("123 Main St", "94102")

        assert result is not None
        assert result.provider == "rentcast"
        assert result.value == Decimal("500000")
        assert result.low == Decimal("475000")
        assert result.high == Decimal("525000")

    @pytest.mark.asyncio
    async def test_returns_none_when_price_missing(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.RENTCAST_API_KEY = "test_key"
                result = await _get_property_value_rentcast("123 Main St", "94102")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_response)
        )

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.RENTCAST_API_KEY = "test_key"
                result = await _get_property_value_rentcast("123 Main St", "94102")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_missing_range_gracefully(self):
        """priceRangeLow / priceRangeHigh are optional."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"price": 350000}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.RENTCAST_API_KEY = "test_key"
                result = await _get_property_value_rentcast("123 Main St", "94102")

        assert result is not None
        assert result.value == Decimal("350000")
        assert result.low is None
        assert result.high is None


# ── ATTOM provider ────────────────────────────────────────────────────────────


class TestGetPropertyValueAttom:
    @pytest.mark.asyncio
    async def test_returns_valuation_result_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "property": [
                {
                    "avm": {
                        "amount": {
                            "value": 620000,
                            "low": 590000,
                            "high": 650000,
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ATTOM_API_KEY = "test_key"
                result = await _get_property_value_attom("123 Main St", "94102")

        assert result is not None
        assert result.provider == "attom"
        assert result.value == Decimal("620000")
        assert result.low == Decimal("590000")
        assert result.high == Decimal("650000")

    @pytest.mark.asyncio
    async def test_returns_none_when_no_property(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"property": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ATTOM_API_KEY = "test_key"
                result = await _get_property_value_attom("Bad Address", "00000")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_avm_value_missing(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "property": [{"avm": {"amount": {}}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ATTOM_API_KEY = "test_key"
                result = await _get_property_value_attom("123 Main St", "94102")

        assert result is None


# ── Zillow provider ───────────────────────────────────────────────────────────


class TestGetPropertyValueZillow:
    """
    Tests for the unofficial Zillow RapidAPI wrapper.
    NOTE: This provider is not recommended due to ToS concerns.
    """

    @pytest.mark.asyncio
    async def test_returns_valuation_result_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "zestimate": 475000,
            "valuationRangeLow": 450000,
            "valuationRangeHigh": 500000,
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ZILLOW_RAPIDAPI_KEY = "rapidapi_key"
                result = await _get_property_value_zillow("123 Main St", "94102")

        assert result is not None
        assert result.provider == "zillow"
        assert result.value == Decimal("475000")
        assert result.low == Decimal("450000")
        assert result.high == Decimal("500000")

    @pytest.mark.asyncio
    async def test_returns_none_when_zestimate_missing(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Property not found"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ZILLOW_RAPIDAPI_KEY = "rapidapi_key"
                result = await _get_property_value_zillow("Unknown Address", "00000")

        assert result is None

    @pytest.mark.asyncio
    async def test_handles_missing_range_gracefully(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"zestimate": 300000}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ZILLOW_RAPIDAPI_KEY = "rapidapi_key"
                result = await _get_property_value_zillow("123 Main St", "94102")

        assert result is not None
        assert result.value == Decimal("300000")
        assert result.low is None
        assert result.high is None

    @pytest.mark.asyncio
    async def test_returns_none_on_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError("Forbidden", request=MagicMock(), response=mock_response)
        )

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ZILLOW_RAPIDAPI_KEY = "rapidapi_key"
                result = await _get_property_value_zillow("123 Main St", "94102")

        assert result is None

    @pytest.mark.asyncio
    async def test_uses_correct_rapidapi_host_header(self):
        """Verify the correct X-RapidAPI-Host header is sent."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"zestimate": 400000}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.ZILLOW_RAPIDAPI_KEY = "my_rapidapi_key"
                await _get_property_value_zillow("123 Main St", "94102")

        call_kwargs = mock_client.get.call_args
        headers = call_kwargs.kwargs.get("headers", {})
        assert headers.get("X-RapidAPI-Host") == "zillow-com1.p.rapidapi.com"
        assert headers.get("X-RapidAPI-Key") == "my_rapidapi_key"


# ── MarketCheck vehicle provider ──────────────────────────────────────────────


class TestGetVehicleValueMarketcheck:
    @pytest.mark.asyncio
    async def test_returns_valuation_result_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "price": {"mean": 25000, "low": 22000, "high": 28000}
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.MARKETCHECK_API_KEY = "mc_key"
                result = await _get_vehicle_value_marketcheck("1HGBH41JXMN109186", mileage=50000)

        assert result is not None
        assert result.provider == "marketcheck"
        assert result.value == Decimal("25000")
        assert result.low == Decimal("22000")
        assert result.high == Decimal("28000")

    @pytest.mark.asyncio
    async def test_returns_none_when_mean_missing(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"price": {}}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            with patch("app.services.valuation_service.settings") as s:
                s.MARKETCHECK_API_KEY = "mc_key"
                result = await _get_vehicle_value_marketcheck("BADVIN")

        assert result is None


# ── get_property_value (router) ───────────────────────────────────────────────


class TestGetPropertyValue:
    @pytest.mark.asyncio
    async def test_uses_specified_provider(self):
        with patch("app.services.valuation_service._is_provider_configured", return_value=True):
            mock_result = ValuationResult(value=Decimal("500000"), provider="rentcast")
            with patch(
                "app.services.valuation_service._PROPERTY_PROVIDERS",
                {"rentcast": AsyncMock(return_value=mock_result)},
            ):
                result = await get_property_value("123 Main St", "94102", provider="rentcast")

        assert result is not None
        assert result.provider == "rentcast"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_provider(self):
        result = await get_property_value("123 Main St", "94102", provider="unknown_provider")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_provider_not_configured(self):
        with patch("app.services.valuation_service._is_provider_configured", return_value=False):
            result = await get_property_value("123 Main St", "94102", provider="rentcast")
        assert result is None

    @pytest.mark.asyncio
    async def test_auto_selects_first_available_provider(self):
        mock_result = ValuationResult(value=Decimal("400000"), provider="attom")
        with patch(
            "app.services.valuation_service.get_available_property_providers",
            return_value=["attom"],
        ):
            with patch(
                "app.services.valuation_service._PROPERTY_PROVIDERS",
                {"attom": AsyncMock(return_value=mock_result)},
            ):
                result = await get_property_value("123 Main St", "94102")

        assert result is not None
        assert result.provider == "attom"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_providers_available(self):
        with patch(
            "app.services.valuation_service.get_available_property_providers",
            return_value=[],
        ):
            result = await get_property_value("123 Main St", "94102")
        assert result is None


# ── NHTSA VIN decode ──────────────────────────────────────────────────────────


class TestDecodeVinNhtsa:
    @pytest.mark.asyncio
    async def test_returns_vehicle_info_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Results": [
                {"Variable": "Model Year", "Value": "2020"},
                {"Variable": "Make", "Value": "Honda"},
                {"Variable": "Model", "Value": "Accord"},
                {"Variable": "Trim", "Value": "EX"},
                {"Variable": "Body Class", "Value": "Sedan"},
                {"Variable": "Ignored", "Value": None},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            result = await decode_vin_nhtsa("1HGBH41JXMN109186")

        assert result is not None
        assert result["year"] == "2020"
        assert result["make"] == "Honda"
        assert result["model"] == "Accord"
        assert result["trim"] == "EX"
        assert result["body_style"] == "Sedan"

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("app.services.valuation_service.httpx.AsyncClient", return_value=mock_client):
            result = await decode_vin_nhtsa("BAD_VIN")

        assert result is None
