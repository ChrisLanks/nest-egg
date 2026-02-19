"""Tests for budget service."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from app.services.budget_service import BudgetService
from app.models.budget import Budget, BudgetPeriod
from app.models.transaction import Transaction, Category
from app.models.notification import NotificationType


class TestBudgetService:
    """Test suite for budget service."""

    def test_get_period_dates_monthly(self):
        """Should calculate monthly period dates."""
        service = BudgetService()

        # January 2024
        ref_date = date(2024, 1, 15)
        start, end = service._get_period_dates(BudgetPeriod.MONTHLY, ref_date)

        assert start == date(2024, 1, 1)
        assert end == date(2024, 1, 31)

    def test_get_period_dates_monthly_february(self):
        """Should handle February correctly."""
        service = BudgetService()

        # February 2024 (leap year)
        ref_date = date(2024, 2, 15)
        start, end = service._get_period_dates(BudgetPeriod.MONTHLY, ref_date)

        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)  # Leap year

        # February 2023 (non-leap year)
        ref_date = date(2023, 2, 15)
        start, end = service._get_period_dates(BudgetPeriod.MONTHLY, ref_date)

        assert start == date(2023, 2, 1)
        assert end == date(2023, 2, 28)

    def test_get_period_dates_monthly_december(self):
        """Should handle December correctly."""
        service = BudgetService()

        ref_date = date(2024, 12, 15)
        start, end = service._get_period_dates(BudgetPeriod.MONTHLY, ref_date)

        assert start == date(2024, 12, 1)
        assert end == date(2024, 12, 31)

    def test_get_period_dates_quarterly(self):
        """Should calculate quarterly period dates."""
        service = BudgetService()

        # Q1 (Jan-Mar)
        ref_date = date(2024, 2, 15)
        start, end = service._get_period_dates(BudgetPeriod.QUARTERLY, ref_date)

        assert start == date(2024, 1, 1)
        assert end == date(2024, 3, 31)

        # Q2 (Apr-Jun)
        ref_date = date(2024, 5, 15)
        start, end = service._get_period_dates(BudgetPeriod.QUARTERLY, ref_date)

        assert start == date(2024, 4, 1)
        assert end == date(2024, 6, 30)

        # Q3 (Jul-Sep)
        ref_date = date(2024, 8, 15)
        start, end = service._get_period_dates(BudgetPeriod.QUARTERLY, ref_date)

        assert start == date(2024, 7, 1)
        assert end == date(2024, 9, 30)

        # Q4 (Oct-Dec)
        ref_date = date(2024, 11, 15)
        start, end = service._get_period_dates(BudgetPeriod.QUARTERLY, ref_date)

        assert start == date(2024, 10, 1)
        assert end == date(2024, 12, 31)

    def test_get_period_dates_yearly(self):
        """Should calculate yearly period dates."""
        service = BudgetService()

        ref_date = date(2024, 6, 15)
        start, end = service._get_period_dates(BudgetPeriod.YEARLY, ref_date)

        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_create_budget(self, db_session, test_user):
        """Should create a new budget."""
        service = BudgetService()

        budget = await service.create_budget(
            db=db_session,
            user=test_user,
            name="Groceries",
            amount=Decimal("500.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2024, 1, 1),
        )

        assert budget.id is not None
        assert budget.name == "Groceries"
        assert budget.amount == Decimal("500.00")
        assert budget.period == BudgetPeriod.MONTHLY
        assert budget.alert_threshold == Decimal("0.80")  # Default
        assert budget.is_active is True

    @pytest.mark.asyncio
    async def test_create_budget_with_category(self, db_session, test_user):
        """Should create budget linked to category."""
        service = BudgetService()

        # Create category
        category = Category(
            organization_id=test_user.organization_id,
            name="Food",
        )
        db_session.add(category)
        await db_session.commit()

        budget = await service.create_budget(
            db=db_session,
            user=test_user,
            name="Food Budget",
            amount=Decimal("600.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2024, 1, 1),
            category_id=category.id,
        )

        assert budget.category_id == category.id

    @pytest.mark.asyncio
    async def test_create_budget_with_custom_threshold(self, db_session, test_user):
        """Should allow custom alert threshold."""
        service = BudgetService()

        budget = await service.create_budget(
            db=db_session,
            user=test_user,
            name="Custom Alert",
            amount=Decimal("1000.00"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2024, 1, 1),
            alert_threshold=Decimal("0.90"),
        )

        assert budget.alert_threshold == Decimal("0.90")

    @pytest.mark.asyncio
    async def test_get_budgets(self, db, test_user):
        """Should get all budgets for organization."""
        service = BudgetService()

        # Create multiple budgets
        await service.create_budget(
            db, test_user, "Budget 1", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )
        await service.create_budget(
            db, test_user, "Budget 2", Decimal("200"), BudgetPeriod.MONTHLY, date.today()
        )

        budgets = await service.get_budgets(db, test_user)

        assert len(budgets) >= 2

    @pytest.mark.asyncio
    async def test_get_budgets_filter_active(self, db, test_user):
        """Should filter budgets by is_active status."""
        service = BudgetService()

        # Create active budget
        _active = await service.create_budget(
            db, test_user, "Active", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )

        # Create inactive budget
        inactive = await service.create_budget(
            db, test_user, "Inactive", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )
        inactive.is_active = False
        await db.commit()

        # Get only active
        active_budgets = await service.get_budgets(db, test_user, is_active=True)
        active_names = [b.name for b in active_budgets]

        assert "Active" in active_names
        assert "Inactive" not in active_names

    @pytest.mark.asyncio
    async def test_get_budget(self, db, test_user):
        """Should get specific budget by ID."""
        service = BudgetService()

        created = await service.create_budget(
            db, test_user, "Test", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )

        retrieved = await service.get_budget(db, created.id, test_user)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Test"

    @pytest.mark.asyncio
    async def test_get_budget_cross_org_blocked(self, db, test_user, second_organization):
        """Should not allow accessing budgets from other orgs."""
        service = BudgetService()

        # Create budget in other org
        other_budget = Budget(
            id=uuid4(),
            organization_id=second_organization.id,
            name="Other Org",
            amount=Decimal("100"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today(),
        )
        db.add(other_budget)
        await db.commit()

        retrieved = await service.get_budget(db, other_budget.id, test_user)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_budget(self, db, test_user):
        """Should update budget fields."""
        service = BudgetService()

        budget = await service.create_budget(
            db, test_user, "Original", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )

        updated = await service.update_budget(
            db,
            budget.id,
            test_user,
            name="Updated",
            amount=Decimal("200"),
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.amount == Decimal("200")

    @pytest.mark.asyncio
    async def test_update_budget_cross_org_blocked(self, db, test_user, second_organization):
        """Should not allow updating budgets from other orgs."""
        service = BudgetService()

        other_budget = Budget(
            id=uuid4(),
            organization_id=second_organization.id,
            name="Other",
            amount=Decimal("100"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today(),
        )
        db.add(other_budget)
        await db.commit()

        updated = await service.update_budget(db, other_budget.id, test_user, name="Hacked")

        assert updated is None

    @pytest.mark.asyncio
    async def test_delete_budget(self, db, test_user):
        """Should delete budget."""
        service = BudgetService()

        budget = await service.create_budget(
            db, test_user, "To Delete", Decimal("100"), BudgetPeriod.MONTHLY, date.today()
        )
        budget_id = budget.id

        success = await service.delete_budget(db, budget_id, test_user)
        assert success is True

        # Verify deleted
        retrieved = await service.get_budget(db, budget_id, test_user)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_budget_cross_org_blocked(self, db, test_user, second_organization):
        """Should not allow deleting budgets from other orgs."""
        service = BudgetService()

        other_budget = Budget(
            id=uuid4(),
            organization_id=second_organization.id,
            name="Other",
            amount=Decimal("100"),
            period=BudgetPeriod.MONTHLY,
            start_date=date.today(),
        )
        db.add(other_budget)
        await db.commit()

        success = await service.delete_budget(db, other_budget.id, test_user)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_budget_spending(self, db, test_user, test_account):
        """Should calculate spending for budget."""
        service = BudgetService()

        # Create monthly budget
        budget = await service.create_budget(
            db, test_user, "Monthly", Decimal("500.00"), BudgetPeriod.MONTHLY, date.today()
        )

        # Get current month dates
        period_start, period_end = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Create transactions in current month
        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start + timedelta(days=5),
            amount=Decimal("-100.00"),
            merchant_name="Store 1",
            deduplication_hash=str(uuid4()),
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start + timedelta(days=10),
            amount=Decimal("-150.00"),
            merchant_name="Store 2",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2])
        await db.commit()

        spending = await service.get_budget_spending(db, budget.id, test_user)

        assert spending["budget_amount"] == Decimal("500.00")
        assert spending["spent"] == Decimal("250.00")  # 100 + 150
        assert spending["remaining"] == Decimal("250.00")  # 500 - 250
        assert spending["percentage"] == Decimal("50.00")  # 250/500 * 100

    @pytest.mark.asyncio
    async def test_get_budget_spending_category_specific(self, db, test_user, test_account):
        """Should only count transactions in budget's category."""
        service = BudgetService()

        # Create category
        category = Category(
            organization_id=test_user.organization_id,
            name="Food",
        )
        db.add(category)
        await db.commit()

        # Create category-specific budget
        budget = await service.create_budget(
            db,
            test_user,
            "Food Budget",
            Decimal("300.00"),
            BudgetPeriod.MONTHLY,
            date.today(),
            category_id=category.id,
        )

        period_start, period_end = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Transaction in category
        food_txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start + timedelta(days=5),
            amount=Decimal("-50.00"),
            merchant_name="Grocery",
            category_id=category.id,
            deduplication_hash=str(uuid4()),
        )
        # Transaction in different category
        other_txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start + timedelta(days=5),
            amount=Decimal("-100.00"),
            merchant_name="Gas Station",
            category_id=None,
            deduplication_hash=str(uuid4()),
        )
        db.add_all([food_txn, other_txn])
        await db.commit()

        spending = await service.get_budget_spending(db, budget.id, test_user)

        # Should only count food transaction
        assert spending["spent"] == Decimal("50.00")

    @pytest.mark.asyncio
    async def test_get_budget_spending_no_transactions(self, db, test_user):
        """Should handle budget with no spending."""
        service = BudgetService()

        budget = await service.create_budget(
            db, test_user, "Empty", Decimal("500.00"), BudgetPeriod.MONTHLY, date.today()
        )

        spending = await service.get_budget_spending(db, budget.id, test_user)

        assert spending["spent"] == Decimal("0.00")
        assert spending["remaining"] == Decimal("500.00")
        assert spending["percentage"] == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_check_budget_alerts_under_threshold(self, db, test_user, test_account):
        """Should not create alert when under threshold."""
        service = BudgetService()

        # Create budget with 80% threshold
        budget = await service.create_budget(
            db,
            test_user,
            "Test",
            Decimal("1000.00"),
            BudgetPeriod.MONTHLY,
            date.today(),
            alert_threshold=Decimal("0.80"),
        )

        period_start, _ = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Spend 70% (under threshold)
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start,
            amount=Decimal("-700.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add(txn)
        await db.commit()

        alerts = await service.check_budget_alerts(db, test_user)

        # Should not trigger alert
        assert len(alerts) == 0

    @pytest.mark.asyncio
    async def test_check_budget_alerts_at_threshold(self, db, test_user, test_account):
        """Should create alert when at threshold."""
        service = BudgetService()

        budget = await service.create_budget(
            db,
            test_user,
            "Test",
            Decimal("1000.00"),
            BudgetPeriod.MONTHLY,
            date.today(),
            alert_threshold=Decimal("0.80"),
        )

        period_start, _ = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Spend exactly 80%
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start,
            amount=Decimal("-800.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add(txn)
        await db.commit()

        alerts = await service.check_budget_alerts(db, test_user)

        # Should trigger alert
        assert len(alerts) > 0
        alert = alerts[0]
        assert alert["budget"].id == budget.id

    @pytest.mark.asyncio
    async def test_check_budget_alerts_over_budget(self, db, test_user, test_account):
        """Should create high priority alert when over budget."""
        service = BudgetService()

        budget = await service.create_budget(
            db,
            test_user,
            "Test",
            Decimal("1000.00"),
            BudgetPeriod.MONTHLY,
            date.today(),
            alert_threshold=Decimal("0.80"),
        )

        period_start, _ = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Spend 110%
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start,
            amount=Decimal("-1100.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add(txn)
        await db.commit()

        alerts = await service.check_budget_alerts(db, test_user)

        assert len(alerts) > 0
        # Verify notification was created
        from app.models.notification import Notification
        from sqlalchemy import select

        result = await db.execute(
            select(Notification).where(
                Notification.organization_id == test_user.organization_id,
                Notification.type == NotificationType.BUDGET_ALERT,
            )
        )
        notification = result.scalar_one_or_none()
        assert notification is not None
        assert "Test" in notification.title

    @pytest.mark.asyncio
    async def test_check_budget_alerts_ignores_inactive(self, db, test_user, test_account):
        """Should ignore inactive budgets."""
        service = BudgetService()

        # Create inactive budget
        budget = await service.create_budget(
            db, test_user, "Inactive", Decimal("100.00"), BudgetPeriod.MONTHLY, date.today()
        )
        budget.is_active = False
        await db.commit()

        period_start, _ = service._get_period_dates(BudgetPeriod.MONTHLY)

        # Overspend
        txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=period_start,
            amount=Decimal("-200.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add(txn)
        await db.commit()

        alerts = await service.check_budget_alerts(db, test_user)

        # Should not create alert for inactive budget
        inactive_alerts = [a for a in alerts if a["budget"].id == budget.id]
        assert len(inactive_alerts) == 0

    def test_singleton_instance(self):
        """Should provide singleton instance."""
        from app.services.budget_service import budget_service

        assert budget_service is not None
        assert isinstance(budget_service, BudgetService)
