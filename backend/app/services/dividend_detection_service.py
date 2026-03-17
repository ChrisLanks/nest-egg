"""Auto-detect dividend/investment income transactions from synced data.

Scans transaction descriptions and merchant names for dividend-related
keywords and automatically applies a system "Dividend Income" label.
Can also create DividendIncome records from detected transactions.
"""

import logging
import re
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Label, Transaction, TransactionLabel

logger = logging.getLogger(__name__)

# ── Keyword patterns for dividend detection ──────────────────────────────

# Primary patterns — high-confidence matches (case-insensitive).
# Each tuple: (compiled regex, detected income subtype hint).
_PRIMARY_PATTERNS: List[tuple[re.Pattern, str]] = [
    # Specific subtypes first (order matters — first match wins).
    (re.compile(r"\bnon-?qual\s+div", re.I), "dividend"),
    (re.compile(r"\bqualified\s+div", re.I), "qualified_dividend"),
    (re.compile(r"\bqual\s+div\b", re.I), "qualified_dividend"),
    (re.compile(r"\bdiv\s+reinv", re.I), "reinvested_dividend"),
    (re.compile(r"\breinvest\s+div", re.I), "reinvested_dividend"),
    (re.compile(r"\bdrip\b", re.I), "reinvested_dividend"),
    (re.compile(r"\bcapital\s+gain\s+dist", re.I), "capital_gain_distribution"),
    (re.compile(r"\bcap\s*gain\s+dist", re.I), "capital_gain_distribution"),
    (re.compile(r"\blt\s+cap\s+gain\b", re.I), "capital_gain_distribution"),
    (re.compile(r"\bst\s+cap\s+gain\b", re.I), "capital_gain_distribution"),
    (re.compile(r"\breturn\s+of\s+cap", re.I), "return_of_capital"),
    (re.compile(r"\bbond\s+int(erest)?\b", re.I), "interest"),
    (re.compile(r"\binterest\s+payment\b", re.I), "interest"),
    (re.compile(r"\bint\s+income\b", re.I), "interest"),
    (re.compile(r"\bmoney\s+market\s+(int|income)", re.I), "interest"),
    # Generic dividend patterns last (catch-all).
    (re.compile(r"\bcash\s+div\b", re.I), "dividend"),
    (re.compile(r"\bord(inary)?\s+div", re.I), "dividend"),
    (re.compile(r"\bdiv\s+payment\b", re.I), "dividend"),
    (re.compile(r"\bforeign\s+tax\s+w/h", re.I), "dividend"),
    (re.compile(r"\bfed\s+tax\s+w/h.*div", re.I), "dividend"),
    (re.compile(r"\bdividend\b", re.I), "dividend"),
]

# Provider category hints — Plaid/Teller/MX sometimes tag these.
_CATEGORY_KEYWORDS = {
    "dividend",
    "dividends",
    "interest",
    "investment income",
    "investment_income",
}

# System label name used for auto-detected dividends.
DIVIDEND_LABEL_NAME = "Dividend Income"


def detect_dividend(transaction: Transaction) -> Optional[str]:
    """Check if a transaction looks like dividend/investment income.

    Returns the income subtype hint string if matched, or None.
    Examines description, merchant_name, category_primary, and
    category_detailed fields.
    """
    # Build a combined text blob for matching.
    parts = [
        transaction.description or "",
        transaction.merchant_name or "",
    ]
    text = " ".join(parts)

    for pattern, subtype in _PRIMARY_PATTERNS:
        if pattern.search(text):
            return subtype

    # Fall back to provider-supplied category keywords.
    for cat_field in (transaction.category_primary, transaction.category_detailed):
        if cat_field and cat_field.lower().strip() in _CATEGORY_KEYWORDS:
            return "dividend"

    return None


class DividendDetectionService:
    """Scans transactions and auto-applies the "Dividend Income" label."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Label management ─────────────────────────────────────────────────

    async def ensure_system_label(self, organization_id: UUID) -> Label:
        """Get or create the system "Dividend Income" label for an org."""
        result = await self.db.execute(
            select(Label).where(
                and_(
                    Label.organization_id == organization_id,
                    Label.name == DIVIDEND_LABEL_NAME,
                )
            )
        )
        label = result.scalar_one_or_none()
        if label:
            return label

        label = Label(
            organization_id=organization_id,
            name=DIVIDEND_LABEL_NAME,
            color="#22c55e",  # Green
            is_income=True,
            is_system=True,
        )
        self.db.add(label)
        await self.db.flush()
        return label

    # ── Single transaction ───────────────────────────────────────────────

    async def process_transaction(
        self,
        transaction: Transaction,
        label: Optional[Label] = None,
    ) -> Optional[str]:
        """Detect and label a single transaction as dividend income.

        Returns the subtype hint if the transaction was labeled, else None.
        Does NOT commit — caller is responsible for committing.
        """
        subtype = detect_dividend(transaction)
        if subtype is None:
            return None

        if label is None:
            label = await self.ensure_system_label(transaction.organization_id)

        # Avoid duplicate label application.
        existing = await self.db.execute(
            select(TransactionLabel.id).where(
                and_(
                    TransactionLabel.transaction_id == transaction.id,
                    TransactionLabel.label_id == label.id,
                )
            )
        )
        if existing.scalar_one_or_none() is not None:
            return subtype  # Already labeled

        txn_label = TransactionLabel(
            transaction_id=transaction.id,
            label_id=label.id,
        )
        self.db.add(txn_label)
        logger.info(
            "Auto-labeled transaction %s as %s (%s)",
            transaction.id,
            DIVIDEND_LABEL_NAME,
            subtype,
        )
        return subtype

    # ── Batch: process newly synced transactions ─────────────────────────

    async def process_batch(
        self,
        transactions: List[Transaction],
        organization_id: UUID,
    ) -> int:
        """Process a list of transactions, labeling any that match.

        Returns the number of transactions that were labeled.
        Does NOT commit — caller is responsible.
        """
        if not transactions:
            return 0

        label = await self.ensure_system_label(organization_id)

        # Pre-fetch existing labels to avoid N+1.
        txn_ids = [t.id for t in transactions if t.id is not None]
        if txn_ids:
            existing_result = await self.db.execute(
                select(TransactionLabel.transaction_id).where(
                    and_(
                        TransactionLabel.transaction_id.in_(txn_ids),
                        TransactionLabel.label_id == label.id,
                    )
                )
            )
            already_labeled = {row[0] for row in existing_result.all()}
        else:
            already_labeled = set()

        count = 0
        for txn in transactions:
            subtype = detect_dividend(txn)
            if subtype is None:
                continue
            if txn.id in already_labeled:
                continue

            txn_label = TransactionLabel(
                transaction_id=txn.id,
                label_id=label.id,
            )
            self.db.add(txn_label)
            count += 1
            logger.debug(
                "Batch-labeled txn %s as %s (%s)",
                txn.id,
                DIVIDEND_LABEL_NAME,
                subtype,
            )

        if count > 0:
            logger.info(
                "Auto-labeled %d/%d transactions as dividend income",
                count,
                len(transactions),
            )
        return count

    # ── Backfill: scan existing transactions for an org ──────────────────

    async def backfill_organization(
        self,
        organization_id: UUID,
        batch_size: int = 500,
    ) -> int:
        """Scan all unlabeled transactions in an org and label matches.

        Processes in batches and commits after each batch.
        Returns total number of newly labeled transactions.
        """
        await self.ensure_system_label(organization_id)
        total = 0
        offset = 0

        while True:
            result = await self.db.execute(
                select(Transaction)
                .where(Transaction.organization_id == organization_id)
                .order_by(Transaction.id)
                .limit(batch_size)
                .offset(offset)
            )
            transactions = list(result.scalars().all())
            if not transactions:
                break

            count = await self.process_batch(transactions, organization_id)
            total += count
            offset += batch_size

            if count > 0:
                await self.db.flush()

        return total
