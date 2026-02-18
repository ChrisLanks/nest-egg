"""Service for debt payoff strategies (snowball, avalanche, etc.)."""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.services.amortization_service import AmortizationService


class DebtAccount:
    """Simple debt account representation for payoff calculations."""

    def __init__(
        self,
        account_id: UUID,
        name: str,
        balance: Decimal,
        interest_rate: Decimal,
        minimum_payment: Decimal,
        account_type: str,
    ):
        self.account_id = account_id
        self.name = name
        self.balance = balance
        self.interest_rate = interest_rate
        self.minimum_payment = minimum_payment
        self.account_type = account_type


class PayoffStrategyService:
    """Service for calculating debt payoff strategies."""

    @staticmethod
    async def get_debt_accounts(
        db: AsyncSession, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> List[DebtAccount]:
        """
        Get all debt accounts with positive balances.

        Args:
            db: Database session
            organization_id: Organization ID
            user_id: Optional user ID for filtering

        Returns:
            List of debt accounts
        """
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.account_type.in_(["CREDIT_CARD", "LOAN", "STUDENT_LOAN", "MORTGAGE"]),
            Account.current_balance < 0,  # Debt accounts have negative balances
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        result = await db.execute(select(Account).where(and_(*conditions)))

        accounts = result.scalars().all()
        debt_accounts = []

        for account in accounts:
            balance = abs(account.current_balance)

            # Estimate minimum payment if not set
            if account.minimum_payment and account.minimum_payment > 0:
                min_payment = account.minimum_payment
            elif account.account_type == "CREDIT_CARD":
                min_payment = AmortizationService.calculate_credit_card_minimum(balance)
            elif account.interest_rate and account.interest_rate > 0:
                # Estimate based on 5-year payoff
                min_payment = AmortizationService.calculate_monthly_payment(
                    balance, account.interest_rate, 60  # 5 years
                )
            else:
                # Default to 2% of balance
                min_payment = max(balance * Decimal("0.02"), Decimal("25"))

            interest_rate = account.interest_rate or Decimal(
                "18.0"
            )  # Default 18% for unknown rates

            debt_accounts.append(
                DebtAccount(
                    account_id=account.id,
                    name=account.name,
                    balance=balance,
                    interest_rate=interest_rate,
                    minimum_payment=min_payment,
                    account_type=account.account_type,
                )
            )

        return debt_accounts

    @staticmethod
    def calculate_snowball(debts: List[DebtAccount], extra_payment: Decimal) -> Dict:
        """
        Calculate snowball strategy (smallest balance first).

        Args:
            debts: List of debt accounts
            extra_payment: Extra monthly payment to apply

        Returns:
            Strategy results with timeline and totals
        """
        if not debts:
            return {
                "strategy": "SNOWBALL",
                "total_months": 0,
                "total_interest": 0,
                "total_paid": 0,
                "debt_free_date": None,
                "debts": [],
            }

        # Sort by balance (smallest first)
        sorted_debts = sorted(debts, key=lambda d: d.balance)

        return PayoffStrategyService._calculate_strategy(sorted_debts, extra_payment, "SNOWBALL")

    @staticmethod
    def calculate_avalanche(debts: List[DebtAccount], extra_payment: Decimal) -> Dict:
        """
        Calculate avalanche strategy (highest interest rate first).

        Args:
            debts: List of debt accounts
            extra_payment: Extra monthly payment to apply

        Returns:
            Strategy results with timeline and totals
        """
        if not debts:
            return {
                "strategy": "AVALANCHE",
                "total_months": 0,
                "total_interest": 0,
                "total_paid": 0,
                "debt_free_date": None,
                "debts": [],
            }

        # Sort by interest rate (highest first)
        sorted_debts = sorted(debts, key=lambda d: d.interest_rate, reverse=True)

        return PayoffStrategyService._calculate_strategy(sorted_debts, extra_payment, "AVALANCHE")

    @staticmethod
    def calculate_current_pace(debts: List[DebtAccount]) -> Dict:
        """
        Calculate current pace (minimum payments only).

        Args:
            debts: List of debt accounts

        Returns:
            Current pace results
        """
        if not debts:
            return {
                "strategy": "CURRENT_PACE",
                "total_months": 0,
                "total_interest": 0,
                "total_paid": 0,
                "debt_free_date": None,
                "debts": [],
            }

        return PayoffStrategyService._calculate_strategy(debts, Decimal(0), "CURRENT_PACE")

    @staticmethod
    def _calculate_strategy(
        debts: List[DebtAccount], extra_payment: Decimal, strategy_name: str
    ) -> Dict:
        """
        Core strategy calculation engine.

        Simulates month-by-month payments with rolling snowball effect.

        Args:
            debts: Sorted list of debts (order determines payoff priority)
            extra_payment: Extra monthly payment available
            strategy_name: Name of strategy for result

        Returns:
            Complete strategy results
        """
        # Create working copies with running balances
        debt_states = [
            {
                "account_id": str(debt.account_id),
                "name": debt.name,
                "original_balance": float(debt.balance),
                "balance": debt.balance,
                "interest_rate": debt.interest_rate,
                "minimum_payment": debt.minimum_payment,
                "months_to_payoff": 0,
                "total_interest": Decimal(0),
                "total_paid": Decimal(0),
                "payoff_date": None,
            }
            for debt in debts
        ]

        available_extra = extra_payment
        current_month = 0
        max_months = 360  # Cap at 30 years

        while current_month < max_months:
            current_month += 1
            all_paid = True

            # Apply minimum payments and interest to all debts
            for debt in debt_states:
                if debt["balance"] > Decimal("0.01"):
                    all_paid = False

                    # Calculate interest for this month
                    monthly_rate = debt["interest_rate"] / Decimal(100) / Decimal(12)
                    interest = (debt["balance"] * monthly_rate).quantize(Decimal("0.01"))

                    # Apply minimum payment
                    payment = min(debt["minimum_payment"], debt["balance"] + interest)
                    principal = payment - interest

                    debt["balance"] -= principal
                    debt["balance"] = max(debt["balance"], Decimal(0))
                    debt["total_interest"] += interest
                    debt["total_paid"] += payment

            if all_paid:
                break

            # Apply extra payment to first debt with balance (snowball/avalanche priority)
            for debt in debt_states:
                if debt["balance"] > Decimal("0.01") and available_extra > 0:
                    extra_principal = min(available_extra, debt["balance"])
                    debt["balance"] -= extra_principal
                    debt["total_paid"] += extra_principal
                    available_extra -= extra_principal

                    if debt["balance"] <= Decimal("0.01"):
                        debt["balance"] = Decimal(0)
                        debt["months_to_payoff"] = current_month
                        debt["payoff_date"] = (
                            date.today().replace(day=1) + timedelta(days=30 * current_month)
                        ).isoformat()

                        # Snowball effect: add this debt's minimum to available extra
                        available_extra += debt["minimum_payment"]

                    break

            # Reset available extra for next month
            available_extra = extra_payment

        # Calculate totals
        total_interest = sum(debt["total_interest"] for debt in debt_states)
        total_paid = sum(debt["total_paid"] for debt in debt_states)

        # Set payoff dates for any remaining debts
        for debt in debt_states:
            if debt["months_to_payoff"] == 0 and debt["balance"] <= Decimal("0.01"):
                debt["months_to_payoff"] = current_month

        # Convert Decimal to float for JSON serialization
        for debt in debt_states:
            debt["balance"] = float(debt["balance"])
            debt["total_interest"] = float(debt["total_interest"])
            debt["total_paid"] = float(debt["total_paid"])
            debt["interest_rate"] = float(debt["interest_rate"])
            debt["minimum_payment"] = float(debt["minimum_payment"])

        return {
            "strategy": strategy_name,
            "total_months": current_month,
            "total_interest": float(total_interest),
            "total_paid": float(total_paid),
            "debt_free_date": (
                (date.today().replace(day=1) + timedelta(days=30 * current_month)).isoformat()
                if current_month < max_months
                else None
            ),
            "debts": debt_states,
        }

    @staticmethod
    async def compare_strategies(
        db: AsyncSession,
        organization_id: UUID,
        extra_payment: Decimal,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict:
        """
        Compare snowball, avalanche, and current pace strategies.

        Args:
            db: Database session
            organization_id: Organization ID
            extra_payment: Extra monthly payment amount
            user_id: Optional user ID for filtering
            account_ids: Optional list of specific account IDs to include

        Returns:
            Comparison of all three strategies
        """
        debts = await PayoffStrategyService.get_debt_accounts(db, organization_id, user_id)

        # Filter by account IDs if provided
        if account_ids:
            debts = [d for d in debts if d.account_id in account_ids]

        if not debts:
            return {
                "snowball": None,
                "avalanche": None,
                "current_pace": None,
                "recommendation": None,
            }

        snowball = PayoffStrategyService.calculate_snowball(debts, extra_payment)
        avalanche = PayoffStrategyService.calculate_avalanche(debts, extra_payment)
        current_pace = PayoffStrategyService.calculate_current_pace(debts)

        # Add savings comparisons
        if extra_payment > 0:
            snowball["interest_saved_vs_current"] = (
                current_pace["total_interest"] - snowball["total_interest"]
            )
            snowball["months_saved_vs_current"] = (
                current_pace["total_months"] - snowball["total_months"]
            )

            avalanche["interest_saved_vs_current"] = (
                current_pace["total_interest"] - avalanche["total_interest"]
            )
            avalanche["months_saved_vs_current"] = (
                current_pace["total_months"] - avalanche["total_months"]
            )

        # Determine recommendation
        recommendation = (
            "AVALANCHE" if avalanche["total_interest"] < snowball["total_interest"] else "SNOWBALL"
        )

        return {
            "snowball": snowball,
            "avalanche": avalanche,
            "current_pace": current_pace,
            "recommendation": recommendation,
        }


# Import timedelta here to avoid circular import
from datetime import timedelta
