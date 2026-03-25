"""Unit tests for EstatePlanningService."""
from decimal import Decimal
import pytest
from app.services.estate_planning_service import EstatePlanningService


class TestEstateTaxExposure:
    def test_below_exemption_no_tax(self):
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("5_000_000"),
            filing_status="single",
        )
        assert result["taxable_estate"] == 0.0
        assert result["estimated_federal_tax"] == 0.0
        assert result["above_exemption"] is False

    def test_above_exemption_has_tax(self):
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("20_000_000"),
            filing_status="single",
        )
        assert result["taxable_estate"] > 0
        assert result["estimated_federal_tax"] > 0
        assert result["above_exemption"] is True

    def test_married_doubles_exemption(self):
        single = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("15_000_000"),
            filing_status="single",
        )
        married = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("15_000_000"),
            filing_status="married",
        )
        # Married has higher exemption, so less taxable
        assert married["taxable_estate"] < single["taxable_estate"]

    def test_tcja_sunset_flagged(self):
        result = EstatePlanningService.calculate_estate_tax_exposure(
            net_worth=Decimal("5_000_000"),
        )
        assert result["tcja_sunset_risk"] is True


class TestBeneficiaryCoverage:
    def test_all_accounts_covered(self):
        accounts = [
            {"id": "a1", "balance": 100_000},
            {"id": "a2", "balance": 50_000},
        ]
        beneficiaries = [
            {"account_id": "a1", "designation_type": "primary"},
            {"account_id": "a2", "designation_type": "primary"},
        ]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, beneficiaries)
        assert result["coverage_pct"] == 100.0

    def test_no_beneficiaries(self):
        accounts = [{"id": "a1", "balance": 100_000}]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, [])
        assert result["coverage_pct"] == 0.0
        assert result["uncovered_value"] == 100_000.0

    def test_partial_coverage(self):
        accounts = [
            {"id": "a1", "balance": 200_000},
            {"id": "a2", "balance": 200_000},
        ]
        beneficiaries = [{"account_id": "a1", "designation_type": "primary"}]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, beneficiaries)
        assert result["coverage_pct"] == 50.0

    def test_contingent_not_counted_as_coverage(self):
        accounts = [{"id": "a1", "balance": 100_000}]
        beneficiaries = [{"account_id": "a1", "designation_type": "contingent"}]
        result = EstatePlanningService.get_beneficiary_coverage_summary(accounts, beneficiaries)
        assert result["coverage_pct"] == 0.0

    def test_empty_accounts(self):
        result = EstatePlanningService.get_beneficiary_coverage_summary([], [])
        assert result["coverage_pct"] == 0.0


class TestBeneficiaryPercentages:
    def test_valid_two_beneficiaries(self):
        designations = [
            {"designation_type": "primary", "percentage": 60},
            {"designation_type": "primary", "percentage": 40},
        ]
        result = EstatePlanningService.validate_beneficiary_percentages(designations, "primary")
        assert result["valid"] is True

    def test_invalid_over_100(self):
        designations = [
            {"designation_type": "primary", "percentage": 60},
            {"designation_type": "primary", "percentage": 50},
        ]
        result = EstatePlanningService.validate_beneficiary_percentages(designations, "primary")
        assert result["valid"] is False

    def test_no_designations_of_type(self):
        designations = [{"designation_type": "contingent", "percentage": 100}]
        result = EstatePlanningService.validate_beneficiary_percentages(designations, "primary")
        assert result["valid"] is True  # no primary = vacuously valid

    def test_single_100_pct(self):
        designations = [{"designation_type": "primary", "percentage": 100}]
        result = EstatePlanningService.validate_beneficiary_percentages(designations, "primary")
        assert result["valid"] is True
