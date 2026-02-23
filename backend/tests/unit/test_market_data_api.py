"""Unit tests for market_data API helpers.

Focused on the _validate_symbol function added as part of the ticker
security fix (previously any string was accepted and forwarded to the
market data provider, allowing SSRF-like injection via symbol names).
"""

import pytest
from fastapi import HTTPException

from app.api.v1.market_data import _validate_symbol


@pytest.mark.unit
class TestValidateSymbol:
    """Tests for _validate_symbol helper."""

    # -----------------------------------------------------------------------
    # Valid symbols
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize("symbol", [
        "AAPL",          # plain US stock
        "MSFT",          # plain US stock
        "BRK.A",         # Berkshire class A (contains dot)
        "BRK.B",         # Berkshire class B
        "^GSPC",         # S&P 500 index (starts with caret)
        "^DJI",          # Dow Jones index
        "BTC-USD",       # crypto pair (contains dash)
        "ETH-USD",       # crypto pair
        "A",             # single-letter ticker
        "ABCDE12345",    # 10 chars — within limit
        "123456789012345", # 15 chars — at limit
    ])
    def test_valid_symbol_passes(self, symbol):
        """Valid tickers should return the uppercased, stripped symbol."""
        result = _validate_symbol(symbol)
        assert result == symbol.strip().upper()

    def test_lowercases_are_normalised(self):
        """Lowercase input should be uppercased, not rejected."""
        assert _validate_symbol("aapl") == "AAPL"
        assert _validate_symbol("brk.a") == "BRK.A"

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped before validation."""
        assert _validate_symbol("  AAPL  ") == "AAPL"
        assert _validate_symbol("\tMSFT\n") == "MSFT"

    # -----------------------------------------------------------------------
    # Invalid symbols → HTTPException 400
    # -----------------------------------------------------------------------

    @pytest.mark.parametrize("bad_symbol", [
        "",                    # empty string
        "WAYTOOLONGSYMBOL",   # 17 chars — over 15-char limit
        "AAPL MSFT",          # space in middle
        "AAPL\x00",           # null byte
        "../etc/passwd",      # path traversal attempt
        "AAPL; DROP TABLE",   # SQL injection attempt
        "$(echo pwned)",      # command injection attempt
        "AAPL\nMSFT",         # newline injection
    ])
    def test_invalid_symbol_raises_400(self, bad_symbol):
        """Symbols with illegal characters or length should raise 400."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_symbol(bad_symbol)
        assert exc_info.value.status_code == 400

    def test_error_message_contains_symbol(self):
        """Error detail should reference the submitted symbol for clarity."""
        with pytest.raises(HTTPException) as exc_info:
            _validate_symbol("BAD SYMBOL")
        assert "BAD SYMBOL" in exc_info.value.detail

    def test_exactly_16_chars_is_rejected(self):
        """16-char ticker exceeds the 15-char maximum."""
        with pytest.raises(HTTPException):
            _validate_symbol("A" * 16)

    def test_exactly_15_chars_is_accepted(self):
        """15-char ticker is at the boundary and should be accepted."""
        result = _validate_symbol("A" * 15)
        assert result == "A" * 15

    def test_single_char_accepted(self):
        """Single character (minimum length) should be valid."""
        assert _validate_symbol("A") == "A"
