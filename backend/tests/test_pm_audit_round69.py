"""
PM Audit Round 69 — Rental Properties + AccountDetail + Nav visibility fixes.

Tests:
1. rental_property_service imports or_ and PropertyType
2. get_rental_properties filter includes property_type == INVESTMENT
3. _display_address uses rental_address first, falls back to property_address + property_zip
4. get_property_pnl uses _display_address
5. useNavDefaults hasRental detects property_type === 'investment'
6. AccountDetailPage seeds propertyAddress/Zip from account data
7. Tax Center marked as advanced in NAV_SECTIONS
8. ADVANCED_PATHS includes both /investment-tools and /tax-center
"""

import inspect
import re


# ── Backend: rental_property_service ────────────────────────────────────────

def test_rental_service_imports_property_type():
    from app.services.rental_property_service import RentalPropertyService
    from app.models.account import PropertyType
    src = inspect.getsource(RentalPropertyService)
    assert "PropertyType" in src


def test_rental_service_imports_or_():
    import app.services.rental_property_service as mod
    src = inspect.getsource(mod)
    assert "from sqlalchemy import or_" in src


def test_rental_service_get_rental_includes_investment_filter():
    from app.services.rental_property_service import RentalPropertyService
    src = inspect.getsource(RentalPropertyService.get_rental_properties)
    assert "PropertyType.INVESTMENT" in src
    assert "or_(" in src


def test_rental_service_display_address_method_exists():
    from app.services.rental_property_service import RentalPropertyService
    assert hasattr(RentalPropertyService, "_display_address")


def test_display_address_prefers_rental_address():
    from app.services.rental_property_service import RentalPropertyService
    from unittest.mock import MagicMock
    acct = MagicMock()
    acct.rental_address = "456 Oak Ave"
    acct.property_address = "123 Main St"
    acct.property_zip = "90210"
    result = RentalPropertyService._display_address(acct)
    assert result == "456 Oak Ave"


def test_display_address_falls_back_to_property_address():
    from app.services.rental_property_service import RentalPropertyService
    from unittest.mock import MagicMock
    acct = MagicMock()
    acct.rental_address = None
    acct.property_address = "123 Main St"
    acct.property_zip = "90210"
    result = RentalPropertyService._display_address(acct)
    assert "123 Main St" in result
    assert "90210" in result


def test_display_address_empty_when_no_address():
    from app.services.rental_property_service import RentalPropertyService
    from unittest.mock import MagicMock
    acct = MagicMock()
    acct.rental_address = None
    acct.property_address = None
    acct.property_zip = None
    result = RentalPropertyService._display_address(acct)
    assert result == ""


def test_get_property_pnl_uses_display_address():
    from app.services.rental_property_service import RentalPropertyService
    src = inspect.getsource(RentalPropertyService.get_property_pnl)
    assert "_display_address" in src


def test_get_rental_properties_uses_display_address():
    from app.services.rental_property_service import RentalPropertyService
    src = inspect.getsource(RentalPropertyService.get_rental_properties)
    assert "_display_address" in src


# ── Frontend (source inspection) ────────────────────────────────────────────

import os

FRONTEND = os.path.join(os.path.dirname(__file__), "../../frontend/src")


def _read(rel: str) -> str:
    return open(os.path.join(FRONTEND, rel), encoding="utf-8").read()


def test_account_detail_seeds_property_address():
    src = _read("pages/AccountDetailPage.tsx")
    assert "account.property_address" in src and "setPropertyAddress" in src


def test_account_detail_seeds_property_zip():
    src = _read("pages/AccountDetailPage.tsx")
    assert "account.property_zip" in src and "setPropertyZip" in src


def test_nav_defaults_tax_center_advanced():
    src = _read("hooks/useNavDefaults.ts")
    # Find the Tax Center block
    idx = src.index('"/tax-center"')
    block = src[idx - 30 : idx + 200]
    assert "advanced: true" in block


def test_nav_defaults_hasRental_checks_property_type():
    src = _read("hooks/useNavDefaults.ts")
    assert 'a.property_type === "investment"' in src


def test_nav_defaults_tax_center_not_in_buildConditionalDefaults():
    src = _read("hooks/useNavDefaults.ts")
    build_idx = src.index("buildConditionalDefaults")
    build_body = src[build_idx : build_idx + 1500]
    assert '"/tax-center"' not in build_body


def test_preferences_advanced_paths_includes_tax_center():
    src = _read("pages/PreferencesPage.tsx")
    adv_idx = src.index("ADVANCED_PATHS")
    block = src[adv_idx : adv_idx + 200]
    assert '"/tax-center"' in block


def test_layout_tax_center_is_advanced():
    src = _read("components/Layout.tsx")
    idx = src.index('path: "/tax-center"')
    block = src[idx - 20 : idx + 200]
    assert "advanced: true" in block


def test_layout_planning_tools_is_advanced():
    src = _read("components/Layout.tsx")
    idx = src.index('path: "/investment-tools"')
    block = src[idx - 20 : idx + 200]
    assert "advanced: true" in block


def test_layout_pe_performance_not_advanced():
    src = _read("components/Layout.tsx")
    idx = src.index('path: "/pe-performance"')
    end = src.index("}", idx)
    segment = src[idx:end]
    assert "advanced: true" not in segment


def test_layout_rental_properties_not_advanced():
    src = _read("components/Layout.tsx")
    idx = src.index('path: "/rental-properties"')
    end = src.index("}", idx)
    segment = src[idx:end]
    assert "advanced: true" not in segment
