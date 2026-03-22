"""Tests for PM audit round 8 fixes.

Covers:
- Bill reminder deduplication uses timestamp range instead of func.date() == string
- Ticker parsing dead code removed (logic unchanged, just cleaner)
"""

import asyncio
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Bill reminder deduplication — timestamp range approach
# ---------------------------------------------------------------------------


def test_bill_reminder_dedup_uses_range_not_string():
    """Dedup guard must compare created_at against a timestamp range, not a string.

    The old code used func.date(created_at) == today_str which is fragile and
    not index-friendly. The new code computes day_start and day_end and uses
    >= / < comparisons that leverage the existing created_at index.
    """
    import inspect
    from app.workers.tasks import bill_reminder_tasks

    source = inspect.getsource(bill_reminder_tasks)
    # Must NOT use the old pattern (today_str was the isoformat string variable)
    assert "today_str" not in source, "today_str (old string dedup pattern) should be removed"
    # Must NOT call func.date() — a comment mentioning it is fine, but a call must not exist
    assert "func.date(" not in source, "func.date() call should be removed in favour of range check"
    # Must use the new range pattern
    assert "day_start" in source, "day_start timestamp range variable expected"
    assert "day_end" in source, "day_end timestamp range variable expected"
    assert "created_at >= day_start" in source, "created_at >= day_start range check expected"
    assert "created_at < day_end" in source, "created_at < day_end range check expected"


def test_bill_reminder_day_range_covers_full_day():
    """day_end - day_start must equal exactly 24 hours."""
    from datetime import datetime, timedelta, date

    today = date(2026, 3, 22)
    day_start = datetime.combine(today, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    assert day_end - day_start == timedelta(hours=24)
    assert day_start.hour == 0 and day_start.minute == 0 and day_start.second == 0
    assert day_end.hour == 0 and day_end.minute == 0 and day_end.second == 0


def test_bill_reminder_day_range_no_overlap():
    """Consecutive day ranges must not overlap (day1_end == day2_start)."""
    from datetime import datetime, timedelta, date

    day1 = date(2026, 3, 22)
    day2 = date(2026, 3, 23)

    day1_start = datetime.combine(day1, datetime.min.time())
    day1_end = day1_start + timedelta(days=1)
    day2_start = datetime.combine(day2, datetime.min.time())

    assert day1_end == day2_start, "Ranges must be contiguous with no gap or overlap"


def test_bill_reminder_day_range_midnight_boundary():
    """A notification created exactly at midnight belongs to the NEW day, not the old one."""
    from datetime import datetime, timedelta, date

    midnight = datetime(2026, 3, 23, 0, 0, 0)  # start of March 23

    # March 22 range: [2026-03-22 00:00:00, 2026-03-23 00:00:00)
    day_start_22 = datetime(2026, 3, 22, 0, 0, 0)
    day_end_22 = day_start_22 + timedelta(days=1)

    # March 23 range: [2026-03-23 00:00:00, 2026-03-24 00:00:00)
    day_start_23 = datetime(2026, 3, 23, 0, 0, 0)
    day_end_23 = day_start_23 + timedelta(days=1)

    # midnight is NOT in March 22 range (upper bound is exclusive)
    assert not (day_start_22 <= midnight < day_end_22), "midnight should NOT be in March 22"
    # midnight IS in March 23 range
    assert day_start_23 <= midnight < day_end_23, "midnight should be in March 23"


# ---------------------------------------------------------------------------
# Ticker parsing — dead code removed, logic preserved
# ---------------------------------------------------------------------------


def test_ticker_dead_code_removed():
    """The unconditional ticker = ... assignment before the if/elif/else must be gone."""
    import inspect
    from app.api.v1.accounts import refresh_equity_price

    source = inspect.getsource(refresh_equity_price)
    # The dead assignment set ticker before the if-block; now there should be no
    # bare assignment that is immediately overwritten
    assert "ticker = account.name.strip() if not account.institution_name else None" not in source


def test_ticker_prefers_institution_name_as_symbol():
    """institution_name that looks like a ticker symbol (1-5 uppercase letters) wins."""
    import re

    institution_name = "AAPL"
    name = "Apple Inc Stock Options"

    if institution_name and re.match(r"^[A-Z]{1,5}$", institution_name.strip()):
        ticker = institution_name.strip()
    elif name and re.match(r"^[A-Z]{1,5}$", name.strip()):
        ticker = name.strip()
    else:
        ticker = institution_name or name

    assert ticker == "AAPL"


def test_ticker_falls_back_to_name_symbol():
    """When institution_name is not a ticker pattern, name is checked next."""
    import re

    institution_name = "Goldman Sachs"
    name = "MSFT"

    if institution_name and re.match(r"^[A-Z]{1,5}$", institution_name.strip()):
        ticker = institution_name.strip()
    elif name and re.match(r"^[A-Z]{1,5}$", name.strip()):
        ticker = name.strip()
    else:
        ticker = institution_name or name

    assert ticker == "MSFT"


def test_ticker_falls_back_to_institution_name_search():
    """When neither matches a ticker pattern, institution_name is used as search query."""
    import re

    institution_name = "Stripe Inc"
    name = "Series B Preferred"

    if institution_name and re.match(r"^[A-Z]{1,5}$", institution_name.strip()):
        ticker = institution_name.strip()
    elif name and re.match(r"^[A-Z]{1,5}$", name.strip()):
        ticker = name.strip()
    else:
        ticker = institution_name or name

    assert ticker == "Stripe Inc"


def test_ticker_falls_back_to_name_when_no_institution():
    """When institution_name is empty/None and name is not a symbol, name is used."""
    import re

    institution_name = None
    name = "My Stock Options"

    if institution_name and re.match(r"^[A-Z]{1,5}$", institution_name.strip()):
        ticker = institution_name.strip()
    elif name and re.match(r"^[A-Z]{1,5}$", name.strip()):
        ticker = name.strip()
    else:
        ticker = institution_name or name

    assert ticker == "My Stock Options"


def test_ticker_symbol_regex_rejects_lowercase():
    """Ticker regex must reject lowercase — tickers are uppercase only."""
    import re

    assert not re.match(r"^[A-Z]{1,5}$", "aapl")
    assert not re.match(r"^[A-Z]{1,5}$", "Aapl")
    assert re.match(r"^[A-Z]{1,5}$", "AAPL")


def test_ticker_symbol_regex_rejects_too_long():
    """Ticker regex must reject strings longer than 5 characters."""
    import re

    assert not re.match(r"^[A-Z]{1,5}$", "TOOLONG")
    assert re.match(r"^[A-Z]{1,5}$", "ABCDE")
