"""Unit tests for bank linking API endpoints."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.bank_linking import (
    ExchangeTokenRequest,
    LinkTokenRequest,
    create_link_token,
    disconnect_account,
    exchange_token,
    list_providers,
    sync_holdings,
    sync_transactions,
)
from app.models.account import AccountSource
from app.models.user import User


@pytest.fixture
def mock_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.fixture
def mock_http_request():
    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    return req


# ---------------------------------------------------------------------------
# POST /link-token
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateLinkToken:
    """Tests for create_link_token endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.PlaidService")
    @patch("app.api.v1.bank_linking.settings")
    async def test_plaid_link_token_success(
        self, mock_settings, mock_plaid_cls, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.PLAID_ENABLED = True
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_plaid = MagicMock()
        mock_plaid.create_link_token = AsyncMock(
            return_value=("link-token-123", "2025-01-01T00:00:00Z")
        )
        mock_plaid_cls.return_value = mock_plaid

        request = LinkTokenRequest(provider="plaid")
        result = await create_link_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "plaid"
        assert result.link_token == "link-token-123"
        assert result.expiration == "2025-01-01T00:00:00Z"

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.settings")
    async def test_plaid_disabled_raises_400(
        self, mock_settings, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.PLAID_ENABLED = False
        mock_rate_limit.check_rate_limit = AsyncMock()

        request = LinkTokenRequest(provider="plaid")
        with pytest.raises(HTTPException) as exc_info:
            await create_link_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400
        assert "not enabled" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_teller_service")
    @patch("app.api.v1.bank_linking.settings")
    async def test_teller_link_token_success(
        self, mock_settings, mock_get_teller, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.TELLER_ENABLED = True
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_teller = MagicMock()
        mock_teller.get_enrollment_url = AsyncMock(return_value="https://teller.io/enroll/123")
        mock_get_teller.return_value = mock_teller

        request = LinkTokenRequest(provider="teller")
        result = await create_link_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "teller"
        assert result.link_token == "https://teller.io/enroll/123"
        assert result.expiration == "7d"

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.settings")
    async def test_teller_disabled_raises_400(
        self, mock_settings, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.TELLER_ENABLED = False
        mock_rate_limit.check_rate_limit = AsyncMock()

        request = LinkTokenRequest(provider="teller")
        with pytest.raises(HTTPException) as exc_info:
            await create_link_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    @patch("app.api.v1.bank_linking.settings")
    async def test_mx_link_token_success(
        self, mock_settings, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.MX_ENABLED = True
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_mx = MagicMock()
        mock_mx.get_or_create_user = AsyncMock(return_value="mx_user_guid_123")
        mock_mx.get_connect_widget_url = AsyncMock(return_value=("https://mx.com/widget", "1h"))
        mock_get_mx.return_value = mock_mx

        request = LinkTokenRequest(provider="mx")
        result = await create_link_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "mx"
        assert result.link_token == "https://mx.com/widget"
        assert result.expiration == "1h"

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.settings")
    async def test_mx_disabled_raises_400(
        self, mock_settings, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.MX_ENABLED = False
        mock_rate_limit.check_rate_limit = AsyncMock()

        request = LinkTokenRequest(provider="mx")
        with pytest.raises(HTTPException) as exc_info:
            await create_link_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.PlaidService")
    @patch("app.api.v1.bank_linking.settings")
    async def test_plaid_service_error_raises_500(
        self, mock_settings, mock_plaid_cls, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_settings.PLAID_ENABLED = True
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_plaid = MagicMock()
        mock_plaid.create_link_token = AsyncMock(side_effect=RuntimeError("Connection error"))
        mock_plaid_cls.return_value = mock_plaid

        request = LinkTokenRequest(provider="plaid")
        with pytest.raises(HTTPException) as exc_info:
            await create_link_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# POST /exchange-token
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExchangeToken:
    """Tests for exchange_token endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.plaid_exchange")
    async def test_plaid_exchange_success(
        self, mock_plaid_exchange, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_id = "acc_1"
        mock_account.name = "Checking"
        mock_account.mask = "1234"
        mock_account.type = "depository"
        mock_account.subtype = "checking"
        mock_account.current_balance = 5000.0

        mock_response = MagicMock()
        mock_response.item_id = "item_abc"
        mock_response.accounts = [mock_account]
        mock_plaid_exchange.return_value = mock_response

        request = ExchangeTokenRequest(
            provider="plaid",
            public_token="public-token-123",
            institution_id="ins_1",
            institution_name="Test Bank",
            accounts=[{"id": "acc_1"}],
        )

        result = await exchange_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "plaid"
        assert result.item_id == "item_abc"
        assert len(result.accounts) == 1

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_teller_service")
    async def test_teller_exchange_success(
        self, mock_get_teller, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_teller = MagicMock()

        mock_enrollment = MagicMock()
        mock_enrollment.enrollment_id = "enroll_123"
        mock_teller.create_enrollment = AsyncMock(return_value=mock_enrollment)

        mock_acc = MagicMock()
        mock_acc.external_account_id = "ext_acc_1"
        mock_acc.name = "Checking"
        mock_acc.mask = "5678"
        mock_acc.account_type = MagicMock(value="depository")
        mock_acc.current_balance = 3000.0
        mock_teller.sync_accounts = AsyncMock(return_value=[mock_acc])
        mock_get_teller.return_value = mock_teller

        request = ExchangeTokenRequest(
            provider="teller",
            public_token="enroll_123",
            access_token="teller_access_token",
            institution_id="ins_2",
            institution_name="Teller Bank",
            accounts=[],
        )

        result = await exchange_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "teller"
        assert result.item_id == "enroll_123"

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    async def test_mx_exchange_success(
        self, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_mx = MagicMock()

        mock_member = MagicMock()
        mock_member.member_guid = "mbr_123"
        mock_mx.create_member_record = AsyncMock(return_value=mock_member)

        mock_acc = MagicMock()
        mock_acc.external_account_id = "mx_acc_1"
        mock_acc.name = "Savings"
        mock_acc.mask = "9012"
        mock_acc.account_type = MagicMock(value="depository")
        mock_acc.current_balance = 10000.0
        mock_mx.sync_accounts = AsyncMock(return_value=[mock_acc])
        mock_get_mx.return_value = mock_mx

        request = ExchangeTokenRequest(
            provider="mx",
            public_token="member_guid_123",
            access_token="mx_user_guid_456",
            institution_id="mx_ins_1",
            institution_name="MX Bank",
            accounts=[],
        )

        result = await exchange_token(request, mock_http_request, mock_user, mock_db)

        assert result.provider == "mx"
        assert result.item_id == "mbr_123"

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    async def test_mx_exchange_missing_guids_raises_400(
        self, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        request = ExchangeTokenRequest(
            provider="mx",
            public_token="member_guid_123",
            access_token=None,  # missing
            institution_id="mx_ins_1",
            institution_name="MX Bank",
            accounts=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await exchange_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.plaid_exchange")
    async def test_exchange_error_rolls_back_and_raises_500(
        self, mock_plaid_exchange, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_plaid_exchange.side_effect = RuntimeError("DB error")

        request = ExchangeTokenRequest(
            provider="plaid",
            public_token="public-token-123",
            institution_id="ins_1",
            institution_name="Test Bank",
            accounts=[],
        )

        with pytest.raises(HTTPException) as exc_info:
            await exchange_token(request, mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 500
        mock_db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# POST /sync-transactions/{account_id}
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncTransactions:
    """Tests for sync_transactions endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_account_not_found_raises_404(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.plaid_sync")
    async def test_plaid_sync_success(
        self, mock_plaid_sync, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_account.plaid_item_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_plaid_sync.return_value = {"success": True}

        result = await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert result == {"success": True}

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_plaid_missing_item_id_raises_400(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_account.plaid_item_id = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_teller_service")
    async def test_teller_sync_success(
        self, mock_get_teller, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.TELLER
        mock_account.teller_enrollment = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_teller = MagicMock()
        mock_teller.sync_transactions = AsyncMock(return_value=[MagicMock(), MagicMock()])
        mock_get_teller.return_value = mock_teller

        result = await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert result["provider"] == "teller"
        assert result["stats"]["added"] == 2

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_teller_missing_enrollment_raises_400(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.TELLER
        mock_account.teller_enrollment = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    async def test_mx_sync_success(
        self, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MX
        mock_account.mx_member = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_mx = MagicMock()
        mock_mx.sync_transactions = AsyncMock(return_value=[MagicMock()])
        mock_get_mx.return_value = mock_mx

        result = await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert result["provider"] == "mx"
        assert result["stats"]["added"] == 1

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    async def test_mx_missing_member_raises_400(
        self, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MX
        mock_account.mx_member = None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_manual_account_raises_400(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MANUAL
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.plaid_sync")
    async def test_sync_error_raises_500(
        self, mock_plaid_sync, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_account.plaid_item_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_plaid_sync.side_effect = RuntimeError("Network error")

        with pytest.raises(HTTPException) as exc_info:
            await sync_transactions(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# POST /sync-holdings/{account_id}
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncHoldings:
    """Tests for sync_holdings endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_account_not_found_raises_404(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_holdings(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.plaid_sync_holdings")
    async def test_plaid_holdings_sync_success(
        self, mock_plaid_sync, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_plaid_sync.return_value = {"holdings": []}

        result = await sync_holdings(uuid4(), mock_http_request, mock_user, mock_db)
        assert result == {"holdings": []}

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_teller_holdings_not_supported(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.TELLER
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_holdings(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 501

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_mx_holdings_not_supported(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MX
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_holdings(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 501

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_manual_holdings_raises_400(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MANUAL
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await sync_holdings(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# POST /disconnect/{account_id}
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDisconnectAccount:
    """Tests for disconnect_account endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_account_not_found_raises_404(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await disconnect_account(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_plaid_disconnect_deactivates_item(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_plaid_item = MagicMock()
        mock_plaid_item.is_active = True

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_account.plaid_item_id = uuid4()
        mock_account.is_active = True
        mock_account.user_id = mock_user.id

        # First call returns the account, second returns the plaid item
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_account
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_plaid_item
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        result = await disconnect_account(uuid4(), mock_http_request, mock_user, mock_db)

        assert result["success"] is True
        assert result["status"] == "disconnected"
        assert mock_plaid_item.is_active is False
        assert mock_account.is_active is False

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_teller_service")
    async def test_teller_disconnect_revokes_enrollment(
        self, mock_get_teller, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_enrollment = MagicMock()
        mock_enrollment.enrollment_id = "enroll_abc"
        mock_enrollment.get_decrypted_access_token.return_value = "decrypted_token"

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.TELLER
        mock_account.teller_enrollment_id = uuid4()
        mock_account.is_active = True
        mock_account.user_id = mock_user.id

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_account
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_enrollment
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        mock_teller = MagicMock()
        mock_teller._make_request = AsyncMock()
        mock_get_teller.return_value = mock_teller

        result = await disconnect_account(uuid4(), mock_http_request, mock_user, mock_db)

        assert result["success"] is True
        assert mock_account.is_active is False

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    @patch("app.api.v1.bank_linking.get_mx_service")
    async def test_mx_disconnect_deletes_member(
        self, mock_get_mx, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_mx_member = MagicMock()
        mock_mx_member.mx_user_guid = "mx_user_guid"
        mock_mx_member.member_guid = "mbr_guid"

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.MX
        mock_account.mx_member_id = uuid4()
        mock_account.is_active = True
        mock_account.user_id = mock_user.id

        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_account
        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_mx_member
        mock_db.execute = AsyncMock(side_effect=[mock_result1, mock_result2])

        mock_mx = MagicMock()
        mock_mx.delete_member = AsyncMock()
        mock_get_mx.return_value = mock_mx

        result = await disconnect_account(uuid4(), mock_http_request, mock_user, mock_db)

        assert result["success"] is True
        mock_mx.delete_member.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.rate_limit_service")
    async def test_disconnect_error_raises_500(
        self, mock_rate_limit, mock_user, mock_db, mock_http_request
    ):
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_account = MagicMock()
        mock_account.account_source = AccountSource.PLAID
        mock_account.plaid_item_id = uuid4()
        mock_account.user_id = mock_user.id
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(side_effect=[mock_result, RuntimeError("DB error")])

        with pytest.raises(HTTPException) as exc_info:
            await disconnect_account(uuid4(), mock_http_request, mock_user, mock_db)
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# GET /providers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListProviders:
    """Tests for list_providers endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.settings")
    async def test_all_providers_enabled(self, mock_settings, mock_user):
        mock_settings.PLAID_ENABLED = True
        mock_settings.TELLER_ENABLED = True
        mock_settings.MX_ENABLED = True

        result = await list_providers(mock_user)
        assert len(result["providers"]) == 3
        ids = [p["id"] for p in result["providers"]]
        assert "plaid" in ids
        assert "teller" in ids
        assert "mx" in ids

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.settings")
    async def test_no_providers_enabled(self, mock_settings, mock_user):
        mock_settings.PLAID_ENABLED = False
        mock_settings.TELLER_ENABLED = False
        mock_settings.MX_ENABLED = False

        result = await list_providers(mock_user)
        assert len(result["providers"]) == 0

    @pytest.mark.asyncio
    @patch("app.api.v1.bank_linking.settings")
    async def test_only_plaid_enabled(self, mock_settings, mock_user):
        mock_settings.PLAID_ENABLED = True
        mock_settings.TELLER_ENABLED = False
        mock_settings.MX_ENABLED = False

        result = await list_providers(mock_user)
        assert len(result["providers"]) == 1
        assert result["providers"][0]["id"] == "plaid"
