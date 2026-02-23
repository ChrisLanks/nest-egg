"""Shared date range validation for API endpoints."""

from datetime import date

from fastapi import HTTPException

MAX_RANGE_DAYS = 18250  # ~50 years


def validate_date_range(start_date: date, end_date: date) -> None:
    """Validate date range parameters.

    Raises HTTPException(400) if:
      - start_date is before 1900-01-01
      - end_date is after 2100-12-31
      - start_date is after end_date
      - range exceeds MAX_RANGE_DAYS (~50 years)
    """
    min_date = date(1900, 1, 1)
    max_date = date(2100, 12, 31)

    if start_date < min_date:
        raise HTTPException(
            status_code=400, detail=f"start_date cannot be before {min_date.isoformat()}"
        )

    if end_date > max_date:
        raise HTTPException(
            status_code=400, detail=f"end_date cannot be after {max_date.isoformat()}"
        )

    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="start_date must be before or equal to end_date"
        )

    date_diff = (end_date - start_date).days
    if date_diff > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range cannot exceed {MAX_RANGE_DAYS} days (~50 years)",
        )
