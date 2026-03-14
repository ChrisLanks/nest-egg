"""Unit tests for Plaid API endpoints."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.plaid import (
    _handle_auth_webhook,
    _handle_item_webhook,
    _handle_transactions_webhook,
    _map_plaid_account_type,
    create_link_token,
    exchange_public_token,
    handle_plaid_webhook,
    sync_transactions,
)
from app.models.account import Account, AccountType, PlaidItem, TaxTreatment
from app.models.user import User
from app.schemas.plaid import (
    LinkTokenCreateRequest,
    PublicTokenExchangeRequest,
)


@pytest.fixture
def mock_user():
    """Create a mock user without database."""
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "test@example.com"
    user.is_active = True
    return user


@pytest.fixture
def mock_request():
    """Create a mock HTTP request."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


@pytest.mark.unit
class TestMapPlaidAccountType:
    """Test _map_plaid_account_type helper function."""

    def test_maps_checking_account(self):
        """Should map checking account correctly."""
        result = _map_plaid_account_type("depository", "checking")
        assert result == (AccountType.CHECKING, None)

    def test_maps_savings_account(self):
        """Should map savings account correctly."""
        result = _map_plaid_account_type("depository", "savings")
        assert result == (AccountType.SAVINGS, None)

    def test_maps_credit_card(self):
        """Should map credit card correctly."""
        result = _map_plaid_account_type("credit", "credit_card")
        assert result == (AccountType.CREDIT_CARD, None)

    def test_maps_mortgage(self):
        """Should map mortgage correctly."""
        result = _map_plaid_account_type("loan", "mortgage")
        assert result == (AccountType.MORTGAGE, None)

    def test_maps_401k_as_pre_tax(self):
        """Should map traditional 401k with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "401k")
        assert result == (AccountType.RETIREMENT_401K, TaxTreatment.PRE_TAX)

    def test_maps_roth_401k(self):
        """Should map roth_401k to RETIREMENT_401K with ROTH treatment."""
        result = _map_plaid_account_type("investment", "roth_401k")
        assert result == (AccountType.RETIREMENT_401K, TaxTreatment.ROTH)

    def test_maps_roth_403b(self):
        """Should map roth_403b to RETIREMENT_403B with ROTH treatment."""
        result = _map_plaid_account_type("investment", "roth_403b")
        assert result == (AccountType.RETIREMENT_403B, TaxTreatment.ROTH)

    def test_maps_403b_as_pre_tax(self):
        """Should map traditional 403b with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "403b")
        assert result == (AccountType.RETIREMENT_403B, TaxTreatment.PRE_TAX)

    def test_maps_457b_as_pre_tax(self):
        """Should map 457b with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "457b")
        assert result == (AccountType.RETIREMENT_457B, TaxTreatment.PRE_TAX)

    def test_maps_sep_ira(self):
        """Should map SEP IRA with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "sep_ira")
        assert result == (AccountType.RETIREMENT_SEP_IRA, TaxTreatment.PRE_TAX)

    def test_maps_simple_ira(self):
        """Should map SIMPLE IRA with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "simple_ira")
        assert result == (AccountType.RETIREMENT_SIMPLE_IRA, TaxTreatment.PRE_TAX)

    def test_maps_ira_as_pre_tax(self):
        """Should map traditional IRA with PRE_TAX treatment."""
        result = _map_plaid_account_type("investment", "ira")
        assert result == (AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX)

    def test_maps_roth_ira(self):
        """Should map Roth IRA correctly."""
        result = _map_plaid_account_type("investment", "roth")
        assert result == (AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH)

    def test_maps_hsa(self):
        """Should map HSA with TAX_FREE treatment."""
        result = _map_plaid_account_type("investment", "hsa")
        assert result == (AccountType.HSA, TaxTreatment.TAX_FREE)

    def test_maps_brokerage(self):
        """Should map brokerage correctly."""
        result = _map_plaid_account_type("investment", "brokerage")
        assert result == (AccountType.BROKERAGE, TaxTreatment.TAXABLE)

    def test_defaults_unknown_to_other(self):
        """Should default unknown types to OTHER."""
        result = _map_plaid_account_type("unknown", "unknown")
        assert result == (AccountType.OTHER, None)


@pytest.mark.unit
class TestCreateLinkToken:
    """Test create_link_token endpoint."""

    @pytest.mark.asyncio
    async def test_creates_link_token_successfully(self, mock_user, mock_request):
        """Should create link token successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        request_data = LinkTokenCreateRequest(update_mode=False)

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService") as MockPlaidService:
                mock_plaid_service = MockPlaidService.return_value
                mock_plaid_service.create_link_token = AsyncMock(
                    return_value=("link-token-123", "2024-12-31T23:59:59Z")
                )

                result = await create_link_token(
                    request=request_data,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

                assert result.link_token == "link-token-123"
                assert result.expiration == "2024-12-31T23:59:59Z"

    @pytest.mark.asyncio
    async def test_create_link_token_handles_error(self, mock_user, mock_request):
        """Should raise HTTPException when PlaidService fails."""
        mock_db = AsyncMock(spec=AsyncSession)
        request_data = LinkTokenCreateRequest(update_mode=False)

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService") as MockPlaidService:
                mock_plaid_service = MockPlaidService.return_value
                mock_plaid_service.create_link_token = AsyncMock(
                    side_effect=Exception("Plaid API error")
                )

                with pytest.raises(HTTPException) as exc_info:
                    await create_link_token(
                        request=request_data,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 500
                assert "Failed to create link token" in exc_info.value.detail


@pytest.mark.unit
class TestExchangePublicToken:
    """Test exchange_public_token endpoint."""

    @pytest.mark.asyncio
    async def test_exchanges_token_and_creates_accounts(self, mock_user, mock_request):
        """Should exchange token and create accounts successfully."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()

        request_data = PublicTokenExchangeRequest(
            public_token="public-token-123",
            institution_id="ins_1",
            institution_name="Test Bank",
            accounts=[],
        )

        mock_plaid_accounts = [
            {
                "account_id": "acc_123",
                "name": "Checking",
                "type": "depository",
                "subtype": "checking",
                "mask": "1234",
                "current_balance": 1000.0,
                "available_balance": 900.0,
                "limit": None,
            }
        ]

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService") as MockPlaidService:
                with patch("app.api.v1.plaid.encryption_service") as mock_encryption:
                    with patch("app.api.v1.plaid.deduplication_service") as mock_dedup:
                        mock_plaid_service = MockPlaidService.return_value
                        mock_plaid_service.exchange_public_token = AsyncMock(
                            return_value=("access-token-123", mock_plaid_accounts)
                        )
                        mock_encryption.encrypt_token.return_value = "encrypted-token"
                        mock_dedup.calculate_plaid_hash.return_value = "hash-123"

                        result = await exchange_public_token(
                            request=request_data,
                            http_request=mock_request,
                            current_user=mock_user,
                            db=mock_db,
                        )

                        assert result.item_id.startswith("item_")
                        assert len(result.accounts) == 1
                        assert result.accounts[0].name == "Checking"
                        mock_db.add.assert_called()
                        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_token_handles_error(self, mock_user, mock_request):
        """Should rollback and raise HTTPException on error."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_db.rollback = AsyncMock()

        request_data = PublicTokenExchangeRequest(
            public_token="public-token-123",
            institution_id="ins_1",
            institution_name="Test Bank",
            accounts=[],
        )

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService") as MockPlaidService:
                mock_plaid_service = MockPlaidService.return_value
                mock_plaid_service.exchange_public_token = AsyncMock(
                    side_effect=Exception("Exchange failed")
                )

                with pytest.raises(HTTPException) as exc_info:
                    await exchange_public_token(
                        request=request_data,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

                assert exc_info.value.status_code == 500
                assert "Failed to exchange token" in exc_info.value.detail
                mock_db.rollback.assert_called_once()


@pytest.mark.unit
class TestHandlePlaidWebhook:
    """Test handle_plaid_webhook endpoint."""

    @pytest.mark.asyncio
    async def test_handles_item_error_webhook(self, mock_request):
        """Should handle ITEM ERROR webhook."""
        import json as _json

        mock_db = AsyncMock(spec=AsyncSession)

        webhook_data = {
            "webhook_type": "ITEM",
            "webhook_code": "ERROR",
            "item_id": "item_123",
            "error": {
                "error_code": "ITEM_LOGIN_REQUIRED",
                "error_message": "Login required",
            },
        }

        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.institution_name = "Test Bank"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_plaid_item
        mock_db.execute.return_value = mock_result

        # Webhook handler now reads raw body first for signature verification
        mock_request.body = AsyncMock(return_value=_json.dumps(webhook_data).encode())
        mock_request.headers = {"Plaid-Verification": "signature"}

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService.verify_webhook_signature"):
                with patch("app.api.v1.plaid._handle_item_webhook", new=AsyncMock()) as mock_handle:
                    result = await handle_plaid_webhook(
                        request=mock_request,
                        db=mock_db,
                    )

                    assert result["status"] == "acknowledged"
                    mock_handle.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_returns_item_not_found(self, mock_request):
        """Should return item_not_found if PlaidItem doesn't exist."""
        import json as _json

        mock_db = AsyncMock(spec=AsyncSession)

        webhook_data = {
            "webhook_type": "ITEM",
            "webhook_code": "ERROR",
            "item_id": "nonexistent_item",
        }

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Webhook handler now reads raw body first for signature verification
        mock_request.body = AsyncMock(return_value=_json.dumps(webhook_data).encode())
        mock_request.headers = {"Plaid-Verification": "signature"}

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.PlaidService.verify_webhook_signature"):
                result = await handle_plaid_webhook(
                    request=mock_request,
                    db=mock_db,
                )

                assert result["status"] == "item_not_found"


@pytest.mark.unit
class TestSyncTransactions:
    """Test sync_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_syncs_transactions_for_test_user(self, mock_user, mock_request):
        """Should sync mock transactions for test users."""
        mock_db = AsyncMock(spec=AsyncSession)
        plaid_item_id = uuid4()

        # Mock test user
        mock_user.email = "test@test.com"

        # Mock PlaidItem
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = plaid_item_id
        mock_plaid_item.organization_id = mock_user.organization_id

        mock_plaid_result = Mock()
        mock_plaid_result.scalar_one_or_none.return_value = mock_plaid_item

        # Mock accounts
        mock_account = Mock(spec=Account)
        mock_account.external_account_id = "acc_123"

        mock_accounts_result = Mock()
        mock_accounts_scalars = Mock()
        mock_accounts_scalars.all.return_value = [mock_account]
        mock_accounts_result.scalars.return_value = mock_accounts_scalars

        mock_db.execute.side_effect = [mock_plaid_result, mock_accounts_result]

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.MockPlaidTransactionGenerator") as MockGen:
                with patch("app.api.v1.plaid.PlaidTransactionSyncService") as MockSync:
                    MockGen.generate_mock_transactions.return_value = [{"id": "txn_1"}]

                    mock_sync_service = MockSync.return_value
                    mock_sync_service.sync_transactions_for_item = AsyncMock(
                        return_value={"added": 30, "updated": 0}
                    )

                    result = await sync_transactions(
                        plaid_item_id=plaid_item_id,
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )

                    assert result["success"] is True
                    assert result["is_test_mode"] is True
                    assert "stats" in result

    @pytest.mark.asyncio
    async def test_sync_returns_404_for_nonexistent_item(self, mock_user, mock_request):
        """Should return 404 if PlaidItem doesn't exist."""
        mock_db = AsyncMock(spec=AsyncSession)
        plaid_item_id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_transactions(
                    plaid_item_id=plaid_item_id,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_rejects_non_test_users(self, mock_user, mock_request):
        """Should reject non-test users with 501."""
        mock_db = AsyncMock(spec=AsyncSession)
        plaid_item_id = uuid4()

        # Non-test user
        mock_user.email = "real@user.com"

        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = plaid_item_id
        mock_plaid_item.organization_id = mock_user.organization_id

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_plaid_item
        mock_db.execute.return_value = mock_result

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_transactions(
                    plaid_item_id=plaid_item_id,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )

            assert exc_info.value.status_code == 501
            assert "not yet implemented" in exc_info.value.detail


@pytest.mark.unit
class TestWebhookHandlers:
    """Test webhook handler helper functions."""

    @pytest.mark.asyncio
    async def test_handle_item_webhook_error(self):
        """Should create notification on ITEM ERROR."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.institution_name = "Test Bank"

        mock_account = Mock(spec=Account)
        mock_account.id = uuid4()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result

        webhook_data = {
            "error": {
                "error_code": "ITEM_LOGIN_REQUIRED",
                "error_message": "Login required",
            }
        }

        with patch(
            "app.api.v1.plaid.notification_service.create_account_sync_notification",
            new=AsyncMock(),
        ) as mock_notify:
            await _handle_item_webhook(
                db=mock_db,
                plaid_item=mock_plaid_item,
                webhook_code="ERROR",
                webhook_data=webhook_data,
            )

            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_item_webhook_user_permission_revoked(self):
        """Should mark item inactive on USER_PERMISSION_REVOKED."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.institution_name = "Test Bank"
        mock_plaid_item.is_active = True

        with patch("app.api.v1.plaid.notification_service.create_notification", new=AsyncMock()):
            await _handle_item_webhook(
                db=mock_db,
                plaid_item=mock_plaid_item,
                webhook_code="USER_PERMISSION_REVOKED",
                webhook_data={},
            )

            assert mock_plaid_item.is_active is False
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_transactions_webhook_default_update(self):
        """Should handle DEFAULT_UPDATE webhook."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.item_id = "item_123"

        # Mock user query
        mock_user = Mock(spec=User)
        mock_user.email = "test@test.com"

        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock accounts query
        mock_accounts_result = Mock()
        mock_accounts_scalars = Mock()
        mock_accounts_scalars.all.return_value = []
        mock_accounts_result.scalars.return_value = mock_accounts_scalars

        mock_db.execute.side_effect = [mock_user_result, mock_accounts_result]

        with patch("app.api.v1.plaid.PlaidTransactionSyncService") as MockSync:
            with patch("app.api.v1.plaid.MockPlaidTransactionGenerator") as MockGen:
                MockGen.generate_mock_transactions.return_value = []

                mock_sync_service = MockSync.return_value
                mock_sync_service.sync_transactions_for_item = AsyncMock(return_value={"added": 0})

                await _handle_transactions_webhook(
                    db=mock_db,
                    plaid_item=mock_plaid_item,
                    webhook_code="DEFAULT_UPDATE",
                    webhook_data={},
                )

                # Should have attempted to sync
                assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_handle_auth_webhook(self):
        """Should handle AUTH webhooks."""
        mock_db = AsyncMock(spec=AsyncSession)
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.item_id = "item_123"

        # Should not raise errors
        await _handle_auth_webhook(
            db=mock_db,
            plaid_item=mock_plaid_item,
            webhook_code="AUTOMATICALLY_VERIFIED",
            webhook_data={},
        )

        await _handle_auth_webhook(
            db=mock_db,
            plaid_item=mock_plaid_item,
            webhook_code="VERIFICATION_EXPIRED",
            webhook_data={},
        )


# ---------------------------------------------------------------------------
# Coverage: _map_plaid_account_type — missing branches (lines 210,216,221-224,252,257)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMapPlaidAccountTypeExtended:
    """Cover remaining _map_plaid_account_type branches."""

    def test_depository_unknown_subtype_defaults_checking(self):
        """Unknown depository subtype should default to CHECKING."""
        result = _map_plaid_account_type("depository", "money_market")
        assert result == (AccountType.CHECKING, None)

    def test_credit_unknown_subtype_defaults_loan(self):
        """Unknown credit subtype should default to LOAN."""
        result = _map_plaid_account_type("credit", "line_of_credit")
        assert result == (AccountType.LOAN, None)

    def test_loan_student(self):
        """Student loan subtype."""
        result = _map_plaid_account_type("loan", "student")
        assert result == (AccountType.STUDENT_LOAN, None)

    def test_loan_unknown_subtype_defaults_loan(self):
        """Unknown loan subtype should default to LOAN."""
        result = _map_plaid_account_type("loan", "auto")
        assert result == (AccountType.LOAN, None)

    def test_loan_home_equity(self):
        """Home equity should map to MORTGAGE."""
        result = _map_plaid_account_type("loan", "home_equity")
        assert result == (AccountType.MORTGAGE, None)

    def test_investment_traditional_ira(self):
        """traditional_ira subtype."""
        result = _map_plaid_account_type("investment", "traditional_ira")
        assert result == (AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX)

    def test_investment_roth_ira(self):
        """roth_ira subtype."""
        result = _map_plaid_account_type("investment", "roth_ira")
        assert result == (AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH)

    def test_investment_529(self):
        """529 education savings."""
        result = _map_plaid_account_type("investment", "529")
        assert result == (AccountType.RETIREMENT_529, TaxTreatment.TAX_FREE)

    def test_investment_education_savings(self):
        """education_savings subtype."""
        result = _map_plaid_account_type("investment", "education_savings")
        assert result == (AccountType.RETIREMENT_529, TaxTreatment.TAX_FREE)

    def test_investment_unknown_defaults_brokerage(self):
        """Unknown investment subtype defaults to BROKERAGE/TAXABLE."""
        result = _map_plaid_account_type("investment", "trust")
        assert result == (AccountType.BROKERAGE, TaxTreatment.TAXABLE)


# ---------------------------------------------------------------------------
# Coverage: sync_plaid_holdings (lines 278-344)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncPlaidHoldings:
    """Cover sync_plaid_holdings endpoint."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.email = "test@test.com"
        return user

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_sync_holdings_success(self, mock_user, mock_request):
        """Should sync holdings successfully."""
        from app.api.v1.plaid import sync_plaid_holdings

        account_id = uuid4()
        plaid_item_id = uuid4()

        mock_account = Mock(spec=Account)
        mock_account.id = account_id
        mock_account.plaid_item_id = plaid_item_id

        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = plaid_item_id
        mock_plaid_item.access_token = "encrypted_token"

        mock_db = AsyncMock()
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        plaid_item_result = Mock()
        plaid_item_result.scalar_one_or_none.return_value = mock_plaid_item
        mock_db.execute = AsyncMock(side_effect=[account_result, plaid_item_result])

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.encryption_service") as mock_enc:
                mock_enc.decrypt_token.return_value = "access_token_123"
                with patch("app.api.v1.plaid.PlaidService") as MockPS:
                    mock_ps = MockPS.return_value
                    mock_ps.get_investment_holdings = AsyncMock(return_value=([], []))
                    with patch("app.api.v1.plaid.plaid_holdings_sync_service") as mock_sync:
                        mock_sync.sync_holdings = AsyncMock(return_value=5)
                        result = await sync_plaid_holdings(
                            account_id=account_id,
                            http_request=mock_request,
                            current_user=mock_user,
                            db=mock_db,
                        )

        assert result["success"] is True
        assert result["synced"] == 5

    @pytest.mark.asyncio
    async def test_sync_holdings_account_not_found(self, mock_user, mock_request):
        """Should return 404 if account not found."""
        from app.api.v1.plaid import sync_plaid_holdings

        mock_db = AsyncMock()
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=account_result)

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_plaid_holdings(
                    account_id=uuid4(),
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_holdings_not_plaid_account(self, mock_user, mock_request):
        """Should return 400 if account has no plaid_item_id."""
        from app.api.v1.plaid import sync_plaid_holdings

        mock_account = Mock(spec=Account)
        mock_account.plaid_item_id = None

        mock_db = AsyncMock()
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute = AsyncMock(return_value=account_result)

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_plaid_holdings(
                    account_id=uuid4(),
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_holdings_plaid_item_not_found(self, mock_user, mock_request):
        """Should return 404 if PlaidItem not found."""
        from app.api.v1.plaid import sync_plaid_holdings

        mock_account = Mock(spec=Account)
        mock_account.plaid_item_id = uuid4()

        mock_db = AsyncMock()
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        plaid_item_result = Mock()
        plaid_item_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[account_result, plaid_item_result])

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_plaid_holdings(
                    account_id=uuid4(),
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sync_holdings_error_returns_500(self, mock_user, mock_request):
        """Should return 500 on unexpected error."""
        from app.api.v1.plaid import sync_plaid_holdings

        mock_account = Mock(spec=Account)
        mock_account.plaid_item_id = uuid4()
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.access_token = "enc"

        mock_db = AsyncMock()
        account_result = Mock()
        account_result.scalar_one_or_none.return_value = mock_account
        plaid_item_result = Mock()
        plaid_item_result.scalar_one_or_none.return_value = mock_plaid_item
        mock_db.execute = AsyncMock(side_effect=[account_result, plaid_item_result])

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with patch("app.api.v1.plaid.encryption_service") as mock_enc:
                mock_enc.decrypt_token.side_effect = Exception("decrypt fail")
                with pytest.raises(HTTPException) as exc_info:
                    await sync_plaid_holdings(
                        account_id=uuid4(),
                        http_request=mock_request,
                        current_user=mock_user,
                        db=mock_db,
                    )
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Coverage: sync_transactions — no accounts (line 460), error (501-503)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncTransactionsExtended:
    """Cover additional sync_transactions branches."""

    @pytest.fixture
    def mock_user(self):
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()
        user.email = "test@test.com"
        return user

    @pytest.fixture
    def mock_request(self):
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request

    @pytest.mark.asyncio
    async def test_sync_no_accounts_returns_400(self, mock_user, mock_request):
        """Should return 400 when no accounts found for Plaid item."""
        mock_db = AsyncMock()
        plaid_item_id = uuid4()

        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = plaid_item_id

        plaid_result = Mock()
        plaid_result.scalar_one_or_none.return_value = mock_plaid_item

        accounts_scalars = Mock()
        accounts_scalars.all.return_value = []
        accounts_result = Mock()
        accounts_result.scalars.return_value = accounts_scalars

        mock_db.execute = AsyncMock(side_effect=[plaid_result, accounts_result])

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_transactions(
                    plaid_item_id=plaid_item_id,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sync_unexpected_error_returns_500(self, mock_user, mock_request):
        """Should return 500 on unexpected error."""
        mock_db = AsyncMock()
        plaid_item_id = uuid4()

        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = plaid_item_id

        plaid_result = Mock()
        plaid_result.scalar_one_or_none.return_value = mock_plaid_item

        # Second execute raises
        mock_db.execute = AsyncMock(side_effect=[plaid_result, Exception("DB error")])

        with patch("app.api.v1.plaid.rate_limit_service.check_rate_limit", new=AsyncMock()):
            with pytest.raises(HTTPException) as exc_info:
                await sync_transactions(
                    plaid_item_id=plaid_item_id,
                    http_request=mock_request,
                    current_user=mock_user,
                    db=mock_db,
                )
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# Coverage: _handle_item_webhook — PENDING_EXPIRATION (line 541)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleItemWebhookPendingExpiration:
    """Cover PENDING_EXPIRATION branch."""

    @pytest.mark.asyncio
    async def test_pending_expiration(self):
        mock_db = AsyncMock()
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.institution_name = "Test Bank"

        with patch(
            "app.api.v1.plaid.notification_service.create_notification", new=AsyncMock()
        ) as mock_notify:
            await _handle_item_webhook(
                db=mock_db,
                plaid_item=mock_plaid_item,
                webhook_code="PENDING_EXPIRATION",
                webhook_data={},
            )
            mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Coverage: _handle_transactions_webhook — TRANSACTIONS_REMOVED (lines 637-647)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleTransactionsWebhookRemoved:
    """Cover TRANSACTIONS_REMOVED branch."""

    @pytest.mark.asyncio
    async def test_transactions_removed(self):
        mock_db = AsyncMock()
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()

        webhook_data = {
            "removed_transactions": ["txn_1", "txn_2"],
        }

        with patch("app.api.v1.plaid.PlaidTransactionSyncService") as MockSync:
            mock_sync = MockSync.return_value
            mock_sync.remove_transactions = AsyncMock(return_value=2)

            await _handle_transactions_webhook(
                db=mock_db,
                plaid_item=mock_plaid_item,
                webhook_code="TRANSACTIONS_REMOVED",
                webhook_data=webhook_data,
            )

            mock_sync.remove_transactions.assert_called_once()

    @pytest.mark.asyncio
    async def test_transactions_removed_empty_list(self):
        """Empty removed_transactions list should not call remove."""
        mock_db = AsyncMock()
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()

        with patch("app.api.v1.plaid.PlaidTransactionSyncService") as MockSync:
            mock_sync = MockSync.return_value
            mock_sync.remove_transactions = AsyncMock()

            await _handle_transactions_webhook(
                db=mock_db,
                plaid_item=mock_plaid_item,
                webhook_code="TRANSACTIONS_REMOVED",
                webhook_data={"removed_transactions": []},
            )

            mock_sync.remove_transactions.assert_not_called()


# ---------------------------------------------------------------------------
# Coverage: _handle_transactions_webhook — non-test user (line 632)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleTransactionsWebhookRealUser:
    """Cover the real-user (non-test) branch of DEFAULT_UPDATE."""

    @pytest.mark.asyncio
    async def test_real_user_logs_warning(self):
        mock_db = AsyncMock()
        mock_plaid_item = Mock(spec=PlaidItem)
        mock_plaid_item.id = uuid4()
        mock_plaid_item.organization_id = uuid4()
        mock_plaid_item.item_id = "item_abc"

        # User is not test@test.com
        mock_user_obj = Mock(spec=User)
        mock_user_obj.email = "real@user.com"
        user_result = Mock()
        user_result.scalar_one_or_none.return_value = mock_user_obj

        mock_db.execute = AsyncMock(return_value=user_result)

        await _handle_transactions_webhook(
            db=mock_db,
            plaid_item=mock_plaid_item,
            webhook_code="DEFAULT_UPDATE",
            webhook_data={},
        )
        # No error, just logs a warning
