"""Tests for cash account APY improvements and valuation-providers route fix.

Covers:
1. /accounts/valuation-providers was returning 422 because the route was
   defined after /{account_id}, causing FastAPI to try to parse the literal
   string "valuation-providers" as a UUID. Fixed by moving the route before
   the /{account_id} catch-all.

2. RetirementMonteCarloService now has _CASH_DEFAULT_APY fallbacks so that
   cash accounts without an explicit interest_rate still contribute a
   reasonable rate to retirement projections instead of 0%.
"""

import inspect
from decimal import Decimal


# ─── Route ordering fix ───────────────────────────────────────────────────────


def test_valuation_providers_route_before_account_id_catch_all():
    """GET /valuation-providers must be registered before GET /{account_id}."""
    from app.api.v1 import accounts as accounts_module

    routes = [r.path for r in accounts_module.router.routes]
    vp_idx = next((i for i, p in enumerate(routes) if p == "/valuation-providers"), None)
    catch_idx = next((i for i, p in enumerate(routes) if p == "/{account_id}"), None)
    assert vp_idx is not None, "/valuation-providers route must exist"
    assert catch_idx is not None, "/{account_id} route must exist"
    assert vp_idx < catch_idx, (
        "/valuation-providers must come before /{account_id} to avoid 422 UUID parse error"
    )


def test_valuation_providers_not_duplicated():
    """There must be exactly one /valuation-providers GET route."""
    from app.api.v1 import accounts as accounts_module
    from fastapi.routing import APIRoute

    vp_routes = [
        r for r in accounts_module.router.routes
        if isinstance(r, APIRoute)
        and r.path == "/valuation-providers"
        and "GET" in r.methods
    ]
    assert len(vp_routes) == 1, f"Expected 1 /valuation-providers GET route, found {len(vp_routes)}"


# ─── Cash APY defaults ────────────────────────────────────────────────────────


def test_cash_default_apy_map_exists():
    """_CASH_DEFAULT_APY must exist on RetirementMonteCarloService."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService

    assert hasattr(RetirementMonteCarloService, "_CASH_DEFAULT_APY"), (
        "_CASH_DEFAULT_APY dict must be defined on RetirementMonteCarloService"
    )
    apy = RetirementMonteCarloService._CASH_DEFAULT_APY
    assert len(apy) >= 3, "Must have defaults for at least 3 cash account types"


def test_cash_default_apy_values_are_positive():
    """All default APY values must be positive Decimals."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService

    for acct_type, rate in RetirementMonteCarloService._CASH_DEFAULT_APY.items():
        assert isinstance(rate, Decimal), f"{acct_type}: rate must be Decimal"
        assert rate > Decimal("0"), f"{acct_type}: default APY must be > 0"
        assert rate < Decimal("20"), f"{acct_type}: default APY sanity check < 20%"


def test_cash_default_apy_checking_is_conservative():
    """Checking account default should be conservative (< 2%)."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService
    from app.models.account import AccountType

    rate = RetirementMonteCarloService._CASH_DEFAULT_APY.get(AccountType.CHECKING)
    assert rate is not None, "Must have a default for CHECKING"
    assert rate < Decimal("2"), "Checking default APY should be conservative (< 2%)"


def test_cash_rate_fallback_used_when_no_interest_rate():
    """When account.interest_rate is None, _gather_account_data must use the fallback."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService

    source = inspect.getsource(RetirementMonteCarloService._gather_account_data)
    # Must check interest_rate is not None explicitly (not just `or`)
    assert "interest_rate is not None" in source, (
        "Must check `account.interest_rate is not None` to distinguish 0.0 from unset"
    )
    assert "_CASH_DEFAULT_APY" in source, (
        "Must reference _CASH_DEFAULT_APY as fallback in _gather_account_data"
    )


def test_explicit_zero_rate_preserved():
    """An explicit interest_rate of 0 must NOT be replaced by the fallback."""
    from app.services.retirement.monte_carlo_service import RetirementMonteCarloService

    source = inspect.getsource(RetirementMonteCarloService._gather_account_data)
    # The pattern must be `is not None` (not `or`), so 0.0 passes through
    assert "account.interest_rate is not None" in source, (
        "Using `is not None` ensures explicit 0% rate is kept (not replaced by fallback)"
    )
