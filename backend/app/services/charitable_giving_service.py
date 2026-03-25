"""
Charitable giving optimization service.
Uses constants from app.constants.financial.CHARITABLE.
"""
from decimal import Decimal
from app.constants.financial import CHARITABLE


class CharitableGivingService:
    @staticmethod
    def calculate_bunching_benefit(
        annual_donation: Decimal,
        standard_deduction: Decimal,
        marginal_rate: Decimal,
        bunch_years: int = 2,
    ) -> dict:
        """
        Compares annual giving vs bunching N years of donations.
        Bunching strategy: give N years of donations in one year, skip the next years.
        """
        # Annual strategy: only deduct amount above standard deduction each year
        annual_deductible = max(Decimal("0"), annual_donation - standard_deduction)
        annual_tax_savings_per_year = annual_deductible * marginal_rate
        total_annual_over_horizon = annual_tax_savings_per_year * bunch_years

        # Bunching strategy: give N * annual in year 1, standard deduction in skip years
        bunched_amount = annual_donation * bunch_years
        bunched_deductible = max(Decimal("0"), bunched_amount - standard_deduction)
        bunched_tax_savings = bunched_deductible * marginal_rate
        # Skip years just take standard deduction (no extra savings)
        total_bunched_over_horizon = bunched_tax_savings  # Only year 1 matters

        advantage = total_bunched_over_horizon - total_annual_over_horizon
        return {
            "annual_strategy_tax_savings": float(total_annual_over_horizon),
            "bunching_strategy_tax_savings": float(total_bunched_over_horizon),
            "bunching_advantage": float(advantage),
            "recommended_strategy": "bunching" if advantage > 0 else "annual",
        }

    @staticmethod
    def calculate_qcd_benefit(
        ira_rmd_amount: Decimal,
        qcd_amount: Decimal,
        marginal_rate: Decimal,
        age: float,
    ) -> dict:
        """
        Calculates tax benefit of QCD vs taking RMD as income and donating cash.
        QCD satisfies RMD without counting as income.
        """
        if age < float(CHARITABLE.QCD_ELIGIBLE_AGE):
            return {"eligible": False, "reason": f"Must be age {CHARITABLE.QCD_ELIGIBLE_AGE}+ for QCD"}

        qcd_capped = min(qcd_amount, Decimal(str(CHARITABLE.QCD_MAX_ANNUAL)))
        # QCD: donation is tax-free (not counted as income)
        qcd_tax_avoided = qcd_capped * marginal_rate
        # Cash donation: RMD counted as income, then deducted — net the same if itemizing
        # But QCD wins if taking standard deduction (no itemizing needed)
        return {
            "eligible": True,
            "qcd_amount": float(qcd_capped),
            "tax_avoided": float(qcd_tax_avoided),
            "benefit_note": "QCD avoids income inclusion entirely — superior to cash donation when taking standard deduction",
        }

    @staticmethod
    def calculate_appreciated_security_benefit(
        fair_market_value: Decimal,
        cost_basis: Decimal,
        marginal_rate: Decimal,
        ltcg_rate: Decimal,
    ) -> dict:
        """Donating appreciated securities avoids capital gains vs selling then donating cash."""
        gain = fair_market_value - cost_basis
        cg_avoided = gain * ltcg_rate
        deduction_value = fair_market_value * marginal_rate
        cash_deduction_value = fair_market_value * marginal_rate  # Same if same amount donated
        extra_benefit = cg_avoided  # The advantage of donating securities vs cash
        return {
            "fair_market_value": float(fair_market_value),
            "unrealized_gain": float(gain),
            "capital_gains_tax_avoided": float(cg_avoided),
            "deduction_value": float(deduction_value),
            "total_tax_benefit": float(deduction_value + cg_avoided),
            "vs_cash_donation_extra_benefit": float(extra_benefit),
        }
