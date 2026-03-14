"""Unit tests for permission CRUD operations."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.crud.permission import PermissionGrantCRUD


@pytest.mark.unit
class TestPermissionGrantCRUD:
    """Test PermissionGrantCRUD operations."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_db):
        grant = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = grant
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.get_by_id(mock_db, uuid4())
        assert result == grant

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_db):
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.get_by_id(mock_db, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_find_active_with_resource_id(self, mock_db):
        grant = Mock()
        scalars_mock = Mock()
        scalars_mock.first.return_value = grant
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.find_active(
            mock_db, uuid4(), uuid4(), "accounts", resource_id=uuid4()
        )
        assert result == grant

    @pytest.mark.asyncio
    async def test_find_active_without_resource_id(self, mock_db):
        scalars_mock = Mock()
        scalars_mock.first.return_value = None
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.find_active(mock_db, uuid4(), uuid4(), "accounts")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_exact_with_resource_id(self, mock_db):
        grant = Mock()
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = grant
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.find_exact(
            mock_db, uuid4(), uuid4(), "accounts", resource_id=uuid4()
        )
        assert result == grant

    @pytest.mark.asyncio
    async def test_find_exact_with_none_resource_id(self, mock_db):
        """Wildcard grant: resource_id is None."""
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.find_exact(
            mock_db, uuid4(), uuid4(), "accounts", resource_id=None
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_list_grants_for_grantee(self, mock_db):
        grants = [Mock(), Mock()]
        scalars_mock = Mock()
        scalars_mock.all.return_value = grants
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.list_grants_for_grantee(mock_db, uuid4(), "accounts")
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_given(self, mock_db):
        grants = [Mock()]
        scalars_mock = Mock()
        scalars_mock.all.return_value = grants
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.list_given(mock_db, uuid4(), uuid4())
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_received(self, mock_db):
        grants = [Mock(), Mock(), Mock()]
        scalars_mock = Mock()
        scalars_mock.all.return_value = grants
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.list_received(mock_db, uuid4(), uuid4())
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_audit(self, mock_db):
        audits = [Mock()]
        scalars_mock = Mock()
        scalars_mock.all.return_value = audits
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.list_audit(mock_db, uuid4(), limit=10, offset=5)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_list_audit_default_params(self, mock_db):
        scalars_mock = Mock()
        scalars_mock.all.return_value = []
        result_mock = Mock()
        result_mock.scalars.return_value = scalars_mock
        mock_db.execute.return_value = result_mock

        result = await PermissionGrantCRUD.list_audit(mock_db, uuid4())
        assert result == []
