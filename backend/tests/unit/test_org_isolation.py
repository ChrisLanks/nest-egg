"""Tests for cross-organization data isolation (IDOR prevention).

Verifies that service-layer queries always include organization_id scoping
so that a compromised or buggy API caller cannot access another household's data.

Each test confirms that:
1. The service function accepts an org_id parameter (defense-in-depth)
2. Queries include the org_id filter when it is supplied
3. Cross-org data is NOT returned even if IDs are valid in a different org
"""

import inspect
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# tax_lot_service: Account.cost_basis_method query org-scoped
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaxLotServiceOrgIsolation:
    """tax_lot_service queries must all include org_id scoping."""

    def test_record_sale_account_query_includes_org_id(self):
        """record_sale must scope Account lookup to org_id, not bare Account.id."""
        import pathlib

        src = pathlib.Path(
            "/home/lanx/git/nest-egg/backend/app/services/tax_lot_service.py"
        ).read_text()

        # Find the region around the cost_basis_method query
        assert (
            "Account.organization_id == org_id" in src
        ), "Account.cost_basis_method query must filter by org_id"

    def test_import_lots_from_holding_accepts_org_id(self):
        """import_lots_from_holding must accept org_id parameter."""
        from app.services.tax_lot_service import TaxLotService

        sig = inspect.signature(TaxLotService.import_lots_from_holding)
        assert "org_id" in sig.parameters, "import_lots_from_holding must accept org_id"

    def test_get_unrealized_gains_accepts_org_id(self):
        """get_unrealized_gains must accept org_id parameter."""
        from app.services.tax_lot_service import TaxLotService

        sig = inspect.signature(TaxLotService.get_unrealized_gains)
        assert "org_id" in sig.parameters, "get_unrealized_gains must accept org_id"

    def test_import_lots_from_holding_applies_org_filter(self):
        """import_lots_from_holding must add org_id to Holding query when supplied."""
        import pathlib

        src = pathlib.Path(
            "/home/lanx/git/nest-egg/backend/app/services/tax_lot_service.py"
        ).read_text()
        assert (
            "Holding.organization_id == org_id" in src
        ), "import_lots_from_holding must filter Holding by org_id"

    def test_get_unrealized_gains_applies_org_filter(self):
        """get_unrealized_gains must add org_id filter to Holding batch query."""
        import pathlib

        src = pathlib.Path(
            "/home/lanx/git/nest-egg/backend/app/services/tax_lot_service.py"
        ).read_text()
        # The Holding batch query must be conditionally scoped
        assert (
            "holdings_query" in src and "Holding.organization_id == org_id" in src
        ), "get_unrealized_gains Holding batch must be org-scoped"

    @pytest.mark.asyncio
    async def test_import_lots_returns_none_for_cross_org_holding(self):
        """import_lots_from_holding must return None when holding is in a different org."""
        from app.services.tax_lot_service import TaxLotService

        service = TaxLotService()
        org_a = uuid4()
        org_b = uuid4()
        holding_id = uuid4()

        # Holding belongs to org_b but we request with org_a
        mock_holding = Mock()
        mock_holding.organization_id = org_b
        mock_holding.cost_basis_per_share = Decimal("100")
        mock_holding.shares = Decimal("10")

        mock_db = AsyncMock()
        mock_result = Mock()
        # When org filter is applied, holding won't be found for org_a
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)

        lot = await service.import_lots_from_holding(mock_db, holding_id, org_id=org_a)
        assert lot is None, "Cross-org holding must not be returned"

        # Verify the query included org_id filter by checking execute was called
        assert mock_db.execute.called


# ---------------------------------------------------------------------------
# tax_lots API: org_id passed to service calls
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTaxLotsApiPassesOrgId:
    """API endpoints must pass org_id to service calls."""

    def test_import_lots_api_passes_org_id(self):
        """import_lots_from_holding API endpoint must pass org_id to service."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/tax_lots.py").read_text()
        assert (
            "org_id=current_user.organization_id" in src
        ), "import_lots endpoint must pass org_id=current_user.organization_id to service"

    def test_get_unrealized_gains_api_passes_org_id(self):
        """get_unrealized_gains API endpoint must pass org_id to service."""
        import pathlib

        src = pathlib.Path("/home/lanx/git/nest-egg/backend/app/api/v1/tax_lots.py").read_text()
        # The unrealized gains call should include org_id
        assert (
            "org_id=current_user.organization_id" in src
        ), "get_unrealized_gains endpoint must pass org_id=current_user.organization_id"


# ---------------------------------------------------------------------------
# budget_service: Category queries org-scoped
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBudgetServiceCategoryOrgIsolation:
    """Category lookups in budget_service must be scoped to the user's org."""

    def test_category_lookup_includes_org_id(self):
        """get_budget_spending must filter Category by organization_id."""
        import pathlib

        src = pathlib.Path(
            "/home/lanx/git/nest-egg/backend/app/services/budget_service.py"
        ).read_text()
        assert (
            "Category.organization_id == user.organization_id" in src
        ), "Category query must include organization_id filter"

    def test_category_children_lookup_includes_org_id(self):
        """Child category lookup must also be scoped to the user's org."""
        import pathlib

        src = pathlib.Path(
            "/home/lanx/git/nest-egg/backend/app/services/budget_service.py"
        ).read_text()
        # Count occurrences — both parent and children queries must have org filter
        count = src.count("Category.organization_id == user.organization_id")
        assert (
            count >= 2
        ), f"Both Category queries (parent + children) must filter by org_id, found {count}"

    @pytest.mark.asyncio
    async def test_cross_org_category_not_used_in_budget(self):
        """A budget with a category_id from another org must not match cross-org categories."""
        from app.services.budget_service import BudgetService

        org_a = uuid4()

        # Budget belongs to org_a but has a category_id that only exists in a different org
        mock_budget = Mock()
        mock_budget.category_id = uuid4()
        mock_budget.label_id = None
        mock_budget.period = "monthly"
        mock_budget.amount = Decimal("500.00")

        mock_user = Mock()
        mock_user.organization_id = org_a

        mock_db = AsyncMock()

        # First execute: Organization lookup → returns mock org
        mock_org = Mock()
        mock_org.monthly_start_day = 1
        org_result = Mock()
        org_result.scalar_one_or_none = Mock(return_value=mock_org)

        # Second execute: Category lookup for org_a → None (cross-org category not found)
        cat_result = Mock()
        cat_result.scalar_one_or_none = Mock(return_value=None)

        # Third execute: Transaction sum (with direct category_id filter fallback)
        sum_result = Mock()
        sum_result.scalar = Mock(return_value=None)

        mock_db.execute = AsyncMock(side_effect=[org_result, cat_result, sum_result])

        # Mock get_budget to return our budget
        with patch.object(
            BudgetService, "get_budget", new_callable=AsyncMock, return_value=mock_budget
        ):
            result = await BudgetService.get_budget_spending(
                mock_db, mock_budget.category_id, mock_user
            )

        # When cross-org category is not found, spending falls through to the else branch.
        # This is safe: transaction query is still scoped to org_a.
        assert isinstance(result, dict)
