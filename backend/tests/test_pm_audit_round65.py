"""PM Audit Round 65 — hardcoded values, year-keyed constants, OBBBA SALT update.

Tests cover:
  - QCD limit resolves to current year value (not 2024)
  - SALT cap is $40,000 for 2025 and 2026 (not $10,000)
  - SALT cap is $10,000 for 2024
  - HDHP limits for 2026 match expected values
  - HEALTHCARE.for_year(2026) returns values higher than 2024
  - EDUCATION.costs_for_year(2026) returns values inflated above 2024
  - FICA class exists with correct rates
  - Additional Medicare thresholds exist as TAX constants
  - TAX.SALT_CAP for current year is 40_000
  - MEDIGAP year-keyed
  - Bond ladder default start_year is dynamic
"""

import datetime
from decimal import Decimal

import pytest


class TestQCDLimit:
    """Fix 1: QCD limit resolves to current year value."""

    def test_qcd_limit_not_2024_hardcoded(self):
        from app.constants.financial import QCD
        # QCD_MAX_ANNUAL should be resolved for the current year (2026), not hardcoded 105_000
        assert QCD.QCD_MAX_ANNUAL >= 105_000
        # For 2026, the value should be 108_000 (from _QCD_DATA)
        data_2026 = QCD.for_year(2026)
        assert data_2026["QCD_MAX_ANNUAL"] == 108_000

    def test_qcd_2024_value(self):
        from app.constants.financial import QCD
        data_2024 = QCD.for_year(2024)
        assert data_2024["QCD_MAX_ANNUAL"] == 105_000

    def test_charitable_giving_uses_qcd_constant(self):
        from app.api.v1.charitable_giving import QCD_ANNUAL_LIMIT
        from app.constants.financial import QCD
        assert QCD_ANNUAL_LIMIT == QCD.QCD_MAX_ANNUAL


class TestSALTCap:
    """Fix 5: SALT cap updated for OBBBA 2025."""

    def test_salt_cap_2024_is_10k(self):
        from app.constants.financial import TAX
        assert TAX.salt_cap_for_year(2024) == 10_000

    def test_salt_cap_2025_is_40k(self):
        from app.constants.financial import TAX
        assert TAX.salt_cap_for_year(2025) == 40_000

    def test_salt_cap_2026_is_40k(self):
        from app.constants.financial import TAX
        assert TAX.salt_cap_for_year(2026) == 40_000

    def test_salt_cap_current_year_is_40k(self):
        from app.constants.financial import TAX
        # Current year is 2026, so SALT_CAP should be 40_000
        assert TAX.SALT_CAP == 40_000

    def test_salt_cap_phaseout_2025(self):
        from app.constants.financial import TAX
        assert TAX.salt_cap_phaseout_for_year(2025) == 500_000

    def test_salt_cap_phaseout_2024_is_none(self):
        from app.constants.financial import TAX
        assert TAX.salt_cap_phaseout_for_year(2024) is None


class TestHDHPLimits:
    """Fix 6: HDHP limits year-keyed."""

    def test_hdhp_2026_values(self):
        from app.constants.financial import HSA
        data = HSA.hdhp_for_year(2026)
        assert data["MIN_DEDUCTIBLE_INDIVIDUAL"] == 1_700
        assert data["MIN_DEDUCTIBLE_FAMILY"] == 3_400
        assert data["MAX_OOP_INDIVIDUAL"] == 8_500
        assert data["MAX_OOP_FAMILY"] == 17_000

    def test_hdhp_2024_values(self):
        from app.constants.financial import HSA
        data = HSA.hdhp_for_year(2024)
        assert data["MIN_DEDUCTIBLE_INDIVIDUAL"] == 1_600
        assert data["MIN_DEDUCTIBLE_FAMILY"] == 3_200

    def test_hdhp_backward_compat_attrs(self):
        from app.constants.financial import HSA
        # Current year (2026) backward-compat attributes should match
        assert HSA.HDHP_MIN_DEDUCTIBLE_INDIVIDUAL == 1_700
        assert HSA.HDHP_MIN_DEDUCTIBLE_FAMILY == 3_400
        assert HSA.HDHP_MAX_OOP_INDIVIDUAL == 8_500
        assert HSA.HDHP_MAX_OOP_FAMILY == 17_000


class TestHealthcare:
    """Fix 7: HEALTHCARE year-keyed data."""

    def test_healthcare_for_year_2026_higher_than_2024(self):
        from app.constants.financial import HEALTHCARE
        data_2024 = HEALTHCARE.for_year(2024)
        data_2026 = HEALTHCARE.for_year(2026)
        assert data_2026["ACA_MONTHLY_SINGLE"] > data_2024["ACA_MONTHLY_SINGLE"]
        assert data_2026["LTC_FACILITY_MONTHLY"] > data_2024["LTC_FACILITY_MONTHLY"]

    def test_healthcare_for_year_projects_forward(self):
        from app.constants.financial import HEALTHCARE
        # 2028 should project forward from 2026 base
        data_2028 = HEALTHCARE.for_year(2028)
        data_2026 = HEALTHCARE.for_year(2026)
        assert data_2028["ACA_MONTHLY_SINGLE"] > data_2026["ACA_MONTHLY_SINGLE"]

    def test_healthcare_backward_compat(self):
        from app.constants.financial import HEALTHCARE
        # Current-year attributes should exist and be positive
        assert HEALTHCARE.ACA_MONTHLY_SINGLE > 0
        assert HEALTHCARE.ACA_MONTHLY_COUPLE > 0
        assert HEALTHCARE.LTC_FACILITY_MONTHLY > 0


class TestMedigap:
    """Fix 8: MEDIGAP year-keyed."""

    def test_medigap_2026(self):
        from app.constants.financial import MEDICARE
        assert MEDICARE.medigap_for_year(2026) == 180.00

    def test_medigap_2024(self):
        from app.constants.financial import MEDICARE
        assert MEDICARE.medigap_for_year(2024) == 160.00

    def test_medigap_backward_compat(self):
        from app.constants.financial import MEDICARE
        # Current year is 2026
        assert MEDICARE.MEDIGAP_MONTHLY == 180.00


class TestEducation:
    """Fix 9: EDUCATION.costs_for_year inflation."""

    def test_costs_for_year_2026_above_2024(self):
        from app.constants.financial import EDUCATION
        costs_2024 = EDUCATION.costs_for_year(2024)
        costs_2026 = EDUCATION.costs_for_year(2026)
        for k in costs_2024:
            assert costs_2026[k] > costs_2024[k], f"{k} should be higher in 2026"

    def test_costs_for_year_2024_is_base(self):
        from app.constants.financial import EDUCATION
        costs = EDUCATION.costs_for_year(2024)
        # Should match base values exactly (factor = 1.0)
        assert costs["public_in_state"] == 23_250
        assert costs["private"] == 57_000

    def test_inflation_factor(self):
        from app.constants.financial import EDUCATION
        # Test inflation projection for a year beyond the data table
        base_year = EDUCATION.COLLEGE_COSTS_BASE_YEAR
        future_year = base_year + 3
        costs_future = EDUCATION.costs_for_year(future_year)
        base_costs = EDUCATION.costs_for_year(base_year)
        # Must project higher than base
        assert costs_future["public_in_state"] > base_costs["public_in_state"]


class TestFICA:
    """Fix 10: FICA class exists with correct rates."""

    def test_fica_exists(self):
        from app.constants.financial import FICA
        assert FICA is not None

    def test_ss_employee_rate(self):
        from app.constants.financial import FICA
        assert FICA.SS_EMPLOYEE_RATE == Decimal("0.062")

    def test_ss_self_employed_rate(self):
        from app.constants.financial import FICA
        assert FICA.SS_SELF_EMPLOYED_RATE == Decimal("0.124")

    def test_medicare_employee_rate(self):
        from app.constants.financial import FICA
        assert FICA.MEDICARE_EMPLOYEE_RATE == Decimal("0.0145")

    def test_additional_medicare_rate(self):
        from app.constants.financial import FICA
        assert FICA.ADDITIONAL_MEDICARE_RATE == Decimal("0.009")


class TestAdditionalMedicareThresholds:
    """Fix 2: Additional Medicare Tax thresholds as TAX constants."""

    def test_threshold_single(self):
        from app.constants.financial import TAX
        assert TAX.ADDITIONAL_MEDICARE_THRESHOLD_SINGLE == 200_000

    def test_threshold_married(self):
        from app.constants.financial import TAX
        assert TAX.ADDITIONAL_MEDICARE_THRESHOLD_MARRIED == 250_000

    def test_additional_medicare_rate(self):
        from app.constants.financial import TAX
        assert TAX.ADDITIONAL_MEDICARE_RATE == Decimal("0.009")


class TestBondLadderDynamic:
    """Fix 4 & 12: Bond ladder start_year default is dynamic, fallback rates consolidated."""

    def test_request_model_start_year_default_none(self):
        from app.api.v1.bond_ladder import BondLadderRequest
        req = BondLadderRequest(total_investment=100_000)
        assert req.start_year is None

    def test_fallback_rates_constant_exists(self):
        from app.api.v1.bond_ladder import _FALLBACK_TREASURY_RATES
        assert "1_year" in _FALLBACK_TREASURY_RATES
        assert "10_year" in _FALLBACK_TREASURY_RATES


class TestCollegeStartYearFallback:
    """Fix 13: College start year uses dynamic fallback."""

    def test_no_hardcoded_2030(self):
        """The financial_plan module should not use a hardcoded 2030 fallback."""
        import inspect
        from app.api.v1 import financial_plan
        source = inspect.getsource(financial_plan._build_education_section)
        assert "or 2030" not in source
        assert "current_year + 10" in source or "+ 10)" in source
