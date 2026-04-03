"""
PM Audit Round 81 — Production hardening: rate limits, input validation, error guards.

Changes covered:
1. financial_plan.py: rate limit (10/min) on /summary; net worth section
   wrapped in try/except so it falls back gracefully instead of 500-ing
2. estate.py: rate limit (30/min) on /tax-exposure
3. transactions.py: min_amount/max_amount query params now have ge=0, le=999_999_999_999.99
4. financial.py: NET_WORTH_MILESTONES.TIERS replaces hardcoded list in dashboard.py
5. dashboard.py: milestone loop uses NET_WORTH_MILESTONES.TIERS
"""

import inspect


# ---------------------------------------------------------------------------
# 1. financial_plan.py — rate_limit_service imported and used on /summary
# ---------------------------------------------------------------------------

def test_financial_plan_imports_rate_limit_service():
    import app.api.v1.financial_plan as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src


def test_financial_plan_summary_has_rate_limit():
    import app.api.v1.financial_plan as mod
    src = inspect.getsource(mod.get_financial_plan_summary)
    assert "check_rate_limit" in src


def test_financial_plan_summary_rate_limit_max_10():
    import app.api.v1.financial_plan as mod
    src = inspect.getsource(mod.get_financial_plan_summary)
    assert "max_requests=10" in src


# ---------------------------------------------------------------------------
# 2. financial_plan.py — net worth section guarded with try/except
# ---------------------------------------------------------------------------

def test_financial_plan_net_worth_section_guarded():
    import app.api.v1.financial_plan as mod
    src = inspect.getsource(mod.get_financial_plan_summary)
    # Both the try and the fallback dict must be present
    assert "get_current_breakdown" in src
    assert "net worth section failed" in src


# ---------------------------------------------------------------------------
# 3. estate.py — rate_limit_service imported and used on /tax-exposure
# ---------------------------------------------------------------------------

def test_estate_imports_rate_limit_service():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "rate_limit_service" in src


def test_estate_tax_exposure_has_rate_limit():
    # Rate limit is applied at router level via _rate_limit dependency
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "check_rate_limit" in src
    assert "_rate_limit" in src


def test_estate_tax_exposure_rate_limit_max_30():
    # Rate limit max is set in the _rate_limit function, not per-endpoint
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "max_requests=30" in src


# ---------------------------------------------------------------------------
# 4. transactions.py — amount query params are bounded
# ---------------------------------------------------------------------------

def test_transactions_list_min_amount_has_ge_bound():
    import app.api.v1.transactions as mod
    src = inspect.getsource(mod)
    # ge=0 must be present on the min_amount Query
    assert "ge=0" in src


def test_transactions_list_max_amount_has_le_bound():
    import app.api.v1.transactions as mod
    src = inspect.getsource(mod)
    assert "le=999_999_999_999.99" in src


# ---------------------------------------------------------------------------
# 5. NET_WORTH_MILESTONES in financial.py
# ---------------------------------------------------------------------------

def test_net_worth_milestones_class_exists():
    from app.constants.financial import NET_WORTH_MILESTONES
    assert hasattr(NET_WORTH_MILESTONES, "TIERS")


def test_net_worth_milestones_tiers_is_list():
    from app.constants.financial import NET_WORTH_MILESTONES
    assert isinstance(NET_WORTH_MILESTONES.TIERS, list)


def test_net_worth_milestones_contains_1_million():
    from app.constants.financial import NET_WORTH_MILESTONES
    assert 1_000_000 in NET_WORTH_MILESTONES.TIERS


def test_net_worth_milestones_tiers_sorted():
    from app.constants.financial import NET_WORTH_MILESTONES
    assert NET_WORTH_MILESTONES.TIERS == sorted(NET_WORTH_MILESTONES.TIERS)


# ---------------------------------------------------------------------------
# 6. dashboard.py — uses NET_WORTH_MILESTONES, no bare hardcoded list
# ---------------------------------------------------------------------------

def test_dashboard_imports_net_worth_milestones():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    assert "NET_WORTH_MILESTONES" in src


def test_dashboard_no_bare_milestone_thresholds():
    import app.api.v1.dashboard as mod
    src = inspect.getsource(mod)
    # The old hardcoded list must be gone
    assert "[50000, 100000, 250000, 500000, 750000, 1000000, 2000000, 5000000]" not in src
