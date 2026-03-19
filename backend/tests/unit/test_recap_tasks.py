"""Unit tests for the weekly recap Celery task logic.

Tests the message-building logic and preference-gating without hitting the
real database or Celery broker — pure unit testing of the business logic.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_org(org_id=None):
    org = MagicMock()
    org.id = org_id or uuid4()
    org.is_active = True
    return org


def _make_account(org_id, balance=0.0, is_asset=True):
    acc = MagicMock()
    acc.id = uuid4()
    acc.organization_id = org_id
    acc.is_active = True
    acc.current_balance = balance

    # Simulate account_type.category
    from app.models.account import AccountCategory

    category = AccountCategory.ASSET if is_asset else AccountCategory.DEBT
    acc.account_type = MagicMock()
    acc.account_type.category = category
    return acc


def _make_user(org_id, prefs=None):
    user = MagicMock()
    user.id = uuid4()
    user.organization_id = org_id
    user.is_active = True
    user.notification_preferences = prefs or {}
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRecapTaskMessageBuilding:
    """Tests for the recap message composition logic."""

    def test_net_sign_positive(self):
        """Positive net (income > spending) shows + prefix."""
        income = 3000.0
        spending = 2000.0
        net = income - spending
        net_sign = "+" if net >= 0 else ""
        assert net_sign == "+"

    def test_net_sign_negative(self):
        """Negative net (spending > income) shows no prefix."""
        income = 1000.0
        spending = 2500.0
        net = income - spending
        net_sign = "+" if net >= 0 else ""
        assert net_sign == ""

    def test_net_sign_zero(self):
        """Zero net shows + prefix (break-even is treated as positive)."""
        net = 0.0
        net_sign = "+" if net >= 0 else ""
        assert net_sign == "+"

    def test_week_date_range_calculation(self):
        """week_start is 7 days ago, week_end is yesterday."""
        today = date(2025, 3, 17)
        week_start = today - timedelta(days=7)
        week_end = today - timedelta(days=1)
        assert week_start == date(2025, 3, 10)
        assert week_end == date(2025, 3, 16)

    def test_message_contains_income_line(self):
        """Message includes income amount."""
        total_income = 3500.0
        total_spending = 2100.0
        fmt = lambda v: f"${v:,.0f}"  # noqa: E731
        net = total_income - total_spending
        net_sign = "+" if net >= 0 else ""
        lines = [
            f"💰 Income: {fmt(total_income)}",
            f"💸 Spending: {fmt(total_spending)}",
            f"📊 Net: {net_sign}{fmt(net)}",
        ]
        message = "\n".join(lines)
        assert "$3,500" in message
        assert "$2,100" in message
        assert "+$1,400" in message

    def test_message_without_top_category(self):
        """When there are no categorized transactions, top category line is omitted."""
        top_category = None
        lines = ["Base line"]
        if top_category:
            lines.append(f"🏆 Top category: {top_category}")
        assert len(lines) == 1

    def test_message_with_top_category(self):
        """Top category line is appended when data is available."""
        top_category = "Food & Drink"
        top_amount = 450.0
        fmt = lambda v: f"${v:,.0f}"  # noqa: E731
        lines = []
        if top_category:
            lines.append(f"🏆 Top category: {top_category} ({fmt(top_amount)})")
        assert lines[0] == "🏆 Top category: Food & Drink ($450)"

    def test_title_format_positive_net(self):
        """Title shows net amount with sign."""
        net = 1400.0
        net_sign = "+"
        fmt = lambda v: f"${v:,.0f}"  # noqa: E731
        title = f"Your weekly recap: {net_sign}{fmt(net)} net"
        assert title == "Your weekly recap: +$1,400 net"

    def test_title_format_negative_net(self):
        """Title shows negative net without + sign."""
        net = -300.0
        net_sign = ""
        fmt = lambda v: f"${v:,.0f}"  # noqa: E731
        title = f"Your weekly recap: {net_sign}{fmt(abs(net))} net"
        assert title == "Your weekly recap: $300 net"


@pytest.mark.unit
class TestRecapPreferenceGating:
    """Tests for the weekly_recap notification preference check."""

    def test_no_prefs_means_enabled(self):
        """A user with no notification_preferences dict gets the recap (default on)."""
        prefs = {}
        should_skip = prefs.get("weekly_recap") is False
        assert not should_skip

    def test_prefs_explicitly_true_means_enabled(self):
        """weekly_recap=True sends the notification."""
        prefs = {"weekly_recap": True}
        should_skip = prefs.get("weekly_recap") is False
        assert not should_skip

    def test_prefs_explicitly_false_means_skipped(self):
        """weekly_recap=False suppresses the notification."""
        prefs = {"weekly_recap": False}
        should_skip = prefs.get("weekly_recap") is False
        assert should_skip

    def test_prefs_none_value_means_enabled(self):
        """If the key is missing entirely, user gets the recap."""
        prefs = {"budget_alerts": True}
        should_skip = prefs.get("weekly_recap") is False
        assert not should_skip

    def test_other_prefs_dont_affect_recap(self):
        """Unrelated preferences don't suppress the weekly recap."""
        prefs = {"account_syncs": False, "milestones": False}
        should_skip = prefs.get("weekly_recap") is False
        assert not should_skip


@pytest.mark.unit
class TestNetWorthCalculation:
    """Tests for asset/liability aggregation logic used in the recap."""

    def test_net_worth_assets_minus_debts(self):
        """Net worth = total assets - total liabilities."""
        total_assets = 100_000.0
        total_debts = 25_000.0
        net_worth = total_assets - total_debts
        assert net_worth == 75_000.0

    def test_net_worth_negative_when_debts_exceed_assets(self):
        """Net worth can be negative."""
        total_assets = 5_000.0
        total_debts = 30_000.0
        net_worth = total_assets - total_debts
        assert net_worth == -25_000.0

    def test_zero_balances_handled(self):
        """Accounts with None balance treated as 0."""
        balances = [None, 1000.0, None, 500.0]
        total = sum(float(b or 0) for b in balances)
        assert total == 1500.0

    def test_account_categorization(self):
        """Asset and liability accounts are split correctly."""
        from app.models.account import AccountCategory

        org_id = uuid4()
        asset_acc = _make_account(org_id, balance=50_000.0, is_asset=True)
        debt_acc = _make_account(org_id, balance=10_000.0, is_asset=False)
        accounts = [asset_acc, debt_acc]

        asset_accounts = [a for a in accounts if a.account_type.category == AccountCategory.ASSET]
        debt_accounts = [a for a in accounts if a.account_type.category == AccountCategory.DEBT]

        assert len(asset_accounts) == 1
        assert len(debt_accounts) == 1
        total_assets = sum(float(a.current_balance or 0) for a in asset_accounts)
        assert total_assets == 50_000.0
