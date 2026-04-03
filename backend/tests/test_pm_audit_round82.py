"""
PM Audit Round 82 — Rate limits on compute endpoints + DB indexes + constants.

Changes covered:
1. stress_test.py: rate limit on /run (30/min) and /run-all (10/min)
2. backdoor_roth.py: rate limit (20/min) on /backdoor-roth-analysis
3. rmd_planner.py: rate limit (20/min) on /rmd-planner
4. pension_modeler.py: rate limit (20/min) on /pension-model; hardcoded
   break-even thresholds (15/20 yr) replaced with PENSION_MODELER constants
5. pe_performance.py: rate limit (20/min) on /portfolio
6. liquidity_dashboard.py: rate limit (20/min) on /liquidity; _TARGET_MONTHS
   and 5_000 default replaced with LIQUIDITY constants
7. financial.py: LIQUIDITY and PENSION_MODELER classes added
8. holding.py: 3 new composite indexes (org_ticker, asset_type, sector)
9. savings_goal.py: new index ix_savings_goals_org_target_date
10. Migration r80_holding_goal_idx creates all 4 new indexes
"""

import inspect


# ---------------------------------------------------------------------------
# 1. stress_test.py — rate limits on both run endpoints
# ---------------------------------------------------------------------------

def test_stress_test_run_scenario_has_rate_limit():
    import app.api.v1.stress_test as mod
    src = inspect.getsource(mod.run_scenario)
    assert "check_rate_limit" in src


def test_stress_test_run_all_has_rate_limit():
    import app.api.v1.stress_test as mod
    src = inspect.getsource(mod.run_all_scenarios)
    assert "check_rate_limit" in src


def test_stress_test_run_all_tighter_limit():
    import app.api.v1.stress_test as mod
    src = inspect.getsource(mod.run_all_scenarios)
    assert "max_requests=10" in src


# ---------------------------------------------------------------------------
# 2. backdoor_roth.py — rate limit
# ---------------------------------------------------------------------------

def test_backdoor_roth_has_rate_limit():
    import app.api.v1.backdoor_roth as mod
    src = inspect.getsource(mod.get_backdoor_roth_analysis)
    assert "check_rate_limit" in src


# ---------------------------------------------------------------------------
# 3. rmd_planner.py — rate limit
# ---------------------------------------------------------------------------

def test_rmd_planner_has_rate_limit():
    import app.api.v1.rmd_planner as mod
    src = inspect.getsource(mod.get_rmd_planner)
    assert "check_rate_limit" in src


# ---------------------------------------------------------------------------
# 4. pension_modeler.py — rate limit + constants
# ---------------------------------------------------------------------------

def test_pension_modeler_has_rate_limit():
    import app.api.v1.pension_modeler as mod
    src = inspect.getsource(mod.get_pension_model)
    assert "check_rate_limit" in src


def test_pension_modeler_no_bare_15():
    import app.api.v1.pension_modeler as mod
    src = inspect.getsource(mod)
    assert "break_even_years < 15" not in src


def test_pension_modeler_no_bare_20_hurdle():
    import app.api.v1.pension_modeler as mod
    src = inspect.getsource(mod)
    assert "break_even_years > 20" not in src


def test_pension_modeler_uses_pension_modeler_constant():
    import app.api.v1.pension_modeler as mod
    src = inspect.getsource(mod)
    assert "PENSION_MODELER" in src


# ---------------------------------------------------------------------------
# 5. pe_performance.py — rate limit on /portfolio
# ---------------------------------------------------------------------------

def test_pe_portfolio_has_rate_limit():
    import app.api.v1.pe_performance as mod
    src = inspect.getsource(mod.get_pe_portfolio)
    assert "check_rate_limit" in src


# ---------------------------------------------------------------------------
# 6. liquidity_dashboard.py — rate limit + no bare 5_000 / 6.0
# ---------------------------------------------------------------------------

def test_liquidity_dashboard_has_rate_limit():
    import app.api.v1.liquidity_dashboard as mod
    src = inspect.getsource(mod.get_liquidity_dashboard)
    assert "check_rate_limit" in src


def test_liquidity_dashboard_no_bare_5000():
    import app.api.v1.liquidity_dashboard as mod
    src = inspect.getsource(mod)
    assert "5_000.0" not in src
    assert "5000.0" not in src


def test_liquidity_dashboard_uses_liquidity_constant():
    import app.api.v1.liquidity_dashboard as mod
    src = inspect.getsource(mod)
    assert "LIQUIDITY" in src


# ---------------------------------------------------------------------------
# 7. financial.py — LIQUIDITY and PENSION_MODELER classes
# ---------------------------------------------------------------------------

def test_liquidity_class_exists():
    from app.constants.financial import LIQUIDITY
    assert hasattr(LIQUIDITY, "TARGET_EMERGENCY_FUND_MONTHS")
    assert hasattr(LIQUIDITY, "DEFAULT_MONTHLY_SPENDING_ESTIMATE")


def test_liquidity_target_months_value():
    from app.constants.financial import LIQUIDITY
    assert LIQUIDITY.TARGET_EMERGENCY_FUND_MONTHS == 6.0


def test_liquidity_default_spending_value():
    from app.constants.financial import LIQUIDITY
    assert LIQUIDITY.DEFAULT_MONTHLY_SPENDING_ESTIMATE == 5_000.0


def test_pension_modeler_class_exists():
    from app.constants.financial import PENSION_MODELER
    assert hasattr(PENSION_MODELER, "BREAK_EVEN_ANNUITY_HURDLE_YEARS")
    assert hasattr(PENSION_MODELER, "BREAK_EVEN_LUMP_SUM_HURDLE_YEARS")
    assert hasattr(PENSION_MODELER, "LIFETIME_VALUE_WINDOWS")


def test_pension_modeler_hurdle_values():
    from app.constants.financial import PENSION_MODELER
    assert PENSION_MODELER.BREAK_EVEN_ANNUITY_HURDLE_YEARS == 15
    assert PENSION_MODELER.BREAK_EVEN_LUMP_SUM_HURDLE_YEARS == 20
    assert PENSION_MODELER.LIFETIME_VALUE_WINDOWS == [20, 25]


# ---------------------------------------------------------------------------
# 8. holding.py — 3 new composite indexes in __table_args__
# ---------------------------------------------------------------------------

def test_holding_org_ticker_index():
    from app.models.holding import Holding
    names = [i.name for i in Holding.__table__.indexes]
    assert "ix_holdings_org_ticker" in names


def test_holding_asset_type_index():
    from app.models.holding import Holding
    names = [i.name for i in Holding.__table__.indexes]
    assert "ix_holdings_asset_type" in names


def test_holding_sector_index():
    from app.models.holding import Holding
    names = [i.name for i in Holding.__table__.indexes]
    assert "ix_holdings_sector" in names


# ---------------------------------------------------------------------------
# 9. savings_goal.py — target_date index
# ---------------------------------------------------------------------------

def test_savings_goal_target_date_index():
    from app.models.savings_goal import SavingsGoal
    names = [i.name for i in SavingsGoal.__table__.indexes]
    assert "ix_savings_goals_org_target_date" in names


# ---------------------------------------------------------------------------
# 10. Migration r80_holding_goal_idx
# ---------------------------------------------------------------------------

def test_migration_r80_exists():
    import pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    found = any("r80_add_holding_and_goal_indexes" in f.name for f in migrations.iterdir())
    assert found, "Migration r80_add_holding_and_goal_indexes not found"


def test_migration_r80_revision_and_chain():
    import importlib.util, pathlib
    migrations = pathlib.Path(__file__).parent.parent / "alembic" / "versions"
    target = next(f for f in migrations.iterdir() if "r80_add_holding_and_goal_indexes" in f.name)
    spec = importlib.util.spec_from_file_location("mig_r80", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "r80_holding_goal_idx"
    assert mod.down_revision == "r79_notif_covering_idx"
