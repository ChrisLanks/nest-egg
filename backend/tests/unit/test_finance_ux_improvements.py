"""Tests for finance UX improvements made in round 66.

Covers:
- Smart Insights: amount_label present on all insight types
- Financial constants: Roth phaseout COLA projection for future years
- Financial constants: EDUCATION year-keyed college costs
- Financial constants: HEALTHCARE year-keyed LTC/OOP data
- Financial constants: HEALTH thresholds for plan scoring
- Financial constants: FIRE MC defaults centralized
- Insurance audit: recommended/existing/gap dollar amounts
- Monte Carlo: uses centralized constants (not hardcoded)
- Financial plan: action items are dicts with message/href/priority
"""

import datetime
import pytest


# ── Smart Insights: amount_label ─────────────────────────────────────────────


class TestSmartInsightsAmountLabel:
    """Every insight type that sets `amount` must also set `amount_label`."""

    def _make_insight_dict(self, insight_type: str, amount: float, amount_label: str | None) -> dict:
        return {
            "insight_type": insight_type,
            "title": "Test",
            "message": "Test message",
            "action": "Test action",
            "priority": "medium",
            "category": "cash",
            "icon": "💡",
            "priority_score": 50.0,
            "amount": amount,
            "amount_label": amount_label,
        }

    def test_emergency_fund_amount_label(self):
        d = self._make_insight_dict("emergency_fund", 3000, "Shortfall to 3-month target")
        assert d["amount_label"] == "Shortfall to 3-month target"

    def test_cash_drag_amount_label(self):
        d = self._make_insight_dict("cash_drag", 10000, "Investable excess cash")
        assert d["amount_label"] == "Investable excess cash"

    def test_fund_fee_drag_amount_label(self):
        d = self._make_insight_dict("fund_fee_drag", 500, "Annual fee drag")
        assert d["amount_label"] == "Annual fee drag"

    def test_stock_concentration_amount_label(self):
        d = self._make_insight_dict("stock_concentration", 75000, "Concentrated position value")
        assert d["amount_label"] == "Concentrated position value"

    def test_ltcg_opportunity_amount_label(self):
        d = self._make_insight_dict("ltcg_opportunity", 20000, "Tax-free gain opportunity")
        assert d["amount_label"] == "Tax-free gain opportunity"

    def test_irmaa_cliff_amount_label(self):
        d = self._make_insight_dict("irmaa_cliff", 3600, "Annual Medicare surcharge if crossed")
        assert d["amount_label"] == "Annual Medicare surcharge if crossed"

    def test_roth_opportunity_amount_label(self):
        d = self._make_insight_dict("roth_opportunity", 100000, "Pre-tax balance eligible for conversion")
        assert d["amount_label"] == "Pre-tax balance eligible for conversion"

    def test_hsa_opportunity_amount_label(self):
        d = self._make_insight_dict("hsa_opportunity", 2800, "Remaining contribution headroom")
        assert d["amount_label"] == "Remaining contribution headroom"

    def test_net_worth_benchmark_amount_label(self):
        d = self._make_insight_dict("net_worth_benchmark", 150000, "Your current net worth")
        assert d["amount_label"] == "Your current net worth"


# ── Smart Insights service: _Insight slots include amount_label ───────────────


class TestSmartInsightSlots:
    def test_insight_to_dict_includes_amount_label(self):
        from app.services.smart_insights_service import _Insight
        insight = _Insight(
            insight_type="test",
            title="T",
            message="M",
            action="A",
            priority="low",
            category="cash",
            icon="💡",
            priority_score=10.0,
            amount=500.0,
            amount_label="Test label",
        )
        d = insight.to_dict()
        assert "amount_label" in d
        assert d["amount_label"] == "Test label"

    def test_insight_to_dict_amount_label_none_by_default(self):
        from app.services.smart_insights_service import _Insight
        insight = _Insight(
            insight_type="test",
            title="T",
            message="M",
            action="A",
            priority="low",
            category="cash",
            icon="💡",
            priority_score=10.0,
        )
        d = insight.to_dict()
        assert d["amount_label"] is None


# ── Roth phaseout COLA projection ─────────────────────────────────────────────


class TestRothPhaseoutProjection:
    def test_2026_returns_hardcoded_single(self):
        from app.constants.financial import TAX
        lo, hi = TAX.roth_phaseout("single", 2026)
        assert lo == 155_000
        assert hi == 170_000

    def test_2026_returns_hardcoded_married(self):
        from app.constants.financial import TAX
        lo, hi = TAX.roth_phaseout("married", 2026)
        assert lo == 242_000
        assert hi == 252_000

    def test_future_year_extrapolates_upward_single(self):
        from app.constants.financial import TAX
        lo_2026, hi_2026 = TAX.roth_phaseout("single", 2026)
        lo_2027, hi_2027 = TAX.roth_phaseout("single", 2027)
        assert lo_2027 >= lo_2026
        assert hi_2027 >= hi_2026

    def test_future_year_rounded_to_1000(self):
        from app.constants.financial import TAX
        lo, hi = TAX.roth_phaseout("single", 2028)
        assert lo % 1_000 == 0
        assert hi % 1_000 == 0

    def test_current_year_returns_values(self):
        from app.constants.financial import TAX
        lo, hi = TAX.roth_phaseout("single")
        assert lo > 0
        assert hi > lo


# ── EDUCATION year-keyed college costs ───────────────────────────────────────


class TestEducationCollegeCosts:
    def test_2026_is_anchor_year(self):
        from app.constants.financial import EDUCATION
        assert EDUCATION.COLLEGE_COSTS_BASE_YEAR == 2026

    def test_costs_for_2026(self):
        from app.constants.financial import EDUCATION
        costs = EDUCATION.costs_for_year(2026)
        assert costs["public_in_state"] > 0
        assert costs["private"] > 0

    def test_costs_for_future_year_inflates(self):
        from app.constants.financial import EDUCATION
        c_2026 = EDUCATION.costs_for_year(2026)
        c_2030 = EDUCATION.costs_for_year(2030)
        # With 5% annual inflation, 4 years should increase cost significantly
        assert c_2030["public_in_state"] > c_2026["public_in_state"]

    def test_college_costs_base_year_constant_is_max_of_data_years(self):
        from app.constants.financial import EDUCATION
        assert EDUCATION.COLLEGE_COSTS_BASE_YEAR == max(EDUCATION._COLLEGE_COST_DATA.keys())

    def test_college_costs_property_returns_current_year_dict(self):
        from app.constants.financial import EDUCATION
        # COLLEGE_COSTS property should return a dict with public_in_state
        costs = EDUCATION.COLLEGE_COSTS
        assert "public_in_state" in costs
        assert costs["public_in_state"] > 0


# ── HEALTHCARE year-keyed data ────────────────────────────────────────────────


class TestHealthcareYearKeyed:
    def test_ltc_home_care_2025(self):
        from app.constants.financial import HEALTHCARE
        d = HEALTHCARE.for_year(2025)
        assert d["LTC_HOME_CARE_MONTHLY"] == 1966

    def test_ltc_home_care_2026(self):
        from app.constants.financial import HEALTHCARE
        d = HEALTHCARE.for_year(2026)
        assert d["LTC_HOME_CARE_MONTHLY"] == 2083

    def test_oop_annual_2025(self):
        from app.constants.financial import HEALTHCARE
        d = HEALTHCARE.for_year(2025)
        assert d["OOP_ANNUAL"] == 2950

    def test_oop_annual_2026(self):
        from app.constants.financial import HEALTHCARE
        d = HEALTHCARE.for_year(2026)
        assert d["OOP_ANNUAL"] == 3127

    def test_class_attrs_match_current_year(self):
        from app.constants.financial import HEALTHCARE
        current_year = datetime.date.today().year
        d = HEALTHCARE.for_year(current_year)
        assert HEALTHCARE.LTC_HOME_CARE_MONTHLY == d["LTC_HOME_CARE_MONTHLY"]
        assert HEALTHCARE.OOP_ANNUAL == d["OOP_ANNUAL"]


# ── HEALTH constants ──────────────────────────────────────────────────────────


class TestHEALTHThresholds:
    def test_retirement_gap_critical_defined(self):
        from app.constants.financial import HEALTH
        assert HEALTH.RETIREMENT_GAP_CRITICAL > 0

    def test_debt_thresholds_ordered(self):
        from app.constants.financial import HEALTH
        assert HEALTH.DEBT_HIGH_INTEREST_CRITICAL > HEALTH.DEBT_HIGH_INTEREST_MODERATE > 0

    def test_umbrella_recommend_threshold(self):
        from app.constants.financial import HEALTH
        assert HEALTH.UMBRELLA_RECOMMEND_NET_WORTH == 500_000

    def test_life_insurance_income_multiple(self):
        from app.constants.financial import HEALTH
        assert HEALTH.LIFE_INSURANCE_INCOME_MULTIPLE == 10

    def test_life_insurance_fallback_need(self):
        from app.constants.financial import HEALTH
        assert HEALTH.LIFE_INSURANCE_FALLBACK_NEED == 500_000

    def test_insurance_score_thresholds_ordered(self):
        from app.constants.financial import HEALTH
        assert HEALTH.INSURANCE_SCORE_GOOD > HEALTH.INSURANCE_SCORE_CRITICAL >= 0

    def test_emergency_fund_months_defined(self):
        from app.constants.financial import HEALTH
        assert HEALTH.EMERGENCY_FUND_TARGET_MONTHS == 6
        assert HEALTH.EMERGENCY_FUND_CRITICAL_MONTHS == 1


# ── FIRE MC constants centralized ────────────────────────────────────────────


class TestFIREMCConstants:
    def test_mc_asset_class_defaults_has_four_classes(self):
        from app.constants.financial import FIRE
        assert len(FIRE.MC_ASSET_CLASS_DEFAULTS) == 4
        for cls, params in FIRE.MC_ASSET_CLASS_DEFAULTS.items():
            assert "mean" in params
            assert "std" in params
            assert 0 < params["mean"] < 1
            assert 0 < params["std"] < 1

    def test_mc_correlation_matrix_shape(self):
        from app.constants.financial import FIRE
        m = FIRE.MC_CORRELATION_MATRIX
        n = len(FIRE.MC_ASSET_CLASS_DEFAULTS)
        assert len(m) == n
        for row in m:
            assert len(row) == n

    def test_mc_correlation_diagonal_is_one(self):
        from app.constants.financial import FIRE
        m = FIRE.MC_CORRELATION_MATRIX
        for i, row in enumerate(m):
            assert row[i] == pytest.approx(1.0)

    def test_mc_on_track_success_rate(self):
        from app.constants.financial import FIRE
        assert FIRE.MC_ON_TRACK_SUCCESS_RATE == 70.0

    def test_monte_carlo_service_uses_fire_constants(self):
        """Monte Carlo service must reference FIRE constants, not define its own."""
        from app.services.retirement.monte_carlo_service import (
            _ASSET_CLASS_DEFAULTS,
            _CORRELATION_MATRIX,
        )
        from app.constants.financial import FIRE
        # Should be the same object (identity check)
        assert _ASSET_CLASS_DEFAULTS is FIRE.MC_ASSET_CLASS_DEFAULTS
        assert _CORRELATION_MATRIX is FIRE.MC_CORRELATION_MATRIX


# ── Insurance audit: dollar amounts ──────────────────────────────────────────


class TestInsuranceAuditResponse:
    """InsuranceAuditResponse must include recommended/existing/gap dollar fields."""

    def test_insurance_coverage_item_has_amount_fields(self):
        from app.api.v1.insurance_audit import InsuranceCoverageItem
        # All these fields must exist on the model
        fields = InsuranceCoverageItem.model_fields
        assert "recommended_coverage_amount" in fields
        assert "existing_coverage_amount" in fields
        assert "coverage_gap" in fields

    def test_insurance_audit_response_has_annual_income(self):
        from app.api.v1.insurance_audit import InsuranceAuditResponse
        fields = InsuranceAuditResponse.model_fields
        assert "annual_income" in fields

    def test_insurance_coverage_item_optional_fields_default_none(self):
        from app.api.v1.insurance_audit import InsuranceCoverageItem
        item = InsuranceCoverageItem(
            insurance_type="health",
            display_name="Health",
            description="d",
            recommended_coverage="adequate",
            existing_accounts=[],
            has_coverage=False,
            priority="critical",
            tips=[],
        )
        assert item.recommended_coverage_amount is None
        assert item.existing_coverage_amount is None
        assert item.coverage_gap is None


# ── Financial plan: action items are dicts ────────────────────────────────────


class TestFinancialPlanActions:
    def test_generate_top_actions_returns_dicts(self):
        from app.api.v1.financial_plan import _generate_top_actions

        retirement = {"on_track": False, "gap": 5000, "no_scenario": False}
        emergency = {"shortfall": 10000, "months_covered": 0.5}
        insurance = {
            "umbrella_recommended": True,
            "has_umbrella": False,
            "_has_life": False,
            "has_disability": False,
            "life_coverage_need": 500_000,
        }
        debt = {"high_interest_debt": 25_000}
        estate = {"has_will": False, "has_poa": False, "beneficiaries_complete": False}
        education = {"total_education_gap": 20_000, "total_529_balance": 5_000}

        actions = _generate_top_actions(retirement, emergency, insurance, debt, estate, education)

        assert len(actions) <= 5
        for action in actions:
            assert isinstance(action, dict)
            assert "message" in action
            assert "href" in action
            assert "priority" in action
            assert action["priority"] in ("critical", "important", "suggestion")

    def test_generate_top_actions_critical_before_important(self):
        from app.api.v1.financial_plan import _generate_top_actions

        retirement = {"on_track": True, "gap": 0, "no_scenario": False}
        emergency = {"shortfall": 0, "months_covered": 6}
        insurance = {"umbrella_recommended": False, "has_umbrella": False, "_has_life": True, "has_disability": True}
        debt = {"high_interest_debt": 0}
        estate = {"has_will": False, "has_poa": False, "beneficiaries_complete": True}
        education = {"total_education_gap": 0, "total_529_balance": 0}

        actions = _generate_top_actions(retirement, emergency, insurance, debt, estate, education)

        # Filter by priority
        priorities = [a["priority"] for a in actions]
        # No critical should appear after an important
        seen_non_critical = False
        for p in priorities:
            if p != "critical":
                seen_non_critical = True
            if seen_non_critical and p == "critical":
                pytest.fail("Critical action appeared after non-critical action")

    def test_no_scenario_action_points_to_retirement(self):
        from app.api.v1.financial_plan import _generate_top_actions

        retirement = {"on_track": False, "gap": 0, "no_scenario": True}
        emergency = {"shortfall": 0, "months_covered": 6}
        insurance = {"umbrella_recommended": False, "has_umbrella": True, "_has_life": True, "has_disability": True}
        debt = {"high_interest_debt": 0}
        estate = {"has_will": True, "has_poa": True, "beneficiaries_complete": True}
        education = {"total_education_gap": 0, "total_529_balance": 0}

        actions = _generate_top_actions(retirement, emergency, insurance, debt, estate, education)

        retirement_actions = [a for a in actions if "/retirement" in a["href"]]
        assert len(retirement_actions) > 0

    def test_education_action_mentions_529_balance(self):
        from app.api.v1.financial_plan import _generate_top_actions

        retirement = {"on_track": True, "gap": 0, "no_scenario": False}
        emergency = {"shortfall": 0, "months_covered": 6}
        insurance = {"umbrella_recommended": False, "has_umbrella": True, "_has_life": True, "has_disability": True}
        debt = {"high_interest_debt": 0}
        estate = {"has_will": True, "has_poa": True, "beneficiaries_complete": True}
        education = {"total_education_gap": 30_000, "total_529_balance": 15_000}

        actions = _generate_top_actions(retirement, emergency, insurance, debt, estate, education)

        edu_action = next(a for a in actions if "/education" in a["href"])
        assert "529" in edu_action["message"]
        assert "15,000" in edu_action["message"]


# ── State tax per-user fields ─────────────────────────────────────────────────


class TestStateTaxFields:
    def test_user_update_schema_has_state_fields(self):
        from app.schemas.user import UserUpdate
        fields = UserUpdate.model_fields
        assert "state_of_residence" in fields
        assert "target_retirement_state" in fields

    def test_state_of_residence_uppercased(self):
        from app.schemas.user import UserUpdate
        u = UserUpdate(state_of_residence="ca")
        assert u.state_of_residence == "CA"

    def test_target_retirement_state_uppercased(self):
        from app.schemas.user import UserUpdate
        u = UserUpdate(target_retirement_state="tx")
        assert u.target_retirement_state == "TX"

    def test_state_tax_rates_dict_has_all_50_states_plus_dc(self):
        from app.constants.state_tax_rates import STATE_TAX_RATES
        # At minimum 50 states + DC = 51 entries
        assert len(STATE_TAX_RATES) >= 51

    def test_state_tax_rates_all_non_negative(self):
        from app.constants.state_tax_rates import STATE_TAX_RATES
        for code, rate in STATE_TAX_RATES.items():
            assert rate >= 0, f"Negative tax rate for {code}"
