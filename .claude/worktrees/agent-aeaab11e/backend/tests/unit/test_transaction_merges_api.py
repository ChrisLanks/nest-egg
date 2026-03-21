"""Tests for app.api.v1.transaction_merges API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.transaction_merges import (
    auto_detect_and_merge_duplicates,
    find_potential_duplicates,
    get_merge_history,
    merge_transactions,
)
from app.models.user import User


@pytest.mark.unit
class TestFindPotentialDuplicates:
    """Test find_potential_duplicates endpoint."""

    @pytest.mark.asyncio
    async def test_returns_duplicates_list(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        transaction_id = uuid4()
        mock_duplicates = [MagicMock(), MagicMock()]

        request = MagicMock()
        request.transaction_id = transaction_id
        request.date_window_days = 3
        request.amount_tolerance = Decimal("0.01")

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.find_potential_duplicates",
            new_callable=AsyncMock,
            return_value=mock_duplicates,
        ) as mock_find:
            result = await find_potential_duplicates(
                request=request,
                current_user=user,
                db=db,
            )

            mock_find.assert_called_once_with(
                db=db,
                transaction_id=transaction_id,
                user=user,
                date_window_days=3,
                amount_tolerance=Decimal("0.01"),
            )
            assert result["transaction_id"] == transaction_id
            assert result["potential_duplicates"] == mock_duplicates
            assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_duplicates(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        request = MagicMock()
        request.transaction_id = uuid4()
        request.date_window_days = 5
        request.amount_tolerance = Decimal("0.05")

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.find_potential_duplicates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await find_potential_duplicates(
                request=request,
                current_user=user,
                db=db,
            )

            assert result["potential_duplicates"] == []
            assert result["count"] == 0


@pytest.mark.unit
class TestMergeTransactions:
    """Test merge_transactions endpoint."""

    @pytest.mark.asyncio
    async def test_merge_success(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        primary_id = uuid4()
        dup_ids = [uuid4(), uuid4()]
        mock_merge_record = MagicMock()

        merge_request = MagicMock()
        merge_request.primary_transaction_id = primary_id
        merge_request.duplicate_transaction_ids = dup_ids
        merge_request.merge_reason = "Same transaction"

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.merge_transactions",
            new_callable=AsyncMock,
            return_value=mock_merge_record,
        ) as mock_merge:
            result = await merge_transactions(
                merge_request=merge_request,
                current_user=user,
                db=db,
            )

            mock_merge.assert_called_once_with(
                db=db,
                primary_transaction_id=primary_id,
                duplicate_transaction_ids=dup_ids,
                user=user,
                merge_reason="Same transaction",
                is_auto_merged=False,
            )
            assert result is mock_merge_record

    @pytest.mark.asyncio
    async def test_merge_value_error_raises_400(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        merge_request = MagicMock()
        merge_request.primary_transaction_id = uuid4()
        merge_request.duplicate_transaction_ids = [uuid4()]
        merge_request.merge_reason = None

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.merge_transactions",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid merge"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await merge_transactions(
                    merge_request=merge_request,
                    current_user=user,
                    db=db,
                )
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Invalid merge request"


@pytest.mark.unit
class TestGetMergeHistory:
    """Test get_merge_history endpoint."""

    @pytest.mark.asyncio
    async def test_returns_history_list(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        transaction_id = uuid4()
        mock_history = [MagicMock(), MagicMock(), MagicMock()]

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.get_merge_history",
            new_callable=AsyncMock,
            return_value=mock_history,
        ) as mock_get:
            result = await get_merge_history(
                transaction_id=transaction_id,
                current_user=user,
                db=db,
            )

            mock_get.assert_called_once_with(
                db=db,
                transaction_id=transaction_id,
                user=user,
            )
            assert result == mock_history

    @pytest.mark.asyncio
    async def test_returns_empty_history(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.get_merge_history",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await get_merge_history(
                transaction_id=uuid4(),
                current_user=user,
                db=db,
            )

            assert result == []


@pytest.mark.unit
class TestAutoDetectAndMergeDuplicates:
    """Test auto_detect_and_merge_duplicates endpoint."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_matches(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        primary1 = MagicMock()
        dups1 = [MagicMock(), MagicMock()]
        primary2 = MagicMock()
        dups2 = [MagicMock()]
        mock_matches = [(primary1, dups1), (primary2, dups2)]

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.auto_detect_and_merge_duplicates",
            new_callable=AsyncMock,
            return_value=mock_matches,
        ) as mock_auto:
            result = await auto_detect_and_merge_duplicates(
                dry_run=True,
                date_window_days=3,
                current_user=user,
                db=db,
            )

            mock_auto.assert_called_once_with(
                db=db,
                user=user,
                date_window_days=3,
                dry_run=True,
            )
            assert result["dry_run"] is True
            assert result["matches_found"] == 2
            assert len(result["matches"]) == 2
            assert result["matches"][0]["primary"] is primary1
            assert result["matches"][0]["duplicates"] is dups1
            assert result["matches"][1]["primary"] is primary2
            assert result["matches"][1]["duplicates"] is dups2

    @pytest.mark.asyncio
    async def test_no_matches_found(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.auto_detect_and_merge_duplicates",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await auto_detect_and_merge_duplicates(
                dry_run=True,
                date_window_days=5,
                current_user=user,
                db=db,
            )

            assert result["dry_run"] is True
            assert result["matches_found"] == 0
            assert result["matches"] == []

    @pytest.mark.asyncio
    async def test_dry_run_false(self):
        db = AsyncMock()
        user = Mock(spec=User)
        user.id = uuid4()
        user.organization_id = uuid4()

        mock_matches = [(MagicMock(), [MagicMock()])]

        with patch(
            "app.api.v1.transaction_merges.transaction_merge_service.auto_detect_and_merge_duplicates",
            new_callable=AsyncMock,
            return_value=mock_matches,
        ) as mock_auto:
            result = await auto_detect_and_merge_duplicates(
                dry_run=False,
                date_window_days=3,
                current_user=user,
                db=db,
            )

            mock_auto.assert_called_once_with(
                db=db,
                user=user,
                date_window_days=3,
                dry_run=False,
            )
            assert result["dry_run"] is False
            assert result["matches_found"] == 1
