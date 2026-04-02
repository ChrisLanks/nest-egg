"""Unit tests for employer_match._build_item action string logic."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.api.v1.employer_match import _build_item
from app.models.account import AccountType
from app.models.contribution import AccountContribution, ContributionFrequency, ContributionType


def _make_account(
    match_pct=None,
    match_limit_pct=None,
    annual_salary=None,
    account_type=AccountType.RETIREMENT_401K,
):
    acct = MagicMock()
    acct.id = uuid4()
    acct.name = "My 401k"
    acct.account_type = account_type
    acct.employer_match_percent = match_pct
    acct.employer_match_limit_percent = match_limit_pct
    acct.annual_salary = str(annual_salary) if annual_salary is not None else None
    acct._user_name = "Alice"
    return acct


def _make_contrib(pct: float, freq=ContributionFrequency.MONTHLY):
    c = MagicMock(spec=AccountContribution)
    c.account_id = uuid4()
    c.is_active = True
    c.contribution_type = ContributionType.PERCENTAGE_GROWTH
    c.amount = pct
    c.frequency = freq
    c.created_at = MagicMock()
    return c


class TestBuildItemActionStrings:
    def test_no_match_config_shows_no_match_action(self):
        acct = _make_account()
        item = _build_item(acct, contrib=None)
        assert "No employer match" in item.action

    def test_match_pct_set_but_no_salary_shows_add_salary_action(self):
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=None)
        item = _build_item(acct, contrib=None)
        assert "annual salary" in item.action.lower()
        assert "No employer match" not in item.action

    def test_full_match_captured_shows_captured_action(self):
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=100_000)
        contrib = _make_contrib(pct=8.0)  # contributing 8% > 6% required
        item = _build_item(acct, contrib=contrib)
        assert item.is_capturing_full_match is True
        assert "captured" in item.action.lower()

    def test_under_contributing_shows_increase_action(self):
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=100_000)
        contrib = _make_contrib(pct=3.0)  # only 3%, need 6%
        item = _build_item(acct, contrib=contrib)
        assert item.is_capturing_full_match is False
        assert "6%" in item.action

    def test_match_percent_only_no_limit_no_salary_shows_add_salary(self):
        """Only match_pct set, no limit, no salary → still prompt for salary."""
        acct = _make_account(match_pct=100, match_limit_pct=None, annual_salary=None)
        item = _build_item(acct, contrib=None)
        assert "annual salary" in item.action.lower()

    def test_annual_match_value_computed_correctly(self):
        """annual_match_value = salary * limit_pct * match_pct."""
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=100_000)
        item = _build_item(acct, contrib=None)
        # 50% of 6% of $100k = $3,000
        assert item.annual_match_value == pytest.approx(3_000.0, abs=0.01)

    def test_annual_match_value_none_when_salary_missing(self):
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=None)
        item = _build_item(acct, contrib=None)
        assert item.annual_match_value is None

    def test_left_on_table_is_full_match_when_no_contribution(self):
        """No contribution record → assume zero captured → full match left on table."""
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=100_000)
        item = _build_item(acct, contrib=None)
        assert item.estimated_left_on_table == pytest.approx(3_000.0, abs=0.01)

    def test_left_on_table_is_zero_when_full_match_captured(self):
        acct = _make_account(match_pct=50, match_limit_pct=6, annual_salary=100_000)
        contrib = _make_contrib(pct=10.0)  # well above 6% cap
        item = _build_item(acct, contrib=contrib)
        assert item.is_capturing_full_match is True
        assert (item.estimated_left_on_table or 0.0) == pytest.approx(0.0, abs=0.01)

    def test_user_name_falls_back_to_unknown_if_not_set(self):
        acct = _make_account()
        acct._user_name = None
        item = _build_item(acct, contrib=None)
        assert item.user_name == "Unknown"
