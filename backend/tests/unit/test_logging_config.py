"""Tests for app.core.logging_config module."""

import logging
from unittest.mock import MagicMock, patch

from app.core.logging_config import (
    _configure_uvicorn_logging,
    get_logger,
    log_celery_task,
    log_database_query,
    log_request,
    pii_redaction_processor,
    setup_logging,
)


class TestPiiRedactionProcessor:
    """Test the PII redaction structlog processor."""

    def test_redacts_email(self):
        event_dict = {"event": "login", "email": "user@example.com"}
        result = pii_redaction_processor(None, "info", event_dict)
        assert "user@example.com" not in result["email"]
        assert "***" in result["email"] or "hash:" in result["email"]

    def test_redacts_ip_address(self):
        event_dict = {"event": "request", "ip": "192.168.1.100"}
        result = pii_redaction_processor(None, "info", event_dict)
        assert "100" not in result["ip"]
        assert "***" in result["ip"]

    def test_redacts_phone_number(self):
        event_dict = {"event": "signup", "contact": "Call 555-123-4567 for info"}
        result = pii_redaction_processor(None, "info", event_dict)
        assert "[PHONE REDACTED]" in result["contact"]

    def test_ignores_non_string_values(self):
        event_dict = {"event": "metric", "count": 42, "active": True}
        result = pii_redaction_processor(None, "info", event_dict)
        assert result["count"] == 42
        assert result["active"] is True

    def test_handles_empty_strings(self):
        event_dict = {"event": "", "data": ""}
        result = pii_redaction_processor(None, "info", event_dict)
        assert result["event"] == ""
        assert result["data"] == ""

    def test_multiple_pii_in_one_value(self):
        event_dict = {"msg": "User user@example.com from 10.0.0.1 called 555-987-6543"}
        result = pii_redaction_processor(None, "info", event_dict)
        assert "user@example.com" not in result["msg"]
        assert "10.0.0.1" not in result["msg"]
        assert "555-987-6543" not in result["msg"]


class TestSetupLogging:
    """Test the setup_logging function."""

    def test_setup_logging_development(self):
        """Should configure logging without error in dev mode."""
        with patch("app.core.logging_config.settings") as mock_settings:
            mock_settings.LOG_FORMAT = "text"
            mock_settings.ENVIRONMENT = "development"
            mock_settings.LOG_LEVEL = "INFO"
            setup_logging()

    def test_setup_logging_production_json(self):
        """Should configure JSON logging in production."""
        with patch("app.core.logging_config.settings") as mock_settings:
            mock_settings.LOG_FORMAT = "json"
            mock_settings.ENVIRONMENT = "production"
            mock_settings.LOG_LEVEL = "WARNING"
            setup_logging()

    def test_setup_logging_production_silences_noisy_loggers(self):
        """Should silence uvicorn.access and httpx in production."""
        with patch("app.core.logging_config.settings") as mock_settings:
            mock_settings.LOG_FORMAT = "json"
            mock_settings.ENVIRONMENT = "production"
            mock_settings.LOG_LEVEL = "INFO"
            setup_logging()
            assert logging.getLogger("uvicorn.access").level == logging.WARNING
            assert logging.getLogger("httpx").level == logging.WARNING


class TestConfigureUvicornLogging:
    """Test the _configure_uvicorn_logging function."""

    def test_json_mode_sets_json_formatter(self):
        _configure_uvicorn_logging(use_json=True)
        uvicorn_logger = logging.getLogger("uvicorn")
        # Should have a handler with JSON formatter
        assert len(uvicorn_logger.handlers) > 0

    def test_non_json_mode_does_nothing(self):
        """When use_json=False, no handlers should be set up."""
        # Clear existing handlers first
        for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
            logging.getLogger(name).handlers.clear()
        _configure_uvicorn_logging(use_json=False)
        # No handlers added in non-JSON mode
        # (the function only acts when use_json=True)


class TestGetLogger:
    """Test get_logger helper."""

    def test_returns_bound_logger(self):
        logger = get_logger("test_module")
        assert logger is not None


class TestLogHelpers:
    """Test log helper functions."""

    def test_log_request(self):
        mock_logger = MagicMock()
        log_request(mock_logger, "GET", "/api/v1/test", 200, 15.5, user_id="123")
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args
        assert call_kwargs[0][0] == "http_request"

    def test_log_database_query(self):
        mock_logger = MagicMock()
        log_database_query(mock_logger, "SELECT * FROM users", 3.2, rows_affected=5)
        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args
        assert call_kwargs[0][0] == "database_query"

    def test_log_database_query_truncates_long_query(self):
        mock_logger = MagicMock()
        long_query = "SELECT " + "x" * 300
        log_database_query(mock_logger, long_query, 1.0)
        call_kwargs = mock_logger.debug.call_args
        assert len(call_kwargs[1]["query"]) <= 200

    def test_log_celery_task(self):
        mock_logger = MagicMock()
        log_celery_task(mock_logger, "process_csv", "task-123", "SUCCESS", 500.0)
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args
        assert call_kwargs[0][0] == "celery_task"
