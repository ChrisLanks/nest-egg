"""Abstract base class for state income tax rate providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StateTaxBracket:
    """A single income tax bracket."""

    min_income: float
    max_income: float  # float("inf") for the top bracket
    rate: float


class StateTaxProvider(ABC):
    """Plugin interface for state income tax rate data."""

    @abstractmethod
    async def get_rate(self, state: str, filing_status: str, income: float) -> float:
        """Return effective marginal rate for the given state/status/income."""

    @abstractmethod
    async def get_brackets(self, state: str, filing_status: str) -> list[StateTaxBracket]:
        """Return full bracket list for the given state/filing status."""

    @abstractmethod
    def source_name(self) -> str:
        """Human-readable name of this provider."""

    @abstractmethod
    def tax_year(self) -> int:
        """The tax year this provider's data covers."""
