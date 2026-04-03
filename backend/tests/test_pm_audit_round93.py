"""
PM Audit Round 93 — Replace is_active == True with is_active.is_(True) across all files.

SQLAlchemy's == True operator can be misinterpreted by linters and some DB engines.
The .is_(True) form is the idiomatic and unambiguous SQLAlchemy pattern.

Files fixed: 22 files across app/api/v1/, app/crud/, and app/services/.
"""

import inspect


# ---------------------------------------------------------------------------
# API layer files
# ---------------------------------------------------------------------------

def test_asset_location_uses_is_true():
    import app.api.v1.asset_location as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_backdoor_roth_uses_is_true():
    import app.api.v1.backdoor_roth as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src


def test_calculator_prefill_uses_is_true():
    import app.api.v1.calculator_prefill as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src


def test_contribution_headroom_uses_is_true():
    import app.api.v1.contribution_headroom as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_employer_match_uses_is_true():
    import app.api.v1.employer_match as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src


def test_estate_uses_is_true():
    import app.api.v1.estate as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_financial_ratios_uses_is_true():
    import app.api.v1.financial_ratios as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_insurance_audit_uses_is_true():
    import app.api.v1.insurance_audit as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_rmd_planner_uses_is_true():
    import app.api.v1.rmd_planner as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


# ---------------------------------------------------------------------------
# Service layer files
# ---------------------------------------------------------------------------

def test_education_service_uses_is_true():
    import app.services.education_planning_service as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_financial_templates_service_uses_is_true():
    import app.services.financial_templates_service as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_savings_goal_service_uses_is_true():
    import app.services.savings_goal_service as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_tax_bucket_service_uses_is_true():
    import app.services.tax_bucket_service as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src


def test_net_worth_attribution_service_uses_is_true():
    import app.services.net_worth_attribution_service as mod
    src = inspect.getsource(mod)
    assert "is_active == True" not in src
    assert "is_active.is_(True)" in src
