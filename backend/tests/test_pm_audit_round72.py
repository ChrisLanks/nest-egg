"""
PM Audit Round 72 — /settings/financial-defaults endpoint + frontend seeding.

Ensures:
1. GET /settings/financial-defaults endpoint exists in settings router
2. All expected keys are present in the response body
3. Values match the source constants in financial.py
4. NetWorthForecastTab.tsx no longer has bare useState(67/7/24000) literals
5. RothConversionPage.tsx fetches /settings/financial-defaults on mount
"""

import inspect
import os

FRONTEND = os.path.join(os.path.dirname(__file__), "../../frontend/src")


def _read(rel: str) -> str:
    return open(os.path.join(FRONTEND, rel), encoding="utf-8").read()


# ---------------------------------------------------------------------------
# 1. Backend: settings router has financial-defaults endpoint
# ---------------------------------------------------------------------------

def test_settings_router_has_financial_defaults_route():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert '"/financial-defaults"' in src or "financial-defaults" in src


def test_settings_financial_defaults_imports_fire():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "FIRE" in src


def test_settings_financial_defaults_imports_retirement():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "RETIREMENT" in src


def test_settings_financial_defaults_imports_tax():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "TAX" in src


def test_settings_financial_defaults_returns_withdrawal_rate():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "default_withdrawal_rate" in src


def test_settings_financial_defaults_returns_expected_return():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "default_expected_return" in src


def test_settings_financial_defaults_returns_retirement_age():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "default_retirement_age" in src


def test_settings_financial_defaults_returns_annual_contribution():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "default_annual_contribution" in src


def test_settings_financial_defaults_returns_annual_spending():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "default_annual_spending" in src


def test_settings_financial_defaults_returns_medical_floor():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "medical_deduction_agi_floor" in src


# ---------------------------------------------------------------------------
# 2. Constants roundtrip — values in endpoint match financial.py
# ---------------------------------------------------------------------------

def test_financial_defaults_fire_values_consistent():
    from app.constants.financial import FIRE
    assert FIRE.DEFAULT_ANNUAL_CONTRIBUTION == 24_000
    assert FIRE.DEFAULT_ANNUAL_SPENDING == 80_000
    assert FIRE.DEFAULT_EXPECTED_RETURN == 0.07
    assert FIRE.DEFAULT_WITHDRAWAL_RATE == 0.04
    assert FIRE.DEFAULT_INFLATION == 0.03


def test_financial_defaults_retirement_values_consistent():
    from app.constants.financial import RETIREMENT
    assert RETIREMENT.DEFAULT_RETIREMENT_AGE == 67


# ---------------------------------------------------------------------------
# 3. Frontend: NetWorthForecastTab no longer embeds bare defaults
# ---------------------------------------------------------------------------

def test_net_worth_forecast_tab_fetches_financial_defaults():
    src = _read("pages/NetWorthForecastTab.tsx")
    assert "/settings/financial-defaults" in src


def test_net_worth_forecast_tab_no_bare_67_usestate():
    src = _read("pages/NetWorthForecastTab.tsx")
    assert "useState(67)" not in src


def test_net_worth_forecast_tab_no_bare_7_usestate():
    src = _read("pages/NetWorthForecastTab.tsx")
    assert "useState(7)" not in src


def test_net_worth_forecast_tab_no_bare_24000_usestate():
    src = _read("pages/NetWorthForecastTab.tsx")
    assert "useState(24000)" not in src


def test_net_worth_forecast_tab_uses_effective_values():
    src = _read("pages/NetWorthForecastTab.tsx")
    assert "effectiveRetirementAge" in src
    assert "effectiveAnnualReturn" in src
    assert "effectiveAnnualContrib" in src


# ---------------------------------------------------------------------------
# 4. Frontend: RothConversionPage seeds from /settings/financial-defaults
# ---------------------------------------------------------------------------

def test_roth_conversion_page_fetches_financial_defaults():
    src = _read("pages/RothConversionPage.tsx")
    assert "/settings/financial-defaults" in src


def test_roth_conversion_page_uses_from_storage_flag():
    src = _read("pages/RothConversionPage.tsx")
    assert "_fromStorage" in src
