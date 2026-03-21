"""Tests for app.api.v1.bulk_operations API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.bulk_operations import list_bulk_operations, undo_bulk_operation
from app.models.user import User


def _make_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _make_operation(user, **overrides):
    op = MagicMock()
    op.id = overrides.get("id", uuid4())
    op.organization_id = overrides.get("organization_id", user.organization_id)
    op.user_id = overrides.get("user_id", user.id)
    op.operation_type = overrides.get("operation_type", "bulk_categorize")
    op.affected_ids = overrides.get("affected_ids", ["id1", "id2"])
    op.previous_state = overrides.get("previous_state", {"field": "old"})
    op.new_state = overrides.get("new_state", {"field": "new"})
    op.is_undone = overrides.get("is_undone", False)
    op.created_at = overrides.get(
        "created_at", datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    )
    op.undone_at = overrides.get("undone_at", None)
    return op


@pytest.mark.unit
class TestListBulkOperations:
    """Test list_bulk_operations endpoint."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_operations(self):
        db = AsyncMock()
        user = _make_user()

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        result = await list_bulk_operations(limit=20, current_user=user, db=db)

        assert result == []
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_operations_correctly(self):
        db = AsyncMock()
        user = _make_user()

        op1 = _make_operation(user, operation_type="bulk_categorize")
        op2 = _make_operation(user, operation_type="bulk_delete")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [op1, op2]
        result_mock.scalars.return_value = scalars_mock
        db.execute.return_value = result_mock

        result = await list_bulk_operations(limit=20, current_user=user, db=db)

        assert len(result) == 2
        assert result[0].id == op1.id
        assert result[0].operation_type == "bulk_categorize"
        assert result[0].is_undone is False
        assert result[0].created_at == op1.created_at.isoformat()
        assert result[0].undone_at is None
        assert result[1].id == op2.id
        assert result[1].operation_type == "bulk_delete"


@pytest.mark.unit
class TestUndoBulkOperation:
    """Test undo_bulk_operation endpoint."""

    @pytest.mark.asyncio
    async def test_successfully_undoes_operation(self):
        db = AsyncMock()
        user = _make_user()
        op = _make_operation(user, is_undone=False, affected_ids=["id1", "id2"])

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = op
        db.execute.return_value = result_mock

        operation_id = op.id
        result = await undo_bulk_operation(operation_id=operation_id, current_user=user, db=db)

        assert result.id == op.id
        assert result.operation_type == op.operation_type
        assert result.is_undone is True
        assert result.restored_count == 2
        assert result.undone_at is not None
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(op)

    @pytest.mark.asyncio
    async def test_returns_404_when_operation_not_found(self):
        db = AsyncMock()
        user = _make_user()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await undo_bulk_operation(operation_id=uuid4(), current_user=user, db=db)

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_returns_409_when_already_undone(self):
        db = AsyncMock()
        user = _make_user()
        op = _make_operation(
            user,
            is_undone=True,
            undone_at=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        )

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = op
        db.execute.return_value = result_mock

        with pytest.raises(HTTPException) as exc_info:
            await undo_bulk_operation(operation_id=op.id, current_user=user, db=db)

        assert exc_info.value.status_code == 409
        assert "already been undone" in exc_info.value.detail.lower()
