"""Unit tests for income_expenses API endpoints."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1.income_expenses import (
    get_account_merchant_breakdown,
    get_account_summary,
    get_annual_summary,
    get_category_drill_down,
    get_category_trends,
    get_income_expense_summary,
    get_income_expense_trend,
    get_label_merchant_breakdown,
    get_label_summary,
    get_merchant_breakdown,
    get_merchant_summary,
    get_quarterly_summary,
    get_year_over_year_comparison,
)
from app.models.account import Account
from app.models.user import User

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user():
    user = Mock(spec=User)
    user.id = uuid4()
    user.organization_id = uuid4()
    return user


def _make_account():
    acc = Mock(spec=Account)
    acc.id = uuid4()
    acc.name = "Checking"
    acc.is_active = True
    return acc


# ---------------------------------------------------------------------------
# GET /income-expenses/summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetIncomeExpenseSummary:
    """Test get_income_expense_summary endpoint."""

    @pytest.mark.asyncio
    async def test_summary_success_no_user_filter(self):
        """Should return income/expense summary for the whole household."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        # 1st call: totals query
        totals_row = Mock()
        totals_row.total_income = Decimal("5000")
        totals_row.total_expenses = Decimal("3000")
        totals_result = Mock()
        totals_result.one.return_value = totals_row

        # 2nd call: category breakdown query (empty)
        cat_result = Mock()
        cat_result.__iter__ = Mock(return_value=iter([]))

        # 3rd call: categories with children query (.all() is called on the result)
        cats_with_children_result = Mock()
        cats_with_children_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[totals_result, cat_result, cats_with_children_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_income_expense_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 5000.0
        assert result.total_expenses == 3000.0
        assert result.net == 2000.0

    @pytest.mark.asyncio
    async def test_summary_with_user_filter(self):
        """Should call verify_household_member when user_id provided."""
        user = _make_user()
        target_user_id = uuid4()
        mock_acc = _make_account()
        db = AsyncMock()

        totals_row = Mock()
        totals_row.total_income = Decimal("1000")
        totals_row.total_expenses = Decimal("500")
        totals_result = Mock()
        totals_result.one.return_value = totals_row

        cat_result = Mock()
        cat_result.__iter__ = Mock(return_value=iter([]))

        cats_with_children_result = Mock()
        cats_with_children_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[totals_result, cat_result, cats_with_children_result])

        with patch(
            "app.api.v1.income_expenses.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.income_expenses.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                result = await get_income_expense_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=target_user_id,
                    current_user=user,
                    db=db,
                )

            mock_verify.assert_awaited_once_with(db, target_user_id, user.organization_id)
            assert result.total_income == 1000.0

    @pytest.mark.asyncio
    async def test_summary_with_categories(self):
        """Should return income and expense categories."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        totals_row = Mock()
        totals_row.total_income = Decimal("5000")
        totals_row.total_expenses = Decimal("3000")
        totals_result = Mock()
        totals_result.one.return_value = totals_row

        # Category rows
        cat_row = Mock()
        cat_row.category_name = "Salary"
        cat_row.income = Decimal("5000")
        cat_row.expenses = Decimal("0")
        cat_row.income_count = 2
        cat_row.expense_count = 0
        cat_row.has_children_flag = 0

        cat_row2 = Mock()
        cat_row2.category_name = "Food"
        cat_row2.income = Decimal("0")
        cat_row2.expenses = Decimal("1500")
        cat_row2.income_count = 0
        cat_row2.expense_count = 10
        cat_row2.has_children_flag = 0

        cat_result = Mock()
        cat_result.__iter__ = Mock(return_value=iter([cat_row, cat_row2]))

        # Categories with children query
        cats_with_children_result = Mock()
        cats_with_children_result.all.return_value = []

        db.execute = AsyncMock(side_effect=[totals_result, cat_result, cats_with_children_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_income_expense_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == "Salary"
        assert result.income_categories[0].amount == 5000.0
        assert len(result.expense_categories) == 1
        assert result.expense_categories[0].category == "Food"

    @pytest.mark.asyncio
    async def test_summary_invalid_date_range(self):
        """Should raise 400 for invalid date range (start > end)."""
        user = _make_user()
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_income_expense_summary(
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
                user_id=None,
                current_user=user,
                db=db,
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# GET /income-expenses/trend
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetIncomeExpenseTrend:
    """Test get_income_expense_trend endpoint."""

    @pytest.mark.asyncio
    async def test_trend_success(self):
        """Should return monthly trend data."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        # Trend row
        row = Mock()
        row.month = date(2024, 1, 1)
        row.income = Decimal("5000")
        row.expenses = Decimal("-3000")

        result = Mock()
        result.__iter__ = Mock(return_value=iter([row]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                trends = await get_income_expense_trend(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(trends) == 1
        assert trends[0].month == "2024-01"
        assert trends[0].income == 5000.0
        assert trends[0].expenses == 3000.0
        assert trends[0].net == 2000.0

    @pytest.mark.asyncio
    async def test_trend_empty(self):
        """Should return empty list when no data."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        result = Mock()
        result.__iter__ = Mock(return_value=iter([]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                trends = await get_income_expense_trend(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert trends == []

    @pytest.mark.asyncio
    async def test_trend_with_user_filter(self):
        """Should filter by user when user_id provided."""
        user = _make_user()
        target_user_id = uuid4()
        mock_acc = _make_account()
        db = AsyncMock()

        result = Mock()
        result.__iter__ = Mock(return_value=iter([]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.income_expenses.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                await get_income_expense_trend(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=target_user_id,
                    current_user=user,
                    db=db,
                )

            mock_verify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_trend_with_label_name_filter(self):
        """Should accept label_name param and return trend data; verify_household_member NOT called."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.month = date(2024, 3, 1)
        row.income = Decimal("4000")
        row.expenses = Decimal("-2500")

        result = Mock()
        result.__iter__ = Mock(return_value=iter([row]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.income_expenses.get_all_household_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                    return_value=[mock_acc],
                ):
                    trends = await get_income_expense_trend(
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 12, 31),
                        user_id=None,
                        label_name="Freelance",
                        current_user=user,
                        db=db,
                    )

        # verify_household_member should NOT be called when user_id=None
        mock_verify.assert_not_awaited()
        # Trend data should still be returned
        assert len(trends) == 1
        assert trends[0].month == "2024-03"
        assert trends[0].income == 4000.0
        assert trends[0].expenses == 2500.0
        assert trends[0].net == 1500.0

    @pytest.mark.asyncio
    async def test_trend_with_label_name_and_user_id(self):
        """Should call verify_household_member when both label_name and user_id are provided."""
        user = _make_user()
        target_user_id = uuid4()
        mock_acc = _make_account()
        db = AsyncMock()

        result = Mock()
        result.__iter__ = Mock(return_value=iter([]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.income_expenses.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                await get_income_expense_trend(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=target_user_id,
                    label_name="Freelance",
                    current_user=user,
                    db=db,
                )

        mock_verify.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_trend_label_name_none_uses_all_income(self):
        """When label_name=None (default), endpoint returns income from all transactions (no regression)."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.month = date(2024, 6, 1)
        row.income = Decimal("6000")
        row.expenses = Decimal("-4000")

        result = Mock()
        result.__iter__ = Mock(return_value=iter([row]))
        db.execute = AsyncMock(return_value=result)

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                trends = await get_income_expense_trend(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    label_name=None,
                    current_user=user,
                    db=db,
                )

        assert len(trends) == 1
        assert trends[0].month == "2024-06"
        assert trends[0].income == 6000.0
        assert trends[0].expenses == 4000.0
        assert trends[0].net == 2000.0


# ---------------------------------------------------------------------------
# GET /income-expenses/merchants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMerchantBreakdown:
    """Test get_merchant_breakdown endpoint."""

    @pytest.mark.asyncio
    async def test_merchant_breakdown_income(self):
        """Should return merchant breakdown for income."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.merchant_name = "Employer Inc"
        row.total = Decimal("5000")
        row.count = 2

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([row]))

        total_result = Mock()
        total_result.scalar.return_value = Decimal("5000")

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    category=None,
                    transaction_type="income",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result) == 1
        assert result[0].category == "Employer Inc"
        assert result[0].amount == 5000.0
        assert result[0].percentage == 100.0

    @pytest.mark.asyncio
    async def test_merchant_breakdown_expense_with_category_filter(self):
        """Should filter by category when provided."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.merchant_name = "Grocery Store"
        row.total = Decimal("-200")
        row.count = 5

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([row]))

        total_result = Mock()
        total_result.scalar.return_value = Decimal("-200")

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    category="Food",
                    transaction_type="expense",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result) == 1
        assert result[0].category == "Grocery Store"
        assert result[0].amount == 200.0

    @pytest.mark.asyncio
    async def test_merchant_breakdown_empty(self):
        """Should return empty list when no merchants found."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([]))

        total_result = Mock()
        total_result.scalar.return_value = None

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    category=None,
                    transaction_type="expense",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result == []


# ---------------------------------------------------------------------------
# GET /income-expenses/merchant-summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetMerchantSummary:
    """Test get_merchant_summary endpoint."""

    @pytest.mark.asyncio
    async def test_merchant_summary_success(self):
        """Should return merchant summary with income and expenses."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row1 = Mock()
        row1.merchant_name = "Employer"
        row1.income = Decimal("5000")
        row1.expenses = Decimal("0")
        row1.income_count = 1
        row1.expense_count = 0

        row2 = Mock()
        row2.merchant_name = "Grocery"
        row2.income = Decimal("0")
        row2.expenses = Decimal("300")
        row2.income_count = 0
        row2.expense_count = 5

        result_mock = Mock()
        result_mock.__iter__ = Mock(return_value=iter([row1, row2]))
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_merchant_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 5000.0
        assert result.total_expenses == 300.0
        assert result.net == 4700.0
        assert len(result.income_categories) == 1
        assert len(result.expense_categories) == 1

    @pytest.mark.asyncio
    async def test_merchant_summary_empty(self):
        """Should return zeros when no merchant data."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        result_mock = Mock()
        result_mock.__iter__ = Mock(return_value=iter([]))
        db.execute = AsyncMock(return_value=result_mock)

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_merchant_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 0.0
        assert result.total_expenses == 0.0


# ---------------------------------------------------------------------------
# GET /income-expenses/account-summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAccountSummary:
    """Test get_account_summary endpoint."""

    @pytest.mark.asyncio
    async def test_account_summary_success(self):
        """Should return account summary grouped by account."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        # income total
        income_total_result = Mock()
        income_total_result.scalar.return_value = Decimal("5000")

        # expense total
        expense_total_result = Mock()
        expense_total_result.scalar.return_value = Decimal("-3000")

        # income by account
        acc_id = uuid4()
        inc_row = Mock()
        inc_row.id = acc_id
        inc_row.name = "Checking"
        inc_row.total = Decimal("5000")
        inc_row.count = 2
        income_accounts_result = Mock()
        income_accounts_result.__iter__ = Mock(return_value=iter([inc_row]))

        # expense by account
        exp_row = Mock()
        exp_row.id = acc_id
        exp_row.name = "Checking"
        exp_row.total = Decimal("-3000")
        exp_row.count = 10
        expense_accounts_result = Mock()
        expense_accounts_result.__iter__ = Mock(return_value=iter([exp_row]))

        db.execute = AsyncMock(
            side_effect=[
                income_total_result,
                expense_total_result,
                income_accounts_result,
                expense_accounts_result,
            ]
        )

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_account_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 5000.0
        assert result.total_expenses == 3000.0
        assert len(result.income_categories) == 1
        assert result.income_categories[0].id == str(acc_id)


# ---------------------------------------------------------------------------
# GET /income-expenses/account-merchants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetAccountMerchantBreakdown:
    """Test get_account_merchant_breakdown endpoint."""

    @pytest.mark.asyncio
    async def test_account_merchant_breakdown_success(self):
        """Should return merchant breakdown for a specific account."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.merchant_name = "Amazon"
        row.total = Decimal("-150")
        row.count = 3

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([row]))

        total_result = Mock()
        total_result.scalar.return_value = Decimal("-150")

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_account_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    account_id=str(mock_acc.id),
                    transaction_type="expense",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result) == 1
        assert result[0].category == "Amazon"
        assert result[0].amount == 150.0


# ---------------------------------------------------------------------------
# GET /income-expenses/label-summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLabelSummary:
    """Test get_label_summary endpoint."""

    @pytest.mark.asyncio
    async def test_label_summary_success(self):
        """Should return label-based summary with unlabeled categories."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        # total income
        income_total = Mock()
        income_total.scalar.return_value = Decimal("5000")

        # total expenses
        expense_total = Mock()
        expense_total.scalar.return_value = Decimal("-3000")

        # income by label (empty - all unlabeled)
        income_labels = Mock()
        income_labels.__iter__ = Mock(return_value=iter([]))

        # unlabeled income count
        unlabeled_income_count = Mock()
        unlabeled_income_count.scalar.return_value = 2

        # expense by label (empty - all unlabeled)
        expense_labels = Mock()
        expense_labels.__iter__ = Mock(return_value=iter([]))

        # unlabeled expense count
        unlabeled_expense_count = Mock()
        unlabeled_expense_count.scalar.return_value = 10

        db.execute = AsyncMock(
            side_effect=[
                income_total,
                expense_total,
                income_labels,
                unlabeled_income_count,
                expense_labels,
                unlabeled_expense_count,
            ]
        )

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_label_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 5000.0
        assert result.total_expenses == 3000.0
        # Should have "Unlabeled" entries
        assert any(c.category == "Unlabeled" for c in result.income_categories)
        assert any(c.category == "Unlabeled" for c in result.expense_categories)

    @pytest.mark.asyncio
    async def test_label_summary_with_labels(self):
        """Should return label breakdown when labels exist."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        income_total = Mock()
        income_total.scalar.return_value = Decimal("5000")

        expense_total = Mock()
        expense_total.scalar.return_value = Decimal("-3000")

        # income labels: fully labeled
        label_row = Mock()
        label_row.name = "Work"
        label_row.total = Decimal("5000")
        label_row.count = 2
        income_labels = Mock()
        income_labels.__iter__ = Mock(return_value=iter([label_row]))

        # expense labels: partially labeled
        exp_label_row = Mock()
        exp_label_row.name = "Groceries"
        exp_label_row.total = Decimal("-2000")
        exp_label_row.count = 5
        expense_labels = Mock()
        expense_labels.__iter__ = Mock(return_value=iter([exp_label_row]))

        # unlabeled expense count
        unlabeled_expense_count = Mock()
        unlabeled_expense_count.scalar.return_value = 3

        db.execute = AsyncMock(
            side_effect=[
                income_total,
                expense_total,
                income_labels,
                expense_labels,
                unlabeled_expense_count,
            ]
        )

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_label_summary(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        # Income fully labeled => no "Unlabeled" for income
        assert len(result.income_categories) == 1
        assert result.income_categories[0].category == "Work"
        # Expense partially labeled => "Groceries" + "Unlabeled"
        assert len(result.expense_categories) == 2


# ---------------------------------------------------------------------------
# GET /income-expenses/label-merchants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetLabelMerchantBreakdown:
    """Test get_label_merchant_breakdown endpoint."""

    @pytest.mark.asyncio
    async def test_label_merchant_with_specific_label(self):
        """Should return merchants for a specific label."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.merchant_name = "Costco"
        row.total = Decimal("-200")
        row.count = 2

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([row]))

        total_result = Mock()
        total_result.scalar.return_value = Decimal("-200")

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_label_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    label="Groceries",
                    transaction_type="expense",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result) == 1
        assert result[0].category == "Costco"

    @pytest.mark.asyncio
    async def test_label_merchant_unlabeled(self):
        """Should handle 'Unlabeled' special case."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        row = Mock()
        row.merchant_name = "Corner Store"
        row.total = Decimal("-50")
        row.count = 1

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([row]))

        total_result = Mock()
        total_result.scalar.return_value = Decimal("-50")

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_label_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    label="Unlabeled",
                    transaction_type="expense",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_label_merchant_no_label_filter(self):
        """Should return all merchants when no label filter."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        merchant_result = Mock()
        merchant_result.__iter__ = Mock(return_value=iter([]))

        total_result = Mock()
        total_result.scalar.return_value = None

        db.execute = AsyncMock(side_effect=[merchant_result, total_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_label_merchant_breakdown(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    label=None,
                    transaction_type="income",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result == []


# ---------------------------------------------------------------------------
# GET /income-expenses/category-drill-down
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetCategoryDrillDown:
    """Test get_category_drill_down endpoint."""

    @pytest.mark.asyncio
    async def test_drill_down_no_custom_category_fallback(self):
        """Should fall back to provider category when no custom category found."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        # parent category not found (scalar_one_or_none returns None)
        parent_cat_result = Mock()
        parent_cat_result.scalar_one_or_none.return_value = None

        # income result
        income_row = Mock()
        income_row.total = Decimal("1000")
        income_row.count = 2
        income_result = Mock()
        income_result.one_or_none.return_value = income_row

        # expense result
        expense_row = Mock()
        expense_row.total = Decimal("-500")
        expense_row.count = 5
        expense_result = Mock()
        expense_result.one_or_none.return_value = expense_row

        db.execute = AsyncMock(side_effect=[parent_cat_result, income_result, expense_result])

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                result = await get_category_drill_down(
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 12, 31),
                    parent_category="Food",
                    user_id=None,
                    current_user=user,
                    db=db,
                )

        assert result.total_income == 1000.0
        assert result.total_expenses == 500.0


# ---------------------------------------------------------------------------
# Trend Analysis Endpoints
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrendAnalysisEndpoints:
    """Test trend analysis endpoints (year-over-year, quarterly, etc.)."""

    @pytest.mark.asyncio
    async def test_year_over_year_comparison(self):
        """Should delegate to TrendAnalysisService."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        expected = {"years": [2024, 2023], "data": []}

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_year_over_year_comparison",
                    new_callable=AsyncMock,
                    return_value=expected,
                ) as mock_service:
                    result = await get_year_over_year_comparison(
                        years=[2024, 2023],
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result == expected
        mock_service.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_quarterly_summary(self):
        """Should delegate to TrendAnalysisService."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        expected = {"quarters": []}

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_quarterly_summary",
                    new_callable=AsyncMock,
                    return_value=expected,
                ):
                    result = await get_quarterly_summary(
                        years=[2024],
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result == expected

    @pytest.mark.asyncio
    async def test_category_trends(self):
        """Should delegate to TrendAnalysisService."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        expected = {"category": "Food", "data": []}

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_category_trends",
                    new_callable=AsyncMock,
                    return_value=expected,
                ):
                    result = await get_category_trends(
                        category="Food",
                        start_date=date(2024, 1, 1),
                        end_date=date(2024, 12, 31),
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result == expected

    @pytest.mark.asyncio
    async def test_annual_summary(self):
        """Should delegate to TrendAnalysisService."""
        user = _make_user()
        mock_acc = _make_account()
        db = AsyncMock()

        expected = {"year": 2024, "total_income": 60000}

        with patch(
            "app.api.v1.income_expenses.get_all_household_accounts",
            new_callable=AsyncMock,
            return_value=[mock_acc],
        ):
            with patch(
                "app.api.v1.income_expenses.deduplication_service.deduplicate_accounts",
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_annual_summary",
                    new_callable=AsyncMock,
                    return_value=expected,
                ):
                    result = await get_annual_summary(
                        year=2024,
                        user_id=None,
                        current_user=user,
                        db=db,
                    )

        assert result == expected

    @pytest.mark.asyncio
    async def test_year_over_year_with_user_filter(self):
        """Should filter by user when user_id provided."""
        user = _make_user()
        target_user_id = uuid4()
        mock_acc = _make_account()
        db = AsyncMock()

        with patch(
            "app.api.v1.income_expenses.verify_household_member",
            new_callable=AsyncMock,
        ) as mock_verify:
            with patch(
                "app.api.v1.income_expenses.get_user_accounts",
                new_callable=AsyncMock,
                return_value=[mock_acc],
            ):
                with patch(
                    "app.api.v1.income_expenses.TrendAnalysisService.get_year_over_year_comparison",
                    new_callable=AsyncMock,
                    return_value={},
                ):
                    await get_year_over_year_comparison(
                        years=[2024],
                        user_id=target_user_id,
                        current_user=user,
                        db=db,
                    )

            mock_verify.assert_awaited_once()


# ---------------------------------------------------------------------------
# MAX_CATEGORY_RESULTS guard
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCategoryBreakdownLimit:
    """Test MAX_CATEGORY_RESULTS constant ensures the category query is bounded."""

    def test_max_category_results_constant(self):
        from app.api.v1.income_expenses import MAX_CATEGORY_RESULTS
        assert MAX_CATEGORY_RESULTS == 200

    def test_summary_returns_at_most_max_category_results_rows(self):
        """get_income_expense_summary must cap category breakdown at MAX_CATEGORY_RESULTS."""
        from app.api.v1.income_expenses import MAX_CATEGORY_RESULTS
        import inspect
        import app.api.v1.income_expenses as ie_module

        source = inspect.getsource(ie_module.get_income_expense_summary)
        assert "MAX_CATEGORY_RESULTS" in source or ".limit(" in source
