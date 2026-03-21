# State Tax Rate Provider System

This package replaces the static `app/constants/state_tax_rates.py` dict with a
pluggable provider architecture, enabling bracket-aware marginal rate lookups that
can be sourced from live data, cached, or fall back to offline approximations.

## What it does

`TaxProjectionService` calls `await provider.get_rate(state, filing_status, income)` to
determine the effective marginal state tax rate for a given taxpayer profile.  The
provider is resolved once per process via the registry and shared across all requests.

## Available providers

### `TaxGraphsProvider` (default)

Fetches full income tax bracket data from the
[taxgraphs](https://github.com/hermantran/taxgraphs) GitHub repository.

**Data source:**
`https://raw.githubusercontent.com/hermantran/taxgraphs/master/data/{year}/taxes.json`

Licensed under **CC BY-NC 4.0** by Herman Tran.

**Behaviour:**
1. Try Redis cache for the current tax year (`state_tax_rates:{year}`, TTL 24 hours).
2. If cache misses, fetch live from GitHub for the current year.
3. If the current year returns 404, retry with `current_year - 1`.
4. On any failure (network error, Redis unavailable), fall back to `StaticStateTaxProvider`.

### `StaticStateTaxProvider`

Wraps the bundled `STATE_TAX_RATES` dict from `app/constants/state_tax_rates.py`.
Returns a flat-rate approximation (effective rate at ~$75k AGI for progressive states).
Always available — no network or cache required.  Tax year is 2024.

## Fallback chain

```
TaxGraphsProvider
  └─ Redis cache (TTL 24 h)
       └─ Live HTTP fetch (GitHub raw)
            └─ StaticStateTaxProvider (bundled dict)
```

## Cache behaviour

- Cache key: `state_tax_rates:{year}` (e.g. `state_tax_rates:2025`)
- TTL: 86400 seconds (24 hours)
- Backend: Redis at `settings.REDIS_URL`
- If Redis is unavailable the provider transparently skips caching; the live fetch
  result is still used for the current request.

## Filing status mapping

The taxgraphs data uses `"single"` and `"married"`.  The following internal filing
status values are mapped before lookup:

| Internal value          | taxgraphs key |
|-------------------------|---------------|
| `"single"`              | `"single"`    |
| `"married"`             | `"married"`   |
| `"married_jointly"`     | `"married"`   |
| `"married_filing_jointly"` | `"married"` |

## How to add a new provider

1. Implement the `StateTaxProvider` ABC from `base.py`:

```python
from app.services.tax_rate_providers.base import StateTaxProvider, StateTaxBracket

class MyCustomProvider(StateTaxProvider):
    def source_name(self) -> str:
        return "my_custom_provider"

    def tax_year(self) -> int:
        return 2025

    async def get_rate(self, state: str, filing_status: str, income: float) -> float:
        # your implementation
        ...

    async def get_brackets(self, state: str, filing_status: str) -> list[StateTaxBracket]:
        # your implementation
        ...
```

2. Register it at application startup (e.g. in `app/main.py` or a startup event):

```python
from app.services.tax_rate_providers import set_provider
from myapp.providers import MyCustomProvider

set_provider(MyCustomProvider())
```

## Testing

The registry singleton can be reset between tests:

```python
import app.services.tax_rate_providers as registry

def teardown():
    registry._provider = None
```

Use `set_provider()` to inject a test double without touching the network or Redis.
