"""Tests for app.api.v1.rebalancing API endpoints."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.rebalancing import (
    create_from_preset,
    create_target_allocation,
    delete_target_allocation,
    get_presets,
    get_rebalancing_analysis,
    list_target_allocations,
    update_target_allocation,
)


class TestGetPresets:
    """Test get_presets endpoint."""

    @pytest.mark.asyncio
    async def test_returns_presets(self):
        user = MagicMock()
        with patch(
            "app.api.v1.rebalancing.RebalancingService.get_presets",
            return_value={"bogleheads_3fund": {"name": "Bogleheads"}},
        ):
            result = await get_presets(current_user=user)
            assert "bogleheads_3fund" in result


class TestListTargetAllocations:
    """Test list_target_allocations endpoint."""

    @pytest.mark.asyncio
    async def test_returns_allocations(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_allocs = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_allocs
        db.execute = AsyncMock(return_value=mock_result)

        result = await list_target_allocations(current_user=user, db=db)
        assert result == mock_allocs


class TestCreateTargetAllocation:
    """Test create_target_allocation endpoint."""

    @pytest.mark.asyncio
    async def test_create_success(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        payload = MagicMock()
        payload.name = "My Portfolio"
        payload.allocations = [
            MagicMock(
                model_dump=MagicMock(
                    return_value={"asset_class": "domestic", "target_percent": 60, "label": "US"}
                )
            ),
            MagicMock(
                model_dump=MagicMock(
                    return_value={"asset_class": "bond", "target_percent": 40, "label": "Bonds"}
                )
            ),
        ]
        payload.drift_threshold = Decimal("5.0")

        with patch(
            "app.api.v1.rebalancing.RebalancingService.deactivate_other_allocations",
            new_callable=AsyncMock,
        ):
            await create_target_allocation(
                payload=payload,
                current_user=user,
                db=db,
            )

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()


class TestCreateFromPreset:
    """Test create_from_preset endpoint."""

    @pytest.mark.asyncio
    async def test_create_from_valid_preset(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        with patch(
            "app.api.v1.rebalancing.RebalancingService.deactivate_other_allocations",
            new_callable=AsyncMock,
        ):
            await create_from_preset(
                preset_key="bogleheads_3fund",
                current_user=user,
                db=db,
            )

        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_from_invalid_preset(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()

        with pytest.raises(HTTPException) as exc_info:
            await create_from_preset(
                preset_key="nonexistent_preset",
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 400
        assert "Unknown preset" in exc_info.value.detail


class TestUpdateTargetAllocation:
    """Test update_target_allocation endpoint."""

    @pytest.mark.asyncio
    async def test_update_success(self):
        allocation_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_alloc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alloc
        db.execute = AsyncMock(return_value=mock_result)

        payload = MagicMock()
        payload.is_active = None
        payload.allocations = None
        payload.model_dump.return_value = {"name": "Updated Name"}

        await update_target_allocation(
            allocation_id=allocation_id,
            payload=payload,
            current_user=user,
            db=db,
        )
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        payload = MagicMock()
        payload.is_active = None

        with pytest.raises(HTTPException) as exc_info:
            await update_target_allocation(
                allocation_id=uuid4(),
                payload=payload,
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_set_active_deactivates_others(self):
        allocation_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_alloc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alloc
        db.execute = AsyncMock(return_value=mock_result)

        payload = MagicMock()
        payload.is_active = True
        payload.allocations = None
        payload.model_dump.return_value = {"is_active": True}

        with patch(
            "app.api.v1.rebalancing.RebalancingService.deactivate_other_allocations",
            new_callable=AsyncMock,
        ) as mock_deactivate:
            await update_target_allocation(
                allocation_id=allocation_id,
                payload=payload,
                current_user=user,
                db=db,
            )
            mock_deactivate.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_with_allocations(self):
        """Cover lines 165-168: allocations serialization."""
        allocation_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_alloc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alloc
        db.execute = AsyncMock(return_value=mock_result)

        slice1 = MagicMock()
        slice1.model_dump.return_value = {
            "asset_class": "domestic",
            "target_percent": 60,
            "label": "US",
        }
        slice2 = MagicMock()
        slice2.model_dump.return_value = {
            "asset_class": "bond",
            "target_percent": 40,
            "label": "Bonds",
        }

        payload = MagicMock()
        payload.is_active = None
        payload.allocations = [slice1, slice2]
        payload.model_dump.return_value = {
            "allocations": [slice1, slice2],
        }

        await update_target_allocation(
            allocation_id=allocation_id,
            payload=payload,
            current_user=user,
            db=db,
        )
        db.commit.assert_called_once()


class TestDeleteTargetAllocation:
    """Test delete_target_allocation endpoint."""

    @pytest.mark.asyncio
    async def test_delete_success(self):
        allocation_id = uuid4()
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_alloc = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_alloc
        db.execute = AsyncMock(return_value=mock_result)

        await delete_target_allocation(
            allocation_id=allocation_id,
            current_user=user,
            db=db,
        )
        db.delete.assert_called_once_with(mock_alloc)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await delete_target_allocation(
                allocation_id=uuid4(),
                current_user=user,
                db=db,
            )
        assert exc_info.value.status_code == 404


class TestGetRebalancingAnalysis:
    """Test get_rebalancing_analysis endpoint."""

    @pytest.fixture(autouse=True)
    def mock_rate_limit(self):
        with patch("app.services.rate_limit_service.rate_limit_service.check_rate_limit", new_callable=AsyncMock):
            yield

    @pytest.mark.asyncio
    async def test_no_active_allocation_404(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        with patch(
            "app.api.v1.rebalancing.RebalancingService.get_active_allocation",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_rebalancing_analysis(http_request=MagicMock(), current_user=user, db=db)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_analysis_success(self):
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_allocation = MagicMock()
        mock_allocation.id = uuid4()
        mock_allocation.name = "My Portfolio"
        mock_allocation.allocations = [
            {"asset_class": "domestic", "target_percent": 60, "label": "US Stocks"},
            {"asset_class": "bond", "target_percent": 40, "label": "Bonds"},
        ]
        mock_allocation.drift_threshold = Decimal("5.0")

        # Mock holdings query result
        mock_row1 = MagicMock()
        mock_row1.asset_class = "domestic"
        mock_row1.total_value = Decimal("70000")

        mock_row2 = MagicMock()
        mock_row2.asset_class = "bond"
        mock_row2.total_value = Decimal("30000")

        mock_holdings_result = MagicMock()
        mock_holdings_result.all.return_value = [mock_row1, mock_row2]

        db.execute = AsyncMock(return_value=mock_holdings_result)

        from app.schemas.target_allocation import DriftItem, TradeRecommendation

        mock_drift_items = [
            DriftItem(
                asset_class="domestic",
                label="US Stocks",
                target_percent=Decimal("60"),
                current_percent=Decimal("70"),
                current_value=Decimal("70000"),
                drift_percent=Decimal("10"),
                drift_value=Decimal("10000"),
                status="overweight",
            ),
            DriftItem(
                asset_class="bond",
                label="Bonds",
                target_percent=Decimal("40"),
                current_percent=Decimal("30"),
                current_value=Decimal("30000"),
                drift_percent=Decimal("-10"),
                drift_value=Decimal("-10000"),
                status="underweight",
            ),
        ]
        mock_trade_recs = [
            TradeRecommendation(
                asset_class="bond",
                label="Bonds",
                action="BUY",
                amount=Decimal("10000"),
                current_value=Decimal("30000"),
                target_value=Decimal("40000"),
                current_percent=Decimal("30"),
                target_percent=Decimal("40"),
            ),
        ]

        with patch(
            "app.api.v1.rebalancing.RebalancingService.get_active_allocation",
            new_callable=AsyncMock,
            return_value=mock_allocation,
        ):
            with patch(
                "app.api.v1.rebalancing.RebalancingService.calculate_drift",
                return_value=(mock_drift_items, mock_trade_recs, True, Decimal("10.0")),
            ):
                result = await get_rebalancing_analysis(http_request=MagicMock(), current_user=user, db=db)

                assert result.target_allocation_id == mock_allocation.id
                assert result.portfolio_total == Decimal("100000")
                assert result.needs_rebalancing is True

    @pytest.mark.asyncio
    async def test_analysis_with_null_asset_class(self):
        """Holdings with null asset_class should be grouped as 'other'."""
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_allocation = MagicMock()
        mock_allocation.id = uuid4()
        mock_allocation.name = "Portfolio"
        mock_allocation.allocations = [
            {"asset_class": "other", "target_percent": 100, "label": "Other"},
        ]
        mock_allocation.drift_threshold = Decimal("5.0")

        mock_row = MagicMock()
        mock_row.asset_class = None  # Null asset class
        mock_row.total_value = Decimal("50000")

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.rebalancing.RebalancingService.get_active_allocation",
            new_callable=AsyncMock,
            return_value=mock_allocation,
        ):
            with patch(
                "app.api.v1.rebalancing.RebalancingService.calculate_drift",
                return_value=([], [], False, Decimal("0")),
            ):
                result = await get_rebalancing_analysis(http_request=MagicMock(), current_user=user, db=db)
                assert result.portfolio_total == Decimal("50000")

    @pytest.mark.asyncio
    async def test_analysis_with_zero_total_value(self):
        """Holdings with null total_value should default to 0."""
        db = AsyncMock()
        user = MagicMock()
        user.organization_id = uuid4()
        user.id = uuid4()

        mock_allocation = MagicMock()
        mock_allocation.id = uuid4()
        mock_allocation.name = "Portfolio"
        mock_allocation.allocations = []
        mock_allocation.drift_threshold = Decimal("5.0")

        mock_row = MagicMock()
        mock_row.asset_class = "domestic"
        mock_row.total_value = None

        mock_result = MagicMock()
        mock_result.all.return_value = [mock_row]
        db.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.api.v1.rebalancing.RebalancingService.get_active_allocation",
            new_callable=AsyncMock,
            return_value=mock_allocation,
        ):
            with patch(
                "app.api.v1.rebalancing.RebalancingService.calculate_drift",
                return_value=([], [], False, Decimal("0")),
            ):
                result = await get_rebalancing_analysis(http_request=MagicMock(), current_user=user, db=db)
                assert result.portfolio_total == Decimal("0")
