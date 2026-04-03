"""
PM Audit Round 83 — Router-level rate limits on analytics routers + cost basis constants.

Changes covered:
1. income_expenses.py: router-level Depends(_rate_limit) — covers all 14 endpoints
2. charitable_giving.py: router-level Depends(_rate_limit) — covers all 4 endpoints
3. employer_match.py: router-level Depends(_rate_limit) — covers both endpoints
4. hsa.py: router-level Depends(_rate_limit) — covers all 8 endpoints
5. cost_basis_aging.py: router-level Depends(_rate_limit); bare 30 and 1000
   replaced with SMART_INSIGHTS.DAYS_TO_LONG_TERM_WARNING and TAX_LOSS_HARVEST_MIN_USD
6. financial.py: SMART_INSIGHTS.DAYS_TO_LONG_TERM_WARNING and TAX_LOSS_HARVEST_MIN_USD added
"""

import inspect


# ---------------------------------------------------------------------------
# 1. income_expenses.py — router-level rate limit dependency
# ---------------------------------------------------------------------------

def test_income_expenses_has_module_rate_limit():
    import app.api.v1.income_expenses as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src
    assert "_rate_limit" in src


def test_income_expenses_router_uses_rate_limit_dependency():
    import app.api.v1.income_expenses as mod
    src = inspect.getsource(mod)
    # Router declaration must include the dependency
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_income_expenses_rate_limit_uses_user_id():
    import app.api.v1.income_expenses as mod
    src = inspect.getsource(mod._rate_limit)
    assert "current_user.id" in src


# ---------------------------------------------------------------------------
# 2. charitable_giving.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_charitable_giving_router_uses_rate_limit_dependency():
    import app.api.v1.charitable_giving as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 3. employer_match.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_employer_match_router_uses_rate_limit_dependency():
    import app.api.v1.employer_match as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 4. hsa.py — router-level rate limit
# ---------------------------------------------------------------------------

def test_hsa_router_uses_rate_limit_dependency():
    import app.api.v1.hsa as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


# ---------------------------------------------------------------------------
# 5. cost_basis_aging.py — router-level rate limit + constants
# ---------------------------------------------------------------------------

def test_cost_basis_aging_router_uses_rate_limit_dependency():
    import app.api.v1.cost_basis_aging as mod
    src = inspect.getsource(mod)
    assert 'dependencies=[Depends(_rate_limit)]' in src


def test_cost_basis_aging_no_bare_30_threshold():
    import app.api.v1.cost_basis_aging as mod
    src = inspect.getsource(mod)
    assert "days_to_long_term <= 30" not in src


def test_cost_basis_aging_no_bare_1000_threshold():
    import app.api.v1.cost_basis_aging as mod
    src = inspect.getsource(mod)
    assert "st_loss < -1000" not in src


def test_cost_basis_aging_uses_smart_insights_constant():
    import app.api.v1.cost_basis_aging as mod
    src = inspect.getsource(mod)
    assert "SMART_INSIGHTS" in src


# ---------------------------------------------------------------------------
# 6. financial.py — new SMART_INSIGHTS constants
# ---------------------------------------------------------------------------

def test_days_to_long_term_warning_constant():
    from app.constants.financial import SMART_INSIGHTS
    assert hasattr(SMART_INSIGHTS, "DAYS_TO_LONG_TERM_WARNING")
    assert SMART_INSIGHTS.DAYS_TO_LONG_TERM_WARNING == 30


def test_tax_loss_harvest_min_usd_constant():
    from app.constants.financial import SMART_INSIGHTS
    assert hasattr(SMART_INSIGHTS, "TAX_LOSS_HARVEST_MIN_USD")
    assert SMART_INSIGHTS.TAX_LOSS_HARVEST_MIN_USD == 1_000
