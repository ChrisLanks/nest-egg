"""Tests for IDOR fix on enhanced_trends.py endpoints.

net_worth_history, spending_velocity, and cash_flow_history accepted an
optional user_id parameter but did NOT call verify_household_member() before
passing it to the service — allowing any authenticated user to query another
user's sensitive financial data by UUID.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException


@pytest.mark.unit
class TestEnhancedTrendsIDOR:
    """verify_household_member must be called before using user_id in all three endpoints."""

    def _make_user(self, org_id=None):
        user = MagicMock()
        user.id = uuid4()
        user.organization_id = org_id or uuid4()
        return user

    @pytest.mark.asyncio
    async def test_net_worth_history_calls_verify_when_user_id_provided(self):
        from app.api.v1.enhanced_trends import get_net_worth_history

        current_user = self._make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.enhanced_trends.EnhancedTrendsService") as MockService:
            MockService.return_value.get_net_worth_history = AsyncMock(return_value=[])
            await get_net_worth_history(
                user_id=target_user_id,
                db=db,
                current_user=current_user,
            )
            mock_verify.assert_awaited_once_with(db, target_user_id, current_user.organization_id)

    @pytest.mark.asyncio
    async def test_net_worth_history_skips_verify_when_no_user_id(self):
        from app.api.v1.enhanced_trends import get_net_worth_history

        current_user = self._make_user()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.enhanced_trends.EnhancedTrendsService") as MockService:
            MockService.return_value.get_net_worth_history = AsyncMock(return_value=[])
            await get_net_worth_history(user_id=None, db=db, current_user=current_user)
            mock_verify.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_net_worth_history_rejects_non_member(self):
        from app.api.v1.enhanced_trends import get_net_worth_history

        current_user = self._make_user()
        stranger_id = uuid4()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=403, detail="Not a household member")
            with pytest.raises(HTTPException) as exc_info:
                await get_net_worth_history(user_id=stranger_id, db=db, current_user=current_user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_spending_velocity_calls_verify_when_user_id_provided(self):
        from app.api.v1.enhanced_trends import get_spending_velocity

        current_user = self._make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.enhanced_trends.EnhancedTrendsService") as MockService:
            MockService.return_value.get_spending_velocity = AsyncMock(return_value=[])
            await get_spending_velocity(
                months=12,
                user_id=target_user_id,
                db=db,
                current_user=current_user,
            )
            mock_verify.assert_awaited_once_with(db, target_user_id, current_user.organization_id)

    @pytest.mark.asyncio
    async def test_spending_velocity_rejects_non_member(self):
        from app.api.v1.enhanced_trends import get_spending_velocity

        current_user = self._make_user()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=403, detail="Not a household member")
            with pytest.raises(HTTPException) as exc_info:
                await get_spending_velocity(months=12, user_id=uuid4(), db=db, current_user=current_user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cash_flow_history_calls_verify_when_user_id_provided(self):
        from app.api.v1.enhanced_trends import get_cash_flow_history

        current_user = self._make_user()
        target_user_id = uuid4()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.enhanced_trends.EnhancedTrendsService") as MockService:
            MockService.return_value.get_cash_flow_history = AsyncMock(return_value=[])
            await get_cash_flow_history(
                months=12,
                user_id=target_user_id,
                db=db,
                current_user=current_user,
            )
            mock_verify.assert_awaited_once_with(db, target_user_id, current_user.organization_id)

    @pytest.mark.asyncio
    async def test_cash_flow_history_rejects_non_member(self):
        from app.api.v1.enhanced_trends import get_cash_flow_history

        current_user = self._make_user()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify:
            mock_verify.side_effect = HTTPException(status_code=403, detail="Not a household member")
            with pytest.raises(HTTPException) as exc_info:
                await get_cash_flow_history(months=12, user_id=uuid4(), db=db, current_user=current_user)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cash_flow_history_skips_verify_when_no_user_id(self):
        from app.api.v1.enhanced_trends import get_cash_flow_history

        current_user = self._make_user()
        db = AsyncMock()

        with patch("app.api.v1.enhanced_trends.verify_household_member", new_callable=AsyncMock) as mock_verify, \
             patch("app.api.v1.enhanced_trends.EnhancedTrendsService") as MockService:
            MockService.return_value.get_cash_flow_history = AsyncMock(return_value=[])
            await get_cash_flow_history(months=12, user_id=None, db=db, current_user=current_user)
            mock_verify.assert_not_awaited()
