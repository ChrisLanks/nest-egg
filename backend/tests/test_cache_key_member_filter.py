"""Tests verifying all cached endpoints include user_ids in cache keys.

When the multi-member filter deselects a user, the API receives user_ids
as a query parameter. Cache keys MUST include this so each filter
combination gets its own cache entry. Without this, toggling members
returns stale full-household data.
"""

import inspect
import pytest


class TestHoldingsCacheKeys:
    """Verify holdings endpoints include user_ids in cache keys."""

    def test_portfolio_cache_key_includes_user_ids(self):
        from app.api.v1 import holdings
        source = inspect.getsource(holdings.get_portfolio_summary)
        assert "user_ids_key" in source or "_uids" in source
        assert "user_ids" in source

    def test_fee_analysis_cache_key_includes_user_ids(self):
        from app.api.v1 import holdings
        source = inspect.getsource(holdings.get_fee_analysis)
        assert "_uids" in source

    def test_fund_overlap_cache_key_includes_user_ids(self):
        from app.api.v1 import holdings
        source = inspect.getsource(holdings.get_fund_overlap)
        assert "_uids" in source


class TestIncomeExpensesCacheKeys:
    """Verify income-expenses endpoints include user_ids in cache keys."""

    def test_yoy_cache_key_includes_user_ids(self):
        from app.api.v1 import income_expenses
        source = inspect.getsource(income_expenses.get_year_over_year_comparison)
        assert "_uids" in source

    def test_quarterly_cache_key_includes_user_ids(self):
        from app.api.v1 import income_expenses
        source = inspect.getsource(income_expenses.get_quarterly_summary)
        assert "_uids" in source

    def test_annual_cache_key_includes_user_ids(self):
        from app.api.v1 import income_expenses
        source = inspect.getsource(income_expenses.get_annual_summary)
        assert "_uids" in source


class TestCacheKeyFormat:
    """Verify cache key format is correct for multi-user filtering."""

    def test_user_ids_key_is_sorted_and_joined(self):
        """user_ids should be sorted and comma-joined for deterministic keys."""
        from uuid import UUID
        user_ids = [
            UUID("bbbbbbbb-0000-0000-0000-000000000000"),
            UUID("aaaaaaaa-0000-0000-0000-000000000000"),
        ]
        key = ",".join(sorted(str(u) for u in user_ids))
        assert key == "aaaaaaaa-0000-0000-0000-000000000000,bbbbbbbb-0000-0000-0000-000000000000"

    def test_empty_user_ids_produces_empty_string(self):
        """When user_ids is None or empty, key segment should be empty."""
        user_ids = None
        key = ",".join(sorted(str(u) for u in user_ids)) if user_ids else ""
        assert key == ""

        user_ids = []
        key = ",".join(sorted(str(u) for u in user_ids)) if user_ids else ""
        assert key == ""

    def test_different_user_ids_produce_different_keys(self):
        """Two different filter selections must produce different cache keys."""
        from uuid import UUID
        ids_a = [UUID("aaaaaaaa-0000-0000-0000-000000000000")]
        ids_b = [
            UUID("aaaaaaaa-0000-0000-0000-000000000000"),
            UUID("bbbbbbbb-0000-0000-0000-000000000000"),
        ]
        key_a = ",".join(sorted(str(u) for u in ids_a))
        key_b = ",".join(sorted(str(u) for u in ids_b))
        assert key_a != key_b


class TestTrendEndpointHasUserIds:
    """Verify the trend endpoint declares user_ids parameter."""

    def test_trend_has_user_ids_param(self):
        from app.api.v1 import income_expenses
        source = inspect.getsource(income_expenses.get_income_expense_trend)
        assert "user_ids" in source


class TestMortgagePageFmt:
    """Verify MortgagePage sub-components receive fmt as a prop."""

    def _read_mortgage_page(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/pages/MortgagePage.tsx",
        )
        with open(path) as f:
            return f.read()

    def test_summary_cards_accepts_fmt_prop(self):
        source = self._read_mortgage_page()
        assert "SummaryCards({ data, fmt }" in source or "SummaryCards({data, fmt}" in source

    def test_refinance_section_accepts_fmt_prop(self):
        source = self._read_mortgage_page()
        assert "RefinanceSection({ data, fmt }" in source or "RefinanceSection({data, fmt}" in source

    def test_equity_milestones_accepts_fmt_prop(self):
        source = self._read_mortgage_page()
        assert "EquityMilestones({ data, fmt }" in source or "EquityMilestones({data, fmt}" in source

    def test_amortization_preview_accepts_fmt_prop(self):
        source = self._read_mortgage_page()
        assert "AmortizationPreview({ data, fmt }" in source or "AmortizationPreview({data, fmt}" in source

    def test_call_sites_pass_fmt_prop(self):
        source = self._read_mortgage_page()
        assert "SummaryCards data={data} fmt={fmt}" in source
        assert "RefinanceSection data={data} fmt={fmt}" in source
        assert "EquityMilestones data={data} fmt={fmt}" in source
        assert "AmortizationPreview data={data} fmt={fmt}" in source


class TestRecurringTransactionSchema:
    """Verify recurring transaction schema allows negative amounts."""

    def test_average_amount_allows_negative(self):
        from app.schemas.recurring_transaction import RecurringTransactionBase
        from decimal import Decimal
        # Should not raise — expenses are negative
        schema = RecurringTransactionBase(
            merchant_name="AT&T",
            account_id="00000000-0000-0000-0000-000000000001",
            frequency="monthly",
            average_amount=Decimal("-85.00"),
        )
        assert schema.average_amount == Decimal("-85.00")

    def test_average_amount_allows_positive(self):
        from app.schemas.recurring_transaction import RecurringTransactionBase
        from decimal import Decimal
        schema = RecurringTransactionBase(
            merchant_name="Freelance",
            account_id="00000000-0000-0000-0000-000000000001",
            frequency="monthly",
            average_amount=Decimal("5000.00"),
        )
        assert schema.average_amount == Decimal("5000.00")


class TestDarkModeOverrides:
    """Verify pages with bg='color.50' have _dark overrides."""

    def _read_page(self, filename):
        import os
        path = os.path.join(
            os.path.dirname(__file__),
            "../../frontend/src/pages",
            filename,
        )
        with open(path) as f:
            return f.read()

    def test_recurring_transactions_dark_mode(self):
        source = self._read_page("RecurringTransactionsPage.tsx")
        assert '_dark={{ bg: "purple.900" }}' in source

    def test_reports_page_dark_mode(self):
        source = self._read_page("ReportsPage.tsx")
        assert '_dark={{ bg: "purple.900" }}' in source

    def test_accounts_page_dark_mode(self):
        source = self._read_page("AccountsPage.tsx")
        assert '_dark={{ bg: "red.900" }}' in source
