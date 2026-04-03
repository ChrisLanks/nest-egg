"""
PM Audit Round 94 — Typed response models for budgets/bond_ladder/dividend_income/rules;
router-level rate limit for dividend_income.

Changes covered:
1. budgets.py: BudgetAlertsResponse model; response_model on POST /check-alerts
2. bond_ladder.py: response_model=Dict[str, Any] on POST /plan
3. dividend_income.py: DividendDetectResponse model; router-level _rate_limit;
   response_model=DividendIncomeResponse on POST /; response_model=DividendDetectResponse on /detect
4. rules.py: ApplyRuleResponse model; response_model on POST /{rule_id}/apply
"""

import inspect


# ---------------------------------------------------------------------------
# 1. budgets.py
# ---------------------------------------------------------------------------

def test_budgets_has_alerts_response():
    import app.api.v1.budgets as mod
    assert hasattr(mod, "BudgetAlertsResponse")
    fields = mod.BudgetAlertsResponse.model_fields
    assert "alerts_created" in fields
    assert "budgets_alerted" in fields


def test_budgets_check_alerts_has_response_model():
    import app.api.v1.budgets as mod
    src = inspect.getsource(mod)
    assert "response_model=BudgetAlertsResponse" in src


def test_budgets_check_alerts_returns_model():
    import app.api.v1.budgets as mod
    src = inspect.getsource(mod.check_budget_alerts)
    assert "BudgetAlertsResponse(" in src


# ---------------------------------------------------------------------------
# 2. bond_ladder.py
# ---------------------------------------------------------------------------

def test_bond_ladder_plan_has_response_model():
    import app.api.v1.bond_ladder as mod
    src = inspect.getsource(mod)
    assert "response_model=Dict[str, Any]" in src


def test_bond_ladder_imports_dict_and_any():
    import app.api.v1.bond_ladder as mod
    src = inspect.getsource(mod)
    assert "Dict" in src
    assert "Any" in src


# ---------------------------------------------------------------------------
# 3. dividend_income.py
# ---------------------------------------------------------------------------

def test_dividend_income_has_detect_response():
    import app.api.v1.dividend_income as mod
    assert hasattr(mod, "DividendDetectResponse")
    fields = mod.DividendDetectResponse.model_fields
    assert "labeled_count" in fields


def test_dividend_income_has_router_rate_limit():
    import app.api.v1.dividend_income as mod
    src = inspect.getsource(mod)
    assert "_rate_limit" in src
    assert "dependencies=[Depends(_rate_limit)]" in src


def test_dividend_income_create_has_response_model():
    import app.api.v1.dividend_income as mod
    src = inspect.getsource(mod)
    assert "response_model=DividendIncomeResponse" in src


def test_dividend_income_detect_has_response_model():
    import app.api.v1.dividend_income as mod
    src = inspect.getsource(mod)
    assert "response_model=DividendDetectResponse" in src


def test_dividend_income_detect_returns_model():
    import app.api.v1.dividend_income as mod
    src = inspect.getsource(mod.detect_dividend_transactions)
    assert "DividendDetectResponse(" in src


# ---------------------------------------------------------------------------
# 4. rules.py
# ---------------------------------------------------------------------------

def test_rules_has_apply_rule_response():
    import app.api.v1.rules as mod
    assert hasattr(mod, "ApplyRuleResponse")
    fields = mod.ApplyRuleResponse.model_fields
    assert "applied_count" in fields
    assert "message" in fields


def test_rules_apply_has_response_model():
    import app.api.v1.rules as mod
    src = inspect.getsource(mod)
    assert "response_model=ApplyRuleResponse" in src


def test_rules_apply_returns_model():
    import app.api.v1.rules as mod
    src = inspect.getsource(mod.apply_rule)
    assert "ApplyRuleResponse(" in src
