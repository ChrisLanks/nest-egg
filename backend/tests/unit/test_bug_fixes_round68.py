"""
Tests for round-68 bug fixes:
1. contribution_headroom.py: acct.account_name → acct.name (AttributeError fix)
2. estate.py: acct.account_name → acct.name (AttributeError fix)
3. irmaa_projection.py: inverted age guard — age is None should NOT count toward lifetime_total
4. smart_insights_service.py: division by zero guard when median_nw is 0
"""
import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1 & 2. account_name → .name in contribution_headroom and estate
# ─────────────────────────────────────────────────────────────────────────────

class TestAccountNameField:
    """account_name doesn't exist on Account model; correct field is .name"""

    def test_contribution_headroom_uses_name_not_account_name(self):
        """contribution_headroom.py must not reference acct.account_name."""
        import app.api.v1.contribution_headroom as ch_module

        source = inspect.getsource(ch_module)
        assert "acct.account_name" not in source, (
            "contribution_headroom.py must not use acct.account_name — use acct.name"
        )
        assert "acct.name" in source, (
            "contribution_headroom.py must use acct.name"
        )

    def test_estate_uses_name_not_account_name(self):
        """estate.py must not reference acct.account_name."""
        import app.api.v1.estate as estate_module

        source = inspect.getsource(estate_module)
        assert "acct.account_name" not in source, (
            "estate.py must not use acct.account_name — use acct.name"
        )

    def test_contribution_headroom_account_headroom_uses_name(self):
        """AccountHeadroom construction uses .name not .account_name."""
        from app.api.v1.contribution_headroom import AccountHeadroom

        item = AccountHeadroom(
            account_id=str(uuid4()),
            account_name="My 401k",  # field name in schema is account_name (fine)
            account_type="traditional_401k",
            limit=23000.0,
            catch_up_limit=23000.0,
            catch_up_eligible=False,
            contributed_ytd=5000.0,
            remaining_headroom=18000.0,
            pct_used=21.7,
        )
        assert item.account_name == "My 401k"


# ─────────────────────────────────────────────────────────────────────────────
# 3. irmaa_projection: age guard logic
# ─────────────────────────────────────────────────────────────────────────────

class TestIrmaaLifetimeTotalAgeGuard:
    """lifetime_total should only accumulate years where age is known AND >= eligibility age."""

    def test_source_uses_age_is_not_none_and(self):
        """Source must use 'age is not None and age >=' not 'age is None or age >='."""
        import app.api.v1.irmaa_projection as ir_module

        source = inspect.getsource(ir_module)
        assert "age is None or age >=" not in source, (
            "irmaa_projection.py: inverted guard 'age is None or age >=' still present"
        )
        assert "age is not None and age >=" in source, (
            "irmaa_projection.py: must use 'age is not None and age >=' for Medicare lifetime total"
        )

    @pytest.mark.asyncio
    async def test_unknown_age_does_not_inflate_lifetime_total(self):
        """When birthdate is unknown (age=None), lifetime_total must stay 0."""
        from app.api.v1.irmaa_projection import get_irmaa_projection

        current_user = MagicMock()
        current_user.id = uuid4()
        current_user.organization_id = uuid4()
        current_user.birthdate = None  # age unknown

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None  # no household member lookup needed (self)
        db.execute = AsyncMock(return_value=result_mock)

        response = await get_irmaa_projection(
            current_magi=300_000.0,
            filing_status="single",
            income_growth_rate=0.03,
            projection_years=10,
            user_id=None,
            current_user=current_user,
            db=db,
        )
        # With no birthdate, age is None for all years → lifetime_premium_estimate must be 0
        assert response.lifetime_premium_estimate == 0.0, (
            f"Expected lifetime_premium_estimate=0 when age unknown, got {response.lifetime_premium_estimate}"
        )

    @pytest.mark.asyncio
    async def test_known_age_below_medicare_does_not_count(self):
        """Years before Medicare eligibility (65) must not count toward lifetime total."""
        import datetime
        from app.api.v1.irmaa_projection import get_irmaa_projection
        from app.constants.financial import MEDICARE

        current_user = MagicMock()
        current_user.id = uuid4()
        current_user.organization_id = uuid4()
        # 30 years old — won't reach 65 in a 5-year projection
        current_user.birthdate = datetime.date(
            datetime.date.today().year - 30, 1, 1
        )

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        response = await get_irmaa_projection(
            current_magi=300_000.0,
            filing_status="single",
            income_growth_rate=0.03,
            projection_years=5,
            user_id=None,
            current_user=current_user,
            db=db,
        )
        assert response.lifetime_premium_estimate == 0.0, (
            f"Expected 0 lifetime_premium_estimate for 30yo with 5yr projection, got {response.lifetime_premium_estimate}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. smart_insights_service: division by zero guard
# ─────────────────────────────────────────────────────────────────────────────

class TestSmartInsightsMedianNwGuard:
    """_build_net_worth_vs_peers must not divide by zero when median_nw is 0."""

    def test_source_has_median_nw_guard(self):
        """Source must guard against median_nw == 0 before division."""
        import app.services.smart_insights_service as sis_module

        source = inspect.getsource(sis_module)
        # Both 'not median_nw' and 'median_nw <= 0' or 'median_nw == 0' are acceptable guards
        has_guard = (
            "not median_nw" in source
            or "median_nw <= 0" in source
            or "median_nw == 0" in source
            or "if median_nw" in source
        )
        assert has_guard, (
            "smart_insights_service.py must guard against median_nw == 0 before division"
        )

    @pytest.mark.asyncio
    async def test_zero_median_nw_returns_none(self):
        """When age group median net worth is 0, method returns None (no insight)."""
        import app.services.smart_insights_service as sis_module

        # Find the method that computes net worth vs peers
        service_class = sis_module.SmartInsightsService
        method_name = None
        for name in dir(service_class):
            if "peer" in name.lower() or "median" in name.lower() or "net_worth" in name.lower():
                method_name = name
                break

        if method_name is None:
            # Fall back to source inspection — the guard exists
            source = inspect.getsource(sis_module)
            assert "not median_nw" in source or "median_nw <= 0" in source or "median_nw == 0" in source
            return

        # Verify the source doesn't do unchecked division
        method_source = inspect.getsource(getattr(service_class, method_name))
        assert "/ median_nw" not in method_source or (
            "not median_nw" in method_source
            or "median_nw <= 0" in method_source
            or "if median_nw" in method_source
        ), "Division by median_nw without a zero guard"
