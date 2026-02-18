"""Service for multi-year trend analysis and year-over-year comparisons."""

from datetime import date
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.account import Account


class TrendAnalysisService:
    """Service for analyzing spending trends across multiple years."""

    @staticmethod
    async def get_year_over_year_comparison(
        db: AsyncSession,
        organization_id: UUID,
        years: List[int],
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> List[Dict]:
        """
        Get side-by-side monthly comparison across multiple years.

        Args:
            db: Database session
            organization_id: Organization ID
            years: List of years to compare (e.g., [2024, 2023, 2022])
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            List of monthly data points with income/expenses for each year:
            [
                {
                    "month": 1,  # January
                    "month_name": "January",
                    "data": {
                        "2024": {"income": 5000, "expenses": 3000, "net": 2000},
                        "2023": {"income": 4800, "expenses": 2900, "net": 1900},
                        ...
                    }
                },
                ...
            ]
        """
        # Build base query conditions
        conditions = [
            Transaction.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        # Add year filter
        conditions.append(extract("year", Transaction.date).in_(years))

        # Query to get monthly data for all years
        result = await db.execute(
            select(
                extract("year", Transaction.date).label("year"),
                extract("month", Transaction.date).label("month"),
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(extract("year", Transaction.date), extract("month", Transaction.date))
            .order_by(extract("month", Transaction.date), extract("year", Transaction.date))
        )

        # Organize data by month
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        # Initialize structure for all 12 months
        monthly_data = {}
        for month_num in range(1, 13):
            monthly_data[month_num] = {
                "month": month_num,
                "month_name": month_names[month_num - 1],
                "data": {},
            }

        # Populate with actual data
        for row in result.all():
            year = int(row.year)
            month = int(row.month)
            income = float(row.income or 0)
            expenses = abs(float(row.expenses or 0))

            monthly_data[month]["data"][str(year)] = {
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            }

        # Fill in missing years with zeros
        for month_num in range(1, 13):
            for year in years:
                year_str = str(year)
                if year_str not in monthly_data[month_num]["data"]:
                    monthly_data[month_num]["data"][year_str] = {
                        "income": 0,
                        "expenses": 0,
                        "net": 0,
                    }

        return list(monthly_data.values())

    @staticmethod
    async def get_quarterly_summary(
        db: AsyncSession,
        organization_id: UUID,
        years: List[int],
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> List[Dict]:
        """
        Get quarterly summary across multiple years.

        Args:
            db: Database session
            organization_id: Organization ID
            years: List of years to compare
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            List of quarterly data points:
            [
                {
                    "quarter": 1,
                    "quarter_name": "Q1",
                    "data": {
                        "2024": {"income": 15000, "expenses": 9000, "net": 6000},
                        "2023": {"income": 14400, "expenses": 8700, "net": 5700},
                        ...
                    }
                },
                ...
            ]
        """
        # Build base query conditions
        conditions = [
            Transaction.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        # Add year filter
        conditions.append(extract("year", Transaction.date).in_(years))

        # Query to get quarterly data
        result = await db.execute(
            select(
                extract("year", Transaction.date).label("year"),
                func.extract("quarter", Transaction.date).label("quarter"),
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(extract("year", Transaction.date), func.extract("quarter", Transaction.date))
            .order_by(func.extract("quarter", Transaction.date), extract("year", Transaction.date))
        )

        # Initialize structure for all 4 quarters
        quarterly_data = {}
        for quarter_num in range(1, 5):
            quarterly_data[quarter_num] = {
                "quarter": quarter_num,
                "quarter_name": f"Q{quarter_num}",
                "data": {},
            }

        # Populate with actual data
        for row in result.all():
            year = int(row.year)
            quarter = int(row.quarter)
            income = float(row.income or 0)
            expenses = abs(float(row.expenses or 0))

            quarterly_data[quarter]["data"][str(year)] = {
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            }

        # Fill in missing years with zeros
        for quarter_num in range(1, 5):
            for year in years:
                year_str = str(year)
                if year_str not in quarterly_data[quarter_num]["data"]:
                    quarterly_data[quarter_num]["data"][year_str] = {
                        "income": 0,
                        "expenses": 0,
                        "net": 0,
                    }

        return list(quarterly_data.values())

    @staticmethod
    async def get_category_trends(
        db: AsyncSession,
        organization_id: UUID,
        category: str,
        start_date: date,
        end_date: date,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> List[Dict]:
        """
        Get time-series trend for a specific category.

        Args:
            db: Database session
            organization_id: Organization ID
            category: Category name to analyze
            start_date: Start date for analysis
            end_date: End date for analysis
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            List of monthly data points:
            [
                {"month": "2024-01", "amount": 450.50, "count": 12},
                {"month": "2024-02", "amount": 523.75, "count": 15},
                ...
            ]
        """
        # Build base query conditions
        conditions = [
            Transaction.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.category_primary == category,
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        # Query monthly trend for category
        month_expr = func.date_trunc("month", Transaction.date)

        result = await db.execute(
            select(
                month_expr.label("month"),
                func.sum(func.abs(Transaction.amount)).label("amount"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(month_expr)
            .order_by(month_expr)
        )

        trends = []
        for row in result.all():
            trends.append(
                {
                    "month": row.month.strftime("%Y-%m") if row.month else "",
                    "amount": float(row.amount or 0),
                    "count": row.count,
                }
            )

        return trends

    @staticmethod
    def calculate_growth_rate(base_value: float, current_value: float) -> Optional[float]:
        """
        Calculate year-over-year growth rate percentage.

        Args:
            base_value: Previous period value
            current_value: Current period value

        Returns:
            Growth rate as percentage (e.g., 15.5 for 15.5% growth)
            None if base_value is 0
        """
        if base_value == 0:
            return None

        return ((current_value - base_value) / base_value) * 100

    @staticmethod
    def calculate_cagr(
        starting_value: float, ending_value: float, num_years: int
    ) -> Optional[float]:
        """
        Calculate Compound Annual Growth Rate (CAGR).

        Args:
            starting_value: Initial value
            ending_value: Final value
            num_years: Number of years

        Returns:
            CAGR as percentage (e.g., 12.5 for 12.5% annual growth)
            None if starting_value is 0 or num_years <= 0
        """
        if starting_value == 0 or num_years <= 0:
            return None

        return (pow(ending_value / starting_value, 1 / num_years) - 1) * 100

    @staticmethod
    async def get_annual_summary(
        db: AsyncSession,
        organization_id: UUID,
        year: int,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict:
        """
        Get annual summary for a single year.

        Args:
            db: Database session
            organization_id: Organization ID
            year: Year to summarize
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            {
                "year": 2024,
                "total_income": 60000,
                "total_expenses": 36000,
                "net": 24000,
                "avg_monthly_income": 5000,
                "avg_monthly_expenses": 3000,
                "peak_expense_month": "November",
                "peak_expense_amount": 4500
            }
        """
        # Build base query conditions
        conditions = [
            Transaction.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            extract("year", Transaction.date) == year,
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        # Get annual totals
        totals_result = await db.execute(
            select(
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
        )

        totals = totals_result.one()
        total_income = float(totals.income or 0)
        total_expenses = abs(float(totals.expenses or 0))

        # Get monthly breakdown to find peak month
        month_expr = extract("month", Transaction.date)
        monthly_result = await db.execute(
            select(
                month_expr.label("month"),
                func.sum(func.abs(Transaction.amount)).label("total"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions), Transaction.amount < 0)  # Only expenses
            .group_by(month_expr)
            .order_by(func.sum(func.abs(Transaction.amount)).desc())
            .limit(1)
        )

        peak_month_row = monthly_result.one_or_none()
        month_names = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]

        if peak_month_row:
            peak_month = month_names[int(peak_month_row.month) - 1]
            peak_amount = float(peak_month_row.total or 0)
        else:
            peak_month = None
            peak_amount = 0

        # Count months with data to calculate averages
        months_with_data_result = await db.execute(
            select(func.count(func.distinct(extract("month", Transaction.date))))
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
        )
        months_with_data = months_with_data_result.scalar() or 12

        return {
            "year": year,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net": total_income - total_expenses,
            "avg_monthly_income": total_income / months_with_data if months_with_data > 0 else 0,
            "avg_monthly_expenses": (
                total_expenses / months_with_data if months_with_data > 0 else 0
            ),
            "peak_expense_month": peak_month,
            "peak_expense_amount": peak_amount,
        }
