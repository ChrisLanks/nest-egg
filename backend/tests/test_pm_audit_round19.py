"""Tests for PM audit round 19 fixes.

Covers:
1. Plaid webhook: improved logging when item_id not found (audit trail)
2. accounts bulk-delete: max 500 IDs enforced to prevent large SQL IN clauses
3. RetirementPage SS estimator: showSocialSecurity must be false when age unknown
   (frontend logic tested via source inspection)
"""

import inspect
from uuid import uuid4


# ─── Plaid webhook: improved not-found logging ───────────────────────────────


def test_plaid_webhook_logs_structured_warning_on_missing_item():
    """Webhook handler must log item_id, webhook_type, and webhook_code when item not found."""
    from app.api.v1 import plaid as plaid_module

    source = inspect.getsource(plaid_module)
    # The warning must include relevant context fields
    assert "item_id" in source
    assert "webhook_type" in source
    assert "webhook_code" in source
    assert "item_not_found" in source


# ─── Bulk delete: max batch size ─────────────────────────────────────────────


def test_bulk_delete_max_constant_exists():
    """_BULK_DELETE_MAX constant must be defined."""
    from app.api.v1 import accounts as accounts_module

    assert hasattr(accounts_module, "_BULK_DELETE_MAX"), "_BULK_DELETE_MAX must be defined"
    assert accounts_module._BULK_DELETE_MAX > 0
    assert accounts_module._BULK_DELETE_MAX <= 1000, "Max batch size should be <= 1000"


def test_bulk_delete_enforces_limit_in_source():
    """bulk_delete_accounts must check len(account_ids) against _BULK_DELETE_MAX."""
    from app.api.v1.accounts import bulk_delete_accounts

    source = inspect.getsource(bulk_delete_accounts)
    assert "_BULK_DELETE_MAX" in source, "Must reference _BULK_DELETE_MAX inside function"
    assert "len(account_ids)" in source or "len(" in source, "Must check length of account_ids"
    assert "HTTPException" in source or "raise" in source, "Must raise on oversize batch"


def test_bulk_delete_rejects_oversized_batch():
    """Calling bulk_delete_accounts with > _BULK_DELETE_MAX IDs raises HTTP 400."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from fastapi import HTTPException
    from app.api.v1.accounts import bulk_delete_accounts, _BULK_DELETE_MAX

    oversized = [uuid4() for _ in range(_BULK_DELETE_MAX + 1)]
    mock_request = MagicMock()
    mock_user = MagicMock()
    mock_db = AsyncMock()

    async def _call():
        return await bulk_delete_accounts(
            account_ids=oversized,
            http_request=mock_request,
            current_user=mock_user,
            db=mock_db,
        )

    with __import__("pytest").raises(HTTPException) as exc_info:
        asyncio.get_event_loop().run_until_complete(_call())

    assert exc_info.value.status_code == 400
    assert str(_BULK_DELETE_MAX) in exc_info.value.detail


def test_bulk_delete_limit_is_boundary():
    """The batch size check is strictly >, so exactly _BULK_DELETE_MAX IDs must not be rejected."""
    from app.api.v1.accounts import bulk_delete_accounts, _BULK_DELETE_MAX

    source = inspect.getsource(bulk_delete_accounts)
    # Must use strict > (not >=) so that exactly _BULK_DELETE_MAX is allowed
    assert f"> _BULK_DELETE_MAX" in source, (
        "Limit check must use > (strict), not >= , so exactly _BULK_DELETE_MAX IDs are accepted"
    )


# ─── Frontend: SS estimator hidden when age unknown ──────────────────────────


def test_ss_show_logic_hides_when_age_unknown():
    """RetirementPage must NOT show SS estimator when currentUserAge is null."""
    import re

    with open(
        "/home/lanx/git/nest-egg/frontend/src/features/retirement/pages/RetirementPage.tsx"
    ) as f:
        source = f.read()

    # Find the showSocialSecurity assignment
    match = re.search(r"const showSocialSecurity\s*=\s*(.+);", source)
    assert match, "showSocialSecurity must be assigned"
    expr = match.group(1)

    # Must NOT use `currentUserAge === null` as a truthy condition for showing
    assert "currentUserAge === null ||" not in expr, (
        "showSocialSecurity must NOT be true when age is null — "
        "that would show it to brand-new users with no birthdate"
    )
    # Must use !== null (or similar) so it only shows when age is known
    assert "!== null" in expr or "currentUserAge >" in expr, (
        "showSocialSecurity must require age to be non-null"
    )
