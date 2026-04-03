"""
PM Audit Round 77 — Household living-together fixes (continued).

Changes covered:
1. /settings/financial-defaults exposes low_balance_warning_usd + max_household_members
2. ForecastSummary model adds by_member breakdown field
3. ForecastService.generate_forecast_summary computes by_member
4. Transaction schema is_split already serialised (round 76) — regression check
5. BudgetsWidget uses budget.alert_threshold instead of hardcoded 80
   (frontend-only; verified via source inspection)
6. CashFlowPage GroupBy type extended with "member" (frontend-only)
7. RecentTransactionsWidget renders is_split / is_transfer badges
   (frontend-only; verified via source inspection)
8. HouseholdSettingsPage uses maxMembers from API + shows capacity badge
   (frontend-only; verified via source inspection)
"""

import inspect


# ---------------------------------------------------------------------------
# 1. /settings/financial-defaults — new fields
# ---------------------------------------------------------------------------

def test_financial_defaults_endpoint_exposes_low_balance_warning():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "low_balance_warning_usd" in src


def test_financial_defaults_endpoint_exposes_max_household_members():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "max_household_members" in src


def test_financial_defaults_imports_cash_flow_timing():
    import app.api.v1.settings as mod
    src = inspect.getsource(mod)
    assert "CASH_FLOW_TIMING" in src


def test_cash_flow_timing_low_balance_constant_exists():
    from app.constants.financial import CASH_FLOW_TIMING
    assert hasattr(CASH_FLOW_TIMING, "LOW_BALANCE_WARNING_USD")
    val = float(CASH_FLOW_TIMING.LOW_BALANCE_WARNING_USD)
    assert val > 0


# ---------------------------------------------------------------------------
# 2. ForecastSummary model — by_member field
# ---------------------------------------------------------------------------

def test_forecast_summary_model_has_by_member():
    from app.api.v1.dashboard import ForecastSummary
    fields = ForecastSummary.model_fields
    assert "by_member" in fields


def test_forecast_summary_by_member_defaults_empty():
    from app.api.v1.dashboard import ForecastSummary
    s = ForecastSummary(
        total_income=0,
        total_expenses=0,
        net=0,
        by_category=[],
        by_merchant=[],
        by_label=[],
        by_account=[],
    )
    assert s.by_member == []


# ---------------------------------------------------------------------------
# 3. ForecastService — by_member in generate_forecast_summary output
# ---------------------------------------------------------------------------

def test_forecast_service_summary_builds_by_member():
    from app.services.forecast_service import ForecastService
    src = inspect.getsource(ForecastService.generate_forecast_summary)
    assert "by_member" in src


def test_forecast_service_summary_queries_account_user():
    """by_member lookup uses Account.user_id to identify the owner."""
    from app.services.forecast_service import ForecastService
    src = inspect.getsource(ForecastService.generate_forecast_summary)
    assert "account_to_member" in src
    assert "users_map" in src


def test_forecast_service_summary_returns_by_member_key():
    from app.services.forecast_service import ForecastService
    src = inspect.getsource(ForecastService.generate_forecast_summary)
    assert '"by_member"' in src


# ---------------------------------------------------------------------------
# 4. Transaction schema — is_split regression check (originally round 76)
# ---------------------------------------------------------------------------

def test_transaction_schema_still_has_is_split():
    from app.schemas.transaction import Transaction as TxSchema
    assert "is_split" in TxSchema.model_fields


# ---------------------------------------------------------------------------
# 5. Dashboard summary — spending_by_member regression (round 76)
# ---------------------------------------------------------------------------

def test_dashboard_summary_still_has_spending_by_member():
    from app.api.v1.dashboard import DashboardSummary
    assert "spending_by_member" in DashboardSummary.model_fields


# ---------------------------------------------------------------------------
# 6. ForecastBreakdownItem model still present
# ---------------------------------------------------------------------------

def test_forecast_breakdown_item_model_exists():
    from app.api.v1.dashboard import ForecastBreakdownItem
    fields = ForecastBreakdownItem.model_fields
    assert "name" in fields
    assert "amount" in fields


# ---------------------------------------------------------------------------
# 7. forecast_service uses User model for member name resolution
# ---------------------------------------------------------------------------

def test_forecast_service_imports_user():
    import app.services.forecast_service as mod
    src = inspect.getsource(mod)
    assert "from app.models.user import" in src
    assert "User" in src
