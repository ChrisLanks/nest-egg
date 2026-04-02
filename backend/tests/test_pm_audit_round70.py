"""
PM Audit Round 70 — Hardcoded value cleanup (financial constants centralisation).

Tests verify that hardcoded numeric literals have been replaced with imports
from app.constants.financial so that a single edit to financial.py propagates
everywhere.

Fixes applied:
1. FICA.COMBINED_EMPLOYEE_RATE added (0.0765) — replaces _FICA_RATE literal
2. VARIABLE_INCOME.SAFE_HARBOR_CURRENT_YEAR_RATE added (0.90)
3. FIRE.DEFAULT_ANNUAL_SPENDING added (80_000)
4. FIRE.DEFAULT_ANNUAL_CONTRIBUTION added (24_000)
5. withholding_check.py uses VARIABLE_INCOME constants (not 150_000 / 0.90 literals)
6. fire.py Query defaults use FIRE.DEFAULT_WITHDRAWAL_RATE / FIRE.DEFAULT_EXPECTED_RETURN /
   RETIREMENT.DEFAULT_RETIREMENT_AGE (not 0.04 / 0.07 / 65)
7. net_worth_forecast.py uses FIRE.DEFAULT_ANNUAL_CONTRIBUTION / FIRE.DEFAULT_ANNUAL_SPENDING
8. dependent_care_optimizer_service.py derives _FICA_RATE from FICA.COMBINED_EMPLOYEE_RATE
"""

import inspect


# ---------------------------------------------------------------------------
# 1. financial.py — new constants present
# ---------------------------------------------------------------------------

def test_fica_combined_employee_rate_exists():
    from app.constants.financial import FICA
    assert hasattr(FICA, "COMBINED_EMPLOYEE_RATE")


def test_fica_combined_employee_rate_value():
    from app.constants.financial import FICA
    from decimal import Decimal
    assert FICA.COMBINED_EMPLOYEE_RATE == Decimal("0.0765")


def test_variable_income_safe_harbor_current_year_rate_exists():
    from app.constants.financial import VARIABLE_INCOME
    assert hasattr(VARIABLE_INCOME, "SAFE_HARBOR_CURRENT_YEAR_RATE")


def test_variable_income_safe_harbor_current_year_rate_value():
    from app.constants.financial import VARIABLE_INCOME
    from decimal import Decimal
    assert VARIABLE_INCOME.SAFE_HARBOR_CURRENT_YEAR_RATE == Decimal("0.90")


def test_fire_default_annual_spending_exists():
    from app.constants.financial import FIRE
    assert hasattr(FIRE, "DEFAULT_ANNUAL_SPENDING")


def test_fire_default_annual_spending_value():
    from app.constants.financial import FIRE
    assert FIRE.DEFAULT_ANNUAL_SPENDING == 80_000


def test_fire_default_annual_contribution_exists():
    from app.constants.financial import FIRE
    assert hasattr(FIRE, "DEFAULT_ANNUAL_CONTRIBUTION")


def test_fire_default_annual_contribution_value():
    from app.constants.financial import FIRE
    assert FIRE.DEFAULT_ANNUAL_CONTRIBUTION == 24_000


# ---------------------------------------------------------------------------
# 2. withholding_check.py — no bare literal 150_000 or 0.90
# ---------------------------------------------------------------------------

def test_withholding_check_imports_variable_income():
    import app.api.v1.withholding_check as mod
    src = inspect.getsource(mod)
    assert "VARIABLE_INCOME" in src


def test_withholding_check_no_bare_agi_threshold_literal():
    import app.api.v1.withholding_check as mod
    src = inspect.getsource(mod)
    # The literal 150_000 should not appear as an assigned value
    assert "agi_threshold = 150_000" not in src
    assert "agi_threshold = 150000" not in src


def test_withholding_check_no_bare_090_literal():
    import app.api.v1.withholding_check as mod
    src = inspect.getsource(mod)
    # Bare 0.90 multiplication should not appear
    assert "projected_tax * 0.90" not in src


def test_withholding_check_uses_safe_harbor_threshold_constant():
    import app.api.v1.withholding_check as mod
    src = inspect.getsource(mod)
    assert "SAFE_HARBOR_110_PCT_INCOME_THRESHOLD" in src


def test_withholding_check_uses_safe_harbor_current_year_rate():
    import app.api.v1.withholding_check as mod
    src = inspect.getsource(mod)
    assert "SAFE_HARBOR_CURRENT_YEAR_RATE" in src


# ---------------------------------------------------------------------------
# 3. fire.py — Query defaults use FIRE / RETIREMENT constants
# ---------------------------------------------------------------------------

def test_fire_endpoint_imports_fire_retirement():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE, RETIREMENT" in src


def test_fire_endpoint_no_bare_004_default():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    # Default literal 0.04 should be replaced
    assert "Query(\n        0.04" not in src
    assert "Query(0.04" not in src


def test_fire_endpoint_no_bare_007_default():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    assert "Query(\n        0.07" not in src
    assert "Query(0.07" not in src


def test_fire_endpoint_no_bare_65_retirement_age():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    # The old default was 65 but DEFAULT_RETIREMENT_AGE is 67
    assert "Query(\n        65," not in src
    assert "Query(65," not in src


def test_fire_endpoint_uses_fire_default_withdrawal_rate():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_WITHDRAWAL_RATE" in src


def test_fire_endpoint_uses_fire_default_expected_return():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_EXPECTED_RETURN" in src


def test_fire_endpoint_uses_retirement_default_age():
    import app.api.v1.fire as mod
    src = inspect.getsource(mod)
    assert "RETIREMENT.DEFAULT_RETIREMENT_AGE" in src


# ---------------------------------------------------------------------------
# 4. net_worth_forecast.py — uses FIRE constants, no bare 24_000 / 80_000
# ---------------------------------------------------------------------------

def test_net_worth_forecast_no_bare_24000_literal():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "24_000.0" not in src
    assert "24000.0" not in src


def test_net_worth_forecast_no_bare_80000_fallback():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    # The hasattr guard + 80_000 literal should be gone
    assert "else 80_000" not in src
    assert "else 80000" not in src


def test_net_worth_forecast_uses_fire_default_annual_contribution():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_ANNUAL_CONTRIBUTION" in src


def test_net_worth_forecast_uses_fire_default_annual_spending():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_ANNUAL_SPENDING" in src


def test_net_worth_forecast_uses_fi_multiplier():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "FIRE.FI_MULTIPLIER" in src


# ---------------------------------------------------------------------------
# 5. dependent_care_optimizer_service.py — uses FICA.COMBINED_EMPLOYEE_RATE
# ---------------------------------------------------------------------------

def test_dependent_care_imports_fica():
    import app.services.dependent_care_optimizer_service as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FICA" in src


def test_dependent_care_no_bare_fica_literal():
    import app.services.dependent_care_optimizer_service as mod
    src = inspect.getsource(mod)
    # Should not have the bare number anymore
    assert "_FICA_RATE = 0.0765" not in src


def test_dependent_care_uses_combined_employee_rate():
    import app.services.dependent_care_optimizer_service as mod
    src = inspect.getsource(mod)
    assert "FICA.COMBINED_EMPLOYEE_RATE" in src


def test_dependent_care_fica_rate_value_correct():
    """Verify the derived rate still equals 0.0765 at runtime."""
    import app.services.dependent_care_optimizer_service as mod
    assert abs(mod._FICA_RATE - 0.0765) < 1e-9
