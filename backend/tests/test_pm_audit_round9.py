"""Tests for PM audit round 9 fixes.

Covers:
- default_currency validated against SUPPORTED_CURRENCIES (rejects XYZ, 123, etc.)
- Dashboard layout validated: each widget must have id (str) and span (1|2), max 30 items
"""

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Currency validation
# ---------------------------------------------------------------------------


def test_supported_currencies_not_empty():
    """SUPPORTED_CURRENCIES must be a non-empty list of 3-char uppercase codes."""
    from app.services.fx_service import SUPPORTED_CURRENCIES

    assert len(SUPPORTED_CURRENCIES) > 0
    for code in SUPPORTED_CURRENCIES:
        assert len(code) == 3, f"Currency code '{code}' must be 3 characters"
        assert code.isupper(), f"Currency code '{code}' must be uppercase"


def test_usd_in_supported_currencies():
    from app.services.fx_service import SUPPORTED_CURRENCIES
    assert "USD" in SUPPORTED_CURRENCIES


def test_eur_in_supported_currencies():
    from app.services.fx_service import SUPPORTED_CURRENCIES
    assert "EUR" in SUPPORTED_CURRENCIES


def test_settings_imports_supported_currencies():
    """settings.py must import SUPPORTED_CURRENCIES for validation."""
    import inspect
    from app.api.v1 import settings as settings_module

    source = inspect.getsource(settings_module)
    assert "SUPPORTED_CURRENCIES" in source, (
        "settings.py must import and use SUPPORTED_CURRENCIES for currency validation"
    )


def test_settings_rejects_unsupported_currency_in_source():
    """Currency update code must reject currencies not in SUPPORTED_CURRENCIES."""
    import inspect
    from app.api.v1 import settings as settings_module

    source = inspect.getsource(settings_module)
    # Must contain the guard
    assert "not in SUPPORTED_CURRENCIES" in source, (
        "settings.py must check 'currency not in SUPPORTED_CURRENCIES'"
    )


# ---------------------------------------------------------------------------
# Dashboard layout validation
# ---------------------------------------------------------------------------


def test_dashboard_widget_valid():
    """A widget with id and span=1 or span=2 should parse cleanly."""
    from app.api.v1.settings import DashboardWidget

    w1 = DashboardWidget(id="net_worth", span=1)
    assert w1.id == "net_worth"
    assert w1.span == 1

    w2 = DashboardWidget(id="spending_chart", span=2)
    assert w2.span == 2


def test_dashboard_widget_rejects_span_3():
    """span=3 must raise a validation error."""
    from app.api.v1.settings import DashboardWidget

    with pytest.raises(ValidationError):
        DashboardWidget(id="net_worth", span=3)


def test_dashboard_widget_rejects_span_0():
    """span=0 must raise a validation error."""
    from app.api.v1.settings import DashboardWidget

    with pytest.raises(ValidationError):
        DashboardWidget(id="net_worth", span=0)


def test_dashboard_widget_rejects_empty_id():
    """Empty string id must raise a validation error."""
    from app.api.v1.settings import DashboardWidget

    with pytest.raises(ValidationError):
        DashboardWidget(id="", span=1)


def test_dashboard_widget_rejects_id_too_long():
    """id longer than 64 chars must raise a validation error."""
    from app.api.v1.settings import DashboardWidget

    with pytest.raises(ValidationError):
        DashboardWidget(id="x" * 65, span=1)


def test_dashboard_layout_update_valid():
    """A layout with valid widgets should parse cleanly."""
    from app.api.v1.settings import DashboardLayoutUpdate, DashboardWidget

    layout = DashboardLayoutUpdate(
        layout=[
            {"id": "net_worth", "span": 1},
            {"id": "spending_chart", "span": 2},
        ]
    )
    assert len(layout.layout) == 2


def test_dashboard_layout_update_rejects_too_many_widgets():
    """More than 30 widgets must raise a validation error."""
    from app.api.v1.settings import DashboardLayoutUpdate

    with pytest.raises(ValidationError):
        DashboardLayoutUpdate(
            layout=[{"id": f"widget_{i}", "span": 1} for i in range(31)]
        )


def test_dashboard_layout_update_allows_30_widgets():
    """Exactly 30 widgets must be accepted."""
    from app.api.v1.settings import DashboardLayoutUpdate

    layout = DashboardLayoutUpdate(
        layout=[{"id": f"widget_{i}", "span": 1} for i in range(30)]
    )
    assert len(layout.layout) == 30


def test_dashboard_layout_update_rejects_invalid_span():
    """A widget with span=5 inside a layout must raise a validation error."""
    from app.api.v1.settings import DashboardLayoutUpdate

    with pytest.raises(ValidationError):
        DashboardLayoutUpdate(
            layout=[{"id": "net_worth", "span": 5}]
        )


def test_dashboard_layout_update_rejects_missing_id():
    """A widget missing the id field must raise a validation error."""
    from app.api.v1.settings import DashboardLayoutUpdate

    with pytest.raises(ValidationError):
        DashboardLayoutUpdate(
            layout=[{"span": 1}]
        )


def test_dashboard_layout_update_rejects_missing_span():
    """A widget missing the span field must raise a validation error."""
    from app.api.v1.settings import DashboardLayoutUpdate

    with pytest.raises(ValidationError):
        DashboardLayoutUpdate(
            layout=[{"id": "net_worth"}]
        )
