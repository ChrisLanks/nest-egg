"""Unit tests for TaxBucketService."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.account import TaxTreatment
from app.services.tax_bucket_service import TaxBucketService


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_account(tax_treatment, balance: Decimal):
    acct = MagicMock()
    acct.tax_treatment = tax_treatment
    acct.current_balance = balance
    acct.is_active = True
    return acct


def _make_db(accounts: list):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = accounts
    db.execute = AsyncMock(return_value=mock_result)
    return db


# ── get_bucket_summary ───────────────────────────────────────────────────────


class TestGetBucketSummary:
    @pytest.mark.asyncio
    async def test_accounts_bucketed_correctly(self):
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("100000")),
            _make_account(TaxTreatment.ROTH, Decimal("50000")),
            _make_account(TaxTreatment.TAXABLE, Decimal("30000")),
            _make_account(TaxTreatment.TAX_FREE, Decimal("20000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["buckets"]["pre_tax"] == pytest.approx(100_000)
        assert result["buckets"]["roth"] == pytest.approx(50_000)
        assert result["buckets"]["taxable"] == pytest.approx(30_000)
        assert result["buckets"]["tax_free"] == pytest.approx(20_000)

    @pytest.mark.asyncio
    async def test_total_is_sum_of_all_buckets(self):
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("60000")),
            _make_account(TaxTreatment.ROTH, Decimal("40000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["total"] == pytest.approx(100_000)

    @pytest.mark.asyncio
    async def test_imbalanced_flag_true_when_pre_tax_over_85_pct(self):
        # 90% pre-tax, 10% Roth  → should trigger warning
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("90000")),
            _make_account(TaxTreatment.ROTH, Decimal("10000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["imbalanced"] is True
        assert result["pre_tax_pct"] == pytest.approx(0.90)

    @pytest.mark.asyncio
    async def test_imbalanced_flag_false_when_pre_tax_under_85_pct(self):
        # 50% pre-tax, 50% Roth  → no warning
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("50000")),
            _make_account(TaxTreatment.ROTH, Decimal("50000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["imbalanced"] is False

    @pytest.mark.asyncio
    async def test_imbalanced_flag_true_at_exactly_85_pct(self):
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("85000")),
            _make_account(TaxTreatment.ROTH, Decimal("15000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["imbalanced"] is True

    @pytest.mark.asyncio
    async def test_zero_balance_accounts_skipped(self):
        accounts = [
            _make_account(TaxTreatment.PRE_TAX, Decimal("0")),
            _make_account(TaxTreatment.ROTH, Decimal("50000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["buckets"]["pre_tax"] == pytest.approx(0.0)
        assert result["buckets"]["roth"] == pytest.approx(50_000)

    @pytest.mark.asyncio
    async def test_no_retirement_accounts_pre_tax_pct_zero(self):
        accounts = [
            _make_account(TaxTreatment.TAXABLE, Decimal("100000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["pre_tax_pct"] == pytest.approx(0.0)
        assert result["imbalanced"] is False

    @pytest.mark.asyncio
    async def test_null_tax_treatment_goes_to_other(self):
        accounts = [
            _make_account(None, Decimal("25000")),
        ]
        db = _make_db(accounts)

        result = await TaxBucketService.get_bucket_summary(db, uuid4())

        assert result["buckets"]["other"] == pytest.approx(25_000)

    @pytest.mark.asyncio
    async def test_user_id_filter_passed_to_query(self):
        db = _make_db([])
        user_id = uuid4()

        await TaxBucketService.get_bucket_summary(db, uuid4(), user_id=user_id)

        # Verify db.execute was called (query was built and executed)
        db.execute.assert_awaited_once()


# ── project_rmd_schedule ─────────────────────────────────────────────────────


class TestProjectRmdSchedule:
    def test_returns_entries_from_rmd_start_age_to_100(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=50,
        )

        ages = [entry["age"] for entry in schedule]
        # RMD starts at TRIGGER_AGE (73) and runs to 100 inclusive
        assert ages[0] == 73
        assert ages[-1] == 100
        assert len(schedule) == 28  # ages 73-100 inclusive

    def test_returns_entries_from_current_age_when_already_past_rmd_start(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=80,
        )

        ages = [entry["age"] for entry in schedule]
        assert ages[0] == 80
        assert ages[-1] == 100

    def test_each_year_remaining_balance_decreases(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("1000000"),
            current_age=70,
            growth_rate=Decimal("0.0"),  # no growth → balance must shrink
        )

        for i in range(1, len(schedule)):
            assert (
                schedule[i]["remaining_balance"] < schedule[i - 1]["remaining_balance"]
            ), f"Balance did not decrease at age {schedule[i]['age']}"

    def test_rmd_amounts_are_positive(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=55,
        )

        for entry in schedule:
            assert entry["rmd_amount"] > 0

    def test_custom_growth_rate_applied(self):
        schedule_low = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=55,
            growth_rate=Decimal("0.02"),
        )
        schedule_high = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("500000"),
            current_age=55,
            growth_rate=Decimal("0.10"),
        )

        # Higher growth means larger RMDs
        assert (
            schedule_high[0]["rmd_amount"] > schedule_low[0]["rmd_amount"]
        )

    def test_zero_balance_returns_zero_rmds(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("0"),
            current_age=55,
        )

        for entry in schedule:
            assert entry["rmd_amount"] == pytest.approx(0.0)

    def test_schedule_entries_have_required_keys(self):
        schedule = TaxBucketService.project_rmd_schedule(
            pre_tax_balance=Decimal("300000"),
            current_age=65,
        )

        assert len(schedule) > 0
        for entry in schedule:
            assert "age" in entry
            assert "rmd_amount" in entry
            assert "remaining_balance" in entry


# ── get_roth_conversion_headroom ─────────────────────────────────────────────


class TestGetRothConversionHeadroom:
    def test_returns_non_negative_headroom(self):
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("50000"),
            filing_status="single",
        )

        assert result["conversion_headroom"] >= 0

    def test_headroom_zero_when_income_exceeds_ceiling(self):
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("500000"),
            filing_status="single",
        )

        assert result["conversion_headroom"] == pytest.approx(0.0)

    def test_headroom_positive_when_income_below_ceiling(self):
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("60000"),
            filing_status="single",
        )

        # At $60k income (single), the 22% bracket ceiling is above $100k
        assert result["conversion_headroom"] > 0

    def test_married_ceiling_higher_than_single(self):
        single = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("50000"),
            filing_status="single",
        )
        married = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("50000"),
            filing_status="married",
        )

        assert married["bracket_ceiling"] > single["bracket_ceiling"]

    def test_result_keys_present(self):
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("70000"),
            filing_status="single",
        )

        assert "target_bracket" in result
        assert "bracket_ceiling" in result
        assert "current_income" in result
        assert "conversion_headroom" in result

    def test_target_bracket_defaults_to_22_pct(self):
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=Decimal("50000"),
            filing_status="single",
        )

        assert result["target_bracket"] == pytest.approx(0.22)

    def test_headroom_equals_ceiling_minus_income(self):
        income = Decimal("60000")
        result = TaxBucketService.get_roth_conversion_headroom(
            current_taxable_income=income,
            filing_status="single",
        )

        expected = result["bracket_ceiling"] - float(income)
        assert result["conversion_headroom"] == pytest.approx(expected, abs=0.01)
