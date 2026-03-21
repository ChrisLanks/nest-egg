"""Rental Property P&L service for Schedule E-style income/expense tracking."""

import logging
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.transaction import Category, Transaction

logger = logging.getLogger(__name__)


class RentalPropertyService:
    """Service for rental property P&L calculations."""

    # Schedule E expense categories
    RENTAL_EXPENSE_CATEGORIES = [
        "Advertising",
        "Auto & Travel",
        "Cleaning & Maintenance",
        "Commissions",
        "Insurance",
        "Legal & Professional",
        "Management Fees",
        "Mortgage Interest",
        "Other Interest",
        "Repairs",
        "Supplies",
        "Taxes",
        "Utilities",
        "Depreciation",
        "Other",
    ]

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rental_properties(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """List all accounts flagged as rental properties."""
        conditions = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.is_rental_property.is_(True),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await self.db.execute(
            select(Account).where(and_(*conditions)).order_by(Account.name)
        )
        accounts = result.scalars().all()

        return [
            {
                "account_id": str(a.id),
                "name": a.name,
                "current_value": float(a.current_balance or 0),
                "rental_monthly_income": float(a.rental_monthly_income or 0),
                "rental_address": a.rental_address or "",
                "property_type": a.property_type.value if a.property_type else None,
                "user_id": str(a.user_id),
            }
            for a in accounts
        ]

    async def get_property_pnl(
        self,
        organization_id: UUID,
        account_id: UUID,
        year: int,
    ) -> Dict[str, Any]:
        """Get P&L for a rental property for a given year.

        Income: positive-amount transactions linked to the account.
        Expenses: negative-amount transactions linked to the account.
        Groups expenses by their custom category name, mapping to the nearest
        Schedule E category when possible.
        """
        # Verify the account belongs to this org and is a rental
        acct_result = await self.db.execute(
            select(Account).where(
                and_(
                    Account.id == account_id,
                    Account.organization_id == organization_id,
                    Account.is_active.is_(True),
                )
            )
        )
        account = acct_result.scalar_one_or_none()
        if account is None:
            return {"error": "Account not found"}

        # Fetch transactions for the year
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        txn_result = await self.db.execute(
            select(Transaction, Category.name.label("category_name"))
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.organization_id == organization_id,
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                    Transaction.is_pending.is_(False),
                )
            )
            .order_by(Transaction.date)
        )
        rows = txn_result.all()

        # Separate income vs expenses and build monthly breakdown
        gross_income = Decimal("0")
        total_expenses = Decimal("0")
        expense_by_category: Dict[str, Decimal] = defaultdict(Decimal)
        monthly_income: Dict[int, Decimal] = defaultdict(Decimal)
        monthly_expenses: Dict[int, Decimal] = defaultdict(Decimal)

        for txn, cat_name in rows:
            month = txn.date.month
            amount = txn.amount or Decimal("0")

            if amount > 0:
                # Income (rent payments, etc.)
                gross_income += amount
                monthly_income[month] += amount
            else:
                # Expense (negative amount)
                abs_amount = abs(amount)
                total_expenses += abs_amount
                monthly_expenses[month] += abs_amount
                category_label = cat_name or "Other"
                expense_by_category[category_label] += abs_amount

        net_income = gross_income - total_expenses

        # Cap rate: net_income / property_value * 100
        property_value = Decimal(str(account.current_balance or 0))
        cap_rate = float(net_income / property_value * 100) if property_value > 0 else 0.0

        # Build monthly breakdown (all 12 months)
        monthly_data = []
        for m in range(1, 13):
            monthly_data.append(
                {
                    "month": m,
                    "income": float(monthly_income.get(m, Decimal("0"))),
                    "expenses": float(monthly_expenses.get(m, Decimal("0"))),
                    "net": float(
                        monthly_income.get(m, Decimal("0")) - monthly_expenses.get(m, Decimal("0"))
                    ),
                }
            )

        # Build expense breakdown (Schedule E style)
        expense_breakdown = [
            {"category": cat, "amount": float(amt)}
            for cat, amt in sorted(expense_by_category.items(), key=lambda x: -x[1])
        ]

        return {
            "account_id": str(account_id),
            "name": account.name,
            "rental_address": account.rental_address or "",
            "current_value": float(property_value),
            "year": year,
            "gross_income": float(gross_income),
            "total_expenses": float(total_expenses),
            "net_income": float(net_income),
            "cap_rate": cap_rate,
            "expense_breakdown": expense_breakdown,
            "monthly": monthly_data,
        }

    async def get_all_properties_summary(
        self,
        organization_id: UUID,
        year: int,
        user_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Summary across all rental properties for a given year."""
        properties = await self.get_rental_properties(organization_id, user_id)

        total_income = Decimal("0")
        total_expenses = Decimal("0")
        total_value = Decimal("0")
        property_summaries = []

        for prop in properties:
            pnl = await self.get_property_pnl(organization_id, UUID(prop["account_id"]), year)
            if "error" in pnl:
                continue

            prop_income = Decimal(str(pnl["gross_income"]))
            prop_expenses = Decimal(str(pnl["total_expenses"]))
            prop_value = Decimal(str(pnl["current_value"]))

            total_income += prop_income
            total_expenses += prop_expenses
            total_value += prop_value

            property_summaries.append(
                {
                    "account_id": prop["account_id"],
                    "name": pnl["name"],
                    "rental_address": pnl["rental_address"],
                    "current_value": pnl["current_value"],
                    "rental_monthly_income": prop["rental_monthly_income"],
                    "gross_income": pnl["gross_income"],
                    "total_expenses": pnl["total_expenses"],
                    "net_income": pnl["net_income"],
                    "cap_rate": pnl["cap_rate"],
                }
            )

        total_net = total_income - total_expenses
        avg_cap_rate = float(total_net / total_value * 100) if total_value > 0 else 0.0

        return {
            "year": year,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "total_net_income": float(total_net),
            "average_cap_rate": avg_cap_rate,
            "property_count": len(property_summaries),
            "properties": property_summaries,
        }

    async def update_rental_fields(
        self,
        organization_id: UUID,
        account_id: UUID,
        is_rental_property: Optional[bool] = None,
        rental_monthly_income: Optional[Decimal] = None,
        rental_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update rental-specific fields on an account."""
        result = await self.db.execute(
            select(Account).where(
                and_(
                    Account.id == account_id,
                    Account.organization_id == organization_id,
                    Account.is_active.is_(True),
                )
            )
        )
        account = result.scalar_one_or_none()
        if account is None:
            return {"error": "Account not found"}

        if is_rental_property is not None:
            account.is_rental_property = is_rental_property
        if rental_monthly_income is not None:
            account.rental_monthly_income = rental_monthly_income
        if rental_address is not None:
            account.rental_address = rental_address

        await self.db.commit()
        await self.db.refresh(account)

        return {
            "account_id": str(account.id),
            "name": account.name,
            "is_rental_property": account.is_rental_property,
            "rental_monthly_income": float(account.rental_monthly_income or 0),
            "rental_address": account.rental_address or "",
        }
