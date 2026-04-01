"""
HSA optimization service.
Models the triple-tax-advantage of Health Savings Accounts.
Uses constants from app.constants.financial.HSA.
"""
from decimal import Decimal

from app.constants.financial import HSA, RETIREMENT


class HsaOptimizationService:
    @staticmethod
    def calculate_contribution_headroom(
        ytd_contributions: Decimal,
        is_family_plan: bool,
        age: int,
        year: int,
    ) -> dict:
        """Returns remaining contribution room for the year."""
        limits = RETIREMENT.for_year(year)
        base_limit = Decimal(str(limits["LIMIT_HSA_FAMILY"] if is_family_plan else limits["LIMIT_HSA_INDIVIDUAL"]))
        catch_up = Decimal(str(limits["LIMIT_HSA_CATCH_UP"])) if age >= RETIREMENT.CATCH_UP_AGE_HSA else Decimal("0")
        total_limit = base_limit + catch_up
        remaining = max(Decimal("0"), total_limit - ytd_contributions)
        return {
            "annual_limit": float(total_limit),
            "ytd_contributions": float(ytd_contributions),
            "remaining_room": float(remaining),
            "catch_up_eligible": age >= RETIREMENT.CATCH_UP_AGE_HSA,
            "catch_up_amount": float(catch_up),
            "can_contribute": remaining > 0 and age < HSA.MEDICARE_CUTOFF_AGE,
        }

    @staticmethod
    def project_invest_strategy(
        current_balance: Decimal,
        annual_contribution: Decimal,
        annual_medical_expenses: Decimal,
        years: int,
        investment_return: Decimal | None = None,
    ) -> dict:
        """
        Projects HSA balance under two strategies:
        1. Pay-as-you-go: spend HSA on medical each year
        2. Invest: pay medical out-of-pocket, let HSA compound
        """
        if investment_return is None:
            investment_return = HSA.INVESTMENT_RETURN_DEFAULT

        # Strategy 1: Spend as you go
        spend_balance = current_balance
        for _ in range(years):
            spend_balance = spend_balance * (1 + investment_return)
            spend_balance += annual_contribution
            spend_balance = max(Decimal("0"), spend_balance - annual_medical_expenses)

        # Strategy 2: Invest everything, pay medical OOP
        invest_balance = current_balance
        for _ in range(years):
            invest_balance = invest_balance * (1 + investment_return)
            invest_balance += annual_contribution

        return {
            "years": years,
            "spend_strategy_balance": float(spend_balance),
            "invest_strategy_balance": float(invest_balance),
            "invest_advantage": float(invest_balance - spend_balance),
            "annual_oop_medical_cost": float(annual_medical_expenses),
            "break_even_note": (
                f"Invest strategy builds ${float(invest_balance - spend_balance):,.0f} more "
                f"over {years} years by investing HSA and paying ${float(annual_medical_expenses):,.0f}/yr OOP"
            ),
        }

    @staticmethod
    def calculate_lifetime_value(
        current_balance: Decimal,
        annual_contribution: Decimal,
        years_until_retirement: int,
        investment_return: Decimal | None = None,
    ) -> dict:
        """Models HSA as a stealth IRA — full retirement account if used optimally."""
        if investment_return is None:
            investment_return = HSA.INVESTMENT_RETURN_DEFAULT

        balance = current_balance
        for _ in range(years_until_retirement):
            balance = balance * (1 + investment_return)
            balance += annual_contribution

        return {
            "projected_balance_at_retirement": float(balance),
            "years_projected": years_until_retirement,
            "tax_free_for_medical": True,
            "taxable_after_65_note": "After age 65, non-medical withdrawals taxed as ordinary income (like traditional IRA)",
        }
