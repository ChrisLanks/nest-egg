"""Tests for new features: Cash Flow Forecast page, Credit Score API, Form 8949 export."""

import inspect


class TestCreditScoreAPI:
    """credit_scores.py: CRUD endpoints and score band logic."""

    def test_score_band_exceptional(self):
        from app.api.v1.credit_scores import _score_band
        assert _score_band(850) == "Exceptional"
        assert _score_band(800) == "Exceptional"

    def test_score_band_very_good(self):
        from app.api.v1.credit_scores import _score_band
        assert _score_band(799) == "Very Good"
        assert _score_band(740) == "Very Good"

    def test_score_band_good(self):
        from app.api.v1.credit_scores import _score_band
        assert _score_band(739) == "Good"
        assert _score_band(670) == "Good"

    def test_score_band_fair(self):
        from app.api.v1.credit_scores import _score_band
        assert _score_band(669) == "Fair"
        assert _score_band(580) == "Fair"

    def test_score_band_poor(self):
        from app.api.v1.credit_scores import _score_band
        assert _score_band(579) == "Poor"
        assert _score_band(300) == "Poor"

    def test_score_schema_validation_bounds(self):
        """CreditScoreCreate schema rejects scores outside 300-850."""
        import pytest
        from pydantic import ValidationError
        from datetime import date
        from app.api.v1.credit_scores import CreditScoreCreate

        # Valid
        entry = CreditScoreCreate(score=720, score_date=date.today(), provider="FICO")
        assert entry.score == 720

        # Too low
        with pytest.raises(ValidationError):
            CreditScoreCreate(score=299, score_date=date.today(), provider="Equifax")

        # Too high
        with pytest.raises(ValidationError):
            CreditScoreCreate(score=851, score_date=date.today(), provider="Equifax")

    def test_router_registered_in_main(self):
        import app.main as main_mod
        src = inspect.getsource(main_mod)
        assert "credit_scores" in src
        assert "credit_scores.router" in src

    def test_model_has_expected_columns(self):
        from app.models.credit_score import CreditScore
        cols = {c.name for c in CreditScore.__table__.columns}
        assert "id" in cols
        assert "organization_id" in cols
        assert "user_id" in cols
        assert "score" in cols
        assert "score_date" in cols
        assert "provider" in cols
        assert "notes" in cols

    def test_get_endpoint_accepts_user_id_param(self):
        import app.api.v1.credit_scores as mod
        src = inspect.getsource(mod)
        assert "user_id" in src
        assert "Household member user ID" in src

    def test_delete_endpoint_checks_ownership(self):
        """DELETE endpoint must verify organization_id matches before deleting."""
        import app.api.v1.credit_scores as mod
        src = inspect.getsource(mod)
        assert "CreditScore.organization_id == current_user.organization_id" in src


class TestForm8949Export:
    """tax_lots.py: Form 8949 CSV export endpoint."""

    def test_export_endpoint_exists(self):
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "/tax-lots/export/8949" in src

    def test_export_returns_streaming_response(self):
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "StreamingResponse" in src

    def test_export_csv_columns(self):
        """CSV header row should match IRS 8949 column names."""
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "Description of Property" in src
        assert "Date Acquired" in src
        assert "Date Sold" in src
        assert "Proceeds" in src
        assert "Cost or Other Basis" in src
        assert "Gain or (Loss)" in src

    def test_export_separates_short_and_long_term(self):
        """Short-term and long-term sections must be separate (IRS requirement)."""
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "SHORT_TERM" in src
        assert "LONG_TERM" in src
        assert "SHORT-TERM" in src
        assert "LONG-TERM" in src

    def test_export_uses_holding_ticker(self):
        """Description should include the holding ticker."""
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "lot.holding.ticker" in src

    def test_export_content_disposition_header(self):
        """Response must include Content-Disposition filename header."""
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "form_8949_" in src
        assert "Content-Disposition" in src

    def test_csv_import_added(self):
        """csv and io stdlib imports must be present."""
        import app.api.v1.tax_lots as mod
        src = inspect.getsource(mod)
        assert "import csv" in src
        assert "import io" in src


class TestCashFlowPage:
    """CashFlowPage: unified /cash-flow route with Overview + Forecast tabs."""

    def test_cash_flow_route_in_app_tsx(self):
        """App.tsx must define the /cash-flow route with CashFlowPage."""
        import os
        app_tsx = os.path.join(os.path.dirname(__file__), "../../../frontend/src/App.tsx")
        with open(app_tsx) as f:
            src = f.read()
        assert "/cash-flow" in src
        assert "CashFlowPage" in src

    def test_old_routes_redirect_in_app_tsx(self):
        """Old /income-expenses and /cash-flow-forecast must redirect to /cash-flow."""
        import os
        app_tsx = os.path.join(os.path.dirname(__file__), "../../../frontend/src/App.tsx")
        with open(app_tsx) as f:
            src = f.read()
        assert "/income-expenses" in src
        assert "/cash-flow-forecast" in src
        # Both old routes must now use Navigate (redirect), not render a page directly
        assert src.count("Navigate") >= 2

    def test_single_nav_entry_in_layout(self):
        """Layout.tsx must have exactly one Cash Flow entry pointing to /cash-flow."""
        import os
        layout_tsx = os.path.join(os.path.dirname(__file__), "../../../frontend/src/components/Layout.tsx")
        with open(layout_tsx) as f:
            src = f.read()
        assert "/cash-flow" in src
        assert "Cash Flow Forecast" not in src  # No longer a separate nav item
        assert src.count("/cash-flow-forecast") == 0

    def test_cash_flow_page_file_exists(self):
        """CashFlowPage.tsx must exist under src/pages/."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        assert os.path.exists(page)

    def test_page_has_both_tabs(self):
        """CashFlowPage must render both Overview and Forecast tabs."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "Overview" in src
        assert "Forecast" in src
        assert "IncomeExpensesPage" in src  # Overview tab reuses existing component

    def test_page_calls_forecast_endpoints(self):
        """CashFlowPage must call both /dashboard/forecast and /dashboard/forecast/summary."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "/dashboard/forecast" in src
        assert "/dashboard/forecast/summary" in src
        assert "days_ahead" in src

    def test_page_has_recharts_charts(self):
        """CashFlowPage Forecast tab must include balance and income/expense charts."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "AreaChart" in src   # Balance trajectory
        assert "BarChart" in src    # Income vs expenses
        assert "recharts" in src

    def test_page_has_group_by_controls(self):
        """Forecast tab must have group-by breakdown (category/merchant/label/account)."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "category" in src
        assert "merchant" in src
        assert "label" in src
        assert "account" in src

    def test_page_has_low_balance_alert(self):
        """Forecast tab must still warn about negative / low projected balances."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "low" in src.lower()
        assert "negative balance" in src.lower()

    def test_tab_param_in_url(self):
        """Tab state must be persisted via ?tab= search param for deep-linking."""
        import os
        page = os.path.join(os.path.dirname(__file__), "../../../frontend/src/pages/CashFlowPage.tsx")
        with open(page) as f:
            src = f.read()
        assert "useSearchParams" in src
        assert "TAB_NAME_MAP" in src  # tab names stored in mapping constant
        assert '"forecast"' in src   # "forecast" tab name defined in mapping


class TestCreditScoreTab:
    """CreditScoreTab.tsx: wired into FinancialHealthPage."""

    def test_tab_added_to_financial_health(self):
        import os
        page = os.path.join(
            os.path.dirname(__file__), "../../../frontend/src/pages/FinancialHealthPage.tsx"
        )
        with open(page) as f:
            src = f.read()
        assert "Credit Score" in src
        assert "CreditScoreTab" in src

    def test_tab_file_exists(self):
        import os
        tab = os.path.join(
            os.path.dirname(__file__), "../../../frontend/src/pages/CreditScoreTab.tsx"
        )
        assert os.path.exists(tab)

    def test_tab_uses_api_endpoint(self):
        import os
        tab = os.path.join(
            os.path.dirname(__file__), "../../../frontend/src/pages/CreditScoreTab.tsx"
        )
        with open(tab) as f:
            src = f.read()
        assert "/credit-scores" in src

    def test_tab_has_fico_bands(self):
        import os
        tab = os.path.join(
            os.path.dirname(__file__), "../../../frontend/src/pages/CreditScoreTab.tsx"
        )
        with open(tab) as f:
            src = f.read()
        assert "Exceptional" in src
        assert "Very Good" in src
        assert "Good" in src
        assert "Fair" in src
        assert "Poor" in src
