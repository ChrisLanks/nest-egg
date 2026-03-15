"""Comprehensive unit tests for TellerService — covers sync_accounts, sync_transactions,
_map_account_type, _generate_dedup_hash, exchange_token, get_enrollment_url, create_enrollment,
and error handling paths."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.account import Account, AccountType, TaxTreatment, TellerEnrollment
from app.services.teller_service import TellerService, get_teller_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_enrollment(org_id=None, user_id=None, enrollment_id="enr_123"):
    """Create a mock TellerEnrollment."""
    enrollment = MagicMock(spec=TellerEnrollment)
    enrollment.id = uuid4()
    enrollment.organization_id = org_id or uuid4()
    enrollment.user_id = user_id or uuid4()
    enrollment.enrollment_id = enrollment_id
    enrollment.get_decrypted_access_token.return_value = "decrypted_token"
    enrollment.last_synced_at = None
    return enrollment


def _make_account(org_id=None, enrollment_id=None, external_id="acc_123"):
    """Create a mock Account."""
    account = MagicMock(spec=Account)
    account.id = uuid4()
    account.organization_id = org_id or uuid4()
    account.teller_enrollment_id = enrollment_id or uuid4()
    account.external_account_id = external_id
    account.current_balance = Decimal("1000.00")
    return account


# ---------------------------------------------------------------------------
# _map_account_type
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMapAccountType:
    """Tests for TellerService._map_account_type."""

    def setup_method(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            self.service = TellerService()

    def test_depository_checking(self):
        result = self.service._map_account_type("depository", "checking")
        assert result == (AccountType.CHECKING, None)

    def test_depository_savings(self):
        result = self.service._map_account_type("depository", "savings")
        assert result == (AccountType.SAVINGS, None)

    def test_depository_money_market(self):
        result = self.service._map_account_type("depository", "money_market")
        assert result == (AccountType.SAVINGS, None)

    def test_depository_cd(self):
        result = self.service._map_account_type("depository", "cd")
        assert result == (AccountType.SAVINGS, None)

    def test_depository_default(self):
        result = self.service._map_account_type("depository", "other")
        assert result == (AccountType.CHECKING, None)

    def test_credit(self):
        result = self.service._map_account_type("credit")
        assert result == (AccountType.CREDIT_CARD, None)

    def test_loan(self):
        result = self.service._map_account_type("loan")
        assert result == (AccountType.LOAN, None)

    def test_investment_brokerage_default(self):
        result = self.service._map_account_type("investment")
        assert result == (AccountType.BROKERAGE, TaxTreatment.TAXABLE)

    def test_investment_ira(self):
        result = self.service._map_account_type("investment", "ira")
        assert result == (AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX)

    def test_investment_traditional_ira(self):
        result = self.service._map_account_type("investment", "traditional_ira")
        assert result == (AccountType.RETIREMENT_IRA, TaxTreatment.PRE_TAX)

    def test_investment_sep_ira(self):
        result = self.service._map_account_type("investment", "sep_ira")
        assert result == (AccountType.RETIREMENT_SEP_IRA, TaxTreatment.PRE_TAX)

    def test_investment_simple_ira(self):
        result = self.service._map_account_type("investment", "simple_ira")
        assert result == (AccountType.RETIREMENT_SIMPLE_IRA, TaxTreatment.PRE_TAX)

    def test_investment_roth(self):
        result = self.service._map_account_type("investment", "roth")
        assert result == (AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH)

    def test_investment_roth_ira(self):
        result = self.service._map_account_type("investment", "roth_ira")
        assert result == (AccountType.RETIREMENT_ROTH, TaxTreatment.ROTH)

    def test_investment_roth_401k(self):
        result = self.service._map_account_type("investment", "roth_401k")
        assert result == (AccountType.RETIREMENT_401K, TaxTreatment.ROTH)

    def test_investment_roth_403b(self):
        result = self.service._map_account_type("investment", "roth_403b")
        assert result == (AccountType.RETIREMENT_403B, TaxTreatment.ROTH)

    def test_investment_401k(self):
        result = self.service._map_account_type("investment", "401k")
        assert result == (AccountType.RETIREMENT_401K, TaxTreatment.PRE_TAX)

    def test_investment_403b(self):
        result = self.service._map_account_type("investment", "403b")
        assert result == (AccountType.RETIREMENT_403B, TaxTreatment.PRE_TAX)

    def test_investment_457b(self):
        result = self.service._map_account_type("investment", "457b")
        assert result == (AccountType.RETIREMENT_457B, TaxTreatment.PRE_TAX)

    def test_investment_hsa(self):
        result = self.service._map_account_type("investment", "hsa")
        assert result == (AccountType.HSA, TaxTreatment.TAX_FREE)

    def test_investment_brokerage_explicit(self):
        result = self.service._map_account_type("investment", "brokerage")
        assert result == (AccountType.BROKERAGE, TaxTreatment.TAXABLE)

    def test_unknown_type(self):
        result = self.service._map_account_type("unknown")
        assert result == (AccountType.OTHER, None)

    def test_none_type(self):
        result = self.service._map_account_type(None)
        assert result == (AccountType.OTHER, None)


# ---------------------------------------------------------------------------
# _generate_dedup_hash
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGenerateDedupHash:
    """Tests for TellerService._generate_dedup_hash."""

    def setup_method(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key_abc"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            self.service = TellerService()

    def test_consistent_hash(self):
        acct_id = uuid4()
        txn = {"date": "2024-01-01", "amount": "50.00", "description": "Coffee"}
        h1 = self.service._generate_dedup_hash(acct_id, txn)
        h2 = self.service._generate_dedup_hash(acct_id, txn)
        assert h1 == h2

    def test_different_amounts_different_hash(self):
        acct_id = uuid4()
        txn1 = {"date": "2024-01-01", "amount": "50.00", "description": "Coffee"}
        txn2 = {"date": "2024-01-01", "amount": "51.00", "description": "Coffee"}
        assert self.service._generate_dedup_hash(
            acct_id, txn1
        ) != self.service._generate_dedup_hash(acct_id, txn2)

    def test_hash_is_sha256(self):
        h = self.service._generate_dedup_hash(
            uuid4(), {"date": "2024-01-01", "amount": "10", "description": "x"}
        )
        assert len(h) == 64

    def test_missing_description_uses_empty(self):
        acct_id = uuid4()
        txn = {"date": "2024-01-01", "amount": "50.00"}
        h = self.service._generate_dedup_hash(acct_id, txn)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# get_enrollment_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetEnrollmentUrl:
    @pytest.mark.asyncio
    async def test_returns_url_with_app_id(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_xyz"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()
            url = await service.get_enrollment_url("user123")
            assert "app_xyz" in url
            assert url == "https://teller.io/connect/app/app_xyz"


# ---------------------------------------------------------------------------
# exchange_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExchangeToken:
    @pytest.mark.asyncio
    async def test_calls_make_request(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()
            service._make_request = AsyncMock(return_value={"id": "enr_1", "access_token": "tok"})

            result = await service.exchange_token("enr_1")
            service._make_request.assert_awaited_once_with("GET", "/enrollments/enr_1")
            assert result["id"] == "enr_1"


# ---------------------------------------------------------------------------
# create_enrollment
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCreateEnrollment:
    @pytest.mark.asyncio
    async def test_creates_enrollment_and_encrypts_token(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            with patch("app.services.teller_service.get_encryption_service") as mock_enc:
                mock_enc.return_value.encrypt_token.return_value = "encrypted_tok"
                service = TellerService()

                db = AsyncMock()
                org_id = uuid4()
                user_id = uuid4()

                await service.create_enrollment(
                    db=db,
                    organization_id=org_id,
                    user_id=user_id,
                    enrollment_id="enr_1",
                    access_token="raw_token",
                    institution_name="Chase",
                )

                db.add.assert_called_once()
                db.commit.assert_awaited_once()
                db.refresh.assert_awaited_once()
                added = db.add.call_args[0][0]
                assert isinstance(added, TellerEnrollment)
                assert added.enrollment_id == "enr_1"
                assert added.access_token == "encrypted_tok"
                assert added.institution_name == "Chase"


# ---------------------------------------------------------------------------
# _make_request / _do_request error handling
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMakeRequestErrors:
    @pytest.mark.asyncio
    async def test_circuit_breaker_open_raises_503(self):
        """CircuitOpenError should result in 503."""
        from app.services.circuit_breaker import CircuitOpenError

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            with patch("app.services.teller_service.get_circuit_breaker") as mock_cb:
                mock_cb.return_value.call = AsyncMock(side_effect=CircuitOpenError("teller"))

                with pytest.raises(HTTPException) as exc_info:
                    await service._make_request("GET", "/accounts")
                assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_http_status_error_raises_502_via_raise_for_status(self):
        """HTTP status errors from Teller should raise 502."""
        import httpx

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=MagicMock(
                    raise_for_status=MagicMock(
                        side_effect=httpx.HTTPStatusError(
                            "error",
                            request=MagicMock(),
                            response=mock_response,
                        )
                    )
                )
            )

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await service._do_request("GET", "/accounts")
                assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_http_error_raises_502(self):
        """Generic HTTP errors should raise 502."""
        import httpx

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(side_effect=httpx.ConnectError("fail"))

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await service._do_request("GET", "/accounts")
                assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_http_status_error_in_do_request(self):
        """HTTPStatusError should raise 502 with status code info."""
        import httpx

        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.text = "Forbidden"

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                return_value=MagicMock(
                    raise_for_status=MagicMock(
                        side_effect=httpx.HTTPStatusError(
                            "error",
                            request=MagicMock(),
                            response=mock_resp,
                        )
                    )
                )
            )

            with patch("app.services.teller_service.httpx.AsyncClient") as mock_cls:
                mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                with pytest.raises(HTTPException) as exc_info:
                    await service._do_request("GET", "/accounts")
                assert exc_info.value.status_code == 502
                assert "403" in exc_info.value.detail


# ---------------------------------------------------------------------------
# sync_accounts
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncAccounts:
    @pytest.mark.asyncio
    async def test_sync_accounts_creates_new_account(self):
        """Should create a new account when one doesn't exist."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()

            teller_accounts = [
                {
                    "id": "acc_teller_1",
                    "name": "My Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "balance": {"ledger": "5000.00", "current": "5000.00"},
                    "last_four": "1234",
                    "institution": {"name": "Chase"},
                }
            ]

            service._make_request = AsyncMock(return_value=teller_accounts)

            # Mock db
            db = AsyncMock()
            # execute returns no existing account
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            db.execute = AsyncMock(return_value=mock_result)

            # Mock begin_nested context manager
            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                result = await service.sync_accounts(db, enrollment)

            assert len(result) == 1
            db.add.assert_called_once()
            added = db.add.call_args[0][0]
            assert isinstance(added, Account)
            assert added.external_account_id == "acc_teller_1"
            assert added.name == "My Checking"
            assert added.account_type == AccountType.CHECKING
            assert added.current_balance == Decimal("5000.00")

    @pytest.mark.asyncio
    async def test_sync_accounts_updates_existing_account(self):
        """Should update balance on existing account."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()

            teller_accounts = [
                {
                    "id": "acc_teller_1",
                    "name": "My Checking",
                    "type": "depository",
                    "subtype": "checking",
                    "balance": {"ledger": "7000.00"},
                    "last_four": "1234",
                    "institution": {"name": "Chase"},
                }
            ]

            service._make_request = AsyncMock(return_value=teller_accounts)

            existing_account = MagicMock(spec=Account)
            existing_account.current_balance = Decimal("5000.00")

            db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = existing_account
            db.execute = AsyncMock(return_value=mock_result)

            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                result = await service.sync_accounts(db, enrollment)

            assert len(result) == 1
            assert existing_account.current_balance == Decimal("7000.00")

    @pytest.mark.asyncio
    async def test_sync_accounts_redis_lock_prevents_concurrent(self):
        """Should return empty list when Redis lock is already held."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()
            db = AsyncMock()

            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=False)  # Lock not acquired

            with patch("app.services.teller_service.redis_client", mock_redis):
                result = await service.sync_accounts(db, enrollment)

            assert result == []

    @pytest.mark.asyncio
    async def test_sync_accounts_redis_failure_proceeds_without_lock(self):
        """Should proceed without lock if Redis fails."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()

            service._make_request = AsyncMock(return_value=[])

            db = AsyncMock()
            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(side_effect=Exception("Redis down"))

            with patch("app.services.teller_service.redis_client", mock_redis):
                result = await service.sync_accounts(db, enrollment)

            assert result == []

    @pytest.mark.asyncio
    async def test_sync_accounts_balance_fallback_chain(self):
        """Should use ledger -> current -> available fallback for balance."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()

            # Only available balance set
            teller_accounts = [
                {
                    "id": "acc_1",
                    "name": "Account",
                    "type": "depository",
                    "balance": {"available": "3000.00"},
                    "institution": {},
                }
            ]

            service._make_request = AsyncMock(return_value=teller_accounts)

            db = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            db.execute = AsyncMock(return_value=mock_result)

            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                await service.sync_accounts(db, enrollment)

            added = db.add.call_args[0][0]
            assert added.current_balance == Decimal("3000.00")


# ---------------------------------------------------------------------------
# sync_transactions
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncTransactions:
    @pytest.mark.asyncio
    async def test_sync_transactions_creates_new(self):
        """Should create new transactions that don't exist."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()
            account = _make_account(
                org_id=enrollment.organization_id,
                enrollment_id=enrollment.id,
            )

            teller_transactions = [
                {
                    "id": "txn_1",
                    "date": "2026-03-10",
                    "amount": "-50.00",
                    "description": "Coffee Shop",
                    "status": "posted",
                    "details": {
                        "category": "Food",
                        "counterparty": {"name": "Starbucks"},
                    },
                }
            ]

            service._make_request = AsyncMock(return_value=teller_transactions)

            db = AsyncMock()

            # First execute: enrollment lookup
            enrollment_result = MagicMock()
            enrollment_result.scalar_one_or_none.return_value = enrollment

            # Second execute: existing external IDs (empty)
            ext_ids_result = MagicMock()
            ext_ids_result.all.return_value = []

            db.execute = AsyncMock(side_effect=[enrollment_result, ext_ids_result])

            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                result = await service.sync_transactions(db, account)

            assert len(result) == 1
            db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_transactions_skips_existing(self):
        """Should skip transactions that already exist."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()
            account = _make_account(
                org_id=enrollment.organization_id,
                enrollment_id=enrollment.id,
            )

            teller_transactions = [
                {
                    "id": "txn_existing",
                    "date": "2026-03-10",
                    "amount": "-50.00",
                    "description": "Coffee",
                    "status": "posted",
                    "details": {},
                }
            ]

            service._make_request = AsyncMock(return_value=teller_transactions)

            db = AsyncMock()

            enrollment_result = MagicMock()
            enrollment_result.scalar_one_or_none.return_value = enrollment

            ext_ids_result = MagicMock()
            ext_ids_result.all.return_value = [("txn_existing",)]

            db.execute = AsyncMock(side_effect=[enrollment_result, ext_ids_result])

            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                result = await service.sync_transactions(db, account)

            assert len(result) == 0
            db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_transactions_no_enrollment_raises(self):
        """Should raise ValueError when enrollment not found."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            account = _make_account()

            db = AsyncMock()
            enrollment_result = MagicMock()
            enrollment_result.scalar_one_or_none.return_value = None
            db.execute = AsyncMock(return_value=enrollment_result)

            with pytest.raises(ValueError, match="does not have Teller enrollment"):
                await service.sync_transactions(db, account)

    @pytest.mark.asyncio
    async def test_sync_transactions_redis_lock_prevents_concurrent(self):
        """Should return empty list when redis lock is already held."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()
            account = _make_account(enrollment_id=enrollment.id)

            db = AsyncMock()
            enrollment_result = MagicMock()
            enrollment_result.scalar_one_or_none.return_value = enrollment
            db.execute = AsyncMock(return_value=enrollment_result)

            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=False)

            with patch("app.services.teller_service.redis_client", mock_redis):
                result = await service.sync_transactions(db, account)

            assert result == []

    @pytest.mark.asyncio
    async def test_sync_transactions_pending_status(self):
        """Should set is_pending=True when transaction status is pending."""
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            service = TellerService()

            enrollment = _make_enrollment()
            account = _make_account(
                org_id=enrollment.organization_id,
                enrollment_id=enrollment.id,
            )

            teller_transactions = [
                {
                    "id": "txn_pending",
                    "date": "2026-03-10",
                    "amount": "-25.00",
                    "description": "Pending Payment",
                    "status": "pending",
                    "details": {},
                }
            ]

            service._make_request = AsyncMock(return_value=teller_transactions)

            db = AsyncMock()
            enrollment_result = MagicMock()
            enrollment_result.scalar_one_or_none.return_value = enrollment
            ext_ids_result = MagicMock()
            ext_ids_result.all.return_value = []
            db.execute = AsyncMock(side_effect=[enrollment_result, ext_ids_result])

            nested_ctx = AsyncMock()
            nested_ctx.__aenter__ = AsyncMock()
            nested_ctx.__aexit__ = AsyncMock(return_value=False)
            db.begin_nested = MagicMock(return_value=nested_ctx)

            with patch("app.services.teller_service.redis_client", None):
                await service.sync_transactions(db, account)

            added = db.add.call_args[0][0]
            assert added.is_pending is True


# ---------------------------------------------------------------------------
# get_teller_service
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetTellerService:
    def test_returns_teller_service_instance(self):
        with patch("app.services.teller_service.settings") as mock_settings:
            mock_settings.TELLER_APP_ID = "app_123"
            mock_settings.TELLER_API_KEY = "key"  # pragma: allowlist secret
            mock_settings.TELLER_CERT_PATH = ""
            result = get_teller_service()
            assert isinstance(result, TellerService)
