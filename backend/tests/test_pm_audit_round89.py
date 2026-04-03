"""
PM Audit Round 89 — Replace response_model=dict with typed Pydantic models.

Changes covered:
1. financial_templates.py: Added TemplateActivationResponse model; activate endpoint
   now returns response_model=TemplateActivationResponse instead of dict
2. tax_lots.py: Added CostBasisMethodResponse model; cost-basis-method PUT endpoint
   now returns response_model=CostBasisMethodResponse instead of dict
3. rules.py: Changed response_model=dict to response_model=Dict[str, Any]
"""

import inspect


# ---------------------------------------------------------------------------
# 1. financial_templates.py — TemplateActivationResponse
# ---------------------------------------------------------------------------

def test_financial_templates_has_activation_response_model():
    import app.api.v1.financial_templates as mod
    assert hasattr(mod, "TemplateActivationResponse"), (
        "financial_templates must define TemplateActivationResponse"
    )


def test_financial_templates_activation_response_fields():
    from app.api.v1.financial_templates import TemplateActivationResponse
    fields = TemplateActivationResponse.model_fields
    assert "status" in fields
    assert "template_id" in fields
    assert "message" in fields


def test_financial_templates_activate_uses_response_model():
    import app.api.v1.financial_templates as mod
    src = inspect.getsource(mod)
    assert "response_model=TemplateActivationResponse" in src, (
        "activate_template endpoint must declare response_model=TemplateActivationResponse"
    )


def test_financial_templates_no_bare_dict_response_model():
    import app.api.v1.financial_templates as mod
    src = inspect.getsource(mod)
    assert "response_model=dict" not in src, (
        "financial_templates must not use bare response_model=dict"
    )


# ---------------------------------------------------------------------------
# 2. tax_lots.py — CostBasisMethodResponse
# ---------------------------------------------------------------------------

def test_tax_lots_has_cost_basis_method_response_model():
    import app.api.v1.tax_lots as mod
    assert hasattr(mod, "CostBasisMethodResponse"), (
        "tax_lots must define CostBasisMethodResponse"
    )


def test_tax_lots_cost_basis_method_response_fields():
    from app.api.v1.tax_lots import CostBasisMethodResponse
    fields = CostBasisMethodResponse.model_fields
    assert "account_id" in fields
    assert "cost_basis_method" in fields


def test_tax_lots_cost_basis_method_uses_response_model():
    import app.api.v1.tax_lots as mod
    src = inspect.getsource(mod)
    assert "response_model=CostBasisMethodResponse" in src, (
        "update_cost_basis_method endpoint must declare response_model=CostBasisMethodResponse"
    )


def test_tax_lots_no_bare_dict_response_model():
    import app.api.v1.tax_lots as mod
    src = inspect.getsource(mod)
    assert "response_model=dict" not in src, (
        "tax_lots must not use bare response_model=dict"
    )


# ---------------------------------------------------------------------------
# 3. rules.py — Dict[str, Any] instead of bare dict
# ---------------------------------------------------------------------------

def test_rules_imports_dict_and_any():
    import app.api.v1.rules as mod
    src = inspect.getsource(mod)
    assert "Dict" in src, "rules.py must import Dict from typing"
    assert "Any" in src, "rules.py must import Any from typing"


def test_rules_no_bare_dict_response_model():
    import app.api.v1.rules as mod
    src = inspect.getsource(mod)
    assert "response_model=dict" not in src, (
        "rules.py must not use bare response_model=dict"
    )


def test_rules_uses_typed_dict_response_model():
    import app.api.v1.rules as mod
    src = inspect.getsource(mod)
    assert "Dict[str, Any]" in src, (
        "rules.py must use Dict[str, Any] for unstructured response models"
    )
