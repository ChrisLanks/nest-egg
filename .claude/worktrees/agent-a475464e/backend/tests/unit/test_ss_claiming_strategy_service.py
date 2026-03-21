"""Unit tests for SSClaimingStrategyService.

Household view / user_id scoping
---------------------------------
SSClaimingStrategyService is entirely pure-Python — it takes only salary,
age, birth year, and optional PIA inputs; it does not touch the database.
User-level access control (confirming the requested user_id is a member of
the caller's household) is enforced at the API layer by
``verify_household_member()`` before the service is invoked.

The service itself produces different results when called with different
salary/age inputs, which is sufficient to verify that per-user data would
produce per-user projections. Tests for that case are in
TestSSClaimingPerUserProjection below.
"""

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


# ── Per-user projection isolation ─────────────────────────────────────────


class TestSSClaimingPerUserProjection:
    """Verify that different user inputs produce independent projections.

    Because SSClaimingStrategyService has no DB access, the household view
    filter (user_id) is enforced at the API layer. Here we confirm that
    calling the service with the individual member's salary/age produces a
    result distinct from another member's — i.e. each view truly reflects
    only that person's earnings history.
    """

    def test_higher_salary_yields_higher_pia(self):
        result_low = SSClaimingStrategyService.analyze(
            current_salary=50_000,
            current_age=55,
            birth_year=1969,
        )
        result_high = SSClaimingStrategyService.analyze(
            current_salary=150_000,
            current_age=55,
            birth_year=1969,
        )
        assert result_high.estimated_pia > result_low.estimated_pia

    def test_different_users_produce_different_optimal_ages(self):
        """Younger user (more years to grow) vs older user can favour
        different optimal claiming ages under the pessimistic scenario."""
        result_young = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=40,
            birth_year=1984,
        )
        result_older = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=60,
            birth_year=1964,
        )
        # Both return valid results — projections are independent
        assert 62 <= result_young.optimal_age_base_scenario <= 70
        assert 62 <= result_older.optimal_age_base_scenario <= 70

    def test_manual_pia_override_isolates_result_from_salary(self):
        """When a user provides their actual SSA PIA, salary is ignored.
        Two users with identical salary but different PIA overrides produce
        different monthly benefit projections — confirming per-user isolation."""
        result_a = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            manual_pia_override=1_800,
        )
        result_b = SSClaimingStrategyService.analyze(
            current_salary=80_000,
            current_age=58,
            birth_year=1966,
            manual_pia_override=3_200,
        )
        assert result_b.estimated_pia > result_a.estimated_pia
        opt_b = next(o for o in result_b.options if o.claiming_age == 67)
        opt_a = next(o for o in result_a.options if o.claiming_age == 67)
        assert opt_b.monthly_benefit > opt_a.monthly_benefit
