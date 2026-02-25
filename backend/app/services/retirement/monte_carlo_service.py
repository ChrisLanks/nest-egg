"""Server-side Monte Carlo simulation engine for retirement planning.

Ported from frontend/src/utils/monteCarloSimulation.ts with additions:
- Life event costs per simulation year
- Social Security income
- Pension/annuity income
- Tax-aware withdrawal strategy (Phase 3)
"""

import hashlib
import json
import math
import random
import time
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account, AccountType, TaxTreatment
from app.models.contribution import AccountContribution
from app.models.retirement import (
    RetirementScenario,
    RetirementSimulationResult,
)
from app.models.user import User
from app.services.retirement.healthcare_cost_estimator import (
    estimate_annual_healthcare_cost,
)
from app.services.retirement.social_security_estimator import (
    estimate_social_security,
)
from app.services.retirement.withdrawal_strategy_service import (
    AccountBuckets,
    run_withdrawal_comparison,
)
from app.utils.account_type_groups import (
    ALL_RETIREMENT_TYPES,
    INVESTMENT_ACCOUNT_TYPES,
    TAX_TREATMENT_DEFAULTS,
)
from app.utils.account_tax_treatment import get_tax_treatment
from app.utils.datetime_utils import utc_now
from app.utils.rmd_calculator import calculate_age


def _generate_normal_return(mean: float, std_dev: float) -> float:
    """Box-Muller transform for normally distributed returns."""
    u1 = random.random() or 1e-10
    u2 = random.random()
    z = math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    return mean + z * std_dev


def _compute_scenario_hash(scenario: RetirementScenario) -> str:
    """SHA-256 hash of all scenario inputs for cache invalidation."""
    parts = [
        str(scenario.retirement_age),
        str(scenario.life_expectancy),
        str(scenario.annual_spending_retirement),
        str(scenario.pre_retirement_return),
        str(scenario.post_retirement_return),
        str(scenario.volatility),
        str(scenario.inflation_rate),
        str(scenario.medical_inflation_rate),
        str(scenario.social_security_monthly),
        str(scenario.social_security_start_age),
        str(scenario.use_estimated_pia),
        str(scenario.withdrawal_strategy),
        str(scenario.withdrawal_rate),
        str(scenario.federal_tax_rate),
        str(scenario.state_tax_rate),
        str(scenario.num_simulations),
        str(scenario.healthcare_pre65_override),
        str(scenario.healthcare_medicare_override),
        str(scenario.healthcare_ltc_override),
    ]
    # Include life events in hash
    for event in sorted(scenario.life_events, key=lambda e: (e.start_age, e.name)):
        parts.extend([
            event.name,
            str(event.category),
            str(event.start_age),
            str(event.end_age),
            str(event.annual_cost),
            str(event.one_time_cost),
            str(event.income_change),
        ])
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class RetirementMonteCarloService:
    """Server-side Monte Carlo simulation engine for retirement planning."""

    @staticmethod
    async def run_simulation(
        db: AsyncSession,
        scenario: RetirementScenario,
        user: User,
    ) -> RetirementSimulationResult:
        """Run full Monte Carlo simulation for a retirement scenario."""
        start_time = time.monotonic()

        # Get current age from birthdate
        if not user.birthdate:
            raise ValueError("User birthdate is required for retirement simulation")
        current_age = calculate_age(user.birthdate)

        # Gather account data
        account_data = await RetirementMonteCarloService._gather_account_data(
            db, str(scenario.organization_id), str(scenario.user_id)
        )

        # Simulation parameters
        num_sims = scenario.num_simulations or 1000
        retirement_age = scenario.retirement_age
        life_expectancy = scenario.life_expectancy
        total_years = life_expectancy - current_age

        if total_years <= 0:
            raise ValueError("Life expectancy must be greater than current age")

        pre_return = float(scenario.pre_retirement_return) / 100
        post_return = float(scenario.post_retirement_return) / 100
        vol = float(scenario.volatility) / 100
        inflation = float(scenario.inflation_rate) / 100
        med_inflation = float(scenario.medical_inflation_rate) / 100

        annual_spending = float(scenario.annual_spending_retirement)
        annual_contributions = float(account_data["annual_contributions"])
        employer_match = float(account_data["employer_match_annual"])
        total_annual_additions = annual_contributions + employer_match
        current_portfolio = float(account_data["total_portfolio"])
        pension_monthly = float(account_data["pension_monthly"])

        # Social Security — use PIA estimator if enabled and no manual override
        ss_monthly = 0.0
        ss_start_age = scenario.social_security_start_age or 67
        estimated_pia = None
        if scenario.social_security_monthly:
            ss_monthly = float(scenario.social_security_monthly)
        elif scenario.use_estimated_pia and scenario.current_annual_income:
            birth_year = user.birthdate.year if user.birthdate else 1990
            ss_estimate = estimate_social_security(
                current_salary=float(scenario.current_annual_income),
                current_age=current_age,
                birth_year=birth_year,
                claiming_age=ss_start_age,
            )
            ss_monthly = ss_estimate["monthly_benefit"]
            estimated_pia = ss_estimate["estimated_pia"]

        # Spouse Social Security
        spouse_ss_monthly = 0.0
        spouse_ss_start_age = scenario.spouse_social_security_start_age
        if scenario.spouse_social_security_monthly:
            spouse_ss_monthly = float(scenario.spouse_social_security_monthly)

        # Healthcare cost schedule (pre-computed per age in today's dollars)
        # Apply user overrides when set, otherwise use computed estimates
        healthcare_costs: dict[int, float] = {}
        retirement_income_estimate = annual_spending  # Approximate for IRMAA
        pre65_override = float(scenario.healthcare_pre65_override) if scenario.healthcare_pre65_override is not None else None
        medicare_override = float(scenario.healthcare_medicare_override) if scenario.healthcare_medicare_override is not None else None
        ltc_override = float(scenario.healthcare_ltc_override) if scenario.healthcare_ltc_override is not None else None

        for age in range(current_age, life_expectancy + 1):
            if age >= retirement_age:
                hc = estimate_annual_healthcare_cost(
                    age=age,
                    retirement_income=retirement_income_estimate,
                    current_age=current_age,
                    medical_inflation_rate=float(scenario.medical_inflation_rate),
                )
                total = hc["total"]
                # Apply overrides by phase
                if age < 65 and pre65_override is not None:
                    total = pre65_override
                elif 65 <= age < 85 and medicare_override is not None:
                    total = medicare_override
                elif age >= 85:
                    # Age 85+: medicare + LTC components
                    ltc_part = hc.get("long_term_care", 0)
                    medicare_part = total - ltc_part
                    if medicare_override is not None:
                        medicare_part = medicare_override
                    if ltc_override is not None:
                        ltc_part = ltc_override
                    total = medicare_part + ltc_part
                healthcare_costs[age] = total

        # Build life event cost schedule: age -> (cost_this_year, is_medical_inflation)
        life_event_costs = RetirementMonteCarloService._build_life_event_schedule(
            scenario, current_age, life_expectancy
        )

        # Run simulations
        all_paths: list[list[float]] = []
        depleted_at_year: list[int] = []

        for _ in range(num_sims):
            path = [current_portfolio]
            depleted = False
            depletion_year = total_years + 1  # Infinity equivalent

            for year in range(1, total_years + 1):
                if depleted:
                    path.append(0.0)
                    continue

                age = current_age + year
                is_retired = age >= retirement_age

                # Determine return for this year
                mean_return = post_return if is_retired else pre_return
                annual_return = _generate_normal_return(mean_return, vol)

                prev_value = path[year - 1]

                if is_retired:
                    # Withdrawal phase
                    years_from_now = year
                    adjusted_spending = annual_spending * ((1 + inflation) ** years_from_now)

                    # Healthcare costs (already in today's dollars, inflate)
                    hc_cost = healthcare_costs.get(age, 0.0)
                    adjusted_hc = hc_cost * ((1 + med_inflation) ** years_from_now)

                    # Life event costs for this age
                    event_cost = 0.0
                    for cost, use_med_infl in life_event_costs.get(age, []):
                        infl = med_inflation if use_med_infl else inflation
                        event_cost += cost * ((1 + infl) ** years_from_now)

                    # Income sources
                    ss_income = 0.0
                    if age >= ss_start_age and ss_monthly > 0:
                        ss_income = ss_monthly * 12 * ((1 + inflation) ** years_from_now)

                    # Spouse SS income
                    spouse_ss_income = 0.0
                    if spouse_ss_start_age and age >= spouse_ss_start_age and spouse_ss_monthly > 0:
                        spouse_ss_income = spouse_ss_monthly * 12 * ((1 + inflation) ** years_from_now)

                    pension_income = 0.0
                    if pension_monthly > 0:
                        pension_income = pension_monthly * 12 * ((1 + inflation) ** years_from_now)

                    total_income = ss_income + spouse_ss_income + pension_income
                    net_withdrawal = adjusted_spending + adjusted_hc + event_cost - total_income

                    new_value = prev_value * (1 + annual_return) - max(net_withdrawal, 0)
                else:
                    # Accumulation phase
                    # Life event costs during accumulation
                    event_cost = 0.0
                    for cost, use_med_infl in life_event_costs.get(age, []):
                        infl = med_inflation if use_med_infl else inflation
                        event_cost += cost * ((1 + infl) ** year)

                    new_value = (
                        prev_value * (1 + annual_return)
                        + total_annual_additions
                        - event_cost
                    )

                if new_value <= 0:
                    new_value = 0.0
                    depleted = True
                    depletion_year = year

                path.append(new_value)

            all_paths.append(path)
            depleted_at_year.append(depletion_year)

        # Calculate percentiles per year
        projections = []
        for year in range(total_years + 1):
            year_values = sorted(p[year] for p in all_paths)

            p10_idx = int(num_sims * 0.10)
            p25_idx = int(num_sims * 0.25)
            p50_idx = int(num_sims * 0.50)
            p75_idx = int(num_sims * 0.75)
            p90_idx = min(int(num_sims * 0.90), num_sims - 1)

            depleted_count = sum(1 for d in depleted_at_year if d <= year)
            depletion_pct = (depleted_count / num_sims) * 100

            age = current_age + year

            # Track income sources for this age
            income_sources = None
            if age >= retirement_age:
                income_sources = {}
                if age >= ss_start_age and ss_monthly > 0:
                    income_sources["social_security"] = round(ss_monthly * 12, 2)
                if spouse_ss_start_age and age >= spouse_ss_start_age and spouse_ss_monthly > 0:
                    income_sources["spouse_social_security"] = round(spouse_ss_monthly * 12, 2)
                if pension_monthly > 0:
                    income_sources["pension"] = round(float(pension_monthly) * 12, 2)
                hc = healthcare_costs.get(age, 0)
                if hc > 0:
                    income_sources["healthcare_cost"] = round(hc, 2)

            point = {
                "age": age,
                "p10": round(year_values[p10_idx], 2),
                "p25": round(year_values[p25_idx], 2),
                "p50": round(year_values[p50_idx], 2),
                "p75": round(year_values[p75_idx], 2),
                "p90": round(year_values[p90_idx], 2),
                "depletion_pct": round(depletion_pct, 1),
            }
            if income_sources:
                point["income_sources"] = income_sources

            projections.append(point)

        # Summary stats
        final_depleted = sum(1 for d in depleted_at_year if d <= total_years)
        success_rate = ((num_sims - final_depleted) / num_sims) * 100

        sorted_depletion = sorted(d for d in depleted_at_year if d <= total_years)
        median_depletion_age = None
        if len(sorted_depletion) > num_sims / 2:
            median_year = sorted_depletion[len(sorted_depletion) // 2]
            median_depletion_age = current_age + median_year

        # Portfolio at retirement
        retirement_year_offset = retirement_age - current_age
        median_at_retirement = None
        if 0 <= retirement_year_offset <= total_years:
            retirement_values = sorted(p[retirement_year_offset] for p in all_paths)
            median_at_retirement = round(retirement_values[int(num_sims * 0.5)], 2)

        # Portfolio at end
        end_values = sorted(p[total_years] for p in all_paths)
        median_at_end = round(end_values[int(num_sims * 0.5)], 2)

        # Readiness score (0-100)
        readiness_score = RetirementMonteCarloService._calculate_readiness_score(
            success_rate=success_rate,
            current_portfolio=current_portfolio,
            annual_spending=annual_spending,
            years_in_retirement=life_expectancy - retirement_age,
            annual_savings=total_annual_additions,
            annual_income=float(scenario.current_annual_income or 0),
        )

        # Run withdrawal strategy comparison (deterministic, single run)
        withdrawal_comparison = None
        try:
            initial_buckets = AccountBuckets(
                taxable=float(account_data["taxable_balance"]),
                pre_tax=float(account_data["pre_tax_balance"]),
                roth=float(account_data["roth_balance"]),
                hsa=float(account_data["hsa_balance"]),
            )
            if initial_buckets.total > 0:
                withdrawal_comparison = run_withdrawal_comparison(
                    initial_buckets=initial_buckets,
                    annual_spending=annual_spending,
                    retirement_age=retirement_age,
                    life_expectancy=life_expectancy,
                    annual_return=post_return,
                    inflation_rate=inflation,
                    withdrawal_rate=float(scenario.withdrawal_rate) / 100,
                    federal_rate=float(scenario.federal_tax_rate) / 100,
                    state_rate=float(scenario.state_tax_rate) / 100,
                    capital_gains_rate=float(scenario.capital_gains_rate) / 100,
                    ss_annual=ss_monthly * 12,
                    pension_annual=float(pension_monthly) * 12,
                )
        except Exception:
            pass  # Non-critical; don't fail simulation if comparison errors

        compute_time_ms = int((time.monotonic() - start_time) * 1000)
        scenario_hash = _compute_scenario_hash(scenario)

        # Create and save result
        result = RetirementSimulationResult(
            scenario_id=scenario.id,
            computed_at=utc_now(),
            scenario_hash=scenario_hash,
            num_simulations=num_sims,
            compute_time_ms=compute_time_ms,
            success_rate=Decimal(str(round(success_rate, 2))),
            readiness_score=readiness_score,
            median_portfolio_at_retirement=Decimal(str(median_at_retirement)) if median_at_retirement else None,
            median_portfolio_at_end=Decimal(str(median_at_end)),
            median_depletion_age=median_depletion_age,
            estimated_pia=Decimal(str(estimated_pia)) if estimated_pia else None,
            projections_json=json.dumps(projections),
            withdrawal_comparison_json=json.dumps(withdrawal_comparison) if withdrawal_comparison else None,
        )

        db.add(result)
        await db.flush()
        return result

    @staticmethod
    def run_quick_simulation(
        current_portfolio: float,
        annual_contributions: float,
        current_age: int,
        retirement_age: int,
        life_expectancy: int,
        annual_spending: float,
        pre_retirement_return: float = 7.0,
        post_retirement_return: float = 5.0,
        volatility: float = 15.0,
        inflation_rate: float = 3.0,
        social_security_monthly: float = 0.0,
        social_security_start_age: int = 67,
        num_sims: int = 500,
    ) -> dict:
        """Lightweight simulation for real-time slider exploration. No DB access."""
        total_years = life_expectancy - current_age
        if total_years <= 0:
            return {"success_rate": 0, "readiness_score": 0, "projections": [], "median_depletion_age": None}

        pre_return = pre_retirement_return / 100
        post_return = post_retirement_return / 100
        vol = volatility / 100
        inflation = inflation_rate / 100

        all_paths: list[list[float]] = []
        depleted_at_year: list[int] = []

        for _ in range(num_sims):
            path = [current_portfolio]
            depleted = False
            depletion_year = total_years + 1

            for year in range(1, total_years + 1):
                if depleted:
                    path.append(0.0)
                    continue

                age = current_age + year
                is_retired = age >= retirement_age
                mean_return = post_return if is_retired else pre_return
                annual_return = _generate_normal_return(mean_return, vol)
                prev_value = path[year - 1]

                if is_retired:
                    adjusted_spending = annual_spending * ((1 + inflation) ** year)
                    ss_income = 0.0
                    if age >= social_security_start_age and social_security_monthly > 0:
                        ss_income = social_security_monthly * 12 * ((1 + inflation) ** year)
                    net_withdrawal = adjusted_spending - ss_income
                    new_value = prev_value * (1 + annual_return) - max(net_withdrawal, 0)
                else:
                    new_value = prev_value * (1 + annual_return) + annual_contributions

                if new_value <= 0:
                    new_value = 0.0
                    depleted = True
                    depletion_year = year

                path.append(new_value)

            all_paths.append(path)
            depleted_at_year.append(depletion_year)

        # Calculate percentiles
        projections = []
        for year in range(total_years + 1):
            year_values = sorted(p[year] for p in all_paths)
            p10_idx = int(num_sims * 0.10)
            p25_idx = int(num_sims * 0.25)
            p50_idx = int(num_sims * 0.50)
            p75_idx = int(num_sims * 0.75)
            p90_idx = min(int(num_sims * 0.90), num_sims - 1)

            depleted_count = sum(1 for d in depleted_at_year if d <= year)
            depletion_pct = (depleted_count / num_sims) * 100

            projections.append({
                "age": current_age + year,
                "p10": round(year_values[p10_idx], 2),
                "p25": round(year_values[p25_idx], 2),
                "p50": round(year_values[p50_idx], 2),
                "p75": round(year_values[p75_idx], 2),
                "p90": round(year_values[p90_idx], 2),
                "depletion_pct": round(depletion_pct, 1),
            })

        final_depleted = sum(1 for d in depleted_at_year if d <= total_years)
        success_rate = ((num_sims - final_depleted) / num_sims) * 100

        sorted_depletion = sorted(d for d in depleted_at_year if d <= total_years)
        median_depletion_age = None
        if len(sorted_depletion) > num_sims / 2:
            median_depletion_age = current_age + sorted_depletion[len(sorted_depletion) // 2]

        readiness_score = RetirementMonteCarloService._calculate_readiness_score(
            success_rate=success_rate,
            current_portfolio=current_portfolio,
            annual_spending=annual_spending,
            years_in_retirement=life_expectancy - retirement_age,
            annual_savings=annual_contributions,
            annual_income=0,
        )

        return {
            "success_rate": round(success_rate, 2),
            "readiness_score": readiness_score,
            "projections": projections,
            "median_depletion_age": median_depletion_age,
        }

    @staticmethod
    def _build_life_event_schedule(
        scenario: RetirementScenario,
        current_age: int,
        life_expectancy: int,
    ) -> dict[int, list[tuple[float, bool]]]:
        """Build a lookup: age -> list of (cost_in_todays_dollars, use_medical_inflation)."""
        schedule: dict[int, list[tuple[float, bool]]] = {}

        for event in scenario.life_events:
            use_med = event.use_medical_inflation

            # One-time cost at start_age
            if event.one_time_cost:
                cost = float(event.one_time_cost)
                schedule.setdefault(event.start_age, []).append((cost, use_med))

            # Recurring annual cost
            if event.annual_cost:
                cost = float(event.annual_cost)
                end = event.end_age or event.start_age
                for age in range(event.start_age, end + 1):
                    if current_age <= age <= life_expectancy:
                        schedule.setdefault(age, []).append((cost, use_med))

            # Income change (negative cost = income)
            if event.income_change:
                change = -float(event.income_change)  # Positive income_change reduces costs
                end = event.end_age or event.start_age
                for age in range(event.start_age, end + 1):
                    if current_age <= age <= life_expectancy:
                        schedule.setdefault(age, []).append((change, False))

        return schedule

    @staticmethod
    async def _gather_account_data(
        db: AsyncSession,
        organization_id: str,
        user_id: str,
    ) -> dict:
        """Gather current account balances and contributions for simulation."""
        # Fetch active accounts
        result = await db.execute(
            select(Account).where(
                and_(
                    Account.organization_id == organization_id,
                    Account.user_id == user_id,
                    Account.is_active.is_(True),
                )
            )
        )
        accounts = result.scalars().all()

        total_portfolio = Decimal(0)
        taxable_balance = Decimal(0)
        pre_tax_balance = Decimal(0)
        roth_balance = Decimal(0)
        hsa_balance = Decimal(0)
        cash_balance = Decimal(0)
        pension_monthly = Decimal(0)
        employer_match_annual = Decimal(0)
        annual_income = Decimal(0)
        account_items: list[dict] = []

        for account in accounts:
            balance = account.current_balance or Decimal(0)
            tax_cat = get_tax_treatment(account.account_type, account.tax_treatment)

            # Investment-type accounts contribute to portfolio
            if account.account_type in INVESTMENT_ACCOUNT_TYPES:
                total_portfolio += balance
                if tax_cat == "tax-deferred":
                    pre_tax_balance += balance
                    bucket = "pre_tax"
                elif tax_cat == "tax-free":
                    if account.account_type == AccountType.HSA:
                        hsa_balance += balance
                        bucket = "hsa"
                    else:
                        roth_balance += balance
                        bucket = "roth"
                else:
                    taxable_balance += balance
                    bucket = "taxable"
                if balance > 0:
                    account_items.append({
                        "name": account.name or account.account_type.value,
                        "balance": float(balance),
                        "bucket": bucket,
                        "account_type": account.account_type.value,
                    })

            # Cash accounts count too
            if account.account_type in (AccountType.CHECKING, AccountType.SAVINGS, AccountType.MONEY_MARKET):
                total_portfolio += balance
                taxable_balance += balance
                cash_balance += balance
                if balance > 0:
                    account_items.append({
                        "name": account.name or account.account_type.value,
                        "balance": float(balance),
                        "bucket": "cash",
                        "account_type": account.account_type.value,
                    })

            # Pension income
            if account.monthly_benefit and account.account_type == AccountType.PENSION:
                pension_monthly += account.monthly_benefit

            # Annual income from salary fields (e.g., 401k employer match setup)
            if account.annual_salary:
                try:
                    salary = Decimal(str(account.annual_salary))
                    if salary > annual_income:
                        annual_income = salary  # Use highest salary (avoid double-counting)
                except (ValueError, TypeError):
                    pass

            # Employer match
            if account.employer_match_percent and account.annual_salary:
                try:
                    salary = Decimal(str(account.annual_salary))
                    match_pct = account.employer_match_percent / Decimal(100)
                    limit_pct = (account.employer_match_limit_percent or Decimal(100)) / Decimal(100)
                    employer_match_annual += salary * min(match_pct, limit_pct) * match_pct
                except (ValueError, TypeError):
                    pass

        # Fetch active contributions
        result = await db.execute(
            select(AccountContribution).where(
                and_(
                    AccountContribution.account_id.in_([a.id for a in accounts]),
                    AccountContribution.is_active.is_(True),
                )
            )
        )
        contributions = result.scalars().all()

        annual_contributions = Decimal(0)
        for contrib in contributions:
            if not contrib.amount:
                continue
            freq = contrib.frequency.value if contrib.frequency else "monthly"
            multiplier = {
                "weekly": 52,
                "biweekly": 26,
                "monthly": 12,
                "quarterly": 4,
                "annually": 1,
            }.get(freq, 12)
            annual_contributions += contrib.amount * multiplier

        return {
            "total_portfolio": total_portfolio,
            "taxable_balance": taxable_balance,
            "pre_tax_balance": pre_tax_balance,
            "roth_balance": roth_balance,
            "hsa_balance": hsa_balance,
            "cash_balance": cash_balance,
            "pension_monthly": pension_monthly,
            "annual_contributions": annual_contributions,
            "employer_match_annual": employer_match_annual,
            "annual_income": annual_income,
            "accounts": account_items,
        }

    @staticmethod
    def _calculate_readiness_score(
        success_rate: float,
        current_portfolio: float,
        annual_spending: float,
        years_in_retirement: int,
        annual_savings: float,
        annual_income: float,
    ) -> int:
        """Compute 0-100 readiness score.

        Weighted: 50% success_rate + 30% expense_coverage + 20% savings_rate.
        """
        # Success rate component (0-100)
        success_component = success_rate

        # Expense coverage ratio: how many years of expenses are covered
        total_needed = annual_spending * max(years_in_retirement, 1)
        coverage_ratio = min(current_portfolio / total_needed, 1.0) if total_needed > 0 else 0
        coverage_component = coverage_ratio * 100

        # Savings rate component
        savings_rate = 0.0
        if annual_income > 0:
            savings_rate = min(annual_savings / annual_income, 1.0)
        elif annual_savings > 0:
            savings_rate = 0.5  # Saving something but no income data
        savings_component = savings_rate * 100

        score = (
            0.50 * success_component
            + 0.30 * coverage_component
            + 0.20 * savings_component
        )
        return max(0, min(100, round(score)))
