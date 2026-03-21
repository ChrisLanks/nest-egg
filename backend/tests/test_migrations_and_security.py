"""Source-level verification tests for migrations and security fixes.

No DB connection required -- these tests read source files and check content.
"""

import pathlib

BACKEND_DIR = pathlib.Path(__file__).parent.parent
VERSIONS_DIR = BACKEND_DIR / "alembic" / "versions"
ATTACHMENT_SERVICE = BACKEND_DIR / "app" / "services" / "attachment_service.py"


def test_trgm_migration_has_correct_down_revision():
    """The trgm migration must have a non-None, non-placeholder down_revision."""
    migration = VERSIONS_DIR / "b2c3d4e5f6a7_add_trgm_indexes_for_transaction_search.py"
    assert migration.exists(), f"Migration file not found: {migration}"
    text = migration.read_text()

    import re
    # Match both single and double quoted down_revision values
    match = (
        re.search(r'down_revision\s*=\s*"(.*?)"', text)
        or re.search(r"down_revision\s*=\s*'(.*?)'", text)
    )
    assert match is not None, "down_revision not found or is None in migration"
    value = match.group(1)
    assert value, "down_revision is empty"
    assert value != "<latest_revision_id>", "down_revision is still placeholder"
    assert value != "None", "down_revision is string None"


def test_missing_columns_migration_exists():
    """The a1b2c3d4e5f6 migration must exist and mention at least 5 columns."""
    migration = VERSIONS_DIR / "a1b2c3d4e5f6_create_account_contributions_table.py"
    assert migration.exists(), f"Migration file not found: {migration}"
    text = migration.read_text()

    import re
    columns = re.findall(r"sa\.Column\(", text)
    assert len(columns) >= 5, (
        f"Expected at least 5 sa.Column entries, found {len(columns)}"
    )


def test_attachment_service_has_magic_byte_check():
    """attachment_service.py must contain magic-byte validation code."""
    assert ATTACHMENT_SERVICE.exists(), f"File not found: {ATTACHMENT_SERVICE}"
    text = ATTACHMENT_SERVICE.read_text()

    has_file_header = "file_header" in text
    has_filetype = "filetype" in text
    has_magic = "MAGIC_BYTES" in text or "magic" in text.lower()

    assert has_file_header or has_filetype, (
        "Expected magic-byte validation using file_header reads or filetype library"
    )
    assert has_magic or has_filetype, (
        "Expected MAGIC_BYTES dict or filetype library usage"
    )


def test_attachment_content_type_from_detected_not_header():
    """content_type must be set from detected type, not the client-supplied header."""
    assert ATTACHMENT_SERVICE.exists(), f"File not found: {ATTACHMENT_SERVICE}"
    text = ATTACHMENT_SERVICE.read_text()

    assert "content_type = detected_type" in text, (
        "Expected `content_type = detected_type` assignment -- "
        "stored content_type should come from magic-byte detection, not client header"
    )
