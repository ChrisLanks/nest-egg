"""Comprehensive tests for account provider migration service.

Tests use real DB (via db_session fixture) to verify cascade-delete-orphan
behavior — mocks wouldn't catch the ORM orphan deletion issue.
"""

import pytest
import pytest_asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.models.contribution import AccountContribution, ContributionType, ContributionFrequency
from app.models.account_migration import AccountMigrationLog, MigrationStatus
from app.models.user import User, Organization
from app.services.account_migration_service import (
    AccountMigrationService,
    MigrationError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def migration_service():
    return AccountMigrationService()


@pytest_asyncio.fixture
async def org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid4(), name="Migration Test Org")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def user(db: AsyncSession, org: Organization) -> User:
    from app.core.security import hash_password

    u = User(
        id=uuid4(),
        email="migrator@test.com",
        password_hash=hash_password("password123"),
        organization_id=org.id,
        is_org_admin=True,
        is_active=True,
        first_name="Test",
        last_name="Migrator",
        failed_login_attempts=0,
        locked_until=None,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


@pytest_asyncio.fixture
async def other_org(db: AsyncSession) -> Organization:
    org = Organization(id=uuid4(), name="Other Org")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@pytest_asyncio.fixture
async def plaid_item(db: AsyncSession, org: Organization, user: User) -> PlaidItem:
    item = PlaidItem(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        item_id="item_test_plaid_123",
        access_token="encrypted_plaid_token",
        institution_id="ins_123",
        institution_name="Test Bank",
        is_active=True,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@pytest_asyncio.fixture
async def teller_enrollment(
    db: AsyncSession, org: Organization, user: User
) -> TellerEnrollment:
    enrollment = TellerEnrollment(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        enrollment_id="enr_test_teller_456",
        access_token="encrypted_teller_token",
        institution_name="Test Credit Union",
        is_active=True,
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@pytest_asyncio.fixture
async def mx_member(db: AsyncSession, org: Organization, user: User) -> MxMember:
    member = MxMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        mx_user_guid="USR-test-789",
        member_guid="MBR-test-789",
        institution_code="mx_bank",
        institution_name="MX Bank",
        connection_status="CONNECTED",
        is_active=True,
    )
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@pytest_asyncio.fixture
async def plaid_account(
    db: AsyncSession, org: Organization, user: User, plaid_item: PlaidItem
) -> Account:
    """Create a Plaid-linked checking account."""
    account = Account(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        plaid_item_id=plaid_item.id,
        name="Plaid Checking",
        account_type=AccountType.CHECKING,
        account_source=AccountSource.PLAID,
        external_account_id="plaid_acc_001",
        institution_name="Test Bank",
        mask="1234",
        current_balance=Decimal("5000.00"),
        is_manual=False,
        is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@pytest_asyncio.fixture
async def teller_account(
    db: AsyncSession, org: Organization, user: User, teller_enrollment: TellerEnrollment
) -> Account:
    """Create a Teller-linked checking account."""
    account = Account(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        teller_enrollment_id=teller_enrollment.id,
        name="Teller Savings",
        account_type=AccountType.SAVINGS,
        account_source=AccountSource.TELLER,
        external_account_id="teller_acc_001",
        institution_name="Test Credit Union",
        mask="5678",
        current_balance=Decimal("10000.00"),
        is_manual=False,
        is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@pytest_asyncio.fixture
async def mx_account(
    db: AsyncSession, org: Organization, user: User, mx_member: MxMember
) -> Account:
    """Create an MX-linked checking account."""
    account = Account(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        mx_member_id=mx_member.id,
        name="MX Checking",
        account_type=AccountType.CHECKING,
        account_source=AccountSource.MX,
        external_account_id="ACT-mx-001",
        institution_name="MX Bank",
        mask="9012",
        current_balance=Decimal("3000.00"),
        is_manual=False,
        is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@pytest_asyncio.fixture
async def manual_account(
    db: AsyncSession, org: Organization, user: User
) -> Account:
    """Create a manual brokerage account with holdings."""
    account = Account(
        id=uuid4(),
        organization_id=org.id,
        user_id=user.id,
        name="Manual Brokerage",
        account_type=AccountType.BROKERAGE,
        account_source=AccountSource.MANUAL,
        institution_name="Schwab",
        mask="3456",
        current_balance=Decimal("50000.00"),
        is_manual=True,
        is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def _add_transactions(db: AsyncSession, account: Account, count: int = 3):
    """Helper to add transactions to an account."""
    for i in range(count):
        tx = Transaction(
            id=uuid4(),
            organization_id=account.organization_id,
            account_id=account.id,
            date=date(2024, 1, i + 1),
            amount=Decimal("-25.00"),
            description=f"Transaction {i}",
            merchant_name=f"Merchant {i}",
            deduplication_hash=f"hash_{account.id}_{i}",
        )
        db.add(tx)
    await db.flush()


async def _add_holdings(db: AsyncSession, account: Account, count: int = 2):
    """Helper to add holdings to an account."""
    tickers = ["AAPL", "VTSAX", "GOOG", "MSFT"]
    for i in range(count):
        h = Holding(
            id=uuid4(),
            account_id=account.id,
            organization_id=account.organization_id,
            ticker=tickers[i % len(tickers)],
            shares=Decimal("10.00"),
            cost_basis_per_share=Decimal("100.00"),
            total_cost_basis=Decimal("1000.00"),
            current_price_per_share=Decimal("150.00"),
            current_total_value=Decimal("1500.00"),
        )
        db.add(h)
    await db.flush()


async def _add_contributions(db: AsyncSession, account: Account, count: int = 1):
    """Helper to add contributions to an account."""
    for i in range(count):
        c = AccountContribution(
            id=uuid4(),
            organization_id=account.organization_id,
            account_id=account.id,
            contribution_type=ContributionType.FIXED_AMOUNT,
            amount=Decimal("500.00"),
            frequency=ContributionFrequency.MONTHLY,
            start_date=date(2024, 1, 1),
            is_active=True,
        )
        db.add(c)
    await db.flush()


async def _count_transactions(db: AsyncSession, account_id) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.account_id == account_id)
    ) or 0


async def _count_holdings(db: AsyncSession, account_id) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(Holding)
        .where(Holding.account_id == account_id)
    ) or 0


async def _count_contributions(db: AsyncSession, account_id) -> int:
    return await db.scalar(
        select(func.count())
        .select_from(AccountContribution)
        .where(AccountContribution.account_id == account_id)
    ) or 0


async def _account_exists(db: AsyncSession, account_id) -> bool:
    result = await db.scalar(
        select(func.count())
        .select_from(Account)
        .where(Account.id == account_id)
    )
    return (result or 0) > 0


# ===========================================================================
# A. Validation Tests
# ===========================================================================


class TestMigrationValidation:
    """Tests for migration validation rules."""

    @pytest.mark.asyncio
    async def test_migrate_same_provider_rejected(
        self, db, user, plaid_account, migration_service
    ):
        """Cannot migrate to the same provider."""
        with pytest.raises(MigrationError, match="already on plaid"):
            await migration_service.migrate_account(
                db=db,
                account_id=plaid_account.id,
                user=user,
                target_source=AccountSource.PLAID,
                target_enrollment_id=uuid4(),
                target_external_account_id="new_acc",
            )

    @pytest.mark.asyncio
    async def test_migrate_inactive_account_rejected(
        self, db, user, plaid_account, migration_service
    ):
        """Cannot migrate an inactive account."""
        account_id = plaid_account.id
        # Deactivate account via Core SQL to avoid ORM cascade issues
        await db.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(is_active=False)
        )
        await db.refresh(plaid_account)

        with pytest.raises(MigrationError, match="inactive account"):
            await migration_service.migrate_account(
                db=db,
                account_id=account_id,
                user=user,
                target_source=AccountSource.MANUAL,
            )

    @pytest.mark.asyncio
    async def test_migrate_to_provider_without_enrollment_rejected(
        self, db, user, plaid_account, migration_service
    ):
        """Migrating to a linked provider requires enrollment_id."""
        with pytest.raises(MigrationError, match="target_enrollment_id is required"):
            await migration_service.migrate_account(
                db=db,
                account_id=plaid_account.id,
                user=user,
                target_source=AccountSource.TELLER,
            )

    @pytest.mark.asyncio
    async def test_migrate_to_provider_without_external_id_rejected(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """Migrating to a linked provider requires external_account_id."""
        with pytest.raises(
            MigrationError, match="target_external_account_id is required"
        ):
            await migration_service.migrate_account(
                db=db,
                account_id=plaid_account.id,
                user=user,
                target_source=AccountSource.TELLER,
                target_enrollment_id=teller_enrollment.id,
            )

    @pytest.mark.asyncio
    async def test_migrate_to_provider_with_nonexistent_enrollment_rejected(
        self, db, user, plaid_account, migration_service
    ):
        """Enrollment must actually exist."""
        fake_id = uuid4()
        with pytest.raises(MigrationError, match="not found"):
            await migration_service.migrate_account(
                db=db,
                account_id=plaid_account.id,
                user=user,
                target_source=AccountSource.TELLER,
                target_enrollment_id=fake_id,
                target_external_account_id="teller_acc_new",
            )

    @pytest.mark.asyncio
    async def test_migrate_to_provider_with_wrong_org_enrollment_rejected(
        self, db, user, plaid_account, other_org, migration_service
    ):
        """Enrollment must belong to the same organization."""
        from app.core.security import hash_password

        other_user = User(
            id=uuid4(),
            email="other@test.com",
            password_hash=hash_password("password123"),
            organization_id=other_org.id,
            is_org_admin=True,
            is_active=True,
            first_name="Other",
            last_name="User",
            failed_login_attempts=0,
            locked_until=None,
        )
        db.add(other_user)
        await db.flush()

        other_enrollment = TellerEnrollment(
            id=uuid4(),
            organization_id=other_org.id,
            user_id=other_user.id,
            enrollment_id="enr_other_org",
            access_token="encrypted_other",
            institution_name="Other Bank",
            is_active=True,
        )
        db.add(other_enrollment)
        await db.flush()

        with pytest.raises(MigrationError, match="not found"):
            await migration_service.migrate_account(
                db=db,
                account_id=plaid_account.id,
                user=user,
                target_source=AccountSource.TELLER,
                target_enrollment_id=other_enrollment.id,
                target_external_account_id="teller_acc_cross",
            )

    @pytest.mark.asyncio
    async def test_migrate_to_manual_requires_no_enrollment(
        self, db, user, plaid_account, migration_service
    ):
        """Migrating to manual should succeed without enrollment."""
        log = await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        assert log.status == MigrationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_migrate_nonexistent_account_rejected(
        self, db, user, migration_service
    ):
        """Account must exist."""
        with pytest.raises(MigrationError, match="Account not found"):
            await migration_service.migrate_account(
                db=db,
                account_id=uuid4(),
                user=user,
                target_source=AccountSource.MANUAL,
            )


# ===========================================================================
# B. Provider → Manual Migration Tests
# ===========================================================================


class TestProviderToManual:
    """Tests for migrating from a linked provider to Manual."""

    @pytest.mark.asyncio
    async def test_plaid_to_manual_preserves_transactions(
        self, db, user, plaid_account, migration_service
    ):
        """All transactions must survive migration."""
        await _add_transactions(db, plaid_account, 5)
        await db.commit()
        assert await _count_transactions(db, plaid_account.id) == 5

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert await _count_transactions(db, plaid_account.id) == 5

    @pytest.mark.asyncio
    async def test_plaid_to_manual_preserves_holdings(
        self, db, user, plaid_account, migration_service
    ):
        """All holdings must survive migration."""
        await _add_holdings(db, plaid_account, 3)
        await db.commit()
        assert await _count_holdings(db, plaid_account.id) == 3

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert await _count_holdings(db, plaid_account.id) == 3

    @pytest.mark.asyncio
    async def test_plaid_to_manual_preserves_contributions(
        self, db, user, plaid_account, migration_service
    ):
        """All contributions must survive migration."""
        await _add_contributions(db, plaid_account, 2)
        await db.commit()
        assert await _count_contributions(db, plaid_account.id) == 2

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert await _count_contributions(db, plaid_account.id) == 2

    @pytest.mark.asyncio
    async def test_plaid_to_manual_clears_provider_fk(
        self, db, user, plaid_account, migration_service
    ):
        """plaid_item_id should be cleared, is_manual should be True."""
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(plaid_account)

        assert plaid_account.plaid_item_id is None
        assert plaid_account.teller_enrollment_id is None
        assert plaid_account.mx_member_id is None
        assert plaid_account.is_manual is True
        assert plaid_account.account_source == AccountSource.MANUAL

    @pytest.mark.asyncio
    async def test_plaid_to_manual_preserves_external_id_as_previous(
        self, db, user, plaid_account, migration_service
    ):
        """external_account_id should be moved to previous_external_account_id."""
        original_ext_id = plaid_account.external_account_id
        assert original_ext_id == "plaid_acc_001"

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(plaid_account)

        assert plaid_account.external_account_id is None
        assert plaid_account.previous_external_account_id == original_ext_id

    @pytest.mark.asyncio
    async def test_teller_to_manual_works(
        self, db, user, teller_account, migration_service
    ):
        """Teller→Manual migration works identically to Plaid→Manual."""
        await _add_transactions(db, teller_account, 3)
        await db.commit()

        await migration_service.migrate_account(
            db=db,
            account_id=teller_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(teller_account)

        assert teller_account.teller_enrollment_id is None
        assert teller_account.is_manual is True
        assert teller_account.account_source == AccountSource.MANUAL
        assert await _count_transactions(db, teller_account.id) == 3


# ===========================================================================
# C. Manual → Provider Migration Tests
# ===========================================================================


class TestManualToProvider:
    """Tests for migrating from Manual to a linked provider."""

    @pytest.mark.asyncio
    async def test_manual_to_plaid_sets_provider_fk(
        self, db, user, manual_account, plaid_item, migration_service
    ):
        """plaid_item_id should be set correctly."""
        await migration_service.migrate_account(
            db=db,
            account_id=manual_account.id,
            user=user,
            target_source=AccountSource.PLAID,
            target_enrollment_id=plaid_item.id,
            target_external_account_id="plaid_acc_new",
        )
        await db.refresh(manual_account)

        assert manual_account.plaid_item_id == plaid_item.id
        assert manual_account.external_account_id == "plaid_acc_new"
        assert manual_account.account_source == AccountSource.PLAID
        assert manual_account.is_manual is False

    @pytest.mark.asyncio
    async def test_manual_to_plaid_preserves_manual_holdings(
        self, db, user, manual_account, plaid_item, migration_service
    ):
        """Existing manual holdings should NOT be deleted."""
        await _add_holdings(db, manual_account, 3)
        await db.commit()
        assert await _count_holdings(db, manual_account.id) == 3

        await migration_service.migrate_account(
            db=db,
            account_id=manual_account.id,
            user=user,
            target_source=AccountSource.PLAID,
            target_enrollment_id=plaid_item.id,
            target_external_account_id="plaid_acc_new",
        )

        assert await _count_holdings(db, manual_account.id) == 3

    @pytest.mark.asyncio
    async def test_manual_to_teller_sets_enrollment_id(
        self, db, user, manual_account, teller_enrollment, migration_service
    ):
        """teller_enrollment_id should be set."""
        await migration_service.migrate_account(
            db=db,
            account_id=manual_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_acc_new",
        )
        await db.refresh(manual_account)

        assert manual_account.teller_enrollment_id == teller_enrollment.id
        assert manual_account.plaid_item_id is None
        assert manual_account.mx_member_id is None
        assert manual_account.account_source == AccountSource.TELLER

    @pytest.mark.asyncio
    async def test_manual_to_mx_sets_member_id(
        self, db, user, manual_account, mx_member, migration_service
    ):
        """mx_member_id should be set."""
        await migration_service.migrate_account(
            db=db,
            account_id=manual_account.id,
            user=user,
            target_source=AccountSource.MX,
            target_enrollment_id=mx_member.id,
            target_external_account_id="ACT-mx-new",
        )
        await db.refresh(manual_account)

        assert manual_account.mx_member_id == mx_member.id
        assert manual_account.plaid_item_id is None
        assert manual_account.teller_enrollment_id is None
        assert manual_account.account_source == AccountSource.MX


# ===========================================================================
# D. Provider → Provider Migration Tests
# ===========================================================================


class TestProviderToProvider:
    """Tests for migrating between different linked providers."""

    @pytest.mark.asyncio
    async def test_plaid_to_teller_swaps_fks(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """FK should swap from plaid_item_id to teller_enrollment_id."""
        old_plaid_item_id = plaid_account.plaid_item_id

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_acc_migrated",
        )
        await db.refresh(plaid_account)

        assert plaid_account.plaid_item_id is None
        assert plaid_account.teller_enrollment_id == teller_enrollment.id
        assert plaid_account.mx_member_id is None
        assert plaid_account.account_source == AccountSource.TELLER
        assert plaid_account.external_account_id == "teller_acc_migrated"
        assert plaid_account.previous_external_account_id == "plaid_acc_001"

    @pytest.mark.asyncio
    async def test_plaid_to_teller_preserves_transactions(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """All transactions must survive provider-to-provider migration."""
        await _add_transactions(db, plaid_account, 10)
        await db.commit()

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_acc_migrated",
        )

        assert await _count_transactions(db, plaid_account.id) == 10

    @pytest.mark.asyncio
    async def test_teller_to_mx_swaps_fks(
        self, db, user, teller_account, mx_member, migration_service
    ):
        """FK should swap from teller_enrollment_id to mx_member_id."""
        await migration_service.migrate_account(
            db=db,
            account_id=teller_account.id,
            user=user,
            target_source=AccountSource.MX,
            target_enrollment_id=mx_member.id,
            target_external_account_id="ACT-mx-migrated",
        )
        await db.refresh(teller_account)

        assert teller_account.teller_enrollment_id is None
        assert teller_account.mx_member_id == mx_member.id
        assert teller_account.account_source == AccountSource.MX

    @pytest.mark.asyncio
    async def test_provider_switch_preserves_all_downstream_data(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """Comprehensive check: transactions + holdings + contributions all survive."""
        await _add_transactions(db, plaid_account, 5)
        await _add_holdings(db, plaid_account, 3)
        await _add_contributions(db, plaid_account, 2)
        await db.commit()

        assert await _count_transactions(db, plaid_account.id) == 5
        assert await _count_holdings(db, plaid_account.id) == 3
        assert await _count_contributions(db, plaid_account.id) == 2

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_acc_migrated",
        )

        # All downstream data must be intact
        assert await _count_transactions(db, plaid_account.id) == 5
        assert await _count_holdings(db, plaid_account.id) == 3
        assert await _count_contributions(db, plaid_account.id) == 2


# ===========================================================================
# E. Cascade Safety Tests (THE CRITICAL ONES)
# ===========================================================================


class TestCascadeSafety:
    """Verify that ORM delete-orphan cascade is NOT triggered by migration."""

    @pytest.mark.asyncio
    async def test_migration_does_not_trigger_orphan_delete(
        self, db, user, plaid_account, migration_service
    ):
        """After migration, the account must still exist in the DB."""
        account_id = plaid_account.id

        await migration_service.migrate_account(
            db=db,
            account_id=account_id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert await _account_exists(db, account_id)

    @pytest.mark.asyncio
    async def test_migration_does_not_cascade_delete_transactions(
        self, db, user, plaid_account, migration_service
    ):
        """Transaction count must be unchanged after migration."""
        await _add_transactions(db, plaid_account, 7)
        await db.commit()

        before = await _count_transactions(db, plaid_account.id)
        assert before == 7

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        after = await _count_transactions(db, plaid_account.id)
        assert after == before

    @pytest.mark.asyncio
    async def test_migration_does_not_cascade_delete_holdings(
        self, db, user, plaid_account, migration_service
    ):
        """Holdings count must be unchanged after migration."""
        await _add_holdings(db, plaid_account, 4)
        await db.commit()

        before = await _count_holdings(db, plaid_account.id)
        assert before == 4

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        after = await _count_holdings(db, plaid_account.id)
        assert after == before

    @pytest.mark.asyncio
    async def test_plaid_item_still_exists_after_detach(
        self, db, user, plaid_account, plaid_item, migration_service
    ):
        """The PlaidItem itself should NOT be deleted when account is detached."""
        plaid_item_id = plaid_item.id

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        # PlaidItem should still exist
        result = await db.execute(
            select(PlaidItem).where(PlaidItem.id == plaid_item_id)
        )
        item = result.scalar_one_or_none()
        assert item is not None


# ===========================================================================
# F. Deduplication Hash Tests
# ===========================================================================


class TestDedupHash:
    """Tests for deduplication hash recalculation after migration."""

    @pytest.mark.asyncio
    async def test_plaid_to_manual_recalculates_hash(
        self, db, user, plaid_account, migration_service
    ):
        """Hash should change to manual-style after migration."""
        old_hash = plaid_account.plaid_item_hash

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(plaid_account)

        assert plaid_account.plaid_item_hash is not None
        assert plaid_account.plaid_item_hash != old_hash

    @pytest.mark.asyncio
    async def test_manual_to_plaid_recalculates_hash(
        self, db, user, manual_account, plaid_item, migration_service
    ):
        """Hash should change to plaid-style after migration."""
        old_hash = manual_account.plaid_item_hash

        await migration_service.migrate_account(
            db=db,
            account_id=manual_account.id,
            user=user,
            target_source=AccountSource.PLAID,
            target_enrollment_id=plaid_item.id,
            target_external_account_id="plaid_acc_linked",
        )
        await db.refresh(manual_account)

        assert manual_account.plaid_item_hash is not None
        # Verify it's the expected plaid hash
        from app.services.deduplication_service import DeduplicationService

        expected = DeduplicationService.calculate_plaid_hash(
            plaid_item.item_id, "plaid_acc_linked"
        )
        assert manual_account.plaid_item_hash == expected

    @pytest.mark.asyncio
    async def test_provider_to_provider_recalculates_hash(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """Hash should change when migrating between providers."""
        old_hash = plaid_account.plaid_item_hash

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_acc_new",
        )
        await db.refresh(plaid_account)

        assert plaid_account.plaid_item_hash is not None
        assert plaid_account.plaid_item_hash != old_hash


# ===========================================================================
# G. Audit Log Tests
# ===========================================================================


class TestAuditLog:
    """Tests for migration audit log."""

    @pytest.mark.asyncio
    async def test_migration_creates_log_entry(
        self, db, user, plaid_account, migration_service
    ):
        """A completed migration should create a log entry."""
        log = await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert log.id is not None
        assert log.status == MigrationStatus.COMPLETED
        assert log.source_provider == "plaid"
        assert log.target_provider == "manual"
        assert log.account_id == plaid_account.id
        assert log.initiated_by_user_id == user.id
        assert log.completed_at is not None

    @pytest.mark.asyncio
    async def test_log_captures_pre_snapshot(
        self, db, user, plaid_account, plaid_item, migration_service
    ):
        """Pre-snapshot should capture correct provider state and counts."""
        await _add_transactions(db, plaid_account, 3)
        await _add_holdings(db, plaid_account, 2)
        await db.commit()

        log = await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        snap = log.pre_migration_snapshot
        assert snap["account_source"] == "plaid"
        assert snap["plaid_item_id"] == str(plaid_item.id)
        assert snap["external_account_id"] == "plaid_acc_001"
        assert snap["is_manual"] is False
        assert snap["transactions_count"] == 3
        assert snap["holdings_count"] == 2

    @pytest.mark.asyncio
    async def test_log_captures_post_snapshot(
        self, db, user, plaid_account, migration_service
    ):
        """Post-snapshot should capture new provider state."""
        await _add_transactions(db, plaid_account, 2)
        await db.commit()

        log = await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        snap = log.post_migration_snapshot
        assert snap["account_source"] == "manual"
        assert snap["plaid_item_id"] is None
        assert snap["is_manual"] is True
        assert snap["transactions_count"] == 2

    @pytest.mark.asyncio
    async def test_migration_history_returns_logs(
        self, db, user, plaid_account, teller_enrollment, migration_service
    ):
        """get_migration_history should return ordered logs."""
        # First migration: plaid → manual
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        # Second migration: manual → teller
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_migrated",
        )

        history = await migration_service.get_migration_history(
            db=db,
            account_id=plaid_account.id,
            organization_id=user.organization_id,
        )

        assert len(history) == 2
        # Most recent first
        assert history[0].target_provider == "teller"
        assert history[1].target_provider == "manual"


# ===========================================================================
# H. API Endpoint Tests
# ===========================================================================


class TestMigrationAPI:
    """Tests for the /accounts/{id}/migrate API endpoint."""

    @pytest.mark.asyncio
    async def test_migrate_endpoint_requires_confirmation(
        self, authenticated_client, test_account
    ):
        """Should return 400 when confirm is false."""
        response = await authenticated_client.post(
            f"/api/v1/accounts/{test_account.id}/migrate",
            json={
                "target_source": "manual",
                "confirm": False,
            },
        )
        assert response.status_code == 400
        assert "confirm=true" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_migrate_endpoint_rejects_same_provider(
        self, authenticated_client, test_account
    ):
        """Should return 400 for same-provider migration."""
        # test_account from conftest is a manual account (no account_source set defaults to PLAID)
        # We'll migrate to the same source and expect rejection
        response = await authenticated_client.post(
            f"/api/v1/accounts/{test_account.id}/migrate",
            json={
                "target_source": "plaid",
                "target_enrollment_id": str(uuid4()),
                "target_external_account_id": "acc_001",
                "confirm": True,
            },
        )
        # Should get a 400 (either same provider or enrollment not found)
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_migration_history_endpoint(
        self, authenticated_client, test_account
    ):
        """History endpoint should return list (possibly empty)."""
        response = await authenticated_client.get(
            f"/api/v1/accounts/{test_account.id}/migration-history"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ===========================================================================
# I. Edge Case Tests
# ===========================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    @pytest.mark.asyncio
    async def test_migrate_empty_account(
        self, db, user, plaid_account, migration_service
    ):
        """An account with no transactions/holdings should migrate fine."""
        assert await _count_transactions(db, plaid_account.id) == 0
        assert await _count_holdings(db, plaid_account.id) == 0

        log = await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )

        assert log.status == MigrationStatus.COMPLETED
        assert await _account_exists(db, plaid_account.id)

    @pytest.mark.asyncio
    async def test_multiple_sequential_migrations(
        self, db, user, plaid_account, teller_enrollment, mx_member, migration_service
    ):
        """Account should survive A→B→C migrations."""
        await _add_transactions(db, plaid_account, 3)
        await db.commit()

        # Plaid → Teller
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.TELLER,
            target_enrollment_id=teller_enrollment.id,
            target_external_account_id="teller_step1",
        )
        assert await _count_transactions(db, plaid_account.id) == 3

        # Teller → MX
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MX,
            target_enrollment_id=mx_member.id,
            target_external_account_id="ACT-mx-step2",
        )
        assert await _count_transactions(db, plaid_account.id) == 3

        # MX → Manual
        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        assert await _count_transactions(db, plaid_account.id) == 3

        # Verify final state
        await db.refresh(plaid_account)
        assert plaid_account.account_source == AccountSource.MANUAL
        assert plaid_account.is_manual is True
        assert plaid_account.plaid_item_id is None
        assert plaid_account.teller_enrollment_id is None
        assert plaid_account.mx_member_id is None

        # Should have 3 migration logs
        history = await migration_service.get_migration_history(
            db=db,
            account_id=plaid_account.id,
            organization_id=user.organization_id,
        )
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_mx_to_manual_works(
        self, db, user, mx_account, migration_service
    ):
        """MX→Manual migration should work correctly."""
        await _add_transactions(db, mx_account, 4)
        await db.commit()

        await migration_service.migrate_account(
            db=db,
            account_id=mx_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(mx_account)

        assert mx_account.mx_member_id is None
        assert mx_account.account_source == AccountSource.MANUAL
        assert mx_account.is_manual is True
        assert mx_account.previous_external_account_id == "ACT-mx-001"
        assert await _count_transactions(db, mx_account.id) == 4

    @pytest.mark.asyncio
    async def test_balance_preserved_after_migration(
        self, db, user, plaid_account, migration_service
    ):
        """Account balance should not change during migration."""
        original_balance = plaid_account.current_balance

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(plaid_account)

        assert plaid_account.current_balance == original_balance

    @pytest.mark.asyncio
    async def test_account_name_and_type_preserved(
        self, db, user, plaid_account, migration_service
    ):
        """Account name and type should not change during migration."""
        original_name = plaid_account.name
        original_type = plaid_account.account_type

        await migration_service.migrate_account(
            db=db,
            account_id=plaid_account.id,
            user=user,
            target_source=AccountSource.MANUAL,
        )
        await db.refresh(plaid_account)

        assert plaid_account.name == original_name
        assert plaid_account.account_type == original_type
