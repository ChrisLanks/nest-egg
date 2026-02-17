# Market Data Security Analysis

## ⚠️ Security Concerns with Unofficial Yahoo Finance Library

### Critical Issues Identified

#### 1. **Excessive Database Access** (HIGH RISK)
**Problem:** Market data provider has full database session access
```python
# Current implementation in market_data.py
@router.post("/holdings/{holding_id}/refresh-price")
async def refresh_holding_price(
    holding_id: UUID,
    db: AsyncSession = Depends(get_db),  # ❌ Full DB access!
    current_user: User = Depends(get_current_user),
):
```

**Risk:** If yfinance is compromised, malicious code could:
- Read all user data (accounts, balances, transactions)
- Access encrypted tokens (Plaid, Teller)
- Read SECRET_KEY, MASTER_ENCRYPTION_KEY from environment
- Exfiltrate sensitive financial data

**Impact:** CRITICAL - Full database compromise

---

#### 2. **No Input Validation** (MEDIUM RISK)
**Problem:** Symbol inputs not sanitized before external API calls
```python
# Current code allows any symbol
quote = await market_data.get_quote(symbol.upper())
```

**Risk:**
- SSRF attacks via malicious symbols
- Command injection if yfinance has vulnerabilities
- DoS via expensive queries

**Impact:** MEDIUM - Could enable attacks

---

#### 3. **No Response Validation** (MEDIUM RISK)
**Problem:** Trust data from yfinance without validation
```python
# No validation of response data
price=Decimal(str(current_price))  # Could throw with malicious data
```

**Risk:**
- Malicious data could crash application
- SQL injection via crafted responses
- Data corruption in database

**Impact:** MEDIUM - Application availability

---

#### 4. **No Rate Limiting** (LOW RISK)
**Problem:** No limits on calls to external APIs
```python
# Can make unlimited calls to Yahoo
quote = await market_data.get_quote(symbol)
```

**Risk:**
- IP ban from Yahoo Finance
- Resource exhaustion
- DoS from malicious users

**Impact:** LOW - Service disruption

---

#### 5. **Dependency Chain** (MEDIUM RISK)
**Problem:** yfinance has 12+ dependencies
```
yfinance → pandas → numpy → lxml → beautifulsoup4 → ...
```

**Risk:**
- Supply chain attacks
- Vulnerable dependencies
- Large attack surface

**Impact:** MEDIUM - Depends on vulnerabilities

---

## 🛡️ Security Recommendations

### Priority 1: Isolate Market Data Service (CRITICAL)

**Solution:** Separate market data into isolated microservice

```
┌─────────────────────────────────────┐
│   Main App (Trusted)                │
│   - Has DB access                   │
│   - Has secrets                     │
│   - No external APIs                │
└─────────────┬───────────────────────┘
              │ HTTP/API only
              │ (no DB access)
              ▼
┌─────────────────────────────────────┐
│   Market Data Service (Untrusted)   │
│   - NO database access              │
│   - NO secrets                      │
│   - Only fetches prices             │
│   - Sandboxed/containerized         │
└─────────────────────────────────────┘
```

**Implementation:**

```python
# New isolated service: market_data_service.py
# Runs as separate process/container
# Only exposes HTTP API for price fetching

class IsolatedMarketDataService:
    """Isolated service with no database access."""

    def __init__(self):
        # NO database session
        # NO access to secrets
        # Only environment: MARKET_DATA_PROVIDER
        pass

    async def get_quote(self, symbol: str) -> QuoteData:
        """Fetch quote - no DB access needed."""
        # Validate input
        # Call external API
        # Validate response
        # Return ONLY price data
        pass
```

**Main app calls via HTTP:**
```python
# In main app - no direct yfinance import
async def refresh_holding_price(holding_id: UUID, db: AsyncSession):
    # Get holding from DB
    holding = await db.get(Holding, holding_id)

    # Call isolated service via HTTP (internal network only)
    response = await httpx.post(
        "http://market-data-service:8001/quote",
        json={"symbol": holding.symbol},
        timeout=5.0
    )
    quote = response.json()

    # Update DB with validated data
    holding.current_price = Decimal(quote["price"])
    await db.commit()
```

**Benefits:**
- ✅ yfinance cannot access database
- ✅ yfinance cannot access secrets
- ✅ Easy to restart if compromised
- ✅ Can run in sandboxed container
- ✅ Network-level isolation possible

---

### Priority 2: Input Validation (HIGH)

**Solution:** Strict symbol validation

```python
import re

VALID_SYMBOL_PATTERN = re.compile(r'^[A-Z0-9\.\-]{1,10}$')

def validate_symbol(symbol: str) -> str:
    """Validate and sanitize stock symbol."""
    if not symbol:
        raise ValueError("Symbol is required")

    # Convert to uppercase
    symbol = symbol.upper().strip()

    # Check length
    if len(symbol) > 10:
        raise ValueError("Symbol too long")

    # Check pattern (alphanumeric, dots, hyphens only)
    if not VALID_SYMBOL_PATTERN.match(symbol):
        raise ValueError(f"Invalid symbol format: {symbol}")

    # Blacklist dangerous patterns
    dangerous = ["../", "\\", "|", ";", "&", "$", "`"]
    if any(d in symbol for d in dangerous):
        raise ValueError("Symbol contains forbidden characters")

    return symbol
```

**Usage:**
```python
@router.get("/quote/{symbol}")
async def get_quote(symbol: str, ...):
    # Validate BEFORE calling external API
    symbol = validate_symbol(symbol)
    quote = await market_data.get_quote(symbol)
```

---

### Priority 3: Response Validation (HIGH)

**Solution:** Strict output validation

```python
from decimal import Decimal, InvalidOperation
from pydantic import validator

class ValidatedQuoteData(BaseModel):
    """Quote data with strict validation."""

    symbol: str
    price: Decimal
    name: Optional[str] = None

    @validator('price')
    def validate_price(cls, v):
        """Ensure price is reasonable."""
        if v <= 0:
            raise ValueError("Price must be positive")
        if v > 1_000_000:  # $1M per share max
            raise ValueError("Price suspiciously high")
        return v

    @validator('symbol')
    def validate_symbol(cls, v):
        """Sanitize symbol."""
        return validate_symbol(v)

    @validator('name')
    def validate_name(cls, v):
        """Sanitize name to prevent injection."""
        if not v:
            return None
        # Remove HTML tags, special chars
        v = re.sub(r'<[^>]+>', '', v)
        v = re.sub(r'[^\w\s\.\-&]', '', v)
        return v[:255]  # Max length
```

**Wrapper for external data:**
```python
async def get_quote_safe(self, symbol: str) -> QuoteData:
    """Get quote with validation."""
    try:
        # Call yfinance
        raw_quote = await self._get_quote_from_yfinance(symbol)

        # Validate response using Pydantic
        validated = ValidatedQuoteData(**raw_quote)

        return validated

    except ValidationError as e:
        logger.error(f"Invalid data from yfinance for {symbol}: {e}")
        raise ValueError(f"Invalid quote data for {symbol}")
    except Exception as e:
        logger.error(f"Error fetching quote for {symbol}: {e}")
        raise
```

---

### Priority 4: Rate Limiting (MEDIUM)

**Solution:** Implement rate limits

```python
from functools import wraps
from time import time
from collections import defaultdict

class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, calls_per_minute: int = 100):
        self.calls_per_minute = calls_per_minute
        self.calls = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if call is allowed."""
        now = time()
        minute_ago = now - 60

        # Remove old calls
        self.calls[key] = [
            t for t in self.calls[key]
            if t > minute_ago
        ]

        # Check limit
        if len(self.calls[key]) >= self.calls_per_minute:
            return False

        # Record call
        self.calls[key].append(now)
        return True

# Global limiter
rate_limiter = RateLimiter(calls_per_minute=100)

@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    current_user: User = Depends(get_current_user)
):
    # Rate limit per user
    if not rate_limiter.is_allowed(f"user:{current_user.id}"):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later."
        )

    # ... rest of endpoint
```

---

### Priority 5: Network Security (MEDIUM)

**Solution:** Restrict external network access

```python
import httpx
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    "query1.finance.yahoo.com",
    "query2.finance.yahoo.com",
    "finance.yahoo.com"
]

class SecureHTTPClient:
    """HTTP client with domain whitelisting."""

    async def get(self, url: str, **kwargs):
        """Make GET request to whitelisted domain only."""
        # Parse URL
        parsed = urlparse(url)

        # Check domain whitelist
        if parsed.hostname not in ALLOWED_DOMAINS:
            raise SecurityError(f"Domain not allowed: {parsed.hostname}")

        # Enforce HTTPS
        if parsed.scheme != "https":
            raise SecurityError("Only HTTPS allowed")

        # Make request with timeout
        async with httpx.AsyncClient(
            timeout=5.0,
            follow_redirects=False  # No redirects
        ) as client:
            return await client.get(url, **kwargs)
```

---

### Priority 6: Monitoring & Alerting (MEDIUM)

**Solution:** Log all external API calls

```python
import structlog

logger = structlog.get_logger()

async def get_quote(self, symbol: str) -> QuoteData:
    """Get quote with full audit logging."""

    # Log request
    logger.info(
        "external_api_call",
        provider="yahoo_finance",
        symbol=symbol,
        endpoint="quote"
    )

    start_time = time()

    try:
        quote = await self._fetch_quote(symbol)

        # Log success
        logger.info(
            "external_api_success",
            provider="yahoo_finance",
            symbol=symbol,
            duration_ms=(time() - start_time) * 1000,
            price=float(quote.price)
        )

        return quote

    except Exception as e:
        # Log failure
        logger.error(
            "external_api_failure",
            provider="yahoo_finance",
            symbol=symbol,
            error=str(e),
            duration_ms=(time() - start_time) * 1000
        )
        raise
```

**Alert on anomalies:**
```python
# Alert if price changes >50% in one update
if abs(new_price - old_price) / old_price > 0.5:
    logger.warning(
        "suspicious_price_change",
        symbol=symbol,
        old_price=old_price,
        new_price=new_price,
        change_percent=((new_price - old_price) / old_price) * 100
    )
    # Send alert to admin
```

---

## 🔒 Recommended Security Architecture

### Layered Defense

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: API Gateway                                       │
│  - Rate limiting (100 req/min per user)                     │
│  - Input validation (symbol format)                         │
│  - Authentication check                                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Layer 2: Main Application                                  │
│  - Database access (trusted zone)                           │
│  - Business logic                                           │
│  - Secrets management                                       │
│  - NO direct external API calls                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Internal HTTP (network isolated)
┌─────────────────────▼───────────────────────────────────────┐
│  Layer 3: Market Data Service (Sandboxed)                   │
│  - NO database access                                       │
│  - NO secrets                                               │
│  - Response validation                                      │
│  - Domain whitelisting                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS only (yahoo.com)
┌─────────────────────▼───────────────────────────────────────┐
│  Layer 4: External API (Yahoo Finance)                      │
│  - Untrusted                                                │
│  - Unofficial                                               │
│  - Could be malicious                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Implementation Checklist

### Immediate (Critical)
- [ ] Remove direct database access from market data provider
- [ ] Implement input validation for symbols
- [ ] Add response validation with Pydantic
- [ ] Add rate limiting per user

### Short-term (High Priority)
- [ ] Isolate market data into separate service
- [ ] Implement domain whitelisting
- [ ] Add comprehensive logging
- [ ] Set up monitoring alerts

### Medium-term (Defense in Depth)
- [ ] Run market data service in sandboxed container
- [ ] Implement circuit breaker pattern
- [ ] Add anomaly detection for prices
- [ ] Regular dependency security audits

---

## 🎯 Alternative: Use Official APIs Only

### Option A: Alpha Vantage (Official, Free Tier)
```python
# Official API with authentication
# Rate limits: 500 calls/day (enforced by API key)
# More secure than scraping
```

**Pros:**
- ✅ Official API (not scraping)
- ✅ Requires API key (rate limiting enforced)
- ✅ SLA and support
- ✅ Less likely to break

**Cons:**
- ⚠️ 500 calls/day limit
- ⚠️ Requires API key management

### Option B: Hybrid Approach (Recommended)
```python
# Use Alpha Vantage for automated updates (500/day plenty)
# Use Yahoo Finance as fallback for manual refreshes
# Isolate both in separate service
```

**Configuration:**
```bash
# Default: Alpha Vantage (official)
MARKET_DATA_PROVIDER=alpha_vantage
ALPHA_VANTAGE_API_KEY=your_free_key

# Fallback: Yahoo Finance (unofficial, no key)
FALLBACK_PROVIDER=yahoo_finance
```

---

## 💡 Recommendation

**For Production:**
1. **Isolate market data service** (separate container/process)
2. **Use Alpha Vantage as primary** (official, free 500/day)
3. **Keep Yahoo Finance as fallback** (for manual refreshes)
4. **Implement all validation layers**
5. **Add comprehensive monitoring**

**For Development/Testing:**
- Yahoo Finance is fine (with validation)
- Add rate limiting
- Log all external calls

This gives you the best of both worlds:
- ✅ FREE (both have free tiers)
- ✅ Secure (Alpha Vantage is official)
- ✅ Reliable (fallback to Yahoo if quota exceeded)
- ✅ Isolated (no access to sensitive data)
