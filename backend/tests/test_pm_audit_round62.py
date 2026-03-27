"""Tests for PM audit round 62 — CASH account type, ESPP, dependents, insurance,
TLH ledger, FRED treasury rates, SSA import, 529 grouping fix, Trump Account alias.
"""

import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---------------------------------------------------------------------------
# 1. CASH account type exists and is classified as asset
# ---------------------------------------------------------------------------


class TestCashAccountType:
    def test_cash_in_enum(self):
        from app.models.account import AccountType
        assert hasattr(AccountType, "CASH")
        assert AccountType.CASH.value == "cash"

    def test_cash_is_asset(self):
        from app.models.account import AccountType
        assert AccountType.CASH.is_asset is True
        assert AccountType.CASH.is_debt is False

    def test_cash_in_net_worth_service_map(self):
        from app.services.net_worth_service import _ASSET_CATEGORY_MAP
        from app.models.account import AccountType
        assert AccountType.CASH in _ASSET_CATEGORY_MAP
        assert _ASSET_CATEGORY_MAP[AccountType.CASH] == "cash_and_checking"


# ---------------------------------------------------------------------------
# 2. 529 is no longer in "Retirement" group (check accountTypeGroups.ts)
# ---------------------------------------------------------------------------


class TestFrontend529Grouping:
    def test_529_not_in_retirement_group(self):
        """Read accountTypeGroups.ts and verify RETIREMENT_529 is not in Retirement."""
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "accountTypeGroups.ts"
        content = ts_path.read_text()
        # The old line would be: [AccountType.RETIREMENT_529]: { label: "Retirement"
        # New line should be: [AccountType.RETIREMENT_529]: { label: "Education"
        assert 'RETIREMENT_529]: { label: "Retirement"' not in content
        assert 'RETIREMENT_529]: { label: "Education"' in content


# ---------------------------------------------------------------------------
# 3. TRUMP_ACCOUNT display label contains "Minor's IRA"
# ---------------------------------------------------------------------------


class TestTrumpAccountAlias:
    def test_trump_account_display_label(self):
        """Read formatAccountType.ts and verify trump_account maps to Minor's IRA."""
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utils" / "formatAccountType.ts"
        content = ts_path.read_text()
        assert "Minor's IRA (Trump Account)" in content


# ---------------------------------------------------------------------------
# 4. ESPP account type and constants exist
# ---------------------------------------------------------------------------


class TestESPP:
    def test_espp_in_enum(self):
        from app.models.account import AccountType
        assert hasattr(AccountType, "ESPP")
        assert AccountType.ESPP.value == "espp"

    def test_espp_is_asset(self):
        from app.models.account import AccountType
        assert AccountType.ESPP.is_asset is True

    def test_espp_constants(self):
        from app.constants.financial import ESPP
        assert ESPP.MAX_DISCOUNT_RATE == Decimal("0.15")
        assert ESPP.ANNUAL_PURCHASE_LIMIT == 25_000

    def test_espp_service_ordinary_income(self):
        from app.services.espp_service import espp_service
        result = espp_service.calculate_ordinary_income(
            purchase_price=Decimal("85.00"),
            fmv_at_purchase=Decimal("100.00"),
            shares=Decimal("100"),
        )
        assert result == Decimal("1500.00")

    def test_espp_service_qualifying_gain(self):
        from app.services.espp_service import espp_service
        result = espp_service.calculate_qualifying_gain(
            purchase_price=Decimal("85.00"),
            fmv_at_sale=Decimal("120.00"),
            shares=Decimal("100"),
        )
        assert result == Decimal("3500.00")

    def test_espp_service_disqualifying_gain(self):
        from app.services.espp_service import espp_service
        result = espp_service.calculate_disqualifying_gain(
            fmv_at_purchase=Decimal("100.00"),
            fmv_at_sale=Decimal("120.00"),
            shares=Decimal("100"),
        )
        assert result == Decimal("2000.00")

    def test_espp_in_net_worth_map(self):
        from app.services.net_worth_service import _ASSET_CATEGORY_MAP
        from app.models.account import AccountType
        assert AccountType.ESPP in _ASSET_CATEGORY_MAP
        assert _ASSET_CATEGORY_MAP[AccountType.ESPP] == "investments"


# ---------------------------------------------------------------------------
# 5. Insurance policy model and CRUD
# ---------------------------------------------------------------------------


class TestInsurancePolicyModel:
    def test_policy_type_enum(self):
        from app.models.insurance_policy import PolicyType
        assert hasattr(PolicyType, "TERM_LIFE")
        assert hasattr(PolicyType, "UMBRELLA")
        assert hasattr(PolicyType, "LONG_TERM_CARE")
        assert PolicyType.TERM_LIFE.value == "term_life"

    def test_insurance_policy_model_fields(self):
        from app.models.insurance_policy import InsurancePolicy
        assert hasattr(InsurancePolicy, "household_id")
        assert hasattr(InsurancePolicy, "policy_type")
        assert hasattr(InsurancePolicy, "coverage_amount")
        assert hasattr(InsurancePolicy, "annual_premium")
        assert hasattr(InsurancePolicy, "deductible")
        assert hasattr(InsurancePolicy, "beneficiary_name")


# ---------------------------------------------------------------------------
# 6. Dependent model and CRUD
# ---------------------------------------------------------------------------


class TestDependentModel:
    def test_dependent_model_fields(self):
        from app.models.dependent import Dependent
        assert hasattr(Dependent, "household_id")
        assert hasattr(Dependent, "first_name")
        assert hasattr(Dependent, "date_of_birth")
        assert hasattr(Dependent, "relationship")
        assert hasattr(Dependent, "expected_college_start_year")
        assert hasattr(Dependent, "expected_college_cost_annual")


# ---------------------------------------------------------------------------
# 7. TLH wash sale window calculation
# ---------------------------------------------------------------------------


class TestTLHWashSale:
    def test_harvest_status_enum(self):
        from app.models.tax_loss_harvest import HarvestStatus
        assert HarvestStatus.ACTIVE_WINDOW.value == "active_window"
        assert HarvestStatus.WINDOW_CLOSED.value == "window_closed"
        assert HarvestStatus.WASH_SALE_TRIGGERED.value == "wash_sale_triggered"

    def test_wash_sale_window_is_30_days(self):
        from app.api.v1.tax_loss_harvest_ledger import WASH_SALE_WINDOW_DAYS
        assert WASH_SALE_WINDOW_DAYS == 30

    def test_harvest_record_model_fields(self):
        from app.models.tax_loss_harvest import TaxLossHarvestRecord
        assert hasattr(TaxLossHarvestRecord, "date_harvested")
        assert hasattr(TaxLossHarvestRecord, "ticker_sold")
        assert hasattr(TaxLossHarvestRecord, "loss_amount")
        assert hasattr(TaxLossHarvestRecord, "wash_sale_window_end")
        assert hasattr(TaxLossHarvestRecord, "status")
        assert hasattr(TaxLossHarvestRecord, "replacement_ticker")


# ---------------------------------------------------------------------------
# 8. FRED treasury rate endpoint structure
# ---------------------------------------------------------------------------


class TestTreasuryRates:
    def test_treasury_series_defined(self):
        from app.api.v1.treasury_rates import TREASURY_SERIES
        assert "1_month" in TREASURY_SERIES
        assert "10_year" in TREASURY_SERIES
        assert "30_year" in TREASURY_SERIES
        assert TREASURY_SERIES["10_year"] == "DGS10"

    def test_treasury_response_model(self):
        from app.api.v1.treasury_rates import TreasuryRateResponse
        resp = TreasuryRateResponse(
            rates={"1_year": 0.0425, "10_year": 0.0385},
            as_of_date="2026-03-27",
        )
        assert resp.rates["1_year"] == 0.0425
        assert resp.source == "FRED / U.S. Treasury"


# ---------------------------------------------------------------------------
# 9. SSA manual benefit import endpoint structure
# ---------------------------------------------------------------------------


class TestSSABenefitImport:
    def test_ss_benefit_estimate_model(self):
        from app.models.ss_benefit_estimate import SSBenefitEstimate
        assert hasattr(SSBenefitEstimate, "user_id")
        assert hasattr(SSBenefitEstimate, "age_62_benefit")
        assert hasattr(SSBenefitEstimate, "age_67_benefit")
        assert hasattr(SSBenefitEstimate, "age_70_benefit")
        assert hasattr(SSBenefitEstimate, "as_of_year")

    def test_ss_benefit_input_schema(self):
        from app.api.v1.social_security import SSBenefitInput
        body = SSBenefitInput(
            age_62_benefit=Decimal("1800"),
            age_67_benefit=Decimal("2400"),
            age_70_benefit=Decimal("3100"),
            as_of_year=2026,
        )
        assert body.age_62_benefit == Decimal("1800")
        assert body.as_of_year == 2026


# ---------------------------------------------------------------------------
# 10. Help content entries exist
# ---------------------------------------------------------------------------


class TestHelpContent:
    def test_help_content_file_has_education(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "education:" in content
        assert "529" in content

    def test_help_content_file_has_insurance(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "insurance:" in content

    def test_help_content_file_has_equity_compensation(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "equityCompensation:" in content
        assert "espp:" in content

    def test_help_content_file_has_estate(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "estate:" in content

    def test_help_content_file_has_charitable(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "charitableGiving:" in content

    def test_help_content_file_has_loan_modeler(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "helpContent.ts"
        content = ts_path.read_text()
        assert "loanModeler:" in content


# ---------------------------------------------------------------------------
# 11. Nav structure doc exists
# ---------------------------------------------------------------------------


class TestNavStructure:
    def test_nav_structure_file_exists(self):
        path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "navStructure.md"
        assert path.exists()

    def test_nav_structure_has_tax_center(self):
        path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "navStructure.md"
        content = path.read_text()
        assert "Tax Center" in content
        assert "Life Planning" in content


# ---------------------------------------------------------------------------
# 12. show_locked_nav support in useNavDefaults
# ---------------------------------------------------------------------------


class TestShowLockedNav:
    def test_nav_defaults_has_locked_nav_support(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "hooks" / "useNavDefaults.ts"
        content = ts_path.read_text()
        assert "show_locked_nav" in content
        assert "getNavState" in content
        assert "getLockedNavTooltip" in content


# ---------------------------------------------------------------------------
# 13. CUSTODIAL_UGMA and TRUMP_ACCOUNT now in Education group
# ---------------------------------------------------------------------------


class TestEducationGrouping:
    def test_custodial_ugma_in_education_group(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "accountTypeGroups.ts"
        content = ts_path.read_text()
        assert 'CUSTODIAL_UGMA]: { label: "Education"' in content

    def test_trump_account_in_education_group(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "accountTypeGroups.ts"
        content = ts_path.read_text()
        assert 'TRUMP_ACCOUNT]: { label: "Education"' in content


# ---------------------------------------------------------------------------
# 14. CASH account in frontend sidebar config
# ---------------------------------------------------------------------------


class TestCashFrontend:
    def test_cash_in_frontend_enum(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "account.ts"
        content = ts_path.read_text()
        assert 'CASH = "cash"' in content

    def test_cash_in_sidebar_config(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "constants" / "accountTypeGroups.ts"
        content = ts_path.read_text()
        assert "CASH]:" in content

    def test_cash_in_format_account_type(self):
        ts_path = Path(__file__).resolve().parents[2] / "frontend" / "src" / "utils" / "formatAccountType.ts"
        content = ts_path.read_text()
        assert "Physical Cash" in content


# ---------------------------------------------------------------------------
# 15. Route registration
# ---------------------------------------------------------------------------


class TestRouteRegistration:
    def test_new_routes_in_main(self):
        main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
        content = main_path.read_text()
        assert "insurance_policies" in content
        assert "dependents" in content
        assert "espp" in content
        assert "treasury_rates" in content
        assert "social_security" in content
        assert "tax_loss_harvest_ledger" in content

    def test_route_prefixes(self):
        main_path = Path(__file__).resolve().parents[1] / "app" / "main.py"
        content = main_path.read_text()
        assert '"/api/v1/insurance-policies"' in content
        assert '"/api/v1/dependents"' in content
        assert '"/api/v1/espp"' in content
        assert '"/api/v1/social-security"' in content
