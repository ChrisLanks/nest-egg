"""Unit tests for Teller API webhook endpoints."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.teller import (
    _handle_enrollment_connected,
    _handle_transaction_posted,
    handle_teller_webhook,
    verify_teller_webhook_signature,
)
from app.models.account import Account, TellerEnrollment


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def mock_enrollment():
    enrollment = Mock(spec=TellerEnrollment)
    enrollment.id = uuid4()
    enrollment.enrollment_id = "test_enrollment_123"
    enrollment.organization_id = uuid4()
    enrollment.user_id = uuid4()
    enrollment.institution_name = "Chase"
    enrollment.is_active = True
    enrollment.last_error_code = None
    enrollment.last_error_message = None
    return enrollment


def _make_signed_body(payload: dict, secret: str) -> tuple[bytes, str]:
    """Create a webhook body and its HMAC-SHA256 signature."""
    raw = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    return raw, sig


@pytest.mark.unit
class TestVerifyTellerWebhookSignature:
    """Tests for webhook signature verification."""

    def test_valid_signature_passes(self):
        """Should return True for a correctly signed payload."""
        secret = "webhook_secret_123"  # pragma: allowlist secret
        body = b'{"event":"enrollment.connected"}'
        expected_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        result = verify_teller_webhook_signature(expected_sig, body, secret)
        assert result is True

    def test_invalid_signature_raises_401(self):
        """Should raise 401 for an invalid signature."""
        secret = "webhook_secret_123"  # pragma: allowlist secret
        body = b'{"event":"enrollment.connected"}'

        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature("bad_signature", body, secret)

        assert exc_info.value.status_code == 401
        assert "Invalid webhook signature" in exc_info.value.detail

    def test_missing_signature_raises_401(self):
        """Should raise 401 when signature header is empty."""
        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature("", b"body", "secret")

        assert exc_info.value.status_code == 401
        assert "Missing Teller-Signature" in exc_info.value.detail

    def test_missing_secret_raises_500(self):
        """Should raise 500 when webhook secret is not configured."""
        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature("some_sig", b"body", "")

        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail

    def test_none_signature_raises_401(self):
        """Should raise 401 when signature header is None."""
        with pytest.raises(HTTPException) as exc_info:
            verify_teller_webhook_signature(None, b"body", "secret")

        assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestHandleEnrollmentConnected:
    """Tests for _handle_enrollment_connected handler."""

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.notification_service")
    async def test_creates_notification(self, mock_notif, mock_db, mock_enrollment):
        """Should create a notification for enrollment connection."""
        mock_notif.create_notification = AsyncMock()
        await _handle_enrollment_connected(mock_db, mock_enrollment, {})

        mock_notif.create_notification.assert_awaited_once()
        call_kwargs = mock_notif.create_notification.call_args.kwargs
        assert call_kwargs["organization_id"] == mock_enrollment.organization_id
        assert call_kwargs["user_id"] == mock_enrollment.user_id
        assert "Chase" in call_kwargs["title"]
        mock_db.commit.assert_awaited_once()


@pytest.mark.unit
class TestHandleTransactionPosted:
    """Tests for _handle_transaction_posted handler."""

    @pytest.mark.asyncio
    async def test_returns_early_without_account_id(self, mock_db, mock_enrollment):
        """Should return early when payload has no account_id."""
        await _handle_transaction_posted(mock_db, mock_enrollment, {})

        # No db query should happen
        mock_db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.get_teller_service")
    async def test_syncs_transactions_when_account_found(
        self, mock_get_service, mock_db, mock_enrollment
    ):
        """Should trigger transaction sync when account is found."""
        mock_account = Mock(spec=Account)
        mock_account.name = "Chase Checking"

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_account
        mock_db.execute.return_value = mock_result

        mock_service = AsyncMock()
        mock_get_service.return_value = mock_service

        await _handle_transaction_posted(mock_db, mock_enrollment, {"account_id": "acc_123"})

        mock_service.sync_transactions.assert_awaited_once_with(mock_db, mock_account, days_back=7)

    @pytest.mark.asyncio
    async def test_no_sync_when_account_not_found(self, mock_db, mock_enrollment):
        """Should skip sync when account is not found in DB."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Should not raise
        await _handle_transaction_posted(mock_db, mock_enrollment, {"account_id": "acc_unknown"})


@pytest.mark.unit
class TestHandleTellerWebhook:
    """Tests for the main webhook dispatcher endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_rejects_missing_signature(self, mock_settings, mock_rate_limit, mock_db):
        """Should raise 401 when Teller-Signature header is absent."""
        mock_settings.TELLER_WEBHOOK_SECRET = "secret123"  # pragma: allowlist secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_request = AsyncMock()
        mock_request.body.return_value = b'{"event":"test"}'
        mock_request.headers = {}  # No Teller-Signature

        with pytest.raises(HTTPException) as exc_info:
            await handle_teller_webhook(request=mock_request, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_rejects_invalid_signature(self, mock_settings, mock_rate_limit, mock_db):
        """Should raise 401 when signature does not match."""
        mock_settings.TELLER_WEBHOOK_SECRET = "secret123"  # pragma: allowlist secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        mock_request = AsyncMock()
        mock_request.body.return_value = b'{"event":"test"}'
        mock_request.headers = {"Teller-Signature": "invalid_hex_signature"}

        with pytest.raises(HTTPException) as exc_info:
            await handle_teller_webhook(request=mock_request, db=mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.api.v1.teller._handle_enrollment_connected", new_callable=AsyncMock)
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_dispatches_enrollment_connected(
        self, mock_settings, mock_rate_limit, mock_handle, mock_db
    ):
        """Should dispatch to _handle_enrollment_connected for correct event type."""
        secret = "secret123"  # pragma: allowlist secret
        mock_settings.TELLER_WEBHOOK_SECRET = secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        enrollment_id = "enr_abc"
        payload = {
            "event": "enrollment.connected",
            "payload": {"enrollment_id": enrollment_id},
        }
        raw_body, signature = _make_signed_body(payload, secret)

        mock_request = AsyncMock()
        mock_request.body.return_value = raw_body
        mock_request.headers = {"Teller-Signature": signature}

        # Mock enrollment lookup
        mock_enrollment = Mock(spec=TellerEnrollment)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_enrollment
        mock_db.execute.return_value = mock_result

        result = await handle_teller_webhook(request=mock_request, db=mock_db)

        assert result == {"status": "acknowledged"}
        mock_handle.assert_awaited_once_with(mock_db, mock_enrollment, payload["payload"])

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_acknowledges_missing_enrollment_id(
        self, mock_settings, mock_rate_limit, mock_db
    ):
        """Should return acknowledged when enrollment_id is missing from payload."""
        secret = "secret123"  # pragma: allowlist secret
        mock_settings.TELLER_WEBHOOK_SECRET = secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        payload = {"event": "enrollment.connected", "payload": {}}
        raw_body, signature = _make_signed_body(payload, secret)

        mock_request = AsyncMock()
        mock_request.body.return_value = raw_body
        mock_request.headers = {"Teller-Signature": signature}

        result = await handle_teller_webhook(request=mock_request, db=mock_db)

        assert result == {"status": "acknowledged"}

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_returns_enrollment_not_found(self, mock_settings, mock_rate_limit, mock_db):
        """Should return enrollment_not_found when enrollment doesn't exist."""
        secret = "secret123"  # pragma: allowlist secret
        mock_settings.TELLER_WEBHOOK_SECRET = secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        payload = {
            "event": "enrollment.connected",
            "payload": {"enrollment_id": "enr_nonexistent"},
        }
        raw_body, signature = _make_signed_body(payload, secret)

        mock_request = AsyncMock()
        mock_request.body.return_value = raw_body
        mock_request.headers = {"Teller-Signature": signature}

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await handle_teller_webhook(request=mock_request, db=mock_db)

        assert result == {"status": "enrollment_not_found"}

    @pytest.mark.asyncio
    @patch("app.api.v1.teller.rate_limit_service")
    @patch("app.api.v1.teller.settings")
    async def test_rejects_malformed_json(self, mock_settings, mock_rate_limit, mock_db):
        """Should raise 400 for malformed JSON body."""
        secret = "secret123"  # pragma: allowlist secret
        mock_settings.TELLER_WEBHOOK_SECRET = secret
        mock_rate_limit.check_rate_limit = AsyncMock()

        raw_body = b"not valid json"
        signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        mock_request = AsyncMock()
        mock_request.body.return_value = raw_body
        mock_request.headers = {"Teller-Signature": signature}

        with pytest.raises(HTTPException) as exc_info:
            await handle_teller_webhook(request=mock_request, db=mock_db)

        assert exc_info.value.status_code == 400
        assert "Invalid JSON" in exc_info.value.detail
