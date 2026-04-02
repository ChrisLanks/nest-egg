"""
PM Audit Round 74 — Third-pass hardcoded constant cleanup.

Fixes:
1. RETIREMENT.SURVIVOR_SPENDING_REDUCTION = 0.20 added to financial.py
2. smart_insights.py expected_return Query default uses FIRE.DEFAULT_EXPECTED_RETURN
3. tax_buckets.py growth_rate Query default uses FIRE.DEFAULT_GROWTH_RATE
4. financial_planning.py spending_reduction_pct Query default uses
   RETIREMENT.SURVIVOR_SPENDING_REDUCTION
"""

import inspect


# ---------------------------------------------------------------------------
# 1. financial.py — new RETIREMENT.SURVIVOR_SPENDING_REDUCTION constant
# ---------------------------------------------------------------------------

def test_retirement_survivor_spending_reduction_exists():
    from app.constants.financial import RETIREMENT
    assert hasattr(RETIREMENT, "SURVIVOR_SPENDING_REDUCTION")


def test_retirement_survivor_spending_reduction_value():
    from app.constants.financial import RETIREMENT
    assert RETIREMENT.SURVIVOR_SPENDING_REDUCTION == 0.20


# ---------------------------------------------------------------------------
# 2. smart_insights.py — expected_return uses FIRE constant
# ---------------------------------------------------------------------------

def test_smart_insights_imports_fire():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE" in src


def test_smart_insights_no_bare_007_expected_return():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod)
    assert "Query(0.07," not in src


def test_smart_insights_uses_fire_expected_return():
    import app.api.v1.smart_insights as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_EXPECTED_RETURN" in src


# ---------------------------------------------------------------------------
# 3. tax_buckets.py — growth_rate uses FIRE.DEFAULT_GROWTH_RATE
# ---------------------------------------------------------------------------

def test_tax_buckets_imports_fire():
    import app.api.v1.tax_buckets as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE" in src


def test_tax_buckets_no_bare_006_growth_rate():
    import app.api.v1.tax_buckets as mod
    src = inspect.getsource(mod)
    assert "Query(0.06," not in src


def test_tax_buckets_uses_fire_default_growth_rate():
    import app.api.v1.tax_buckets as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_GROWTH_RATE" in src


# ---------------------------------------------------------------------------
# 4. financial_planning.py — spending_reduction_pct uses RETIREMENT constant
# ---------------------------------------------------------------------------

def test_financial_planning_imports_retirement():
    import app.api.v1.financial_planning as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import RETIREMENT" in src


def test_financial_planning_no_bare_020_spending_reduction():
    import app.api.v1.financial_planning as mod
    src = inspect.getsource(mod)
    assert "Query(0.20," not in src


def test_financial_planning_uses_survivor_spending_reduction():
    import app.api.v1.financial_planning as mod
    src = inspect.getsource(mod)
    assert "RETIREMENT.SURVIVOR_SPENDING_REDUCTION" in src
