"""Tests for the email service (SMTP sending and token helpers)."""

import hashlib
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.email_service import (
    EmailService,
    create_password_reset_token,
    create_verification_token,
    hash_token,
)
from app.utils.datetime_utils import utc_now

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(smtp_host=None, **kwargs):
    defaults = dict(
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        from_email="noreply@test.com",
        from_name="Test App",
        use_tls=True,
        app_base_url="http://localhost:5173",
    )
    defaults.update(kwargs)
    return EmailService(smtp_host=smtp_host, **defaults)


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsConfigured:
    def test_false_when_no_smtp_host(self):
        svc = _make_service(smtp_host=None)
        assert svc.is_configured is False

    def test_false_when_empty_string(self):
        svc = _make_service(smtp_host="")
        assert svc.is_configured is False

    def test_true_when_smtp_host_set(self):
        svc = _make_service(smtp_host="smtp.gmail.com")
        assert svc.is_configured is True


# ---------------------------------------------------------------------------
# send_email
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSendEmail:
    async def test_returns_false_when_unconfigured(self):
        svc = _make_service(smtp_host=None)
        result = await svc.send_email("a@b.com", "Subject", "<p>hi</p>", "hi")
        assert result is False

    async def test_does_not_raise_when_unconfigured(self):
        svc = _make_service(smtp_host=None)
        # Should silently return False, not raise
        result = await svc.send_email("a@b.com", "Subject", "<p>hi</p>", "hi")
        assert result is False

    async def test_calls_aiosmtplib_when_configured(self):
        svc = _make_service(smtp_host="smtp.example.com")
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await svc.send_email("a@b.com", "Subject", "<p>hi</p>", "hi")
        assert result is True
        mock_send.assert_called_once()

    async def test_returns_false_on_smtp_error(self):
        svc = _make_service(smtp_host="smtp.example.com")
        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            result = await svc.send_email("a@b.com", "Subject", "<p>hi</p>", "hi")
        assert result is False


# ---------------------------------------------------------------------------
# Email header injection prevention
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestEmailHeaderInjection:
    """Verify that CR/LF in subject/to_email cannot inject extra headers."""

    async def _captured_msg(self, svc, subject, to_email):
        """Send an email and return the MIMEMultipart message passed to aiosmtplib."""
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["msg"] = msg

        with patch("app.services.email_service.aiosmtplib.send", side_effect=fake_send):
            await svc.send_email(to_email, subject, "<p>hi</p>", "hi")
        return captured.get("msg")

    async def test_subject_crlf_stripped(self):
        svc = _make_service(smtp_host="smtp.example.com")
        msg = await self._captured_msg(
            svc,
            subject="Legit\r\nBcc: attacker@evil.com",
            to_email="user@example.com",
        )
        assert msg is not None
        subject_val = msg["Subject"]
        # CRLF must be stripped — without them the "Bcc:" text is harmless (not a header)
        assert "\r" not in subject_val
        assert "\n" not in subject_val

    async def test_subject_lf_only_stripped(self):
        svc = _make_service(smtp_host="smtp.example.com")
        msg = await self._captured_msg(
            svc,
            subject="Hello\nBcc: evil@attacker.com",
            to_email="user@example.com",
        )
        assert msg is not None
        assert "\n" not in msg["Subject"]

    async def test_to_email_crlf_stripped(self):
        svc = _make_service(smtp_host="smtp.example.com")
        msg = await self._captured_msg(
            svc,
            subject="Normal Subject",
            to_email="user@example.com\r\nBcc: attacker@evil.com",
        )
        assert msg is not None
        to_val = msg["To"]
        assert "\r" not in to_val
        assert "\n" not in to_val

    async def test_clean_subject_unchanged(self):
        svc = _make_service(smtp_host="smtp.example.com")
        msg = await self._captured_msg(
            svc,
            subject="Nest Egg: Your weekly summary",
            to_email="user@example.com",
        )
        assert msg is not None
        assert msg["Subject"] == "Nest Egg: Your weekly summary"

    async def test_send_notification_email_subject_sanitized(self):
        """End-to-end: notification title with newlines must not inject headers."""
        svc = _make_service(smtp_host="smtp.example.com")
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["msg"] = msg

        with patch("app.services.email_service.aiosmtplib.send", side_effect=fake_send):
            await svc.send_notification_email(
                to_email="user@example.com",
                title="Alert\r\nBcc: attacker@evil.com",
                message="Something happened",
            )

        msg = captured.get("msg")
        assert msg is not None
        # CRLF must be stripped — that eliminates the header injection vector
        assert "\r" not in msg["Subject"]
        assert "\n" not in msg["Subject"]


# ---------------------------------------------------------------------------
# send_verification_email
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSendVerificationEmail:
    async def test_builds_correct_url(self):
        svc = _make_service(smtp_host="smtp.example.com", app_base_url="https://app.example.com")
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["body"] = msg.as_string()

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=fake_send,
        ):
            await svc.send_verification_email("user@test.com", "mytoken123", "Alice")

        assert "https://app.example.com/verify-email?token=mytoken123" in captured["body"]

    async def test_returns_false_when_unconfigured(self):
        svc = _make_service(smtp_host=None)
        result = await svc.send_verification_email("u@t.com", "tok", "Alice")
        assert result is False


# ---------------------------------------------------------------------------
# send_invitation_email
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSendInvitationEmail:
    async def test_builds_correct_url(self):
        svc = _make_service(smtp_host="smtp.example.com", app_base_url="https://app.example.com")
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["body"] = msg.as_string()

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=fake_send,
        ):
            await svc.send_invitation_email("invite@test.com", "abc123code", "Bob", "The Smiths")

        assert "https://app.example.com/accept-invite?code=abc123code" in captured["body"]
        assert "The Smiths" in captured["body"]
        assert "Bob" in captured["body"]

    async def test_returns_false_when_unconfigured(self):
        svc = _make_service(smtp_host=None)
        result = await svc.send_invitation_email("a@b.com", "code", "Bob", "Org")
        assert result is False


# ---------------------------------------------------------------------------
# hash_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHashToken:
    def test_returns_sha256_hex(self):
        raw = "some_raw_token"
        expected = hashlib.sha256(raw.encode()).hexdigest()
        assert hash_token(raw) == expected

    def test_deterministic(self):
        assert hash_token("abc") == hash_token("abc")

    def test_different_inputs_produce_different_hashes(self):
        assert hash_token("abc") != hash_token("xyz")


# ---------------------------------------------------------------------------
# create_verification_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreateVerificationToken:
    async def test_returns_raw_token(self):
        user_id = uuid4()
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        raw = await create_verification_token(db, user_id)

        assert isinstance(raw, str)
        assert len(raw) > 20  # token_urlsafe(32) is ~43 chars

    async def test_stored_token_hash_matches(self):
        """Token stored in DB should be the SHA-256 of the returned raw token."""
        user_id = uuid4()
        stored_record = None

        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        def capture_add(record):
            nonlocal stored_record
            stored_record = record

        db.add = capture_add

        raw = await create_verification_token(db, user_id)

        assert stored_record is not None
        assert stored_record.token_hash == hash_token(raw)
        assert stored_record.user_id == user_id


# ---------------------------------------------------------------------------
# create_password_reset_token
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestCreatePasswordResetToken:
    async def test_returns_raw_token(self):
        user_id = uuid4()
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()

        raw = await create_password_reset_token(db, user_id)

        assert isinstance(raw, str)
        assert len(raw) > 20  # token_urlsafe(32) is ~43 chars

    async def test_stored_token_hash_matches(self):
        """Token stored in DB should be the SHA-256 of the returned raw token."""
        user_id = uuid4()
        stored_record = None

        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        def capture_add(record):
            nonlocal stored_record
            stored_record = record

        db.add = capture_add

        raw = await create_password_reset_token(db, user_id)

        assert stored_record is not None
        assert stored_record.token_hash == hash_token(raw)
        assert stored_record.user_id == user_id

    async def test_expires_in_fifteen_minutes(self):
        """Password reset tokens expire in 15 minutes to limit leaked-email replay window."""
        user_id = uuid4()
        stored_record = None

        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        def capture_add(record):
            nonlocal stored_record
            stored_record = record

        db.add = capture_add

        before = utc_now()
        await create_password_reset_token(db, user_id)

        assert stored_record is not None
        # Should expire roughly 15 minutes from now (between 14 and 16 minutes)
        delta = stored_record.expires_at - before
        assert timedelta(minutes=14) < delta < timedelta(minutes=16)


# ---------------------------------------------------------------------------
# send_password_reset_email
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestSendPasswordResetEmail:
    async def test_builds_correct_url(self):
        svc = _make_service(smtp_host="smtp.example.com", app_base_url="https://app.example.com")
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["body"] = msg.as_string()

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=fake_send,
        ):
            await svc.send_password_reset_email("user@test.com", "resettoken456", "Bob")

        assert "https://app.example.com/reset-password?token=resettoken456" in captured["body"]

    async def test_returns_false_when_unconfigured(self):
        svc = _make_service(smtp_host=None)
        result = await svc.send_password_reset_email("u@t.com", "tok", "Bob")
        assert result is False

    async def test_includes_display_name_in_email(self):
        svc = _make_service(smtp_host="smtp.example.com")
        captured = {}

        async def fake_send(msg, **kwargs):
            captured["body"] = msg.as_string()

        with patch(
            "app.services.email_service.aiosmtplib.send",
            new_callable=AsyncMock,
            side_effect=fake_send,
        ):
            await svc.send_password_reset_email("user@test.com", "tok", "Charlie")

        assert "Charlie" in captured["body"]
