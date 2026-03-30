"""Unit tests for PE performance API — primarily the /portfolio route ordering fix.

The critical regression: FastAPI matches routes in definition order.
`GET /{account_id}` was defined before `GET /portfolio`, so requests to
/portfolio were parsed as account_id="portfolio", failing UUID validation
with a 422. The fix moves /portfolio before /{account_id} in the router.
"""

import pytest
from fastapi.routing import APIRoute

from app.api.v1.pe_performance import router


class TestPortfolioRouteOrdering:
    """Verify /portfolio is registered before /{account_id} in the router."""

    def _get_route_order(self):
        """Return list of (path, methods) in router registration order."""
        return [
            (route.path, route.methods)
            for route in router.routes
            if isinstance(route, APIRoute)
        ]

    def test_portfolio_route_exists(self):
        paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
        assert "/portfolio" in paths

    def test_account_id_route_exists(self):
        paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
        assert "/{account_id}" in paths

    def test_portfolio_registered_before_account_id(self):
        """
        /portfolio must come before /{account_id} so FastAPI doesn't try to
        parse the literal string "portfolio" as a UUID.
        """
        routes = self._get_route_order()
        portfolio_idx = next(
            i for i, (p, _) in enumerate(routes) if p == "/portfolio"
        )
        account_id_get_idx = next(
            i
            for i, (p, methods) in enumerate(routes)
            if p == "/{account_id}" and "GET" in (methods or set())
        )
        assert portfolio_idx < account_id_get_idx, (
            f"/portfolio is at index {portfolio_idx} but /{'{account_id}'} GET "
            f"is at index {account_id_get_idx}. "
            "FastAPI will match /portfolio as /{account_id} and fail UUID parsing."
        )

    def test_portfolio_is_get_method(self):
        routes = {
            route.path: route.methods
            for route in router.routes
            if isinstance(route, APIRoute)
        }
        assert "GET" in (routes.get("/portfolio") or set())

    def test_transactions_post_route_exists(self):
        paths = [r.path for r in router.routes if isinstance(r, APIRoute)]
        assert "/{account_id}/transactions" in paths


class TestPEMetricsResponseShape:
    """Verify PEMetricsResponse has the fields the frontend expects."""

    def test_response_model_fields(self):
        from app.api.v1.pe_performance import PEMetricsResponse

        fields = PEMetricsResponse.model_fields
        required = {
            "account_id", "account_name", "tvpi", "dpi", "moic",
            "total_called", "total_distributions", "current_nav",
            "net_profit", "irr", "irr_pct", "transactions",
        }
        for field in required:
            assert field in fields, f"PEMetricsResponse missing field: {field}"

    def test_no_rvpi_field(self):
        """Frontend was updated to use moic; rvpi should not be in the model."""
        from app.api.v1.pe_performance import PEMetricsResponse

        assert "rvpi" not in PEMetricsResponse.model_fields

    def test_portfolio_response_uses_name_not_account_name(self):
        """
        /portfolio returns plain dicts with key 'name' (not 'account_name').
        The frontend PeAccount interface uses 'name' — this documents the contract.
        """
        import inspect
        import app.api.v1.pe_performance as pe_mod

        source = inspect.getsource(pe_mod.get_pe_portfolio)
        assert '"name": account.name' in source or "'name': account.name" in source, (
            "get_pe_portfolio must use 'name' key (not 'account_name') to match frontend"
        )
