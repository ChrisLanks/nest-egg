"""Service for tax-deductible transaction tracking and reporting."""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID
import csv
import io

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionLabel, Label
from app.models.account import Account


class TaxDeductibleSummary:
    """Tax-deductible summary data."""

    def __init__(
        self,
        label_id: UUID,
        label_name: str,
        label_color: str,
        total_amount: Decimal,
        transaction_count: int,
        transactions: List[Dict],
    ):
        self.label_id = label_id
        self.label_name = label_name
        self.label_color = label_color
        self.total_amount = total_amount
        self.transaction_count = transaction_count
        self.transactions = transactions


class TaxService:
    """Service for tax-deductible transaction management."""

    # Default tax label definitions
    DEFAULT_TAX_LABELS = [
        {"name": "Medical & Dental", "color": "#48BB78", "is_income": False},
        {"name": "Charitable Donations", "color": "#4299E1", "is_income": False},
        {"name": "Business Expenses", "color": "#9F7AEA", "is_income": False},
        {"name": "Education", "color": "#ED8936", "is_income": False},
        {"name": "Home Office", "color": "#F56565", "is_income": False},
    ]

    @staticmethod
    async def initialize_tax_labels(db: AsyncSession, organization_id: UUID) -> List[Label]:
        """
        Create default tax-deductible labels for an organization.

        Idempotent - only creates labels that don't already exist.

        Args:
            db: Database session
            organization_id: Organization ID

        Returns:
            List of created or existing tax labels
        """
        created_labels = []

        for label_data in TaxService.DEFAULT_TAX_LABELS:
            # Check if label already exists
            result = await db.execute(
                select(Label).where(
                    and_(Label.organization_id == organization_id, Label.name == label_data["name"])
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                created_labels.append(existing)
            else:
                # Create new label
                label = Label(
                    organization_id=organization_id,
                    name=label_data["name"],
                    color=label_data["color"],
                    is_income=label_data["is_income"],
                    is_system=False,
                )
                db.add(label)
                created_labels.append(label)

        await db.commit()

        # Refresh all labels
        for label in created_labels:
            await db.refresh(label)

        return created_labels

    @staticmethod
    async def get_tax_deductible_summary(
        db: AsyncSession,
        organization_id: UUID,
        start_date: date,
        end_date: date,
        label_ids: Optional[List[UUID]] = None,
        user_id: Optional[UUID] = None,
    ) -> List[TaxDeductibleSummary]:
        """
        Get tax-deductible transactions grouped by label.

        Args:
            db: Database session
            organization_id: Organization ID
            start_date: Start date for tax period
            end_date: End date for tax period
            label_ids: Optional filter for specific tax labels
            user_id: Optional filter by user

        Returns:
            List of tax-deductible summaries grouped by label
        """
        # Only surface the 5 official tax-deductible labels, not arbitrary user labels
        tax_label_names = [label["name"] for label in TaxService.DEFAULT_TAX_LABELS]

        # Build base query for transactions with tax labels
        query = (
            select(
                Label.id.label("label_id"),
                Label.name.label("label_name"),
                Label.color.label("label_color"),
                func.sum(func.abs(Transaction.amount)).label("total_amount"),
                func.count(Transaction.id).label("transaction_count"),
            )
            .select_from(Transaction)
            .join(TransactionLabel, Transaction.id == TransactionLabel.transaction_id)
            .join(Label, TransactionLabel.label_id == Label.id)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                and_(
                    Account.organization_id == organization_id,
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                    Label.name.in_(tax_label_names),
                )
            )
        )

        # Apply label filter if provided
        if label_ids:
            query = query.where(Label.id.in_(label_ids))

        # Apply user filter if provided
        if user_id:
            query = query.where(Account.user_id == user_id)

        # Group by label
        query = query.group_by(Label.id, Label.name, Label.color)
        query = query.order_by(func.sum(func.abs(Transaction.amount)).desc())

        result = await db.execute(query)

        # Merge rows with the same label name — avoids showing duplicates when a
        # label was created both manually and via initialize (same name, different id).
        merged: dict = {}
        for row in result.all():
            name = row.label_name
            if name in merged:
                merged[name]["label_ids"].append(row.label_id)
                merged[name]["total_amount"] += row.total_amount
                merged[name]["transaction_count"] += row.transaction_count
            else:
                merged[name] = {
                    "label_id": row.label_id,
                    "label_ids": [row.label_id],
                    "label_name": row.label_name,
                    "label_color": row.label_color,
                    "total_amount": row.total_amount,
                    "transaction_count": row.transaction_count,
                }

        summaries = []
        for data in merged.values():
            transactions = await TaxService._get_transactions_for_label(
                db,
                organization_id,
                start_date,
                end_date,
                data["label_ids"],
                user_id,
            )

            summary = TaxDeductibleSummary(
                label_id=data["label_id"],
                label_name=data["label_name"],
                label_color=data["label_color"],
                total_amount=data["total_amount"],
                transaction_count=len(transactions),
                transactions=transactions,
            )
            summaries.append(summary)

        return summaries

    @staticmethod
    async def _get_transactions_for_label(
        db: AsyncSession,
        organization_id: UUID,
        start_date: date,
        end_date: date,
        label_ids: List[UUID],
        user_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Get deduplicated transaction list for one or more label IDs sharing the same name."""
        query = (
            select(
                Transaction.id,
                Transaction.date,
                Transaction.merchant_name,
                Transaction.description,
                Transaction.amount,
                Transaction.category_primary,
                Account.name.label("account_name"),
            )
            .distinct()
            .select_from(Transaction)
            .join(TransactionLabel, Transaction.id == TransactionLabel.transaction_id)
            .join(Account, Transaction.account_id == Account.id)
            .where(
                and_(
                    Account.organization_id == organization_id,
                    Transaction.date >= start_date,
                    Transaction.date <= end_date,
                    TransactionLabel.label_id.in_(label_ids),
                )
            )
        )

        if user_id:
            query = query.where(Account.user_id == user_id)

        query = query.order_by(Transaction.date.desc())

        result = await db.execute(query)
        transactions = []

        for row in result.all():
            transactions.append(
                {
                    "id": str(row.id),
                    "date": row.date.isoformat(),
                    "merchant_name": row.merchant_name,
                    "description": row.description or "",
                    "amount": float(abs(row.amount)),
                    "category": row.category_primary or "Uncategorized",
                    "account_name": row.account_name,
                }
            )

        return transactions

    @staticmethod
    async def generate_tax_export_csv(
        db: AsyncSession,
        organization_id: UUID,
        start_date: date,
        end_date: date,
        label_ids: Optional[List[UUID]] = None,
        user_id: Optional[UUID] = None,
    ) -> str:
        """
        Generate CSV export of tax-deductible transactions.

        Format: Date, Merchant, Description, Category, Tax Label, Amount, Account, Notes

        Args:
            db: Database session
            organization_id: Organization ID
            start_date: Start date for tax period
            end_date: End date for tax period
            label_ids: Optional filter for specific tax labels
            user_id: Optional filter by user

        Returns:
            CSV string formatted for tax software
        """
        # Get summaries with all transactions
        summaries = await TaxService.get_tax_deductible_summary(
            db, organization_id, start_date, end_date, label_ids, user_id
        )

        # Build CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(
            [
                "Date",
                "Merchant",
                "Description",
                "Category",
                "Tax Label",
                "Amount",
                "Account",
                "Notes",
            ]
        )

        # Data rows
        for summary in summaries:
            for transaction in summary.transactions:
                writer.writerow(
                    [
                        transaction["date"],
                        transaction["merchant_name"],
                        transaction["description"],
                        transaction["category"],
                        summary.label_name,
                        f"${transaction['amount']:.2f}",
                        transaction["account_name"],
                        "",  # Notes column for user's manual entries
                    ]
                )

        return output.getvalue()


tax_service = TaxService()
