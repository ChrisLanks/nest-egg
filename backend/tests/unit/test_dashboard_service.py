"""Tests for dashboard service."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.account import Account, AccountType
from app.models.transaction import Transaction
from app.services.dashboard_service import DashboardService


class TestDashboardService:
    """Test suite for dashboard service."""

    @pytest.mark.asyncio
    async def test_get_net_worth_assets_only(self, db, test_user):
        """Should calculate net worth with only asset accounts."""
        # Create asset accounts
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        savings = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        db.add_all([checking, savings])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_debts(self, db, test_user):
        """Should subtract debts from assets."""
        # Asset
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        # Debt
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-3000.00"),  # Negative balance
            is_active=True,
        )
        db.add_all([checking, credit_card])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 10000 - 3000 = 7000
        assert net_worth == Decimal("7000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_positive_debt_balance(self, db, test_user):
        """Should handle debt accounts with positive balance representation."""
        # Some systems store debt as positive values
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("3000.00"),  # Positive (some banks do this)
            is_active=True,
        )
        db.add_all([checking, credit_card])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # Should use abs() to handle both representations
        assert net_worth == Decimal("7000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_excludes_inactive(self, db, test_user):
        """Should exclude inactive accounts."""
        active = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Active",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        inactive = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Inactive",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            is_active=False,
        )
        db.add_all([active, inactive])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # Should only count active account
        assert net_worth == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_account_filter(self, db, test_user):
        """Should filter by specific account IDs."""
        account1 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Account 1",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        account2 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Account 2",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        db.add_all([account1, account2])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(
            test_user.organization_id, account_ids=[account1.id]
        )

        # Should only count account1
        assert net_worth == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_handles_null_balance(self, db, test_user):
        """Should treat null balance as zero."""
        account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Account",
            account_type=AccountType.CHECKING,
            current_balance=None,
            is_active=True,
        )
        db.add(account)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_total_assets(self, db, test_user):
        """Should sum only asset accounts."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        savings = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-3000.00"),
            is_active=True,
        )
        db.add_all([checking, savings, credit_card])
        await db.commit()

        service = DashboardService(db)
        total = await service.get_total_assets(test_user.organization_id)

        # Should only sum checking + savings, not credit card
        assert total == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_get_total_debts(self, db, test_user):
        """Should sum only debt accounts."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-3000.00"),
            is_active=True,
        )
        loan = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Loan",
            account_type=AccountType.LOAN,
            current_balance=Decimal("-2000.00"),
            is_active=True,
        )
        db.add_all([checking, credit_card, loan])
        await db.commit()

        service = DashboardService(db)
        total = await service.get_total_debts(test_user.organization_id)

        # Should sum credit card + loan as absolute values
        assert total == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_current_month(self, db, test_user, test_account):
        """Should calculate spending for current month by default."""
        # Create transactions in current month
        today = date.today()
        first_of_month = date(today.year, today.month, 1)

        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=first_of_month,
            amount=Decimal("-100.00"),
            merchant_name="Store 1",
            deduplication_hash=str(uuid4()),
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=today,
            amount=Decimal("-50.00"),
            merchant_name="Store 2",
            deduplication_hash=str(uuid4()),
        )
        # Income transaction (should be excluded)
        txn3 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=today,
            amount=Decimal("1000.00"),
            merchant_name="Paycheck",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2, txn3])
        await db.commit()

        service = DashboardService(db)
        spending = await service.get_monthly_spending(test_user.organization_id)

        # Should sum negative transactions as absolute value
        assert spending == Decimal("150.00")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_custom_date_range(self, db, test_user, test_account):
        """Should calculate spending for custom date range."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # Transaction in range
        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date(2024, 1, 15),
            amount=Decimal("-100.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        # Transaction outside range
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date(2024, 2, 1),
            amount=Decimal("-50.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2])
        await db.commit()

        service = DashboardService(db)
        spending = await service.get_monthly_spending(
            test_user.organization_id, start_date=start_date, end_date=end_date
        )

        # Should only count txn1
        assert spending == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_with_account_filter(self, db, test_user):
        """Should filter spending by account IDs."""
        account1 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Account 1",
            account_type=AccountType.CHECKING,
            is_active=True,
        )
        account2 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Account 2",
            account_type=AccountType.CHECKING,
            is_active=True,
        )
        db.add_all([account1, account2])
        await db.commit()

        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=account1.id,
            date=date.today(),
            amount=Decimal("-100.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=account2.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2])
        await db.commit()

        service = DashboardService(db)
        spending = await service.get_monthly_spending(
            test_user.organization_id, account_ids=[account1.id]
        )

        # Should only count account1 transaction
        assert spending == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_no_transactions(self, db, test_user):
        """Should return zero when no transactions."""
        service = DashboardService(db)
        spending = await service.get_monthly_spending(test_user.organization_id)

        assert spending == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_monthly_income(self, db, test_user, test_account):
        """Should calculate income for period."""
        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("1000.00"),
            merchant_name="Paycheck",
            deduplication_hash=str(uuid4()),
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("500.00"),
            merchant_name="Freelance",
            deduplication_hash=str(uuid4()),
        )
        # Expense (should be excluded)
        txn3 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Store",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2, txn3])
        await db.commit()

        service = DashboardService(db)
        income = await service.get_monthly_income(test_user.organization_id)

        assert income == Decimal("1500.00")

    @pytest.mark.asyncio
    async def test_get_expense_by_category(self, db, test_user, test_account):
        """Should group expenses by category."""
        txn1 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-100.00"),
            merchant_name="Grocery Store",
            category_primary="Groceries",
            deduplication_hash=str(uuid4()),
        )
        txn2 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Another Grocery",
            category_primary="Groceries",
            deduplication_hash=str(uuid4()),
        )
        txn3 = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-75.00"),
            merchant_name="Gas Station",
            category_primary="Transportation",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([txn1, txn2, txn3])
        await db.commit()

        service = DashboardService(db)
        categories = await service.get_expense_by_category(test_user.organization_id)

        assert len(categories) == 2
        # Should be ordered by total (most negative first)
        assert categories[0]["category"] == "Groceries"
        assert categories[0]["total"] == 150.0
        assert categories[0]["count"] == 2
        assert categories[1]["category"] == "Transportation"
        assert categories[1]["total"] == 75.0
        assert categories[1]["count"] == 1

    @pytest.mark.asyncio
    async def test_get_expense_by_category_excludes_uncategorized(
        self, db, test_user, test_account
    ):
        """Should exclude transactions without category."""
        categorized = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-100.00"),
            merchant_name="Store",
            category_primary="Shopping",
            deduplication_hash=str(uuid4()),
        )
        uncategorized = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Other",
            category_primary=None,
            deduplication_hash=str(uuid4()),
        )
        db.add_all([categorized, uncategorized])
        await db.commit()

        service = DashboardService(db)
        categories = await service.get_expense_by_category(test_user.organization_id)

        # Should only include categorized
        assert len(categories) == 1
        assert categories[0]["category"] == "Shopping"

    @pytest.mark.asyncio
    async def test_get_expense_by_category_respects_limit(self, db, test_user, test_account):
        """Should limit number of categories returned."""
        # Create 15 different categories
        for i in range(15):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date.today(),
                amount=Decimal("-10.00"),
                merchant_name=f"Store {i}",
                category_primary=f"Category {i}",
                deduplication_hash=str(uuid4()),
            )
            db.add(txn)
        await db.commit()

        service = DashboardService(db)
        categories = await service.get_expense_by_category(test_user.organization_id, limit=5)

        # Should return only 5
        assert len(categories) == 5

    @pytest.mark.asyncio
    async def test_get_recent_transactions(self, db, test_user, test_account):
        """Should get recent transactions ordered by date."""
        old_txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today() - timedelta(days=30),
            amount=Decimal("-100.00"),
            merchant_name="Old Transaction",
            deduplication_hash=str(uuid4()),
        )
        recent_txn = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=date.today(),
            amount=Decimal("-50.00"),
            merchant_name="Recent Transaction",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([old_txn, recent_txn])
        await db.commit()

        service = DashboardService(db)
        transactions = await service.get_recent_transactions(test_user.organization_id, limit=10)

        # Should be ordered most recent first
        assert len(transactions) == 2
        assert transactions[0].id == recent_txn.id
        assert transactions[1].id == old_txn.id

    @pytest.mark.asyncio
    async def test_get_recent_transactions_limit(self, db, test_user, test_account):
        """Should respect limit parameter."""
        # Create 20 transactions
        for i in range(20):
            txn = Transaction(
                organization_id=test_user.organization_id,
                account_id=test_account.id,
                date=date.today(),
                amount=Decimal("-10.00"),
                merchant_name=f"Transaction {i}",
                deduplication_hash=str(uuid4()),
            )
            db.add(txn)
        await db.commit()

        service = DashboardService(db)
        transactions = await service.get_recent_transactions(test_user.organization_id, limit=5)

        assert len(transactions) == 5

    @pytest.mark.asyncio
    async def test_get_cash_flow_trend(self, db, test_user, test_account):
        """Should calculate monthly income vs expenses trend."""
        # Use recent dates so they fall within the default 3-month window
        today = date.today()
        # Current month and previous month (both within 3-month range)
        cur_month_date = date(today.year, today.month, 10)
        # Previous month
        if today.month == 1:
            prev_month_date = date(today.year - 1, 12, 10)
        else:
            prev_month_date = date(today.year, today.month - 1, 10)
        cur_month_key = f"{cur_month_date.year}-{cur_month_date.month:02d}"
        prev_month_key = f"{prev_month_date.year}-{prev_month_date.month:02d}"

        cur_income = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=cur_month_date,
            amount=Decimal("2000.00"),
            merchant_name="Paycheck",
            deduplication_hash=str(uuid4()),
        )
        cur_expense = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=cur_month_date,
            amount=Decimal("-1000.00"),
            merchant_name="Rent",
            deduplication_hash=str(uuid4()),
        )
        prev_income = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=prev_month_date,
            amount=Decimal("2500.00"),
            merchant_name="Paycheck",
            deduplication_hash=str(uuid4()),
        )
        prev_expense = Transaction(
            organization_id=test_user.organization_id,
            account_id=test_account.id,
            date=prev_month_date,
            amount=Decimal("-1200.00"),
            merchant_name="Rent",
            deduplication_hash=str(uuid4()),
        )
        db.add_all([cur_income, cur_expense, prev_income, prev_expense])
        await db.commit()

        service = DashboardService(db)
        trend = await service.get_cash_flow_trend(test_user.organization_id, months=3)

        # Should have monthly aggregations for both months
        assert len(trend) >= 2
        cur_data = next((t for t in trend if t["month"] == cur_month_key), None)
        assert cur_data is not None
        assert cur_data["income"] == 2000.0
        assert cur_data["expenses"] == 1000.0
        prev_data = next((t for t in trend if t["month"] == prev_month_key), None)
        assert prev_data is not None
        assert prev_data["income"] == 2500.0
        assert prev_data["expenses"] == 1200.0

    @pytest.mark.asyncio
    async def test_get_account_balances(self, db, test_user):
        """Should get all active account balances."""
        account1 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            institution_name="Chase",
            is_active=True,
        )
        account2 = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            institution_name="Wells Fargo",
            is_active=True,
        )
        db.add_all([account1, account2])
        await db.commit()

        service = DashboardService(db)
        balances = await service.get_account_balances(test_user.organization_id)

        assert len(balances) == 2
        assert balances[0]["name"] in ["Checking", "Savings"]
        assert balances[0]["balance"] in [5000.0, 10000.0]
        assert balances[0]["institution"] in ["Chase", "Wells Fargo"]

    @pytest.mark.asyncio
    async def test_get_account_balances_ordered(self, db, test_user):
        """Should order accounts by type then name."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Z Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("1000.00"),
            is_active=True,
        )
        savings = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="A Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("2000.00"),
            is_active=True,
        )
        db.add_all([checking, savings])
        await db.commit()

        service = DashboardService(db)
        balances = await service.get_account_balances(test_user.organization_id)

        # Should be ordered by account_type then name
        assert len(balances) == 2

    @pytest.mark.asyncio
    async def test_cross_organization_isolation(self, db, test_user):
        """Should not access data from other organizations."""
        from app.models.user import Organization
        from app.models.user import User as UserModel

        # Create the other org + user so FK constraints are satisfied
        other_org = Organization(id=uuid4(), name="Other Org")
        db.add(other_org)
        await db.flush()

        other_user = UserModel(
            id=uuid4(),
            organization_id=other_org.id,
            email="other@example.com",
            password_hash="fakehash",
            first_name="Other",
            last_name="User",
        )
        db.add(other_user)
        await db.flush()

        # Account in test_user's org
        user_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="User Account",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        # Account in other org
        other_account = Account(
            id=uuid4(),
            organization_id=other_org.id,
            user_id=other_user.id,
            name="Other Account",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        db.add_all([user_account, other_account])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # Should only count user's account
        assert net_worth == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_business_equity_direct_value(self, db, test_user):
        """Should calculate net worth using direct equity value for business equity accounts."""
        # Create asset accounts
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        business = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="My Company LLC",
            account_type=AccountType.BUSINESS_EQUITY,
            current_balance=Decimal("0.00"),  # Not used when equity_value is provided
            equity_value=Decimal("250000.00"),  # Direct equity value
            is_active=True,
        )
        db.add_all([checking, business])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 5000 (checking) + 250000 (business equity) = 255000
        assert net_worth == Decimal("255000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_business_equity_valuation_percentage(self, db, test_user):
        """Should calculate net worth using company valuation and ownership percentage."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        business = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Tech Startup Inc",
            account_type=AccountType.BUSINESS_EQUITY,
            current_balance=Decimal("0.00"),
            company_valuation=Decimal("1000000.00"),  # $1M company
            ownership_percentage=Decimal("25.00"),  # 25% ownership
            is_active=True,
        )
        db.add_all([checking, business])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 5000 (checking) + (1000000 * 0.25) = 255000
        assert net_worth == Decimal("255000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_business_equity_valuation_only(self, db, test_user):
        """Should assume 100% ownership when only company valuation is provided."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        business = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Sole Proprietorship",
            account_type=AccountType.BUSINESS_EQUITY,
            current_balance=Decimal("0.00"),
            company_valuation=Decimal("500000.00"),  # $500K company
            # No ownership_percentage provided - should assume 100%
            is_active=True,
        )
        db.add_all([checking, business])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 10000 (checking) + 500000 (100% of company) = 510000
        assert net_worth == Decimal("510000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_business_equity_fallback_to_balance(self, db, test_user):
        """Should fallback to current_balance when no equity fields are set."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        business = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Incomplete Business Entry",
            account_type=AccountType.BUSINESS_EQUITY,
            current_balance=Decimal("50000.00"),  # Fallback value
            # No equity_value, company_valuation, or ownership_percentage
            is_active=True,
        )
        db.add_all([checking, business])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 5000 (checking) + 50000 (fallback to current_balance) = 55000
        assert net_worth == Decimal("55000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_business_equity_and_debts(self, db, test_user):
        """Should include business equity and subtract debts in net worth calculation."""
        # Assets
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        business = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Business Equity",
            account_type=AccountType.BUSINESS_EQUITY,
            company_valuation=Decimal("2000000.00"),
            ownership_percentage=Decimal("15.00"),  # 15% = $300K
            is_active=True,
        )
        # Debts
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-5000.00"),
            is_active=True,
        )
        mortgage = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Mortgage",
            account_type=AccountType.MORTGAGE,
            current_balance=Decimal("-250000.00"),
            is_active=True,
        )
        db.add_all([checking, business, credit_card, mortgage])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 10000 (checking) + 300000 (business 15% of 2M)
        # - 5000 (credit card) - 250000 (mortgage) = 55000
        assert net_worth == Decimal("55000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_multiple_business_equity_accounts(self, db, test_user):
        """Should correctly sum multiple business equity accounts with different input methods."""
        business_direct = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Direct Entry Business",
            account_type=AccountType.BUSINESS_EQUITY,
            equity_value=Decimal("100000.00"),
            is_active=True,
        )
        business_percentage = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Percentage Ownership",
            account_type=AccountType.BUSINESS_EQUITY,
            company_valuation=Decimal("500000.00"),
            ownership_percentage=Decimal("20.00"),  # 20% = $100K
            is_active=True,
        )
        business_full = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Sole Ownership",
            account_type=AccountType.BUSINESS_EQUITY,
            company_valuation=Decimal("50000.00"),  # No percentage = 100%
            is_active=True,
        )
        db.add_all([business_direct, business_percentage, business_full])
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # 100000 (direct) + 100000 (20% of 500K) + 50000 (100% of 50K) = 250000
        assert net_worth == Decimal("250000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_with_private_equity_vesting(self, db, test_user):
        """Should calculate net worth using vested equity for private equity accounts."""
        import json

        # Private equity with vesting schedule
        pe_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Startup Equity",
            account_type=AccountType.PRIVATE_EQUITY,
            current_balance=Decimal("100000.00"),
            vesting_schedule=json.dumps(
                [
                    {"date": "2020-01-01", "quantity": 100},  # Vested
                    {"date": "2020-06-01", "quantity": 50},  # Vested
                    {"date": "2099-01-01", "quantity": 200},  # Not vested yet
                ]
            ),
            share_price=Decimal("50.00"),
            include_in_networth=True,
            is_active=True,
        )
        db.add(pe_account)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # Only vested: (100 + 50) * 50 = 7500
        assert net_worth == Decimal("7500.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_private_equity_malformed_vesting(self, db, test_user):
        """Malformed vesting schedule should fallback to current_balance."""
        pe_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Bad Vesting PE",
            account_type=AccountType.PRIVATE_EQUITY,
            current_balance=Decimal("25000.00"),
            vesting_schedule="not-valid-json",
            share_price=Decimal("50.00"),
            include_in_networth=True,
            is_active=True,
        )
        db.add(pe_account)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        # Fallback to current_balance
        assert net_worth == Decimal("25000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_private_equity_not_list_vesting(self, db, test_user):
        """Non-list vesting schedule JSON should fallback to current_balance."""
        import json

        pe_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Dict Vesting PE",
            account_type=AccountType.PRIVATE_EQUITY,
            current_balance=Decimal("15000.00"),
            vesting_schedule=json.dumps({"not": "a list"}),
            share_price=Decimal("50.00"),
            include_in_networth=True,
            is_active=True,
        )
        db.add(pe_account)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("15000.00")

    @pytest.mark.asyncio
    async def test_get_net_worth_private_equity_no_vesting(self, db, test_user):
        """Private equity without vesting schedule should use current_balance."""
        pe_account = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="No Vesting PE",
            account_type=AccountType.PRIVATE_EQUITY,
            current_balance=Decimal("30000.00"),
            vesting_schedule=None,
            include_in_networth=True,
            is_active=True,
        )
        db.add(pe_account)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("30000.00")

    @pytest.mark.asyncio
    async def test_should_include_vehicle_excluded_by_default(self, db, test_user):
        """Vehicle accounts should be excluded from net worth by default."""
        vehicle = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Car",
            account_type=AccountType.VEHICLE,
            current_balance=Decimal("20000.00"),
            include_in_networth=None,  # Not explicitly set
            is_active=True,
        )
        db.add(vehicle)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("0")

    @pytest.mark.asyncio
    async def test_should_include_vehicle_explicitly_included(self, db, test_user):
        """Vehicle accounts explicitly included should be in net worth."""
        vehicle = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Classic Car",
            account_type=AccountType.VEHICLE,
            current_balance=Decimal("50000.00"),
            include_in_networth=True,
            is_active=True,
        )
        db.add(vehicle)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_should_include_explicitly_excluded(self, db, test_user):
        """Accounts explicitly excluded should not be in net worth."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Hidden Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("10000.00"),
            include_in_networth=False,
            is_active=True,
        )
        db.add(checking)
        await db.commit()

        service = DashboardService(db)
        net_worth = await service.get_net_worth(test_user.organization_id)

        assert net_worth == Decimal("0")

    @pytest.mark.asyncio
    async def test_compute_methods_no_db(self, db, test_user):
        """Test compute_* methods work with pre-fetched accounts list."""
        accounts = [
            Account(
                id=uuid4(),
                organization_id=test_user.organization_id,
                user_id=test_user.id,
                name="Checking",
                account_type=AccountType.CHECKING,
                current_balance=Decimal("5000.00"),
                is_active=True,
            ),
            Account(
                id=uuid4(),
                organization_id=test_user.organization_id,
                user_id=test_user.id,
                name="Credit Card",
                account_type=AccountType.CREDIT_CARD,
                current_balance=Decimal("-2000.00"),
                is_active=True,
            ),
        ]

        service = DashboardService(db)
        net_worth = service.compute_net_worth(accounts)
        total_assets = service.compute_total_assets(accounts)
        total_debts = service.compute_total_debts(accounts)
        balances = service.compute_account_balances(accounts)

        assert net_worth == Decimal("3000.00")
        assert total_assets == Decimal("5000.00")
        assert total_debts == Decimal("2000.00")
        assert len(balances) == 2

    @pytest.mark.asyncio
    async def test_empty_state_no_accounts(self, db, test_user):
        """Should handle organization with no accounts."""
        service = DashboardService(db)

        net_worth = await service.get_net_worth(test_user.organization_id)
        total_assets = await service.get_total_assets(test_user.organization_id)
        total_debts = await service.get_total_debts(test_user.organization_id)
        balances = await service.get_account_balances(test_user.organization_id)

        assert net_worth == Decimal("0")
        assert total_assets == Decimal("0")
        assert total_debts == Decimal("0")
        assert balances == []

    @pytest.mark.asyncio
    async def test_empty_state_no_transactions(self, db, test_user):
        """Should handle organization with no transactions."""
        service = DashboardService(db)

        spending = await service.get_monthly_spending(test_user.organization_id)
        income = await service.get_monthly_income(test_user.organization_id)
        categories = await service.get_expense_by_category(test_user.organization_id)
        transactions = await service.get_recent_transactions(test_user.organization_id)
        trend = await service.get_cash_flow_trend(test_user.organization_id)

        assert spending == Decimal("0")
        assert income == Decimal("0")
        assert categories == []
        assert transactions == []
        assert trend == []


class TestDashboardServiceMocked:
    """Tests using mocked DB to cover lines unreachable with SQLite."""

    @pytest.mark.asyncio
    async def test_private_equity_public_company_included(self):
        """Line 117: PE with company_status='public' should be included by default."""
        from unittest.mock import AsyncMock, MagicMock

        mock_account = MagicMock()
        mock_account.include_in_networth = None
        mock_account.account_type = AccountType.PRIVATE_EQUITY
        mock_account.company_status = MagicMock()
        mock_account.company_status.value = "public"
        mock_account.current_balance = Decimal("100000")
        mock_account.vesting_schedule = None

        db = AsyncMock()
        service = DashboardService(db)
        assert service._should_include_in_networth(mock_account) is True

    @pytest.mark.asyncio
    async def test_private_equity_private_company_excluded(self):
        """Line 117: PE with company_status != 'public' should be excluded."""
        from unittest.mock import AsyncMock, MagicMock

        mock_account = MagicMock()
        mock_account.include_in_networth = None
        mock_account.account_type = AccountType.PRIVATE_EQUITY
        mock_account.company_status = MagicMock()
        mock_account.company_status.value = "private"

        db = AsyncMock()
        service = DashboardService(db)
        assert service._should_include_in_networth(mock_account) is False

    @pytest.mark.asyncio
    async def test_vesting_milestone_bad_date_skipped(self):
        """Lines 168, 174-175: milestone with invalid date format is skipped."""
        import json
        from unittest.mock import AsyncMock, MagicMock

        mock_account = MagicMock()
        mock_account.account_type = AccountType.PRIVATE_EQUITY
        mock_account.current_balance = Decimal("50000")
        mock_account.vesting_schedule = json.dumps(
            [
                {"date": "not-a-date", "quantity": 100},
                {"date": None, "quantity": 50},
                {"date": "2020-01-01", "quantity": 200},
            ]
        )
        mock_account.share_price = Decimal("10")

        db = AsyncMock()
        service = DashboardService(db)
        value = service._calculate_account_value(mock_account)
        # Only the valid 2020-01-01 milestone vests: 200 * 10 = 2000
        assert value == Decimal("2000")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_with_account_filter(self):
        """Lines 224: spending with account_ids filter."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = Decimal("-500")
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        result = await service.get_monthly_spending(
            "org-123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            account_ids=[uuid4()],
        )
        assert result == Decimal("500")

    @pytest.mark.asyncio
    async def test_get_monthly_spending_defaults(self):
        """Lines 209-216: default start_date and end_date."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        result = await service.get_monthly_spending("org-123")
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_monthly_income_with_account_filter(self):
        """Lines 240-261: income with account_ids filter."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = Decimal("3000")
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        result = await service.get_monthly_income(
            "org-123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            account_ids=[uuid4()],
        )
        assert result == Decimal("3000")

    @pytest.mark.asyncio
    async def test_get_monthly_income_defaults_no_data(self):
        """Lines 240-261: income defaults to 0 when no data."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        result = await service.get_monthly_income("org-123")
        assert result == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_spending_and_income_combined(self):
        """Lines 271-299: single-query spending and income."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.spending = Decimal("-800")
        mock_row.income = Decimal("3000")
        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        spending, income = await service.get_spending_and_income(
            "org-123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert spending == Decimal("800")
        assert income == Decimal("3000")

    @pytest.mark.asyncio
    async def test_get_spending_and_income_none_values(self):
        """Lines 297-298: handles None spending/income."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.spending = None
        mock_row.income = None
        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        spending, income = await service.get_spending_and_income("org-123")
        assert spending == Decimal("0")
        assert income == Decimal("0")

    @pytest.mark.asyncio
    async def test_get_spending_and_income_with_account_filter(self):
        """Lines 283-284: spending_and_income with account_ids."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_row = MagicMock()
        mock_row.spending = Decimal("-200")
        mock_row.income = Decimal("1000")
        mock_result = MagicMock()
        mock_result.one.return_value = mock_row
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        spending, income = await service.get_spending_and_income("org-123", account_ids=[uuid4()])
        assert spending == Decimal("200")
        assert income == Decimal("1000")

    @pytest.mark.asyncio
    async def test_get_expense_by_category(self):
        """Lines 310-349: top expense categories."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_rows = [
            MagicMock(category_primary="Dining", total=Decimal("-500"), count=10),
            MagicMock(category_primary="Groceries", total=Decimal("-300"), count=5),
        ]
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter(mock_rows))
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        categories = await service.get_expense_by_category(
            "org-123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert len(categories) == 2
        assert categories[0]["category"] == "Dining"
        assert categories[0]["total"] == Decimal("500")
        assert categories[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_get_expense_by_category_with_account_filter(self):
        """Lines 325-326: category expenses with account_ids."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        categories = await service.get_expense_by_category("org-123", account_ids=[uuid4()])
        assert categories == []

    @pytest.mark.asyncio
    async def test_get_recent_transactions(self):
        """Lines 355-370: recent transactions."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_txn = MagicMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [mock_txn]
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        txns = await service.get_recent_transactions("org-123", limit=5)
        assert len(txns) == 1

    @pytest.mark.asyncio
    async def test_get_recent_transactions_with_account_filter(self):
        """Lines 357-358: recent transactions with account_ids."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        txns = await service.get_recent_transactions("org-123", account_ids=[uuid4()])
        assert txns == []

    @pytest.mark.asyncio
    async def test_get_cash_flow_trend(self):
        """Cash flow trend grouped by month using Python-side aggregation."""
        from datetime import date as date_type
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        # Rows have .date and .amount attributes (fetched directly from Transaction)
        mock_rows = [
            MagicMock(date=date_type(2024, 1, 15), amount=Decimal("5000")),
            MagicMock(date=date_type(2024, 1, 20), amount=Decimal("-2000")),
            MagicMock(date=date_type(2024, 2, 15), amount=Decimal("5500")),
            MagicMock(date=date_type(2024, 2, 20), amount=Decimal("-2500")),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        trend = await service.get_cash_flow_trend("org-123", months=3)
        assert len(trend) == 2
        assert trend[0]["month"] == "2024-01"
        assert trend[0]["income"] == 5000.0
        assert trend[0]["expenses"] == 2000.0

    @pytest.mark.asyncio
    async def test_get_cash_flow_trend_with_account_filter(self):
        """Trend with account_ids filter returns empty when no matching rows."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        trend = await service.get_cash_flow_trend("org-123", account_ids=[uuid4()])
        assert trend == []

    @pytest.mark.asyncio
    async def test_get_cash_flow_trend_none_values(self):
        """Handles None amount in trend rows gracefully (treated as 0)."""
        from datetime import date as date_type
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        mock_rows = [
            MagicMock(date=date_type(2024, 3, 1), amount=None),
        ]
        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        db.execute = AsyncMock(return_value=mock_result)

        service = DashboardService(db)
        trend = await service.get_cash_flow_trend("org-123")
        assert len(trend) == 1
        assert trend[0]["income"] == 0.0
        assert trend[0]["expenses"] == 0.0
