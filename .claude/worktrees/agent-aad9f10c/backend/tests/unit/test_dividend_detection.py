"""Tests for the dividend detection service.

Tests the keyword matching / pattern recognition logic that auto-detects
dividend and investment income transactions from synced provider data.
"""

import re
import uuid
from types import SimpleNamespace

import pytest

from app.services.dividend_detection_service import (
    _CATEGORY_KEYWORDS,
    _PRIMARY_PATTERNS,
    DIVIDEND_LABEL_NAME,
    detect_dividend,
)

# ── Helper to build a fake Transaction-like object ────────────────────────


def _txn(
    description: str = "",
    merchant_name: str = "",
    category_primary: str | None = None,
    category_detailed: str | None = None,
) -> SimpleNamespace:
    """Build a minimal object with the fields detect_dividend reads."""
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        description=description,
        merchant_name=merchant_name,
        category_primary=category_primary,
        category_detailed=category_detailed,
    )


# ── detect_dividend() pure function tests ─────────────────────────────────


class TestDetectDividend:
    """Test the core keyword-matching logic."""

    # ── Positive matches ──────────────────────────────────────────────

    def test_plain_dividend_keyword(self):
        txn = _txn(description="DIVIDEND RECEIVED")
        assert detect_dividend(txn) == "dividend"

    def test_div_payment(self):
        txn = _txn(description="DIV PAYMENT - AAPL")
        assert detect_dividend(txn) == "dividend"

    def test_cash_div(self):
        txn = _txn(description="CASH DIV ON 100 SHS")
        assert detect_dividend(txn) == "dividend"

    def test_ordinary_dividend(self):
        txn = _txn(description="ORDINARY DIVIDEND")
        assert detect_dividend(txn) == "dividend"

    def test_ord_div_abbrev(self):
        txn = _txn(description="ORD DIV PAYMENT")
        assert detect_dividend(txn) == "dividend"

    def test_ord_div_reinv_detects_reinvestment(self):
        """'ORD DIV REINV' matches reinvested_dividend (more specific)."""
        txn = _txn(description="ORD DIV REINV")
        assert detect_dividend(txn) == "reinvested_dividend"

    def test_nonqualified_dividend(self):
        txn = _txn(description="NON-QUAL DIV ON 50 SHS")
        assert detect_dividend(txn) == "dividend"

    def test_nonqual_no_hyphen(self):
        txn = _txn(description="NONQUAL DIV PAYMENT")
        assert detect_dividend(txn) == "dividend"

    def test_qualified_dividend(self):
        txn = _txn(description="QUAL DIV 0.82/SH")
        assert detect_dividend(txn) == "qualified_dividend"

    def test_qualified_dividend_full(self):
        txn = _txn(description="QUALIFIED DIVIDEND PAYMENT")
        assert detect_dividend(txn) == "qualified_dividend"

    def test_reinvest_div(self):
        txn = _txn(description="REINVEST DIV @ $150.23")
        assert detect_dividend(txn) == "reinvested_dividend"

    def test_div_reinvest(self):
        txn = _txn(description="DIV REINVESTMENT")
        assert detect_dividend(txn) == "reinvested_dividend"

    def test_drip(self):
        txn = _txn(description="DRIP PURCHASE 0.5 SHS VTI")
        assert detect_dividend(txn) == "reinvested_dividend"

    def test_cap_gain_dist(self):
        txn = _txn(description="CAP GAIN DIST LT")
        assert detect_dividend(txn) == "capital_gain_distribution"

    def test_capital_gain_distribution(self):
        txn = _txn(description="CAPITAL GAIN DISTRIBUTION")
        assert detect_dividend(txn) == "capital_gain_distribution"

    def test_lt_cap_gain(self):
        txn = _txn(description="LT CAP GAIN ON 200 SHS")
        assert detect_dividend(txn) == "capital_gain_distribution"

    def test_st_cap_gain(self):
        txn = _txn(description="ST CAP GAIN DISTRIBUTION")
        assert detect_dividend(txn) == "capital_gain_distribution"

    def test_return_of_capital(self):
        txn = _txn(description="RETURN OF CAPITAL")
        assert detect_dividend(txn) == "return_of_capital"

    def test_bond_interest(self):
        txn = _txn(description="BOND INTEREST PAYMENT")
        assert detect_dividend(txn) == "interest"

    def test_bond_int_abbrev(self):
        txn = _txn(description="BOND INT ACCRUED")
        assert detect_dividend(txn) == "interest"

    def test_interest_payment(self):
        txn = _txn(description="INTEREST PAYMENT")
        assert detect_dividend(txn) == "interest"

    def test_int_income(self):
        txn = _txn(description="INT INCOME FROM MM FUND")
        assert detect_dividend(txn) == "interest"

    def test_money_market_interest(self):
        txn = _txn(description="MONEY MARKET INTEREST")
        assert detect_dividend(txn) == "interest"

    def test_money_market_income(self):
        txn = _txn(description="MONEY MARKET INCOME")
        assert detect_dividend(txn) == "interest"

    def test_foreign_tax_withholding(self):
        txn = _txn(description="FOREIGN TAX W/H ON DIV")
        assert detect_dividend(txn) == "dividend"

    # ── Case insensitivity ────────────────────────────────────────────

    def test_lowercase_dividend(self):
        txn = _txn(description="dividend payment aapl")
        assert detect_dividend(txn) == "dividend"

    def test_mixed_case(self):
        txn = _txn(description="Qualified Dividend Payment")
        assert detect_dividend(txn) == "qualified_dividend"

    # ── Merchant name fallback ────────────────────────────────────────

    def test_matches_merchant_name(self):
        txn = _txn(merchant_name="DIVIDEND REINVESTMENT")
        assert detect_dividend(txn) == "dividend"

    def test_matches_across_fields(self):
        """Pattern can match across combined description + merchant."""
        txn = _txn(description="PAYMENT", merchant_name="BOND INT RECEIVED")
        assert detect_dividend(txn) == "interest"

    # ── Category keyword fallback ─────────────────────────────────────

    def test_category_primary_dividend(self):
        txn = _txn(category_primary="dividend")
        assert detect_dividend(txn) == "dividend"

    def test_category_primary_interest(self):
        txn = _txn(category_primary="Interest")
        assert detect_dividend(txn) == "dividend"

    def test_category_detailed_investment_income(self):
        txn = _txn(category_detailed="investment income")
        assert detect_dividend(txn) == "dividend"

    def test_category_with_underscore(self):
        txn = _txn(category_primary="investment_income")
        assert detect_dividend(txn) == "dividend"

    # ── Negative matches (should NOT detect as dividend) ──────────────

    def test_regular_purchase(self):
        txn = _txn(description="WHOLE FOODS MARKET", merchant_name="Whole Foods")
        assert detect_dividend(txn) is None

    def test_amazon_purchase(self):
        txn = _txn(description="AMAZON.COM PURCHASE")
        assert detect_dividend(txn) is None

    def test_rent_payment(self):
        txn = _txn(description="RENT PAYMENT", category_primary="Bills")
        assert detect_dividend(txn) is None

    def test_payroll(self):
        txn = _txn(description="PAYROLL DIRECT DEPOSIT")
        assert detect_dividend(txn) is None

    def test_transfer(self):
        txn = _txn(description="TRANSFER TO SAVINGS")
        assert detect_dividend(txn) is None

    def test_atm_withdrawal(self):
        txn = _txn(description="ATM WITHDRAWAL")
        assert detect_dividend(txn) is None

    def test_empty_fields(self):
        txn = _txn()
        assert detect_dividend(txn) is None

    def test_none_fields(self):
        txn = SimpleNamespace(
            id=uuid.uuid4(),
            organization_id=uuid.uuid4(),
            description=None,
            merchant_name=None,
            category_primary=None,
            category_detailed=None,
        )
        assert detect_dividend(txn) is None

    def test_word_boundary_no_false_positive(self):
        """'individual' contains 'div' but should NOT match."""
        txn = _txn(description="INDIVIDUAL RETIREMENT ACCOUNT CONTRIBUTION")
        assert detect_dividend(txn) is None

    def test_subdivision_no_match(self):
        """'subdivision' should NOT trigger dividend detection."""
        txn = _txn(description="SUBDIVISION ASSESSMENT FEE")
        assert detect_dividend(txn) is None

    def test_interest_in_context(self):
        """'interest' by itself should NOT match — needs 'interest payment'."""
        txn = _txn(description="THANKS FOR YOUR INTEREST IN OUR PRODUCT")
        assert detect_dividend(txn) is None

    def test_category_groceries(self):
        txn = _txn(category_primary="Groceries", category_detailed="Supermarkets")
        assert detect_dividend(txn) is None


# ── Subtype hint accuracy ─────────────────────────────────────────────────


class TestSubtypeHints:
    """Verify that the correct subtype hint is returned for each pattern."""

    @pytest.mark.parametrize(
        "desc, expected_subtype",
        [
            ("DIVIDEND PAYMENT", "dividend"),
            ("QUAL DIV 0.50/SH", "qualified_dividend"),
            ("REINVEST DIV @ 150.00", "reinvested_dividend"),
            ("DRIP PURCHASE", "reinvested_dividend"),
            ("CAPITAL GAIN DISTRIBUTION", "capital_gain_distribution"),
            ("LT CAP GAIN", "capital_gain_distribution"),
            ("RETURN OF CAPITAL", "return_of_capital"),
            ("BOND INTEREST PAYMENT", "interest"),
            ("INT INCOME", "interest"),
            ("MONEY MARKET INTEREST", "interest"),
        ],
    )
    def test_subtype_mapping(self, desc: str, expected_subtype: str):
        txn = _txn(description=desc)
        assert detect_dividend(txn) == expected_subtype


# ── Real-world brokerage descriptions ─────────────────────────────────────


class TestRealWorldDescriptions:
    """Test against actual brokerage transaction descriptions."""

    @pytest.mark.parametrize(
        "desc",
        [
            "DIVIDEND RECEIVED CASH DIV ON 150 SHS REC 01/15/25 PAY 02/01/25",
            "QUAL DIV REINV",
            "REINVEST DIVIDEND 0.350 SHS @ $97.14",
            "QUALIFIED DIVIDEND TAX EXEMPT",
            "CAP GAIN DIST LT 12/15/2024",
            "BOND INT 4.25% DUE 06/01/2025",
            "MONEY MARKET INT 5.10% APY",
            "CASH DIV ON 25 SHS OF AAPL INC",
            "LT CAP GAIN ON 200 SHS VTSAX",
            "INT INCOME FEDERAL MM FUND",
            "DIV REINV VANGUARD 500 INDEX",
            "ORDINARY DIVIDEND ~AAPL",
            "RETURN OF CAPITAL DISTRIBUTION",
            "FOREIGN TAX W/H ON QUAL DIV",
        ],
    )
    def test_real_brokerage_descriptions_detected(self, desc: str):
        txn = _txn(description=desc)
        result = detect_dividend(txn)
        assert result is not None, f"Failed to detect: {desc}"


# ── Pattern edge cases ────────────────────────────────────────────────────


class TestPatternEdgeCases:
    """Edge cases and boundary conditions for pattern matching."""

    def test_dividend_in_middle_of_text(self):
        txn = _txn(description="FIDELITY CASH DIVIDEND RECEIVED ON 01/15")
        assert detect_dividend(txn) == "dividend"

    def test_multiple_patterns_returns_first_match(self):
        """If description matches multiple patterns, first wins."""
        txn = _txn(description="QUAL DIV REINV 0.5 SHS")
        # "QUAL DIV" matches qualified_dividend before "REINV" could match
        assert detect_dividend(txn) == "qualified_dividend"

    def test_description_priority_over_category(self):
        """Description match takes priority over category match."""
        txn = _txn(description="BOND INTEREST PAYMENT", category_primary="Transfer")
        assert detect_dividend(txn) == "interest"

    def test_very_long_description(self):
        """Long descriptions should still be searched."""
        desc = "X" * 500 + " DIVIDEND PAYMENT " + "Y" * 500
        txn = _txn(description=desc)
        assert detect_dividend(txn) == "dividend"

    def test_special_characters_in_description(self):
        txn = _txn(description="DIV PAYMENT - $0.82/SH (AAPL) REC:01/15")
        assert detect_dividend(txn) == "dividend"


# ── Seed rule regex tests ─────────────────────────────────────────────────


class TestSeedRuleRegex:
    """Verify the regexes used in the seed dividend detection rule
    match the same transactions as the service's pattern list."""

    @pytest.fixture()
    def seed_regexes(self):
        from app.api.v1.rules import _DIVIDEND_REGEX_1, _DIVIDEND_REGEX_2

        return [
            re.compile(_DIVIDEND_REGEX_1, re.IGNORECASE),
            re.compile(_DIVIDEND_REGEX_2, re.IGNORECASE),
        ]

    def _any_match(self, regexes, text):
        return any(r.search(text) for r in regexes)

    @pytest.mark.parametrize(
        "text",
        [
            "DIVIDEND RECEIVED",
            "DIV PAYMENT - AAPL",
            "QUAL DIV 0.82/SH",
            "CASH DIV ON 100 SHS",
            "REINVEST DIV @ $150.23",
            "DIV REINVESTMENT",
            "DRIP PURCHASE 0.5 SHS VTI",
            "CAP GAIN DIST LT",
            "CAPITAL GAIN DISTRIBUTION",
            "LT CAP GAIN ON 200 SHS",
            "ST CAP GAIN DISTRIBUTION",
            "RETURN OF CAPITAL",
            "BOND INTEREST PAYMENT",
            "BOND INT ACCRUED",
            "INTEREST PAYMENT",
            "INT INCOME FROM MM FUND",
            "MONEY MARKET INTEREST",
            "MONEY MARKET INCOME",
            "ORDINARY DIVIDEND",
            "ORD DIV PAYMENT",
            "NON-QUAL DIV ON 50 SHS",
            "NONQUAL DIV PAYMENT",
        ],
    )
    def test_seed_regex_matches_known_dividends(self, seed_regexes, text):
        assert self._any_match(seed_regexes, text), f"Seed regex missed: {text}"

    @pytest.mark.parametrize(
        "text",
        [
            "WHOLE FOODS MARKET",
            "AMAZON.COM PURCHASE",
            "RENT PAYMENT",
            "PAYROLL DIRECT DEPOSIT",
            "TRANSFER TO SAVINGS",
            "ATM WITHDRAWAL",
            "INDIVIDUAL RETIREMENT ACCOUNT CONTRIBUTION",
            "SUBDIVISION ASSESSMENT FEE",
        ],
    )
    def test_seed_regex_does_not_match_non_dividends(self, seed_regexes, text):
        assert not self._any_match(seed_regexes, text), f"Seed regex false positive: {text}"

    def test_seed_regex_is_case_insensitive(self, seed_regexes):
        assert self._any_match(seed_regexes, "dividend payment aapl")
        assert self._any_match(seed_regexes, "Qualified Dividend Payment")


# ── Constants and configuration tests ─────────────────────────────────────


class TestServiceConfiguration:
    """Validate the detection service's configuration."""

    def test_label_name_is_set(self):
        assert DIVIDEND_LABEL_NAME == "Dividend Income"

    def test_primary_patterns_not_empty(self):
        assert len(_PRIMARY_PATTERNS) > 0

    def test_all_patterns_are_compiled_regex(self):
        for pattern, subtype in _PRIMARY_PATTERNS:
            assert isinstance(pattern, re.Pattern)
            assert isinstance(subtype, str)

    def test_all_subtypes_are_valid(self):
        valid_subtypes = {
            "dividend",
            "qualified_dividend",
            "reinvested_dividend",
            "capital_gain_distribution",
            "return_of_capital",
            "interest",
        }
        for _, subtype in _PRIMARY_PATTERNS:
            assert subtype in valid_subtypes, f"Invalid subtype: {subtype}"

    def test_category_keywords_not_empty(self):
        assert len(_CATEGORY_KEYWORDS) > 0

    def test_category_keywords_are_lowercase(self):
        for kw in _CATEGORY_KEYWORDS:
            assert kw == kw.lower(), f"Category keyword not lowercase: {kw}"

    def test_seed_rule_name_constant(self):
        from app.api.v1.rules import _DIVIDEND_RULE_NAME

        assert _DIVIDEND_RULE_NAME == "Dividend Income Detection"

    def test_seed_regex_compiles(self):
        """Verify the seed regex strings are valid."""
        from app.api.v1.rules import _DIVIDEND_REGEX_1, _DIVIDEND_REGEX_2

        for regex_str in [_DIVIDEND_REGEX_1, _DIVIDEND_REGEX_2]:
            compiled = re.compile(regex_str, re.IGNORECASE)
            assert compiled is not None

    def test_seed_regex_length_within_rule_engine_limit(self):
        """Rule engine caps regex at 200 chars."""
        from app.api.v1.rules import _DIVIDEND_REGEX_1, _DIVIDEND_REGEX_2

        for regex_str in [_DIVIDEND_REGEX_1, _DIVIDEND_REGEX_2]:
            assert len(regex_str) <= 200, (
                f"Seed regex too long ({len(regex_str)} chars), " "rule engine limit is 200"
            )
