"""CSV formula injection prevention.

Spreadsheet applications (Excel, LibreOffice, Google Sheets) treat cell values
that begin with =, +, -, @, TAB, or CR as formulas when the file is opened.
An attacker who can store such values in merchant names, descriptions, or
account names could execute arbitrary formulas on the recipient's machine.

Reference: OWASP CSV Injection
https://owasp.org/www-community/attacks/CSV_Injection
"""

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_field(value: object) -> object:
    """Escape a value to prevent CSV formula injection.

    Non-string values are returned unchanged.  String values that start with a
    formula-trigger character are prefixed with a single-quote ('), which
    causes spreadsheet apps to treat the cell as plain text.
    """
    if not isinstance(value, str):
        return value
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def sanitize_csv_row(row: list) -> list:
    """Return a new list with every string field sanitized."""
    return [sanitize_csv_field(v) for v in row]
