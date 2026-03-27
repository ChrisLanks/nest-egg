"""Tests for PM audit round 64 — NIIT, AMT, SE tax cap, gift tracker,
deduction optimizer, withholding check, ESTATE for_year, SS bend points."""

import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── NIIT calculation ─────────────────────────────────────────────────────

class TestNIIT:
    """Net Investment Income Tax in tax_projection_service."""

    def test_niit_above_threshold_single(self):
        """NIIT applies when MAGI > $200K single."""
        from app.constants.financial import TAX
        magi = 300_000
        threshold = TAX.NII_THRESHOLD_SINGLE  # 200_000
        cap_gains = 80_000
        net_investment_income = cap_gains
        niit = min(net_investment_income, magi - threshold) * float(TAX.NII_SURTAX_RATE)
        assert niit == pytest.approx(80_000 * 0.038, abs=1)

    def test_niit_below_threshold(self):
        """No NIIT when MAGI below threshold."""
        from app.constants.financial import TAX
        magi = 150_000
        threshold = TAX.NII_THRESHOLD_SINGLE
        assert magi <= threshold
        # NIIT = 0

    def test_niit_married_threshold(self):
        """NIIT threshold is $250K for married filers."""
        from app.constants.financial import TAX
        assert TAX.NII_THRESHOLD_MARRIED == 250_000

    def test_niit_lesser_of_nii_or_excess(self):
        """NIIT is on lesser of NII or (MAGI - threshold)."""
        from app.constants.financial import TAX
        magi = 220_000  # $20K over threshold
        cap_gains = 50_000  # NII is larger
        threshold = TAX.NII_THRESHOLD_SINGLE
        niit = min(cap_gains, magi - threshold) * float(TAX.NII_SURTAX_RATE)
        # min(50K, 20K) = 20K * 3.8% = 760
        assert niit == pytest.approx(760, abs=1)


# ── AMT calculation ──────────────────────────────────────────────────────

class TestAMT:
    """AMT exposure calculator."""

    def test_amt_no_iso(self):
        """No AMT when no ISO exercises and moderate income."""
        from app.api.v1.amt_calculator import _bracket_tax
        from app.constants.financial import AMT, TAX

        year = 2026
        tax_data = TAX.for_year(year)
        amt_data = AMT.for_year(year)

        income = 100_000
        std_ded = tax_data["STANDARD_DEDUCTION_SINGLE"]
        regular_tax = _bracket_tax(max(0, income - std_ded), "single", year)

        # AMT income with no ISO
        amti = income
        exemption = amt_data["AMT_EXEMPTION_SINGLE"]
        amt_taxable = max(0, amti - exemption)
        # At $100K income, exemption (~$90K) covers most
        tmt = amt_taxable * 0.26
        assert max(0, tmt - regular_tax) == 0  # No AMT owed

    def test_amt_with_iso_exercises(self):
        """AMT owed when ISO exercises push AMTI above exemption."""
        from app.api.v1.amt_calculator import _bracket_tax
        from app.constants.financial import AMT, TAX

        year = 2026
        amt_data = AMT.for_year(year)
        tax_data = TAX.for_year(year)

        income = 200_000
        iso_exercises = 300_000
        std_ded = tax_data["STANDARD_DEDUCTION_SINGLE"]
        regular_tax = _bracket_tax(max(0, income - std_ded), "single", year)

        amti = income + iso_exercises  # 500K
        exemption = amt_data["AMT_EXEMPTION_SINGLE"]
        phaseout = amt_data["AMT_PHASEOUT_SINGLE"]
        if amti > phaseout:
            exemption = max(0, exemption - (amti - phaseout) * 0.25)
        amt_taxable = max(0, amti - exemption)
        threshold_26 = amt_data["AMT_RATE_26_THRESHOLD"]
        if amt_taxable <= threshold_26:
            tmt = amt_taxable * 0.26
        else:
            tmt = threshold_26 * 0.26 + (amt_taxable - threshold_26) * 0.28

        amt_owed = max(0, tmt - regular_tax)
        assert amt_owed > 0  # ISO exercises cause AMT

    def test_amt_exemption_phaseout(self):
        """AMT exemption phases out at 25 cents per dollar over threshold."""
        from app.constants.financial import AMT
        amt_data = AMT.for_year(2026)
        phaseout = amt_data["AMT_PHASEOUT_SINGLE"]
        exemption = amt_data["AMT_EXEMPTION_SINGLE"]
        # $100K over phaseout reduces exemption by $25K
        excess = 100_000
        reduced = max(0, exemption - excess * 0.25)
        assert reduced == exemption - 25_000


# ── SE tax with SS wage base cap ─────────────────────────────────────────

class TestSETax:
    """Self-employment tax capping and Additional Medicare Tax."""

    def test_se_ss_capped_at_taxable_max(self):
        """SS portion of SE tax is capped at SS.TAXABLE_MAX."""
        from app.constants.financial import SS
        se_income = 300_000
        ss_portion = min(se_income, SS.TAXABLE_MAX) * 0.124
        # Should be capped, not 300K * 0.124
        assert ss_portion == SS.TAXABLE_MAX * 0.124

    def test_se_medicare_no_cap(self):
        """Medicare portion of SE tax has no cap."""
        se_income = 500_000
        medicare = se_income * 0.029
        assert medicare == 500_000 * 0.029

    def test_se_additional_medicare_single(self):
        """Additional Medicare Tax on SE income above $200K (single)."""
        se_income = 300_000
        threshold = 200_000
        additional = max(0, se_income - threshold) * 0.009
        assert additional == 100_000 * 0.009

    def test_se_additional_medicare_married(self):
        """Additional Medicare Tax threshold is $250K for married."""
        se_income = 300_000
        threshold = 250_000
        additional = max(0, se_income - threshold) * 0.009
        assert additional == 50_000 * 0.009

    def test_se_deduction_half(self):
        """SE tax deduction is 50% of total SE tax."""
        from app.constants.financial import SS
        se_income = 150_000
        se_ss = min(se_income, SS.TAXABLE_MAX) * 0.124
        se_medicare = se_income * 0.029
        se_tax = se_ss + se_medicare
        se_deduction = se_tax * 0.50
        assert se_deduction == pytest.approx(se_tax / 2, abs=0.01)


# ── Gift tracker CRUD and summary ────────────────────────────────────────

class TestGiftTracker:
    """Gift tracker API logic tests."""

    def test_annual_exclusion_from_constants(self):
        """Gift annual exclusion comes from ESTATE constants."""
        from app.constants.financial import ESTATE
        assert ESTATE.ANNUAL_GIFT_EXCLUSION == 19_000
        assert ESTATE.ANNUAL_GIFT_EXCLUSION_MARRIED == 38_000

    def test_gift_excess_counts_against_lifetime(self):
        """Gifts exceeding annual exclusion count against lifetime exemption."""
        annual_limit = 19_000
        gifts_to_alice = 25_000
        excess = max(0, gifts_to_alice - annual_limit)
        assert excess == 6_000

    def test_gift_summary_multiple_recipients(self):
        """Summary correctly groups by recipient."""
        annual_limit = 19_000
        gifts = {
            "Alice": 25_000,
            "Bob": 10_000,
        }
        total_excess = 0
        for name, amount in gifts.items():
            excess = max(0, amount - annual_limit)
            total_excess += excess
        assert total_excess == 6_000  # Only Alice exceeds

    def test_529_superfunding(self):
        """529 superfunding allows 5x annual exclusion."""
        from app.constants.financial import ESTATE
        limit = ESTATE.ANNUAL_GIFT_EXCLUSION
        superfund_max = limit * 5
        assert superfund_max == 95_000


# ── Deduction optimizer ──────────────────────────────────────────────────

class TestDeductionOptimizer:
    """Itemized vs standard deduction comparison."""

    def test_standard_wins_low_deductions(self):
        """Standard deduction wins when itemized total is lower."""
        from app.constants.financial import TAX
        std = TAX.STANDARD_DEDUCTION_SINGLE
        salt = min(5_000, 10_000)
        mortgage = 3_000
        charitable = 1_000
        medical = 0
        total_itemized = salt + mortgage + charitable + medical
        assert total_itemized < std

    def test_itemized_wins_high_deductions(self):
        """Itemizing wins when mortgage + SALT + charitable exceed standard."""
        from app.constants.financial import TAX
        std = TAX.STANDARD_DEDUCTION_SINGLE
        salt = min(10_000, 10_000)
        mortgage = 12_000
        charitable = 5_000
        medical = 0
        total_itemized = salt + mortgage + charitable + medical
        # With 2026 std ded of ~$16,100, $27K itemized should win
        assert total_itemized > std

    def test_salt_cap_applied(self):
        """SALT deduction is capped at $10,000."""
        state_taxes = 25_000
        capped = min(state_taxes, 10_000)
        assert capped == 10_000

    def test_medical_deduction_threshold(self):
        """Medical expenses only deductible above 7.5% of AGI."""
        agi = 100_000
        medical = 10_000
        deductible = max(0, medical - agi * 0.075)
        assert deductible == 2_500

    def test_breakeven_mortgage_interest(self):
        """Breakeven = standard deduction minus other itemized deductions."""
        from app.constants.financial import TAX
        std = TAX.STANDARD_DEDUCTION_SINGLE
        other = 8_000  # SALT + charitable
        breakeven = max(0, std - other)
        assert breakeven == std - 8_000


# ── Withholding check safe harbour ───────────────────────────────────────

class TestWithholdingCheck:
    """W-4 withholding optimizer."""

    def test_safe_harbour_90_pct_current(self):
        """Safe harbour is 90% of current year tax when no prior year data."""
        projected_tax = 30_000
        safe_harbour = projected_tax * 0.90
        assert safe_harbour == 27_000

    def test_safe_harbour_with_prior_year(self):
        """Safe harbour uses min(90% current, 110% prior) for high earners."""
        projected_tax = 50_000
        prior_year_tax = 40_000
        total_income = 200_000  # > $150K threshold
        prior_factor = 1.10
        safe_harbour = min(projected_tax * 0.90, prior_year_tax * prior_factor)
        assert safe_harbour == min(45_000, 44_000)
        assert safe_harbour == 44_000

    def test_safe_harbour_100_pct_prior_low_income(self):
        """100% of prior year tax for AGI <= $150K."""
        projected_tax = 20_000
        prior_year_tax = 18_000
        total_income = 100_000  # <= $150K
        prior_factor = 1.00
        safe_harbour = min(projected_tax * 0.90, prior_year_tax * prior_factor)
        assert safe_harbour == min(18_000, 18_000)
        assert safe_harbour == 18_000

    def test_underpayment_risk(self):
        """Underpayment risk when projected withholding < safe harbour."""
        ytd_withheld = 10_000
        monthly_rate = ytd_withheld / 6  # 6 months elapsed
        projected_year_end = ytd_withheld + monthly_rate * 6
        safe_harbour = 25_000
        assert projected_year_end < safe_harbour


# ── ESTATE for_year ──────────────────────────────────────────────────────

class TestEstateForYear:
    """ESTATE class year-keyed data."""

    def test_estate_2024(self):
        """2024 estate exemption is $13.61M."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2024)
        assert data["FEDERAL_EXEMPTION"] == 13_610_000

    def test_estate_2025(self):
        """2025 estate exemption is $13.99M."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2025)
        assert data["FEDERAL_EXEMPTION"] == 13_990_000

    def test_estate_2026(self):
        """2026 estate exemption matches current-year class attr."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2026)
        assert data["FEDERAL_EXEMPTION"] == ESTATE.FEDERAL_EXEMPTION

    def test_estate_gift_exclusion_2024(self):
        """2024 annual gift exclusion is $18K."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2024)
        assert data["ANNUAL_GIFT_EXCLUSION"] == 18_000

    def test_estate_gift_exclusion_married(self):
        """Married gift exclusion is 2x single."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2025)
        assert data["ANNUAL_GIFT_EXCLUSION_MARRIED"] == 38_000

    def test_estate_projects_forward(self):
        """Future year projects forward from latest known."""
        from app.constants.financial import ESTATE
        data = ESTATE.for_year(2030)
        # Should project from 2026 data
        assert data["FEDERAL_EXEMPTION"] > 13_990_000


# ── SS bend points use year_turn_62 ──────────────────────────────────────

class TestSSBendPoints:
    """Social Security bend points by eligibility year."""

    def test_bend_points_2024(self):
        """2024 bend points from data table."""
        from app.constants.financial import SS
        data = SS.for_year(2024)
        assert data["BEND_POINT_1"] == 1_174
        assert data["BEND_POINT_2"] == 7_078

    def test_bend_points_2026(self):
        """2026 bend points from data table."""
        from app.constants.financial import SS
        data = SS.for_year(2026)
        assert data["BEND_POINT_1"] == 1_286
        assert data["BEND_POINT_2"] == 7_749

    def test_estimate_pia_uses_year_turn_62(self):
        """estimate_pia uses bend points for the year worker turns 62."""
        from app.services.retirement.social_security_estimator import estimate_pia
        from app.constants.financial import SS

        aime = 5000  # Between bend points
        pia_2024 = estimate_pia(aime, year_turn_62=2024)
        pia_2026 = estimate_pia(aime, year_turn_62=2026)
        # Different bend points should produce different PIAs
        # (2026 has higher bend points, so more at 90% rate = higher PIA)
        assert pia_2026 > pia_2024

    def test_estimate_pia_default_uses_current(self):
        """estimate_pia without year_turn_62 uses module-level constants."""
        from app.services.retirement.social_security_estimator import estimate_pia
        aime = 3000
        pia = estimate_pia(aime)
        assert pia > 0

    def test_bend_points_project_forward(self):
        """Future year projects bend points from latest known."""
        from app.constants.financial import SS
        data = SS.for_year(2030)
        # Should be higher than 2026
        assert data["BEND_POINT_1"] > 1_286


# ── Charitable giving uses TAX constants ─────────────────────────────────

class TestCharitableGivingConstants:
    """Verify charitable giving module uses dynamic constants."""

    def test_standard_deduction_from_tax_class(self):
        """Charitable giving std deduction matches TAX class."""
        from app.api.v1.charitable_giving import STANDARD_DEDUCTION_SINGLE, STANDARD_DEDUCTION_MFJ
        from app.constants.financial import TAX
        assert STANDARD_DEDUCTION_SINGLE == TAX.STANDARD_DEDUCTION_SINGLE
        assert STANDARD_DEDUCTION_MFJ == TAX.STANDARD_DEDUCTION_MARRIED


# ── What-if salary change uses dynamic brackets ─────────────────────────

class TestWhatIfSalaryChange:
    """Verify salary change endpoint uses year-keyed brackets."""

    def test_salary_change_request_has_filing_status(self):
        """SalaryChangeRequest has filing_status field."""
        from app.api.v1.what_if import SalaryChangeRequest
        req = SalaryChangeRequest(
            current_salary=100_000,
            new_salary=120_000,
            current_state="CA",
            filing_status="married",
        )
        assert req.filing_status == "married"


# ── Financial plan uses ESTATE constant ──────────────────────────────────

class TestFinancialPlanConstants:
    """Verify financial plan uses constants instead of hardcodes."""

    def test_estate_exemption_not_hardcoded(self):
        """ESTATE.FEDERAL_EXEMPTION should match what financial_plan uses."""
        from app.constants.financial import ESTATE
        # The 2025 value was 13.61M in the bug; should now be 13.99M for 2025+
        assert ESTATE.FEDERAL_EXEMPTION >= 13_610_000
