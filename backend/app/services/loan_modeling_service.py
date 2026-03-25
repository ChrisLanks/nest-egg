"""
Loan origination and affordability modeling service.
Uses constants from app.constants.financial.LENDING.
"""
from decimal import Decimal
from app.constants.financial import LENDING


class LoanModelingService:
    @staticmethod
    def calculate_monthly_payment(principal: Decimal, annual_rate: Decimal, term_months: int) -> Decimal:
        """Standard amortization formula: M = P[r(1+r)^n]/[(1+r)^n-1]"""
        if annual_rate == 0:
            return (principal / term_months).quantize(Decimal("0.01"))
        r = annual_rate / 12
        n = term_months
        factor = r * (1 + r) ** n / ((1 + r) ** n - 1)
        return (principal * factor).quantize(Decimal("0.01"))

    @staticmethod
    def calculate_dti_impact(
        annual_gross_income: Decimal,
        existing_monthly_debt: Decimal,
        new_monthly_payment: Decimal,
    ) -> dict:
        """Returns DTI before and after new loan, plus whether it exceeds limits."""
        monthly_income = annual_gross_income / 12
        dti_before = existing_monthly_debt / monthly_income
        dti_after = (existing_monthly_debt + new_monthly_payment) / monthly_income
        return {
            "dti_before": float(dti_before),
            "dti_after": float(dti_after),
            "exceeds_conventional": dti_after > LENDING.MAX_DTI_CONVENTIONAL,
            "exceeds_fha": dti_after > LENDING.MAX_DTI_FHA,
            "recommendation": (
                "Within conventional limits" if dti_after <= LENDING.MAX_DTI_CONVENTIONAL
                else "Exceeds conventional limit — consider FHA or reducing loan amount"
            ),
        }

    @staticmethod
    def generate_amortization_schedule(
        principal: Decimal,
        annual_rate: Decimal,
        term_months: int,
    ) -> list[dict]:
        """Returns full amortization schedule."""
        monthly_payment = LoanModelingService.calculate_monthly_payment(principal, annual_rate, term_months)
        r = annual_rate / 12
        balance = principal
        schedule = []
        for month in range(1, term_months + 1):
            interest = (balance * r).quantize(Decimal("0.01"))
            principal_paid = monthly_payment - interest
            balance = max(Decimal("0"), balance - principal_paid)
            schedule.append({
                "month": month,
                "payment": float(monthly_payment),
                "principal": float(principal_paid),
                "interest": float(interest),
                "balance": float(balance),
            })
        return schedule

    @staticmethod
    def buy_vs_lease(
        vehicle_price: Decimal,
        down_payment: Decimal,
        loan_rate: Decimal,
        loan_term_months: int,
        lease_monthly: Decimal,
        lease_term_months: int,
        residual_value_pct: Decimal,
    ) -> dict:
        """Compares total cost of buying vs leasing over the lease term."""
        loan_amount = vehicle_price - down_payment
        monthly_payment = LoanModelingService.calculate_monthly_payment(loan_amount, loan_rate, loan_term_months)
        # Cost of buying over lease_term_months
        buy_payments = monthly_payment * lease_term_months
        residual_value = vehicle_price * residual_value_pct
        buy_total_cost = float(down_payment + buy_payments - residual_value)
        lease_total_cost = float(lease_monthly * lease_term_months)
        return {
            "buy_total_cost": buy_total_cost,
            "lease_total_cost": lease_total_cost,
            "buy_monthly": float(monthly_payment),
            "lease_monthly": float(lease_monthly),
            "recommendation": "buy" if buy_total_cost < lease_total_cost else "lease",
            "savings": abs(buy_total_cost - lease_total_cost),
        }
