"""DateTime utilities for timezone-aware timestamp handling.

This module provides utility functions for consistent datetime handling
across the application, replacing deprecated datetime.utcnow() with
timezone-aware alternatives.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Get current UTC datetime with timezone awareness.

    Replaces deprecated datetime.utcnow() with datetime.now(timezone.utc).
    This function returns a timezone-aware datetime object.

    Returns:
        Current UTC datetime with timezone info

    Example:
        >>> now = utc_now()
        >>> print(now.tzinfo)
        UTC
    """
    return datetime.now(timezone.utc)


# Lambda version for SQLAlchemy default/onupdate parameters
utc_now_lambda = lambda: datetime.now(timezone.utc)
