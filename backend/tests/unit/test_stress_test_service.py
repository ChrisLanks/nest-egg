"""Unit tests for StressTestService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest
from sqlalchemy.sql import ClauseElement

from app.constants.financial import STRESS_TEST
from app.services.stress_test_service import (
    StressTestService,
    EQUITY_ACCOUNT_TYPES,
    BOND_ACCOUNT_TYPES,
)


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def org_id():
    return uuid4()


def _make_portfolio(equity=0.0, bonds=0.0, other=0.0):
    """Build a portfolio composition dict."""
    return {
        "equity": equity,
        "bonds": bonds,
        "other": other,
        "total": equity + bonds + other,
    }


# ── run_scenario ──────────────────────────────────────────────────────────


class TestRunScenario:
    def test_run_scenario_gfc(self):
        """100% equity portfolio drops ~57% under GFC 2008 scenario."""
        portfolio = _make_portfolio(equity=100_000.0)
        result = StressTestService.run_scenario(portfolio, "gfc_2008")

        assert result["scenario_key"] == "gfc_2008"
        assert result["portfolio_before"] == pytest.approx(100_000.0)
        # equity_drop = -0.57 → 43,000 remaining
        assert result["portfolio_after"] == pytest.approx(43_000.0, abs=1.0)
        assert result["pct_change"] == pytest.approx(-0.57, abs=0.001)

    def test_run_scenario_bond_only(self):
        """Bond-only portfolio barely affected by equity crash (GFC)."""
        portfolio = _make_portfolio(bonds=100_000.0)
        result = StressTestService.run_scenario(portfolio, "gfc_2008")

        # GFC bond_change = +0.08 (flight to safety)
        assert result["portfolio_after"] == pytest.approx(108_000.0, abs=1.0)
        assert result["pct_change"] == pytest.approx(0.08, abs=0.001)
        assert result["by_asset_class"]["equity"]["before"] == pytest.approx(0.0)
        assert result["by_asset_class"]["equity"]["after"] == pytest.approx(0.0)

    def test_run_scenario_invalid_key(self):
        """Raises ValueError for an unknown scenario key."""
        portfolio = _make_portfolio(equity=100_000.0)
        with pytest.raises(ValueError, match="Unknown scenario"):
            StressTestService.run_scenario(portfolio, "nonexistent_scenario_xyz")

    def test_rate_shock_bonds(self):
        """Bonds drop when rates rise in the rate_shock_200bps scenario."""
        portfolio = _make_portfolio(bonds=100_000.0)
        result = StressTestService.run_scenario(portfolio, "rate_shock_200bps")

        # rate_increase_bps=200, avg_duration=6, sensitivity=-0.01/100bps
        # bond_change = 6 * -0.01 * (200/100) = -0.12
        assert result["by_asset_class"]["bonds"]["change_pct"] == pytest.approx(-0.12, abs=0.001)
        assert result["portfolio_after"] < result["portfolio_before"]

    def test_run_scenario_mixed_portfolio(self):
        """Mixed equity+bond portfolio correctly splits scenario impact."""
        portfolio = _make_portfolio(equity=70_000.0, bonds=30_000.0)
        result = StressTestService.run_scenario(portfolio, "market_crash_30")

        # equity_drop=-0.30 → 49,000; bond_change=+0.05 → 31,500
        expected_after = 70_000 * 0.70 + 30_000 * 1.05
        assert result["portfolio_after"] == pytest.approx(expected_after, abs=1.0)

    def test_scenario_label_present(self):
        """Each scenario result includes a human-readable label."""
        portfolio = _make_portfolio(equity=50_000.0)
        result = StressTestService.run_scenario(portfolio, "dot_com_2000")
        assert "Dot-Com" in result["scenario_label"]

    def test_zero_portfolio_pct_change_is_zero(self):
        """Zero portfolio doesn't cause division by zero."""
        portfolio = _make_portfolio()
        result = StressTestService.run_scenario(portfolio, "gfc_2008")
        assert result["pct_change"] == pytest.approx(0.0)


# ── run_all_scenarios ─────────────────────────────────────────────────────


def _empty_db_mock(mock_db):
    """Set mock_db.execute to return empty holdings (pass 1) and empty accounts (pass 2)."""
    holding_result = MagicMock()
    holding_result.all.return_value = []
    balance_result = MagicMock()
    balance_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[holding_result, balance_result])


def _holding_db_mock(mock_db, holding_rows):
    """Set mock_db.execute for pass 1 (holdings) with given rows, pass 2 empty accounts."""
    holding_result = MagicMock()
    holding_result.all.return_value = holding_rows
    balance_result = MagicMock()
    balance_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[holding_result, balance_result])


class TestRunAllScenarios:
    @pytest.mark.asyncio
    async def test_run_all_scenarios_returns_all(self, mock_db, org_id):
        """All 6 scenarios are returned."""
        _empty_db_mock(mock_db)
        results = await StressTestService.run_all_scenarios(
            db=mock_db,
            organization_id=org_id,
        )
        expected_count = len(STRESS_TEST.SCENARIOS)
        assert len(results) == expected_count

    @pytest.mark.asyncio
    async def test_run_all_scenarios_sorted_worst_first(self, mock_db, org_id):
        """Results are sorted from worst (most negative) to best pct_change."""
        _empty_db_mock(mock_db)
        results = await StressTestService.run_all_scenarios(
            db=mock_db,
            organization_id=org_id,
        )
        pct_changes = [r["pct_change"] for r in results]
        assert pct_changes == sorted(pct_changes)


# ── SQL enum-cast regression ──────────────────────────────────────────────


class TestPassTwoSqlEnumCast:
    """Regression: asyncpg raises 'invalid input value for enum accounttype'
    when SQLAlchemy passes enum members directly in IN().  The fix casts the
    column to String and passes .name (uppercase) values."""

    def test_investment_account_type_names_are_uppercase(self):
        """All values passed to IN() must be uppercase strings (DB storage format)."""
        INVESTMENT_ACCOUNT_TYPES = EQUITY_ACCOUNT_TYPES | BOND_ACCOUNT_TYPES
        names = [t.name for t in INVESTMENT_ACCOUNT_TYPES]
        for name in names:
            assert name == name.upper(), f"{name!r} is not uppercase"

    def test_equity_and_bond_types_are_disjoint(self):
        """No account type appears in both equity and bond sets."""
        overlap = EQUITY_ACCOUNT_TYPES & BOND_ACCOUNT_TYPES
        assert overlap == set(), f"Overlapping types: {overlap}"

    @pytest.mark.asyncio
    async def test_pass2_query_executed_once(self, mock_db, org_id):
        """get_portfolio_composition issues exactly two execute() calls:
        pass 1 (holdings JOIN accounts) and pass 2 (balance-only accounts)."""
        _empty_db_mock(mock_db)
        await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert mock_db.execute.call_count == 2

    def test_pass2_uses_name_not_value(self):
        """Verify that .name (uppercase) is used for the IN() list, not .value
        (lowercase). asyncpg expects the stored enum label, which is uppercase."""
        from app.models.account import AccountType
        INVESTMENT_ACCOUNT_TYPES = EQUITY_ACCOUNT_TYPES | BOND_ACCOUNT_TYPES
        names = [t.name for t in INVESTMENT_ACCOUNT_TYPES]
        values = [t.value for t in INVESTMENT_ACCOUNT_TYPES]
        # Names are uppercase (DB storage format)
        assert all(n == n.upper() for n in names)
        # Values are lowercase (Python enum definition) — these would fail in asyncpg
        assert all(v == v.lower() for v in values)
        # Names and values are different — the bug is passing values
        assert set(names) != set(values)

    @pytest.mark.asyncio
    async def test_pass2_sql_uses_cast_string(self, mock_db, org_id):
        """The pass-2 statement wraps account_type in CAST(... AS VARCHAR) so
        asyncpg does not attempt to bind plain strings as the accounttype enum.

        We inspect the where-clause AST rather than compiling to SQL (SQLAlchemy's
        SQLEnum compile recurses infinitely in dialect-less unit test environments)."""
        from sqlalchemy import Cast, String
        from sqlalchemy.sql.elements import BinaryExpression, ClauseList

        _empty_db_mock(mock_db)
        await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        _, pass2_stmt = [c.args[0] for c in mock_db.execute.call_args_list]

        # Walk the WHERE clause looking for a Cast(account_type, String) node
        found_cast = False
        for clause in pass2_stmt.whereclause.clauses:
            # Each clause is a BinaryExpression; the left side of IN() is a Cast
            left = getattr(clause, "left", None)
            if isinstance(left, Cast):
                if isinstance(left.type, String):
                    found_cast = True
                    break

        assert found_cast, (
            "pass-2 query should use cast(Account.account_type, String).in_() "
            "to avoid asyncpg 'invalid input value for enum accounttype' error"
        )


# ── get_portfolio_composition ─────────────────────────────────────────────


class TestGetPortfolioComposition:
    @pytest.mark.asyncio
    async def test_empty_portfolio(self, mock_db, org_id):
        """Empty portfolio returns zeros."""
        _empty_db_mock(mock_db)
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == 0.0
        assert result["bonds"] == 0.0
        assert result["other"] == 0.0
        assert result["total"] == 0.0

    @pytest.mark.asyncio
    async def test_classifies_bond_asset_type(self, mock_db, org_id):
        """Holdings with asset_type='bond' go to bonds bucket."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("10000")
        holding.asset_type = "bond"
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["bonds"] == pytest.approx(10000.0)
        assert result["equity"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_classifies_stock_as_equity(self, mock_db, org_id):
        """Holdings with asset_type='stock' go to equity bucket."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("25000")
        holding.asset_type = "stock"
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(25000.0)
        assert result["bonds"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_null_asset_type_equity_account_classifies_as_equity(self, mock_db, org_id):
        """Holding with no asset_type on a brokerage account → equity (not other)."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("500")
        holding.asset_type = None
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(500.0)
        assert result["other"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_null_asset_type_on_retirement_account_classifies_as_equity(self, mock_db, org_id):
        """Holding with no asset_type on a 401k account → equity."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("50000")
        holding.asset_type = None
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.RETIREMENT_401K
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(50000.0)

    @pytest.mark.asyncio
    async def test_asset_class_bond_classifies_as_bond(self, mock_db, org_id):
        """Holding with asset_class='bond' goes to bonds even if asset_type is unset."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("15000")
        holding.asset_type = None
        holding.asset_class = "bond"

        account = MagicMock()
        account.account_type = AccountType.BROKERAGE
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["bonds"] == pytest.approx(15000.0)
        assert result["equity"] == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_bond_account_type_classifies_as_bond(self, mock_db, org_id):
        """Account with AccountType.BOND goes to bonds bucket."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("20000")
        holding.asset_type = None
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.BOND
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["bonds"] == pytest.approx(20000.0)

    @pytest.mark.asyncio
    async def test_balance_only_account_counted_when_no_holdings(self, mock_db, org_id):
        """Accounts with no holdings use current_balance, classified by account type."""
        from app.models.account import AccountType

        account = MagicMock()
        account.id = uuid4()
        account.account_type = AccountType.RETIREMENT_401K
        account.current_balance = Decimal("50000")
        account.is_active = True

        # Pass 1: no holdings at all
        holding_result = MagicMock()
        holding_result.all.return_value = []
        # Pass 2: one investment account with a balance
        balance_result = MagicMock()
        balance_result.scalars.return_value.all.return_value = [account]
        mock_db.execute = AsyncMock(side_effect=[holding_result, balance_result])

        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(50000.0)
        assert result["other"] == pytest.approx(0.0)
        assert result["total"] == pytest.approx(50000.0)

    @pytest.mark.asyncio
    async def test_balance_not_double_counted_when_holdings_exist(self, mock_db, org_id):
        """Account already counted via holdings is not also counted via balance."""
        from app.models.account import AccountType

        acct_id = uuid4()
        holding = MagicMock()
        holding.current_total_value = Decimal("500")
        holding.asset_type = "etf"
        holding.asset_class = None

        account = MagicMock()
        account.id = acct_id
        account.account_type = AccountType.BROKERAGE
        account.current_balance = Decimal("500")
        account.is_active = True

        holding_result = MagicMock()
        holding_result.all.return_value = [(holding, account)]
        balance_result = MagicMock()
        balance_result.scalars.return_value.all.return_value = [account]
        mock_db.execute = AsyncMock(side_effect=[holding_result, balance_result])

        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        # $500 counted once, not $1000
        assert result["equity"] == pytest.approx(500.0)
        assert result["total"] == pytest.approx(500.0)

    @pytest.mark.asyncio
    async def test_sep_ira_classifies_as_equity(self, mock_db, org_id):
        """SEP-IRA account with no asset_type goes to equity (was missing from set)."""
        from app.models.account import AccountType

        holding = MagicMock()
        holding.current_total_value = Decimal("75000")
        holding.asset_type = None
        holding.asset_class = None

        account = MagicMock()
        account.account_type = AccountType.RETIREMENT_SEP_IRA
        account.is_active = True

        _holding_db_mock(mock_db, [(holding, account)])
        result = await StressTestService.get_portfolio_composition(
            db=mock_db,
            organization_id=org_id,
        )
        assert result["equity"] == pytest.approx(75000.0)
        assert result["other"] == pytest.approx(0.0)
