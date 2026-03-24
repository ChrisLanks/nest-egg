"""Tests for CSV formula injection prevention utility."""

import pytest

from app.utils.csv_sanitize import sanitize_csv_field, sanitize_csv_row


class TestSanitizeCsvField:
    """sanitize_csv_field escapes formula-trigger prefixes."""

    @pytest.mark.parametrize(
        "value",
        [
            "=SUM(A1:A10)",
            "=cmd|'/c calc.exe'!A0",
            "+1234567890",
            "-1+2",
            "@SUM(1+1)",
            "\t=malicious",
            "\r=malicious",
        ],
    )
    def test_escapes_formula_prefixes(self, value):
        result = sanitize_csv_field(value)
        assert result.startswith("'"), f"Expected leading quote for: {value!r}"
        assert result[1:] == value

    @pytest.mark.parametrize(
        "value",
        [
            "Normal merchant name",
            "Starbucks",
            "Amazon.com",
            "1234",
            "100.50",
            "",
            " leading space is fine",
        ],
    )
    def test_leaves_safe_values_unchanged(self, value):
        assert sanitize_csv_field(value) == value

    def test_non_string_passthrough(self):
        assert sanitize_csv_field(42) == 42
        assert sanitize_csv_field(3.14) == 3.14
        assert sanitize_csv_field(None) is None
        assert sanitize_csv_field(True) is True

    def test_empty_string_unchanged(self):
        assert sanitize_csv_field("") == ""

    def test_single_char_formula_prefix(self):
        assert sanitize_csv_field("=") == "'="
        assert sanitize_csv_field("+") == "'+"
        assert sanitize_csv_field("-") == "'-"
        assert sanitize_csv_field("@") == "'@"


class TestSanitizeCsvRow:
    """sanitize_csv_row applies field sanitization across a whole row."""

    def test_sanitizes_string_fields_in_row(self):
        row = ["Normal", "=FORMULA", "safe", "+inject"]
        result = sanitize_csv_row(row)
        assert result == ["Normal", "'=FORMULA", "safe", "'+inject"]

    def test_preserves_numeric_fields(self):
        row = ["Merchant", 99.99, None, True]
        result = sanitize_csv_row(row)
        assert result == ["Merchant", 99.99, None, True]

    def test_mixed_row(self):
        row = ["=evil", 100.0, "normal description", "@inject", ""]
        result = sanitize_csv_row(row)
        assert result[0] == "'=evil"
        assert result[1] == 100.0
        assert result[2] == "normal description"
        assert result[3] == "'@inject"
        assert result[4] == ""

    def test_empty_row(self):
        assert sanitize_csv_row([]) == []

    def test_returns_new_list(self):
        """sanitize_csv_row must not mutate the input list."""
        original = ["=formula", "safe"]
        result = sanitize_csv_row(original)
        assert original[0] == "=formula"  # unchanged
        assert result[0] == "'=formula"
