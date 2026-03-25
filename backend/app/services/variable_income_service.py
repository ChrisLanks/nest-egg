"""
Variable income planning service for freelancers and self-employed individuals.
Uses constants from app.constants.financial.VARIABLE_INCOME.
"""
from decimal import Decimal
from app.constants.financial import VARIABLE_INCOME


class VariableIncomeService:
    @staticmethod
    def calculate_smoothed_income(monthly_incomes: list[Decimal]) -> dict:
        """Rolling average and income floor from historical monthly incomes."""
        if not monthly_incomes:
            return {"average": 0.0, "minimum": 0.0, "maximum": 0.0, "volatility_pct": 0.0, "floor": 0.0}
        n = len(monthly_incomes)
        avg = sum(monthly_incomes) / n
        minimum = min(monthly_incomes)
        maximum = max(monthly_incomes)
        variance = sum((x - avg) ** 2 for x in monthly_incomes) / n
        std_dev = variance ** Decimal("0.5")
        volatility_pct = (std_dev / avg * 100) if avg > 0 else Decimal("0")
        # Conservative floor: use the 25th percentile of monthly incomes
        sorted_incomes = sorted(monthly_incomes)
        floor_idx = max(0, int(n * 0.25) - 1)
        floor = sorted_incomes[floor_idx]
        return {
            "average": float(avg),
            "minimum": float(minimum),
            "maximum": float(maximum),
            "volatility_pct": float(volatility_pct),
            "floor": float(floor),
            "months_analyzed": n,
        }

    @staticmethod
    def estimate_quarterly_taxes(
        ytd_income: Decimal,
        prior_year_tax: Decimal,
        annual_income_estimate: Decimal,
        effective_rate: Decimal,
        quarter: int,
    ) -> dict:
        """Estimates the quarterly estimated tax payment due."""
        # Safe harbor: pay 100% (or 110% if income > threshold) of prior year tax
        if annual_income_estimate > VARIABLE_INCOME.SAFE_HARBOR_110_PCT_INCOME_THRESHOLD:
            safe_harbor_annual = prior_year_tax * VARIABLE_INCOME.SAFE_HARBOR_RATE_HIGH_INCOME
        else:
            safe_harbor_annual = prior_year_tax * VARIABLE_INCOME.SAFE_HARBOR_RATE_NORMAL
        quarterly_safe_harbor = safe_harbor_annual / 4

        # Annualized income method
        annualized_tax = annual_income_estimate * effective_rate
        # Add self-employment tax
        se_tax = annual_income_estimate * VARIABLE_INCOME.SE_TAX_RATE
        se_deduction = se_tax * VARIABLE_INCOME.SE_TAX_DEDUCTIBLE_HALF
        total_estimated_annual = annualized_tax + se_tax - (se_deduction * effective_rate)
        quarterly_annualized = total_estimated_annual / 4

        due_month = VARIABLE_INCOME.QUARTERLY_TAX_DUE_MONTHS[quarter - 1]
        return {
            "quarter": quarter,
            "due_month": due_month,
            "safe_harbor_payment": float(quarterly_safe_harbor),
            "annualized_estimate": float(quarterly_annualized),
            "recommended_payment": float(max(quarterly_safe_harbor, quarterly_annualized)),
        }

    @staticmethod
    def calculate_se_tax(net_self_employment_income: Decimal) -> dict:
        """Calculates self-employment tax and the deductible half."""
        se_tax = net_self_employment_income * VARIABLE_INCOME.SE_TAX_RATE
        deductible_half = se_tax * VARIABLE_INCOME.SE_TAX_DEDUCTIBLE_HALF
        return {
            "se_tax": float(se_tax),
            "deductible_half": float(deductible_half),
            "net_cost": float(se_tax - deductible_half),
        }
