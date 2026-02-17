"""Logging utilities for PII redaction and secure logging."""

import hashlib
from typing import Optional


def redact_email(email: Optional[str]) -> str:
    """
    Redact email address for logging while maintaining uniqueness.

    Args:
        email: Email address to redact

    Returns:
        Redacted email in format: u***@example.com or hash:abc123 for empty local parts
        Returns 'N/A' if email is None or empty

    Examples:
        >>> redact_email("user@example.com")
        'u***@example.com'
        >>> redact_email("a@example.com")
        'hash:9a7b3c'
        >>> redact_email(None)
        'N/A'
    """
    if not email:
        return "N/A"

    try:
        local, domain = email.split("@", 1)

        # If local part is too short (< 3 chars), use hash for privacy
        if len(local) < 3:
            # Create a short hash for uniqueness in logs
            email_hash = hashlib.sha256(email.encode()).hexdigest()[:6]
            return f"hash:{email_hash}@{domain}"

        # Show first char + *** + domain
        return f"{local[0]}***@{domain}"

    except (ValueError, IndexError):
        # Malformed email - hash it
        email_hash = hashlib.sha256(str(email).encode()).hexdigest()[:6]
        return f"hash:{email_hash}"


def redact_ip(ip_address: Optional[str]) -> str:
    """
    Redact IP address for logging while maintaining network info.

    Args:
        ip_address: IP address to redact

    Returns:
        Redacted IP in format: xxx.xxx.xxx.0 or xxx:xxx:xxx:0 for IPv6

    Examples:
        >>> redact_ip("192.168.1.100")
        '192.168.1.***'
        >>> redact_ip(None)
        'N/A'
    """
    if not ip_address:
        return "N/A"

    # IPv4
    if "." in ip_address:
        parts = ip_address.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.***"

    # IPv6 (simplified)
    if ":" in ip_address:
        parts = ip_address.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:3]) + ":***"

    # Unknown format - hash it
    ip_hash = hashlib.sha256(str(ip_address).encode()).hexdigest()[:6]
    return f"hash:{ip_hash}"
