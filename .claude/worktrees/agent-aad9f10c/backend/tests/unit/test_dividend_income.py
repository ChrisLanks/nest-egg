"""Tests for dividend income model and schema.

Covers:
- IncomeType enum values
- DividendIncome model fields
- Schema validation (create, update, response)
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.dividend import IncomeType
from app.schemas.dividend import (
    DividendByTicker,
    DividendIncomeCreate,
    DividendIncomeUpdate,
    DividendSummary,
)

# ── IncomeType enum ────────────────────────────────────────────────────────


class TestIncomeType:
    def test_all_types_exist(self):
        types = [e.value for e in IncomeType]
        assert "dividend" in types
        assert "qualified_dividend" in types
        assert "capital_gain_distribution" in types
        assert "return_of_capital" in types
        assert "interest" in types
        assert "reinvested_dividend" in types

    def test_type_count(self):
        assert len(IncomeType) == 6


# ── Schema validation ──────────────────────────────────────────────────────


class TestDividendIncomeCreate:
    def test_valid_creation(self):
        schema = DividendIncomeCreate(
            account_id=uuid4(),
            income_type=IncomeType.DIVIDEND,
            ticker="AAPL",
            amount=Decimal("125.50"),
            ex_date=date(2024, 3, 15),
        )
        assert schema.ticker == "AAPL"
        assert schema.amount == Decimal("125.50")
        assert schema.is_reinvested is False

    def test_reinvested_dividend(self):
        schema = DividendIncomeCreate(
            account_id=uuid4(),
            income_type=IncomeType.REINVESTED_DIVIDEND,
            ticker="VTI",
            amount=Decimal("88.30"),
            is_reinvested=True,
            reinvested_shares=Decimal("0.350"),
            reinvested_price=Decimal("252.29"),
        )
        assert schema.is_reinvested is True
        assert schema.reinvested_shares == Decimal("0.350")

    def test_amount_must_be_positive(self):
        with pytest.raises(Exception):
            DividendIncomeCreate(
                account_id=uuid4(),
                income_type=IncomeType.DIVIDEND,
                ticker="AAPL",
                amount=Decimal("-10.00"),
            )

    def test_zero_amount_rejected(self):
        with pytest.raises(Exception):
            DividendIncomeCreate(
                account_id=uuid4(),
                income_type=IncomeType.DIVIDEND,
                ticker="AAPL",
                amount=Decimal("0"),
            )


class TestDividendIncomeUpdate:
    def test_partial_update(self):
        schema = DividendIncomeUpdate(
            amount=Decimal("200.00"),
        )
        assert schema.amount == Decimal("200.00")
        assert schema.income_type is None
        assert schema.is_reinvested is None


class TestDividendByTicker:
    def test_yield_on_cost(self):
        entry = DividendByTicker(
            ticker="SCHD",
            total_income=Decimal("500.00"),
            payment_count=4,
            yield_on_cost=Decimal("3.25"),
        )
        assert entry.yield_on_cost == Decimal("3.25")


class TestDividendSummary:
    def test_full_summary(self):
        summary = DividendSummary(
            total_income_ytd=Decimal("2500.00"),
            total_income_trailing_12m=Decimal("5000.00"),
            total_income_all_time=Decimal("12000.00"),
            projected_annual_income=Decimal("5200.00"),
            monthly_average=Decimal("416.67"),
            by_ticker=[],
            by_month=[],
            top_payers=[],
            income_growth_pct=Decimal("12.5"),
        )
        assert summary.total_income_ytd == Decimal("2500.00")
        assert summary.income_growth_pct == Decimal("12.5")
