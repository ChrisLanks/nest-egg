"""Unit tests for SSClaimingStrategyService."""

import pytest

from app.services.ss_claiming_strategy_service import (
    SSClaimingStrategyService,
    _breakeven_months,
    _lifetime_benefit,
)

# ── _lifetime_benefit ──────────────────────────────────────────────────────


class TestLifetimeBenefit:
    def test_basic_calculation(self):
        # $2,000/month, claim at 62, die at 85 → 23 years × 12 months
        result = _lifetime_benefit(2000, 62, 85)
        assert result == 2000 * 23 * 12

    def test_death_before_claiming_returns_zero(self):
        assert _lifetime_benefit(2000, 70, 65) == 0.0

    def test_death_at_claiming_age_returns_zero(self):
        assert _lifetime_benefit(2000, 70, 70) == 0.0

    def test_one_year_benefit(self):
        assert _lifetime_benefit(1000, 62, 63) == 12_000.0


# ── _breakeven_months ──────────────────────────────────────────────────────


class TestBreakevenMonths:
    def test_later_benefit_higher_gives_breakeven(self):
        # Claim at 62: $1800/month; claim at 67: $2400/month
        # Foregone: 5yr × 12 × $1800 = $108,000
        # Monthly advantage: $600
        # Recoup: int($108,000 / $600) + 1 = 181 months after 67
        # Total: 60 + 181 = 241
        result = _breakeven_months(1800, 2400, 62, 67)
        assert result == 241

    def test_same_benefit_returns_none(self):
        assert _breakeven_months(2000, 2000, 62, 67) is None

    def test_lower_later_benefit_returns_none(self):
        assert _breakeven_months(2000, 1500, 62, 70) is None


# ── SSClaimingStrategyService.analyze ──────────────────────────────────────


class TestSSClaimingStrategyService:
    def test_options_cover_62_to_70(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        ages = [o.claiming_age for o in result.options]
        assert ages == list(range(62, 71))

    def test_fra_set_correctly(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1960,  # born 1960 → FRA = 67
        )
        assert result.fra_age == 67.0

    def test_pia_positive(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        assert result.estimated_pia > 0

    def test_manual_pia_override_used(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            manual_pia_override=2_500,
        )
        assert result.estimated_pia == pytest.approx(2_500, abs=0.01)

    def test_benefit_at_70_higher_than_62(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        opt62 = next(o for o in result.options if o.claiming_age == 62)
        opt70 = next(o for o in result.options if o.claiming_age == 70)
        assert opt70.monthly_benefit > opt62.monthly_benefit

    def test_breakeven_none_for_age_62(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        opt62 = next(o for o in result.options if o.claiming_age == 62)
        assert opt62.breakeven_vs_62_months is None

    def test_breakeven_positive_for_later_ages(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        for o in result.options:
            if o.claiming_age > 62:
                assert o.breakeven_vs_62_months is not None
                assert o.breakeven_vs_62_months > 0

    def test_optimal_age_base_is_valid(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        assert 62 <= result.optimal_age_base_scenario <= 70

    def test_optimal_age_pessimistic_lte_base(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        # Pessimistic (die at 78) should favour earlier claiming
        assert result.optimal_age_pessimistic_scenario <= result.optimal_age_base_scenario

    def test_optimal_age_optimistic_gte_base(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        # Optimistic (live to 92) should favour later claiming
        assert result.optimal_age_optimistic_scenario >= result.optimal_age_base_scenario

    def test_no_spousal_when_not_provided(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        assert result.spousal is None

    def test_spousal_benefit_present(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            spouse_pia=1_200,
        )
        assert result.spousal is not None
        assert result.spousal.spousal_monthly_at_fra == pytest.approx(600.0, abs=0.01)

    def test_spousal_at_62_less_than_fra(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            spouse_pia=1_200,
        )
        assert result.spousal.spousal_monthly_at_62 < result.spousal.spousal_monthly_at_fra

    def test_spousal_at_70_equals_fra(self):
        # Spousal benefit doesn't earn delayed credits beyond FRA
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            spouse_pia=1_200,
        )
        assert result.spousal.spousal_monthly_at_70 == result.spousal.spousal_monthly_at_fra

    def test_summary_non_empty(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        assert len(result.summary) > 0

    def test_lifetime_pessimistic_less_than_base(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        # For any given age, pessimistic lifetime < base lifetime
        for o in result.options:
            assert o.lifetime_pessimistic <= o.lifetime_base

    def test_lifetime_base_less_than_optimistic(self):
        result = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
        )
        for o in result.options:
            assert o.lifetime_base <= o.lifetime_optimistic
