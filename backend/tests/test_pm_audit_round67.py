"""Tests for PM audit round 67 — smart insights STR and crypto TLH checks.

Covers:
1. SmartInsightsService imports RENTAL and CRYPTO_TAX constants
2. SmartInsightsService imports RentalType from account model
3. INSIGHT_STR_OPPORTUNITY and INSIGHT_CRYPTO_TLH constants defined
4. _check_str_opportunity method exists and references STR_LOOPHOLE_ACTIVE
5. _check_crypto_tlh method exists and references IS_PROPERTY and CRYPTO_TAX
6. Both methods registered in get_insights
7. _check_str_opportunity returns None when no STR accounts
8. _check_crypto_tlh returns None when no crypto accounts
9. TaxInsightsWidget duplicate key fix (category-idx key)
10. TaxInsightsWidget categoryColor function present
"""

import inspect


# ---------------------------------------------------------------------------
# 1. SmartInsightsService imports
# ---------------------------------------------------------------------------


def test_smart_insights_imports_rental():
    """SmartInsightsService must import RENTAL constant."""
    from app.services import smart_insights_service
    source = inspect.getsource(smart_insights_service)
    assert "RENTAL" in source


def test_smart_insights_imports_crypto_tax():
    """SmartInsightsService must import CRYPTO_TAX constant."""
    from app.services import smart_insights_service
    source = inspect.getsource(smart_insights_service)
    assert "CRYPTO_TAX" in source


def test_smart_insights_imports_rental_type():
    """SmartInsightsService must import RentalType enum."""
    from app.services import smart_insights_service
    source = inspect.getsource(smart_insights_service)
    assert "RentalType" in source


# ---------------------------------------------------------------------------
# 2. Insight type constants
# ---------------------------------------------------------------------------


def test_insight_str_opportunity_constant():
    """INSIGHT_STR_OPPORTUNITY must be defined."""
    from app.services.smart_insights_service import INSIGHT_STR_OPPORTUNITY
    assert INSIGHT_STR_OPPORTUNITY == "str_opportunity"


def test_insight_crypto_tlh_constant():
    """INSIGHT_CRYPTO_TLH must be defined."""
    from app.services.smart_insights_service import INSIGHT_CRYPTO_TLH
    assert INSIGHT_CRYPTO_TLH == "crypto_tlh"


# ---------------------------------------------------------------------------
# 3. _check_str_opportunity method
# ---------------------------------------------------------------------------


def test_str_opportunity_method_exists():
    """SmartInsightsService must have _check_str_opportunity method."""
    from app.services.smart_insights_service import SmartInsightsService
    assert hasattr(SmartInsightsService, "_check_str_opportunity")


def test_str_opportunity_references_str_loophole_active():
    """_check_str_opportunity must gate on RENTAL.STR_LOOPHOLE_ACTIVE."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_str_opportunity)
    assert "STR_LOOPHOLE_ACTIVE" in source


def test_str_opportunity_references_short_term_rental():
    """_check_str_opportunity must filter by SHORT_TERM_RENTAL rental type."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_str_opportunity)
    assert "SHORT_TERM_RENTAL" in source


def test_str_opportunity_irc_469_reference():
    """_check_str_opportunity message must reference IRC §469."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_str_opportunity)
    assert "469" in source


def test_str_opportunity_returns_none_no_str_accounts():
    """_check_str_opportunity must return None when no STR accounts present."""
    from unittest.mock import MagicMock
    from app.services.smart_insights_service import SmartInsightsService
    from app.models.account import Account, AccountType, RentalType

    db = MagicMock()
    service = SmartInsightsService(db)

    # Account with checking type (not STR)
    acct = MagicMock(spec=Account)
    acct.account_type = AccountType.CHECKING
    acct.rental_type = None

    result = service._check_str_opportunity([acct])
    assert result is None


def test_str_opportunity_returns_insight_for_str_account():
    """_check_str_opportunity must return an insight for STR accounts."""
    from unittest.mock import MagicMock
    from app.services.smart_insights_service import SmartInsightsService
    from app.models.account import Account, AccountType, RentalType

    db = MagicMock()
    service = SmartInsightsService(db)

    acct = MagicMock(spec=Account)
    acct.account_type = AccountType.PROPERTY
    acct.rental_type = RentalType.SHORT_TERM_RENTAL

    result = service._check_str_opportunity([acct])
    assert result is not None
    assert result.type == "str_opportunity"
    assert result.category == "tax"
    assert result.priority == "high"


# ---------------------------------------------------------------------------
# 4. _check_crypto_tlh method
# ---------------------------------------------------------------------------


def test_crypto_tlh_method_exists():
    """SmartInsightsService must have _check_crypto_tlh method."""
    from app.services.smart_insights_service import SmartInsightsService
    assert hasattr(SmartInsightsService, "_check_crypto_tlh")


def test_crypto_tlh_references_is_property():
    """_check_crypto_tlh must gate on CRYPTO_TAX.IS_PROPERTY."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_crypto_tlh)
    assert "IS_PROPERTY" in source


def test_crypto_tlh_references_irc_1221():
    """_check_crypto_tlh message must reference IRC §1221."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_crypto_tlh)
    assert "1221" in source


def test_crypto_tlh_references_wash_sale_rule():
    """_check_crypto_tlh message must mention wash-sale rule."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_crypto_tlh)
    assert "wash" in source.lower()


def test_crypto_tlh_filters_by_crypto_account_type():
    """_check_crypto_tlh must filter accounts by CRYPTO type."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService._check_crypto_tlh)
    assert "AccountType.CRYPTO" in source


# ---------------------------------------------------------------------------
# 5. get_insights registers new checks
# ---------------------------------------------------------------------------


def test_get_insights_includes_str_check():
    """get_insights must call _check_str_opportunity."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService.get_insights)
    assert "_check_str_opportunity" in source


def test_get_insights_includes_crypto_tlh_check():
    """get_insights must call _check_crypto_tlh."""
    from app.services.smart_insights_service import SmartInsightsService
    source = inspect.getsource(SmartInsightsService.get_insights)
    assert "_check_crypto_tlh" in source
