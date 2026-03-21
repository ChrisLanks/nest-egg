"""Extended unit tests for market_data API endpoints — covers get_quote, get_quotes_batch,
get_historical_prices, search_symbols, get_provider_info, refresh_holding_price,
and refresh_all_holdings."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.market_data import (
    HistoricalPriceResponse,
    ProviderInfo,
    QuoteResponse,
    SearchResultResponse,
    get_historical_prices,
    get_provider_info,
    get_quote,
    get_quotes_batch,
    refresh_all_holdings,
    refresh_holding_price,
    search_symbols,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(org_id=None, user_id=None):
    user = MagicMock()
    user.id = user_id or uuid4()
    user.organization_id = org_id or uuid4()
    return user


def _make_quote(symbol="AAPL", price=Decimal("150.00")):
    quote = MagicMock()
    quote.symbol = symbol
    quote.price = price
    quote.name = "Apple Inc."
    quote.currency = "USD"
    quote.exchange = "NASDAQ"
    quote.volume = 1000000
    quote.market_cap = Decimal("2500000000000")
    quote.change = Decimal("2.50")
    quote.change_percent = Decimal("1.69")
    quote.previous_close = Decimal("147.50")
    quote.open = Decimal("148.00")
    quote.high = Decimal("151.00")
    quote.low = Decimal("147.00")
    quote.year_high = Decimal("200.00")
    quote.year_low = Decimal("120.00")
    quote.dividend_yield = Decimal("0.55")
    quote.pe_ratio = Decimal("25.5")
    quote.model_dump = MagicMock(
        return_value={
            "symbol": symbol,
            "price": price,
            "name": "Apple Inc.",
            "currency": "USD",
            "exchange": "NASDAQ",
            "volume": 1000000,
            "market_cap": Decimal("2500000000000"),
            "change": Decimal("2.50"),
            "change_percent": Decimal("1.69"),
            "previous_close": Decimal("147.50"),
            "open": Decimal("148.00"),
            "high": Decimal("151.00"),
            "low": Decimal("147.00"),
            "year_high": Decimal("200.00"),
            "year_low": Decimal("120.00"),
            "dividend_yield": Decimal("0.55"),
            "pe_ratio": Decimal("25.5"),
        }
    )
    return quote


def _make_provider():
    provider = MagicMock()
    provider.get_provider_name.return_value = "yahoo_finance"
    provider.supports_realtime.return_value = False
    provider.get_rate_limits.return_value = {"requests_per_minute": 100}
    return provider


# ---------------------------------------------------------------------------
# get_quote
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetQuote:
    @pytest.mark.asyncio
    async def test_returns_quote(self):
        user = _make_user()
        quote = _make_quote()
        provider = _make_provider()
        provider.get_quote = AsyncMock(return_value=quote)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await get_quote(symbol="AAPL", provider=None, current_user=user)

        assert isinstance(result, QuoteResponse)
        assert result.symbol == "AAPL"
        assert result.provider == "yahoo_finance"

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_symbol(self):
        user = _make_user()
        provider = _make_provider()
        provider.get_quote = AsyncMock(side_effect=ValueError("Not found"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await get_quote(symbol="ZZZZZ", provider=None, current_user=user)
                assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_500_on_generic_error(self):
        user = _make_user()
        provider = _make_provider()
        provider.get_quote = AsyncMock(side_effect=RuntimeError("API error"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await get_quote(symbol="AAPL", provider=None, current_user=user)
                assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_with_provider_override(self):
        user = _make_user()
        quote = _make_quote()
        provider = _make_provider()
        provider.get_quote = AsyncMock(return_value=quote)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch(
                "app.api.v1.market_data.get_market_data_provider", return_value=provider
            ) as mock_get:
                await get_quote(symbol="AAPL", provider="alpha_vantage", current_user=user)
                mock_get.assert_called_once_with("alpha_vantage")


# ---------------------------------------------------------------------------
# get_quotes_batch
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetQuotesBatch:
    @pytest.mark.asyncio
    async def test_returns_batch_quotes(self):
        user = _make_user()
        quote = _make_quote()
        provider = _make_provider()
        provider.get_quotes_batch = AsyncMock(return_value={"AAPL": quote})

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await get_quotes_batch(symbols=["AAPL"], provider=None, current_user=user)

        assert "AAPL" in result

    @pytest.mark.asyncio
    async def test_raises_400_too_many_symbols(self):
        user = _make_user()

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await get_quotes_batch(
                    symbols=["SYM"] * 51,
                    provider=None,
                    current_user=user,
                )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_500_on_error(self):
        user = _make_user()
        provider = _make_provider()
        provider.get_quotes_batch = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await get_quotes_batch(symbols=["AAPL"], provider=None, current_user=user)
                assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get_historical_prices
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetHistoricalPrices:
    @pytest.mark.asyncio
    async def test_returns_historical_data(self):
        user = _make_user()
        provider = _make_provider()

        mock_price = MagicMock()
        mock_price.model_dump.return_value = {
            "date": date(2024, 1, 1),
            "open": Decimal("150"),
            "high": Decimal("155"),
            "low": Decimal("148"),
            "close": Decimal("153"),
            "volume": 500000,
            "adjusted_close": Decimal("153"),
        }
        provider.get_historical_prices = AsyncMock(return_value=[mock_price])

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await get_historical_prices(
                    symbol="AAPL",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    interval="1d",
                    provider=None,
                    current_user=user,
                )

        assert len(result) == 1
        assert isinstance(result[0], HistoricalPriceResponse)

    @pytest.mark.asyncio
    async def test_raises_404_on_value_error(self):
        user = _make_user()
        provider = _make_provider()
        provider.get_historical_prices = AsyncMock(side_effect=ValueError("Not found"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await get_historical_prices(
                        symbol="ZZZZZ",
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 1, 31),
                        interval="1d",
                        provider=None,
                        current_user=user,
                    )
                assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_500_on_generic_error(self):
        user = _make_user()
        provider = _make_provider()
        provider.get_historical_prices = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await get_historical_prices(
                        symbol="AAPL",
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 1, 31),
                        interval="1d",
                        provider=None,
                        current_user=user,
                    )
                assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# search_symbols
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchSymbols:
    @pytest.mark.asyncio
    async def test_returns_results(self):
        user = _make_user()
        provider = _make_provider()

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "type": "stock",
            "exchange": "NASDAQ",
            "currency": "USD",
        }
        provider.search_symbol = AsyncMock(return_value=[mock_result])

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await search_symbols(query="Apple", provider=None, current_user=user)

        assert len(result) == 1
        assert isinstance(result[0], SearchResultResponse)

    @pytest.mark.asyncio
    async def test_raises_500_on_error(self):
        user = _make_user()
        provider = _make_provider()
        provider.search_symbol = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await search_symbols(query="Apple", provider=None, current_user=user)
                assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# get_provider_info
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProviderInfo:
    @pytest.mark.asyncio
    async def test_returns_info(self):
        user = _make_user()
        provider = _make_provider()

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await get_provider_info(provider=None, current_user=user)

        assert isinstance(result, ProviderInfo)
        assert result.name == "yahoo_finance"
        assert result.supports_realtime is False


# ---------------------------------------------------------------------------
# refresh_holding_price
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshHoldingPrice:
    @pytest.mark.asyncio
    async def test_refreshes_price(self):
        user = _make_user()
        db = AsyncMock()
        holding_id = uuid4()

        mock_holding = MagicMock()
        mock_holding.id = holding_id
        mock_holding.ticker = "AAPL"
        mock_holding.shares = Decimal("10")
        mock_holding.total_cost_basis = Decimal("1400")
        mock_holding.organization_id = user.organization_id

        # Select holding
        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = mock_holding

        # Update result
        update_result = MagicMock()

        db.execute = AsyncMock(side_effect=[holding_result, update_result])

        quote = _make_quote(price=Decimal("150.00"))
        provider = _make_provider()
        provider.get_quote = AsyncMock(return_value=quote)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await refresh_holding_price(
                    holding_id=holding_id, db=db, current_user=user
                )

        assert result["symbol"] == "AAPL"
        assert result["current_price"] == 150.0
        assert result["current_value"] == 1500.0

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        user = _make_user()
        db = AsyncMock()

        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=holding_result)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_holding_price(holding_id=uuid4(), db=db, current_user=user)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_on_value_error(self):
        user = _make_user()
        db = AsyncMock()

        mock_holding = MagicMock()
        mock_holding.ticker = "ZZZZZ"
        mock_holding.organization_id = user.organization_id

        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = mock_holding
        db.execute = AsyncMock(return_value=holding_result)

        provider = _make_provider()
        provider.get_quote = AsyncMock(side_effect=ValueError("Not found"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_holding_price(holding_id=uuid4(), db=db, current_user=user)
                assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_500_on_generic_error(self):
        user = _make_user()
        db = AsyncMock()

        mock_holding = MagicMock()
        mock_holding.ticker = "AAPL"
        mock_holding.organization_id = user.organization_id

        holding_result = MagicMock()
        holding_result.scalar_one_or_none.return_value = mock_holding
        db.execute = AsyncMock(return_value=holding_result)

        provider = _make_provider()
        provider.get_quote = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_holding_price(holding_id=uuid4(), db=db, current_user=user)
                assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# refresh_all_holdings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshAllHoldings:
    @pytest.mark.asyncio
    async def test_refreshes_all_holdings(self):
        """Verify refresh_all_holdings reads ticker, updates current_price_per_share/price_as_of."""
        user = _make_user()
        db = AsyncMock()

        h1 = MagicMock()
        h1.ticker = "AAPL"
        h1.organization_id = user.organization_id

        h2 = MagicMock()
        h2.ticker = "GOOG"
        h2.organization_id = user.organization_id

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [h1, h2]
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock

        update_result = MagicMock()
        update_result.rowcount = 1

        db.execute = AsyncMock(side_effect=[select_result, update_result, update_result])

        quote_aapl = _make_quote(symbol="AAPL", price=Decimal("150.00"))
        quote_goog = _make_quote(symbol="GOOG", price=Decimal("2800.00"))

        provider = _make_provider()
        provider.get_quotes_batch = AsyncMock(return_value={"AAPL": quote_aapl, "GOOG": quote_goog})

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            with patch("app.api.v1.market_data.get_market_data_provider", return_value=provider):
                result = await refresh_all_holdings(user_id=None, db=db, current_user=user)

        assert result["updated"] == 2
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_holdings(self):
        user = _make_user()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=select_result)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            result = await refresh_all_holdings(user_id=None, db=db, current_user=user)

        assert result["updated"] == 0

    @pytest.mark.asyncio
    async def test_filters_by_user_id(self):
        user = _make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        select_result = MagicMock()
        select_result.scalars.return_value = scalars_mock
        db.execute = AsyncMock(return_value=select_result)

        with patch("app.api.v1.market_data.check_rate_limit", new_callable=AsyncMock):
            result = await refresh_all_holdings(user_id=target_user_id, db=db, current_user=user)

        assert result["updated"] == 0
