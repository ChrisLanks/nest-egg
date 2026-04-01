"""Unit tests for accounts API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.accounts import (
    _ALLOWED_VALUATION_PROVIDERS,
    BulkVisibilityUpdate,
    bulk_delete_accounts,
    bulk_update_visibility,
    create_manual_account,
    get_account,
    list_accounts,
    refresh_account_valuation,
    refresh_equity_price,
    update_account,
)
from app.models.account import Account, AccountSource, AccountType
from app.models.user import User
from app.schemas.account import AccountUpdate, ManualAccountCreate


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
        # Equity / stock option fields (added in round 61)
        account.grant_type = None
        account.quantity = None
        account.strike_price = None
        account.share_price = None
        account.grant_date = None
        account.company_status = None
        account.vesting_schedule = None
        return account

    @pytest.mark.asyncio
    async def test_lists_household_accounts_by_default(self, mock_db, mock_user, mock_account):
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
    async def test_filters_by_user_when_user_id_provided(self, mock_db, mock_user, mock_account):
        """Should filter accounts by user_id when provided."""
        user_id = uuid4()

        with patch("app.api.v1.accounts.verify_household_member", return_value=None) as mock_verify:
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
                mock_verify.assert_called_once_with(mock_db, user_id, mock_user.organization_id)
                mock_get_user.assert_called_once_with(mock_db, user_id, mock_user.organization_id)

    @pytest.mark.asyncio
    async def test_includes_hidden_accounts_when_flag_true(self, mock_db, mock_user, mock_account):
        """Should include hidden (inactive) accounts when include_hidden=True."""
        mock_account.is_active = False

        # Mock database query for admin view
        mock_result = Mock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [mock_account]
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
    async def test_includes_hidden_with_user_filter(self, mock_db, mock_user, mock_account):
        """Should include hidden accounts filtered by user_id (admin view)."""
        user_id = uuid4()
        mock_account.is_active = False

        # Mock database query for admin view with user filter
        mock_result = Mock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = [mock_account]
        mock_db.execute.return_value = mock_result

        with patch("app.api.v1.accounts.verify_household_member", return_value=None) as mock_verify:
            result = await list_accounts(
                include_hidden=True,
                user_id=user_id,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            mock_verify.assert_called_once_with(mock_db, user_id, mock_user.organization_id)

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
        account1.grant_type = None
        account1.quantity = None
        account1.strike_price = None
        account1.share_price = None
        account1.grant_date = None
        account1.company_status = None
        account1.vesting_schedule = None

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
        account2.grant_type = None
        account2.quantity = None
        account2.strike_price = None
        account2.share_price = None
        account2.grant_date = None
        account2.company_status = None
        account2.vesting_schedule = None

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
        account.grant_type = None
        account.quantity = None
        account.strike_price = None
        account.share_price = None
        account.grant_date = None
        account.company_status = None
        account.vesting_schedule = None

        # Mock Plaid item
        plaid_item = Mock()
        plaid_item.last_synced_at = datetime(2024, 1, 1, 12, 0, 0)
        plaid_item.last_error_code = "ITEM_LOGIN_REQUIRED"
        plaid_item.last_error_message = "Credentials invalid"
        plaid_item.needs_reauth = True

        account.plaid_item = plaid_item
        account.plaid_item_id = uuid4()

        with patch("app.api.v1.accounts.get_all_household_accounts", return_value=[account]):
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

    @pytest.mark.asyncio
    async def test_includes_teller_sync_status(self, mock_db, mock_user):
        """Should include Teller sync status for Teller accounts."""
        from datetime import datetime

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.name = "Teller Checking"
        account.account_source = AccountSource.TELLER
        account.account_type = AccountType.CHECKING
        account.property_type = None
        account.institution_name = "Bank of America"
        account.mask = "4321"
        account.current_balance = Decimal("4000")
        account.balance_as_of = None
        account.is_active = True
        account.exclude_from_cash_flow = False
        account.plaid_item_hash = None
        account.plaid_item = None
        account.plaid_item_id = None
        account.grant_type = None
        account.quantity = None
        account.strike_price = None
        account.share_price = None
        account.grant_date = None
        account.company_status = None
        account.vesting_schedule = None

        # Mock Teller enrollment
        teller_enrollment = Mock()
        teller_enrollment.last_synced_at = datetime(2024, 2, 1, 10, 0, 0)
        teller_enrollment.last_error_code = "INVALID_CREDENTIALS"
        teller_enrollment.last_error_message = "Login failed"

        account.teller_enrollment = teller_enrollment
        account.teller_enrollment_id = uuid4()

        with patch("app.api.v1.accounts.get_all_household_accounts", return_value=[account]):
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

            assert len(result) == 1
            assert result[0].provider_item_id == account.teller_enrollment_id
            assert result[0].last_synced_at == teller_enrollment.last_synced_at
            assert result[0].last_error_code == "INVALID_CREDENTIALS"
            assert result[0].needs_reauth is False  # Teller doesn't use reauth

    @pytest.mark.asyncio
    async def test_includes_equity_fields_in_summary(self, mock_db, mock_user):
        """AccountSummary returned by list_accounts must include equity fields."""
        import json

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.name = "Startup Options"
        account.account_type = AccountType.STOCK_OPTIONS
        account.account_source = AccountSource.MANUAL
        account.property_type = None
        account.institution_name = None
        account.mask = None
        account.current_balance = Decimal("10000.00")
        account.balance_as_of = None
        account.is_active = True
        account.exclude_from_cash_flow = False
        account.plaid_item_hash = None
        account.plaid_item = None
        account.plaid_item_id = None
        account.teller_enrollment = None
        account.teller_enrollment_id = None
        # Equity fields
        account.grant_type = "iso"
        account.quantity = Decimal("1000")
        account.strike_price = Decimal("6.00")
        account.share_price = Decimal("10.00")
        account.grant_date = None
        account.company_status = "private"
        account.vesting_schedule = json.dumps([{"date": "2026-01-01", "quantity": 250}])

        with patch("app.api.v1.accounts.get_all_household_accounts", return_value=[account]):
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 1
        summary = result[0]
        assert summary.grant_type == "iso"
        assert summary.quantity == Decimal("1000")
        assert summary.strike_price == Decimal("6.00")
        assert summary.share_price == Decimal("10.00")
        assert summary.company_status == "private"
        parsed = json.loads(summary.vesting_schedule)
        assert parsed[0]["date"] == "2026-01-01"
        assert parsed[0]["quantity"] == 250

    @pytest.mark.asyncio
    async def test_equity_fields_null_for_non_equity_accounts(self, mock_db, mock_user, mock_account):
        """Non-equity accounts should return None for all equity fields."""
        mock_account.grant_type = None
        mock_account.quantity = None
        mock_account.strike_price = None
        mock_account.share_price = None
        mock_account.grant_date = None
        mock_account.company_status = None
        mock_account.vesting_schedule = None

        with patch("app.api.v1.accounts.get_all_household_accounts", return_value=[mock_account]):
            result = await list_accounts(
                include_hidden=False,
                user_id=None,
                current_user=mock_user,
                db=mock_db,
            )

        assert len(result) == 1
        summary = result[0]
        assert summary.grant_type is None
        assert summary.quantity is None
        assert summary.strike_price is None
        assert summary.share_price is None
        assert summary.company_status is None
        assert summary.vesting_schedule is None


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
    async def test_excludes_debt_accounts_from_cash_flow(self, mock_db, mock_user):
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
    async def test_collectibles_defaults_include_in_networth_to_none(self, mock_db, mock_user):
        """Collectibles without include_in_networth should store
        None (excluded by default in calculations)."""
        account_data = ManualAccountCreate(
            name="My Art Collection",
            account_type=AccountType.COLLECTIBLES,
            account_source=AccountSource.MANUAL,
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

            assert result.include_in_networth is None

    @pytest.mark.asyncio
    async def test_collectibles_include_in_networth_false_is_stored(self, mock_db, mock_user):
        """Collectibles with include_in_networth=False should store False explicitly."""
        account_data = ManualAccountCreate(
            name="My Art Collection",
            account_type=AccountType.COLLECTIBLES,
            account_source=AccountSource.MANUAL,
            balance=Decimal("5000.00"),
            include_in_networth=False,
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

            assert result.include_in_networth is False

    @pytest.mark.asyncio
    async def test_collectibles_include_in_networth_true_is_stored(self, mock_db, mock_user):
        """User can opt collectibles into net worth by setting include_in_networth=True."""
        account_data = ManualAccountCreate(
            name="My Watch Collection",
            account_type=AccountType.COLLECTIBLES,
            account_source=AccountSource.MANUAL,
            balance=Decimal("25000.00"),
            include_in_networth=True,
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

            assert result.include_in_networth is True

    @pytest.mark.asyncio
    async def test_other_account_include_in_networth_false_is_stored(self, mock_db, mock_user):
        """Other/manual accounts with include_in_networth=False should store False."""
        account_data = ManualAccountCreate(
            name="Miscellaneous Assets",
            account_type=AccountType.OTHER,
            account_source=AccountSource.MANUAL,
            balance=Decimal("1000.00"),
            include_in_networth=False,
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

            assert result.include_in_networth is False

    @pytest.mark.asyncio
    async def test_create_negates_positive_balance_for_debt_account(self, mock_db, mock_user):
        """Positive balance entered for a debt account must be stored as negative."""
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
                balance=Decimal("10000.00"),
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

            assert result.current_balance == Decimal(
                "-10000.00"
            ), f"{account_type.value} with positive balance should be negated"

    @pytest.mark.asyncio
    async def test_create_keeps_negative_balance_for_debt_account(self, mock_db, mock_user):
        """Already-negative balance for a debt account should be stored as-is."""
        account_data = ManualAccountCreate(
            name="My Mortgage",
            account_type=AccountType.MORTGAGE,
            account_source=AccountSource.MANUAL,
            balance=Decimal("-330000.00"),
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

        assert result.current_balance == Decimal("-330000.00")

    @pytest.mark.asyncio
    async def test_create_keeps_positive_balance_for_asset_account(self, mock_db, mock_user):
        """Positive balance for a non-debt account must NOT be negated."""
        account_data = ManualAccountCreate(
            name="My Savings",
            account_type=AccountType.SAVINGS,
            account_source=AccountSource.MANUAL,
            balance=Decimal("50000.00"),
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

        assert result.current_balance == Decimal("50000.00")

    @pytest.mark.asyncio
    async def test_creates_holdings_for_investment_accounts(self, mock_db, mock_user):
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
            await create_manual_account(
                account_data=account_data,
                current_user=mock_user,
                db=mock_db,
            )

            # Should have called db.add 3 times: 1 account + 2 holdings
            assert mock_db.add.call_count == 3
            # Should have committed twice: once for account, once for holdings
            assert mock_db.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_creates_401k_with_employer_match(self, mock_db, mock_user):
        """Should persist employer match fields when creating a 401k manual account."""
        account_data = ManualAccountCreate(
            name="My 401k",
            account_type=AccountType.RETIREMENT_401K,
            account_source=AccountSource.MANUAL,
            institution="Fidelity",
            account_number_last4="9999",
            balance=Decimal("50000.00"),
            annual_salary=Decimal("100000.00"),
            employer_match_percent=Decimal("50"),
            employer_match_limit_percent=Decimal("6"),
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

        assert result.employer_match_percent == Decimal("50")
        assert result.employer_match_limit_percent == Decimal("6")
        assert result.annual_salary == Decimal("100000.00")


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
    async def test_updates_account_visibility(self, mock_db, mock_user, mock_http_request):
        """Should update is_active for specified accounts."""
        account_ids = [uuid4(), uuid4()]
        request_data = BulkVisibilityUpdate(account_ids=account_ids, is_active=False)

        # Mock check query — selects (Account.id, Account.user_id)
        check_result = Mock()
        check_result.all.return_value = [
            (account_ids[0], mock_user.id),
            (account_ids[1], mock_user.id),
        ]

        # Mock update result
        update_result = Mock()
        update_result.rowcount = 2

        mock_db.execute.side_effect = [check_result, update_result]

        with (
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                return_value=None,
            ),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=account_ids),
            ) as mock_filter,
        ):
            result = await bulk_update_visibility(
                request=request_data,
                http_request=mock_http_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["updated_count"] == 2
            assert mock_db.commit.called
            mock_filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_only_updates_owned_accounts(self, mock_db, mock_user, mock_http_request):
        """Should only update accounts the user owns or has update grant for."""
        account_ids = [uuid4(), uuid4()]
        other_user_id = uuid4()
        request_data = BulkVisibilityUpdate(account_ids=account_ids, is_active=True)

        # Mock check query — accounts exist but owned by someone else
        check_result = Mock()
        check_result.all.return_value = [
            (account_ids[0], other_user_id),
            (account_ids[1], other_user_id),
        ]

        mock_db.execute.return_value = check_result

        with (
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                return_value=None,
            ),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await bulk_update_visibility(
                request=request_data,
                http_request=mock_http_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["updated_count"] == 0

    @pytest.mark.asyncio
    async def test_updates_granted_accounts(self, mock_db, mock_user, mock_http_request):
        """Should update accounts the user has an update grant for (not just owned)."""
        account_ids = [uuid4(), uuid4()]
        other_user_id = uuid4()
        request_data = BulkVisibilityUpdate(account_ids=account_ids, is_active=False)

        # Accounts exist in org but owned by another user
        check_result = Mock()
        check_result.all.return_value = [
            (account_ids[0], other_user_id),
            (account_ids[1], other_user_id),
        ]

        # Update result
        update_result = Mock()
        update_result.rowcount = 2

        mock_db.execute.side_effect = [check_result, update_result]

        with (
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                return_value=None,
            ),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=account_ids),
            ),
        ):
            result = await bulk_update_visibility(
                request=request_data,
                http_request=mock_http_request,
                current_user=mock_user,
                db=mock_db,
            )

            assert result["updated_count"] == 2
            assert mock_db.commit.called


@pytest.mark.unit
class TestUpdateAccount:
    """Test update_account endpoint."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.is_org_admin = False
        return user

    @pytest.fixture
    def mock_account(self, mock_user):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id  # owned by mock_user
        account.name = "Original Name"
        account.is_active = True
        account.current_balance = Decimal("1000.00")
        account.mask = "1234"
        account.exclude_from_cash_flow = False
        account.account_type = AccountType.CHECKING  # non-debt so balance stays positive
        return account

    @pytest.fixture(autouse=True)
    def _allow_permission(self):
        with patch(
            "app.api.v1.accounts.permission_service.require",
            new=AsyncMock(return_value=None),
        ):
            yield

    @pytest.mark.asyncio
    async def test_updates_account_name(self, mock_db, mock_user, mock_account):
        """Should update account name."""
        update_data = AccountUpdate(name="New Name")

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.name == "New Name"
        assert mock_db.commit.called
        assert mock_db.refresh.called

    @pytest.mark.asyncio
    async def test_updates_is_active_flag(self, mock_db, mock_user, mock_account):
        """Should update is_active flag."""
        update_data = AccountUpdate(is_active=False)

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_updates_balance(self, mock_db, mock_user, mock_account):
        """Should update current_balance."""
        update_data = AccountUpdate(current_balance=Decimal("5000.00"))

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.current_balance == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_updates_exclude_from_cash_flow(self, mock_db, mock_user, mock_account):
        """Should update exclude_from_cash_flow flag."""
        update_data = AccountUpdate(exclude_from_cash_flow=True)

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.exclude_from_cash_flow is True

    @pytest.mark.asyncio
    async def test_updates_multiple_fields(self, mock_db, mock_user, mock_account):
        """Should update multiple fields at once."""
        update_data = AccountUpdate(
            name="New Name",
            is_active=False,
            current_balance=Decimal("2000.00"),
            mask="5678",
        )

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.name == "New Name"
        assert result.is_active is False
        assert result.current_balance == Decimal("2000.00")
        assert result.mask == "5678"

    @pytest.mark.asyncio
    async def test_update_negates_positive_balance_for_debt_account(self, mock_db, mock_user):
        """Positive current_balance on update for a debt account must be negated."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.name = "My Mortgage"
        account.account_type = AccountType.MORTGAGE
        account.is_active = True
        account.current_balance = Decimal("-330000.00")
        account.mask = "1234"
        account.exclude_from_cash_flow = True

        update_data = AccountUpdate(current_balance=Decimal("330000.00"))

        result = await update_account(
            account_data=update_data,
            account=account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.current_balance == Decimal("-330000.00")

    @pytest.mark.asyncio
    async def test_update_keeps_negative_balance_for_debt_account(self, mock_db, mock_user):
        """Already-negative current_balance on update for a debt account should be stored as-is."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.name = "My Loan"
        account.account_type = AccountType.LOAN
        account.is_active = True
        account.current_balance = Decimal("-15000.00")
        account.mask = "5678"
        account.exclude_from_cash_flow = True

        update_data = AccountUpdate(current_balance=Decimal("-12000.00"))

        result = await update_account(
            account_data=update_data,
            account=account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.current_balance == Decimal("-12000.00")

    @pytest.mark.asyncio
    async def test_update_keeps_positive_balance_for_asset_account(self, mock_db, mock_user):
        """Positive current_balance on update for a non-debt account must NOT be negated."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.name = "My Checking"
        account.account_type = AccountType.CHECKING
        account.is_active = True
        account.current_balance = Decimal("5000.00")
        account.mask = "1234"
        account.exclude_from_cash_flow = False

        update_data = AccountUpdate(current_balance=Decimal("7500.00"))

        result = await update_account(
            account_data=update_data,
            account=account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.current_balance == Decimal("7500.00")

    @pytest.mark.asyncio
    async def test_update_rejects_without_permission(self, mock_db, mock_account):
        """Should raise 403 when user has no update grant for another user's account."""
        other_user = Mock(spec=User)
        other_user.id = uuid4()
        other_user.organization_id = (
            mock_account.organization_id if hasattr(mock_account, "organization_id") else uuid4()
        )
        other_user.is_org_admin = False

        update_data = AccountUpdate(name="Hacked")

        with patch(
            "app.api.v1.accounts.permission_service.require",
            new=AsyncMock(
                side_effect=HTTPException(status_code=403, detail="Insufficient permissions")
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await update_account(
                    account_data=update_data,
                    account=mock_account,
                    current_user=other_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_updates_employer_match_fields(self, mock_db, mock_user, mock_account):
        """Should update employer match fields on a 401k account."""
        mock_account.account_type = AccountType.RETIREMENT_401K
        mock_account.employer_match_percent = None
        mock_account.employer_match_limit_percent = None
        mock_account.annual_salary = None

        update_data = AccountUpdate(
            employer_match_percent=Decimal("50"),
            employer_match_limit_percent=Decimal("6"),
            annual_salary=Decimal("120000.00"),
        )

        result = await update_account(
            account_data=update_data,
            account=mock_account,
            current_user=mock_user,
            db=mock_db,
        )

        assert result.employer_match_percent == Decimal("50")
        assert result.employer_match_limit_percent == Decimal("6")
        assert result.annual_salary == Decimal("120000.00")
        assert mock_db.commit.called


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
        """Should delete multiple accounts at once (owned accounts)."""
        account_ids = [uuid4(), uuid4(), uuid4()]

        # First execute: fetch (id, user_id) pairs — all owned by current user
        fetch_result = Mock()
        fetch_result.all.return_value = [
            (account_ids[0], mock_user.id),
            (account_ids[1], mock_user.id),
            (account_ids[2], mock_user.id),
        ]

        # Second execute: the DELETE statement
        delete_result = Mock()
        delete_result.rowcount = 3

        mock_db.execute.side_effect = [fetch_result, delete_result]

        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        with (
            patch("app.api.v1.accounts.rate_limit_service.check_rate_limit", return_value=None),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=account_ids),
            ),
        ):
            result = await bulk_delete_accounts(
                account_ids=account_ids,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["deleted_count"] == 3
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_only_deletes_owned_accounts(self, mock_db, mock_user):
        """Should not delete accounts the user neither owns nor has a delete grant for."""
        account_ids = [uuid4(), uuid4()]
        other_user_id = uuid4()

        # Fetch returns accounts owned by someone else, not mock_user
        fetch_result = Mock()
        fetch_result.all.return_value = [
            (account_ids[0], other_user_id),
            (account_ids[1], other_user_id),
        ]
        mock_db.execute.return_value = fetch_result

        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        # No delete grant — filter_allowed_resources returns empty list
        with (
            patch("app.api.v1.accounts.rate_limit_service.check_rate_limit", return_value=None),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await bulk_delete_accounts(
                account_ids=account_ids,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

        # Early return before DELETE execute — nothing deleted
        assert result["deleted_count"] == 0
        assert not mock_db.commit.called

    @pytest.mark.asyncio
    async def test_deletes_granted_accounts(self, mock_db, mock_user):
        """Should delete accounts the user has a delete grant for (not just owned)."""
        account_ids = [uuid4(), uuid4()]
        other_user_id = uuid4()

        # Accounts exist in org but owned by another user
        fetch_result = Mock()
        fetch_result.all.return_value = [
            (account_ids[0], other_user_id),
            (account_ids[1], other_user_id),
        ]

        # DELETE result
        delete_result = Mock()
        delete_result.rowcount = 2

        mock_db.execute.side_effect = [fetch_result, delete_result]

        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {}

        with (
            patch("app.api.v1.accounts.rate_limit_service.check_rate_limit", return_value=None),
            patch(
                "app.api.v1.accounts.permission_service.filter_allowed_resources",
                new=AsyncMock(return_value=account_ids),
            ),
        ):
            result = await bulk_delete_accounts(
                account_ids=account_ids,
                http_request=mock_request,
                current_user=mock_user,
                db=mock_db,
            )

        assert result["deleted_count"] == 2
        assert mock_db.commit.called


@pytest.mark.unit
class TestValuationProviderWhitelist:
    """Test that refresh_account_valuation enforces the provider allowlist."""

    @pytest.fixture(autouse=True)
    def patch_rate_limit(self):
        with patch(
            "app.services.rate_limit_service.rate_limit_service.check_rate_limit",
            new_callable=AsyncMock,
        ):
            yield

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    def test_allowed_providers_constant(self):
        """The allowlist must contain exactly the expected providers."""
        assert _ALLOWED_VALUATION_PROVIDERS == {"rentcast", "attom", "marketcheck"}

    @pytest.mark.asyncio
    async def test_invalid_provider_raises_400(self, mock_db, mock_user):
        """An unlisted provider string must raise HTTP 400."""
        with pytest.raises(HTTPException) as exc_info:
            await refresh_account_valuation(
                account_id=uuid4(),
                http_request=MagicMock(),
                provider="evil_provider",
                current_user=mock_user,
                db=mock_db,
            )
        assert exc_info.value.status_code == 400
        assert "Invalid provider" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_none_provider_passes_whitelist(self, mock_db, mock_user):
        """provider=None (omitted) must not trigger the whitelist check."""
        # After the whitelist check passes, the endpoint queries the DB.
        # We just need the whitelist itself not to raise; the 404 from the
        # missing account is fine.
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await refresh_account_valuation(
                account_id=uuid4(),
                http_request=MagicMock(),
                provider=None,
                current_user=mock_user,
                db=mock_db,
            )
        # Should get 404 (account not found), NOT 400 (bad provider)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_valid_provider_passes_whitelist(self, mock_db, mock_user):
        """Each allowed provider must not trigger the whitelist rejection."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        for provider in ("rentcast", "attom", "marketcheck"):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_account_valuation(
                    account_id=uuid4(),
                    http_request=MagicMock(),
                    provider=provider,
                    current_user=mock_user,
                    db=mock_db,
                )
            # 404 means the whitelist passed; 400 would mean it was rejected
            assert (
                exc_info.value.status_code == 404
            ), f"Provider '{provider}' was incorrectly rejected"


@pytest.mark.unit
class TestAccountNameSanitization:
    """Test that HTML is stripped from account names on create and update."""

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
    async def test_create_strips_html_from_name(self, mock_db, mock_user):
        """HTML tags in account name must be stripped on create."""
        account_data = ManualAccountCreate(
            name="<script>alert(1)</script>My Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.MANUAL,
            balance=Decimal("1000.00"),
        )

        with patch(
            "app.api.v1.accounts.deduplication_service.calculate_manual_account_hash",
            return_value="hash",
        ):
            with patch(
                "app.api.v1.accounts.input_sanitization_service.sanitize_html",
                side_effect=lambda s: s.replace("<script>alert(1)</script>", ""),
            ) as mock_sanitize:
                result = await create_manual_account(
                    account_data=account_data,
                    current_user=mock_user,
                    db=mock_db,
                )

        mock_sanitize.assert_called_once_with("<script>alert(1)</script>My Checking")
        assert "<script>" not in result.name

    @pytest.mark.asyncio
    async def test_update_strips_html_from_name(self, mock_db, mock_user):
        """HTML tags in account name must be stripped on update."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.name = "Original"
        account.is_active = True
        account.current_balance = Decimal("1000.00")
        account.mask = "1234"
        account.exclude_from_cash_flow = False

        update_data = AccountUpdate(name="<b>Bold</b> Name")

        with patch(
            "app.api.v1.accounts.permission_service.require",
            new_callable=AsyncMock,
        ):
            with patch(
                "app.api.v1.accounts.input_sanitization_service.sanitize_html",
                side_effect=lambda s: s.replace("<b>", "").replace("</b>", ""),
            ) as mock_sanitize:
                result = await update_account(
                    account_data=update_data,
                    account=account,
                    current_user=mock_user,
                    db=mock_db,
                )

        mock_sanitize.assert_called_once_with("<b>Bold</b> Name")
        assert "<b>" not in result.name


# ---------------------------------------------------------------------------
# GET /accounts/providers/availability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetProviderAvailability:
    """Test get_provider_availability endpoint."""

    @pytest.mark.asyncio
    async def test_all_providers_disabled(self):
        from app.api.v1.accounts import get_provider_availability

        user = Mock(spec=User)
        user.id = uuid4()

        with patch("app.api.v1.accounts.settings") as mock_settings:
            mock_settings.PLAID_ENABLED = False
            mock_settings.PLAID_CLIENT_ID = ""
            mock_settings.PLAID_SECRET = ""
            mock_settings.TELLER_ENABLED = False
            mock_settings.TELLER_APP_ID = ""
            mock_settings.TELLER_API_KEY = ""

            result = await get_provider_availability(current_user=user)

        assert result.plaid is False
        assert result.teller is False
        assert result.mx is False

    @pytest.mark.asyncio
    async def test_plaid_enabled(self):
        from app.api.v1.accounts import get_provider_availability

        user = Mock(spec=User)
        user.id = uuid4()

        with patch("app.api.v1.accounts.settings") as mock_settings:
            mock_settings.PLAID_ENABLED = True
            mock_settings.PLAID_CLIENT_ID = "client_id"
            mock_settings.PLAID_SECRET = "secret"  # pragma: allowlist secret
            mock_settings.TELLER_ENABLED = False
            mock_settings.TELLER_APP_ID = ""
            mock_settings.TELLER_API_KEY = ""

            result = await get_provider_availability(current_user=user)

        assert result.plaid is True
        assert result.teller is False


# ---------------------------------------------------------------------------
# GET /accounts/export/csv
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExportAccountsCsv:
    """Test export_accounts_csv endpoint."""

    @pytest.mark.asyncio
    async def test_export_csv_success(self):
        from app.api.v1.accounts import export_accounts_csv

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()

        mock_acc = Mock(spec=Account)
        mock_acc.id = uuid4()
        mock_acc.name = "Checking"
        mock_acc.account_type = AccountType.CHECKING
        mock_acc.institution_name = "Test Bank"
        mock_acc.current_balance = Decimal("5000.00")
        mock_acc.available_balance = Decimal("4500.00")
        mock_acc.limit = None
        mock_acc.account_source = AccountSource.PLAID
        mock_acc.tax_treatment = None
        mock_acc.mask = "1234"
        mock_acc.is_active = True

        with (
            patch(
                "app.api.v1.accounts.get_all_household_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ),
            patch(
                "app.api.v1.accounts.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ),
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                new_callable=AsyncMock,
            ),
        ):
            result = await export_accounts_csv(
                request=Mock(), user_id=None, current_user=user, db=db
            )

        assert result.media_type == "text/csv"

    @pytest.mark.asyncio
    async def test_export_csv_empty(self):
        from app.api.v1.accounts import export_accounts_csv

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()

        with (
            patch(
                "app.api.v1.accounts.get_all_household_accounts",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.api.v1.accounts.deduplication_service.deduplicate_accounts",
                return_value=[],
            ),
            patch(
                "app.api.v1.accounts.rate_limit_service.check_rate_limit",
                new_callable=AsyncMock,
            ),
        ):
            result = await export_accounts_csv(
                request=Mock(), user_id=None, current_user=user, db=db
            )

        assert result.media_type == "text/csv"


# ---------------------------------------------------------------------------
# GET /accounts/valuation-providers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetValuationProviders:
    """Test get_valuation_providers endpoint."""

    @pytest.mark.asyncio
    async def test_valuation_providers(self):
        from app.api.v1.accounts import get_valuation_providers

        user = Mock(spec=User)
        user.id = uuid4()

        with patch(
            "app.api.v1.accounts.get_available_property_providers",
            return_value=["rentcast"],
        ):
            with patch(
                "app.api.v1.accounts.get_available_vehicle_providers",
                return_value=["marketcheck"],
            ):
                result = await get_valuation_providers(current_user=user)

        assert result["property"] == ["rentcast"]
        assert result["vehicle"] == ["marketcheck"]

    @pytest.mark.asyncio
    async def test_valuation_providers_empty(self):
        from app.api.v1.accounts import get_valuation_providers

        user = Mock(spec=User)
        user.id = uuid4()

        with patch("app.api.v1.accounts.get_available_property_providers", return_value=[]):
            with patch("app.api.v1.accounts.get_available_vehicle_providers", return_value=[]):
                result = await get_valuation_providers(current_user=user)

        assert result["property"] == []
        assert result["vehicle"] == []


# ---------------------------------------------------------------------------
# POST /accounts/{id}/refresh-valuation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshValuationAdditional:
    """Additional tests for refresh_account_valuation branches."""

    @pytest.fixture(autouse=True)
    def patch_rate_limit(self):
        with patch(
            "app.services.rate_limit_service.rate_limit_service.check_rate_limit",
            new_callable=AsyncMock,
        ):
            yield

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_invalid_provider_raises_400(self, mock_user):
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await refresh_account_valuation(
                account_id=uuid4(),
                http_request=MagicMock(),
                provider="invalid_provider",
                current_user=mock_user,
                db=db,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_account_not_found_raises_404(self, mock_user):
        db = AsyncMock()

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        with pytest.raises(HTTPException) as exc_info:
            await refresh_account_valuation(
                account_id=uuid4(),
                http_request=MagicMock(),
                provider=None,
                current_user=mock_user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_unsupported_account_type_raises_422(self, mock_user):
        db = AsyncMock()

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.account_type = AccountType.CHECKING  # Not property or vehicle
        account.organization_id = mock_user.organization_id

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.api.v1.accounts.permission_service.require",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_account_valuation(
                    account_id=account.id,
                    http_request=MagicMock(),
                    provider=None,
                    current_user=mock_user,
                    db=db,
                )

        assert exc_info.value.status_code == 422
        assert "Auto-valuation is only supported" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_property_missing_address_raises_422(self, mock_user):
        db = AsyncMock()

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.account_type = AccountType.PROPERTY
        account.property_address = None
        account.property_zip = None
        account.organization_id = mock_user.organization_id

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.api.v1.accounts.permission_service.require",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await refresh_account_valuation(
                    account_id=account.id,
                    http_request=MagicMock(),
                    provider=None,
                    current_user=mock_user,
                    db=db,
                )

        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_vehicle_no_vin_raises_422(self, mock_user):
        db = AsyncMock()

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        account.account_type = AccountType.VEHICLE
        account.vehicle_vin = None
        account.organization_id = mock_user.organization_id

        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=result_mock)

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch(
                "app.api.v1.accounts.get_available_vehicle_providers", return_value=["marketcheck"]
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_account_valuation(
                        account_id=account.id,
                        http_request=MagicMock(),
                        provider=None,
                        current_user=mock_user,
                        db=db,
                    )

        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# POST /accounts/{id}/migrate
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMigrateAccount:
    """Test migrate_account endpoint."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_migrate_not_confirmed_raises_400(self, mock_user):
        from app.api.v1.accounts import migrate_account
        from app.schemas.account_migration import MigrateAccountRequest

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        http_request = Mock()
        db = AsyncMock()

        request_body = MigrateAccountRequest(
            target_source="manual",
            confirm=False,
        )

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit", new_callable=AsyncMock
        ):
            with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
                with pytest.raises(HTTPException) as exc_info:
                    await migrate_account(
                        account_id=account.id,
                        request_body=request_body,
                        http_request=http_request,
                        account=account,
                        current_user=mock_user,
                        db=db,
                    )

        assert exc_info.value.status_code == 400
        assert "confirm" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_migrate_migration_error_raises_400(self, mock_user):
        from app.api.v1.accounts import migrate_account
        from app.schemas.account_migration import MigrateAccountRequest
        from app.services.account_migration_service import MigrationError

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = mock_user.id
        http_request = Mock()
        db = AsyncMock()

        request_body = MigrateAccountRequest(
            target_source="manual",
            confirm=True,
        )

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit", new_callable=AsyncMock
        ):
            with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
                with patch(
                    "app.api.v1.accounts.account_migration_service.migrate_account",
                    new_callable=AsyncMock,
                    side_effect=MigrationError("Already manual"),
                ):
                    with pytest.raises(HTTPException) as exc_info:
                        await migrate_account(
                            account_id=account.id,
                            request_body=request_body,
                            http_request=http_request,
                            account=account,
                            current_user=mock_user,
                            db=db,
                        )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# GET /accounts/{id}/migration-history
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMigrationHistory:
    """Test get_migration_history endpoint."""

    @pytest.mark.asyncio
    async def test_get_migration_history_success(self):
        from app.api.v1.accounts import get_migration_history

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        account = Mock(spec=Account)
        account.id = uuid4()
        db = AsyncMock()

        with patch(
            "app.api.v1.accounts.account_migration_service.get_migration_history",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_history:
            result = await get_migration_history(
                account_id=account.id,
                account=account,
                current_user=user,
                db=db,
            )

        assert result == []
        mock_history.assert_awaited_once()


# ---------------------------------------------------------------------------
# GET /accounts/{id}/reconciliation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAccountReconciliation:
    """Test get_account_reconciliation endpoint."""

    @pytest.mark.asyncio
    async def test_reconciliation_success(self):
        from app.api.v1.accounts import get_account_reconciliation

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        account = Mock(spec=Account)
        account.id = uuid4()
        db = AsyncMock()

        mock_result = Mock()
        mock_result.to_dict.return_value = {
            "account_id": str(account.id),
            "bank_balance": 5000.0,
            "computed_balance": 4950.0,
            "discrepancy": 50.0,
        }

        with patch(
            "app.api.v1.accounts.reconciliation_service.reconcile_account",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await get_account_reconciliation(
                account_id=account.id,
                account=account,
                current_user=user,
                db=db,
            )

        assert result["discrepancy"] == 50.0


# ---------------------------------------------------------------------------
# Bulk operations with empty results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBulkOperationsEmpty:
    """Test bulk operations return 0 when no accounts match."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    @pytest.mark.asyncio
    async def test_bulk_visibility_no_matching_accounts(self, mock_user):
        db = AsyncMock()
        http_request = Mock()

        check_result = Mock()
        check_result.all.return_value = []
        db.execute = AsyncMock(return_value=check_result)

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit", new_callable=AsyncMock
        ):
            result = await bulk_update_visibility(
                request=BulkVisibilityUpdate(account_ids=[uuid4()], is_active=False),
                http_request=http_request,
                current_user=mock_user,
                db=db,
            )

        assert result["updated_count"] == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_no_matching_accounts(self, mock_user):
        db = AsyncMock()
        http_request = Mock()

        fetch_result = Mock()
        fetch_result.all.return_value = []
        db.execute = AsyncMock(return_value=fetch_result)

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit", new_callable=AsyncMock
        ):
            result = await bulk_delete_accounts(
                account_ids=[uuid4()],
                http_request=http_request,
                current_user=mock_user,
                db=db,
            )

        assert result["deleted_count"] == 0


# ---------------------------------------------------------------------------
# Coverage: update_account — extended field branches (lines 471-554)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdateAccountExtendedFields:
    """Cover update_account branches for debt, equity, pension, vehicle, etc."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    def _make_account(self, account_type=AccountType.CHECKING):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.account_type = account_type
        return account

    @pytest.mark.asyncio
    async def test_update_debt_loan_fields(self, mock_user):
        """Should update all debt/loan fields when provided."""
        from datetime import date as dt_date

        account = self._make_account(AccountType.LOAN)
        db = AsyncMock()

        account_data = AccountUpdate(
            tax_treatment="pre_tax",
            interest_rate=Decimal("5.5"),
            interest_rate_type="fixed",
            minimum_payment=Decimal("500"),
            payment_due_day=15,
            original_amount=Decimal("200000"),
            origination_date=dt_date(2020, 1, 1),
            maturity_date=dt_date(2050, 1, 1),
            loan_term_months=360,
            compounding_frequency="monthly",
            principal_amount=Decimal("190000"),
        )

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            await update_account(
                account_data=account_data,
                account=account,
                current_user=mock_user,
                db=db,
            )

        assert account.tax_treatment == "pre_tax"
        assert account.interest_rate == Decimal("5.5")
        assert account.interest_rate_type == "fixed"
        assert account.minimum_payment == Decimal("500")
        assert account.payment_due_day == 15
        assert account.original_amount == Decimal("200000")
        assert account.loan_term_months == 360
        assert account.compounding_frequency == "monthly"
        assert account.principal_amount == Decimal("190000")
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_private_equity_fields(self, mock_user):
        """Should update all private equity fields."""
        from datetime import date as dt_date

        account = self._make_account()
        db = AsyncMock()

        # Use a mock for account_data to bypass schema validation for vesting_schedule
        # (AccountUpdate has vesting_schedule as Optional[str] but the code iterates it as list)
        account_data = Mock()
        account_data.name = None
        account_data.is_active = None
        account_data.current_balance = None
        account_data.mask = None
        account_data.exclude_from_cash_flow = None
        account_data.tax_treatment = None
        account_data.interest_rate = None
        account_data.interest_rate_type = None
        account_data.minimum_payment = None
        account_data.payment_due_day = None
        account_data.original_amount = None
        account_data.origination_date = None
        account_data.maturity_date = None
        account_data.loan_term_months = None
        account_data.compounding_frequency = None
        account_data.principal_amount = None
        account_data.monthly_benefit = None
        account_data.benefit_start_date = None
        account_data.credit_limit = None
        account_data.company_valuation = None
        account_data.ownership_percentage = None
        account_data.equity_value = None
        account_data.property_address = None
        account_data.property_zip = None
        account_data.vehicle_vin = None
        account_data.vehicle_mileage = None
        account_data.valuation_adjustment_pct = None
        # Fields we want to test
        import json

        account_data.grant_type = "iso"
        account_data.grant_date = dt_date(2023, 6, 1)
        account_data.quantity = Decimal("1000")
        account_data.strike_price = Decimal("10.50")
        account_data.vesting_schedule = json.dumps([
            {"date": "2024-06-01", "quantity": 250},
            {"date": "2025-06-01", "quantity": 250},
        ])
        account_data.share_price = Decimal("25.00")
        account_data.company_status = "private"
        account_data.valuation_method = "409a"
        account_data.include_in_networth = True

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            await update_account(
                account_data=account_data,
                account=account,
                current_user=mock_user,
                db=db,
            )

        assert account.grant_type == "iso"
        assert account.quantity == Decimal("1000")
        assert account.strike_price == Decimal("10.50")
        assert account.share_price == Decimal("25.00")
        assert account.company_status == "private"
        assert account.valuation_method == "409a"
        assert account.include_in_networth is True
        # vesting_schedule is stored as a raw JSON string (direct assignment)
        parsed = json.loads(account.vesting_schedule)
        assert len(parsed) == 2
        assert parsed[0]["date"] == "2024-06-01"
        assert parsed[1]["quantity"] == 250

    @pytest.mark.asyncio
    async def test_update_pension_and_credit_fields(self, mock_user):
        """Should update pension/annuity and credit card fields."""
        from datetime import date as dt_date

        account = self._make_account()
        db = AsyncMock()

        account_data = AccountUpdate(
            monthly_benefit=Decimal("2500"),
            benefit_start_date=dt_date(2030, 1, 1),
            credit_limit=Decimal("15000"),
        )

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            await update_account(
                account_data=account_data,
                account=account,
                current_user=mock_user,
                db=db,
            )

        assert account.monthly_benefit == Decimal("2500")
        assert account.limit == Decimal("15000")

    @pytest.mark.asyncio
    async def test_update_business_equity_fields(self, mock_user):
        """Should update business equity fields."""
        account = self._make_account()
        db = AsyncMock()

        account_data = AccountUpdate(
            company_valuation=Decimal("5000000"),
            ownership_percentage=Decimal("25.0"),
            equity_value=Decimal("1250000"),
        )

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            await update_account(
                account_data=account_data,
                account=account,
                current_user=mock_user,
                db=db,
            )

        assert account.company_valuation == Decimal("5000000")
        assert account.ownership_percentage == Decimal("25.0")
        assert account.equity_value == Decimal("1250000")

    @pytest.mark.asyncio
    async def test_update_property_and_vehicle_fields(self, mock_user):
        """Should update property address/zip and vehicle vin/mileage fields."""
        account = self._make_account()
        db = AsyncMock()

        account_data = AccountUpdate(
            property_address="123 Main St",
            property_zip="90210",
            vehicle_vin="abc123def456",  # pragma: allowlist secret
            vehicle_mileage=50000,
            valuation_adjustment_pct=Decimal("-5.0"),
        )

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            await update_account(
                account_data=account_data,
                account=account,
                current_user=mock_user,
                db=db,
            )

        assert account.property_address == "123 Main St"
        assert account.property_zip == "90210"
        assert account.vehicle_vin == "ABC123DEF456"  # uppercased  # pragma: allowlist secret
        assert account.vehicle_mileage == 50000
        assert account.valuation_adjustment_pct == Decimal("-5.0")


# ---------------------------------------------------------------------------
# Coverage: refresh_account_valuation — vehicle branch (lines 635-715)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshValuationVehicle:
    """Cover vehicle valuation branch and adjustment logic."""

    @pytest.fixture(autouse=True)
    def patch_rate_limit(self):
        with patch(
            "app.services.rate_limit_service.rate_limit_service.check_rate_limit",
            new_callable=AsyncMock,
        ):
            yield

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        return user

    def _make_vehicle_account(self, vin="1HGBH41JXMN109186", mileage=60000, adj=None):
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.account_type = AccountType.VEHICLE
        account.vehicle_vin = vin
        account.vehicle_mileage = mileage
        account.valuation_adjustment_pct = adj
        return account

    @pytest.mark.asyncio
    async def test_vehicle_no_providers_returns_503(self, mock_user):
        """Should return 503 when no vehicle providers are configured."""
        account = self._make_vehicle_account()
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch(
                "app.api.v1.accounts.decode_vin_nhtsa",
                new_callable=AsyncMock,
                return_value={"make": "Honda"},
            ):
                with patch("app.api.v1.accounts.get_available_vehicle_providers", return_value=[]):
                    with pytest.raises(HTTPException) as exc_info:
                        await refresh_account_valuation(
                            account_id=account.id,
                            http_request=MagicMock(),
                            provider=None,
                            current_user=mock_user,
                            db=db,
                        )
                    assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_vehicle_no_vin_returns_422(self, mock_user):
        """Should return 422 when vehicle has no VIN."""
        account = self._make_vehicle_account(vin=None)
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch(
                "app.api.v1.accounts.get_available_vehicle_providers", return_value=["marketcheck"]
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_account_valuation(
                        account_id=account.id,
                        http_request=MagicMock(),
                        provider=None,
                        current_user=mock_user,
                        db=db,
                    )
                assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_vehicle_valuation_with_adjustment(self, mock_user):
        """Should apply valuation adjustment and return result."""
        account = self._make_vehicle_account(adj=Decimal("-10"))
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=mock_result)

        valuation = Mock()
        valuation.value = Decimal("30000.00")
        valuation.low = Decimal("28000.00")
        valuation.high = Decimal("32000.00")
        valuation.provider = "marketcheck"

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch(
                "app.api.v1.accounts.decode_vin_nhtsa",
                new_callable=AsyncMock,
                return_value={"make": "Honda"},
            ):
                with patch(
                    "app.api.v1.accounts.get_available_vehicle_providers",
                    return_value=["marketcheck"],
                ):
                    with patch(
                        "app.api.v1.accounts.get_vehicle_value",
                        new_callable=AsyncMock,
                        return_value=valuation,
                    ):
                        result = await refresh_account_valuation(
                            account_id=account.id,
                            http_request=MagicMock(),
                            provider=None,
                            current_user=mock_user,
                            db=db,
                        )

        assert result["raw_value"] == 30000.0
        # -10% adjustment: 30000 * 0.90 = 27000.00
        assert result["new_value"] == 27000.0
        assert result["adjustment_pct"] == -10.0
        assert result["vin_info"] == {"make": "Honda"}

    @pytest.mark.asyncio
    async def test_vehicle_valuation_adjustment_with_no_low_high(self, mock_user):
        """Should handle None low/high with adjustment."""
        account = self._make_vehicle_account(adj=Decimal("5"))
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=mock_result)

        valuation = Mock()
        valuation.value = Decimal("20000.00")
        valuation.low = None
        valuation.high = None
        valuation.provider = "marketcheck"

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch(
                "app.api.v1.accounts.decode_vin_nhtsa", new_callable=AsyncMock, return_value=None
            ):
                with patch(
                    "app.api.v1.accounts.get_available_vehicle_providers",
                    return_value=["marketcheck"],
                ):
                    with patch(
                        "app.api.v1.accounts.get_vehicle_value",
                        new_callable=AsyncMock,
                        return_value=valuation,
                    ):
                        result = await refresh_account_valuation(
                            account_id=account.id,
                            http_request=MagicMock(),
                            provider=None,
                            current_user=mock_user,
                            db=db,
                        )

        assert result["low"] is None
        assert result["high"] is None
        assert result["new_value"] == 21000.0  # +5%

    @pytest.mark.asyncio
    async def test_property_no_providers_returns_503(self, mock_user):
        """Should return 503 when no property providers available."""
        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.account_type = AccountType.PROPERTY
        account.property_address = "123 Main St"
        account.property_zip = "90210"
        db = AsyncMock()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = account
        db.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.v1.accounts.permission_service.require", new_callable=AsyncMock):
            with patch("app.api.v1.accounts.get_available_property_providers", return_value=[]):
                with pytest.raises(HTTPException) as exc_info:
                    await refresh_account_valuation(
                        account_id=account.id,
                        http_request=MagicMock(),
                        provider=None,
                        current_user=mock_user,
                        db=db,
                    )
                assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# Coverage: get_migration_history (lines 822-824)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMigrationHistoryAdditional:
    """Cover get_migration_history endpoint."""

    @pytest.mark.asyncio
    async def test_returns_migration_history(self):
        from app.api.v1.accounts import get_migration_history

        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        account = Mock(spec=Account)
        account.id = uuid4()
        db = AsyncMock()

        mock_history = [Mock(), Mock()]
        with patch(
            "app.api.v1.accounts.account_migration_service.get_migration_history",
            new_callable=AsyncMock,
            return_value=mock_history,
        ) as mock_get:
            result = await get_migration_history(
                account_id=account.id,
                account=account,
                current_user=user,
                db=db,
            )

        assert result == mock_history
        mock_get.assert_awaited_once_with(
            db=db,
            account_id=account.id,
            organization_id=user.organization_id,
        )


# ---------------------------------------------------------------------------
# Bulk operation size limits — security: prevent large-payload DoS
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBulkSizeLimits:
    """Bulk endpoints must reject requests with too many IDs."""

    def test_bulk_visibility_rejects_over_limit(self):
        """BulkVisibilityUpdate must reject lists longer than _BULK_VISIBILITY_MAX."""
        from app.api.v1.accounts import _BULK_VISIBILITY_MAX
        from pydantic import ValidationError

        over_limit_ids = [uuid4() for _ in range(_BULK_VISIBILITY_MAX + 1)]
        with pytest.raises(ValidationError):
            BulkVisibilityUpdate(account_ids=over_limit_ids, is_active=True)

    def test_bulk_visibility_accepts_at_limit(self):
        """Exactly _BULK_VISIBILITY_MAX IDs must be accepted."""
        from app.api.v1.accounts import _BULK_VISIBILITY_MAX

        at_limit_ids = [uuid4() for _ in range(_BULK_VISIBILITY_MAX)]
        obj = BulkVisibilityUpdate(account_ids=at_limit_ids, is_active=False)
        assert len(obj.account_ids) == _BULK_VISIBILITY_MAX

    def test_bulk_visibility_accepts_small_list(self):
        ids = [uuid4(), uuid4(), uuid4()]
        obj = BulkVisibilityUpdate(account_ids=ids, is_active=True)
        assert len(obj.account_ids) == 3

    @pytest.mark.asyncio
    async def test_bulk_delete_rejects_over_500(self):
        """Bulk delete endpoint raises 400 when account_ids exceeds _BULK_DELETE_MAX."""
        from app.api.v1.accounts import _BULK_DELETE_MAX, bulk_delete_accounts

        user = Mock()
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()
        over_limit_ids = [uuid4() for _ in range(_BULK_DELETE_MAX + 1)]

        with patch(
            "app.api.v1.accounts.rate_limit_service.check_rate_limit",
            new_callable=AsyncMock,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await bulk_delete_accounts(
                    account_ids=over_limit_ids,
                    http_request=Mock(),
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 400
        assert str(_BULK_DELETE_MAX) in exc_info.value.detail


# ---------------------------------------------------------------------------
# refresh_equity_price — information-disclosure prevention
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRefreshEquityPriceInfoDisclosure:
    """Verify that market-data provider errors do not leak internal details."""

    def _make_equity_account(self, account_type=None, ticker="AAPL"):
        from app.models.account import AccountType, CompanyStatus

        account = Mock(spec=Account)
        account.id = uuid4()
        account.user_id = uuid4()
        account.account_type = account_type or AccountType.STOCK_OPTIONS
        account.institution_name = ticker
        account.name = ticker
        account.company_status = CompanyStatus.PUBLIC
        account.quantity = 10
        return account

    @pytest.mark.asyncio
    async def test_market_data_value_error_returns_generic_message(self):
        """ValueError from market data provider must not leak internal error details."""
        account = self._make_equity_account()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()

        internal_error = "CoinGecko API rate limit exceeded — retry after 60s"

        with patch(
            "app.api.v1.accounts.get_market_data_provider"
        ) as mock_factory:
            mock_provider = Mock()
            mock_provider.get_quote = AsyncMock(side_effect=ValueError(internal_error))
            mock_factory.return_value = mock_provider

            with pytest.raises(HTTPException) as exc_info:
                await refresh_equity_price(
                    account_id=account.id,
                    account=account,
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 422
        # Internal error message must NOT be exposed to the client
        assert internal_error not in exc_info.value.detail
        assert "CoinGecko" not in exc_info.value.detail
        assert "rate limit" not in exc_info.value.detail
        # Should contain the ticker (user's own input) and a safe hint
        assert "AAPL" in exc_info.value.detail
        assert "ticker" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_market_data_value_error_with_connection_details_sanitized(self):
        """Even if the ValueError contains a URL or API key fragment, it must not leak."""
        account = self._make_equity_account(ticker="MSFT")
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        db = AsyncMock()

        internal_error = "Failed to connect to https://api.example.com?key=SECRET123"

        with patch(
            "app.api.v1.accounts.get_market_data_provider"
        ) as mock_factory:
            mock_provider = Mock()
            mock_provider.get_quote = AsyncMock(side_effect=ValueError(internal_error))
            mock_factory.return_value = mock_provider

            with pytest.raises(HTTPException) as exc_info:
                await refresh_equity_price(
                    account_id=account.id,
                    account=account,
                    current_user=user,
                    db=db,
                )

        assert exc_info.value.status_code == 422
        assert "SECRET123" not in exc_info.value.detail
        assert "api.example.com" not in exc_info.value.detail
