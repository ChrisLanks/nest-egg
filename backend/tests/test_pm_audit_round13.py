"""Tests for PM audit round 13 fixes.

Covers:
- Realized gains endpoint now passes account_id to service, preventing
  cross-member data exposure in multi-person households.
- get_realized_gains_summary service method now accepts optional account_id filter.
"""

import inspect
from uuid import UUID


def test_realized_gains_endpoint_passes_account_id():
    """The get_realized_gains endpoint must pass account_id to the service call."""
    from app.api.v1 import tax_lots as tax_lots_module

    source = inspect.getsource(tax_lots_module.get_realized_gains)
    assert "account_id=account_id" in source, (
        "get_realized_gains must pass account_id to get_realized_gains_summary"
    )


def test_realized_gains_service_accepts_account_id():
    """get_realized_gains_summary must accept an optional account_id parameter."""
    from app.services.tax_lot_service import TaxLotService

    import inspect
    sig = inspect.signature(TaxLotService.get_realized_gains_summary)
    assert "account_id" in sig.parameters, (
        "get_realized_gains_summary must have an account_id parameter"
    )
    param = sig.parameters["account_id"]
    assert param.default is None, "account_id must be optional (default None)"


def test_realized_gains_service_filters_by_account_when_provided():
    """When account_id is provided, the service source must filter TaxLot by it."""
    import inspect
    from app.services import tax_lot_service as svc_module

    source = inspect.getsource(svc_module.TaxLotService.get_realized_gains_summary)
    assert "TaxLot.account_id == account_id" in source, (
        "When account_id is not None, must add TaxLot.account_id == account_id filter"
    )
    assert "account_id is not None" in source, (
        "Must guard the account_id filter with 'if account_id is not None'"
    )


def test_realized_gains_endpoint_verifies_account_ownership():
    """The endpoint must verify the account belongs to the current user's org before querying."""
    from app.api.v1 import tax_lots as tax_lots_module

    source = inspect.getsource(tax_lots_module.get_realized_gains)
    # Must check org ownership
    assert "organization_id" in source
    assert "404" in source or "not found" in source.lower(), (
        "Must return 404 if account not found in org"
    )


def test_get_realized_gains_summary_signature():
    """Service signature: (self, db, org_id, tax_year, account_id=None)."""
    from app.services.tax_lot_service import TaxLotService
    import inspect

    sig = inspect.signature(TaxLotService.get_realized_gains_summary)
    params = list(sig.parameters.keys())
    assert "org_id" in params
    assert "tax_year" in params
    assert "account_id" in params


def test_unrealized_gains_service_already_has_account_id():
    """Sanity: unrealized gains service already scoped by account_id (not a regression)."""
    from app.services.tax_lot_service import TaxLotService
    import inspect

    sig = inspect.signature(TaxLotService.get_unrealized_gains)
    assert "account_id" in sig.parameters, (
        "get_unrealized_gains must also have account_id (already scoped correctly)"
    )
