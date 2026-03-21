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
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Benchmark expense ratio: Vanguard Total Stock Market ETF (VTI) at 0.03 %
_BENCHMARK_ER = 0.0003

# ---------------------------------------------------------------------------
# Known expense ratios for common ETFs and mutual funds (as decimal fractions)
# Source: fund fact sheets / provider websites as of early 2025
# ---------------------------------------------------------------------------
KNOWN_EXPENSE_RATIOS: dict[str, float] = {
    # Vanguard broad market
    "VTI": 0.0003,
    "VTSAX": 0.0004,
    "VOO": 0.0003,
    "VFIAX": 0.0004,
    "VEA": 0.0005,
    "VXUS": 0.0007,
    "VTIAX": 0.0011,
    "BND": 0.0003,
    "BNDX": 0.0007,
    "VBTLX": 0.0005,
    "VGT": 0.0010,
    "VHT": 0.0010,
    "VFH": 0.0010,
    "VDE": 0.0010,
    "VNQ": 0.0012,
    "VGIT": 0.0004,
    "VGLT": 0.0004,
    "VGSH": 0.0004,
    "VMFXX": 0.0011,
    "VMMXX": 0.0016,
    "VTEB": 0.0005,
    "VWITX": 0.0017,
    "VWAHX": 0.0017,
    "VWELX": 0.0023,
    "VWINX": 0.0023,
    "VBIAX": 0.0007,
    "VTHRX": 0.0008,
    "VTWNX": 0.0012,
    "VFORX": 0.0012,
    "VTIVX": 0.0012,
    "VTINX": 0.0012,
    "VO": 0.0004,
    "VB": 0.0005,
    "VV": 0.0004,
    "MGC": 0.0003,
    "MGK": 0.0007,
    "MGV": 0.0007,
    # iShares / BlackRock
    "IVV": 0.0003,
    "ITOT": 0.0003,
    "IWM": 0.0019,
    "IWF": 0.0019,
    "IWD": 0.0019,
    "IWB": 0.0015,
    "IEFA": 0.0007,
    "IEMG": 0.0009,
    "AGG": 0.0003,
    "LQD": 0.0014,
    "HYG": 0.0048,
    "TLT": 0.0015,
    "IEF": 0.0015,
    "SHY": 0.0015,
    "MBB": 0.0004,
    "USMV": 0.0015,
    "MTUM": 0.0015,
    "QUAL": 0.0015,
    "SIZE": 0.0015,
    "VLUE": 0.0015,
    "IGV": 0.0041,
    "SOXX": 0.0035,
    "IYR": 0.0039,
    "IAU": 0.0025,
    "SLV": 0.0050,
    "ACWI": 0.0032,
    "EFA": 0.0032,
    "EEM": 0.0068,
    "EWJ": 0.0050,
    # SPDR / State Street
    "SPY": 0.0009,
    "MDY": 0.0023,
    "SLY": 0.0015,
    "GLD": 0.0040,
    "SPYG": 0.0004,
    "SPYV": 0.0004,
    "SPDW": 0.0003,
    "SPEM": 0.0011,
    "SPSB": 0.0003,
    "SPIB": 0.0003,
    "SPLB": 0.0003,
    "SPAB": 0.0003,
    "SPTI": 0.0003,
    "SPTS": 0.0003,
    # Schwab
    "SCHB": 0.0003,
    "SCHX": 0.0003,
    "SCHG": 0.0004,
    "SCHV": 0.0004,
    "SCHA": 0.0004,
    "SCHF": 0.0006,
    "SCHE": 0.0011,
    "SCHD": 0.0006,
    "SCHP": 0.0003,
    "SCHZ": 0.0003,
    "SCHI": 0.0003,
    "SWPPX": 0.0002,
    "SWTSX": 0.0003,
    "SWLGX": 0.0003,
    # Fidelity
    "FZROX": 0.0000,
    "FZILX": 0.0000,
    "FXAIX": 0.0015,
    "FSKAX": 0.0015,
    "FTIHX": 0.0006,
    "FBTC": 0.0025,
    "FSMDX": 0.0025,
    "FSSNX": 0.0025,
    "FXNAX": 0.0025,
    "FBND": 0.0036,
    "FZIPX": 0.0000,
    # Invesco / QQQ
    "QQQ": 0.0020,
    "QQQM": 0.0015,
    "RSP": 0.0020,
    "BKLN": 0.0065,
    "PGX": 0.0052,
    # ARK
    "ARKK": 0.0075,
    "ARKW": 0.0083,
    "ARKG": 0.0075,
    "ARKF": 0.0075,
    "ARKQ": 0.0075,
    # Sector / thematic
    "XLK": 0.0010,
    "XLF": 0.0010,
    "XLV": 0.0010,
    "XLE": 0.0010,
    "XLY": 0.0010,
    "XLP": 0.0010,
    "XLI": 0.0010,
    "XLB": 0.0010,
    "XLU": 0.0010,
    "XLRE": 0.0010,
    "XLC": 0.0010,
    "VIG": 0.0006,
    "VYM": 0.0006,
    "DVY": 0.0038,
    "DGRO": 0.0008,
    "SDY": 0.0035,
    # TIPS / inflation
    "TIP": 0.0019,
    "VTIP": 0.0004,
    # Money market / stable
    "SPAXX": 0.0042,
    "FDRXX": 0.0042,
    "SPRXX": 0.0010,
}

# Asset-class fallback estimates when ticker is unknown
# Keys match the asset_class column values in the Holding model
ASSET_CLASS_ER_ESTIMATES: dict[str, float] = {
    "domestic": 0.0012,  # Blend of passive/active US equity
    "international": 0.0020,  # International equity tends to cost more
    "bond": 0.0010,  # Fixed income average
    "cash": 0.0005,  # Money market / stable value
    "real_estate": 0.0015,  # REITs
    "commodities": 0.0030,  # Commodity funds
    "other": 0.0020,  # Unknown
}

# asset_type fallback (used when asset_class is also absent)
ASSET_TYPE_ER_ESTIMATES: dict[str, float] = {
    "etf": 0.0015,
    "mutual_fund": 0.0050,  # Active funds are pricier on average
    "stock": 0.0000,  # Individual stocks have no ER
    "bond": 0.0010,
    "cash": 0.0005,
    "other": 0.0020,
}


def resolve_expense_ratio(
    ticker: Optional[str],
    name: Optional[str],
    asset_class: Optional[str],
    asset_type: Optional[str],
    stored_er: Optional[float],
) -> Tuple[float, bool]:
    """Return ``(expense_ratio, is_estimated)``.

    Priority order:
    1. ``stored_er`` — value persisted in DB (from yfinance nightly enrichment
       task or manual user entry); authoritative, never estimated
    2. ``KNOWN_EXPENSE_RATIOS`` — static lookup for ~150 well-known tickers;
       used at query-time when the nightly task hasn't run yet or the ticker
       isn't covered by yfinance
    3. ``ASSET_CLASS_ER_ESTIMATES`` — fallback average by asset class (estimated)
    4. ``ASSET_TYPE_ER_ESTIMATES`` — fallback average by asset type (estimated)
    5. 0.0 / is_estimated=True — last resort when no data is available
    """
    if stored_er is not None:
        return float(stored_er), False

    if ticker:
        normalized = ticker.upper().strip()
        if normalized in KNOWN_EXPENSE_RATIOS:
            return KNOWN_EXPENSE_RATIOS[normalized], False

    if asset_class:
        key = asset_class.lower().strip()
        if key in ASSET_CLASS_ER_ESTIMATES:
            return ASSET_CLASS_ER_ESTIMATES[key], True

    if asset_type:
        key = asset_type.lower().strip()
        if key in ASSET_TYPE_ER_ESTIMATES:
            # Individual stocks have no ER — treat as known (not estimated)
            is_estimated = key != "stock"
            return ASSET_TYPE_ER_ESTIMATES[key], is_estimated

    return 0.0, True


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
    is_estimated: bool = False  # True when ER was estimated, not from stored/known data

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
            asset_class = FundFeeAnalyzerService._attr(h, "asset_class")
            asset_type = FundFeeAnalyzerService._attr(h, "asset_type")

            if mv <= 0:
                continue

            total_invested += mv

            er, is_estimated = resolve_expense_ratio(ticker, name, asset_class, asset_type, er_raw)

            if er_raw is None and er == 0.0 and is_estimated:
                # Truly no data and no useful fallback
                without_er_count += 1
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
                        is_estimated=False,
                    )
                )
                continue

            if er_raw is None:
                # Using estimated/looked-up value — count separately
                without_er_count += 1

            annual_fee = mv * er
            detail = FundFeeAnalyzerService._build_detail(
                ticker, name, mv, er, annual_fee, benchmark_er, high_cost_threshold, is_estimated
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
        is_estimated: bool = False,
    ) -> HoldingFeeDetail:
        ten_yr = FundFeeAnalyzerService._drag_vs_benchmark(mv, er, benchmark_er, 10)
        twenty_yr = FundFeeAnalyzerService._drag_vs_benchmark(mv, er, benchmark_er, 20)

        estimated_note = " (estimated)" if is_estimated else ""
        if er >= _EXTREME_COST_THRESHOLD:
            flag = "extreme_cost"
            suggestion = (
                f"Expense ratio of {er * 100:.2f}%{estimated_note} is very high. "
                f"Consider replacing with a comparable index ETF (e.g. 0.03–0.10%)."
            )
        elif er >= high_cost_threshold:
            flag = "high_cost"
            suggestion = (
                f"Expense ratio of {er * 100:.2f}%{estimated_note} exceeds the 0.50% threshold. "
                f"A lower-cost alternative could save ${twenty_yr:,.0f} over 20 years."
            )
        else:
            flag = "ok"
            suggestion = (
                f"Expense ratio estimated at {er * 100:.2f}% based on asset class."
                if is_estimated
                else None
            )

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
            is_estimated=is_estimated,
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
