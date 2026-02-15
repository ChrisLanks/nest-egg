"""DateTime utilities for timezone-aware timestamp handling.

This module provides utility functions for consistent datetime handling
across the application, replacing deprecated datetime.utcnow() with
timezone-aware alternatives.
"""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """
    Get current UTC datetime without timezone info (offset-naive).

    Replaces deprecated datetime.utcnow() with datetime.now(timezone.utc).
    Returns offset-naive datetime compatible with PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns.

    Returns:
        Current UTC datetime without timezone info

    Example:
        >>> now = utc_now()
        >>> print(now.tzinfo)
        None
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Lambda version for SQLAlchemy default/onupdate parameters
utc_now_lambda = lambda: datetime.now(timezone.utc).replace(tzinfo=None)
