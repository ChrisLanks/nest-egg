"""Error logging service with PII redaction for production safety."""

import re
import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime


class ErrorLoggingService:
    """Service for logging errors with PII redaction."""

    # PII patterns to redact from logs
    PII_PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
        'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'password': r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'\s]+)',
        'token': r'(token|jwt|bearer)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{20,})',
        'api_key': r'(api[_-]?key|apikey|key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{20,})',
    }

    @staticmethod
    def redact_pii(text: str) -> str:
        """
        Redact PII from text.

        Args:
            text: Text potentially containing PII

        Returns:
            Text with PII redacted
        """
        if not text:
            return text

        redacted = text

        # Redact emails
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['email'],
            '[REDACTED_EMAIL]',
            redacted
        )

        # Redact SSNs
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['ssn'],
            '[REDACTED_SSN]',
            redacted
        )

        # Redact credit cards
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['credit_card'],
            '[REDACTED_CC]',
            redacted
        )

        # Redact phone numbers
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['phone'],
            '[REDACTED_PHONE]',
            redacted
        )

        # Redact passwords (keep key name, redact value)
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['password'],
            r'\1=[REDACTED_PASSWORD]',
            redacted,
            flags=re.IGNORECASE
        )

        # Redact tokens
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['token'],
            r'\1=[REDACTED_TOKEN]',
            redacted,
            flags=re.IGNORECASE
        )

        # Redact API keys
        redacted = re.sub(
            ErrorLoggingService.PII_PATTERNS['api_key'],
            r'\1=[REDACTED_KEY]',
            redacted,
            flags=re.IGNORECASE
        )

        return redacted

    @staticmethod
    def log_error(
        logger: logging.Logger,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> None:
        """
        Log error with PII redaction.

        Args:
            logger: Logger instance
            error: Exception to log
            context: Additional context (will be redacted)
            user_id: User ID (not PII, safe to log)
        """
        # Get error traceback
        error_traceback = ''.join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))

        # Redact PII from error message and traceback
        error_message = ErrorLoggingService.redact_pii(str(error))
        error_traceback = ErrorLoggingService.redact_pii(error_traceback)

        # Build log message
        log_parts = [
            f"Error: {error_message}",
            f"Type: {type(error).__name__}",
        ]

        if user_id:
            log_parts.append(f"User ID: {user_id}")

        if context:
            # Redact PII from context
            safe_context = {
                k: ErrorLoggingService.redact_pii(str(v))
                for k, v in context.items()
            }
            log_parts.append(f"Context: {safe_context}")

        log_parts.append(f"Traceback:\n{error_traceback}")

        # Log the error
        logger.error('\n'.join(log_parts))

    @staticmethod
    def log_security_event(
        logger: logging.Logger,
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log security-related event.

        Args:
            logger: Logger instance
            event_type: Type of security event (login_failure, rate_limit, etc.)
            message: Event description
            user_id: User ID if applicable
            ip_address: Source IP address
            additional_data: Additional event data
        """
        timestamp = datetime.utcnow().isoformat()

        log_data = {
            "timestamp": timestamp,
            "event_type": event_type,
            "message": ErrorLoggingService.redact_pii(message),
        }

        if user_id:
            log_data["user_id"] = user_id

        if ip_address:
            # Log first 3 octets only for privacy
            log_data["ip_prefix"] = '.'.join(ip_address.split('.')[:3]) + '.xxx'

        if additional_data:
            log_data["data"] = {
                k: ErrorLoggingService.redact_pii(str(v))
                for k, v in additional_data.items()
            }

        logger.warning(f"SECURITY_EVENT: {log_data}")

    @staticmethod
    def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize request data for logging.

        Args:
            data: Request data dictionary

        Returns:
            Sanitized dictionary safe for logging
        """
        if not data:
            return {}

        sanitized = {}

        for key, value in data.items():
            key_lower = key.lower()

            # Always redact sensitive fields
            if any(sensitive in key_lower for sensitive in [
                'password', 'secret', 'token', 'key', 'auth', 'credential'
            ]):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, str):
                # Redact PII from string values
                sanitized[key] = ErrorLoggingService.redact_pii(value)
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = ErrorLoggingService.sanitize_request_data(value)
            elif isinstance(value, list):
                # Sanitize list items if they're dicts or strings
                sanitized[key] = [
                    ErrorLoggingService.sanitize_request_data(item) if isinstance(item, dict)
                    else ErrorLoggingService.redact_pii(str(item)) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                # Keep non-sensitive types as-is
                sanitized[key] = value

        return sanitized


# Create singleton instance
error_logging_service = ErrorLoggingService()
