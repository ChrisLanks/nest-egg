"""Service for amortization calculations and debt payoff math."""

import math
from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional


class AmortizationService:
    """Service for calculating loan amortization and payoff schedules."""

    @staticmethod
    def calculate_monthly_payment(
        principal: Decimal, annual_rate: Decimal, term_months: int
    ) -> Decimal:
        """
        Calculate monthly payment using standard amortization formula.

        Formula: M = P[r(1+r)^n]/[(1+r)^n-1]
        where:
        - M = monthly payment
        - P = principal
        - r = monthly interest rate (annual rate / 12)
        - n = number of payments

        Args:
            principal: Loan principal amount
            annual_rate: Annual interest rate as percentage (e.g., 5.5 for 5.5%)
            term_months: Loan term in months

        Returns:
            Monthly payment amount
        """
        if principal <= 0 or term_months <= 0:
            return Decimal(0)

        if annual_rate == 0:
            # No interest, simple division
            return principal / Decimal(term_months)

        # Convert annual rate to monthly decimal rate
        monthly_rate = (annual_rate / Decimal(100)) / Decimal(12)

        # Calculate using amortization formula
        numerator = monthly_rate * (Decimal(1) + monthly_rate) ** term_months
        denominator = ((Decimal(1) + monthly_rate) ** term_months) - Decimal(1)

        monthly_payment = principal * (numerator / denominator)

        return monthly_payment.quantize(Decimal("0.01"))

    @staticmethod
    def calculate_credit_card_minimum(
        balance: Decimal,
        minimum_percentage: Decimal = Decimal("2.0"),
        minimum_floor: Decimal = Decimal("25.00"),
    ) -> Decimal:
        """
        Calculate credit card minimum payment.

        Typically 2% of balance or $25, whichever is higher.

        Args:
            balance: Current balance
            minimum_percentage: Minimum percentage (default 2%)
            minimum_floor: Minimum floor amount (default $25)

        Returns:
            Minimum payment amount
        """
        if balance <= 0:
            return Decimal(0)

        percentage_payment = balance * minimum_percentage / Decimal(100)
        return max(percentage_payment, minimum_floor).quantize(Decimal("0.01"))

    @staticmethod
    def calculate_payoff_months(
        balance: Decimal, annual_rate: Decimal, monthly_payment: Decimal
    ) -> int:
        """
        Calculate months to pay off debt.

        Args:
            balance: Current balance
            annual_rate: Annual interest rate as percentage
            monthly_payment: Monthly payment amount

        Returns:
            Number of months to payoff (0 if payment too low)
        """
        if balance <= 0:
            return 0

        if monthly_payment <= 0:
            return 999  # Payment too low, will never pay off

        if annual_rate == 0:
            # No interest, simple division
            return math.ceil(float(balance / monthly_payment))

        monthly_rate = float(annual_rate / Decimal(100) / Decimal(12))
        monthly_interest = float(balance) * monthly_rate

        # Check if payment covers interest
        if monthly_payment <= Decimal(str(monthly_interest)):
            return 999  # Payment too low to cover interest

        # Use logarithm formula: n = -log(1 - r*P/M) / log(1 + r)
        try:
            numerator = -math.log(1 - (monthly_rate * float(balance) / float(monthly_payment)))
            denominator = math.log(1 + monthly_rate)
            months = math.ceil(numerator / denominator)
            return min(months, 999)  # Cap at 999 months
        except (ValueError, ZeroDivisionError):
            return 999

    @staticmethod
    def generate_amortization_schedule(
        principal: Decimal,
        annual_rate: Decimal,
        monthly_payment: Decimal,
        start_date: Optional[date] = None,
        max_months: int = 360,
    ) -> List[Dict]:
        """
        Generate month-by-month amortization schedule.

        Args:
            principal: Starting principal
            annual_rate: Annual interest rate as percentage
            monthly_payment: Monthly payment amount
            start_date: Starting date (defaults to today)
            max_months: Maximum months to calculate (cap at 360 = 30 years)

        Returns:
            List of monthly payment breakdowns with principal/interest split
        """
        if start_date is None:
            start_date = date.today()

        schedule = []
        remaining_balance = principal
        current_date = start_date
        month_num = 0

        monthly_rate = annual_rate / Decimal(100) / Decimal(12)

        while remaining_balance > Decimal("0.01") and month_num < max_months:
            month_num += 1

            # Calculate interest for this month
            interest_payment = (remaining_balance * monthly_rate).quantize(Decimal("0.01"))

            # Principal payment is remainder
            principal_payment = monthly_payment - interest_payment

            # Handle final payment
            if principal_payment >= remaining_balance:
                principal_payment = remaining_balance
                total_payment = principal_payment + interest_payment
            else:
                total_payment = monthly_payment

            remaining_balance -= principal_payment
            remaining_balance = remaining_balance.quantize(Decimal("0.01"))

            schedule.append(
                {
                    "month": month_num,
                    "date": current_date.isoformat(),
                    "payment": float(total_payment),
                    "principal": float(principal_payment),
                    "interest": float(interest_payment),
                    "balance": float(max(remaining_balance, Decimal(0))),
                }
            )

            # Move to next month
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, current_date.day)
            else:
                try:
                    current_date = date(current_date.year, current_date.month + 1, current_date.day)
                except ValueError:
                    # Handle cases like Jan 31 -> Feb 31 (doesn't exist)
                    current_date = date(current_date.year, current_date.month + 1, 28)

            # Stop if balance is paid off
            if remaining_balance <= Decimal("0.01"):
                break

        return schedule

    @staticmethod
    def calculate_total_interest(
        principal: Decimal, annual_rate: Decimal, monthly_payment: Decimal
    ) -> Decimal:
        """
        Calculate total interest paid over life of loan.

        Args:
            principal: Loan principal
            annual_rate: Annual interest rate as percentage
            monthly_payment: Monthly payment amount

        Returns:
            Total interest paid
        """
        months = AmortizationService.calculate_payoff_months(
            principal, annual_rate, monthly_payment
        )

        if months >= 999:
            return Decimal(999999)  # Essentially infinite

        total_paid = monthly_payment * Decimal(months)
        total_interest = total_paid - principal

        return total_interest.quantize(Decimal("0.01"))
