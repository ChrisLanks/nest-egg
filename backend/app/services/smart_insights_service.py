"""Smart financial insights service.

Generates proactive, data-driven planning insights by analyzing live account
data, investment holdings, and transaction history.  Each insight is only
produced when sufficient data is available — if the relevant account types or
holdings are absent the check is silently skipped.

Insight categories
------------------
cash        – liquidity adequacy and cash-drag
investing   – fee drag, concentration risk
tax         – LTCG harvesting, IRMAA cliff
retirement  – Roth gap, HSA under-utilisation

All public methods return plain dicts so they are JSON-serialisable without
an extra Pydantic pass.
"""

from __future__ import annotations

import inspect
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.financial import MEDICARE, RETIREMENT, TAX
from app.models.account import Account, AccountType
from app.models.budget import Budget, BudgetPeriod
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.services.dashboard_service import DashboardService
from app.services.scf_benchmark_service import age_bucket, fidelity_target, get_benchmarks
from app.utils.rmd_calculator import calculate_age

logger = logging.getLogger(__name__)

# ── Insight type string constants ──────────────────────────────────────────
INSIGHT_EMERGENCY_FUND = "emergency_fund_low"
INSIGHT_CASH_DRAG = "cash_drag"
INSIGHT_FUND_FEE_DRAG = "fund_fee_drag"
INSIGHT_STOCK_CONCENTRATION = "stock_concentration"
INSIGHT_LTCG_OPPORTUNITY = "ltcg_opportunity"
INSIGHT_IRMAA_CLIFF = "irmaa_cliff"
INSIGHT_ROTH_OPPORTUNITY = "roth_opportunity"
INSIGHT_HSA_OPPORTUNITY = "hsa_opportunity"
INSIGHT_NET_WORTH_BENCHMARK = "net_worth_benchmark"
INSIGHT_SPENDING_ANOMALY = "spending_anomaly"
INSIGHT_BUDGET_OVERRUN = "budget_overrun"

# ── Account type groupings ─────────────────────────────────────────────────
LIQUID_ACCOUNT_TYPES = frozenset(
    {AccountType.CHECKING, AccountType.SAVINGS, AccountType.MONEY_MARKET}
)

TAXABLE_INVESTMENT_TYPES = frozenset({AccountType.BROKERAGE})

TRADITIONAL_RETIREMENT_TYPES = frozenset(
    {
        AccountType.RETIREMENT_401K,
        AccountType.RETIREMENT_403B,
        AccountType.RETIREMENT_457B,
        AccountType.RETIREMENT_IRA,
        AccountType.RETIREMENT_SEP_IRA,
        AccountType.RETIREMENT_SIMPLE_IRA,
    }
)

ROTH_RETIREMENT_TYPES = frozenset({AccountType.RETIREMENT_ROTH})


# ── Internal data class ─────────────────────────────────────────────────────
class _Insight:
    """Internal representation of a single smart insight."""

    __slots__ = (
        "type",
        "title",
        "message",
        "action",
        "priority",
        "category",
        "icon",
        "priority_score",
        "amount",
        "amount_label",  # Optional[str] – describes what `amount` represents in context
        "data_vintage",  # Optional[str] – ISO year string, set when insight uses static/stale data
        "data_is_stale",  # Optional[bool] – True when data source is outdated
    )

    def __init__(
        self,
        insight_type: str,
        title: str,
        message: str,
        action: str,
        priority: str,
        category: str,
        icon: str,
        priority_score: float,
        amount: Optional[float] = None,
        amount_label: Optional[str] = None,
        data_vintage: Optional[str] = None,
        data_is_stale: Optional[bool] = None,
    ) -> None:
        self.type = insight_type
        self.title = title
        self.message = message
        self.action = action
        self.priority = priority
        self.category = category
        self.icon = icon
        self.priority_score = priority_score
        self.amount = amount
        self.amount_label = amount_label
        self.data_vintage = data_vintage
        self.data_is_stale = data_is_stale

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "action": self.action,
            "priority": self.priority,
            "category": self.category,
            "icon": self.icon,
            "priority_score": self.priority_score,
            "amount": self.amount,
            "amount_label": self.amount_label,
            "data_vintage": self.data_vintage,
            "data_is_stale": self.data_is_stale,
        }


# ── Service ─────────────────────────────────────────────────────────────────
class SmartInsightsService:
    """
    Generates proactive financial planning insights from live account data.

    Usage::

        service = SmartInsightsService(db)
        insights = await service.get_insights(
            organization_id=org_id,
            user_id=user_id,          # None = household view
            user_birthdate=birthdate,  # Optional – unlocks age-gated checks
            max_insights=10,
        )

    Returns a list of dicts (JSON-ready), sorted by descending priority_score.
    """

    # Minimum liquid balance gap before flagging emergency fund
    _EMERGENCY_FUND_MONTHS = 3
    # Months of expenses before cash-drag alert fires
    _CASH_DRAG_MONTHS = 12
    # Minimum excess cash to flag (avoid noise on small accounts)
    _CASH_DRAG_MIN_EXCESS = 5_000
    # Expense-ratio threshold above which fund-fee insight fires (0.30%)
    _FEE_DRAG_THRESHOLD = 0.003
    # Single-position concentration threshold (10 %)
    _CONCENTRATION_THRESHOLD = 0.10
    # Minimum portfolio value to evaluate concentration
    _CONCENTRATION_MIN_VALUE = 10_000
    # Age at which IRMAA warnings become relevant
    _IRMAA_AGE_THRESHOLD = 55
    # Distance from IRMAA tier boundary to trigger warning ($)
    _IRMAA_GAP_THRESHOLD = 10_000
    # Spending anomaly: merchant must be 2x normal and at least this much above avg
    _ANOMALY_MULTIPLIER = 2.0
    _ANOMALY_MIN_EXCESS = 50.0
    # Budget run-rate: flag when projected MTD spend will exceed budget by this fraction
    _BUDGET_OVERRUN_THRESHOLD = 1.05  # 5% over budget

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public API ────────────────────────────────────────────────────────

    async def get_insights(
        self,
        organization_id: UUID,
        user_id: Optional[UUID] = None,
        user_birthdate: Optional[date] = None,
        max_insights: int = 10,
    ) -> list[dict]:
        """
        Return up to *max_insights* smart planning insights sorted by priority.

        Each check is wrapped individually so one failure never blocks others.
        """
        accounts = await self._get_accounts(organization_id, user_id)
        if not accounts:
            return []

        account_ids = [a.id for a in accounts]
        checks = [
            self._check_emergency_fund(accounts, account_ids),
            self._check_cash_drag(accounts, account_ids),
            self._check_fund_fees(organization_id, user_id),
            self._check_stock_concentration(organization_id, user_id),
            self._check_ltcg_opportunity(accounts, account_ids),
            self._check_irmaa_cliff(account_ids, user_birthdate),
            self._check_roth_opportunity_sync(accounts, user_birthdate),
            self._check_hsa_opportunity_sync(accounts),
            self._check_net_worth_benchmark(accounts, account_ids, user_birthdate),
            self._check_spending_anomaly(account_ids),
            self._check_budget_overrun(organization_id, user_id, account_ids),
        ]

        insights: list[_Insight] = []
        for coro in checks:
            try:
                # Some checks are sync and return directly; others are async
                if inspect.isawaitable(coro):
                    result = await coro
                else:
                    result = coro
                if result is not None:
                    insights.append(result)
            except Exception:
                logger.exception("Smart insight check failed — skipping")

        insights.sort(key=lambda x: x.priority_score, reverse=True)
        return [i.to_dict() for i in insights[:max_insights]]

    # ── Data helpers ─────────────────────────────────────────────────────

    async def _get_accounts(self, organization_id: UUID, user_id: Optional[UUID]) -> list[Account]:
        conditions: list = [
            Account.organization_id == organization_id,
            Account.is_active.is_(True),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)
        result = await self.db.execute(select(Account).where(and_(*conditions)))
        return list(result.scalars().all())

    async def _monthly_expenses(self, account_ids: list[UUID], months: int = 3) -> Decimal:
        """Average monthly spending over the past *months* months."""
        if not account_ids:
            return Decimal("0")
        cutoff = date.today() - timedelta(days=30 * months)
        result = await self.db.execute(
            select(func.sum(func.abs(Transaction.amount))).where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= cutoff,
                    Transaction.amount < 0,
                    Transaction.is_transfer.is_(False),
                )
            )
        )
        total = Decimal(str(result.scalar() or 0))
        return total / months

    async def _annual_income_estimate(self, account_ids: list[UUID]) -> Decimal:
        """Sum of positive (income) transactions over the past 12 months."""
        if not account_ids:
            return Decimal("0")
        cutoff = date.today() - timedelta(days=365)
        result = await self.db.execute(
            select(func.sum(Transaction.amount)).where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= cutoff,
                    Transaction.amount > 0,
                    Transaction.is_transfer.is_(False),
                )
            )
        )
        return Decimal(str(result.scalar() or 0))

    # ── Insight checks ────────────────────────────────────────────────────

    async def _check_emergency_fund(
        self, accounts: list[Account], account_ids: list[UUID]
    ) -> Optional[_Insight]:
        """Flag when liquid savings < 3 months of spending."""
        liquid = [a for a in accounts if a.account_type in LIQUID_ACCOUNT_TYPES]
        if not liquid:
            return None

        liquid_balance = sum(Decimal(str(a.current_balance or 0)) for a in liquid)
        liquid_ids = [a.id for a in liquid]
        monthly_exp = await self._monthly_expenses(liquid_ids)
        if monthly_exp <= 0:
            return None

        months_covered = float(liquid_balance / monthly_exp)
        if months_covered >= self._EMERGENCY_FUND_MONTHS:
            return None

        target = float(monthly_exp * self._EMERGENCY_FUND_MONTHS)
        gap = max(0.0, target - float(liquid_balance))
        return _Insight(
            insight_type=INSIGHT_EMERGENCY_FUND,
            title="Emergency fund below 3-month target",
            message=(
                f"You have {months_covered:.1f} months of expenses covered "
                f"(${liquid_balance:,.0f}). Financial planners recommend 3–6 months. "
                f"Adding ${gap:,.0f} would reach the 3-month minimum."
            ),
            action="Increase your liquid savings balance",
            priority="high",
            category="cash",
            icon="🏦",
            priority_score=90 - (months_covered * 15),
            amount=round(gap, 2),
            amount_label="Shortfall to 3-month target",
        )

    async def _check_cash_drag(
        self, accounts: list[Account], account_ids: list[UUID]
    ) -> Optional[_Insight]:
        """Flag when liquid balance far exceeds a 6-month emergency fund."""
        liquid = [a for a in accounts if a.account_type in LIQUID_ACCOUNT_TYPES]
        if not liquid:
            return None

        liquid_balance = sum(Decimal(str(a.current_balance or 0)) for a in liquid)
        if liquid_balance <= 0:
            return None

        liquid_ids = [a.id for a in liquid]
        monthly_exp = await self._monthly_expenses(liquid_ids)
        if monthly_exp <= 0:
            return None

        months_covered = float(liquid_balance / monthly_exp)
        if months_covered < self._CASH_DRAG_MONTHS:
            return None

        excess = float(liquid_balance) - float(monthly_exp * 6)
        if excess < self._CASH_DRAG_MIN_EXCESS:
            return None

        # Opportunity cost: 7 % market vs 1 % HYSA over 20 years
        opportunity_cost = excess * ((1.07**20) - (1.01**20))
        return _Insight(
            insight_type=INSIGHT_CASH_DRAG,
            title=f"${excess:,.0f} in excess cash could be invested",
            message=(
                f"You have {months_covered:.0f} months of expenses in cash "
                f"(6-month target). The extra ${excess:,.0f} earning ~1 % instead of "
                f"market returns could cost ~${opportunity_cost:,.0f} over 20 years."
            ),
            action="Consider moving excess cash to a brokerage or retirement account",
            priority="medium",
            category="cash",
            icon="💸",
            priority_score=min(75, 40 + months_covered),
            amount=round(excess, 2),
            amount_label="Investable excess cash",
        )

    async def _check_fund_fees(
        self, organization_id: UUID, user_id: Optional[UUID]
    ) -> Optional[_Insight]:
        """Flag when weighted-average fund expense ratio exceeds 0.30 %."""
        conditions: list = [
            Holding.organization_id == organization_id,
            Holding.expense_ratio.isnot(None),
            Holding.expense_ratio > 0,
            Holding.current_total_value > 0,
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await self.db.execute(
            select(
                Holding.ticker,
                Holding.name,
                Holding.current_total_value,
                Holding.expense_ratio,
            )
            .join(Account, Holding.account_id == Account.id)
            .where(and_(*conditions))
        )
        rows = result.all()
        if not rows:
            return None

        total_invested = sum(float(r.current_total_value) for r in rows)
        if total_invested < 1_000:
            return None

        annual_fees = sum(float(r.current_total_value) * float(r.expense_ratio) for r in rows)
        weighted_er = annual_fees / total_invested

        if weighted_er <= self._FEE_DRAG_THRESHOLD:
            return None

        twenty_yr_drag = total_invested * ((1.07**20) - ((1.07 - weighted_er) ** 20))
        worst = max(rows, key=lambda r: float(r.expense_ratio))
        worst_label = worst.ticker or worst.name or "Unknown"

        return _Insight(
            insight_type=INSIGHT_FUND_FEE_DRAG,
            title=f"Paying ${annual_fees:,.0f}/yr in fund fees ({weighted_er * 100:.2f}% avg ER)",
            message=(
                f"Your portfolio's weighted expense ratio is {weighted_er * 100:.2f}%. "
                f"Low-cost index funds average 0.03–0.10%. Switching could save "
                f"~${twenty_yr_drag:,.0f} over 20 years. "
                f"Highest-cost holding: {worst_label} at "
                f"{float(worst.expense_ratio) * 100:.2f}% ER."
            ),
            action="Review fund expense ratios (the annual % fee funds charge) and consider lower-cost index fund alternatives",
            priority="high" if weighted_er > 0.01 else "medium",
            category="investing",
            icon="📊",
            priority_score=min(80, weighted_er * 5_000),
            amount=round(annual_fees, 2),
            amount_label="Annual fee drag",
        )

    async def _check_stock_concentration(
        self, organization_id: UUID, user_id: Optional[UUID]
    ) -> Optional[_Insight]:
        """Flag when any single equity position > 10 % of investable assets."""
        conditions: list = [
            Holding.organization_id == organization_id,
            Holding.current_total_value > 0,
            Holding.asset_type.notin_(["bond", "cash"]),
        ]
        if user_id is not None:
            conditions.append(Account.user_id == user_id)

        result = await self.db.execute(
            select(
                Holding.ticker,
                Holding.name,
                func.sum(Holding.current_total_value).label("position_value"),
            )
            .join(Account, Holding.account_id == Account.id)
            .where(and_(*conditions))
            .group_by(Holding.ticker, Holding.name)
        )
        rows = result.all()
        if not rows:
            return None

        total_value = sum(float(r.position_value) for r in rows)
        if total_value < self._CONCENTRATION_MIN_VALUE:
            return None

        top = max(rows, key=lambda r: float(r.position_value))
        concentration = float(top.position_value) / total_value
        if concentration <= self._CONCENTRATION_THRESHOLD:
            return None

        label = top.ticker or top.name or "Unknown"
        return _Insight(
            insight_type=INSIGHT_STOCK_CONCENTRATION,
            title=f"{label} is {concentration * 100:.0f}% of your portfolio",
            message=(
                f"{label} represents ${float(top.position_value):,.0f} "
                f"({concentration * 100:.0f}%) of your investable assets. "
                f"High single-stock concentration amplifies downside risk — "
                f"most advisors suggest keeping individual positions below 5–10%."
            ),
            action="Consider gradual diversification to reduce single-stock risk",
            priority="high" if concentration > 0.25 else "medium",
            category="investing",
            icon="⚠️",
            priority_score=min(85, concentration * 200),
            amount=round(float(top.position_value), 2),
            amount_label="Concentrated position value",
        )

    async def _check_ltcg_opportunity(
        self, accounts: list[Account], account_ids: list[UUID]
    ) -> Optional[_Insight]:
        """Flag when unrealized gains in taxable accounts fit within 0 % LTCG bracket."""
        taxable = [a for a in accounts if a.account_type in TAXABLE_INVESTMENT_TYPES]
        if not taxable:
            return None

        taxable_ids = [a.id for a in taxable]
        result = await self.db.execute(
            select(
                func.sum(Holding.current_total_value).label("market_value"),
                func.sum(Holding.total_cost_basis).label("cost_basis"),
            ).where(
                and_(
                    Holding.account_id.in_(taxable_ids),
                    Holding.current_total_value > 0,
                    Holding.total_cost_basis.isnot(None),
                    Holding.total_cost_basis > 0,
                )
            )
        )
        row = result.one_or_none()
        if not row or not row.market_value:
            return None

        unrealized_gain = float(row.market_value or 0) - float(row.cost_basis or 0)
        if unrealized_gain < 500:
            return None

        annual_income = float(await self._annual_income_estimate(account_ids))
        ltcg_limit = TAX.LTCG_BRACKETS_SINGLE[0][0]  # 0 % threshold
        headroom = max(0.0, float(ltcg_limit) - annual_income)
        if headroom <= 0:
            return None

        harvestable = min(unrealized_gain, headroom)
        if harvestable < 1_000:
            return None

        return _Insight(
            insight_type=INSIGHT_LTCG_OPPORTUNITY,
            title=f"Up to ${harvestable:,.0f} in gains may be tax-free this year",
            message=(
                f"You have ~${unrealized_gain:,.0f} in unrealized long-term gains "
                f"in taxable accounts. Based on estimated income of ${annual_income:,.0f}, "
                f"you may realise up to ${harvestable:,.0f} at the 0% long-term capital "
                f"gains rate (applies below ${float(ltcg_limit):,.0f} for single filers)."
            ),
            action="Review taxable holdings with gains before year-end",
            priority="medium",
            category="tax",
            icon="📈",
            priority_score=min(70, harvestable / 200),
            amount=round(harvestable, 2),
            amount_label="Tax-free gain opportunity",
        )

    async def _check_irmaa_cliff(
        self,
        account_ids: list[UUID],
        user_birthdate: Optional[date],
    ) -> Optional[_Insight]:
        """Warn when estimated income is within $10 k of an IRMAA tier threshold."""
        if user_birthdate is None:
            return None
        age = calculate_age(user_birthdate)
        if age < self._IRMAA_AGE_THRESHOLD:
            return None

        annual_income = float(await self._annual_income_estimate(account_ids))
        if annual_income <= 0:
            return None

        brackets = MEDICARE.IRMAA_BRACKETS_SINGLE
        for i, (threshold, part_b_surcharge, _part_d) in enumerate(brackets):
            if threshold == float("inf"):
                continue
            gap = float(threshold) - annual_income
            if 0 < gap <= self._IRMAA_GAP_THRESHOLD:
                if i + 1 < len(brackets):
                    next_surcharge = brackets[i + 1][1]
                    annual_increase = (next_surcharge - part_b_surcharge) * 12
                    return _Insight(
                        insight_type=INSIGHT_IRMAA_CLIFF,
                        title=f"${gap:,.0f} from a ${annual_increase:,.0f}/yr Medicare surcharge",
                        message=(
                            f"Your estimated income of ${annual_income:,.0f} is ${gap:,.0f} "
                            f"below the ${float(threshold):,.0f} IRMAA threshold. Crossing it "
                            f"adds ${annual_increase:,.0f}/year to your Medicare Part B+D "
                            f"premiums. Consider Roth conversions, tax-loss harvesting, "
                            f"or deferring income."
                        ),
                        action="Review income sources to stay below the Medicare premium surcharge (IRMAA) threshold",
                        priority="high",
                        category="tax",
                        icon="🏥",
                        priority_score=80 - (gap / 200),
                        amount=round(annual_increase, 2),
                        amount_label="Annual Medicare surcharge if crossed",
                    )
        return None

    def _check_roth_opportunity_sync(
        self, accounts: list[Account], user_birthdate: Optional[date]
    ) -> Optional[_Insight]:
        """Suggest opening a Roth IRA when user has only pre-tax retirement accounts."""
        has_traditional = any(a.account_type in TRADITIONAL_RETIREMENT_TYPES for a in accounts)
        has_roth = any(a.account_type in ROTH_RETIREMENT_TYPES for a in accounts)
        if not has_traditional or has_roth:
            return None

        if user_birthdate is not None:
            age = calculate_age(user_birthdate)
            if age >= 60:
                return None  # Roth conversion math changes significantly at 60+

        traditional_balance = sum(
            float(a.current_balance or 0)
            for a in accounts
            if a.account_type in TRADITIONAL_RETIREMENT_TYPES
        )
        return _Insight(
            insight_type=INSIGHT_ROTH_OPPORTUNITY,
            title="No Roth account — all retirement withdrawals will be taxable",
            message=(
                f"You have ${traditional_balance:,.0f} in pre-tax retirement accounts "
                f"but no Roth IRA or Roth 401(k). Every dollar withdrawn in retirement "
                f"is ordinary income, increasing taxes and future RMDs. Converting a "
                f"portion each year can reduce lifetime tax and create tax-free inheritance."
            ),
            action="Open a Roth IRA and explore annual Roth conversion amounts",
            priority="medium",
            category="retirement",
            icon="🔄",
            priority_score=55,
            amount=round(traditional_balance, 2),
            amount_label="Pre-tax balance eligible for conversion",
        )

    def _check_hsa_opportunity_sync(self, accounts: list[Account]) -> Optional[_Insight]:
        """Suggest maximising HSA when balance is below a meaningful threshold."""
        hsa = [a for a in accounts if a.account_type == AccountType.HSA]
        if not hsa:
            return None

        total_hsa = sum(float(a.current_balance or 0) for a in hsa)
        if total_hsa >= 5_000:
            return None  # Already making good use of HSA

        individual_limit = RETIREMENT.LIMIT_HSA_INDIVIDUAL
        gap = max(0.0, individual_limit - total_hsa)
        return _Insight(
            insight_type=INSIGHT_HSA_OPPORTUNITY,
            title=f"HSA at ${total_hsa:,.0f} — triple tax-advantage underutilised",
            message=(
                f"Your HSA holds ${total_hsa:,.0f}. The {RETIREMENT.TAX_YEAR} limit is "
                f"${individual_limit:,}. HSAs offer a rare triple tax benefit: "
                f"pre-tax contributions, tax-free growth, and tax-free medical withdrawals. "
                f"Unused funds roll over indefinitely and can be invested."
            ),
            action=f"Aim to contribute ${gap:,.0f} more to max your HSA in {RETIREMENT.TAX_YEAR}",
            priority="low",
            category="tax",
            icon="🏥",
            priority_score=35,
            amount=round(gap, 2),
            amount_label="Remaining contribution headroom",
        )

    async def _check_net_worth_benchmark(
        self,
        accounts: list[Account],
        account_ids: list[UUID],
        user_birthdate: Optional[date],
    ) -> Optional[_Insight]:
        """Compare the user's net worth to Federal Reserve SCF age-group medians.

        Requires birthdate to determine the correct age bucket.  Skips silently
        when birthdate is absent or net worth is zero/negative.

        Uses dynamic SCF data when available (scraped from the Fed website and
        cached locally), with automatic fallback to the static table in
        financial.py.  Sets data_is_stale=True when the survey data is more
        than 3 years old so the frontend can show a notice.
        """
        if user_birthdate is None:
            return None

        age = calculate_age(user_birthdate)
        if age < 18:
            return None

        # ── Net worth = vesting-aware assets minus liabilities ───────────
        dashboard_svc = DashboardService(self.db)
        net_worth = float(dashboard_svc.compute_net_worth(accounts))
        if net_worth <= 0:
            return None

        # ── Benchmark data (dynamic → cached → static fallback) ──────────
        benchmarks = get_benchmarks()
        bucket = age_bucket(age)
        median_nw = benchmarks["median"].get(bucket)
        if median_nw is None:
            return None

        is_stale: bool = benchmarks.get("is_stale", False)
        survey_year: int = benchmarks.get("survey_year", 2022)
        vintage_label = str(survey_year)

        # ── Annual income estimate for Fidelity milestone ────────────────
        annual_income = float(await self._annual_income_estimate(account_ids))
        fidelity_tgt = fidelity_target(age, annual_income)

        # ── Determine how the user stacks up ─────────────────────────────
        if not median_nw:
            return None
        pct_of_median = net_worth / median_nw  # e.g. 0.8 = 80 % of median

        if pct_of_median >= 2.0:
            # Well above median — no action needed, skip the insight
            return None

        # Build comparison message
        if pct_of_median >= 1.0:
            comparison = (
                f"Your net worth of ${net_worth:,.0f} is "
                f"{pct_of_median:.0%} of the median for your age group "
                f"(${median_nw:,.0f} for ages {bucket})."
            )
            priority = "low"
            priority_score = 30.0
        elif pct_of_median >= 0.5:
            gap = median_nw - net_worth
            comparison = (
                f"Your net worth of ${net_worth:,.0f} is below the median "
                f"of ${median_nw:,.0f} for ages {bucket} by ${gap:,.0f}."
            )
            priority = "medium"
            priority_score = 55.0
        else:
            gap = median_nw - net_worth
            comparison = (
                f"Your net worth of ${net_worth:,.0f} is significantly below "
                f"the median of ${median_nw:,.0f} for ages {bucket} (${gap:,.0f} gap)."
            )
            priority = "high"
            priority_score = 72.0

        # Add Fidelity milestone context when income is available
        fidelity_note = ""
        if fidelity_tgt is not None:
            fidelity_pct = net_worth / fidelity_tgt
            fidelity_note = (
                f" Fidelity's rule of thumb targets ${fidelity_tgt:,.0f} "
                f"at age {age} ({fidelity_pct:.0%} of that target)."
            )

        stale_note = (
            f" (Benchmark data from {survey_year} SCF — update may be available.)"
            if is_stale
            else ""
        )

        return _Insight(
            insight_type=INSIGHT_NET_WORTH_BENCHMARK,
            title=f"Net worth vs. peers (ages {bucket})",
            message=comparison + fidelity_note + stale_note,
            action=(
                "Review your savings rate, investment allocation, and debt payoff plan "
                "to close the gap over time."
            ),
            priority=priority,
            category="retirement",
            icon="📊",
            priority_score=priority_score,
            amount=round(net_worth, 2),
            amount_label="Your current net worth",
            data_vintage=vintage_label,
            data_is_stale=is_stale,
        )

    async def _check_spending_anomaly(
        self, account_ids: list[UUID]
    ) -> Optional[_Insight]:
        """Flag when any merchant's spend this month is 2x+ their 3-month average.

        Looks at the current calendar month vs the prior 3 full months.
        Only triggers when the excess is meaningful (>= $50).
        Skips transfers.
        """
        if not account_ids:
            return None

        today = date.today()
        month_start = today.replace(day=1)
        three_months_ago = (month_start - timedelta(days=90)).replace(day=1)

        # MTD spending by merchant (current month)
        mtd_result = await self.db.execute(
            select(
                Transaction.merchant_name,
                func.sum(func.abs(Transaction.amount)).label("mtd_total"),
            ).where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= month_start,
                    Transaction.amount < 0,
                    Transaction.is_transfer.is_(False),
                    Transaction.merchant_name.isnot(None),
                )
            ).group_by(Transaction.merchant_name)
        )
        mtd_by_merchant = {r.merchant_name: float(r.mtd_total) for r in mtd_result.all()}

        if not mtd_by_merchant:
            return None

        # Average monthly spend per merchant over prior 3 months
        hist_result = await self.db.execute(
            select(
                Transaction.merchant_name,
                func.sum(func.abs(Transaction.amount)).label("hist_total"),
            ).where(
                and_(
                    Transaction.account_id.in_(account_ids),
                    Transaction.date >= three_months_ago,
                    Transaction.date < month_start,
                    Transaction.amount < 0,
                    Transaction.is_transfer.is_(False),
                    Transaction.merchant_name.isnot(None),
                )
            ).group_by(Transaction.merchant_name)
        )
        # avg per month = total / 3
        hist_avg_by_merchant = {
            r.merchant_name: float(r.hist_total) / 3.0
            for r in hist_result.all()
            if float(r.hist_total) > 0
        }

        # Find worst anomaly
        worst_merchant: Optional[str] = None
        worst_ratio = 0.0
        worst_mtd = 0.0
        worst_avg = 0.0

        for merchant, mtd in mtd_by_merchant.items():
            avg = hist_avg_by_merchant.get(merchant)
            if avg is None or avg < 5.0:
                continue  # skip merchants with negligible history
            ratio = mtd / avg
            excess = mtd - avg
            if (
                ratio >= self._ANOMALY_MULTIPLIER
                and excess >= self._ANOMALY_MIN_EXCESS
                and ratio > worst_ratio
            ):
                worst_ratio = ratio
                worst_merchant = merchant
                worst_mtd = mtd
                worst_avg = avg

        if worst_merchant is None:
            return None

        excess = worst_mtd - worst_avg
        return _Insight(
            insight_type=INSIGHT_SPENDING_ANOMALY,
            title=f"Unusual spending at {worst_merchant}",
            message=(
                f"You've spent ${worst_mtd:,.0f} at {worst_merchant} this month — "
                f"{worst_ratio:.1f}x your typical ${worst_avg:,.0f}/month. "
                f"That's ${excess:,.0f} above your normal pattern."
            ),
            action=f"Review recent transactions at {worst_merchant}",
            priority="medium" if worst_ratio < 5.0 else "high",
            category="spending",
            icon="🔍",
            priority_score=min(70, 40 + worst_ratio * 5),
            amount=round(excess, 2),
            amount_label="Spend above typical monthly amount",
        )

    async def _check_budget_overrun(
        self,
        organization_id: UUID,
        user_id: Optional[UUID],
        account_ids: list[UUID],
    ) -> Optional[_Insight]:
        """Flag when an active monthly budget is on track to exceed its limit.

        Projects full-month spend from MTD velocity:
            projected = (mtd_spend / days_elapsed) * days_in_month
        Fires when projected >= budget_amount * _BUDGET_OVERRUN_THRESHOLD.
        """
        if not account_ids:
            return None

        today = date.today()
        days_elapsed = today.day
        if days_elapsed < 3:
            return None  # too early in month to project accurately

        import calendar
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        month_start = today.replace(day=1)

        # Fetch active monthly budgets
        budget_conditions = [
            Budget.organization_id == organization_id,
            Budget.period == BudgetPeriod.MONTHLY,
            Budget.start_date <= today,
        ]
        if user_id is not None:
            # budget is org-wide; user filter not supported at DB level
            pass

        bq = await self.db.execute(
            select(
                Budget.id,
                Budget.name,
                Budget.amount,
                Budget.category_id,
                Budget.label_id,
            ).where(and_(*budget_conditions))
        )
        budgets = bq.all()
        if not budgets:
            return None

        worst_budget_name: Optional[str] = None
        worst_projected = 0.0
        worst_limit = 0.0
        worst_mtd = 0.0

        for b in budgets:
            limit = float(b.amount)
            if limit <= 0:
                continue

            # Build spend query for this budget's scope
            spend_conditions = [
                Transaction.account_id.in_(account_ids),
                Transaction.date >= month_start,
                Transaction.amount < 0,
                Transaction.is_transfer.is_(False),
            ]
            if b.category_id is not None:
                spend_conditions.append(Transaction.category_id == b.category_id)
            if b.label_id is not None:
                spend_conditions.append(Transaction.label_id == b.label_id)

            mtd_result = await self.db.execute(
                select(func.sum(func.abs(Transaction.amount))).where(
                    and_(*spend_conditions)
                )
            )
            mtd_spend = float(mtd_result.scalar() or 0)
            if mtd_spend <= 0:
                continue

            projected = (mtd_spend / days_elapsed) * days_in_month

            if projected >= limit * self._BUDGET_OVERRUN_THRESHOLD and projected > worst_projected:
                worst_projected = projected
                worst_budget_name = b.name
                worst_limit = limit
                worst_mtd = mtd_spend

        if worst_budget_name is None:
            return None

        overrun = worst_projected - worst_limit
        days_remaining = days_in_month - days_elapsed
        return _Insight(
            insight_type=INSIGHT_BUDGET_OVERRUN,
            title=f"'{worst_budget_name}' budget on track to overspend",
            message=(
                f"You've spent ${worst_mtd:,.0f} with {days_remaining} days left — "
                f"on pace for ${worst_projected:,.0f} against a "
                f"${worst_limit:,.0f} monthly budget. "
                f"Projected overrun: ${overrun:,.0f}."
            ),
            action=f"Review spending in '{worst_budget_name}' to stay within budget",
            priority="high" if overrun > worst_limit * 0.2 else "medium",
            category="spending",
            icon="📉",
            priority_score=min(80, 50 + (overrun / max(worst_limit, 1)) * 100),
            amount=round(overrun, 2),
            amount_label="Projected budget overrun",
        )
