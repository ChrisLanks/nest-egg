"""Service for custom report execution and management."""

import csv
import io
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.report_template import ReportTemplate


class ReportService:
    """Service for executing and managing custom reports."""

    @staticmethod
    async def execute_report(
        db: AsyncSession,
        organization_id: UUID,
        config: Dict[str, Any],
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a report based on configuration.

        Args:
            db: Database session
            organization_id: Organization ID
            config: Report configuration dict
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            Report result with data and metadata
        """
        # Parse date range
        start_date, end_date = ReportService._parse_date_range(config.get("dateRange", {}))

        # Get grouping configuration
        group_by = config.get("groupBy", "category")
        time_grouping = config.get("timeGrouping", "monthly")

        # Get filters
        filters = config.get("filters", {})
        transaction_type = filters.get("transactionType", "both")

        # Build base query conditions
        conditions = [
            Transaction.organization_id == organization_id,
            Account.is_active.is_(True),
            Account.exclude_from_cash_flow.is_(False),
            Transaction.is_transfer.is_(False),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
        ]

        if user_id:
            conditions.append(Account.user_id == user_id)

        if account_ids:
            conditions.append(Transaction.account_id.in_(account_ids))

        # Add transaction type filter
        if transaction_type == "income":
            conditions.append(Transaction.amount > 0)
        elif transaction_type == "expense":
            conditions.append(Transaction.amount < 0)

        # Add amount filters
        if filters.get("minAmount"):
            conditions.append(func.abs(Transaction.amount) >= Decimal(str(filters["minAmount"])))
        if filters.get("maxAmount"):
            conditions.append(func.abs(Transaction.amount) <= Decimal(str(filters["maxAmount"])))

        # Execute query based on grouping
        if group_by == "time":
            result_data = await ReportService._execute_time_grouped_query(
                db, conditions, time_grouping
            )
        elif group_by == "category":
            result_data = await ReportService._execute_category_query(db, conditions, config)
        elif group_by == "merchant":
            result_data = await ReportService._execute_merchant_query(db, conditions, config)
        elif group_by == "account":
            result_data = await ReportService._execute_account_query(db, conditions, config)
        else:
            result_data = []

        # Calculate summary metrics
        metrics = ReportService._calculate_metrics(result_data, config.get("metrics", ["sum"]))

        return {
            "data": result_data,
            "metrics": metrics,
            "config": config,
            "dateRange": {
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat(),
            },
        }

    @staticmethod
    def _parse_date_range(date_range_config: Dict) -> tuple[date, date]:
        """Parse date range from config."""
        range_type = date_range_config.get("type", "custom")

        if range_type == "preset":
            preset = date_range_config.get("preset", "last_30_days")
            today = date.today()

            if preset == "last_30_days":
                return today - timedelta(days=30), today
            elif preset == "last_90_days":
                return today - timedelta(days=90), today
            elif preset == "this_month":
                return date(today.year, today.month, 1), today
            elif preset == "this_year":
                return date(today.year, 1, 1), today
            elif preset == "last_year":
                return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
            else:
                return today - timedelta(days=30), today
        else:
            # Custom date range
            start_str = date_range_config.get("startDate")
            end_str = date_range_config.get("endDate")

            start_date = (
                datetime.fromisoformat(start_str).date()
                if start_str
                else date.today() - timedelta(days=30)
            )
            end_date = datetime.fromisoformat(end_str).date() if end_str else date.today()

            return start_date, end_date

    @staticmethod
    async def _execute_time_grouped_query(
        db: AsyncSession, conditions: List, time_grouping: str
    ) -> List[Dict]:
        """Execute query grouped by time period."""
        # Determine time truncation based on grouping
        if time_grouping == "daily":
            date_expr = func.date(Transaction.date)
        elif time_grouping == "weekly":
            date_expr = func.date_trunc("week", Transaction.date)
        elif time_grouping == "quarterly":
            date_expr = func.date_trunc("quarter", Transaction.date)
        elif time_grouping == "yearly":
            date_expr = func.date_trunc("year", Transaction.date)
        else:  # monthly
            date_expr = func.date_trunc("month", Transaction.date)

        result = await db.execute(
            select(
                date_expr.label("period"),
                func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label(
                    "income"
                ),
                func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label(
                    "expenses"
                ),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(date_expr)
            .order_by(date_expr)
        )

        data = []
        for row in result.all():
            period_str = row.period.strftime("%Y-%m-%d") if row.period else ""
            income = float(row.income or 0)
            expenses = abs(float(row.expenses or 0))

            data.append(
                {
                    "name": period_str,
                    "income": income,
                    "expenses": expenses,
                    "net": income - expenses,
                    "count": row.count,
                }
            )

        return data

    @staticmethod
    async def _execute_category_query(
        db: AsyncSession, conditions: List, config: Dict
    ) -> List[Dict]:
        """Execute query grouped by category."""
        sort_by = config.get("sortBy", "amount")
        sort_direction = config.get("sortDirection", "desc")
        limit = config.get("limit", 20)

        sort_col = (
            func.count(Transaction.id) if sort_by == "count"
            else func.sum(func.abs(Transaction.amount))
        )

        result = await db.execute(
            select(
                Transaction.category_primary,
                func.sum(func.abs(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions), Transaction.category_primary.isnot(None))
            .group_by(Transaction.category_primary)
            .order_by(
                sort_col.desc() if sort_direction == "desc" else sort_col.asc()
            )
            .limit(limit)
        )

        data = []
        total_sum = 0
        for row in result.all():
            amount = float(row.total or 0)
            total_sum += amount

            data.append(
                {
                    "name": row.category_primary or "Uncategorized",
                    "amount": amount,
                    "count": row.count,
                }
            )

        # Calculate percentages
        for item in data:
            item["percentage"] = (item["amount"] / total_sum * 100) if total_sum > 0 else 0

        return data

    @staticmethod
    async def _execute_merchant_query(
        db: AsyncSession, conditions: List, config: Dict
    ) -> List[Dict]:
        """Execute query grouped by merchant."""
        limit = config.get("limit", 20)

        result = await db.execute(
            select(
                Transaction.merchant_name,
                func.sum(func.abs(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions), Transaction.merchant_name.isnot(None))
            .group_by(Transaction.merchant_name)
            .order_by(func.sum(func.abs(Transaction.amount)).desc())
            .limit(limit)
        )

        data = []
        for row in result.all():
            data.append(
                {
                    "name": row.merchant_name or "Unknown",
                    "amount": float(row.total or 0),
                    "count": row.count,
                }
            )

        return data

    @staticmethod
    async def _execute_account_query(
        db: AsyncSession, conditions: List, config: Dict
    ) -> List[Dict]:
        """Execute query grouped by account."""
        result = await db.execute(
            select(
                Account.name,
                func.sum(func.abs(Transaction.amount)).label("total"),
                func.count(Transaction.id).label("count"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(Account.name)
            .order_by(func.sum(func.abs(Transaction.amount)).desc())
        )

        data = []
        for row in result.all():
            data.append(
                {
                    "name": row.name,
                    "amount": float(row.total or 0),
                    "count": row.count,
                }
            )

        return data

    @staticmethod
    def _calculate_metrics(data: List[Dict], metrics: List[str]) -> Dict:
        """Calculate summary metrics for report data."""
        result = {}

        if not data:
            return result

        amounts = [item.get("amount", 0) for item in data]
        counts = [item.get("count", 0) for item in data]

        if "sum" in metrics:
            result["total_amount"] = sum(amounts)

        if "average" in metrics:
            result["average_amount"] = sum(amounts) / len(amounts) if amounts else 0

        if "count" in metrics:
            result["total_transactions"] = sum(counts)
            result["total_items"] = len(data)

        return result

    @staticmethod
    async def generate_export_csv(
        db: AsyncSession,
        organization_id: UUID,
        template_id: UUID,
        user_id: Optional[UUID] = None,
        account_ids: Optional[List[UUID]] = None,
    ) -> str:
        """
        Generate CSV export from a saved template.

        Args:
            db: Database session
            organization_id: Organization ID
            template_id: Report template ID
            user_id: Optional user ID for filtering
            account_ids: Optional list of account IDs for filtering

        Returns:
            CSV string
        """
        # Load template
        result = await db.execute(
            select(ReportTemplate).where(
                and_(
                    ReportTemplate.id == template_id,
                    ReportTemplate.organization_id == organization_id,
                )
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Report template {template_id} not found")

        # Execute report
        report_result = await ReportService.execute_report(
            db,
            organization_id,
            template.config,
            user_id,
            account_ids,
        )

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        data = report_result.get("data", [])
        if data:
            headers = list(data[0].keys())
            writer.writerow(headers)

            # Data rows
            for row in data:
                writer.writerow([row.get(header, "") for header in headers])

        return output.getvalue()
