"""
Natural language transaction search parser.

Converts free-text queries like:
  "coffee last month over $5"
  "amazon between jan and march"
  "income in 2025"
  "rent over $1000 this year"

into structured filter parameters that the existing transaction list endpoint
already understands: search string, date range, amount range, and category hint.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Parsed result
# ---------------------------------------------------------------------------


@dataclass
class ParsedQuery:
    """Structured representation of a natural-language transaction query."""

    search: Optional[str] = None  # Keyword for merchant_name / description
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_income: Optional[bool] = None  # True = income, False = expenses, None = both
    category_hint: Optional[str] = None  # Suggested category filter text
    raw_query: str = ""


# ---------------------------------------------------------------------------
# Relative date helpers
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}


def _month_range(year: int, month: int) -> tuple[date, date]:
    """Return (first_day, last_day) for a given year/month."""
    import calendar

    _, last_day = calendar.monthrange(year, month)
    return date(year, month, 1), date(year, month, last_day)


def _resolve_relative_date(token: str, today: date) -> Optional[tuple[date, date]]:
    """
    Resolve common relative date expressions to (start, end) inclusive ranges.
    Returns None if not recognised.
    """
    t = token.lower().strip()

    if t in ("today",):
        return today, today
    if t in ("yesterday",):
        d = today - timedelta(days=1)
        return d, d
    if t in ("this week", "thisweek"):
        start = today - timedelta(days=today.weekday())
        return start, today
    if t in ("last week", "lastweek"):
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
        return start, end
    if t in ("this month", "thismonth"):
        return _month_range(today.year, today.month)
    if t in ("last month", "lastmonth"):
        m = today.month - 1 if today.month > 1 else 12
        y = today.year if today.month > 1 else today.year - 1
        return _month_range(y, m)
    if t in ("this year", "thisyear"):
        return date(today.year, 1, 1), date(today.year, 12, 31)
    if t in ("last year", "lastyear"):
        y = today.year - 1
        return date(y, 1, 1), date(y, 12, 31)
    if t in ("last 30 days", "last30days", "past 30 days"):
        return today - timedelta(days=30), today
    if t in ("last 90 days", "last90days", "past 90 days"):
        return today - timedelta(days=90), today
    if t in ("last 6 months", "last6months", "past 6 months"):
        return today - timedelta(days=182), today
    if t in ("ytd", "year to date"):
        return date(today.year, 1, 1), today

    # Named month (e.g. "in january", "january 2024", "march")
    month_re = re.match(r"(?:in\s+)?(" + "|".join(_MONTH_NAMES.keys()) + r")(?:\s+(\d{4}))?$", t)
    if month_re:
        month_name, year_str = month_re.groups()
        month_num = _MONTH_NAMES[month_name]
        year = int(year_str) if year_str else today.year
        return _month_range(year, month_num)

    # Plain 4-digit year (e.g. "in 2024", "2025")
    year_re = re.match(r"(?:in\s+)?(\d{4})$", t)
    if year_re:
        y = int(year_re.group(1))
        return date(y, 1, 1), date(y, 12, 31)

    return None


# ---------------------------------------------------------------------------
# Amount extraction
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(
    r"(?:"
    r"(?:over|above|more than|greater than|>)\s*\$?([\d,]+(?:\.\d{1,2})?)"
    r"|(?:under|below|less than|<)\s*\$?([\d,]+(?:\.\d{1,2})?)"
    r"|between\s+\$?([\d,]+(?:\.\d{1,2})?)\s+and\s+\$?([\d,]+(?:\.\d{1,2})?)"
    r"|\$?([\d,]+(?:\.\d{1,2})?)(?:\s*\+)?"
    r")",
    re.IGNORECASE,
)


def _parse_amount(text: str) -> tuple[Optional[float], Optional[float], str]:
    """
    Extract min/max amount from text.
    Returns (min_amount, max_amount, text_with_amount_removed).
    """
    min_amt: Optional[float] = None
    max_amt: Optional[float] = None
    cleaned = text

    for m in _AMOUNT_RE.finditer(text):
        over, under, bet_low, bet_high, exact = m.groups()
        if over:
            min_amt = float(over.replace(",", ""))
        elif under:
            max_amt = float(under.replace(",", ""))
        elif bet_low and bet_high:
            min_amt = float(bet_low.replace(",", ""))
            max_amt = float(bet_high.replace(",", ""))
        elif exact:
            # Bare dollar amount — treat as exact ±10%
            v = float(exact.replace(",", ""))
            min_amt = round(v * 0.9, 2)
            max_amt = round(v * 1.1, 2)
        cleaned = cleaned[: m.start()] + " " + cleaned[m.end() :]
        break  # only first match

    return min_amt, max_amt, cleaned.strip()


# ---------------------------------------------------------------------------
# Income / expense detection
# ---------------------------------------------------------------------------

_INCOME_WORDS = {"income", "salary", "paycheck", "deposit", "deposits", "earnings", "revenue"}
_EXPENSE_WORDS = {"expense", "expenses", "spending", "spent", "purchases", "charges", "debits"}


def _detect_income_flag(text: str) -> tuple[Optional[bool], str]:
    """Detect if the query is asking about income or expenses."""
    words = set(re.split(r"\W+", text.lower()))
    if words & _INCOME_WORDS:
        cleaned = re.sub(
            r"\b(" + "|".join(_INCOME_WORDS) + r")\b", "", text, flags=re.IGNORECASE
        ).strip()
        return True, cleaned
    if words & _EXPENSE_WORDS:
        cleaned = re.sub(
            r"\b(" + "|".join(_EXPENSE_WORDS) + r")\b", "", text, flags=re.IGNORECASE
        ).strip()
        return False, cleaned
    return None, text


# ---------------------------------------------------------------------------
# Date range extraction
# ---------------------------------------------------------------------------

_DATE_PHRASES = [
    # Longer phrases first to avoid partial matches
    "last 30 days",
    "past 30 days",
    "last 90 days",
    "past 90 days",
    "last 6 months",
    "past 6 months",
    "last week",
    "this week",
    "last month",
    "this month",
    "last year",
    "this year",
    "year to date",
    "ytd",
    "yesterday",
    "today",
]

_DATE_PHRASE_RE = re.compile(
    r"\b(?:in\s+)?("
    + "|".join(re.escape(p) for p in _DATE_PHRASES)
    + r"|(?:in\s+)?(?:"
    + "|".join(_MONTH_NAMES.keys())
    + r")(?:\s+\d{4})?"
    + r"|(?:in\s+)?\d{4}"
    + r")\b",
    re.IGNORECASE,
)

_BETWEEN_DATE_RE = re.compile(
    r"between\s+(\w+(?:\s+\d{4})?)\s+and\s+(\w+(?:\s+\d{4})?)",
    re.IGNORECASE,
)


def _extract_date_range(text: str, today: date) -> tuple[Optional[date], Optional[date], str]:
    """
    Extract date range from text.
    Returns (start_date, end_date, text_with_date_removed).
    """
    start: Optional[date] = None
    end: Optional[date] = None
    cleaned = text

    # "between X and Y"
    bet = _BETWEEN_DATE_RE.search(text)
    if bet:
        r1 = _resolve_relative_date(bet.group(1), today)
        r2 = _resolve_relative_date(bet.group(2), today)
        if r1 and r2:
            start = min(r1[0], r2[0])
            end = max(r1[1], r2[1])
            cleaned = text[: bet.start()] + text[bet.end() :]
            return start, end, cleaned.strip()

    # Single phrase
    m = _DATE_PHRASE_RE.search(text)
    if m:
        phrase = m.group(1)
        resolved = _resolve_relative_date(phrase, today)
        if resolved:
            start, end = resolved
            cleaned = text[: m.start()] + text[m.end() :]

    return start, end, cleaned.strip()


# ---------------------------------------------------------------------------
# Stopword removal
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "show",
    "find",
    "get",
    "search",
    "for",
    "me",
    "my",
    "all",
    "the",
    "a",
    "an",
    "transactions",
    "transaction",
    "payments",
    "payment",
    "charges",
    "charge",
    "from",
    "to",
    "at",
    "with",
    "on",
    "of",
    "by",
    "that",
    "were",
    "was",
    "are",
    "is",
    "any",
    "where",
    "which",
    "have",
    "i",
    "spent",
}


def _clean_keyword(text: str) -> Optional[str]:
    """Strip stop words and return a meaningful keyword, or None if nothing left."""
    text = re.sub(r"\s+", " ", text).strip()
    words = [w for w in re.split(r"\W+", text) if w and w.lower() not in _STOPWORDS]
    result = " ".join(words).strip()
    return result if result else None


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------


def parse_natural_query(query: str, today: Optional[date] = None) -> ParsedQuery:
    """
    Parse a free-text query into a structured ParsedQuery.

    Examples:
        "coffee last month"        → search="coffee", last month range
        "amazon over $50 in 2024"  → search="amazon", min_amount=50, year 2024
        "income this year"         → is_income=True, this year range
        "rent over $1000"          → search="rent", min_amount=1000
    """
    if today is None:
        today = date.today()

    raw = query
    text = query.strip()

    # 1. Income/expense flag
    is_income, text = _detect_income_flag(text)

    # 2. Date range
    start_date, end_date, text = _extract_date_range(text, today)

    # 3. Amount
    min_amount, max_amount, text = _parse_amount(text)

    # 4. Keyword (whatever is left)
    keyword = _clean_keyword(text)

    return ParsedQuery(
        search=keyword,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        is_income=is_income,
        raw_query=raw,
    )
