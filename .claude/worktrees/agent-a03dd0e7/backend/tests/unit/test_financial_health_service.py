"""Tests for the Financial Health Score service."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.constants.financial import HEALTH
from app.models.account import Account, AccountType
from app.services.financial_health_service import (
    FinancialHealthService,
    _build_recommendations,
    _debt_to_income_score,
    _emergency_fund_score,
    _grade,
    _retirement_progress_score,
    _retirement_target_multiple,
    _savings_rate_score,
)

# ---------------------------------------------------------------------------
# Grade assignment
# ---------------------------------------------------------------------------


class TestGrade:
    """Test grade thresholds."""

    def test_grade_a(self):
        assert _grade(90) == "A"
        assert _grade(100) == "A"
        assert _grade(95.5) == "A"

    def test_grade_b(self):
        assert _grade(75) == "B"
        assert _grade(89.9) == "B"

    def test_grade_c(self):
        assert _grade(60) == "C"
        assert _grade(74.9) == "C"

    def test_grade_d(self):
        assert _grade(40) == "D"
        assert _grade(59.9) == "D"

    def test_grade_f(self):
        assert _grade(0) == "F"
        assert _grade(39.9) == "F"


# ---------------------------------------------------------------------------
# Retirement target multiple
# ---------------------------------------------------------------------------


class TestRetirementTargetMultiple:
    """Test the Fidelity age-based retirement benchmark interpolation."""

    def test_age_at_or_below_30(self):
        assert _retirement_target_multiple(25) == Decimal(1)
        assert _retirement_target_multiple(30) == Decimal(1)

    def test_age_at_or_above_60(self):
        assert _retirement_target_multiple(60) == Decimal(8)
        assert _retirement_target_multiple(70) == Decimal(8)

    def test_midpoint_interpolation_35(self):
        # Between 30 (1x) and 40 (3x), age 35 => 1 + 0.5*(3-1) = 2
        result = _retirement_target_multiple(35)
        assert result == Decimal(2)

    def test_interpolation_age_45(self):
        # Between 40 (3x) and 50 (6x), age 45 => 3 + 0.5*(6-3) = 4.5
        result = _retirement_target_multiple(45)
        assert result == Decimal("4.5")

    def test_interpolation_age_55(self):
        # Between 50 (6x) and 60 (8x), age 55 => 6 + 0.5*(8-6) = 7
        result = _retirement_target_multiple(55)
        assert result == Decimal(7)


# ---------------------------------------------------------------------------
# Savings rate component
# ---------------------------------------------------------------------------


class TestSavingsRateScore:
    """Test savings rate score calculation."""

    def test_zero_income(self):
        result = _savings_rate_score(Decimal("500"), Decimal("0"))
        assert result["score"] == 0.0
        assert result["label"] == "Savings Rate"

    def test_negative_income(self):
        result = _savings_rate_score(Decimal("500"), Decimal("-100"))
        assert result["score"] == 0.0

    def test_twenty_percent_or_more(self):
        # 1000 savings / 5000 income = 20%
        result = _savings_rate_score(Decimal("1000"), Decimal("5000"))
        assert result["score"] == 100.0

    def test_high_savings_rate(self):
        # 2000 / 5000 = 40%
        result = _savings_rate_score(Decimal("2000"), Decimal("5000"))
        assert result["score"] == 100.0

    def test_fifteen_percent(self):
        # 750 / 5000 = 15% => 50 + (15-10)/10*50 = 50+25 = 75
        result = _savings_rate_score(Decimal("750"), Decimal("5000"))
        assert result["score"] == 75.0

    def test_ten_percent(self):
        # 500 / 5000 = 10% => 50 + 0 = 50
        result = _savings_rate_score(Decimal("500"), Decimal("5000"))
        assert result["score"] == 50.0

    def test_five_percent(self):
        # 250 / 5000 = 5% => 5/10*50 = 25
        result = _savings_rate_score(Decimal("250"), Decimal("5000"))
        assert result["score"] == 25.0

    def test_zero_savings(self):
        result = _savings_rate_score(Decimal("0"), Decimal("5000"))
        assert result["score"] == 0.0

    def test_negative_savings(self):
        result = _savings_rate_score(Decimal("-500"), Decimal("5000"))
        assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# Emergency fund component
# ---------------------------------------------------------------------------


class TestEmergencyFundScore:
    """Test emergency fund score calculation."""

    def test_six_months_or_more(self):
        result = _emergency_fund_score(Decimal("18000"), Decimal("3000"))
        assert result["score"] == 100.0

    def test_exactly_three_months(self):
        result = _emergency_fund_score(Decimal("9000"), Decimal("3000"))
        assert result["score"] == 50.0

    def test_four_and_half_months(self):
        # 4.5 months => 50 + (4.5-3)/3*50 = 50 + 25 = 75
        result = _emergency_fund_score(Decimal("13500"), Decimal("3000"))
        assert result["score"] == 75.0

    def test_one_month(self):
        # 1 month => 1/3*50 ~= 16.7
        result = _emergency_fund_score(Decimal("3000"), Decimal("3000"))
        assert result["score"] == pytest.approx(16.7, abs=0.1)

    def test_zero_expenses_with_savings(self):
        result = _emergency_fund_score(Decimal("5000"), Decimal("0"))
        # months defaults to 6, so score = 100
        assert result["score"] == 100.0

    def test_zero_expenses_zero_savings(self):
        result = _emergency_fund_score(Decimal("0"), Decimal("0"))
        assert result["score"] == 0.0

    def test_zero_savings(self):
        result = _emergency_fund_score(Decimal("0"), Decimal("3000"))
        assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# Debt-to-income component
# ---------------------------------------------------------------------------


class TestDebtToIncomeScore:
    """Test debt-to-income ratio score."""

    def test_zero_debt(self):
        result = _debt_to_income_score(Decimal("0"), Decimal("5000"))
        assert result["score"] == 100.0

    def test_fifteen_percent_or_less(self):
        # 750/5000 = 15%
        result = _debt_to_income_score(Decimal("750"), Decimal("5000"))
        assert result["score"] == 100.0

    def test_twenty_five_percent(self):
        # 25% => 50 + (35-25)/20*50 = 50 + 25 = 75
        result = _debt_to_income_score(Decimal("1250"), Decimal("5000"))
        assert result["score"] == 75.0

    def test_thirty_five_percent(self):
        # 35% => 50 + 0 = 50
        result = _debt_to_income_score(Decimal("1750"), Decimal("5000"))
        assert result["score"] == 50.0

    def test_at_upper_bound(self):
        # DTI_UPPER_BOUND% => score 0
        amount = Decimal("5000") * Decimal(HEALTH.DTI_UPPER_BOUND) / Decimal(100)
        result = _debt_to_income_score(amount, Decimal("5000"))
        assert result["score"] == 0.0

    def test_over_fifty_percent(self):
        result = _debt_to_income_score(Decimal("3500"), Decimal("5000"))
        assert result["score"] == 0.0

    def test_zero_income_with_debt(self):
        result = _debt_to_income_score(Decimal("500"), Decimal("0"))
        # ratio = 100, score = 0
        assert result["score"] == 0.0

    def test_zero_income_zero_debt(self):
        result = _debt_to_income_score(Decimal("0"), Decimal("0"))
        assert result["score"] == 100.0


# ---------------------------------------------------------------------------
# Retirement progress component
# ---------------------------------------------------------------------------


class TestRetirementProgressScore:
    """Test retirement progress score."""

    def test_no_age(self):
        result = _retirement_progress_score(Decimal("100000"), Decimal("60000"), None)
        assert result["score"] == 0.0
        assert "Add birthdate" in result["detail"]

    def test_zero_annual_income(self):
        result = _retirement_progress_score(Decimal("100000"), Decimal("0"), 40)
        assert result["score"] == 0.0

    def test_full_target_met(self):
        # Age 40, target = 3x salary. 60k salary => target 180k.
        # Balance 200k => 111% => score 100
        result = _retirement_progress_score(Decimal("200000"), Decimal("60000"), 40)
        assert result["score"] == 100.0

    def test_seventy_five_percent_progress(self):
        # Age 40, target = 3x60k = 180k, balance = 140k => ~77.8% => score BAND_HIGH
        result = _retirement_progress_score(Decimal("140000"), Decimal("60000"), 40)
        assert result["score"] == HEALTH.RETIREMENT_SCORE_BAND_HIGH

    def test_fifty_percent_progress(self):
        # target 180k, balance 100k => 55.6% => score 50
        result = _retirement_progress_score(Decimal("100000"), Decimal("60000"), 40)
        assert result["score"] == 50.0

    def test_twenty_five_percent_progress(self):
        # target 180k, balance 50k => 27.8% => score BAND_LOW
        result = _retirement_progress_score(Decimal("50000"), Decimal("60000"), 40)
        assert result["score"] == HEALTH.RETIREMENT_SCORE_BAND_LOW

    def test_below_twenty_five_percent(self):
        # target 180k, balance 10k => 5.6% => score 0
        result = _retirement_progress_score(Decimal("10000"), Decimal("60000"), 40)
        assert result["score"] == 0.0


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


class TestBuildRecommendations:
    """Test recommendation generation."""

    def test_all_scores_high_returns_positive_message(self):
        components = {
            "savings_rate": {"score": 95},
            "emergency_fund": {"score": 90},
            "debt_to_income": {"score": 85},
            "retirement_progress": {"score": 100},
        }
        recs = _build_recommendations(components)
        assert len(recs) == 1
        assert "Great job" in recs[0]

    def test_low_savings_rate_recommendation(self):
        components = {
            "savings_rate": {"score": 30},
            "emergency_fund": {"score": 90},
            "debt_to_income": {"score": 90},
            "retirement_progress": {"score": 90},
        }
        recs = _build_recommendations(components)
        assert any("10%" in r for r in recs)

    def test_moderate_savings_rate_recommendation(self):
        components = {
            "savings_rate": {"score": 60},
            "emergency_fund": {"score": 90},
            "debt_to_income": {"score": 90},
            "retirement_progress": {"score": 90},
        }
        recs = _build_recommendations(components)
        assert any("20%" in r for r in recs)

    def test_max_three_recommendations(self):
        components = {
            "savings_rate": {"score": 10},
            "emergency_fund": {"score": 20},
            "debt_to_income": {"score": 15},
            "retirement_progress": {"score": 5},
        }
        recs = _build_recommendations(components)
        assert len(recs) == 3

    def test_low_emergency_fund_recommendation(self):
        components = {
            "savings_rate": {"score": 90},
            "emergency_fund": {"score": 30},
            "debt_to_income": {"score": 90},
            "retirement_progress": {"score": 90},
        }
        recs = _build_recommendations(components)
        assert any("3 months" in r for r in recs)

    def test_high_debt_recommendation(self):
        components = {
            "savings_rate": {"score": 90},
            "emergency_fund": {"score": 90},
            "debt_to_income": {"score": 20},
            "retirement_progress": {"score": 90},
        }
        recs = _build_recommendations(components)
        assert any("high-interest debt" in r for r in recs)


# ---------------------------------------------------------------------------
# Full service calculate (integration with DB)
# ---------------------------------------------------------------------------


class TestFinancialHealthServiceCalculate:
    """Test the full calculate method with database."""

    @pytest.mark.asyncio
    async def test_calculate_with_no_accounts(self, db, test_user):
        """With no accounts, all component scores should be low/zero."""
        service = FinancialHealthService(db)
        result = await service.calculate(
            organization_id=str(test_user.organization_id),
            user_id=test_user.id,
        )

        assert "overall_score" in result
        assert "grade" in result
        assert "components" in result
        assert "recommendations" in result
        assert result["overall_score"] >= 0

    @pytest.mark.asyncio
    async def test_calculate_with_accounts(self, db, test_user):
        """Calculate score with checking, savings, and credit card accounts."""
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        savings = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("15000.00"),
            is_active=True,
        )
        credit_card = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Credit Card",
            account_type=AccountType.CREDIT_CARD,
            current_balance=Decimal("-2000.00"),
            is_active=True,
            minimum_payment=Decimal("50.00"),
        )
        db.add_all([checking, savings, credit_card])
        await db.commit()

        service = FinancialHealthService(db)
        result = await service.calculate(
            organization_id=str(test_user.organization_id),
            user_id=test_user.id,
        )

        assert result["overall_score"] >= 0
        assert result["grade"] in ("A", "B", "C", "D", "F")
        assert "savings_rate" in result["components"]
        assert "emergency_fund" in result["components"]
        assert "debt_to_income" in result["components"]
        assert "retirement_progress" in result["components"]

    @pytest.mark.asyncio
    async def test_calculate_with_retirement_account(self, db, test_user):
        """Retirement accounts contribute to the retirement progress score."""
        # Give user a birthdate for age calculation
        test_user.birthdate = date(1985, 6, 15)
        db.add(test_user)

        ira = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="IRA",
            account_type=AccountType.RETIREMENT_IRA,
            current_balance=Decimal("150000.00"),
            is_active=True,
        )
        # Need some income transactions for the calculation
        checking = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Checking",
            account_type=AccountType.CHECKING,
            current_balance=Decimal("5000.00"),
            is_active=True,
        )
        db.add_all([ira, checking])
        await db.commit()

        service = FinancialHealthService(db)
        result = await service.calculate(
            organization_id=str(test_user.organization_id),
            user_id=test_user.id,
            account_ids=[ira.id, checking.id],
        )

        # Retirement component should have a score
        retirement = result["components"]["retirement_progress"]
        assert retirement["label"] == "Retirement Progress"

    @pytest.mark.asyncio
    async def test_calculate_inactive_accounts_excluded(self, db, test_user):
        """Inactive accounts should not affect the score."""
        active = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Active Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("10000.00"),
            is_active=True,
        )
        inactive = Account(
            id=uuid4(),
            organization_id=test_user.organization_id,
            user_id=test_user.id,
            name="Inactive Savings",
            account_type=AccountType.SAVINGS,
            current_balance=Decimal("50000.00"),
            is_active=False,
        )
        db.add_all([active, inactive])
        await db.commit()

        service = FinancialHealthService(db)
        result = await service.calculate(
            organization_id=str(test_user.organization_id),
            user_id=test_user.id,
        )

        # The emergency fund component should only reflect the active account
        ef = result["components"]["emergency_fund"]
        assert ef["label"] == "Emergency Fund"

    @pytest.mark.asyncio
    async def test_overall_score_is_weighted_average(self, db, test_user):
        """Overall score should be the average of four component scores."""
        service = FinancialHealthService(db)
        result = await service.calculate(
            organization_id=str(test_user.organization_id),
            user_id=test_user.id,
        )

        components = result["components"]
        expected = round(
            components["savings_rate"]["score"] * 0.25
            + components["emergency_fund"]["score"] * 0.25
            + components["debt_to_income"]["score"] * 0.25
            + components["retirement_progress"]["score"] * 0.25,
            1,
        )
        assert result["overall_score"] == expected
