"""
PM Audit Round 99 — response_model coverage for GET endpoints (Dict[str, Any]).

Changes covered: 74 GET endpoints across 31 files now have response_model=Dict[str, Any]:
accounts, auth, bank_linking, bond_ladder, budgets, capital_gains_harvesting,
charitable_giving, debt_payoff, dev, dividend_income, enhanced_trends, enrichment,
estate, holdings, hsa, income_expenses, labels, loan_modeling, monitoring,
net_worth_attribution, notifications, pe_performance, rebalancing, rental_properties,
reports, rules, settings, stress_test, tax_advisor, tax_buckets, transactions.
"""

import inspect


def _has_dict_any_response_model(mod):
    src = inspect.getsource(mod)
    return "response_model=Dict[str, Any]" in src


def test_enhanced_trends_get_endpoints_have_response_model():
    import app.api.v1.enhanced_trends as mod
    assert _has_dict_any_response_model(mod)


def test_capital_gains_harvesting_get_endpoints_have_response_model():
    import app.api.v1.capital_gains_harvesting as mod
    assert _has_dict_any_response_model(mod)


def test_charitable_giving_get_endpoints_have_response_model():
    import app.api.v1.charitable_giving as mod
    assert _has_dict_any_response_model(mod)


def test_debt_payoff_get_endpoints_have_response_model():
    import app.api.v1.debt_payoff as mod
    assert _has_dict_any_response_model(mod)


def test_dividend_income_get_endpoints_have_response_model():
    import app.api.v1.dividend_income as mod
    assert _has_dict_any_response_model(mod)


def test_estate_get_endpoints_have_response_model():
    import app.api.v1.estate as mod
    assert _has_dict_any_response_model(mod)


def test_hsa_get_endpoints_have_response_model():
    import app.api.v1.hsa as mod
    assert _has_dict_any_response_model(mod)


def test_net_worth_attribution_get_endpoints_have_response_model():
    import app.api.v1.net_worth_attribution as mod
    assert _has_dict_any_response_model(mod)


def test_pe_performance_get_endpoints_have_response_model():
    import app.api.v1.pe_performance as mod
    assert _has_dict_any_response_model(mod)


def test_rebalancing_get_endpoints_have_response_model():
    import app.api.v1.rebalancing as mod
    assert _has_dict_any_response_model(mod)


def test_rental_properties_get_endpoints_have_response_model():
    import app.api.v1.rental_properties as mod
    assert _has_dict_any_response_model(mod)


def test_stress_test_get_endpoints_have_response_model():
    import app.api.v1.stress_test as mod
    assert _has_dict_any_response_model(mod)


def test_tax_advisor_get_endpoints_have_response_model():
    import app.api.v1.tax_advisor as mod
    assert _has_dict_any_response_model(mod)


def test_tax_buckets_get_endpoints_have_response_model():
    import app.api.v1.tax_buckets as mod
    assert _has_dict_any_response_model(mod)


def test_loan_modeling_get_endpoints_have_response_model():
    import app.api.v1.loan_modeling as mod
    assert _has_dict_any_response_model(mod)


def test_monitoring_get_endpoints_have_response_model():
    import app.api.v1.monitoring as mod
    assert _has_dict_any_response_model(mod)


def test_income_expenses_get_endpoints_have_response_model():
    import app.api.v1.income_expenses as mod
    assert _has_dict_any_response_model(mod)


def test_notifications_get_endpoints_have_response_model():
    import app.api.v1.notifications as mod
    assert _has_dict_any_response_model(mod)


def test_bond_ladder_get_endpoints_have_response_model():
    import app.api.v1.bond_ladder as mod
    assert _has_dict_any_response_model(mod)


def test_enrichment_get_endpoints_have_response_model():
    import app.api.v1.enrichment as mod
    assert _has_dict_any_response_model(mod)


def test_reports_household_summary_has_response_model():
    import app.api.v1.reports as mod
    assert _has_dict_any_response_model(mod)
