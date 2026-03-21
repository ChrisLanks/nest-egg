"""Tests for notification-related fixes.

Covers:
1. Budget alert deduplication (Fix 1)
2. Notification preferences schema — new fields (Fix 2)
3. Export labels readability (Fix 4)
4. Bill reminder Celery task (Fix 3)
5. Recurring detection deduplication (Fix 5)
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.models.recurring_transaction import RecurringFrequency, RecurringTransaction
from app.models.user import Organization, User
from app.services.budget_service import BudgetService
from app.services.notification_service import NotificationService


# ---------------------------------------------------------------------------
# Fix 1: Budget alert deduplication
# ---------------------------------------------------------------------------


class TestBudgetAlertDedup:
    """Budget alert deduplication tests."""

    @pytest.mark.asyncio
    async def test_budget_alert_dedup_creates_if_none_exists(self, db, test_user, test_account):
        """First run should create a notification when none exists today."""
        from app.models.budget import Budget, BudgetPeriod
        from app.models.transaction import Transaction

        # Create a budget
        budget = Budget(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Groceries",
            amount=Decimal("100.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today().replace(day=1),
            alert_threshold=Decimal("0.80"),
            is_active=True,
        )
        db.add(budget)

        # Create a transaction that puts us over the alert threshold (>80%)
        _hash1 = str(uuid4()).replace("-", "")[:64]
        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-90.00"),  # 90% of $100 budget
            merchant_name="Grocery Store",
            is_transfer=False,
            is_pending=False,
            deduplication_hash=_hash1,
        )
        db.add(txn)
        await db.commit()

        alerts = await BudgetService.check_budget_alerts(db, test_user)

        assert len(alerts) == 1
        assert alerts[0]["budget"].id == budget.id

        # Verify the notification was created in DB
        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.BUDGET_ALERT,
                Notification.related_entity_id == budget.id,
            )
        )
        notifications = notif_result.scalars().all()
        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_budget_alert_dedup_skips_existing(self, db, test_user, test_account):
        """Second run on same day should not create a duplicate notification."""
        from app.models.budget import Budget, BudgetPeriod
        from app.models.transaction import Transaction

        budget = Budget(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Transport",
            amount=Decimal("100.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today().replace(day=1),
            alert_threshold=Decimal("0.80"),
            is_active=True,
        )
        db.add(budget)

        _hash2 = str(uuid4()).replace("-", "")[:64]
        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-90.00"),
            merchant_name="Gas Station",
            is_transfer=False,
            is_pending=False,
            deduplication_hash=_hash2,
        )
        db.add(txn)
        await db.commit()

        # First run — should create notification
        alerts1 = await BudgetService.check_budget_alerts(db, test_user)
        assert len(alerts1) == 1

        # Second run on same day — should skip (dedup)
        alerts2 = await BudgetService.check_budget_alerts(db, test_user)
        assert len(alerts2) == 0

        # Only one notification in DB
        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.BUDGET_ALERT,
                Notification.related_entity_id == budget.id,
            )
        )
        notifications = notif_result.scalars().all()
        assert len(notifications) == 1

    @pytest.mark.asyncio
    async def test_budget_alert_attaches_real_user_id(self, db, test_user, test_account):
        """Budget alert notification should have a non-None user_id so email fires."""
        from app.models.budget import Budget, BudgetPeriod
        from app.models.transaction import Transaction

        budget = Budget(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Dining",
            amount=Decimal("100.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today().replace(day=1),
            alert_threshold=Decimal("0.80"),
            is_active=True,
        )
        db.add(budget)
        _hash3 = str(uuid4()).replace("-", "")[:64]
        txn = Transaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-90.00"),
            merchant_name="Restaurant",
            is_transfer=False,
            is_pending=False,
            deduplication_hash=_hash3,
        )
        db.add(txn)
        await db.commit()

        await BudgetService.check_budget_alerts(db, test_user)

        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.BUDGET_ALERT,
                Notification.related_entity_id == budget.id,
            )
        )
        notif = notif_result.scalar_one_or_none()
        assert notif is not None
        assert notif.user_id is not None, "user_id must be set so emails can fire"


# ---------------------------------------------------------------------------
# Fix 2: Notification preferences schema — add missing fields
# ---------------------------------------------------------------------------


class TestNotificationPreferencesSchema:
    """Tests for notification preferences schema with all 9 fields."""

    @pytest.mark.asyncio
    async def test_notification_prefs_saves_goal_alerts(self, authenticated_client):
        """PATCH /settings/notification-preferences with goal_alerts=true should save it."""
        response = await authenticated_client.patch(
            "/api/v1/settings/notification-preferences",
            json={"goal_alerts": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["goal_alerts"] is True

    @pytest.mark.asyncio
    async def test_notification_prefs_saves_all_new_fields(self, authenticated_client):
        """All four new fields should be accepted and returned."""
        payload = {
            "goal_alerts": False,
            "weekly_recap": True,
            "equity_alerts": False,
            "crypto_alerts": True,
        }
        response = await authenticated_client.patch(
            "/api/v1/settings/notification-preferences",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["goal_alerts"] is False
        assert data["weekly_recap"] is True
        assert data["equity_alerts"] is False
        assert data["crypto_alerts"] is True

    @pytest.mark.asyncio
    async def test_notification_prefs_returns_all_fields(self, authenticated_client):
        """GET /settings/notification-preferences should return all 9 fields."""
        response = await authenticated_client.get(
            "/api/v1/settings/notification-preferences",
        )
        assert response.status_code == 200
        data = response.json()
        expected_fields = {
            "account_syncs",
            "account_activity",
            "budget_alerts",
            "milestones",
            "household",
            "goal_alerts",
            "weekly_recap",
            "equity_alerts",
            "crypto_alerts",
        }
        assert expected_fields.issubset(data.keys()), (
            f"Missing fields: {expected_fields - set(data.keys())}"
        )


# ---------------------------------------------------------------------------
# Fix 4: Export labels readability
# ---------------------------------------------------------------------------


class TestExportLabels:
    """Tests that CSV export uses real label names, not repr strings."""

    @pytest.mark.asyncio
    async def test_export_labels_are_readable(self, authenticated_client, db, test_account):
        """CSV export should contain label name, not '<TransactionLabel ...>'."""
        from app.models.transaction import Label, Transaction, TransactionLabel

        # Create a label
        label = Label(
            id=uuid4(),
            organization_id=test_account.organization_id,
            name="Subscriptions",
        )
        db.add(label)

        # Create a transaction
        _dedup_hash = str(uuid4()).replace("-", "")[:64]
        txn = Transaction(
            id=uuid4(),
            organization_id=test_account.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-12.99"),
            merchant_name="Netflix",
            is_transfer=False,
            is_pending=False,
            deduplication_hash=_dedup_hash,
        )
        db.add(txn)
        await db.flush()

        # Link label to transaction
        txn_label = TransactionLabel(
            id=uuid4(),
            transaction_id=txn.id,
            label_id=label.id,
        )
        db.add(txn_label)
        await db.commit()

        response = await authenticated_client.get("/api/v1/settings/export")
        assert response.status_code == 200

        import io
        import zipfile

        zip_bytes = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_bytes) as zf:
            with zf.open("transactions.csv") as f:
                csv_text = f.read().decode("utf-8")

        # The label name "Subscriptions" must appear; the ORM repr must NOT
        assert "Subscriptions" in csv_text, "Label name missing from CSV export"
        assert "<TransactionLabel" not in csv_text, "ORM repr leaked into CSV export"


# ---------------------------------------------------------------------------
# Fix 3: Bill reminder Celery task
# ---------------------------------------------------------------------------


class TestBillReminderTask:
    """Tests for the send_bill_reminders Celery task."""

    @pytest.mark.asyncio
    async def test_bill_reminder_task_creates_notification(self, db, test_user, test_account):
        """A bill due tomorrow should trigger a reminder notification."""
        bill = RecurringTransaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            merchant_name="Electric Company",
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("75.00"),
            first_occurrence=date.today() - timedelta(days=30),
            occurrence_count=2,
            is_bill=True,
            is_active=True,
            reminder_days_before=3,
            next_expected_date=date.today() + timedelta(days=1),  # Due tomorrow
        )
        db.add(bill)
        await db.commit()

        # Import after setup to avoid circular imports
        from app.workers.tasks.bill_reminder_tasks import _process_org_bills

        org_result = await db.execute(
            select(Organization).where(
                Organization.id == test_user.organization_id
            )
        )
        org = org_result.scalar_one()

        await _process_org_bills(db, org)
        await db.commit()

        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.related_entity_id == bill.id,
            )
        )
        notifications = notif_result.scalars().all()
        assert len(notifications) == 1
        assert "Electric Company" in notifications[0].title

    @pytest.mark.asyncio
    async def test_bill_reminder_task_deduplicates(self, db, test_user, test_account):
        """Running the task twice on the same day should only create one notification."""
        bill = RecurringTransaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            merchant_name="Water Utility",
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("30.00"),
            first_occurrence=date.today() - timedelta(days=30),
            occurrence_count=2,
            is_bill=True,
            is_active=True,
            reminder_days_before=3,
            next_expected_date=date.today() + timedelta(days=2),  # Within window
        )
        db.add(bill)
        await db.commit()

        from app.workers.tasks.bill_reminder_tasks import _process_org_bills

        org_result = await db.execute(
            select(Organization).where(
                Organization.id == test_user.organization_id
            )
        )
        org = org_result.scalar_one()

        # First run
        await _process_org_bills(db, org)
        await db.commit()

        # Second run (same day)
        await _process_org_bills(db, org)
        await db.commit()

        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.related_entity_id == bill.id,
            )
        )
        notifications = notif_result.scalars().all()
        assert len(notifications) == 1, "Duplicate bill reminder should be suppressed"

    @pytest.mark.asyncio
    async def test_bill_reminder_not_triggered_outside_window(self, db, test_user, test_account):
        """A bill due in 10 days with 3-day window should NOT trigger a reminder."""
        bill = RecurringTransaction(
            id=uuid4(),
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            merchant_name="Mortgage",
            frequency=RecurringFrequency.MONTHLY,
            average_amount=Decimal("1500.00"),
            first_occurrence=date.today() - timedelta(days=30),
            occurrence_count=2,
            is_bill=True,
            is_active=True,
            reminder_days_before=3,
            next_expected_date=date.today() + timedelta(days=10),  # Outside 3-day window
        )
        db.add(bill)
        await db.commit()

        from app.workers.tasks.bill_reminder_tasks import _process_org_bills

        org_result = await db.execute(
            select(Organization).where(
                Organization.id == test_user.organization_id
            )
        )
        org = org_result.scalar_one()

        await _process_org_bills(db, org)
        await db.commit()

        notif_result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.related_entity_id == bill.id,
            )
        )
        notifications = notif_result.scalars().all()
        assert len(notifications) == 0


# ---------------------------------------------------------------------------
# Fix 5: Recurring detection deduplication
# ---------------------------------------------------------------------------


class TestRecurringDetectionDedup:
    """Tests that recurring detection does not create duplicate patterns."""

    @pytest.mark.asyncio
    async def test_recurring_detection_no_duplicates(self, db, test_user, test_account):
        """Running detection twice should not create duplicate recurring patterns."""
        from app.models.transaction import Transaction
        from app.services.recurring_detection_service import RecurringDetectionService

        merchant = "Netflix"
        # Create 4 monthly transactions so detection fires
        for i in range(4):
            _dedup = str(uuid4()).replace("-", "")[:64]
            txn = Transaction(
                id=uuid4(),
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date.today() - timedelta(days=30 * i),
                amount=Decimal("-15.99"),
                merchant_name=merchant,
                is_transfer=False,
                is_pending=False,
                deduplication_hash=_dedup,
            )
            db.add(txn)
        await db.commit()

        # First detection run
        patterns1 = await RecurringDetectionService.detect_recurring_patterns(
            db, test_user, min_occurrences=3
        )
        count_after_first = sum(1 for p in patterns1 if p.merchant_name == merchant)

        # Second detection run
        patterns2 = await RecurringDetectionService.detect_recurring_patterns(
            db, test_user, min_occurrences=3
        )
        count_after_second = sum(1 for p in patterns2 if p.merchant_name == merchant)

        # Should have exactly one pattern for this merchant
        assert count_after_first == 1
        assert count_after_second == 1

        # Verify DB has only one row
        result = await db.execute(
            select(RecurringTransaction).where(
                RecurringTransaction.organization_id == test_user.organization_id,
                RecurringTransaction.merchant_name == merchant,
            )
        )
        db_patterns = result.scalars().all()
        assert len(db_patterns) == 1, "Duplicate recurring pattern was inserted"
