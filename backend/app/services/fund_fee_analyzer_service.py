"""Fund fee analyzer service.

Analyses investment-account holdings to quantify the ongoing drag from
fund expense ratios and surface actionable cost-reduction opportunities.

Key outputs
-----------
- Weighted-average expense ratio across the portfolio
- Annual dollar cost of fees
- 10- and 20-year compounding impact vs a hypothetical 0.05 % benchmark
- Per-holding breakdown sorted by annual fee drag
- "High-cost" flags for any holding above the *high_cost_threshold*

The service is pure-Python / no database — pass in a list of holding-like
dicts (or ORM objects with the same attribute names) and it returns a plain
dict suitable for JSON serialisation.

Typical caller::

    rows = await db.execute(
        select(Holding, Account)
        .join(Account)
        .where(Account.organization_id == org_id)
    )
    holdings = [{"ticker": h.ticker, ...} for h, _ in rows]
    result = FundFeeAnalyzerService.analyze(holdings)
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Benchmark expense ratio: Vanguard Total Stock Market ETF (VTI) at 0.03 %
_BENCHMARK_ER = 0.0003
# Flag funds above this threshold as "high cost"
_HIGH_COST_THRESHOLD = 0.005  # 0.50 %
# Flag funds above this as "extreme cost" (actively managed)
_EXTREME_COST_THRESHOLD = 0.01  # 1.00 %
# Assumed annual return *before* fees for drag modelling
_BASE_RETURN = 0.07


@dataclass
class HoldingFeeDetail:
    """Per-holding fee breakdown."""

    ticker: Optional[str]
    name: Optional[str]
    market_value: float
    expense_ratio: float
    annual_fee: float
    ten_year_drag: float
    twenty_year_drag: float
    flag: str  # "ok" | "high_cost" | "extreme_cost" | "no_data"
    suggestion: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FundFeeAnalysis:
    """Top-level fund fee analysis result."""

    total_invested: float
    holdings_with_er_data: int
    holdings_missing_er_data: int
    annual_fee_drag: float
    weighted_avg_expense_ratio: float
    benchmark_expense_ratio: float
    ten_year_impact_vs_benchmark: float
    twenty_year_impact_vs_benchmark: float
    high_cost_count: int
    holdings: list[HoldingFeeDetail]
    summary: str

    def to_dict(self) -> dict:
        return {
            "total_invested": self.total_invested,
            "holdings_with_er_data": self.holdings_with_er_data,
            "holdings_missing_er_data": self.holdings_missing_er_data,
            "annual_fee_drag": self.annual_fee_drag,
            "weighted_avg_expense_ratio": self.weighted_avg_expense_ratio,
            "benchmark_expense_ratio": self.benchmark_expense_ratio,
            "ten_year_impact_vs_benchmark": self.ten_year_impact_vs_benchmark,
            "twenty_year_impact_vs_benchmark": self.twenty_year_impact_vs_benchmark,
            "high_cost_count": self.high_cost_count,
            "holdings": [h.to_dict() for h in self.holdings],
            "summary": self.summary,
        }


class FundFeeAnalyzerService:
    """
    Analyses fund expense ratios across a set of investment holdings.

    All methods are static — no instantiation required.

    Usage::

        # holdings is a list of dicts or objects with:
        #   ticker, name, current_total_value, expense_ratio
        result = FundFeeAnalyzerService.analyze(holdings)
        print(result.annual_fee_drag)
    """

    @staticmethod
    def analyze(
        holdings: list,
        high_cost_threshold: float = _HIGH_COST_THRESHOLD,
        benchmark_er: float = _BENCHMARK_ER,
    ) -> FundFeeAnalysis:
        """
        Analyse fund fees across *holdings*.

        *holdings* can be ORM objects or dicts with keys:
        ``ticker``, ``name``, ``current_total_value``, ``expense_ratio``.
        ``expense_ratio`` may be ``None`` (holding is skipped for fee math but
        counted in ``holdings_missing_er_data``).
        """
        with_er: list[HoldingFeeDetail] = []
        without_er_count = 0
        total_invested = 0.0

        for h in holdings:
            ticker = FundFeeAnalyzerService._attr(h, "ticker")
            name = FundFeeAnalyzerService._attr(h, "name")
            mv = float(FundFeeAnalyzerService._attr(h, "current_total_value") or 0)
            er_raw = FundFeeAnalyzerService._attr(h, "expense_ratio")

            if mv <= 0:
                continue

            total_invested += mv

            if er_raw is None:
                without_er_count += 1
                # Still include in list so user can see which holdings lack data
                with_er.append(
                    HoldingFeeDetail(
                        ticker=ticker,
                        name=name,
                        market_value=round(mv, 2),
                        expense_ratio=0.0,
                        annual_fee=0.0,
                        ten_year_drag=0.0,
                        twenty_year_drag=0.0,
                        flag="no_data",
                        suggestion="Expense ratio data unavailable — look up on fund's fact sheet",
                    )
                )
                continue

            er = float(er_raw)
            annual_fee = mv * er
            detail = FundFeeAnalyzerService._build_detail(
                ticker, name, mv, er, annual_fee, benchmark_er, high_cost_threshold
            )
            with_er.append(detail)

        # Separate holdings with fee data for weighted calculations
        with_fee_data = [h for h in with_er if h.flag != "no_data"]
        total_with_data = sum(h.market_value for h in with_fee_data)

        if total_with_data <= 0:
            return FundFeeAnalysis(
                total_invested=round(total_invested, 2),
                holdings_with_er_data=0,
                holdings_missing_er_data=without_er_count,
                annual_fee_drag=0.0,
                weighted_avg_expense_ratio=0.0,
                benchmark_expense_ratio=benchmark_er,
                ten_year_impact_vs_benchmark=0.0,
                twenty_year_impact_vs_benchmark=0.0,
                high_cost_count=0,
                holdings=with_er,
                summary="No expense ratio data available for any holdings.",
            )

        annual_drag = sum(h.annual_fee for h in with_fee_data)
        weighted_er = annual_drag / total_with_data
        high_cost_count = sum(1 for h in with_fee_data if h.flag in ("high_cost", "extreme_cost"))

        # Benchmark-relative drag over time
        ten_yr = FundFeeAnalyzerService._drag_vs_benchmark(
            total_with_data, weighted_er, benchmark_er, 10
        )
        twenty_yr = FundFeeAnalyzerService._drag_vs_benchmark(
            total_with_data, weighted_er, benchmark_er, 20
        )

        # Sort by annual fee descending (biggest drag first)
        with_er.sort(key=lambda h: h.annual_fee, reverse=True)

        summary = FundFeeAnalyzerService._build_summary(
            annual_drag, weighted_er, twenty_yr, high_cost_count
        )

        return FundFeeAnalysis(
            total_invested=round(total_invested, 2),
            holdings_with_er_data=len(with_fee_data),
            holdings_missing_er_data=without_er_count,
            annual_fee_drag=round(annual_drag, 2),
            weighted_avg_expense_ratio=round(weighted_er, 6),
            benchmark_expense_ratio=benchmark_er,
            ten_year_impact_vs_benchmark=round(ten_yr, 2),
            twenty_year_impact_vs_benchmark=round(twenty_yr, 2),
            high_cost_count=high_cost_count,
            holdings=with_er,
            summary=summary,
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _attr(obj, key: str):
        """Get attribute from dict or object."""
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    @staticmethod
    def _build_detail(
        ticker: Optional[str],
        name: Optional[str],
        mv: float,
        er: float,
        annual_fee: float,
        benchmark_er: float,
        high_cost_threshold: float,
    ) -> HoldingFeeDetail:
        ten_yr = FundFeeAnalyzerService._drag_vs_benchmark(mv, er, benchmark_er, 10)
        twenty_yr = FundFeeAnalyzerService._drag_vs_benchmark(mv, er, benchmark_er, 20)

        if er >= _EXTREME_COST_THRESHOLD:
            flag = "extreme_cost"
            suggestion = (
                f"Expense ratio of {er * 100:.2f}% is very high. "
                f"Consider replacing with a comparable index ETF (e.g. 0.03–0.10%)."
            )
        elif er >= high_cost_threshold:
            flag = "high_cost"
            suggestion = (
                f"Expense ratio of {er * 100:.2f}% exceeds the 0.50% threshold. "
                f"A lower-cost alternative could save ${twenty_yr:,.0f} over 20 years."
            )
        else:
            flag = "ok"
            suggestion = None

        return HoldingFeeDetail(
            ticker=ticker,
            name=name,
            market_value=round(mv, 2),
            expense_ratio=er,
            annual_fee=round(annual_fee, 2),
            ten_year_drag=round(ten_yr, 2),
            twenty_year_drag=round(twenty_yr, 2),
            flag=flag,
            suggestion=suggestion,
        )

    @staticmethod
    def _drag_vs_benchmark(
        amount: float, actual_er: float, benchmark_er: float, years: int
    ) -> float:
        """
        Dollar drag of paying *actual_er* instead of *benchmark_er* over *years*.

        Uses compound growth: both scenarios grow at (_BASE_RETURN - er).
        """
        if actual_er <= benchmark_er:
            return 0.0
        value_at_actual = amount * ((1 + _BASE_RETURN - actual_er) ** years)
        value_at_bench = amount * ((1 + _BASE_RETURN - benchmark_er) ** years)
        return max(0.0, value_at_bench - value_at_actual)

    @staticmethod
    def _build_summary(
        annual_drag: float,
        weighted_er: float,
        twenty_yr: float,
        high_cost_count: int,
    ) -> str:
        lines = [
            f"Annual fee drag: ${annual_drag:,.0f} " f"(weighted ER {weighted_er * 100:.2f}%)."
        ]
        if twenty_yr > 0:
            lines.append(
                f"Switching to benchmark-cost funds could add ~${twenty_yr:,.0f} "
                f"to your portfolio over 20 years."
            )
        if high_cost_count > 0:
            lines.append(f"{high_cost_count} holding(s) flagged as high-cost (>0.50% ER).")
        if weighted_er <= _BENCHMARK_ER * 3:
            lines.append("Overall cost is low — your portfolio is cost-efficient.")
        return " ".join(lines)
