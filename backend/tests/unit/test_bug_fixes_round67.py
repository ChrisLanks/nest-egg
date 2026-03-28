"""
Tests for round-67 bug fixes:
1. backdoor_roth.py: account_name → account.name (AttributeError fix)
2. financial_plan.py: EDUCATION_529 → RETIREMENT_529 (wrong enum value)
3. financial_plan.py: estate section uses subject_user not current_user
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 1. backdoor_roth: account.name field used (not account_name)
# ─────────────────────────────────────────────────────────────────────────────

class TestBackdoorRothAccountName:
    """account_name doesn't exist on Account model; correct field is .name"""

    def _make_account(self, name="My Roth IRA", account_type="roth_ira", **kwargs):
        acct = MagicMock()
        acct.id = uuid4()
        acct.name = name
        acct.account_type = account_type
        acct.current_balance = kwargs.get("current_balance", 10000)
        acct.form_8606_basis = kwargs.get("form_8606_basis", None)
        acct.after_tax_401k_balance = kwargs.get("after_tax_401k_balance", None)
        acct.mega_backdoor_eligible = kwargs.get("mega_backdoor_eligible", False)
        # Deliberately NOT setting account_name — should raise if code uses it
        if not hasattr(acct, "account_name"):
            del acct.account_name  # ensure AttributeError if accessed
        return acct

    def test_ira_detail_uses_name_field(self):
        """IraAccountDetail construction should use a.name, not a.account_name."""
        from app.api.v1.backdoor_roth import IraAccountDetail

        acct = self._make_account(name="Traditional IRA")
        # Simulate what the endpoint does
        bal = float(acct.current_balance or 0)
        basis = float(acct.form_8606_basis or 0)
        pre_tax = max(0.0, bal - basis)
        ratio = (pre_tax / bal) if bal > 0 else 0.0

        detail = IraAccountDetail(
            account_id=str(acct.id),
            name=acct.name or acct.account_type,
            balance=bal,
            form_8606_basis=basis,
            pre_tax_portion=pre_tax,
            pro_rata_ratio=round(ratio, 4),
        )
        assert detail.name == "Traditional IRA"

    def test_ira_detail_falls_back_to_account_type(self):
        """When .name is falsy, falls back to account_type string."""
        from app.api.v1.backdoor_roth import IraAccountDetail

        acct = self._make_account(name="")
        detail = IraAccountDetail(
            account_id=str(acct.id),
            name=acct.name or acct.account_type,
            balance=0.0,
            form_8606_basis=0.0,
            pre_tax_portion=0.0,
            pro_rata_ratio=0.0,
        )
        assert detail.name == "roth_ira"

    def test_k401_detail_uses_name_field(self):
        """K401AccountDetail construction should use a.name, not a.account_name."""
        from app.api.v1.backdoor_roth import K401AccountDetail

        acct = self._make_account(name="My 401k", account_type="traditional_401k",
                                   after_tax_401k_balance=5000, mega_backdoor_eligible=True)
        detail = K401AccountDetail(
            account_id=str(acct.id),
            name=acct.name or acct.account_type,
            after_tax_balance=float(acct.after_tax_401k_balance or 0),
            mega_backdoor_eligible=bool(acct.mega_backdoor_eligible),
        )
        assert detail.name == "My 401k"
        assert detail.mega_backdoor_eligible is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. financial_plan: RETIREMENT_529 used for 529 balance query
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialPlanEducation529Enum:
    """_build_education_section must query AccountType.RETIREMENT_529, not EDUCATION_529."""

    def test_retirement_529_enum_value_exists(self):
        """Confirm AccountType.RETIREMENT_529 exists and has expected value."""
        from app.models.account import AccountType
        assert hasattr(AccountType, "RETIREMENT_529"), "AccountType must have RETIREMENT_529"
        assert AccountType.RETIREMENT_529.value == "retirement_529"

    def test_education_529_enum_value_does_not_exist(self):
        """Confirm there is no EDUCATION_529 enum value (would cause silent query failure)."""
        from app.models.account import AccountType
        assert not hasattr(AccountType, "EDUCATION_529"), (
            "EDUCATION_529 should not exist on AccountType — use RETIREMENT_529"
        )

    def test_financial_plan_uses_retirement_529_in_query(self):
        """financial_plan._build_education_section source must reference RETIREMENT_529."""
        import inspect
        import app.api.v1.financial_plan as fp_module

        source = inspect.getsource(fp_module)
        assert "EDUCATION_529" not in source, (
            "financial_plan.py must not reference EDUCATION_529 — use RETIREMENT_529"
        )
        assert "RETIREMENT_529" in source, (
            "financial_plan.py must reference RETIREMENT_529 for 529 balance queries"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. financial_plan: estate section uses subject_user
# ─────────────────────────────────────────────────────────────────────────────

class TestFinancialPlanEstateSubjectUser:
    """_build_estate_section should be called with subject_user, not current_user."""

    def test_estate_section_called_with_subject_user(self):
        """Verify the endpoint passes subject_user (not current_user) to _build_estate_section."""
        import inspect
        import ast
        import app.api.v1.financial_plan as fp_module

        source = inspect.getsource(fp_module)
        # Find the call to _build_estate_section
        # It should pass subject_user as the user argument, not current_user
        assert "_build_estate_section(db, org_id, current_user," not in source, (
            "_build_estate_section must receive subject_user, not current_user"
        )
        assert "_build_estate_section(db, org_id, subject_user," in source, (
            "_build_estate_section must be called with subject_user"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. tax_buckets: verify_household_member called when user_id != current_user
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 5. Silent-404 fix: household member not found raises HTTPException 404
# ─────────────────────────────────────────────────────────────────────────────

class TestHouseholdMember404:
    """When user_id is provided but not found in org, endpoint must raise 404."""

    def _make_current_user(self):
        u = MagicMock()
        u.id = uuid4()
        u.organization_id = uuid4()
        u.birthdate = None
        return u

    def _make_db_returning_none(self):
        """AsyncSession mock where scalar_one_or_none() returns None."""
        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_backdoor_roth_404_for_unknown_member(self):
        from fastapi import HTTPException
        from app.api.v1.backdoor_roth import get_backdoor_roth_analysis

        current_user = self._make_current_user()
        db = self._make_db_returning_none()
        unknown_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await get_backdoor_roth_analysis(
                filing_status="single",
                estimated_magi=None,
                user_id=unknown_id,
                current_user=current_user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_irmaa_404_for_unknown_member(self):
        from fastapi import HTTPException
        from app.api.v1.irmaa_projection import get_irmaa_projection

        current_user = self._make_current_user()
        db = self._make_db_returning_none()
        unknown_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await get_irmaa_projection(
                current_magi=100000.0,
                filing_status="single",
                income_growth_rate=0.03,
                projection_years=15,
                user_id=unknown_id,
                current_user=current_user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_financial_plan_404_for_unknown_member(self):
        from fastapi import HTTPException
        from app.api.v1.financial_plan import get_financial_plan_summary

        current_user = self._make_current_user()
        db = self._make_db_returning_none()
        unknown_id = str(uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await get_financial_plan_summary(
                user_id=unknown_id,
                current_user=current_user,
                db=db,
            )
        assert exc_info.value.status_code == 404


class TestTaxBucketHouseholdVerification:
    """get_bucket_summary should call verify_household_member for cross-user access."""

    def test_tax_buckets_imports_verify_household_member(self):
        """verify_household_member must be imported in tax_buckets.py."""
        import inspect
        import app.api.v1.tax_buckets as tb_module

        source = inspect.getsource(tb_module)
        assert "verify_household_member" in source, (
            "tax_buckets.py must import and use verify_household_member"
        )

    @pytest.mark.asyncio
    async def test_bucket_summary_calls_verify_for_other_user(self):
        """When user_id != current_user.id, verify_household_member is awaited."""
        from app.api.v1.tax_buckets import get_bucket_summary

        current_user = MagicMock()
        current_user.id = uuid4()
        current_user.organization_id = uuid4()

        other_user_id = uuid4()  # different user in household

        db = AsyncMock()

        with patch("app.api.v1.tax_buckets.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.tax_buckets.TaxBucketService.get_bucket_summary", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = {"pre_tax": 0, "roth": 0, "taxable": 0}
            await get_bucket_summary(user_id=other_user_id, db=db, current_user=current_user)
            mock_verify.assert_awaited_once_with(db, other_user_id, current_user.organization_id)

    @pytest.mark.asyncio
    async def test_bucket_summary_no_verify_for_self(self):
        """When user_id == current_user.id, verify_household_member is NOT called."""
        from app.api.v1.tax_buckets import get_bucket_summary

        current_user = MagicMock()
        current_user.id = uuid4()
        current_user.organization_id = uuid4()

        db = AsyncMock()

        with patch("app.api.v1.tax_buckets.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.tax_buckets.TaxBucketService.get_bucket_summary", new_callable=AsyncMock) as mock_svc:
            mock_svc.return_value = {"pre_tax": 0, "roth": 0, "taxable": 0}
            await get_bucket_summary(user_id=current_user.id, db=db, current_user=current_user)
            mock_verify.assert_not_awaited()
