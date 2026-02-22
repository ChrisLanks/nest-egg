"""Tests for the PII auto-redaction structlog processor."""

import pytest

from app.core.logging_config import pii_redaction_processor


@pytest.mark.unit
class TestPiiRedactionProcessor:
    """Tests for pii_redaction_processor inserted into the structlog chain."""

    def _run(self, event_dict: dict) -> dict:
        """Invoke the processor and return the modified event_dict."""
        return pii_redaction_processor(None, "info", event_dict)

    # ── Email redaction ──────────────────────────────────────────────────────

    def test_email_in_event_message_is_redacted(self):
        """Emails embedded in the 'event' string should be redacted."""
        result = self._run({"event": "Login attempt for user@example.com failed"})
        assert "user@example.com" not in result["event"]
        assert "u***@example.com" in result["event"]

    def test_email_in_arbitrary_field_is_redacted(self):
        """Emails in any string field should be redacted."""
        result = self._run({"email": "admin@corp.org", "event": "test"})
        assert "admin@corp.org" not in result["email"]

    def test_multiple_emails_in_one_field(self):
        """All email addresses in a single string value should be redacted."""
        result = self._run({"event": "Sent to alice@a.com and bob@b.com"})
        assert "alice@a.com" not in result["event"]
        assert "bob@b.com" not in result["event"]

    # ── IPv4 redaction ───────────────────────────────────────────────────────

    def test_ipv4_in_field_is_redacted(self):
        """IPv4 addresses should be partially redacted (last octet masked)."""
        result = self._run({"event": "Request from 192.168.1.100"})
        assert "192.168.1.100" not in result["event"]
        # redact_ip keeps first 3 octets
        assert "192.168.1.***" in result["event"]

    def test_multiple_ips_redacted(self):
        """Multiple IPs in a single value should all be redacted."""
        result = self._run({"event": "10.0.0.1 forwarded to 172.16.0.5"})
        assert "10.0.0.1" not in result["event"]
        assert "172.16.0.5" not in result["event"]

    # ── Phone number redaction ───────────────────────────────────────────────

    def test_us_phone_number_redacted(self):
        """US phone numbers (xxx-xxx-xxxx) should be replaced with [PHONE REDACTED]."""
        result = self._run({"event": "Call 555-867-5309 for support"})
        assert "555-867-5309" not in result["event"]
        assert "[PHONE REDACTED]" in result["event"]

    def test_phone_with_dots_redacted(self):
        """Phone in 555.867.5309 format should be redacted."""
        result = self._run({"event": "Contact 555.867.5309"})
        assert "555.867.5309" not in result["event"]
        assert "[PHONE REDACTED]" in result["event"]

    # ── Non-string values are untouched ─────────────────────────────────────

    def test_integer_value_not_modified(self):
        """Non-string values should pass through unchanged."""
        result = self._run({"count": 42, "event": "ok"})
        assert result["count"] == 42

    def test_none_value_not_modified(self):
        """None values should pass through unchanged."""
        result = self._run({"key": None, "event": "ok"})
        assert result["key"] is None

    def test_list_value_not_modified(self):
        """List values are not processed (only top-level strings)."""
        result = self._run({"items": ["user@example.com"], "event": "ok"})
        # Lists are not string — processor skips them
        assert result["items"] == ["user@example.com"]

    # ── Non-PII strings pass through unchanged ───────────────────────────────

    def test_clean_string_unmodified(self):
        """Strings with no PII should be returned as-is."""
        result = self._run({"event": "User logged in successfully", "level": "info"})
        assert result["event"] == "User logged in successfully"

    def test_event_dict_keys_preserved(self):
        """All keys in the event_dict should remain after processing."""
        original = {"event": "test", "level": "info", "count": 3}
        result = self._run(original)
        assert set(result.keys()) == set(original.keys())

    def test_processor_returns_event_dict(self):
        """The processor must return the event_dict (structlog contract)."""
        event_dict = {"event": "hello"}
        result = pii_redaction_processor(None, "debug", event_dict)
        assert isinstance(result, dict)
        assert "event" in result

    # ── Combined PII in single field ─────────────────────────────────────────

    def test_combined_pii_all_redacted(self):
        """A field containing email + IP + phone should have all three redacted."""
        messy = "user@example.com logged in from 10.0.0.55 and called 555-123-4567"
        result = self._run({"event": messy})
        event = result["event"]
        assert "user@example.com" not in event
        assert "10.0.0.55" not in event
        assert "555-123-4567" not in event
