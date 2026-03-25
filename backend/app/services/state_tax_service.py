"""
State income tax awareness service.
Uses STATE_TAX_RATES from app.constants.state_tax_rates.
"""
from decimal import Decimal


class StateTaxService:
    @staticmethod
    def calculate_state_tax(state: str, taxable_income: Decimal, filing_status: str = "single") -> Decimal:
        """Estimates state income tax using flat/bracket rates from constants."""
        try:
            from app.constants.state_tax_rates import STATE_TAX_RATES
            rate_info = STATE_TAX_RATES.get(state.upper())
            if not rate_info:
                return Decimal("0")
            # Support both flat rate and bracket structures
            if isinstance(rate_info, (int, float, Decimal)):
                return (taxable_income * Decimal(str(rate_info))).quantize(Decimal("0.01"))
            if isinstance(rate_info, dict):
                rate = rate_info.get("rate", rate_info.get("flat_rate", 0))
                return (taxable_income * Decimal(str(rate))).quantize(Decimal("0.01"))
            return Decimal("0")
        except ImportError:
            return Decimal("0")

    @staticmethod
    def compare_retirement_states(
        states: list[str],
        projected_income: Decimal,
        projected_ss: Decimal,
        projected_pension: Decimal,
        filing_status: str = "single",
    ) -> list[dict]:
        """Ranks states by effective tax burden in retirement."""
        results = []
        for state in states:
            total_income = projected_income + projected_ss + projected_pension
            state_tax = StateTaxService.calculate_state_tax(state, total_income, filing_status)
            effective_rate = state_tax / total_income if total_income > 0 else Decimal("0")
            results.append({
                "state": state.upper(),
                "total_tax": float(state_tax),
                "effective_rate": float(effective_rate),
                "annual_income": float(total_income),
            })
        return sorted(results, key=lambda x: x["total_tax"])
