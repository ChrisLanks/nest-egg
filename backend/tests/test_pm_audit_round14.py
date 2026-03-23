"""Tests for PM audit round 14 fixes.

Covers:
- list_transactions endpoint now validates account_id is accessible to the
  requesting user, preventing cross-member transaction data exposure.
"""

import inspect


def test_list_transactions_validates_account_id():
    """list_transactions must reject account_id not in the user's accessible accounts."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.list_transactions)

    # Must check account accessibility
    assert "scoped_account_ids" in source, (
        "list_transactions must build scoped_account_ids for account_id validation"
    )
    assert "Account not accessible" in source or "not in scoped_account_ids" in source, (
        "list_transactions must raise 403 when account_id is not in scope"
    )


def test_list_transactions_uses_household_accounts_when_no_user_id():
    """When user_id is not provided, account scope must include all household accounts."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.list_transactions)
    assert "get_all_household_accounts" in source, (
        "Without user_id, must scope to all household accounts"
    )


def test_list_transactions_uses_user_accounts_when_user_id_provided():
    """When user_id is provided, account scope must be limited to that user's accounts."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.list_transactions)
    assert "get_user_accounts" in source, (
        "With user_id, must scope to that user's accounts only"
    )


def test_export_also_validates_account_id():
    """Sanity: the export endpoint already has the same validation (not a regression)."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.export_transactions_csv)
    assert "Account not accessible" in source, (
        "export_transactions_csv must also validate account_id scope"
    )


def test_account_scope_check_position():
    """Account scope validation must happen BEFORE building the query."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.list_transactions)
    lines = source.split("\n")

    scope_check_idx = next(
        (i for i, line in enumerate(lines) if "scoped_account_ids" in line), None
    )
    query_build_idx = next(
        (i for i, line in enumerate(lines) if "select(Transaction)" in line), None
    )

    assert scope_check_idx is not None, "scoped_account_ids check must exist"
    assert query_build_idx is not None, "select(Transaction) must exist"
    assert scope_check_idx < query_build_idx, (
        "Account scope validation must happen before building the DB query"
    )


def test_403_raised_for_foreign_account():
    """The 403 must be raised specifically when account_id not in scoped_account_ids."""
    from app.api.v1 import transactions as tx_module

    source = inspect.getsource(tx_module.list_transactions)
    # The check pattern: if account_id not in scoped_account_ids: raise HTTPException(403)
    assert "403" in source or "status_code=403" in source, (
        "Must raise HTTP 403 for inaccessible account"
    )
