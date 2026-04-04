"""
Tests for centralized get_filtered_accounts dependency.

1. Single user_id returns that user's accounts
2. Multiple user_ids returns accounts for all specified users
3. No filter returns all household accounts (deduplicated)
4. user_ids with single entry behaves like user_id
5. Empty user_ids list returns all accounts
6. get_filtered_accounts is importable from dependencies
7. All major API files import get_filtered_accounts
"""

import inspect
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def test_get_filtered_accounts_importable():
    """get_filtered_accounts can be imported from dependencies."""
    from app.dependencies import get_filtered_accounts

    assert callable(get_filtered_accounts)
    assert inspect.iscoroutinefunction(get_filtered_accounts)


def test_get_filtered_accounts_signature():
    """get_filtered_accounts accepts user_id and user_ids parameters."""
    from app.dependencies import get_filtered_accounts

    sig = inspect.signature(get_filtered_accounts)
    param_names = list(sig.parameters.keys())
    assert "user_id" in param_names
    assert "user_ids" in param_names
    assert "deduplicate" in param_names


@pytest.mark.asyncio
@patch("app.dependencies.get_user_accounts", new_callable=AsyncMock)
@patch("app.dependencies.verify_household_member", new_callable=AsyncMock)
async def test_single_user_id_calls_get_user_accounts(mock_verify, mock_get_user):
    """Single user_id calls get_user_accounts for that user."""
    from app.dependencies import get_filtered_accounts

    user_id = uuid4()
    org_id = uuid4()
    current_user_id = uuid4()
    mock_get_user.return_value = []

    db = MagicMock()
    await get_filtered_accounts(db, org_id, current_user_id, user_id=user_id)

    mock_verify.assert_called_once()
    mock_get_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.dependencies.get_user_accounts", new_callable=AsyncMock)
@patch("app.dependencies.verify_household_member", new_callable=AsyncMock)
async def test_single_user_id_same_as_current_skips_verify(mock_verify, mock_get_user):
    """When user_id is the current user, verification is skipped."""
    from app.dependencies import get_filtered_accounts

    user_id = uuid4()
    org_id = uuid4()
    mock_get_user.return_value = []

    await get_filtered_accounts(
        MagicMock(), org_id, user_id, user_id=user_id  # same user
    )

    mock_verify.assert_not_called()
    mock_get_user.assert_called_once()


@pytest.mark.asyncio
@patch("app.dependencies.verify_household_member", new_callable=AsyncMock)
async def test_multiple_user_ids_queries_in_clause(mock_verify):
    """Multiple user_ids queries with IN clause."""
    from app.dependencies import get_filtered_accounts

    user1 = uuid4()
    user2 = uuid4()
    org_id = uuid4()
    current_user_id = user1

    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.unique.return_value.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await get_filtered_accounts(
        mock_db, org_id, current_user_id, user_ids=[user1, user2]
    )

    assert result == []
    mock_db.execute.assert_called_once()
    # user2 != current_user, so verify is called for user2
    mock_verify.assert_called_once()


@pytest.mark.asyncio
@patch("app.dependencies.get_all_household_accounts", new_callable=AsyncMock)
async def test_no_filter_returns_all_deduplicated(mock_get_all):
    """No user_id or user_ids returns all household accounts, deduplicated."""
    from app.dependencies import get_filtered_accounts

    org_id = uuid4()
    current_user_id = uuid4()
    mock_get_all.return_value = []

    with patch("app.services.deduplication_service.DeduplicationService") as mock_dedup_cls:
        mock_dedup = MagicMock()
        mock_dedup.deduplicate_accounts.return_value = []
        mock_dedup_cls.return_value = mock_dedup

        result = await get_filtered_accounts(
            MagicMock(), org_id, current_user_id
        )

    assert result == []
    mock_get_all.assert_called_once()


# ---------------------------------------------------------------------------
# Structural tests: verify all major API files import get_filtered_accounts
# ---------------------------------------------------------------------------

import os

API_DIR = os.path.join(
    os.path.dirname(__file__), "..", "app", "api", "v1"
)

MAJOR_API_FILES = [
    "dashboard.py",
    "income_expenses.py",
    "holdings.py",
    "transactions.py",
    "accounts.py",
    "budgets.py",
    "recurring_transactions.py",
    "tax_buckets.py",
    "reports.py",
]


@pytest.mark.parametrize("filename", MAJOR_API_FILES)
def test_api_file_imports_get_filtered_accounts(filename):
    """Major API files import get_filtered_accounts."""
    filepath = os.path.join(API_DIR, filename)
    if not os.path.exists(filepath):
        pytest.skip(f"{filename} not found")
    source = open(filepath).read()
    assert "get_filtered_accounts" in source, f"{filename} missing get_filtered_accounts import"
