"""Unit tests for the NLP natural-language transaction search parser.

Covers: date expressions, amount expressions, income/expense detection,
keyword extraction, combined queries, and edge cases.
"""

from datetime import date

import pytest

from app.services.nlp_search_service import (
    _clean_keyword,
    _detect_income_flag,
    _parse_amount,
    _resolve_relative_date,
    parse_natural_query,
)

# ---------------------------------------------------------------------------
# Fixed reference date for deterministic tests
# ---------------------------------------------------------------------------
TODAY = date(2025, 3, 15)  # Saturday, mid-month


# ===========================================================================
# _resolve_relative_date
# ===========================================================================


class TestResolveRelativeDate:
    def test_today(self):
        start, end = _resolve_relative_date("today", TODAY)
        assert start == TODAY
        assert end == TODAY

    def test_yesterday(self):
        start, end = _resolve_relative_date("yesterday", TODAY)
        assert start == date(2025, 3, 14)
        assert end == date(2025, 3, 14)

    def test_this_week(self):
        # TODAY is Saturday (weekday=5); week starts Monday Mar 10
        start, end = _resolve_relative_date("this week", TODAY)
        assert start == date(2025, 3, 10)
        assert end == TODAY

    def test_last_week(self):
        start, end = _resolve_relative_date("last week", TODAY)
        assert start == date(2025, 3, 3)
        assert end == date(2025, 3, 9)

    def test_this_month(self):
        start, end = _resolve_relative_date("this month", TODAY)
        assert start == date(2025, 3, 1)
        assert end == date(2025, 3, 31)

    def test_last_month(self):
        start, end = _resolve_relative_date("last month", TODAY)
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)  # 2025 is not a leap year

    def test_last_month_january_wraps_to_december(self):
        jan_today = date(2025, 1, 10)
        start, end = _resolve_relative_date("last month", jan_today)
        assert start == date(2024, 12, 1)
        assert end == date(2024, 12, 31)

    def test_this_year(self):
        start, end = _resolve_relative_date("this year", TODAY)
        assert start == date(2025, 1, 1)
        assert end == date(2025, 12, 31)

    def test_last_year(self):
        start, end = _resolve_relative_date("last year", TODAY)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_last_30_days(self):
        start, end = _resolve_relative_date("last 30 days", TODAY)
        assert start == date(2025, 2, 13)
        assert end == TODAY

    def test_last_90_days(self):
        start, end = _resolve_relative_date("last 90 days", TODAY)
        assert start == date(2024, 12, 15)
        assert end == TODAY

    def test_ytd(self):
        start, end = _resolve_relative_date("ytd", TODAY)
        assert start == date(2025, 1, 1)
        assert end == TODAY

    def test_year_to_date(self):
        start, end = _resolve_relative_date("year to date", TODAY)
        assert start == date(2025, 1, 1)
        assert end == TODAY

    def test_named_month_no_year(self):
        start, end = _resolve_relative_date("january", TODAY)
        assert start == date(2025, 1, 1)
        assert end == date(2025, 1, 31)

    def test_named_month_with_year(self):
        start, end = _resolve_relative_date("march 2024", TODAY)
        assert start == date(2024, 3, 1)
        assert end == date(2024, 3, 31)

    def test_abbreviated_month(self):
        start, end = _resolve_relative_date("feb", TODAY)
        assert start == date(2025, 2, 1)
        assert end == date(2025, 2, 28)

    def test_in_month_prefix(self):
        start, end = _resolve_relative_date("in january", TODAY)
        assert start == date(2025, 1, 1)
        assert end == date(2025, 1, 31)

    def test_plain_year(self):
        start, end = _resolve_relative_date("2024", TODAY)
        assert start == date(2024, 1, 1)
        assert end == date(2024, 12, 31)

    def test_in_year(self):
        start, end = _resolve_relative_date("in 2023", TODAY)
        assert start == date(2023, 1, 1)
        assert end == date(2023, 12, 31)

    def test_unknown_token_returns_none(self):
        result = _resolve_relative_date("whenever", TODAY)
        assert result is None

    def test_february_leap_year(self):
        leap_today = date(2024, 3, 1)
        start, end = _resolve_relative_date("february 2024", leap_today)
        assert start == date(2024, 2, 1)
        assert end == date(2024, 2, 29)


# ===========================================================================
# _parse_amount
# ===========================================================================


class TestParseAmount:
    def test_over(self):
        min_amt, max_amt, _ = _parse_amount("over $50")
        assert min_amt == 50.0
        assert max_amt is None

    def test_above(self):
        min_amt, max_amt, _ = _parse_amount("above $100")
        assert min_amt == 100.0

    def test_more_than(self):
        min_amt, max_amt, _ = _parse_amount("more than $200")
        assert min_amt == 200.0

    def test_greater_than(self):
        min_amt, max_amt, _ = _parse_amount("greater than $75.50")
        assert min_amt == 75.5

    def test_under(self):
        min_amt, max_amt, _ = _parse_amount("under $30")
        assert min_amt is None
        assert max_amt == 30.0

    def test_below(self):
        min_amt, max_amt, _ = _parse_amount("below $500")
        assert max_amt == 500.0

    def test_less_than(self):
        min_amt, max_amt, _ = _parse_amount("less than $1,000")
        assert max_amt == 1000.0

    def test_between(self):
        min_amt, max_amt, _ = _parse_amount("between $20 and $80")
        assert min_amt == 20.0
        assert max_amt == 80.0

    def test_between_without_dollar_signs(self):
        min_amt, max_amt, _ = _parse_amount("between 50 and 200")
        assert min_amt == 50.0
        assert max_amt == 200.0

    def test_exact_amount_creates_range(self):
        min_amt, max_amt, _ = _parse_amount("$100")
        assert min_amt == pytest.approx(90.0)
        assert max_amt == pytest.approx(110.0)

    def test_commas_in_amount(self):
        min_amt, max_amt, _ = _parse_amount("over $1,500")
        assert min_amt == 1500.0

    def test_no_amount_returns_none(self):
        min_amt, max_amt, remaining = _parse_amount("coffee last month")
        assert min_amt is None
        assert max_amt is None
        assert "coffee" in remaining

    def test_removes_amount_from_text(self):
        _, _, remaining = _parse_amount("starbucks over $5")
        assert "over" not in remaining
        assert "$5" not in remaining
        assert "starbucks" in remaining


# ===========================================================================
# _detect_income_flag
# ===========================================================================


class TestDetectIncomeFlag:
    def test_income_word(self):
        flag, _ = _detect_income_flag("income last month")
        assert flag is True

    def test_salary_word(self):
        flag, _ = _detect_income_flag("salary deposits")
        assert flag is True

    def test_paycheck(self):
        flag, _ = _detect_income_flag("paycheck")
        assert flag is True

    def test_deposit(self):
        flag, _ = _detect_income_flag("deposit this week")
        assert flag is True

    def test_expenses_word(self):
        flag, _ = _detect_income_flag("expenses last month")
        assert flag is False

    def test_spending_word(self):
        flag, _ = _detect_income_flag("spending this year")
        assert flag is False

    def test_charges_word(self):
        flag, _ = _detect_income_flag("charges over $50")
        assert flag is False

    def test_neutral_returns_none(self):
        flag, text = _detect_income_flag("coffee amazon")
        assert flag is None
        assert "coffee" in text

    def test_removes_income_word_from_text(self):
        _, remaining = _detect_income_flag("income in january")
        assert "income" not in remaining.lower()


# ===========================================================================
# _clean_keyword
# ===========================================================================


class TestCleanKeyword:
    def test_returns_meaningful_word(self):
        assert _clean_keyword("amazon") == "amazon"

    def test_strips_stopwords(self):
        result = _clean_keyword("show me all my transactions from amazon")
        assert result == "amazon"

    def test_multiple_keywords_preserved(self):
        result = _clean_keyword("whole foods market")
        assert result == "whole foods market"

    def test_only_stopwords_returns_none(self):
        result = _clean_keyword("show me all transactions")
        assert result is None

    def test_empty_string_returns_none(self):
        result = _clean_keyword("")
        assert result is None

    def test_extra_whitespace_handled(self):
        result = _clean_keyword("   starbucks   ")
        assert result == "starbucks"


# ===========================================================================
# parse_natural_query — integration-level cases
# ===========================================================================


class TestParseNaturalQuery:
    """Full pipeline tests covering realistic user queries."""

    def test_simple_merchant_keyword(self):
        result = parse_natural_query("coffee", today=TODAY)
        assert result.search == "coffee"
        assert result.start_date is None
        assert result.min_amount is None
        assert result.is_income is None

    def test_merchant_with_date(self):
        result = parse_natural_query("coffee last month", today=TODAY)
        assert result.search == "coffee"
        assert result.start_date == date(2025, 2, 1)
        assert result.end_date == date(2025, 2, 28)

    def test_merchant_with_amount(self):
        result = parse_natural_query("amazon over $50", today=TODAY)
        assert result.search == "amazon"
        assert result.min_amount == 50.0
        assert result.max_amount is None

    def test_merchant_with_date_and_amount(self):
        result = parse_natural_query("amazon over $50 in 2024", today=TODAY)
        assert result.search == "amazon"
        assert result.min_amount == 50.0
        assert result.start_date == date(2024, 1, 1)
        assert result.end_date == date(2024, 12, 31)

    def test_income_this_year(self):
        result = parse_natural_query("income this year", today=TODAY)
        assert result.is_income is True
        assert result.start_date == date(2025, 1, 1)
        assert result.end_date == date(2025, 12, 31)
        assert result.search is None

    def test_expenses_last_month(self):
        result = parse_natural_query("expenses last month", today=TODAY)
        assert result.is_income is False
        assert result.start_date == date(2025, 2, 1)
        assert result.end_date == date(2025, 2, 28)

    def test_rent_over_amount(self):
        # Use explicit $ sign so the amount regex fires before the year regex
        result = parse_natural_query("rent over $1,500", today=TODAY)
        assert result.search is not None
        assert "rent" in result.search
        assert result.min_amount == 1500.0

    def test_between_amount_range(self):
        result = parse_natural_query("dining between $20 and $100 last month", today=TODAY)
        assert result.search == "dining"
        assert result.min_amount == 20.0
        assert result.max_amount == 100.0
        assert result.start_date == date(2025, 2, 1)

    def test_named_month(self):
        result = parse_natural_query("starbucks in january", today=TODAY)
        assert result.search == "starbucks"
        assert result.start_date == date(2025, 1, 1)
        assert result.end_date == date(2025, 1, 31)

    def test_named_month_with_year(self):
        result = parse_natural_query("netflix january 2024", today=TODAY)
        assert result.search == "netflix"
        assert result.start_date == date(2024, 1, 1)

    def test_ytd(self):
        result = parse_natural_query("spending ytd", today=TODAY)
        assert result.is_income is False
        assert result.start_date == date(2025, 1, 1)
        assert result.end_date == TODAY

    def test_stopword_only_query_no_keyword(self):
        result = parse_natural_query("show me all my transactions", today=TODAY)
        assert result.search is None
        assert result.start_date is None

    def test_raw_query_preserved(self):
        q = "coffee last month over $5"
        result = parse_natural_query(q, today=TODAY)
        assert result.raw_query == q

    def test_empty_query(self):
        result = parse_natural_query("", today=TODAY)
        assert result.search is None
        assert result.start_date is None
        assert result.is_income is None

    def test_whitespace_only_query(self):
        result = parse_natural_query("   ", today=TODAY)
        assert result.search is None

    def test_this_week_date_range(self):
        result = parse_natural_query("groceries this week", today=TODAY)
        assert result.search == "groceries"
        assert result.start_date == date(2025, 3, 10)
        assert result.end_date == TODAY

    def test_last_30_days(self):
        result = parse_natural_query("subscriptions last 30 days", today=TODAY)
        assert result.search == "subscriptions"
        assert result.start_date == date(2025, 2, 13)

    def test_under_amount(self):
        result = parse_natural_query("coffee under $10", today=TODAY)
        assert result.search == "coffee"
        assert result.max_amount == 10.0
        assert result.min_amount is None

    def test_exact_amount_with_keyword(self):
        result = parse_natural_query("spotify $10", today=TODAY)
        assert result.search == "spotify"
        assert result.min_amount == pytest.approx(9.0)
        assert result.max_amount == pytest.approx(11.0)

    def test_salary_deposits_this_month(self):
        result = parse_natural_query("salary deposits this month", today=TODAY)
        assert result.is_income is True
        assert result.start_date == date(2025, 3, 1)

    def test_case_insensitive(self):
        result = parse_natural_query("AMAZON LAST MONTH OVER $50", today=TODAY)
        assert result.search == "AMAZON"
        assert result.min_amount == 50.0
        assert result.start_date == date(2025, 2, 1)
