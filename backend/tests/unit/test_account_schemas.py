"""Unit tests for account schema validation changes introduced in the security audit."""

import json
import pytest
from datetime import date
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.account import VestingMilestone, ManualAccountCreate
from app.models.account import AccountType, AccountSource


@pytest.mark.unit
class TestVestingMilestone:
    """Test VestingMilestone Pydantic model validation."""

    def test_valid_milestone(self):
        """Should accept a valid date and positive quantity."""
        m = VestingMilestone(date=date(2026, 1, 1), quantity=Decimal("100"))
        assert m.date == date(2026, 1, 1)
        assert m.quantity == Decimal("100")

    def test_zero_quantity_is_valid(self):
        """Zero quantity is allowed (ge=0)."""
        m = VestingMilestone(date=date(2026, 6, 15), quantity=Decimal("0"))
        assert m.quantity == Decimal("0")

    def test_negative_quantity_is_rejected(self):
        """Negative quantity must be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VestingMilestone(date=date(2026, 1, 1), quantity=Decimal("-1"))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("quantity",) for e in errors)

    def test_missing_date_is_rejected(self):
        """date field is required."""
        with pytest.raises(ValidationError):
            VestingMilestone(quantity=Decimal("50"))  # type: ignore[call-arg]

    def test_missing_quantity_is_rejected(self):
        """quantity field is required."""
        with pytest.raises(ValidationError):
            VestingMilestone(date=date(2026, 1, 1))  # type: ignore[call-arg]


@pytest.mark.unit
class TestOwnershipPercentageConstraint:
    """Test ownership_percentage ge=0, le=100 on ManualAccountCreate."""

    def _base(self, **kwargs) -> dict:
        return dict(
            name="Test Account",
            account_type=AccountType.BROKERAGE,
            account_source=AccountSource.MANUAL,
            balance=Decimal("1000.00"),
            **kwargs,
        )

    def test_valid_percentage_zero(self):
        acc = ManualAccountCreate(**self._base(ownership_percentage=Decimal("0")))
        assert acc.ownership_percentage == Decimal("0")

    def test_valid_percentage_100(self):
        acc = ManualAccountCreate(**self._base(ownership_percentage=Decimal("100")))
        assert acc.ownership_percentage == Decimal("100")

    def test_valid_percentage_partial(self):
        acc = ManualAccountCreate(**self._base(ownership_percentage=Decimal("49.5")))
        assert acc.ownership_percentage == Decimal("49.5")

    def test_ownership_percentage_above_100_is_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ManualAccountCreate(**self._base(ownership_percentage=Decimal("101")))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ownership_percentage",) for e in errors)

    def test_ownership_percentage_negative_is_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            ManualAccountCreate(**self._base(ownership_percentage=Decimal("-1")))
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ownership_percentage",) for e in errors)

    def test_ownership_percentage_optional_defaults_none(self):
        acc = ManualAccountCreate(**self._base())
        assert acc.ownership_percentage is None


@pytest.mark.unit
class TestVestingScheduleField:
    """Test that vesting_schedule accepts List[VestingMilestone] and serializes to JSON."""

    def test_vesting_schedule_accepts_list_of_milestones(self):
        milestones = [
            VestingMilestone(date=date(2026, 1, 1), quantity=Decimal("100")),
            VestingMilestone(date=date(2027, 1, 1), quantity=Decimal("200")),
        ]
        acc = ManualAccountCreate(
            name="RSU Account",
            account_type=AccountType.STOCK_OPTIONS,
            account_source=AccountSource.MANUAL,
            balance=Decimal("0"),
            vesting_schedule=milestones,
        )
        assert len(acc.vesting_schedule) == 2
        assert acc.vesting_schedule[0].quantity == Decimal("100")

    def test_vesting_schedule_defaults_to_none(self):
        acc = ManualAccountCreate(
            name="RSU Account",
            account_type=AccountType.STOCK_OPTIONS,
            account_source=AccountSource.MANUAL,
            balance=Decimal("0"),
        )
        assert acc.vesting_schedule is None

    def test_vesting_schedule_json_serialization(self):
        """Milestones should serialize to the JSON format used by the API layer."""
        milestones = [
            VestingMilestone(date=date(2026, 3, 15), quantity=Decimal("50.5")),
        ]
        serialized = json.dumps(
            [{"date": m.date.isoformat(), "quantity": float(m.quantity)} for m in milestones]
        )
        parsed = json.loads(serialized)
        assert parsed[0]["date"] == "2026-03-15"
        assert parsed[0]["quantity"] == pytest.approx(50.5)
