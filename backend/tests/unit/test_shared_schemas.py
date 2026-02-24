"""Tests for shared budget/goal schema fields."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.schemas.savings_goal import SavingsGoalCreate, SavingsGoalUpdate, SavingsGoalResponse
from app.models.budget import BudgetPeriod


@pytest.mark.unit
class TestBudgetSchemaSharedFields:
    """Budget schemas handle is_shared and shared_user_ids correctly."""

    def test_create_schema_accepts_shared_fields(self):
        data = BudgetCreate(
            name="Shared",
            amount=Decimal("500"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2026, 1, 1),
            is_shared=True,
            shared_user_ids=[str(uuid4())],
        )
        assert data.is_shared is True
        assert len(data.shared_user_ids) == 1

    def test_create_schema_defaults_not_shared(self):
        data = BudgetCreate(
            name="Personal",
            amount=Decimal("100"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2026, 1, 1),
        )
        assert data.is_shared is False
        assert data.shared_user_ids is None

    def test_update_schema_is_shared_unset_by_default(self):
        data = BudgetUpdate(name="Renamed")
        dumped = data.model_dump(exclude_unset=True)
        assert "is_shared" not in dumped

    def test_update_schema_includes_is_shared_when_set(self):
        data = BudgetUpdate(is_shared=True)
        dumped = data.model_dump(exclude_unset=True)
        assert dumped["is_shared"] is True

    def test_response_schema_includes_user_id(self):
        uid = uuid4()
        resp = BudgetResponse(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uid,
            name="Test",
            amount=Decimal("100"),
            period=BudgetPeriod.MONTHLY,
            start_date=date(2026, 1, 1),
            end_date=None,
            category_id=None,
            label_id=None,
            rollover_unused=False,
            alert_threshold=Decimal("0.80"),
            is_active=True,
            is_shared=False,
            shared_user_ids=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert resp.user_id == uid


@pytest.mark.unit
class TestSavingsGoalSchemaSharedFields:
    """SavingsGoal schemas handle is_shared and shared_user_ids correctly."""

    def test_create_schema_accepts_shared_fields(self):
        data = SavingsGoalCreate(
            name="Shared Goal",
            target_amount=Decimal("5000"),
            start_date=date(2026, 1, 1),
            is_shared=True,
            shared_user_ids=[str(uuid4())],
        )
        assert data.is_shared is True
        assert len(data.shared_user_ids) == 1

    def test_create_schema_defaults_not_shared(self):
        data = SavingsGoalCreate(
            name="Personal",
            target_amount=Decimal("1000"),
            start_date=date(2026, 1, 1),
        )
        assert data.is_shared is False
        assert data.shared_user_ids is None

    def test_update_schema_is_shared_unset_by_default(self):
        data = SavingsGoalUpdate(name="Renamed")
        dumped = data.model_dump(exclude_unset=True)
        assert "is_shared" not in dumped

    def test_update_schema_includes_is_shared_when_set(self):
        data = SavingsGoalUpdate(is_shared=True)
        dumped = data.model_dump(exclude_unset=True)
        assert dumped["is_shared"] is True

    def test_response_schema_includes_user_id(self):
        uid = uuid4()
        resp = SavingsGoalResponse(
            id=uuid4(),
            organization_id=uuid4(),
            user_id=uid,
            name="Test",
            description=None,
            target_amount=Decimal("1000"),
            start_date=date(2026, 1, 1),
            target_date=None,
            account_id=None,
            current_amount=Decimal("0"),
            auto_sync=False,
            priority=1,
            is_completed=False,
            completed_at=None,
            is_funded=False,
            funded_at=None,
            is_shared=False,
            shared_user_ids=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert resp.user_id == uid
