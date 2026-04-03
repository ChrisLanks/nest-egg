"""
PM Audit Round 87 — Router-level rate limits on all remaining analytics/feature endpoints.

Changes covered:
35 files received router-level Depends(_rate_limit) dependency (30 req/min per user):
amt_calculator, asset_location, bond_ladder, bulk_operations, capital_gains_harvesting,
contributions, dashboard, debt_payoff, deduction_optimizer, dependents, education,
enhanced_trends, espp, financial_planning, financial_ratios, financial_templates,
fx_rates, insurance_audit, insurance_policies, irmaa_projection, loan_modeling,
net_worth_attribution, net_worth_forecast, net_worth_percentile, onboarding, permissions,
rental_properties, social_security, subscriptions, tax_buckets, tax_loss_harvest_ledger,
tax_lots, treasury_rates, what_if, withholding_check
"""

import importlib
import inspect


def _check_module(module_name: str):
    """Helper: load module and verify it has _rate_limit + dependencies on router."""
    mod = importlib.import_module(f"app.api.v1.{module_name}")
    assert hasattr(mod, "_rate_limit"), f"{module_name}: missing _rate_limit function"
    src = inspect.getsource(mod)
    assert "dependencies=[Depends(_rate_limit)]" in src, f"{module_name}: router missing dependency"
    assert "rate_limit_service" in src, f"{module_name}: missing rate_limit_service"


def test_amt_calculator_rate_limited():
    _check_module("amt_calculator")

def test_asset_location_rate_limited():
    _check_module("asset_location")

def test_bond_ladder_rate_limited():
    _check_module("bond_ladder")

def test_bulk_operations_rate_limited():
    _check_module("bulk_operations")

def test_capital_gains_harvesting_rate_limited():
    _check_module("capital_gains_harvesting")

def test_contributions_rate_limited():
    _check_module("contributions")

def test_dashboard_rate_limited():
    _check_module("dashboard")

def test_debt_payoff_rate_limited():
    _check_module("debt_payoff")

def test_deduction_optimizer_rate_limited():
    _check_module("deduction_optimizer")

def test_dependents_rate_limited():
    _check_module("dependents")

def test_education_rate_limited():
    _check_module("education")

def test_enhanced_trends_rate_limited():
    _check_module("enhanced_trends")

def test_espp_rate_limited():
    _check_module("espp")

def test_financial_planning_rate_limited():
    _check_module("financial_planning")

def test_financial_ratios_rate_limited():
    _check_module("financial_ratios")

def test_financial_templates_rate_limited():
    _check_module("financial_templates")

def test_fx_rates_rate_limited():
    _check_module("fx_rates")

def test_insurance_audit_rate_limited():
    _check_module("insurance_audit")

def test_insurance_policies_rate_limited():
    _check_module("insurance_policies")

def test_irmaa_projection_rate_limited():
    _check_module("irmaa_projection")

def test_loan_modeling_rate_limited():
    _check_module("loan_modeling")

def test_net_worth_attribution_rate_limited():
    _check_module("net_worth_attribution")

def test_net_worth_forecast_rate_limited():
    _check_module("net_worth_forecast")

def test_net_worth_percentile_rate_limited():
    _check_module("net_worth_percentile")

def test_onboarding_rate_limited():
    _check_module("onboarding")

def test_permissions_rate_limited():
    _check_module("permissions")

def test_rental_properties_rate_limited():
    _check_module("rental_properties")

def test_social_security_rate_limited():
    _check_module("social_security")

def test_subscriptions_rate_limited():
    _check_module("subscriptions")

def test_tax_buckets_rate_limited():
    _check_module("tax_buckets")

def test_tax_loss_harvest_ledger_rate_limited():
    _check_module("tax_loss_harvest_ledger")

def test_tax_lots_rate_limited():
    _check_module("tax_lots")

def test_treasury_rates_rate_limited():
    _check_module("treasury_rates")

def test_what_if_rate_limited():
    _check_module("what_if")

def test_withholding_check_rate_limited():
    _check_module("withholding_check")
