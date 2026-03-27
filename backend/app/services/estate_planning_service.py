"""
Estate and beneficiary planning service.
Uses constants from app.constants.financial.ESTATE.
"""
from decimal import Decimal

from app.constants.financial import ESTATE


class EstatePlanningService:
    @staticmethod
    def calculate_estate_tax_exposure(
        net_worth: Decimal,
        filing_status: str = "single",
    ) -> dict:
        """Estimates federal estate tax exposure above the exemption."""
        exemption = Decimal(str(ESTATE.FEDERAL_EXEMPTION))
        if filing_status == "married":
            exemption = exemption * 2  # Portability
        taxable_estate = max(Decimal("0"), net_worth - exemption)
        estimated_tax = taxable_estate * ESTATE.FEDERAL_TAX_RATE
        return {
            "net_worth": float(net_worth),
            "federal_exemption": float(exemption),
            "taxable_estate": float(taxable_estate),
            "estimated_federal_tax": float(estimated_tax),
            "above_exemption": taxable_estate > 0,
            "tcja_sunset_risk": ESTATE.TCJA_SUNSET_RISK,
            "sunset_note": (
                "TCJA high exemption extended through 2034 by the One Big Beautiful Bill Act (2025). "
                "Exemption may revert to ~$7M (inflation-adjusted) after 2034 if not further extended."
            ),
        }

    @staticmethod
    def get_beneficiary_coverage_summary(
        accounts: list[dict],
        beneficiaries: list[dict],
    ) -> dict:
        """Returns % of accounts by value that have a primary beneficiary."""
        account_ids_with_beneficiary = {
            b["account_id"] for b in beneficiaries
            if b.get("designation_type") == "primary" and b.get("account_id")
        }
        total_value = sum(a.get("balance", 0) for a in accounts)
        covered_value = sum(
            a.get("balance", 0) for a in accounts
            if a.get("id") in account_ids_with_beneficiary
        )
        coverage_pct = (covered_value / total_value * 100) if total_value > 0 else 0.0
        return {
            "total_accounts": len(accounts),
            "covered_accounts": len([a for a in accounts if a.get("id") in account_ids_with_beneficiary]),
            "coverage_pct": round(coverage_pct, 1),
            "total_value": float(total_value),
            "covered_value": float(covered_value),
            "uncovered_value": float(total_value - covered_value),
        }

    @staticmethod
    def validate_beneficiary_percentages(
        designations: list[dict],
        designation_type: str,
    ) -> dict:
        """Validates that primary (or contingent) beneficiary percentages sum to 100."""
        filtered = [d for d in designations if d.get("designation_type") == designation_type]
        if not filtered:
            return {"valid": True, "total_pct": 0.0, "message": "No designations of this type"}
        total = sum(Decimal(str(d.get("percentage", 0))) for d in filtered)
        valid = abs(total - Decimal("100")) < Decimal("0.01")
        return {
            "valid": valid,
            "total_pct": float(total),
            "message": "Valid" if valid else f"Percentages sum to {float(total):.1f}%, must be 100%",
        }
