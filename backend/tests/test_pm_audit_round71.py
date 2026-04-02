"""
PM Audit Round 71 — Second pass hardcoded value cleanup.

Fixes applied:
1. TAX.MEDICAL_DEDUCTION_AGI_FLOOR = 0.075 added to financial.py
2. net_worth_forecast.py Query defaults use RETIREMENT / FIRE constants
3. what_if.py Field defaults use FIRE.DEFAULT_EXPECTED_RETURN and TAX.FEDERAL_MARGINAL_RATE
4. deduction_optimizer.py uses TAX.MEDICAL_DEDUCTION_AGI_FLOOR
5. fund_fee_analyzer_service.py uses FIRE.DEFAULT_EXPECTED_RETURN for _BASE_RETURN
6. inheritance_projection_service.py uses FIRE.DEFAULT_WITHDRAWAL_RATE for 0.04 literals
"""

import inspect


# ---------------------------------------------------------------------------
# 1. financial.py — new TAX.MEDICAL_DEDUCTION_AGI_FLOOR constant
# ---------------------------------------------------------------------------

def test_tax_medical_deduction_agi_floor_exists():
    from app.constants.financial import TAX
    assert hasattr(TAX, "MEDICAL_DEDUCTION_AGI_FLOOR")


def test_tax_medical_deduction_agi_floor_value():
    from app.constants.financial import TAX
    from decimal import Decimal
    assert TAX.MEDICAL_DEDUCTION_AGI_FLOOR == Decimal("0.075")


# ---------------------------------------------------------------------------
# 2. net_worth_forecast.py — Query defaults use constants
# ---------------------------------------------------------------------------

def test_net_worth_forecast_no_bare_67_default():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "default=67" not in src
    assert "default=RETIREMENT.DEFAULT_RETIREMENT_AGE" in src


def test_net_worth_forecast_no_bare_007_return_default():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "default=0.07" not in src
    assert "default=FIRE.DEFAULT_EXPECTED_RETURN" in src


def test_net_worth_forecast_no_bare_003_inflation_default():
    import app.api.v1.net_worth_forecast as mod
    src = inspect.getsource(mod)
    assert "default=0.03" not in src
    assert "default=FIRE.DEFAULT_INFLATION" in src


# ---------------------------------------------------------------------------
# 3. what_if.py — Field defaults use constants
# ---------------------------------------------------------------------------

def test_what_if_no_bare_008_investment_return():
    import app.api.v1.what_if as mod
    src = inspect.getsource(mod)
    assert "Field(0.08," not in src


def test_what_if_no_bare_022_tax_bracket():
    import app.api.v1.what_if as mod
    src = inspect.getsource(mod)
    assert "Field(0.22," not in src


def test_what_if_no_bare_007_expected_return():
    import app.api.v1.what_if as mod
    src = inspect.getsource(mod)
    assert "Field(0.07," not in src


def test_what_if_uses_fire_default_expected_return():
    import app.api.v1.what_if as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_EXPECTED_RETURN" in src


def test_what_if_uses_tax_federal_marginal_rate():
    import app.api.v1.what_if as mod
    src = inspect.getsource(mod)
    assert "TAX.FEDERAL_MARGINAL_RATE" in src


# ---------------------------------------------------------------------------
# 4. deduction_optimizer.py — uses TAX.MEDICAL_DEDUCTION_AGI_FLOOR
# ---------------------------------------------------------------------------

def test_deduction_optimizer_no_bare_0075():
    import app.api.v1.deduction_optimizer as mod
    src = inspect.getsource(mod)
    assert "* 0.075" not in src


def test_deduction_optimizer_uses_medical_floor_constant():
    import app.api.v1.deduction_optimizer as mod
    src = inspect.getsource(mod)
    assert "TAX.MEDICAL_DEDUCTION_AGI_FLOOR" in src


# ---------------------------------------------------------------------------
# 5. fund_fee_analyzer_service.py — _BASE_RETURN from FIRE constant
# ---------------------------------------------------------------------------

def test_fund_fee_analyzer_imports_fire():
    import app.services.fund_fee_analyzer_service as mod
    src = inspect.getsource(mod)
    assert "from app.constants.financial import FIRE" in src


def test_fund_fee_analyzer_no_bare_007_base_return():
    import app.services.fund_fee_analyzer_service as mod
    src = inspect.getsource(mod)
    assert "_BASE_RETURN = 0.07" not in src


def test_fund_fee_analyzer_base_return_uses_fire_constant():
    import app.services.fund_fee_analyzer_service as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_EXPECTED_RETURN" in src


def test_fund_fee_analyzer_base_return_value_correct():
    """Runtime value should still be 0.07."""
    import app.services.fund_fee_analyzer_service as mod
    from app.constants.financial import FIRE
    assert mod._BASE_RETURN == FIRE.DEFAULT_EXPECTED_RETURN


# ---------------------------------------------------------------------------
# 6. inheritance_projection_service.py — uses FIRE.DEFAULT_WITHDRAWAL_RATE
# ---------------------------------------------------------------------------

def test_inheritance_service_no_bare_004_withdrawal():
    import app.services.inheritance_projection_service as mod
    src = inspect.getsource(mod)
    # The literal "* 0.04" should not appear now
    assert "* 0.04" not in src


def test_inheritance_service_uses_fire_default_withdrawal_rate():
    import app.services.inheritance_projection_service as mod
    src = inspect.getsource(mod)
    assert "FIRE.DEFAULT_WITHDRAWAL_RATE" in src
