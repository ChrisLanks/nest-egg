"""Static flat-rate state tax provider backed by the bundled 2024 rates dict."""

from app.constants.state_tax_rates import STATE_TAX_RATES
from app.services.tax_rate_providers.base import StateTaxBracket, StateTaxProvider


class StaticStateTaxProvider(StateTaxProvider):
    """
    Flat-rate approximation provider using the bundled STATE_TAX_RATES dict.

    Always available — no network or Redis required.
    """

    def source_name(self) -> str:
        return "static_bundled_rates_2026"

    def tax_year(self) -> int:
        return 2026

    async def get_rate(self, state: str, filing_status: str, income: float) -> float:
        """Return the flat-rate approximation for the given state."""
        return STATE_TAX_RATES.get(state.upper(), 0.0)

    async def get_brackets(self, state: str, filing_status: str) -> list[StateTaxBracket]:
        """Return a single-bracket representation of the flat-rate state tax."""
        rate = STATE_TAX_RATES.get(state.upper(), 0.0)
        return [StateTaxBracket(min_income=0, max_income=float("inf"), rate=rate)]
