"""Service for importing transactions from CSV files."""

import csv
import hashlib
import io
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.account import Account
from app.models.user import User


class CSVImportService:
    """Service for importing transactions from CSV files."""

    # Common CSV column name variations
    DATE_COLUMNS = ["date", "transaction date", "posting date", "trans date", "Date"]
    AMOUNT_COLUMNS = ["amount", "value", "transaction amount", "debit", "credit", "Amount"]
    DESCRIPTION_COLUMNS = ["description", "memo", "narrative", "details", "Description", "Memo"]
    MERCHANT_COLUMNS = ["merchant", "payee", "merchant name", "description", "Merchant"]

    @staticmethod
    def _detect_column_mapping(
        headers: List[str],
    ) -> Dict[str, Optional[str]]:
        """
        Auto-detect column mapping from CSV headers.

        Returns:
            Dict mapping canonical names (date, amount, description, merchant) to actual column names
        """
        headers_lower = {h.lower(): h for h in headers}

        mapping = {
            "date": None,
            "amount": None,
            "description": None,
            "merchant": None,
        }

        # Detect date column
        for col in CSVImportService.DATE_COLUMNS:
            if col.lower() in headers_lower:
                mapping["date"] = headers_lower[col.lower()]
                break

        # Detect amount column
        for col in CSVImportService.AMOUNT_COLUMNS:
            if col.lower() in headers_lower:
                mapping["amount"] = headers_lower[col.lower()]
                break

        # Detect description column
        for col in CSVImportService.DESCRIPTION_COLUMNS:
            if col.lower() in headers_lower:
                mapping["description"] = headers_lower[col.lower()]
                break

        # Detect merchant column
        for col in CSVImportService.MERCHANT_COLUMNS:
            if col.lower() in headers_lower:
                mapping["merchant"] = headers_lower[col.lower()]
                break

        return mapping

    @staticmethod
    def _parse_date(date_str: str) -> Optional[date]:
        """Parse date from various formats."""
        date_formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%m/%d/%y",
            "%d/%m/%y",
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def _parse_amount(amount_str: str) -> Optional[Decimal]:
        """Parse amount from string, handling various formats."""
        if not amount_str:
            return None

        # Remove currency symbols, commas, spaces
        cleaned = amount_str.strip().replace("$", "").replace(",", "").replace(" ", "")

        # Handle parentheses for negative (accounting format)
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]

        try:
            return Decimal(cleaned)
        except Exception:
            return None

    @staticmethod
    def _generate_deduplication_hash(
        account_id: UUID,
        txn_date: date,
        amount: Decimal,
        description: str,
    ) -> str:
        """Generate deduplication hash for transaction."""
        hash_input = f"{account_id}|{txn_date}|{amount}|{description or ''}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    @staticmethod
    async def preview_csv(
        csv_content: str,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Preview CSV file and return sample data with detected columns.

        Args:
            csv_content: CSV file content as string
            column_mapping: Optional manual column mapping

        Returns:
            Dict with detected columns, sample rows, and stats
        """
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        headers = reader.fieldnames or []

        # Auto-detect columns if not provided
        if not column_mapping:
            column_mapping = CSVImportService._detect_column_mapping(headers)

        # Preview first 5 rows
        preview_rows = []
        for i, row in enumerate(reader):
            if i >= 5:
                break

            parsed_row = {
                "date": CSVImportService._parse_date(row.get(column_mapping.get("date", ""), "")),
                "amount": CSVImportService._parse_amount(row.get(column_mapping.get("amount", ""), "")),
                "description": row.get(column_mapping.get("description", ""), ""),
                "merchant": row.get(column_mapping.get("merchant", ""), ""),
                "raw": row,
            }
            preview_rows.append(parsed_row)

        # Count total rows
        csv_file.seek(0)
        next(csv.reader(csv_file))  # Skip header
        total_rows = sum(1 for _ in csv.reader(csv_file))

        return {
            "headers": headers,
            "detected_mapping": column_mapping,
            "preview_rows": preview_rows,
            "total_rows": total_rows,
        }

    @staticmethod
    async def import_csv(
        db: AsyncSession,
        user: User,
        account_id: UUID,
        csv_content: str,
        column_mapping: Dict[str, str],
        skip_duplicates: bool = True,
    ) -> Dict[str, Any]:
        """
        Import transactions from CSV file.

        Args:
            db: Database session
            user: Current user
            account_id: Account to import transactions into
            csv_content: CSV file content as string
            column_mapping: Column mapping (date, amount, description, merchant)
            skip_duplicates: Skip transactions that already exist

        Returns:
            Dict with import stats (imported, skipped, errors)
        """
        # Validate account exists
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.id == account_id,
                    Account.organization_id == user.organization_id,
                )
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise ValueError("Account not found")

        # Parse CSV
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        imported = 0
        skipped = 0
        errors = []

        for i, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            try:
                # Parse fields
                txn_date = CSVImportService._parse_date(row.get(column_mapping.get("date", ""), ""))
                amount = CSVImportService._parse_amount(row.get(column_mapping.get("amount", ""), ""))
                description = row.get(column_mapping.get("description", ""), "")
                merchant = row.get(column_mapping.get("merchant", ""), "")

                # Validate required fields
                if not txn_date:
                    errors.append(f"Row {i}: Invalid or missing date")
                    continue
                if amount is None:
                    errors.append(f"Row {i}: Invalid or missing amount")
                    continue

                # Generate deduplication hash
                dedup_hash = CSVImportService._generate_deduplication_hash(
                    account_id,
                    txn_date,
                    amount,
                    description,
                )

                # Check for duplicate
                if skip_duplicates:
                    existing_result = await db.execute(
                        select(Transaction).where(
                            Transaction.deduplication_hash == dedup_hash
                        )
                    )
                    if existing_result.scalar_one_or_none():
                        skipped += 1
                        continue

                # Create transaction
                transaction = Transaction(
                    organization_id=user.organization_id,
                    account_id=account_id,
                    date=txn_date,
                    amount=amount,
                    description=description,
                    merchant_name=merchant or None,
                    deduplication_hash=dedup_hash,
                    is_pending=False,
                )

                db.add(transaction)
                imported += 1

                # Commit in batches of 100
                if imported % 100 == 0:
                    await db.commit()

            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        # Final commit
        await db.commit()

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "total_processed": imported + skipped + len(errors),
        }

    @staticmethod
    def validate_csv_format(
        csv_content: str,
    ) -> Dict[str, Any]:
        """
        Validate CSV format and return any errors.

        Returns:
            Dict with is_valid flag and error messages
        """
        errors = []

        try:
            csv_file = io.StringIO(csv_content)
            reader = csv.DictReader(csv_file)

            headers = reader.fieldnames
            if not headers:
                errors.append("CSV file has no headers")
                return {"is_valid": False, "errors": errors}

            # Check if we can detect required columns
            mapping = CSVImportService._detect_column_mapping(headers)

            if not mapping.get("date"):
                errors.append("Could not detect date column. Please specify manually.")
            if not mapping.get("amount"):
                errors.append("Could not detect amount column. Please specify manually.")

            # Try to read first row
            try:
                first_row = next(reader)
            except StopIteration:
                errors.append("CSV file is empty (no data rows)")

        except Exception as e:
            errors.append(f"Failed to parse CSV: {str(e)}")

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
        }


csv_import_service = CSVImportService()
