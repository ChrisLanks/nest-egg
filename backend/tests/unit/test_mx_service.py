"""Tests for MX Platform API service."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.account import Account, AccountSource, AccountType, MxMember, TaxTreatment


class TestMxServiceInit:
    """Test MX service initialization."""

    def test_init_requires_credentials(self, monkeypatch):
        """Should raise ValueError if MX credentials not configured."""
        monkeypatch.setattr("app.config.settings.MX_CLIENT_ID", "")
        monkeypatch.setattr("app.config.settings.MX_API_KEY", "")
        from app.services.mx_service import MxService

        with pytest.raises(ValueError, match="MX_CLIENT_ID"):
            MxService()

    def test_init_sandbox_url(self, monkeypatch):
        """Should use sandbox base URL by default."""
        monkeypatch.setattr("app.config.settings.MX_CLIENT_ID", "test-client")
        monkeypatch.setattr("app.config.settings.MX_API_KEY", "test-key")
        monkeypatch.setattr("app.config.settings.MX_ENV", "sandbox")
        from app.services.mx_service import MxService

        service = MxService()
        assert service.base_url == "https://int-api.mx.com"

    def test_init_production_url(self, monkeypatch):
        """Should use production base URL when configured."""
        monkeypatch.setattr("app.config.settings.MX_CLIENT_ID", "test-client")
        monkeypatch.setattr("app.config.settings.MX_API_KEY", "test-key")
        monkeypatch.setattr("app.config.settings.MX_ENV", "production")
        from app.services.mx_service import MxService

        service = MxService()
        assert service.base_url == "https://api.mx.com"


@pytest.fixture
def mx_service(monkeypatch):
    """Create an MxService with test credentials."""
    monkeypatch.setattr("app.config.settings.MX_CLIENT_ID", "test-client")
    monkeypatch.setattr("app.config.settings.MX_API_KEY", "test-key")
    monkeypatch.setattr("app.config.settings.MX_ENV", "sandbox")
    from app.services.mx_service import MxService

    return MxService()


class TestMxServiceCreateUser:
    """Test MX user creation."""

    @pytest.mark.asyncio
    async def test_create_user(self, mx_service):
        """Should create an MX user and return the GUID."""
        user_id = uuid4()
        mx_service._make_request = AsyncMock(
            return_value={"user": {"guid": "USR-abc123"}}
        )

        result = await mx_service.create_user(user_id)

        assert result == "USR-abc123"
        mx_service._make_request.assert_called_once_with(
            "POST",
            "/users",
            json={"user": {"metadata": str(user_id)}},
        )


class TestMxServiceConnectWidget:
    """Test MX Connect Widget URL generation."""

    @pytest.mark.asyncio
    async def test_get_connect_widget_url(self, mx_service):
        """Should return widget URL and expiration."""
        mx_service._make_request = AsyncMock(
            return_value={
                "user": {
                    "connect_widget_url": {
                        "url": "https://int-widgets.mx.com/connect/abc123",
                        "expiration": "10m",
                    }
                }
            }
        )

        url, expiration = await mx_service.get_connect_widget_url("USR-abc123")

        assert url == "https://int-widgets.mx.com/connect/abc123"
        assert expiration == "10m"


class TestMxServiceMemberManagement:
    """Test MX member operations."""

    @pytest.mark.asyncio
    async def test_create_member_record(self, mx_service, db_session):
        """Should persist an MxMember record."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        member = await mx_service.create_member_record(
            db=db_session,
            organization_id=org.id,
            user_id=user.id,
            mx_user_guid="USR-abc123",
            member_guid="MBR-xyz789",
            institution_code="chase",
            institution_name="Chase",
        )

        assert member.mx_user_guid == "USR-abc123"
        assert member.member_guid == "MBR-xyz789"
        assert member.institution_name == "Chase"
        assert member.connection_status == "CONNECTED"
        assert member.is_active is True

    @pytest.mark.asyncio
    async def test_get_member_status(self, mx_service):
        """Should return member connection status."""
        mx_service._make_request = AsyncMock(
            return_value={
                "member": {
                    "connection_status": "CONNECTED",
                    "is_being_aggregated": False,
                    "successfully_aggregated_at": "2024-01-01T00:00:00Z",
                }
            }
        )

        status = await mx_service.get_member_status("USR-abc123", "MBR-xyz789")

        assert status["connection_status"] == "CONNECTED"

    @pytest.mark.asyncio
    async def test_delete_member(self, mx_service):
        """Should call MX API to delete the member."""
        mx_service._make_request = AsyncMock(return_value={})

        await mx_service.delete_member("USR-abc123", "MBR-xyz789")

        mx_service._make_request.assert_called_once_with(
            "DELETE",
            "/users/USR-abc123/members/MBR-xyz789",
        )


class TestMxServiceAccountSync:
    """Test MX account synchronization."""

    @pytest.mark.asyncio
    async def test_sync_accounts_creates_new(self, mx_service, db_session):
        """Should create new Account records from MX data."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        member = MxMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_user_guid="USR-abc123",
            member_guid="MBR-xyz789",
            institution_name="Chase",
        )
        db_session.add(member)
        await db_session.flush()

        mx_service._make_request = AsyncMock(
            return_value={
                "accounts": [
                    {
                        "guid": "ACT-001",
                        "name": "Chase Checking",
                        "type": "CHECKING",
                        "balance": 1500.50,
                        "available_balance": 1400.00,
                        "account_number": "****1234",
                    },
                    {
                        "guid": "ACT-002",
                        "name": "Chase Savings",
                        "type": "SAVINGS",
                        "balance": 10000.00,
                        "available_balance": 10000.00,
                    },
                ]
            }
        )

        accounts = await mx_service.sync_accounts(db_session, member)

        assert len(accounts) == 2
        assert accounts[0].name == "Chase Checking"
        assert accounts[0].account_type == AccountType.CHECKING
        assert accounts[0].account_source == AccountSource.MX
        assert accounts[0].current_balance == Decimal("1500.50")
        assert accounts[0].mask == "1234"
        assert accounts[1].name == "Chase Savings"
        assert accounts[1].account_type == AccountType.SAVINGS

    @pytest.mark.asyncio
    async def test_sync_accounts_updates_existing(self, mx_service, db_session):
        """Should update balance on existing accounts."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        member = MxMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_user_guid="USR-abc123",
            member_guid="MBR-xyz789",
        )
        db_session.add(member)
        await db_session.flush()

        # Pre-create account
        existing = Account(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_member_id=member.id,
            external_account_id="ACT-001",
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.MX,
            current_balance=Decimal("1000.00"),
        )
        db_session.add(existing)
        await db_session.flush()

        mx_service._make_request = AsyncMock(
            return_value={
                "accounts": [
                    {
                        "guid": "ACT-001",
                        "name": "Chase Checking",
                        "type": "CHECKING",
                        "balance": 2000.00,
                        "available_balance": 1900.00,
                    }
                ]
            }
        )

        accounts = await mx_service.sync_accounts(db_session, member)

        assert len(accounts) == 1
        assert accounts[0].current_balance == Decimal("2000.0")


class TestMxServiceTransactionSync:
    """Test MX transaction synchronization."""

    @pytest.mark.asyncio
    async def test_sync_transactions(self, mx_service, db_session):
        """Should create Transaction records from MX data."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        member = MxMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_user_guid="USR-abc123",
            member_guid="MBR-xyz789",
        )
        db_session.add(member)
        await db_session.flush()

        account = Account(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_member_id=member.id,
            external_account_id="ACT-001",
            name="Chase Checking",
            account_type=AccountType.CHECKING,
            account_source=AccountSource.MX,
        )
        db_session.add(account)
        await db_session.flush()

        mx_service._make_request = AsyncMock(
            return_value={
                "transactions": [
                    {
                        "guid": "TRN-001",
                        "date": "2024-01-15",
                        "amount": -42.50,
                        "description": "STARBUCKS #1234",
                        "original_description": "STARBUCKS STORE #1234",
                        "top_level_category": "Food & Dining",
                        "category": "Coffee Shops",
                        "status": "POSTED",
                    },
                    {
                        "guid": "TRN-002",
                        "transacted_at": "2024-01-16T10:30:00Z",
                        "amount": -15.00,
                        "description": "Uber",
                        "top_level_category": "Auto & Transport",
                        "category": "Ride Share",
                        "status": "PENDING",
                    },
                ]
            }
        )

        transactions = await mx_service.sync_transactions(db_session, account)

        assert len(transactions) == 2
        assert transactions[0].external_transaction_id == "TRN-001"
        assert transactions[0].amount == Decimal("-42.50")
        assert transactions[0].category_primary == "Food & Dining"
        assert transactions[0].category_detailed == "Coffee Shops"
        assert transactions[0].is_pending is False
        assert transactions[1].is_pending is True

    @pytest.mark.asyncio
    async def test_sync_transactions_no_member_raises(self, mx_service, db_session):
        """Should raise ValueError if account has no MX member."""
        account = MagicMock()
        account.mx_member = None

        with pytest.raises(ValueError, match="does not have MX member"):
            await mx_service.sync_transactions(db_session, account)


class TestMxServiceAccountTypeMapping:
    """Test MX account type mapping."""

    def test_checking_type(self, mx_service):
        assert mx_service._map_account_type("CHECKING") == (AccountType.CHECKING, None)

    def test_savings_type(self, mx_service):
        assert mx_service._map_account_type("SAVINGS") == (AccountType.SAVINGS, None)

    def test_credit_card_type(self, mx_service):
        assert mx_service._map_account_type("CREDIT_CARD") == (AccountType.CREDIT_CARD, None)

    def test_mortgage_type(self, mx_service):
        assert mx_service._map_account_type("MORTGAGE") == (AccountType.MORTGAGE, None)

    def test_loan_type(self, mx_service):
        assert mx_service._map_account_type("LOAN") == (AccountType.LOAN, None)

    def test_student_loan_type(self, mx_service):
        assert mx_service._map_account_type("STUDENT_LOAN") == (AccountType.STUDENT_LOAN, None)

    def test_investment_type(self, mx_service):
        assert mx_service._map_account_type("INVESTMENT") == (AccountType.BROKERAGE, TaxTreatment.TAXABLE)

    def test_retirement_defaults_to_pre_tax(self, mx_service):
        """MX returns generic RETIREMENT — we default to PRE_TAX (traditional)."""
        assert mx_service._map_account_type("RETIREMENT") == (AccountType.RETIREMENT_401K, TaxTreatment.PRE_TAX)

    def test_property_type(self, mx_service):
        assert mx_service._map_account_type("PROPERTY") == (AccountType.PROPERTY, None)

    def test_unknown_type_defaults_to_other(self, mx_service):
        assert mx_service._map_account_type("UNKNOWN_TYPE") == (AccountType.OTHER, None)

    def test_none_type_defaults_to_other(self, mx_service):
        assert mx_service._map_account_type(None) == (AccountType.OTHER, None)

    def test_case_insensitive(self, mx_service):
        assert mx_service._map_account_type("checking") == (AccountType.CHECKING, None)


class TestMxServiceMakeRequest:
    """Test the HTTP request layer."""

    @pytest.mark.asyncio
    async def test_make_request_uses_basic_auth(self, mx_service):
        """Should send Basic Auth with client_id:api_key."""
        with patch("app.services.mx_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"user": {"guid": "USR-123"}}
            mock_response.content = b'{"user": {"guid": "USR-123"}}'
            mock_response.raise_for_status = MagicMock()
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await mx_service._make_request("GET", "/users")

            call_kwargs = mock_client.request.call_args
            assert call_kwargs.kwargs["auth"] == ("test-client", "test-key")
            assert "application/vnd.mx.api.v1+json" in call_kwargs.kwargs["headers"]["Accept"]

    @pytest.mark.asyncio
    async def test_make_request_raises_on_http_error(self, mx_service):
        """Should propagate HTTP errors."""
        with patch("app.services.mx_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(Exception, match="401"):
                await mx_service._make_request("GET", "/users")


class TestMxServiceGetOrCreateUser:
    """Test get_or_create_user logic."""

    @pytest.mark.asyncio
    async def test_reuses_existing_mx_user_guid(self, mx_service, db_session):
        """Should reuse mx_user_guid from an existing MxMember."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="test@test.com",
            password_hash="hash",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        # Pre-create a member for this user
        member = MxMember(
            id=uuid4(),
            organization_id=org.id,
            user_id=user.id,
            mx_user_guid="USR-existing",
            member_guid="MBR-existing",
        )
        db_session.add(member)
        await db_session.flush()

        mx_service._make_request = AsyncMock()  # Should NOT be called

        result = await mx_service.get_or_create_user(db_session, user.id)

        assert result == "USR-existing"
        mx_service._make_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_mx_user_when_none_exists(self, mx_service, db_session):
        """Should create a new MX user if none exists."""
        from app.models.user import Organization, User

        org = Organization(id=uuid4(), name="Test Org")
        db_session.add(org)
        await db_session.flush()

        user = User(
            id=uuid4(),
            organization_id=org.id,
            email="new@test.com",
            password_hash="hash",
            first_name="New",
            last_name="User",
        )
        db_session.add(user)
        await db_session.flush()

        mx_service._make_request = AsyncMock(
            return_value={"user": {"guid": "USR-new123"}}
        )

        result = await mx_service.get_or_create_user(db_session, user.id)

        assert result == "USR-new123"
        mx_service._make_request.assert_called_once()
