"""
Security utilities for market data services.

Implements validation, sanitization, and rate limiting to protect against
malicious data from unofficial external APIs.
"""

import re
from decimal import Decimal, InvalidOperation
from typing import Optional
from pydantic import BaseModel, field_validator
import logging

logger = logging.getLogger(__name__)

# Valid stock symbol pattern: uppercase alphanumeric, dots, hyphens only
VALID_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9\.\-]{1,10}$")

# Dangerous patterns that could indicate injection attacks
DANGEROUS_PATTERNS = ["../", "\\", "|", ";", "&", "$", "`", "<", ">", "{", "}"]


class SymbolValidationError(ValueError):
    """Raised when symbol validation fails."""


class PriceValidationError(ValueError):
    """Raised when price validation fails."""


def validate_symbol(symbol: str) -> str:
    """
    Validate and sanitize stock symbol.

    Args:
        symbol: Raw symbol input

    Returns:
        Sanitized symbol

    Raises:
        SymbolValidationError: If symbol is invalid

    Security: Prevents injection attacks via malicious symbols
    """
    if not symbol:
        raise SymbolValidationError("Symbol is required")

    # Remove whitespace, convert to uppercase
    symbol = symbol.strip().upper()

    # Check length (reasonable limit)
    if len(symbol) > 10:
        raise SymbolValidationError(f"Symbol too long: {len(symbol)} chars (max 10)")

    if len(symbol) < 1:
        raise SymbolValidationError("Symbol too short")

    # Check pattern (only alphanumeric, dots, hyphens)
    if not VALID_SYMBOL_PATTERN.match(symbol):
        raise SymbolValidationError(
            f"Invalid symbol format: {symbol}. "
            f"Only uppercase letters, numbers, dots, and hyphens allowed."
        )

    # Blacklist dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if pattern in symbol:
            raise SymbolValidationError(f"Symbol contains forbidden pattern: {pattern}")

    logger.debug(f"Validated symbol: {symbol}")
    return symbol


def validate_price(price: Decimal, symbol: str = "") -> Decimal:
    """
    Validate price data.

    Args:
        price: Price value
        symbol: Symbol (for logging)

    Returns:
        Validated price

    Raises:
        PriceValidationError: If price is invalid

    Security: Prevents corrupt/malicious price data from entering database
    """
    try:
        price = Decimal(str(price))
    except (InvalidOperation, ValueError) as e:
        raise PriceValidationError(f"Invalid price format for {symbol}: {e}")

    # Price must be positive
    if price <= 0:
        raise PriceValidationError(f"Price must be positive for {symbol}: {price}")

    # Reasonable upper limit (prevents obvious errors/attacks)
    if price > Decimal("10000000"):  # $10M per share
        logger.warning(
            f"Suspiciously high price for {symbol}: ${price}. "
            f"Possible data corruption or attack."
        )
        raise PriceValidationError(f"Price suspiciously high for {symbol}: ${price}")

    # Check precision (max 4 decimal places)
    if price.as_tuple().exponent < -4:
        logger.warning(f"Excessive precision for {symbol}: {price}")
        # Round to 4 decimal places
        price = price.quantize(Decimal("0.0001"))

    return price


def sanitize_text(text: Optional[str], max_length: int = 255) -> Optional[str]:
    """
    Sanitize text fields from external APIs.

    Args:
        text: Raw text
        max_length: Maximum allowed length

    Returns:
        Sanitized text or None

    Security: Prevents XSS, SQL injection, and data corruption
    """
    if not text:
        return None

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Remove control characters
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Remove most special characters (keep basic punctuation)
    text = re.sub(r"[^\w\s\.\-&,\(\)]", "", text)

    # Normalize whitespace
    text = " ".join(text.split())

    # Truncate to max length
    if len(text) > max_length:
        text = text[:max_length]
        logger.debug(f"Truncated text to {max_length} chars")

    return text.strip() if text.strip() else None


class ValidatedQuoteData(BaseModel):
    """
    Quote data with strict security validation.

    All data from external APIs must pass through this validator
    before being stored in the database.
    """

    symbol: str
    price: Decimal
    name: Optional[str] = None
    currency: str = "USD"
    exchange: Optional[str] = None
    volume: Optional[int] = None
    market_cap: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    year_high: Optional[Decimal] = None
    year_low: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None

    @field_validator("symbol")
    @classmethod
    def validate_symbol_field(cls, v):
        """Validate symbol."""
        return validate_symbol(v)

    @field_validator("price")
    @classmethod
    def validate_price_field(cls, v):
        """Validate price."""
        return validate_price(v)

    @field_validator("name", "exchange")
    @classmethod
    def validate_text_fields(cls, v):
        """Sanitize text fields."""
        return sanitize_text(v)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Validate currency code."""
        if not v:
            return "USD"
        v = v.upper().strip()
        if len(v) != 3 or not v.isalpha():
            logger.warning(f"Invalid currency code: {v}, using USD")
            return "USD"
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v):
        """Validate volume."""
        if v is None:
            return None
        if v < 0:
            logger.warning(f"Negative volume: {v}")
            return None
        if v > 10_000_000_000_000:  # 10 trillion shares (unrealistic)
            logger.warning(f"Suspiciously high volume: {v}")
            return None
        return v

    @field_validator("market_cap", "high", "low", "open", "previous_close", "year_high", "year_low")
    @classmethod
    def validate_optional_price(cls, v, info):
        """Validate optional price fields."""
        if v is None:
            return None
        try:
            return validate_price(v, info.field_name)
        except PriceValidationError:
            logger.warning(f"Invalid {info.field_name}: {v}")
            return None

    @field_validator("change", "change_percent", "dividend_yield", "pe_ratio")
    @classmethod
    def validate_optional_decimal(cls, v, info):
        """Validate optional decimal fields."""
        if v is None:
            return None
        try:
            decimal_val = Decimal(str(v))
            # Allow negative for change
            if abs(decimal_val) > Decimal("1000000"):
                logger.warning(f"Suspiciously large {info.field_name}: {v}")
                return None
            return decimal_val
        except (InvalidOperation, ValueError):
            logger.warning(f"Invalid {info.field_name}: {v}")
            return None


def validate_quote_response(raw_data: dict, symbol: str) -> ValidatedQuoteData:
    """
    Validate quote data from external API.

    Args:
        raw_data: Raw response from external API
        symbol: Expected symbol

    Returns:
        Validated quote data

    Raises:
        PriceValidationError: If validation fails

    Security: This is the CRITICAL security boundary between
    untrusted external data and our database.
    """
    try:
        # Ensure symbol matches
        if raw_data.get("symbol", "").upper() != symbol.upper():
            logger.warning(f"Symbol mismatch: expected {symbol}, " f"got {raw_data.get('symbol')}")
            raw_data["symbol"] = symbol  # Override with expected

        # Validate using Pydantic model
        validated = ValidatedQuoteData(**raw_data)

        logger.info(f"Successfully validated quote for {validated.symbol}: " f"${validated.price}")

        return validated

    except Exception as e:
        logger.error(f"Quote validation failed for {symbol}: {e}", exc_info=True)
