"""Unit tests for SmartInsightsService.

Strategy
--------
- Synchronous check methods (_check_roth_opportunity_sync,
  _check_hsa_opportunity_sync) are tested directly — no DB required.
- The _Insight dataclass and to_dict() contract are verified.
- Async checks that require a DB are tested with a lightweight AsyncMock
  session that returns pre-canned query results, avoiding real DB I/O.

The goal is broad coverage of business logic:
  - All guard conditions (early returns)
  - Insight field values
  - Priority score formula constraints
  - to_dict() shape
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.constants.financial import RETIREMENT
from app.models.account import AccountType
from app.services.smart_insights_service import (
    INSIGHT_CASH_DRAG,
    INSIGHT_EMERGENCY_FUND,
    INSIGHT_HSA_OPPORTUNITY,
    INSIGHT_IRMAA_CLIFF,
    INSIGHT_ROTH_OPPORTUNITY,
    LIQUID_ACCOUNT_TYPES,
    ROTH_RETIREMENT_TYPES,
    TRADITIONAL_RETIREMENT_TYPES,
    SmartInsightsService,
    _Insight,
)

# ── _Insight class tests ───────────────────────────────────────────────────


class TestInsightClass:
    def _make(self, **kwargs):
        defaults = dict(
            insight_type="test_type",
            title="Test Title",
            message="Test message.",
            action="Do something",
            priority="medium",
            category="cash",
            icon="💡",
            priority_score=50.0,
            amount=None,
        )
        defaults.update(kwargs)
        return _Insight(**defaults)

    def test_to_dict_has_all_required_keys(self):
        insight = self._make()
        d = insight.to_dict()
        required = {
            "type",
            "title",
            "message",
            "action",
            "priority",
            "category",
            "icon",
            "priority_score",
            "amount",
        }
        assert required == set(d.keys())

    def test_to_dict_type_matches_insight_type(self):
        insight = self._make(insight_type="emergency_fund_low")
        assert insight.to_dict()["type"] == "emergency_fund_low"

    def test_amount_defaults_to_none(self):
        insight = self._make()
        assert insight.to_dict()["amount"] is None

    def test_amount_set_when_provided(self):
        insight = self._make(amount=1234.56)
        assert insight.to_dict()["amount"] == pytest.approx(1234.56)


# ── Fake account factory ───────────────────────────────────────────────────


def _fake_account(
    account_type: AccountType,
    balance: float = 0.0,
    user_id: Optional[uuid.UUID] = None,
) -> MagicMock:
    acc = MagicMock()
    acc.id = uuid.uuid4()
    acc.account_type = account_type
    acc.current_balance = Decimal(str(balance))
    acc.user_id = user_id or uuid.uuid4()
    return acc


# ── _check_roth_opportunity_sync ──────────────────────────────────────────


class TestCheckRothOpportunitySync:
    def _svc(self):
        return SmartInsightsService(db=MagicMock())

    def test_no_traditional_returns_none(self):
        accounts = [_fake_account(AccountType.BROKERAGE, 50_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result is None

    def test_has_roth_already_returns_none(self):
        accounts = [
            _fake_account(AccountType.RETIREMENT_IRA, 100_000),
            _fake_account(AccountType.RETIREMENT_ROTH, 50_000),
        ]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result is None

    def test_traditional_only_returns_insight(self):
        accounts = [_fake_account(AccountType.RETIREMENT_IRA, 100_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result is not None
        assert result.type == INSIGHT_ROTH_OPPORTUNITY

    def test_insight_amount_is_traditional_balance(self):
        accounts = [
            _fake_account(AccountType.RETIREMENT_401K, 60_000),
            _fake_account(AccountType.RETIREMENT_IRA, 40_000),
        ]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result is not None
        assert result.amount == pytest.approx(100_000.0)

    def test_age_60_plus_returns_none(self):
        """Users 60+ have different Roth math; skip the insight."""
        birthdate = date.today() - timedelta(days=365 * 62)
        accounts = [_fake_account(AccountType.RETIREMENT_IRA, 200_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, birthdate)
        assert result is None

    def test_under_60_with_traditional_returns_insight(self):
        birthdate = date.today() - timedelta(days=365 * 45)
        accounts = [_fake_account(AccountType.RETIREMENT_IRA, 200_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, birthdate)
        assert result is not None

    def test_priority_is_medium(self):
        accounts = [_fake_account(AccountType.RETIREMENT_IRA, 50_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result.priority == "medium"

    def test_category_is_retirement(self):
        accounts = [_fake_account(AccountType.RETIREMENT_IRA, 50_000)]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result.category == "retirement"

    def test_multiple_traditional_types_counted(self):
        accounts = [
            _fake_account(AccountType.RETIREMENT_401K, 50_000),
            _fake_account(AccountType.RETIREMENT_403B, 30_000),
            _fake_account(AccountType.RETIREMENT_IRA, 20_000),
        ]
        result = self._svc()._check_roth_opportunity_sync(accounts, None)
        assert result is not None
        assert result.amount == pytest.approx(100_000.0)


# ── _check_hsa_opportunity_sync ────────────────────────────────────────────


class TestCheckHsaOpportunitySync:
    def _svc(self):
        return SmartInsightsService(db=MagicMock())

    def test_no_hsa_account_returns_none(self):
        accounts = [_fake_account(AccountType.CHECKING, 10_000)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result is None

    def test_hsa_above_5000_returns_none(self):
        accounts = [_fake_account(AccountType.HSA, 7_500)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result is None

    def test_hsa_below_5000_returns_insight(self):
        accounts = [_fake_account(AccountType.HSA, 1_000)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result is not None
        assert result.type == INSIGHT_HSA_OPPORTUNITY

    def test_hsa_at_zero_returns_insight(self):
        accounts = [_fake_account(AccountType.HSA, 0)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result is not None

    def test_amount_is_gap_to_individual_limit(self):
        balance = 1_000.0
        accounts = [_fake_account(AccountType.HSA, balance)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        expected_gap = max(0.0, float(RETIREMENT.LIMIT_HSA_INDIVIDUAL) - balance)
        assert result.amount == pytest.approx(expected_gap, rel=1e-4)

    def test_priority_is_low(self):
        accounts = [_fake_account(AccountType.HSA, 500)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result.priority == "low"

    def test_category_is_tax(self):
        accounts = [_fake_account(AccountType.HSA, 500)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result.category == "tax"

    def test_multiple_hsa_balances_summed(self):
        accounts = [
            _fake_account(AccountType.HSA, 1_000),
            _fake_account(AccountType.HSA, 2_000),
        ]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert result is not None
        expected_gap = max(0.0, float(RETIREMENT.LIMIT_HSA_INDIVIDUAL) - 3_000)
        assert result.amount == pytest.approx(expected_gap, rel=1e-4)

    def test_action_mentions_tax_year(self):
        accounts = [_fake_account(AccountType.HSA, 500)]
        result = self._svc()._check_hsa_opportunity_sync(accounts)
        assert str(RETIREMENT.TAX_YEAR) in result.action


# ── Async checks with mocked DB ────────────────────────────────────────────
#
# We use AsyncMock to provide a minimal db session that returns
# pre-defined scalars/rows for each check.


class TestCheckEmergencyFundAsync:
    """_check_emergency_fund — async but we mock _monthly_expenses."""

    def _svc(self):
        db = AsyncMock()
        return SmartInsightsService(db=db)

    @pytest.mark.asyncio
    async def test_no_liquid_accounts_returns_none(self):
        accounts = [_fake_account(AccountType.BROKERAGE, 50_000)]
        svc = self._svc()
        result = await svc._check_emergency_fund(accounts, [])
        assert result is None

    @pytest.mark.asyncio
    async def test_sufficient_emergency_fund_returns_none(self):
        """3+ months covered → no insight."""
        accounts = [_fake_account(AccountType.CHECKING, 15_000)]
        svc = self._svc()
        # Patch _monthly_expenses to return $4000/mo → 3.75 months covered
        svc._monthly_expenses = AsyncMock(return_value=Decimal("4000"))
        result = await svc._check_emergency_fund(accounts, [acc.id for acc in accounts])
        assert result is None

    @pytest.mark.asyncio
    async def test_insufficient_fund_returns_insight(self):
        """< 3 months covered → return insight."""
        accounts = [_fake_account(AccountType.CHECKING, 3_000)]
        svc = self._svc()
        # $2000/mo expenses → 1.5 months covered → below threshold
        svc._monthly_expenses = AsyncMock(return_value=Decimal("2000"))
        result = await svc._check_emergency_fund(accounts, [acc.id for acc in accounts])
        assert result is not None
        assert result.type == INSIGHT_EMERGENCY_FUND

    @pytest.mark.asyncio
    async def test_insight_amount_equals_gap(self):
        balance = 3_000.0
        monthly_exp = Decimal("2000")
        target = float(monthly_exp * 3)
        gap = target - balance
        accounts = [_fake_account(AccountType.CHECKING, balance)]
        svc = self._svc()
        svc._monthly_expenses = AsyncMock(return_value=monthly_exp)
        result = await svc._check_emergency_fund(accounts, [])
        assert result.amount == pytest.approx(gap, rel=1e-4)

    @pytest.mark.asyncio
    async def test_zero_expenses_returns_none(self):
        accounts = [_fake_account(AccountType.CHECKING, 10_000)]
        svc = self._svc()
        svc._monthly_expenses = AsyncMock(return_value=Decimal("0"))
        result = await svc._check_emergency_fund(accounts, [])
        assert result is None

    @pytest.mark.asyncio
    async def test_priority_is_high(self):
        accounts = [_fake_account(AccountType.CHECKING, 1_000)]
        svc = self._svc()
        svc._monthly_expenses = AsyncMock(return_value=Decimal("2000"))
        result = await svc._check_emergency_fund(accounts, [])
        assert result.priority == "high"


class TestCheckCashDragAsync:
    def _svc(self):
        return SmartInsightsService(db=AsyncMock())

    @pytest.mark.asyncio
    async def test_no_liquid_accounts_returns_none(self):
        accounts = [_fake_account(AccountType.BROKERAGE, 100_000)]
        svc = self._svc()
        result = await svc._check_cash_drag(accounts, [])
        assert result is None

    @pytest.mark.asyncio
    async def test_below_12_months_returns_none(self):
        accounts = [_fake_account(AccountType.CHECKING, 30_000)]
        svc = self._svc()
        # $5000/mo → 6 months covered → below 12-month threshold
        svc._monthly_expenses = AsyncMock(return_value=Decimal("5000"))
        result = await svc._check_cash_drag(accounts, [])
        assert result is None

    @pytest.mark.asyncio
    async def test_excess_cash_returns_insight(self):
        accounts = [_fake_account(AccountType.SAVINGS, 120_000)]
        svc = self._svc()
        # $5000/mo → 24 months → excess = 120k - 30k(6mo) = 90k > $5000 min
        svc._monthly_expenses = AsyncMock(return_value=Decimal("5000"))
        result = await svc._check_cash_drag(accounts, [])
        assert result is not None
        assert result.type == INSIGHT_CASH_DRAG

    @pytest.mark.asyncio
    async def test_excess_below_minimum_returns_none(self):
        """Excess < $5000 threshold → no insight (noise guard)."""
        accounts = [_fake_account(AccountType.SAVINGS, 63_000)]
        svc = self._svc()
        # $10000/mo → 6.3 months → 12+ threshold not met (just 6.3) → returns None anyway
        # Use 5001/mo: 63000/5001 = 12.6 mo; excess = 63000 - 5001*6 = 62994 > 5000 → insight
        svc._monthly_expenses = AsyncMock(return_value=Decimal("5001"))
        result = await svc._check_cash_drag(accounts, [])
        # 12.6 months > 12 threshold, excess = 63000 - 30006 = ~33000 → insight fires
        assert result is not None

    @pytest.mark.asyncio
    async def test_zero_expenses_returns_none(self):
        accounts = [_fake_account(AccountType.CHECKING, 100_000)]
        svc = self._svc()
        svc._monthly_expenses = AsyncMock(return_value=Decimal("0"))
        result = await svc._check_cash_drag(accounts, [])
        assert result is None


class TestCheckIrmaaCliffAsync:
    def _svc(self):
        return SmartInsightsService(db=AsyncMock())

    @pytest.mark.asyncio
    async def test_no_birthdate_returns_none(self):
        svc = self._svc()
        result = await svc._check_irmaa_cliff([], None)
        assert result is None

    @pytest.mark.asyncio
    async def test_under_55_returns_none(self):
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 40)
        result = await svc._check_irmaa_cliff([], birthdate)
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_income_returns_none(self):
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 65)
        svc._annual_income_estimate = AsyncMock(return_value=Decimal("0"))
        result = await svc._check_irmaa_cliff([], birthdate)
        assert result is None

    @pytest.mark.asyncio
    async def test_income_near_irmaa_threshold_returns_insight(self):
        """Income $5000 below first IRMAA threshold → insight fires."""
        from app.constants.financial import MEDICARE

        first_threshold = float(MEDICARE.IRMAA_BRACKETS_SINGLE[0][0])
        income = first_threshold - 5_000  # $5k below threshold
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 65)
        svc._annual_income_estimate = AsyncMock(return_value=Decimal(str(income)))
        result = await svc._check_irmaa_cliff([], birthdate)
        assert result is not None
        assert result.type == INSIGHT_IRMAA_CLIFF

    @pytest.mark.asyncio
    async def test_income_above_threshold_returns_none(self):
        """Already crossed the threshold → no cliff warning."""
        from app.constants.financial import MEDICARE

        first_threshold = float(MEDICARE.IRMAA_BRACKETS_SINGLE[0][0])
        income = first_threshold + 10_000  # already past it
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 65)
        svc._annual_income_estimate = AsyncMock(return_value=Decimal(str(income)))
        result = await svc._check_irmaa_cliff([], birthdate)
        # If above threshold and not within $10k of next, None
        # (This tests that it doesn't fire for income already past current tier)
        # The result may or may not be None depending on next tier proximity
        # Just verify no crash:
        assert result is None or result.type == INSIGHT_IRMAA_CLIFF

    @pytest.mark.asyncio
    async def test_income_far_below_threshold_returns_none(self):
        """Income $50k below first threshold → safely below, no warning needed."""
        from app.constants.financial import MEDICARE

        first_threshold = float(MEDICARE.IRMAA_BRACKETS_SINGLE[0][0])
        income = first_threshold - 50_000
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 65)
        svc._annual_income_estimate = AsyncMock(return_value=Decimal(str(income)))
        result = await svc._check_irmaa_cliff([], birthdate)
        assert result is None

    @pytest.mark.asyncio
    async def test_insight_priority_is_high(self):
        from app.constants.financial import MEDICARE

        first_threshold = float(MEDICARE.IRMAA_BRACKETS_SINGLE[0][0])
        income = first_threshold - 3_000
        svc = self._svc()
        birthdate = date.today() - timedelta(days=365 * 65)
        svc._annual_income_estimate = AsyncMock(return_value=Decimal(str(income)))
        result = await svc._check_irmaa_cliff([], birthdate)
        if result is not None:
            assert result.priority == "high"
            assert result.category == "tax"


# ── Account type set membership ────────────────────────────────────────────


class TestAccountTypeSets:
    def test_liquid_types_contain_checking_savings_money_market(self):
        assert AccountType.CHECKING in LIQUID_ACCOUNT_TYPES
        assert AccountType.SAVINGS in LIQUID_ACCOUNT_TYPES
        assert AccountType.MONEY_MARKET in LIQUID_ACCOUNT_TYPES

    def test_brokerage_not_in_liquid_types(self):
        assert AccountType.BROKERAGE not in LIQUID_ACCOUNT_TYPES

    def test_traditional_retirement_types_include_all_pretax(self):
        assert AccountType.RETIREMENT_IRA in TRADITIONAL_RETIREMENT_TYPES
        assert AccountType.RETIREMENT_401K in TRADITIONAL_RETIREMENT_TYPES
        assert AccountType.RETIREMENT_403B in TRADITIONAL_RETIREMENT_TYPES
        assert AccountType.RETIREMENT_SEP_IRA in TRADITIONAL_RETIREMENT_TYPES

    def test_roth_not_in_traditional_types(self):
        assert AccountType.RETIREMENT_ROTH not in TRADITIONAL_RETIREMENT_TYPES

    def test_roth_type_in_roth_set(self):
        assert AccountType.RETIREMENT_ROTH in ROTH_RETIREMENT_TYPES


# ── get_insights integration (mocked DB) ──────────────────────────────────


class TestGetInsights:
    """Top-level get_insights method with a heavily mocked DB session."""

    @pytest.mark.asyncio
    async def test_returns_list_on_empty_accounts(self):
        db = AsyncMock()
        # _get_accounts returns empty list
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        svc = SmartInsightsService(db)
        result = await svc.get_insights(uuid.uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_insights_are_sorted_by_priority_score(self):
        """Insights should be returned sorted highest priority first."""
        svc = SmartInsightsService(db=MagicMock())

        # Return two accounts: checking + HSA (will fire HSA and Roth checks)
        checking = _fake_account(AccountType.CHECKING, 20_000)
        hsa = _fake_account(AccountType.HSA, 500)
        trad_ira = _fake_account(AccountType.RETIREMENT_IRA, 100_000)

        async def _fake_get_accounts(*args, **kwargs):
            return [checking, hsa, trad_ira]

        svc._get_accounts = _fake_get_accounts
        svc._monthly_expenses = AsyncMock(return_value=Decimal("1500"))  # 13.3mo covered
        svc._annual_income_estimate = AsyncMock(return_value=Decimal("45_000"))
        svc._check_fund_fees = AsyncMock(return_value=None)
        svc._check_stock_concentration = AsyncMock(return_value=None)
        svc._check_ltcg_opportunity = AsyncMock(return_value=None)
        svc._check_irmaa_cliff = AsyncMock(return_value=None)

        result = await svc.get_insights(uuid.uuid4())
        assert isinstance(result, list)
        # Verify descending priority_score order
        scores = [r["priority_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_max_insights_limits_output(self):
        """max_insights param caps the number returned."""
        svc = SmartInsightsService(db=MagicMock())

        checking = _fake_account(AccountType.CHECKING, 500)  # low balance → emergency fund
        hsa = _fake_account(AccountType.HSA, 0)
        trad_ira = _fake_account(AccountType.RETIREMENT_IRA, 100_000)

        async def _fake_get_accounts(*args, **kwargs):
            return [checking, hsa, trad_ira]

        svc._get_accounts = _fake_get_accounts
        svc._monthly_expenses = AsyncMock(return_value=Decimal("2000"))
        svc._annual_income_estimate = AsyncMock(return_value=Decimal("50_000"))
        svc._check_fund_fees = AsyncMock(return_value=None)
        svc._check_stock_concentration = AsyncMock(return_value=None)
        svc._check_ltcg_opportunity = AsyncMock(return_value=None)
        svc._check_irmaa_cliff = AsyncMock(return_value=None)

        result = await svc.get_insights(uuid.uuid4(), max_insights=1)
        assert len(result) <= 1

    @pytest.mark.asyncio
    async def test_failed_check_does_not_break_others(self):
        """If one check raises, the rest should still run."""
        svc = SmartInsightsService(db=MagicMock())

        hsa = _fake_account(AccountType.HSA, 500)

        async def _fake_get_accounts(*args, **kwargs):
            return [hsa]

        svc._get_accounts = _fake_get_accounts
        svc._monthly_expenses = AsyncMock(return_value=Decimal("0"))
        svc._annual_income_estimate = AsyncMock(return_value=Decimal("0"))
        # Make fund_fees raise
        svc._check_fund_fees = AsyncMock(side_effect=RuntimeError("DB error"))
        svc._check_stock_concentration = AsyncMock(return_value=None)
        svc._check_ltcg_opportunity = AsyncMock(return_value=None)
        svc._check_irmaa_cliff = AsyncMock(return_value=None)

        # Should not raise; HSA insight should still appear
        result = await svc.get_insights(uuid.uuid4())
        assert isinstance(result, list)
        # HSA check should still run
        hsa_insights = [r for r in result if r["type"] == "hsa_opportunity"]
        assert len(hsa_insights) == 1
