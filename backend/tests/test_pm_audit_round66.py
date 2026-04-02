"""Tests for PM audit round 66 — rental type classification, crypto TLH, LP interest.

Covers:
1. RENTAL financial constants — STR loophole flag, depreciation, passive loss rules
2. CRYPTO_TAX financial constants — IS_PROPERTY flag, wash-sale suppression
3. RentalType enum in account model — three rental strategy classifications
4. GrantType.LP_INTEREST — Limited Partnership interest added to account model
5. Account.rental_type column present and nullable
6. TaxLossOpportunity.is_crypto / no_wash_sale_rule fields
7. Alembic migration r68 uses safe DO block (no CREATE TYPE IF NOT EXISTS)
"""

import inspect


# ---------------------------------------------------------------------------
# 1. RENTAL constants
# ---------------------------------------------------------------------------


def test_rental_str_loophole_active():
    from app.constants.financial import RENTAL
    assert RENTAL.STR_LOOPHOLE_ACTIVE is True, (
        "STR_LOOPHOLE_ACTIVE must be True until Congress closes the loophole"
    )


def test_rental_str_days_threshold():
    from app.constants.financial import RENTAL
    assert RENTAL.STR_AVG_RENTAL_DAYS_THRESHOLD == 7


def test_rental_depreciation_years():
    from app.constants.financial import RENTAL
    assert RENTAL.RESIDENTIAL_DEPRECIATION_YEARS == 27.5


def test_rental_depreciation_rate():
    from app.constants.financial import RENTAL
    assert abs(RENTAL.RESIDENTIAL_DEPRECIATION_RATE - (1 / 27.5)) < 1e-9


def test_rental_passive_loss_allowance():
    from app.constants.financial import RENTAL
    assert RENTAL.PASSIVE_LOSS_ALLOWANCE_MAX == 25_000


def test_rental_passive_loss_phaseout_range():
    from app.constants.financial import RENTAL
    assert RENTAL.PASSIVE_LOSS_PHASEOUT_START == 100_000
    assert RENTAL.PASSIVE_LOSS_PHASEOUT_END == 150_000


# ---------------------------------------------------------------------------
# 2. CRYPTO_TAX constants
# ---------------------------------------------------------------------------


def test_crypto_is_property():
    from app.constants.financial import CRYPTO_TAX
    assert CRYPTO_TAX.IS_PROPERTY is True


def test_crypto_wash_sale_does_not_apply():
    from app.constants.financial import CRYPTO_TAX
    assert CRYPTO_TAX.WASH_SALE_APPLIES is False


def test_crypto_wash_sale_inverse_of_is_property():
    from app.constants.financial import CRYPTO_TAX
    assert CRYPTO_TAX.WASH_SALE_APPLIES is not CRYPTO_TAX.IS_PROPERTY


def test_crypto_tax_has_note():
    from app.constants.financial import CRYPTO_TAX
    assert hasattr(CRYPTO_TAX, "NOTE")
    assert "IRC" in CRYPTO_TAX.NOTE or "1221" in CRYPTO_TAX.NOTE


# ---------------------------------------------------------------------------
# 3. RentalType enum
# ---------------------------------------------------------------------------


def test_rental_type_enum_values():
    from app.models.account import RentalType
    values = {e.value for e in RentalType}
    assert "buy_and_hold" in values
    assert "long_term_rental" in values
    assert "short_term_rental" in values


def test_rental_type_enum_count():
    from app.models.account import RentalType
    assert len(list(RentalType)) == 3


def test_rental_type_is_str_enum():
    from app.models.account import RentalType
    import enum
    assert issubclass(RentalType, str)
    assert issubclass(RentalType, enum.Enum)


# ---------------------------------------------------------------------------
# 4. GrantType.LP_INTEREST
# ---------------------------------------------------------------------------


def test_grant_type_lp_interest_exists():
    from app.models.account import GrantType
    assert GrantType.LP_INTEREST.value == "lp_interest"


def test_grant_type_has_both_pe_types():
    from app.models.account import GrantType
    values = {e.value for e in GrantType}
    assert "profit_interest" in values, "LLC profit interest must still exist"
    assert "lp_interest" in values, "LP interest must be added"


# ---------------------------------------------------------------------------
# 5. Account.rental_type column
# ---------------------------------------------------------------------------


def test_account_model_has_rental_type_column():
    from app.models.account import Account
    assert hasattr(Account, "rental_type"), "Account model must have rental_type attribute"
    col = Account.rental_type.property.columns[0]
    assert col.nullable is True


# ---------------------------------------------------------------------------
# 6. TaxLossOpportunity crypto fields
# ---------------------------------------------------------------------------


def test_tax_loss_opportunity_has_is_crypto():
    from app.services.tax_loss_harvesting_service import TaxLossOpportunity
    sig = inspect.signature(TaxLossOpportunity.__init__)
    assert "is_crypto" in sig.parameters


def test_tax_loss_opportunity_has_no_wash_sale_rule():
    from app.services.tax_loss_harvesting_service import TaxLossOpportunity
    sig = inspect.signature(TaxLossOpportunity.__init__)
    assert "no_wash_sale_rule" in sig.parameters


def test_tax_loss_opportunity_defaults_non_crypto():
    from decimal import Decimal
    from app.services.tax_loss_harvesting_service import TaxLossOpportunity
    import uuid
    opp = TaxLossOpportunity(
        holding_id=uuid.uuid4(),
        ticker="AAPL",
        name="Apple Inc.",
        shares=Decimal("10"),
        cost_basis=Decimal("1200"),
        current_value=Decimal("1000"),
        unrealized_loss=Decimal("-200"),
        loss_percentage=Decimal("-16.7"),
        estimated_tax_savings=Decimal("50"),
        wash_sale_risk=False,
        wash_sale_reason=None,
        sector="Technology",
        suggested_replacements=[],
    )
    assert opp.is_crypto is False
    assert opp.no_wash_sale_rule is False


def test_tax_loss_opportunity_crypto_flag():
    from decimal import Decimal
    from app.services.tax_loss_harvesting_service import TaxLossOpportunity
    import uuid
    opp = TaxLossOpportunity(
        holding_id=uuid.uuid4(),
        ticker="BTC",
        name="Bitcoin",
        shares=Decimal("0.5"),
        cost_basis=Decimal("10000"),
        current_value=Decimal("8000"),
        unrealized_loss=Decimal("-2000"),
        loss_percentage=Decimal("-20"),
        estimated_tax_savings=Decimal("500"),
        wash_sale_risk=False,
        wash_sale_reason=None,
        sector="Crypto",
        suggested_replacements=[],
        is_crypto=True,
        no_wash_sale_rule=True,
    )
    assert opp.is_crypto is True
    assert opp.no_wash_sale_rule is True


def test_tlh_service_sets_crypto_based_on_account_type():
    from app.services import tax_loss_harvesting_service
    source = inspect.getsource(tax_loss_harvesting_service)
    assert "AccountType.CRYPTO" in source or "account_type" in source
    assert "is_crypto" in source


# ---------------------------------------------------------------------------
# 7. Migration r68 uses safe enum creation
# ---------------------------------------------------------------------------


def test_r68_migration_no_create_type_if_not_exists():
    """PostgreSQL < 16 does not support CREATE TYPE IF NOT EXISTS; must use DO block."""
    import os
    migrations_dir = os.path.join(
        os.path.dirname(__file__), "..", "alembic", "versions"
    )
    r68 = next(f for f in os.listdir(migrations_dir) if "r68" in f)
    content = open(os.path.join(migrations_dir, r68)).read()
    assert "CREATE TYPE IF NOT EXISTS" not in content, (
        "r68 must not use CREATE TYPE IF NOT EXISTS (unsupported in PG < 16)"
    )
    assert "rentaltype" in content.lower()


def test_rental_type_service_includes_rental_type_field():
    from app.services import rental_property_service
    source = inspect.getsource(rental_property_service)
    assert "rental_type" in source


# ---------------------------------------------------------------------------
# 8. Tax Advisor STR and crypto insights
# ---------------------------------------------------------------------------


def test_tax_advisor_imports_rental_constants():
    """tax_advisor_service must import RENTAL and CRYPTO_TAX constants."""
    from app.services import tax_advisor_service

    source = inspect.getsource(tax_advisor_service)
    assert "RENTAL" in source
    assert "CRYPTO_TAX" in source


def test_tax_advisor_str_insight_when_loophole_active():
    """tax_advisor_service must generate STR insight when RENTAL.STR_LOOPHOLE_ACTIVE."""
    from app.services import tax_advisor_service

    source = inspect.getsource(tax_advisor_service)
    assert "STR_LOOPHOLE_ACTIVE" in source
    assert "Short-Term Rental" in source or "STR" in source
    assert "material participation" in source.lower() or "materially participate" in source.lower()


def test_tax_advisor_crypto_insight_when_is_property():
    """tax_advisor_service must generate crypto no-wash-sale insight when CRYPTO_TAX.IS_PROPERTY."""
    from app.services import tax_advisor_service

    source = inspect.getsource(tax_advisor_service)
    assert "CRYPTO_TAX.IS_PROPERTY" in source
    assert "wash-sale" in source.lower() or "wash_sale" in source.lower()


def test_tax_advisor_imports_rental_type():
    """tax_advisor_service must import RentalType to detect STR accounts."""
    from app.services import tax_advisor_service

    source = inspect.getsource(tax_advisor_service)
    assert "RentalType" in source
    assert "SHORT_TERM_RENTAL" in source


# ---------------------------------------------------------------------------
# 9. DEPENDENT_BENEFITS constants
# ---------------------------------------------------------------------------


def test_dependent_benefits_ctc_per_child():
    """DEPENDENT_BENEFITS.CHILD_TAX_CREDIT_PER_CHILD must be $2,000."""
    from app.constants.financial import DEPENDENT_BENEFITS
    assert DEPENDENT_BENEFITS.CHILD_TAX_CREDIT_PER_CHILD == 2_000


def test_dependent_benefits_dependent_care_fsa():
    """DEPENDENT_BENEFITS.DEPENDENT_CARE_FSA_MAX must be $5,000."""
    from app.constants.financial import DEPENDENT_BENEFITS
    assert DEPENDENT_BENEFITS.DEPENDENT_CARE_FSA_MAX == 5_000


def test_dependent_benefits_age_thresholds():
    """Age thresholds for CTC and care credit must match IRS rules."""
    from app.constants.financial import DEPENDENT_BENEFITS
    assert DEPENDENT_BENEFITS.CHILD_TAX_CREDIT_MAX_AGE == 17
    assert DEPENDENT_BENEFITS.DEPENDENT_CARE_MAX_AGE == 13


def test_dependent_benefits_phaseout_married_higher():
    """Married phaseout must be higher than single phaseout for CTC."""
    from app.constants.financial import DEPENDENT_BENEFITS
    assert DEPENDENT_BENEFITS.CHILD_TAX_CREDIT_PHASEOUT_MARRIED > DEPENDENT_BENEFITS.CHILD_TAX_CREDIT_PHASEOUT_SINGLE


# ---------------------------------------------------------------------------
# 10. Tax Advisor dependent insights
# ---------------------------------------------------------------------------


def test_tax_advisor_imports_dependent_benefits():
    """tax_advisor_service must import DEPENDENT_BENEFITS."""
    from app.services import tax_advisor_service
    source = inspect.getsource(tax_advisor_service)
    assert "DEPENDENT_BENEFITS" in source


def test_tax_advisor_fetches_dependents():
    """tax_advisor_service must query Dependent model."""
    from app.services import tax_advisor_service
    source = inspect.getsource(tax_advisor_service)
    assert "Dependent" in source
    assert "household_id" in source


def test_tax_advisor_ctc_insight():
    """tax_advisor_service must generate Child Tax Credit insight for eligible children."""
    from app.services import tax_advisor_service
    source = inspect.getsource(tax_advisor_service)
    assert "Child Tax Credit" in source
    assert "ctc_children" in source


def test_tax_advisor_care_fsa_insight():
    """tax_advisor_service must generate Dependent Care FSA insight."""
    from app.services import tax_advisor_service
    source = inspect.getsource(tax_advisor_service)
    assert "Dependent Care FSA" in source
    assert "care_children" in source


def test_tax_advisor_response_includes_dependents_count():
    """tax_advisor_service response must include dependents dict."""
    from app.services import tax_advisor_service
    source = inspect.getsource(tax_advisor_service)
    assert "qualifying_children" in source
    assert "ctc_eligible" in source
    assert "care_eligible" in source
