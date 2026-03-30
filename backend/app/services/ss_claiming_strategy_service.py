"""Social Security claiming strategy optimizer.

Extends the basic SS estimator in social_security_estimator.py to produce
a full multi-age comparison and breakeven analysis.

Features
--------
- Monthly benefit at every claiming age 62–70 (integer ages)
- Lifetime cumulative benefit by age under three longevity scenarios
  (pessimistic 78, base 85, optimistic 92)
- Cross-over / breakeven age vs the earliest-claiming option
- Spousal benefit estimate (50% of higher earner's PIA at their FRA)
- Optimal claiming age recommendation narrative
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from app.constants.financial import SS
from app.services.retirement.social_security_estimator import (
    adjust_for_claiming_age,
    estimate_aime_from_salary,
    estimate_pia,
    get_fra,
)

logger = logging.getLogger(__name__)

# Longevity scenarios (age at death)
_SCENARIOS = {
    "pessimistic": 78,
    "base": 85,
    "optimistic": 92,
}

# Annual COLA for projecting future benefit values (used in nominal projections)
_SS_COLA = SS.COLA


@dataclass
class ClaimingAgeOption:
    """Benefit and lifetime value for a single claiming age."""

    claiming_age: int
    monthly_benefit: float  # nominal at time of claim
    annual_benefit: float
    # Cumulative lifetime benefits under each longevity scenario
    lifetime_pessimistic: float  # die at 78
    lifetime_base: float  # die at 85
    lifetime_optimistic: float  # die at 92
    # Months to break even vs claiming at 62
    breakeven_vs_62_months: Optional[int]  # None if claiming_age == 62


@dataclass
class SpousalBenefit:
    """Spousal benefit summary (50% of higher earner's PIA at FRA)."""

    higher_earner_pia: float
    spousal_monthly_at_fra: float
    spousal_monthly_at_62: float
    spousal_monthly_at_70: float
    note: str


@dataclass
class FileAndSuspendAnalysis:
    """Voluntary Suspension (post-2016 rules) analysis.

    Under the Bipartisan Budget Act 2015, the "file and suspend" loophole
    was closed effective April 30, 2016.  Today, voluntarily suspending
    benefits also suspends any benefits payable on the worker's record
    (spousal, dependent) until the worker resumes.

    What remains useful:
      - A worker at or past FRA can voluntarily suspend to earn 8%/year
        delayed retirement credits up to age 70, but spousal benefits are
        also suspended during that period.
      - Restricted Application: Workers born BEFORE Jan 2, 1954 can still
        file a restricted application for spousal-only benefits at FRA while
        deferring their own; those born on/after that date are subject to
        deemed filing rules.

    DATA NOTE: Rules are statutory (BBA 2015 / OBRA 1990).  They do not
    change year-to-year.  The restricted-application cutoff birth year (1954)
    is hard-coded by law.
    """

    worker_birth_year: int
    worker_fra: float

    # Voluntary suspension
    can_suspend: bool  # worker is at or past FRA
    monthly_gain_per_year_suspended: float  # 8%/yr DRC on PIA
    max_gain_age: int  # 70 (no credits beyond 70)
    suspension_note: str

    # Restricted application
    restricted_app_eligible: bool  # born before Jan 2, 1954
    restricted_app_note: str

    # Joint optimal strategy narrative
    joint_strategy_summary: str


@dataclass
class SSClaimingResult:
    """Complete SS claiming strategy analysis."""

    current_age: int
    fra_age: float
    estimated_pia: float
    options: list[ClaimingAgeOption]  # one per age 62–70
    optimal_age_base_scenario: int
    optimal_age_pessimistic_scenario: int
    optimal_age_optimistic_scenario: int
    spousal: Optional[SpousalBenefit]
    file_and_suspend: Optional[FileAndSuspendAnalysis]
    summary: str


# ── Helper ─────────────────────────────────────────────────────────────────


def _lifetime_benefit(
    monthly: float,
    claiming_age: int,
    death_age: int,
) -> float:
    """Total nominal benefits received from claiming_age to death_age."""
    if death_age <= claiming_age:
        return 0.0
    months = (death_age - claiming_age) * 12
    return round(monthly * months, 2)


def _breakeven_months(
    monthly_early: float,
    monthly_later: float,
    age_early: int,
    age_later: int,
) -> Optional[int]:
    """
    Months after the *later* claimant starts receiving benefits at which
    their cumulative total overtakes the early claimant's cumulative total.

    Returns None if the later benefit never exceeds early (same rate or lower).
    """
    if monthly_later <= monthly_early:
        return None

    # Months from age_early to age_later (foregone benefits by waiting)
    foregone_months = (age_later - age_early) * 12
    foregone_total = monthly_early * foregone_months

    # Monthly advantage
    monthly_diff = monthly_later - monthly_early

    # Months after age_later to recoup foregone benefits
    recoup_months = int(foregone_total / monthly_diff) + 1
    total_months = foregone_months + recoup_months
    return total_months


# ── Service ────────────────────────────────────────────────────────────────


class SSClaimingStrategyService:
    """
    Produces a full Social Security claiming strategy analysis.

    All methods are static — no database access.

    Usage::

        result = SSClaimingStrategyService.analyze(
            current_salary=90_000,
            current_age=58,
            birth_year=1966,
            career_start_age=22,
            spouse_pia=800,   # optional
        )
        print(result.optimal_age_base_scenario)
    """

    @staticmethod
    def analyze(
        current_salary: float,
        current_age: int,
        birth_year: int,
        career_start_age: int = 22,
        manual_pia_override: Optional[float] = None,
        spouse_pia: Optional[float] = None,
    ) -> SSClaimingResult:
        """
        Full claiming strategy analysis.

        Parameters
        ----------
        current_salary:
            Current annual gross salary.
        current_age:
            Current age in whole years.
        birth_year:
            Year of birth (determines FRA).
        career_start_age:
            Age when regular earnings began (default 22).
        manual_pia_override:
            If you know your actual PIA from your SSA statement, provide it here.
        spouse_pia:
            If married, the spouse's estimated PIA (optional).
        """
        fra = get_fra(birth_year)

        if manual_pia_override is not None and manual_pia_override > 0:
            pia = float(manual_pia_override)
        else:
            aime = estimate_aime_from_salary(current_salary, current_age, career_start_age)
            pia = estimate_pia(aime)

        # Build options for every claiming age 62–70
        options: list[ClaimingAgeOption] = []
        benefit_at_62 = adjust_for_claiming_age(pia, fra, 62)

        for age in range(62, 71):
            monthly = adjust_for_claiming_age(pia, fra, age)
            annual = round(monthly * 12, 2)

            lt_pess = _lifetime_benefit(monthly, age, _SCENARIOS["pessimistic"])
            lt_base = _lifetime_benefit(monthly, age, _SCENARIOS["base"])
            lt_opt = _lifetime_benefit(monthly, age, _SCENARIOS["optimistic"])

            if age == 62:
                be_vs_62 = None
            else:
                be_vs_62 = _breakeven_months(benefit_at_62, monthly, 62, age)

            options.append(
                ClaimingAgeOption(
                    claiming_age=age,
                    monthly_benefit=monthly,
                    annual_benefit=annual,
                    lifetime_pessimistic=lt_pess,
                    lifetime_base=lt_base,
                    lifetime_optimistic=lt_opt,
                    breakeven_vs_62_months=be_vs_62,
                )
            )

        # Optimal ages by scenario (highest lifetime benefit)
        opt_base = max(options, key=lambda o: o.lifetime_base).claiming_age
        opt_pess = max(options, key=lambda o: o.lifetime_pessimistic).claiming_age
        opt_opt = max(options, key=lambda o: o.lifetime_optimistic).claiming_age

        # Spousal benefit (50% of higher-earner PIA at their FRA)
        spousal: Optional[SpousalBenefit] = None
        if spouse_pia is not None and spouse_pia > 0:
            sp_fra_monthly = round(spouse_pia * 0.50, 2)
            # Spousal benefit reduction for claiming at 62:
            # FRA 67 = 60 months early → first 36 months at 25/36% + 24 months at 5/12%
            # = 25% + 10% = 35% reduction → multiplier = 0.65
            months_early = round((fra - 62) * 12)
            first_36 = min(months_early, 36)
            beyond_36 = max(0, months_early - 36)
            spousal_reduction = first_36 * (25 / 36 / 100) + beyond_36 * (5 / 12 / 100)
            sp_at_62 = round(sp_fra_monthly * (1 - spousal_reduction), 2)
            sp_at_70 = sp_fra_monthly  # no credits beyond FRA for spousal
            spousal = SpousalBenefit(
                higher_earner_pia=round(pia, 2),
                spousal_monthly_at_fra=sp_fra_monthly,
                spousal_monthly_at_62=sp_at_62,
                spousal_monthly_at_70=sp_at_70,
                note=(
                    "Spousal benefit is up to 50% of the higher earner's PIA "
                    "at FRA. It does NOT earn delayed retirement credits beyond FRA. "
                    "Spousal benefit is only available if the higher earner has filed."
                ),
            )

        # File-and-suspend / restricted application analysis
        fas = SSClaimingStrategyService._build_file_and_suspend(
            pia=pia,
            fra=fra,
            birth_year=birth_year,
            current_age=current_age,
            spousal=spousal,
        )

        # Build summary narrative
        option_at_opt = next(o for o in options if o.claiming_age == opt_base)
        option_at_62 = options[0]
        summary = SSClaimingStrategyService._build_summary(
            pia, fra, options, opt_base, opt_pess, opt_opt, option_at_opt, option_at_62
        )

        return SSClaimingResult(
            current_age=current_age,
            fra_age=fra,
            estimated_pia=round(pia, 2),
            options=options,
            optimal_age_base_scenario=opt_base,
            optimal_age_pessimistic_scenario=opt_pess,
            optimal_age_optimistic_scenario=opt_opt,
            spousal=spousal,
            file_and_suspend=fas,
            summary=summary,
        )

    @staticmethod
    def _build_file_and_suspend(
        pia: float,
        fra: float,
        birth_year: int,
        current_age: int,
        spousal: Optional[SpousalBenefit],
    ) -> "FileAndSuspendAnalysis":
        """Compute voluntary-suspension and restricted-application eligibility.

        Rules:
          - Voluntary suspension: available at or after FRA; earns 8%/yr DRC.
          - Restricted application: only for workers born BEFORE Jan 2, 1954.
            (OBRA 1990 / BBA 2015 deemed-filing rules)
        """
        can_suspend = current_age >= int(fra)
        monthly_gain = round(pia * 0.08 / 12, 2)  # 8% of PIA per year = 0.667%/month

        if can_suspend:
            susp_note = (
                f"You can voluntarily suspend benefits to earn delayed retirement credits "
                f"(+8%/year = +${monthly_gain:.0f}/month per year suspended, up to age 70). "
                "⚠ During suspension, any spousal or dependent benefits on your record are "
                "also suspended (post-2016 rules)."
            )
        else:
            years_to_fra = max(0, int(fra) - current_age)
            susp_note = (
                f"Voluntary suspension becomes available at your FRA (age {fra:.1f}, "
                f"approximately {years_to_fra} year(s) from now)."
            )

        # Restricted application cutoff: born before Jan 2, 1954
        restricted_eligible = birth_year < 1954
        if restricted_eligible:
            restr_note = (
                "Born before Jan 2, 1954: you may file a Restricted Application "
                "at FRA to claim spousal-only benefits while deferring your own "
                "benefit to earn delayed credits up to age 70.  "
                "Consult ssa.gov/myaccount or a financial advisor before filing."
            )
        else:
            restr_note = (
                "Born on or after Jan 2, 1954: deemed filing rules apply — "
                "applying for any SS benefit automatically claims all benefits "
                "you are eligible for.  The restricted-application strategy is "
                "not available to you."
            )

        # Joint strategy narrative
        if spousal is not None:
            if restricted_eligible:
                joint_summary = (
                    f"Joint strategy opportunity: the lower-earning spouse could file "
                    f"at FRA for spousal benefits (${spousal.spousal_monthly_at_fra:,.0f}/mo) "
                    f"while the higher earner delays to 70 "
                    f"(+${monthly_gain * 12 * (70 - int(fra)):,.0f} total additional benefit). "
                    "Restricted application required — verify eligibility at ssa.gov."
                )
            else:
                joint_summary = (
                    "Under current deemed-filing rules both spouses must claim all "
                    "eligible benefits simultaneously.  Consider coordinating claiming "
                    "ages to maximise the higher earner's survivor benefit — the survivor "
                    "receives 100% of the deceased's benefit if higher than their own."
                )
        else:
            joint_summary = "Provide spouse PIA to see joint claiming strategy recommendations."

        return FileAndSuspendAnalysis(
            worker_birth_year=birth_year,
            worker_fra=fra,
            can_suspend=can_suspend,
            monthly_gain_per_year_suspended=monthly_gain,
            max_gain_age=70,
            suspension_note=susp_note,
            restricted_app_eligible=restricted_eligible,
            restricted_app_note=restr_note,
            joint_strategy_summary=joint_summary,
        )

    @staticmethod
    def _build_summary(
        pia: float,
        fra: float,
        options: list[ClaimingAgeOption],
        opt_base: int,
        opt_pess: int,
        opt_opt: int,
        option_at_opt: ClaimingAgeOption,
        option_at_62: ClaimingAgeOption,
    ) -> str:
        monthly_at_opt = option_at_opt.monthly_benefit
        monthly_at_62 = option_at_62.monthly_benefit
        be = option_at_opt.breakeven_vs_62_months

        parts = [
            f"Estimated PIA at FRA (age {fra:.1f}): ${pia:,.0f}/month.",
            f"Claiming at {opt_base} maximises lifetime benefits "
            f"(assume living to age {_SCENARIOS['base']}): "
            f"${monthly_at_opt:,.0f}/month "
            f"vs ${monthly_at_62:,.0f}/month at 62.",
        ]

        if be is not None:
            years = be // 12
            months = be % 12
            parts.append(
                f"Break-even vs claiming at 62: {years}y {months}m after your 62nd birthday."
            )

        if opt_pess != opt_base:
            parts.append(
                f"If longevity is a concern (die at {_SCENARIOS['pessimistic']}), "
                f"claiming at {opt_pess} is better."
            )
        if opt_opt != opt_base:
            parts.append(
                f"If you expect a long life (live to {_SCENARIOS['optimistic']}), "
                f"claiming at {opt_opt} maximises total benefits."
            )

        parts.append("This is an estimate — get your personalised statement at ssa.gov/myaccount.")
        return " ".join(parts)
