"""Unit tests for accounts API endpoints."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from decimal import Decimal

from fastapi import HTTPException

from app.api.v1.accounts import (
    list_accounts,
    get_account,
    create_manual_account,
    bulk_update_visibility,
    update_account,
    bulk_delete_accounts,
    BulkVisibilityUpdate,
)
from app.models.user import User
from app.models.account import Account, AccountType, AccountSource
from app.schemas.account import ManualAccountCreate, AccountUpdate


@pytest.mark.unit
class TestListAccounts:
    """Test list_accounts endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def mock_account(self):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.name = "Test Checking"
        account.account_type = AccountType.CHECKING
        account.account_source = AccountSource.PLAID
        account.property_type = None
        account.institution_name = "Test Bank"
        account.mask = "1234"
        account.current_balance = Decimal("5000.00")
        account.balance_as_of = None
        account.is_active = True
        account.exclude_from_cash_flow = False
        account.plaid_item_hash = "test-hash"
        account.plaid_item = None
        account.plaid_item_id = None
        account.teller_enrollment = None
        account.teller_enrollment_id = None
        return account

    @pytest.mark.asyncio
    async def test_lists_household_accounts_by_default(
        self, mock_db, mock_user, mock_account
    ):
        """Should list all household accounts when user_id is None."""
        with patch(
            "app.api.v1.accounts.get_all_household_accounts",
            return_value=[mock_account],
        ) as mock_get_all:
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].id == mock_account.id
            assert result[0].name == "Test Checking"
            mock_get_all.assert_called_once_with(mock_db, mock_user.organization_id)

    @pytest.mark.asyncio
    async def test_filters_by_user_when_user_id_provided(
        self, mock_db, mock_user, mock_account
    ):
        """Should filter accounts by user_id when provided."""
        user_id = uuid4()

        with patch(
            "app.api.v1.accounts.verify_household_member", return_value=None
        ) as mock_verify:
            with patch(
                "app.api.v1.accounts.get_user_accounts", return_value=[mock_account]
            ) as mock_get_user:
                result = await list_accounts(
                    include_hidden=False,
                    user_id=user_id,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert len(result) == 1
                mock_verify.assert_called_once_with(
                    mock_db, user_id, mock_user.organization_id
                )
                mock_get_user.assert_called_once_with(
                    mock_db, user_id, mock_user.organization_id
                )

    @pytest.mark.asyncio
    async def test_includes_hidden_accounts_when_flag_true(
        self, mock_db, mock_user, mock_account
    ):
        """Should include hidden (inactive) accounts when include_hidden=True."""
        mock_account.is_active = False

        # Mock database query for admin view
        mock_result = Mock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [
            mock_account
        ]
        mock_db.execute.return_value = mock_result

        result = await list_accounts(
            include_hidden=True,
            user_id=None,
            current_user=mock_user,
            db=mock_db,
        )

        assert len(result) == 1
        assert result[0].is_active is False

    @pytest.mark.asyncio
    async def test_sorts_accounts_by_name(self, mock_db, mock_user):
        """Should sort accounts alphabetically by name."""
        account1 = Mock(spec=Account)
        account1.id = uuid4()
        account1.user_id = uuid4()
        account1.name = "Zebra Account"
        account1.account_source = AccountSource.MANUAL
        account1.account_type = AccountType.CHECKING
        account1.property_type = None
        account1.institution_name = "Test Bank"
        account1.mask = "1234"
        account1.current_balance = Decimal("1000")
        account1.balance_as_of = None
        account1.is_active = True
        account1.exclude_from_cash_flow = False
        account1.plaid_item_hash = None
        account1.plaid_item = None
        account1.plaid_item_id = None
        account1.teller_enrollment = None
        account1.teller_enrollment_id = None

        account2 = Mock(spec=Account)
        account2.id = uuid4()
        account2.user_id = uuid4()
        account2.name = "Apple Account"
        account2.account_source = AccountSource.MANUAL
        account2.account_type = AccountType.SAVINGS
        account2.property_type = None
        account2.institution_name = "Test Bank"
        account2.mask = "5678"
        account2.current_balance = Decimal("2000")
        account2.balance_as_of = None
        account2.is_active = True
        account2.exclude_from_cash_flow = False
        account2.plaid_item_hash = None
        account2.plaid_item = None
        account2.plaid_item_id = None
        account2.teller_enrollment = None
        account2.teller_enrollment_id = None

        with patch(
            "app.api.v1.accounts.get_all_household_accounts",
            return_value=[account1, account2],
        ):
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 2
            assert result[0].name == "Apple Account"
            assert result[1].name == "Zebra Account"

    @pytest.mark.asyncio
    async def test_includes_plaid_sync_status(self, mock_db, mock_user):
        """Should include Plaid sync status for Plaid accounts."""
        from datetime import datetime

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.name = "Plaid Checking"
        account.account_source = AccountSource.PLAID
        account.account_type = AccountType.CHECKING
        account.property_type = None
        account.institution_name = "Chase"
        account.mask = "9876"
        account.current_balance = Decimal("3000")
        account.balance_as_of = None
        account.is_active = True
        account.exclude_from_cash_flow = False
        account.plaid_item_hash = "plaid-hash"
        account.teller_enrollment = None
        account.teller_enrollment_id = None

        # Mock Plaid item
        plaid_item = Mock()
        plaid_item.last_synced_at = datetime(2024, 1, 1, 12, 0, 0)
        plaid_item.last_error_code = "ITEM_LOGIN_REQUIRED"
        plaid_item.last_error_message = "Credentials invalid"
        plaid_item.needs_reauth = True

        account.plaid_item = plaid_item
        account.plaid_item_id = uuid4()

        with patch(
            "app.api.v1.accounts.get_all_household_accounts", return_value=[account]
        ):
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].provider_item_id == account.plaid_item_id
            assert result[0].last_synced_at == plaid_item.last_synced_at
            assert result[0].last_error_code == "ITEM_LOGIN_REQUIRED"
            assert result[0].needs_reauth is True


@pytest.mark.unit
class TestGetAccount:
    """Test get_account endpoint."""

    @pytest.mark.asyncio
    async def test_returns_verified_account(self):
        """Should return the account from get_verified_account dependency."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = "Test Account"

        result = await get_account(account=account)

        assert result == account
        assert result.id == account.id


@pytest.mark.unit
class TestCreateManualAccount:
    """Test create_manual_account endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def manual_account_data(self):
        return ManualAccountCreate(
            name="My Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.MANUAL,
            institution="Test Bank",
            account_number_last4="1234",
            balance=Decimal("10000.00"),
        )

    @pytest.mark.asyncio
    async def test_creates_manual_account_successfully(
        self, mock_db, mock_user, manual_account_data
    ):
        """Should create a manual account with calculated hash."""
        with patch(
            "app.api.v1.accounts.deduplication_service.calculate_manual_account_hash",
            return_value="test-hash",
        ) as mock_hash:
            result = await create_manual_account(
                account_data=manual_account_data,
                current_user=mock_user,
                db=mock_db,
            )

            assert result.name == "My Checking"
            assert result.account_type == AccountType.CHECKING
            assert result.current_balance == Decimal("10000.00")
            assert result.is_manual is True
            assert result.is_active is True
            assert mock_db.add.called
            assert mock_db.commit.called
            mock_hash.assert_called_once()

    @pytest.mark.asyncio
    async def test_excludes_debt_accounts_from_cash_flow(
        self, mock_db, mock_user
    ):
        """Should exclude mortgages, loans, student loans, credit cards from cash flow."""
        for account_type in [
            AccountType.MORTGAGE,
            AccountType.LOAN,
            AccountType.STUDENT_LOAN,
            AccountType.CREDIT_CARD,
        ]:
            account_data = ManualAccountCreate(
                name=f"Test {account_type.value}",
                account_type=account_type,
                account_source=AccountSource.MANUAL,
                institution="Test Bank",
                account_number_last4="1234",
                balance=Decimal("5000.00"),
            )

            with patch(
                "app.api.v1.accounts.deduplication_service.calculate_manual_account_hash",
                return_value="hash",
            ):
                result = await create_manual_account(
                    account_data=account_data,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert result.exclude_from_cash_flow is True

    @pytest.mark.asyncio
    async def test_creates_holdings_for_investment_accounts(
        self, mock_db, mock_user
    ):
        """Should create holdings when provided for investment accounts."""
        from app.schemas.account import HoldingData

        holdings = [
            HoldingData(
                ticker="AAPL",
                shares=Decimal("10"),
                price_per_share=Decimal("150.00"),
            ),
            HoldingData(
                ticker="GOOGL",
                shares=Decimal("5"),
                price_per_share=Decimal("2800.00"),
            ),
        ]

        account_data = ManualAccountCreate(
            name="My Brokerage",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.MANUAL,
            institution="Test Broker",
            account_number_last4="5678",
            balance=Decimal("15500.00"),
            holdings=holdings,
        )

        with patch(
            "app.api.v1.accounts.deduplication_service.calculate_manual_account_hash",
            return_value="hash",
        ):
            result = await create_manual_account(
                account_data=account_data,
                current_user=mock_user,
                db=mock_db,
            )

            # Should have called db.add 3 times: 1 account + 2 holdings
            assert mock_db.add.call_count == 3
            # Should have committed twice: once for account, once for holdings
            assert mock_db.commit.call_count == 2


@pytest.mark.unit
class TestBulkUpdateVisibility:
    """Test bulk_update_visibility endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.fixture
    def mock_http_request(self):
        request = Mock()
        request.client.host = "192.168.1.1"
        return request

    @pytest.mark.asyncio
    async def test_updates_account_visibility(
        self, mock_db, mock_user, mock_http_request
    ):
        """Should update is_active for specified accounts."""
        account_ids = [uuid4(), uuid4()]
        request_data = BulkVisibilityUpdate(account_ids=account_ids, is_active=False)

        # Mock check query
        check_result = Mock()
        check_result.all.return_value = [(account_ids[0], mock_user.id, mock_user.organization_id, True)]

        # Mock update result
        update_result = Mock()
        update_result.rowcount = 2

        mock_db.execute.side_effect = [check_result, update_result]

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await bulk_update_visibility(
                request=request_data,
                http_request=mock_http_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["updated_count"] == 2
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_only_updates_owned_accounts(self, mock_db, mock_user, mock_http_request):
        """Should only update accounts owned by current user."""
        account_ids = [uuid4(), uuid4()]
        request_data = BulkVisibilityUpdate(account_ids=account_ids, is_active=True)

        # Mock check query
        check_result = Mock()
        check_result.all.return_value = []

        # Mock update result - 0 rows because user doesn't own accounts
        update_result = Mock()
        update_result.rowcount = 0

        mock_db.execute.side_effect = [check_result, update_result]

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit",
            return_value=None,
        ):
            result = await bulk_update_visibility(
                request=request_data,
                http_request=mock_http_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["updated_count"] == 0


@pytest.mark.unit
class TestUpdateAccount:
    """Test update_account endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_account(self):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.name = "Original Name"
        account.is_active = True
        account.current_balance = Decimal("1000.00")
        account.mask = "1234"
        account.exclude_from_cash_flow = False
        return account

    @pytest.mark.asyncio
    async def test_updates_account_name(self, mock_db, mock_account):
        """Should update account name."""
        update_data = AccountUpdate(name="New Name")

        result = await update_account(
            account_data=update_data, account=mock_account, db=mock_db
        )

        assert result.name == "New Name"
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_updates_is_active_flag(self, mock_db, mock_account):
        """Should update is_active flag."""
        update_data = AccountUpdate(is_active=False)

        result = await update_account(
            account_data=update_data, account=mock_account, db=mock_db
        )

        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_updates_balance(self, mock_db, mock_account):
        """Should update current_balance."""
        update_data = AccountUpdate(current_balance=Decimal("5000.00"))

        result = await update_account(
            account_data=update_data, account=mock_account, db=mock_db
        )

        assert result.current_balance == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_updates_exclude_from_cash_flow(self, mock_db, mock_account):
        """Should update exclude_from_cash_flow flag."""
        update_data = AccountUpdate(exclude_from_cash_flow=True)

        result = await update_account(
            account_data=update_data, account=mock_account, db=mock_db
        )

        assert result.exclude_from_cash_flow is True

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self, mock_db, mock_account):
        """Should update multiple fields at once."""
        update_data = AccountUpdate(
            name="New Name",
            is_active=False,
            current_balance=Decimal("2000.00"),
            mask="5678",
        )

        result = await update_account(
            account_data=update_data, account=mock_account, db=mock_db
        )

        assert result.name == "New Name"
        assert result.is_active is False
        assert result.current_balance == Decimal("2000.00")
        assert result.mask == "5678"


@pytest.mark.unit
class TestBulkDeleteAccounts:
    """Test bulk_delete_accounts endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_deletes_multiple_accounts(self, mock_db, mock_user):
        """Should delete multiple accounts at once."""
        account_ids = [uuid4(), uuid4(), uuid4()]

        delete_result = Mock()
        delete_result.rowcount = 3
        mock_db.execute.return_value = delete_result

        result = await bulk_delete_accounts(
            account_ids=account_ids, current_user=mock_user, db=mock_db
        )

        assert result["deleted_count"] == 3
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_only_deletes_owned_accounts(self, mock_db, mock_user):
        """Should only delete accounts owned by current user."""
        account_ids = [uuid4(), uuid4()]

        # Mock 0 rows deleted because user doesn't own accounts
        delete_result = Mock()
        delete_result.rowcount = 0
        mock_db.execute.return_value = delete_result

        result = await bulk_delete_accounts(
            account_ids=account_ids, current_user=mock_user, db=mock_db
        )

        assert result["deleted_count"] == 0
