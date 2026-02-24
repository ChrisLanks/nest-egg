"""Account provider migration service.

Safely migrates accounts between providers (Plaid, Teller, MX, Manual)
while preserving all downstream data (transactions, holdings, contributions, etc.).

CRITICAL: Provider models (PlaidItem, TellerEnrollment, MxMember) use
cascade="all, delete-orphan" on their accounts relationship. Simply NULLing
the FK via ORM would trigger orphan deletion, destroying the account and all
its data. This service uses Core-level SQL UPDATEs to bypass ORM relationship
tracking when changing provider FKs.
"""

import hashlib
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.datetime_utils import utc_now

from app.models.account import (
    Account,
    AccountSource,
    AccountType,
    PlaidItem,
    TellerEnrollment,
    MxMember,
)
from app.models.transaction import Transaction
from app.models.holding import Holding
from app.models.contribution import AccountContribution
from app.models.account_migration import AccountMigrationLog, MigrationStatus
from app.models.user import User
from app.services.deduplication_service import DeduplicationService

logger = logging.getLogger(__name__)
deduplication_service = DeduplicationService()


class MigrationError(Exception):
    """Raised when a migration cannot proceed."""

    pass


class AccountMigrationService:
    """Service for migrating accounts between providers."""

    async def migrate_account(
        self,
        db: AsyncSession,
        account_id: UUID,
        user: User,
        target_source: AccountSource,
        target_enrollment_id: Optional[UUID] = None,
        target_external_account_id: Optional[str] = None,
    ) -> AccountMigrationLog:
        """Migrate an account from its current provider to a target provider.

        Args:
            db: Database session
            account_id: The account to migrate
            user: The user initiating the migration
            target_source: The target provider (PLAID, TELLER, MX, MANUAL)
            target_enrollment_id: Required when target is a linked provider.
                The PlaidItem.id, TellerEnrollment.id, or MxMember.id to link to.
            target_external_account_id: The new provider's external account ID.
                Required for linked providers, ignored for MANUAL.

        Returns:
            AccountMigrationLog record

        Raises:
            MigrationError: If validation fails or migration cannot proceed
        """
        # 1. Load the account
        account = await self._load_account(db, account_id, user.organization_id)

        # 2. Capture immutable fields BEFORE any expire/refresh
        #    (accessing ORM attributes after expire triggers sync lazy-load which
        #    fails in async context)
        acct_id = account.id
        org_id = account.organization_id
        source_value = account.account_source.value
        old_external_id = account.external_account_id
        acct_type = account.account_type
        institution_name = account.institution_name
        mask = account.mask
        name = account.name

        # 3. Validate the migration is allowed
        await self._validate_migration(
            db,
            account,
            target_source,
            target_enrollment_id,
            target_external_account_id,
        )

        # 4. Take pre-migration snapshot
        pre_snapshot = await self._take_snapshot(db, account, acct_id)

        # 5. Create the migration log entry
        migration_log = AccountMigrationLog(
            organization_id=org_id,
            account_id=acct_id,
            initiated_by_user_id=user.id,
            source_provider=source_value,
            target_provider=target_source.value,
            status=MigrationStatus.IN_PROGRESS,
            pre_migration_snapshot=pre_snapshot,
            target_enrollment_id=target_enrollment_id,
        )
        db.add(migration_log)
        await db.flush()

        try:
            # 6. Execute the migration (Core SQL — bypasses ORM orphan detection)
            await self._execute_migration(
                db,
                acct_id,
                old_external_id,
                target_source,
                target_enrollment_id,
                target_external_account_id,
            )

            # 7. Recalculate deduplication hash
            await self._recalculate_dedup_hash(
                db,
                acct_id,
                target_source,
                target_enrollment_id,
                target_external_account_id,
                acct_type,
                institution_name,
                mask,
                name,
            )

            # 8. Refresh the ORM object from DB
            await db.refresh(account)

            # 9. Take post-migration snapshot and finalize log
            post_snapshot = await self._take_snapshot(db, account, acct_id)
            migration_log.post_migration_snapshot = post_snapshot
            migration_log.status = MigrationStatus.COMPLETED
            migration_log.completed_at = utc_now()

            await db.flush()

            logger.info(
                "Account %s migrated from %s to %s by user %s",
                acct_id,
                source_value,
                target_source.value,
                user.id,
            )

            return migration_log

        except Exception as e:
            await db.rollback()
            # Write failure log in a clean transaction after rollback
            # so the audit record survives even though the migration failed.
            try:
                failure_log = AccountMigrationLog(
                    organization_id=org_id,
                    account_id=acct_id,
                    initiated_by_user_id=user.id,
                    source_provider=source_value,
                    target_provider=target_source.value,
                    status=MigrationStatus.FAILED,
                    error_message=str(e)[:2000],
                    pre_migration_snapshot=pre_snapshot,
                    target_enrollment_id=target_enrollment_id,
                    completed_at=utc_now(),
                )
                db.add(failure_log)
                await db.commit()
            except Exception:
                pass  # Don't fail the error handling if audit logging fails
            logger.error(
                "Migration failed for account %s: %s",
                acct_id,
                e,
                exc_info=True,
            )
            raise MigrationError(f"Migration failed: {e}") from e

    async def get_migration_history(
        self,
        db: AsyncSession,
        account_id: UUID,
        organization_id: UUID,
    ) -> list[AccountMigrationLog]:
        """Get migration history for an account."""
        result = await db.execute(
            select(AccountMigrationLog)
            .where(
                AccountMigrationLog.account_id == account_id,
                AccountMigrationLog.organization_id == organization_id,
            )
            .order_by(AccountMigrationLog.initiated_at.desc())
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------
    # Internal methods
    # -------------------------------------------------------------------

    async def _load_account(
        self,
        db: AsyncSession,
        account_id: UUID,
        organization_id: UUID,
    ) -> Account:
        """Load the account, verifying it exists and belongs to the org."""
        result = await db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.organization_id == organization_id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise MigrationError("Account not found")
        return account

    async def _validate_migration(
        self,
        db: AsyncSession,
        account: Account,
        target_source: AccountSource,
        target_enrollment_id: Optional[UUID],
        target_external_account_id: Optional[str],
    ) -> None:
        """Validate the migration is allowed."""
        if account.account_source == target_source:
            raise MigrationError(
                f"Account is already on {target_source.value}. "
                "Use the re-link flow to reconnect to the same provider."
            )

        if not account.is_active:
            raise MigrationError("Cannot migrate an inactive account")

        if target_source != AccountSource.MANUAL:
            if not target_enrollment_id:
                raise MigrationError(
                    f"target_enrollment_id is required when migrating to {target_source.value}"
                )
            if not target_external_account_id:
                raise MigrationError(
                    f"target_external_account_id is required when migrating to {target_source.value}"
                )

            enrollment = await self._verify_enrollment(
                db,
                target_source,
                target_enrollment_id,
                account.organization_id,
            )
            if not enrollment:
                raise MigrationError(
                    f"Target enrollment {target_enrollment_id} not found "
                    "or does not belong to this organization"
                )

    async def _verify_enrollment(
        self,
        db: AsyncSession,
        target_source: AccountSource,
        enrollment_id: UUID,
        organization_id: UUID,
    ):
        """Verify the target enrollment exists and belongs to the org."""
        model_map = {
            AccountSource.PLAID: PlaidItem,
            AccountSource.TELLER: TellerEnrollment,
            AccountSource.MX: MxMember,
        }
        model = model_map.get(target_source)
        if not model:
            raise MigrationError(f"Unknown target source: {target_source}")

        result = await db.execute(
            select(model).where(
                model.id == enrollment_id,
                model.organization_id == organization_id,
            )
        )
        return result.scalar_one_or_none()

    async def _take_snapshot(
        self,
        db: AsyncSession,
        account: Account,
        account_id: UUID,
    ) -> dict:
        """Take a snapshot of the account's provider-related state."""
        tx_count = await db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.account_id == account_id)
        )
        holdings_count = await db.scalar(
            select(func.count())
            .select_from(Holding)
            .where(Holding.account_id == account_id)
        )
        contrib_count = await db.scalar(
            select(func.count())
            .select_from(AccountContribution)
            .where(AccountContribution.account_id == account_id)
        )

        return {
            "account_source": account.account_source.value
            if hasattr(account.account_source, "value")
            else str(account.account_source),
            "plaid_item_id": str(account.plaid_item_id)
            if account.plaid_item_id
            else None,
            "teller_enrollment_id": str(account.teller_enrollment_id)
            if account.teller_enrollment_id
            else None,
            "mx_member_id": str(account.mx_member_id)
            if account.mx_member_id
            else None,
            "external_account_id": account.external_account_id,
            "previous_external_account_id": account.previous_external_account_id,
            "plaid_item_hash": account.plaid_item_hash,
            "is_manual": account.is_manual,
            "transactions_count": tx_count or 0,
            "holdings_count": holdings_count or 0,
            "contributions_count": contrib_count or 0,
        }

    async def _execute_migration(
        self,
        db: AsyncSession,
        account_id: UUID,
        old_external_account_id: Optional[str],
        target_source: AccountSource,
        target_enrollment_id: Optional[UUID],
        target_external_account_id: Optional[str],
    ) -> None:
        """Execute the provider switch using Core SQL to bypass ORM orphan detection.

        CRITICAL: We use `update(Account).where(...)` instead of setting
        `account.plaid_item_id = None` on the ORM object. This prevents
        SQLAlchemy's delete-orphan cascade from firing.
        """
        values = {
            "account_source": target_source,
            "is_manual": target_source == AccountSource.MANUAL,
            "previous_external_account_id": old_external_account_id,
            "plaid_item_id": None,
            "teller_enrollment_id": None,
            "mx_member_id": None,
            "external_account_id": target_external_account_id,
            "updated_at": utc_now(),
        }

        fk_map = {
            AccountSource.PLAID: "plaid_item_id",
            AccountSource.TELLER: "teller_enrollment_id",
            AccountSource.MX: "mx_member_id",
        }
        if target_source in fk_map:
            values[fk_map[target_source]] = target_enrollment_id

        await db.execute(
            update(Account).where(Account.id == account_id).values(**values)
        )

    async def _recalculate_dedup_hash(
        self,
        db: AsyncSession,
        account_id: UUID,
        target_source: AccountSource,
        target_enrollment_id: Optional[UUID],
        target_external_account_id: Optional[str],
        account_type: AccountType,
        institution_name: Optional[str],
        mask: Optional[str],
        name: str,
    ) -> None:
        """Recalculate the plaid_item_hash for the new provider context."""
        new_hash = None

        if (
            target_source == AccountSource.PLAID
            and target_enrollment_id
            and target_external_account_id
        ):
            result = await db.execute(
                select(PlaidItem.item_id).where(
                    PlaidItem.id == target_enrollment_id
                )
            )
            plaid_item_id_str = result.scalar_one_or_none()
            if plaid_item_id_str:
                new_hash = deduplication_service.calculate_plaid_hash(
                    plaid_item_id_str, target_external_account_id
                )

        elif target_source == AccountSource.MANUAL:
            new_hash = deduplication_service.calculate_manual_account_hash(
                account_type, institution_name, mask, name
            )

        elif target_source in (AccountSource.TELLER, AccountSource.MX):
            content = f"{target_source.value}:{target_enrollment_id}:{target_external_account_id}"
            new_hash = hashlib.sha256(content.encode()).hexdigest()

        await db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(plaid_item_hash=new_hash)
        )


# Singleton
account_migration_service = AccountMigrationService()
