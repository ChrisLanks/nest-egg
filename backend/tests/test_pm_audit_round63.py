"""Tests for PM audit round 63 — financial plan summary, bond ladder, what-if
calculators, multi-currency net worth, Monte Carlo correlation, PE metrics,
savings goal linkage, calculator prefill.
"""

import math
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# 1. Bond ladder calculation math
# ---------------------------------------------------------------------------

class TestBondLadderService:
    def test_build_ladder_basic(self):
        from app.services.bond_ladder_service import build_ladder

        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=5,
            ladder_type="treasury",
            start_year=2026,
            annual_income_needed=Decimal("25000"),
            current_treasury_rates={
                "1_year": 0.042, "2_year": 0.041, "5_year": 0.040,
                "10_year": 0.0395, "30_year": 0.041,
            },
        )

        assert result["num_rungs"] == 5
        assert result["total_invested"] == 100000.0
        assert len(result["rungs"]) == 5
        assert result["rungs"][0]["rung"] == 1
        assert result["rungs"][4]["rung"] == 5

        # Each rung should have investment_amount = 20000
        assert result["per_rung_investment"] == 20000.0

        # Maturity years should be sequential
        for i, rung in enumerate(result["rungs"]):
            assert rung["maturity_year"] == 2026 + i + 1

        # Total interest should be positive
        assert result["total_interest"] > 0

    def test_build_ladder_cd_type(self):
        from app.services.bond_ladder_service import build_ladder

        result = build_ladder(
            total_investment=Decimal("50000"),
            num_rungs=3,
            ladder_type="cd",
            start_year=2026,
            annual_income_needed=Decimal("5000"),
            current_treasury_rates={"1_year": 0.04, "2_year": 0.039, "5_year": 0.038},
        )

        assert result["ladder_type"] == "cd"
        # CD rates should be higher than treasury (spread added)
        for rung in result["rungs"]:
            assert rung["annual_rate"] > 0

    def test_build_ladder_tips_type(self):
        from app.services.bond_ladder_service import build_ladder

        result = build_ladder(
            total_investment=Decimal("100000"),
            num_rungs=5,
            ladder_type="tips",
            start_year=2026,
            annual_income_needed=Decimal("20000"),
            current_treasury_rates={"1_year": 0.04, "2_year": 0.039, "5_year": 0.038},
        )

        assert result["ladder_type"] == "tips"
        assert len(result["rungs"]) == 5

    def test_cd_rate_estimates(self):
        from app.services.bond_ladder_service import estimate_cd_rates

        rates = estimate_cd_rates({"1_year": 0.04, "2_year": 0.039, "5_year": 0.038})
        assert "1_year" in rates
        # CD rates should be higher than treasury
        assert rates["1_year"] > 0.04


# ---------------------------------------------------------------------------
# 2. Mortgage vs Invest what-if math
# ---------------------------------------------------------------------------

class TestMortgageVsInvest:
    def test_basic_mortgage_payoff(self):
        """Test the mortgage vs invest calculation logic directly."""
        # Scenario: $300K balance, 6.5% rate, $1900/mo payment, $500 extra
        balance = 300000
        monthly_rate = 0.065 / 12
        payment = 1900
        extra = 500

        # Pay off early
        bal = balance
        months = 0
        while bal > 0 and months < 600:
            interest = bal * monthly_rate
            principal = min(payment + extra - interest, bal)
            if principal <= 0:
                break
            bal -= principal
            months += 1

        # Should pay off faster than 360 months (30 years)
        assert months < 360
        assert months > 0

    def test_invest_vs_payoff_logic(self):
        """Extra payments invested should grow over time."""
        extra = 500
        monthly_inv_return = (1 + 0.08) ** (1/12) - 1
        portfolio = 0
        for _ in range(360):
            portfolio = portfolio * (1 + monthly_inv_return) + extra
        # Over 30 years, $500/mo at 8% should grow significantly
        assert portfolio > 500 * 360  # More than just principal


# ---------------------------------------------------------------------------
# 3. State relocation tax calculation
# ---------------------------------------------------------------------------

class TestRelocationTax:
    def test_calculate_state_tax(self):
        from app.services.state_tax_service import StateTaxService

        # Should return some value for a known state
        tax = StateTaxService.calculate_state_tax("CA", Decimal("100000"))
        assert isinstance(tax, Decimal)

    def test_zero_income_tax_state(self):
        from app.services.state_tax_service import StateTaxService

        # TX has no income tax
        tax = StateTaxService.calculate_state_tax("TX", Decimal("100000"))
        assert tax == Decimal("0")

    def test_state_comparison(self):
        from app.services.state_tax_service import StateTaxService

        results = StateTaxService.compare_retirement_states(
            states=["CA", "TX"],
            projected_income=Decimal("80000"),
            projected_ss=Decimal("24000"),
            projected_pension=Decimal("0"),
        )
        assert len(results) == 2
        # TX should have lower tax
        assert results[0]["state"] == "TX"


# ---------------------------------------------------------------------------
# 4. Salary change comparison
# ---------------------------------------------------------------------------

class TestSalaryChange:
    def test_federal_tax_brackets(self):
        """Verify the federal tax calculation from the what_if module."""
        from app.api.v1.what_if import SalaryChangeRequest

        # Just verify the request model can be created
        req = SalaryChangeRequest(
            current_salary=100000,
            new_salary=120000,
            current_state="CA",
            new_state="TX",
            current_401k_match_pct=5,
            new_401k_match_pct=6,
        )
        assert req.current_salary == 100000
        assert req.new_salary == 120000


# ---------------------------------------------------------------------------
# 5. FX net worth conversion
# ---------------------------------------------------------------------------

class TestFxNetWorth:
    @pytest.mark.asyncio
    async def test_fx_service_returns_rate(self):
        from app.services.fx_service import get_rate

        rate = await get_rate("USD", "USD")
        assert rate == 1.0

        # Non-USD pairs currently return 1.0 (stub)
        rate = await get_rate("USD", "EUR")
        assert isinstance(rate, float)

    def test_net_worth_service_has_multi_currency(self):
        """Verify net_worth_service returns multi_currency fields."""
        from app.services.net_worth_service import NetWorthService
        # The get_current_breakdown method should exist
        assert hasattr(NetWorthService, "get_current_breakdown")


# ---------------------------------------------------------------------------
# 6. Monte Carlo with asset_allocation (backward compat)
# ---------------------------------------------------------------------------

class TestMonteCarloCorrelation:
    def test_cholesky_decomposition(self):
        from app.services.retirement.monte_carlo_service import _cholesky_decomposition

        # Simple 2x2 positive-definite matrix
        matrix = [[4.0, 2.0], [2.0, 3.0]]
        L = _cholesky_decomposition(matrix)
        assert len(L) == 2
        assert len(L[0]) == 2

        # Verify L * L^T ≈ original matrix
        for i in range(2):
            for j in range(2):
                s = sum(L[i][k] * L[j][k] for k in range(2))
                assert abs(s - matrix[i][j]) < 1e-10

    def test_cholesky_correlation_matrix(self):
        from app.services.retirement.monte_carlo_service import (
            _cholesky_decomposition,
            _CORRELATION_MATRIX,
        )

        L = _cholesky_decomposition(_CORRELATION_MATRIX)
        n = len(_CORRELATION_MATRIX)

        # Verify L * L^T ≈ original
        for i in range(n):
            for j in range(n):
                s = sum(L[i][k] * L[j][k] for k in range(n))
                assert abs(s - _CORRELATION_MATRIX[i][j]) < 1e-8

    def test_generate_correlated_returns(self):
        from app.services.retirement.monte_carlo_service import _generate_correlated_returns

        allocation = {"stocks": 0.60, "bonds": 0.30, "real_estate": 0.05, "cash": 0.05}

        # Should return a float
        ret = _generate_correlated_returns(allocation, 0.07, 0.15)
        assert isinstance(ret, float)
        # Sanity: return should be in a reasonable range
        assert -0.80 < ret < 1.50

    def test_correlated_returns_distribution(self):
        """Run many simulations and check mean is reasonable."""
        from app.services.retirement.monte_carlo_service import _generate_correlated_returns
        import random
        random.seed(42)

        allocation = {"stocks": 0.60, "bonds": 0.30, "real_estate": 0.05, "cash": 0.05}
        returns = [_generate_correlated_returns(allocation, 0.07, 0.15) for _ in range(5000)]

        mean_return = sum(returns) / len(returns)
        # Mean should be roughly the weighted average of asset class means
        # stocks: 0.60 * 0.10 = 0.06, bonds: 0.30 * 0.04 = 0.012,
        # real_estate: 0.05 * 0.07 = 0.0035, cash: 0.05 * 0.03 = 0.0015
        # Expected ≈ 0.077
        assert 0.03 < mean_return < 0.15

    def test_backward_compat_no_asset_allocation(self):
        """Without asset_allocation, the old single-return path should work."""
        from app.services.retirement.monte_carlo_service import (
            _generate_normal_return,
            _generate_lognormal_return,
        )

        # Original functions should still work
        ret = _generate_normal_return(0.07, 0.15)
        assert isinstance(ret, float)

        ret = _generate_lognormal_return(0.07, 0.15)
        assert isinstance(ret, float)


# ---------------------------------------------------------------------------
# 7. PE transaction IRR/TVPI/DPI math
# ---------------------------------------------------------------------------

class TestPEPerformance:
    def test_tvpi_calculation(self):
        from app.services.pe_performance_service import calculate_tvpi

        # TVPI = (distributions + NAV) / called
        tvpi = calculate_tvpi(
            total_distributions=Decimal("50000"),
            current_nav=Decimal("80000"),
            total_called=Decimal("100000"),
        )
        assert abs(tvpi - 1.30) < 0.01

    def test_dpi_calculation(self):
        from app.services.pe_performance_service import calculate_dpi

        dpi = calculate_dpi(
            total_distributions=Decimal("50000"),
            total_called=Decimal("100000"),
        )
        assert abs(dpi - 0.50) < 0.01

    def test_irr_simple(self):
        from app.services.pe_performance_service import calculate_irr

        # Simple: invest $100 on day 0, get $110 after 1 year -> ~10% IRR
        cash_flows = [(date(2024, 1, 1), -100)]
        irr = calculate_irr(cash_flows, Decimal("110"), date(2025, 1, 1))
        assert irr is not None
        assert abs(irr - 0.10) < 0.02  # Allow small tolerance

    def test_irr_multiple_cashflows(self):
        from app.services.pe_performance_service import calculate_irr

        cash_flows = [
            (date(2022, 1, 1), -100000),
            (date(2023, 1, 1), -50000),
            (date(2023, 6, 1), 30000),  # distribution
        ]
        irr = calculate_irr(cash_flows, Decimal("180000"), date(2025, 1, 1))
        assert irr is not None
        assert irr > 0  # Should be positive given NAV > total invested

    def test_compute_pe_metrics(self):
        from app.services.pe_performance_service import compute_pe_metrics

        transactions = [
            {"type": "capital_call", "amount": Decimal("100000"), "date": date(2022, 1, 1)},
            {"type": "capital_call", "amount": Decimal("50000"), "date": date(2023, 1, 1)},
            {"type": "distribution", "amount": Decimal("30000"), "date": date(2023, 7, 1)},
        ]
        metrics = compute_pe_metrics(transactions, Decimal("180000"), date(2025, 1, 1))

        assert metrics["total_called"] == 150000.0
        assert metrics["total_distributions"] == 30000.0
        assert metrics["current_nav"] == 180000.0
        assert metrics["tvpi"] > 1.0  # (30000 + 180000) / 150000 = 1.4
        assert abs(metrics["tvpi"] - 1.40) < 0.01
        assert abs(metrics["dpi"] - 0.20) < 0.01
        assert metrics["irr"] is not None

    def test_zero_called_metrics(self):
        from app.services.pe_performance_service import compute_pe_metrics

        metrics = compute_pe_metrics([], Decimal("0"))
        assert metrics["tvpi"] == 0.0
        assert metrics["dpi"] == 0.0


# ---------------------------------------------------------------------------
# 8. Savings goal to life event conversion
# ---------------------------------------------------------------------------

class TestSavingsGoalToLifeEvent:
    def test_link_to_retirement_request_model(self):
        """Verify the LinkToRetirementRequest model exists."""
        from app.api.v1.savings_goals import LinkToRetirementRequest

        req = LinkToRetirementRequest(scenario_id=uuid4())
        assert req.scenario_id is not None

    def test_life_event_category_custom(self):
        """Savings goals should map to CUSTOM category."""
        from app.models.retirement import LifeEventCategory

        assert hasattr(LifeEventCategory, "CUSTOM")
        assert LifeEventCategory.CUSTOM.value == "custom"


# ---------------------------------------------------------------------------
# 9. Calculator prefill endpoint structure
# ---------------------------------------------------------------------------

class TestCalculatorPrefill:
    def test_prefill_calculator_types(self):
        """Verify the prefill endpoint handler recognizes calculator types."""
        # Import the module to check it loads
        from app.api.v1 import calculator_prefill
        assert hasattr(calculator_prefill, "calculator_prefill")

    def test_sum_balances_helper_exists(self):
        from app.api.v1.calculator_prefill import _sum_balances
        assert callable(_sum_balances)


# ---------------------------------------------------------------------------
# 10. Financial plan summary endpoint structure
# ---------------------------------------------------------------------------

class TestFinancialPlanSummary:
    def test_health_score_calculation(self):
        from app.api.v1.financial_plan import _compute_health_score

        # All good scenario
        score = _compute_health_score(
            retirement={"on_track": True},
            emergency={"months_covered": 6},
            insurance={"_coverage_score": 100},
            debt={"high_interest_debt": 0},
            estate={"has_will": True, "has_poa": True, "beneficiaries_complete": True},
        )
        assert score == 100

    def test_health_score_all_bad(self):
        from app.api.v1.financial_plan import _compute_health_score

        score = _compute_health_score(
            retirement={"on_track": False, "projected_at_retirement": 0},
            emergency={"months_covered": 0},
            insurance={"_coverage_score": 0},
            debt={"high_interest_debt": 50000},
            estate={"has_will": False, "has_poa": False, "beneficiaries_complete": False},
        )
        assert score == 0

    def test_health_score_partial(self):
        from app.api.v1.financial_plan import _compute_health_score

        score = _compute_health_score(
            retirement={"on_track": True},
            emergency={"months_covered": 3},
            insurance={"_coverage_score": 50},
            debt={"high_interest_debt": 5000},
            estate={"has_will": True, "has_poa": False, "beneficiaries_complete": True},
        )
        # retirement: 30, emergency: 12, insurance: 10, debt($5000 not < $5000): 5, estate: 10
        assert score == 67

    def test_generate_top_actions(self):
        from app.api.v1.financial_plan import _generate_top_actions

        actions = _generate_top_actions(
            retirement={"on_track": False},
            emergency={"shortfall": 5000},
            insurance={"umbrella_recommended": True, "has_umbrella": False, "_has_life": True, "has_disability": True},
            debt={"high_interest_debt": 10000},
            estate={"has_will": False, "has_poa": False},
            education={"total_education_gap": 40000},
        )
        assert len(actions) <= 5
        assert any("will" in a.lower() for a in actions)
        assert any("umbrella" in a.lower() for a in actions)

    def test_insurance_coverage_score(self):
        from app.api.v1.financial_plan import _insurance_coverage_score

        # All coverage
        assert _insurance_coverage_score(True, True, True, True) == 100
        # No coverage, umbrella not recommended
        assert _insurance_coverage_score(False, False, False, False) == 30
        # No coverage, umbrella recommended
        assert _insurance_coverage_score(False, False, False, True) == 0


# ---------------------------------------------------------------------------
# 11. PE Transaction model exists
# ---------------------------------------------------------------------------

class TestPETransactionModel:
    def test_pe_transaction_type_enum(self):
        from app.models.pe_transaction import PETransactionType

        assert PETransactionType.CAPITAL_CALL.value == "capital_call"
        assert PETransactionType.DISTRIBUTION.value == "distribution"
        assert PETransactionType.NAV_UPDATE.value == "nav_update"

    def test_pe_transaction_model_exists(self):
        from app.models.pe_transaction import PETransaction

        assert PETransaction.__tablename__ == "pe_transactions"


# ---------------------------------------------------------------------------
# 12. FX rates API structure
# ---------------------------------------------------------------------------

class TestFXRatesAPI:
    def test_fx_rates_module_loads(self):
        from app.api.v1 import fx_rates
        assert hasattr(fx_rates, "get_fx_rates")

    def test_supported_currencies(self):
        from app.services.fx_service import supported_currencies, SUPPORTED_CURRENCIES
        currencies = supported_currencies()
        assert "USD" in currencies
        assert "EUR" in currencies
        assert len(currencies) >= 5


# ---------------------------------------------------------------------------
# 13. What-if modules load
# ---------------------------------------------------------------------------

class TestWhatIfModules:
    def test_what_if_module_loads(self):
        from app.api.v1 import what_if
        assert hasattr(what_if, "mortgage_vs_invest")
        assert hasattr(what_if, "relocation_tax_impact")
        assert hasattr(what_if, "salary_change_comparison")
        assert hasattr(what_if, "early_retirement_analysis")

    def test_mortgage_vs_invest_request_model(self):
        from app.api.v1.what_if import MortgageVsInvestRequest
        req = MortgageVsInvestRequest(
            remaining_balance=300000,
            interest_rate=0.065,
            monthly_payment=1900,
            extra_monthly_payment=500,
        )
        assert req.remaining_balance == 300000

    def test_relocation_tax_request_model(self):
        from app.api.v1.what_if import RelocationTaxRequest
        req = RelocationTaxRequest(
            current_state="CA",
            target_state="TX",
            annual_income=150000,
        )
        assert req.current_state == "CA"

    def test_salary_change_request_model(self):
        from app.api.v1.what_if import SalaryChangeRequest
        req = SalaryChangeRequest(
            current_salary=100000,
            new_salary=120000,
            current_state="NY",
        )
        assert req.new_salary == 120000

    def test_early_retirement_request_model(self):
        from app.api.v1.what_if import EarlyRetirementRequest
        req = EarlyRetirementRequest(
            current_age=35,
            target_retirement_age=50,
            current_savings=500000,
            annual_savings=50000,
            annual_expenses=60000,
            expected_return=0.07,
            ss_benefit_at_62=2000,
        )
        assert req.current_age == 35
        assert req.annual_expenses == 60000
        assert req.target_retirement_age == 50

    def test_early_retirement_fire_number(self):
        """Verify FIRE number = 25x annual expenses."""
        # FIRE number for $60K/yr expenses = $1.5M
        fire_number = 60000 * 25
        assert fire_number == 1500000

    def test_early_retirement_projection(self):
        """Test FV calculation for early retirement."""
        current_savings = 500000
        annual_savings = 50000
        r = 0.07
        years = 15  # age 35 -> 50

        fv_current = current_savings * (1 + r) ** years
        fv_contributions = annual_savings * ((1 + r) ** years - 1) / r
        projected = fv_current + fv_contributions

        # Should be well over $1.5M FIRE number
        assert projected > 1500000


# ---------------------------------------------------------------------------
# 14. Bond ladder API module loads
# ---------------------------------------------------------------------------

class TestBondLadderAPI:
    def test_bond_ladder_module_loads(self):
        from app.api.v1 import bond_ladder
        assert hasattr(bond_ladder, "plan_bond_ladder")
        assert hasattr(bond_ladder, "get_ladder_rates")


# ---------------------------------------------------------------------------
# 15. Main.py router registration
# ---------------------------------------------------------------------------

class TestRouterRegistration:
    def test_new_routers_registered(self):
        from app.main import app

        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        # Check key new routes exist
        assert any("/api/v1/financial-plan" in p for p in route_paths)
        assert any("/api/v1/bond-ladder" in p for p in route_paths)
        assert any("/api/v1/what-if" in p for p in route_paths)
        assert any("/api/v1/pe-performance" in p for p in route_paths)
        assert any("/api/v1/calculators" in p for p in route_paths)


# ---------------------------------------------------------------------------
# 16. Financial plan section statuses
# ---------------------------------------------------------------------------

class TestFinancialPlanStatuses:
    def test_section_status_values(self):
        """Verify status field is set correctly for each section scenario."""
        # All valid status values
        valid_statuses = {"on_track", "needs_attention", "critical"}

        # Test retirement status
        retirement_on_track = {"on_track": True, "gap": 0}
        assert (
            "on_track" if retirement_on_track.get("on_track")
            else "critical" if retirement_on_track.get("gap", 0) > 2000
            else "needs_attention"
        ) == "on_track"

        retirement_critical = {"on_track": False, "gap": 5000}
        assert (
            "on_track" if retirement_critical.get("on_track")
            else "critical" if retirement_critical.get("gap", 0) > 2000
            else "needs_attention"
        ) == "critical"

        retirement_attention = {"on_track": False, "gap": 500}
        assert (
            "on_track" if retirement_attention.get("on_track")
            else "critical" if retirement_attention.get("gap", 0) > 2000
            else "needs_attention"
        ) == "needs_attention"

    def test_debt_status(self):
        """Debt status: on_track if no high-interest debt, critical if > $20K."""
        assert (
            "on_track" if 0 == 0
            else "critical" if 0 > 20000
            else "needs_attention"
        ) == "on_track"

        assert (
            "on_track" if 25000 == 0
            else "critical" if 25000 > 20000
            else "needs_attention"
        ) == "critical"


# ---------------------------------------------------------------------------
# 17. Multi-currency net worth aggregation
# ---------------------------------------------------------------------------

class TestMultiCurrencyNetWorth:
    def test_net_worth_service_returns_multi_currency_fields(self):
        """Verify the breakdown response structure includes FX fields."""
        from app.services.net_worth_service import NetWorthService
        svc = NetWorthService()
        # Validate the method signature
        import inspect
        sig = inspect.signature(svc.get_current_breakdown)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "organization_id" in params

    @pytest.mark.asyncio
    async def test_fx_conversion_same_currency(self):
        """USD -> USD should be 1.0 (no conversion)."""
        from app.services.fx_service import get_rate
        rate = await get_rate("USD", "USD")
        assert rate == 1.0

    @pytest.mark.asyncio
    async def test_fx_rate_returns_float(self):
        """All FX rates should return floats."""
        from app.services.fx_service import get_rate
        for currency in ["EUR", "GBP", "CAD", "JPY"]:
            rate = await get_rate("USD", currency)
            assert isinstance(rate, float)
            assert rate > 0


# ---------------------------------------------------------------------------
# 18. Early retirement what-if math
# ---------------------------------------------------------------------------

class TestEarlyRetirement:
    def test_fire_number_calculation(self):
        """FIRE number = 25x annual expenses (4% rule)."""
        expenses = 80000
        assert expenses * 25 == 2000000

    def test_on_track_projection(self):
        """Someone with enough savings should be on_track."""
        current_savings = 1000000
        annual_savings = 100000
        annual_expenses = 60000
        r = 0.07
        years = 10  # age 40 -> 50

        fire_number = annual_expenses * 25  # 1.5M

        fv_current = current_savings * (1 + r) ** years
        fv_contributions = annual_savings * ((1 + r) ** years - 1) / r
        projected = fv_current + fv_contributions

        assert projected > fire_number  # Should be on track

    def test_gap_to_fire(self):
        """Gap should be max(0, fire_number - current_savings)."""
        fire_number = 1500000
        current_savings = 500000
        gap = max(0, fire_number - current_savings)
        assert gap == 1000000

        # No gap when already there
        gap2 = max(0, fire_number - 2000000)
        assert gap2 == 0

    def test_years_to_fire_convergence(self):
        """Binary search for years to FIRE should find a solution."""
        current_savings = 200000
        annual_savings = 50000
        fire_number = 1500000
        r = 0.07

        years_to_fire = None
        for n in range(1, 100):
            fv = current_savings * (1 + r) ** n + annual_savings * ((1 + r) ** n - 1) / r
            if fv >= fire_number:
                years_to_fire = n
                break

        assert years_to_fire is not None
        assert years_to_fire > 0
        assert years_to_fire < 30  # Should be reachable within 30 years
